import io
import os
import re
import json
import uuid
import base64
import requests
from PIL import Image
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.markdown import Markdown
import fitz  # PyMuPDF
from pinecone import Pinecone

# language detection
from lingua import Language, LanguageDetectorBuilder
languages = [
    Language.ENGLISH, 
    Language.FRENCH, 
    Language.GERMAN, 
    Language.ITALIAN, 
    Language.SPANISH
    ]
detector = LanguageDetectorBuilder.from_languages(*languages).build()

from google.cloud import storage

from prompts import DEFAULT_PROMPT, MANRIQUE_PROMPT, IMAGE_INGESTION_PROMPT
from dotenv import load_dotenv
load_dotenv()

# --------------- LANGFUSE ------------------------
from langfuse import observe
# --------------- PHOENIX ------------------------
# from observability import tracer_provider_phoenix
# tracer = tracer_provider_phoenix.get_tracer(__name__)

from google import genai
EMBEDDING_API_KEY = os.getenv("JINA_AI_API_TOKEN")
EMBEDDING_MODEL = os.getenv("JINA_AI_EMBEDDING_MODEL")
EMBEDDING_URL = os.getenv("JINA_AI_EMBEDDING_URL")

# Pinecone Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_HOST = os.getenv("PINECONE_INDEX_HOST")



# Path to directory containing current file being run
BASE_DIR = Path(__file__).resolve().parent
   

class RAGEngine:
    def __init__(self, use_stderr=False):
        self.console = Console(stderr=use_stderr)
        
        # Initialize Pinecone
        if not PINECONE_API_KEY or not PINECONE_INDEX_HOST:
             self.console.print("[bold red]Error: PINECONE_API_KEY or PINECONE_INDEX_HOST not set in environment variables.[/bold red]")
             raise ValueError("Pinecone credentials missing")
             
        self.pc = Pinecone(api_key=PINECONE_API_KEY)
        self.index = self.pc.Index(host=PINECONE_INDEX_HOST)
        
        # We no longer need to explicitly 'get_collection' as namespaces are created on the fly in Pinecone

        # Use CLIP for both text and image embeddings to have a shared vector space
        # self.model = SentenceTransformer('clip-ViT-B-32') # too weak no image in results
        # we use jinaai v4 model for embeddings instead https://jina.ai/embeddings/

        # Initialize Gemini
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        self.MODEL_NAME = os.getenv("GEMINI_MODEL_NAME")
        self.FALLBACK_MODEL_NAME = os.getenv("GEMINI_FALLBACK_MODEL_NAME")
        if not GEMINI_API_KEY:
            print("Warning: GEMINI_API_KEY not found in environment variables.")
        else:
            self.llm = genai.Client(api_key=GEMINI_API_KEY)

        # Initialize Google Cloud Storage
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not self.bucket_name:
            print("Warning: GCS_BUCKET_NAME not found. Image storage will fail.")
            self.storage_client = None
        else:
            try:
                if project_id:
                    self.storage_client = storage.Client(project=project_id)
                else:
                    self.storage_client = storage.Client()
                self.bucket = self.storage_client.bucket(self.bucket_name)
            except Exception as e:
                print(f"Failed to initialize GCS client: {e}")
                self.storage_client = None



    def list_topics(self):
        try:
            stats = self.index.describe_index_stats()
            namespaces = list(stats.get('namespaces', {}).keys())
            return namespaces if namespaces else ["manrique"] # Return default if empty
        except Exception as e:
            self.console.print(f"[red]Error listing topics: {e}[/red]")
            return ["manrique"]


    def generate_image_descriptions(
        self, 
        images: List[Image.Image], 
        context_pages: List[Image.Image]) -> List[str]:
        """
        Generates descriptions for a list of images using the provided context pages.
        """
        if not images:
            return []
        
        if not hasattr(self, 'llm'):
            print("Warning: LLM not initialized. Skipping image description generation.")
            return ["Image description unavailable"] * len(images)

        content = [IMAGE_INGESTION_PROMPT, "Context Pages:"]
        content.extend(context_pages)
        content.extend(["Target Images:"])
        content.extend(images)

        try:
            response = self.llm.models.generate_content(contents=content, model=self.MODEL_NAME)
            text = response.text.strip()
            # print(f"DEBUG: Raw LLM response: {text}")

            # Use regex to find the JSON list
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                json_str = match.group(0)
                try:
                    descriptions = json.loads(json_str)
                except json.JSONDecodeError:
                    print("Failed to parse JSON from regex match.")
                    descriptions = []
            else:
                print("No JSON list found in response.")
                descriptions = []
            
            if not isinstance(descriptions, list) or len(descriptions) != len(images):
                print(f"Warning: LLM returned {len(descriptions) if isinstance(descriptions, list) else 'invalid'} descriptions for {len(images)} images.")
                # Fallback if length mismatch or invalid format
                if isinstance(descriptions, list):
                     # Pad or truncate
                    if len(descriptions) < len(images):
                        descriptions.extend(["Description unavailable"] * (len(images) - len(descriptions)))
                    else:
                        descriptions = descriptions[:len(images)]
                else:
                     return ["Image description unavailable"] * len(images)

            return descriptions

        except Exception as e:
            print(f"Error generating image descriptions: {e}")
            return ["Image description unavailable"] * len(images)


    def ingest_file(
        self, 
        file_path: str, 
        topic: str = "manrique"
    ):
        """
        Ingest a PDF file into the knowledge base.
        - Adds text chunks and image to the knowledge base.
        - Generate descriptions for extracted image. This description is used to compute image embeddings.
        text metadata: 'text' tag, source file name and page number
        image metadata: 'image' tag, source file name, page number, image Google Cloud Storage URL, image description
        
        Args:
            file_path (str): Path to the PDF file to ingest.
            topic (str): Topic name for the knowledge base. Defaults to "manrique".
        
        Returns:
            None
        """
        doc = fitz.open(file_path)
        text_pages_count = 0
        
        extracted_images_info = [] # List of tuples: (image_obj, page_num, img_index)
        pdf_pages = [] # List of page images for context

        self.console.print("Extracting content and rendering pages...", style="bold blue")

        for page_num, page in enumerate(doc):
            # 1. Extract Text
            text = page.get_text()
            if text.strip():
                self._add_text_to_db(text, file_path, page_num+1, topic)
                text_pages_count += 1
            
            # 2. Render Page for Context in image captioning step
            pix = page.get_pixmap()
            page_image = Image.open(io.BytesIO(pix.tobytes()))
            if page_image.mode != "RGB":
                page_image = page_image.convert("RGB")
            pdf_pages.append(page_image)

            # 3. Extract Images
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                try:
                    image = Image.open(io.BytesIO(image_bytes))
                    if image.mode != "RGB":
                        image = image.convert("RGB")
                    extracted_images_info.append((image, page_num+1, img_index))
                except Exception as e:
                    print(f"Failed to process image {img_index} on page {page_num+1}: {e}")
        
        # 4. Generate Descriptions in Batch
        if extracted_images_info:
            self.console.print(f"Generating descriptions for {len(extracted_images_info)} images using {len(pdf_pages)} context pages...", style="bold blue")
            images_to_describe = [info[0] for info in extracted_images_info]
            descriptions = self.generate_image_descriptions(images_to_describe, pdf_pages)
            
            # 5. Add Images to DB
            for i, (image, page_num, img_index) in enumerate(extracted_images_info):
                description = descriptions[i]
                self._add_image_to_db(image, description, file_path, page_num, img_index, topic)
        
        self.console.print(f"Ingestion complete: {text_pages_count} text pages and {len(extracted_images_info)} images processed.", style="bold green")

    #@tracer.chain(name="get_embedding")
    @observe(name="get_embedding")
    def _get_embedding(
        self, 
        text: str = None, 
        image: base64 = None
    ):
        """
        Get embeddings for a given text or image.
        
        Args:
            text (str): Text to get embeddings for.
            image (base64): Image to get embeddings for. # THIS IS NO LONGER USED IN THIS VERSION
        
        Returns:
            list: List of embeddings.
        """
        if text is None and image is None:
            raise ValueError("At least one of text or image must be provided")
        elif text is not None and image is not None:
            raise ValueError("Only one of text or image can be provided")
        if text is not None:
            payload = {
                "model": EMBEDDING_MODEL,
                "task": "text-matching",
                "input": [{"text": text}]
            }
        elif image is not None:
            payload = {
                "model": EMBEDDING_MODEL,
                "task": "text-matching",
                "input": [{"image": image}]
            }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {EMBEDDING_API_KEY}"
        }

        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(EMBEDDING_URL, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
            except Exception as e:
                self.console.print(f"[yellow]Warning: Embedding attempt {attempt + 1} failed: {e}[/yellow]")
                if attempt == max_retries - 1:
                    self.console.print(f"[red]Error getting embedding: {e}[/red]")
                    raise e
                time.sleep(1)

    def _add_text_to_db(
        self, 
        text: str, 
        file_path: str, 
        page_num: int, 
        namespace: str
    ):
        """
        Add text to the knowledge base specified by namespace.
        - compute text embedding
        - store in the knowledge base with metadata (source, page, text chunk)
        
        Args:
            text (str): Text to add to the knowledge base.
            file_path (str): Path to the file the text is from.
            page_num (int): Page number the text is from.
            namespace (str): database collection to store the text in.
        """
        embedding = self._get_embedding(text=text)
        doc_id = str(uuid.uuid4())
        
        metadata = {
            "type": "text",
            "source": file_path,
            "page": page_num,
            "text": text # Storing text in metadata for retrieval
        }
        
        self.index.upsert(
            vectors=[(doc_id, embedding, metadata)],
            namespace=namespace
        )

    def _add_image_to_db(
        self, 
        image: Image.Image, 
        description: str, 
        file_path: str, 
        page_num: int, 
        img_index: int, 
        namespace: str
    ):
        """
        Add image to the knowledge base specified by namespace.
        - compute image embedding using its text description
        - store in the knowledge base with metadata (source, page, image URL, image description)
        
        Args:
            image (Image.Image): Image to add to the knowledge base.
            description (str): Description of the image.
            file_path (str): Path to the file the image is from.
            page_num (int): Page number the image is from.
            img_index (int): Image index on the page.
            namespace (str): database collection to store the image in.
        """

        # calculate embedding from the raw image itself
        #embedding = self.model.encode(image).tolist()  # NO LONGER USED IN THIS VERSION

        doc_id = str(uuid.uuid4())
        
        # Upload to GCS
        image_url = ""
        if self.storage_client and self.bucket:
            try:
                # Sanitize filename
                filename_base = os.path.basename(file_path).replace(" ", "_")
                image_filename = f"{filename_base}_{page_num}_{img_index}.png"
                blob = self.bucket.blob(image_filename)
                
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                
                blob.upload_from_file(img_byte_arr, content_type='image/png')
                image_url = blob.public_url
            except Exception as e:
                print(f"Error uploading to GCS: {e}")
                # Fallback or just log? Assuming GCS is required now.
        else:
            print("GCS not configured, skipping image upload")
            # You might want to handle this case, maybe fallback to local or skip

        # Use description for embedding
        embedding = self._get_embedding(text=description)
        
        metadata = {
            "type": "image",
            "source": file_path,
            "page": page_num,
            "image_path": image_url,
            "description": description, # Store description in metadata
            "text": description # Store as text as well for uniform retrieval key if needed
        }

        self.index.upsert(
            vectors=[(doc_id, embedding, metadata)],
            namespace=namespace
        )

    @observe(name="load_image")
    def load_image(self, image_path: str):
        """Load an image from a URL"""
        try:
            if image_path.startswith("http"):
                response = requests.get(image_path, stream=True)
                response.raise_for_status()
                return Image.open(response.raw)
            else:
                return None
        except Exception as e:
            self.console.print(f"[red]Error loading image {image_path}: {e}[/red]")
            return None

    #@tracer.chain(name="generate_answer")
    @observe(name="generate_answer")
    def generate_answer(
        self, 
        query: str, 
        context: list, 
        history: list = [], 
        system_instruction: str = None
    ):
        """
        Generate an answer to a query based on the provided context.
        The context is prepared as a list of text chunks and images.
        - Text: source file name and text content
        - Image: image URL, image description, raw image for visual analysis
        A follow-up question is generated to be used as a suggested next question.
        
        Args:
            query (str): The query to generate an answer for.
            context (list): The context to use for generating the answer.
            history (list): The conversation history.
            system_instruction (str): The system instruction to use.
        """
        if not hasattr(self, 'llm'):
            return "LLM not initialized. Please check your API key."
            
        # If no system instruction is provided, use the default
        if not system_instruction:
            system_instruction = DEFAULT_PROMPT
        
        # Start the prompt
        parts = ["Context:\n"]
        
        # 1 - prepare context for the LLM to respond to the query
        for item in context:
            # if text chunk: we provide the source file name and the text content
            if item['type'] == 'text':
                source = item['metadata'].get('source', '')
                parts.append(f"- {source}: {item['content'].strip()}\n")
            # if image: we provide the raw image, the image text description and the image GCS URL
            elif item['type'] == 'image':
                # Load the image using the modular load_image method
                image_path = item['metadata'].get('image_path', '')
                description = item.get('content', '')
                
                img = self.load_image(image_path)
                if img:
                    parts.append(f"- [Image]: {description}\n")
                    parts.append(f"  Image URL: {image_path}\n")
                    parts.append(img)
                    parts.append("\n")
                else:
                    parts.append(f"- [Image not found or error loading at {image_path}]\n")
        
        if history:
            parts.append("\nConversation History:\n")
            for msg in history:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                parts.append(f"{role.capitalize()}: {content}\n")
        
        parts.append(f"\n\n<Question to answer> {query} </Question to answer>")
        
        # 2 - generate answer
        try:
            response = self.llm.models.generate_content(
                contents=parts, 
                model=self.MODEL_NAME,
                config={'system_instruction': system_instruction}
            )
            text = response.text
            
            # 3 - Extract follow-up question
            follow_up = None
            match = re.search(r'<follow_up>(.*?)</follow_up>', text, re.DOTALL)
            if match:
                follow_up = match.group(1).strip()
                # We return the original text (with tags) so it can be stored in history,
                # but we also return the extracted follow-up for the frontend to display as a card.
                # The frontend can choose to strip the tag for display if it wants, 
                # but actually generate_answer should return both.
            
            return {
                "answer": text,
                "follow_up": follow_up
            }

        # 4 - handle errors with fallback model in case of LLM overload    
        except Exception as e:
            if "overloaded" in str(e):
                try:
                    self.console.print("[red]Model is overloaded. Trying fallback model.[/red]")
                    try:
                        res = self.llm.models.generate_content(
                            contents=parts, 
                            model=self.FALLBACK_MODEL_NAME,
                            config={'system_instruction': system_instruction}
                        )
                    except:
                        res = self.llm.models.generate_content(
                            contents=parts, 
                            model="gemini-2.0-flash",
                            config={'system_instruction': system_instruction}
                        )
                    
                    text = res.text
                    follow_up = None
                    match = re.search(r'<follow_up>(.*?)</follow_up>', text, re.DOTALL)
                    if match:
                        follow_up = match.group(1).strip()
                    
                    return {
                        "answer": text,
                        "follow_up": follow_up
                    }
                except Exception as e:
                    return {"answer": f"Error generating answer: {e}", "follow_up": None}
            return {"answer": f"Error generating answer: {e}", "follow_up": None}

    #@tracer.chain(name="vector_search")
    @observe(name="vector_search")
    def retrieve(
        self, 
        query_embedding: list, 
        topic: str = "manrique", 
        n_results: int = 10
    ):
        """
        Retrieve documents from vector database based on query embedding.
        
        Args:
            query_embedding (list): The query embedding.
            topic (str): The collection to search in. Defaults to "manrique".
            n_results (int): The number of results to retrieve. Defaults to 10.

        Returns:
            list: The retrieved documents with their metadata.
        """
        # 1 - retrieve documents from vector database
        if topic.lower() == "manrique":
            n_results = 20
        
        results = self.index.query(
            vector=query_embedding,
            top_k=n_results,
            include_metadata=True,
            namespace=topic
        )

        self.console.print("********** VectorDB Results: ", results, style="bold yellow")
        
        # Format results
        formatted_results = []
        if results and results.get("matches"):
            for match in results["matches"]:
                # Extract text content from metadata
                content = match.metadata.get("text", "") or match.metadata.get("description", "")
                
                item = {
                    "id": match.id,
                    "score": match.score,
                    "type": match.metadata.get("type"),
                    "content": content,
                    "metadata": match.metadata
                }
                formatted_results.append(item)
        
        return formatted_results
        
    @observe(name="detect_language")
    def detect_language(self, query: str):
        """
        Detect the language of the query.
        Works only for languages initialized in the detector (ES, EN, DE, FR, IT).
        Will return the language with highest probability among the initialized languages.
        Detection can fails if the query is too short or if the language is not initialized.
        
        Args:
            query (str): The query to detect the language of.
        
        Returns:
            str: The language of the query.
        """
        try:
            lang = detector.detect_language_of(query).name
            return lang
        except Exception as e:
            return ""


    async def search_streaming(
        self, 
        query: str, 
        topic: str = "manrique", 
        n_results: int = 10, 
        history: list = []
    ):
        """
        Workflow to respond to a query using RAG.
        Detects the language of the query to respond in the same language.
        yield status messages about the progress of the workflow.
        The outputs are used by the frontend to display the answer, 
        the list of document used as context, a suggested follow-up question.
        
        Args:
            query (str): The query to search for.
            topic (str): The collection to search in. Defaults to "manrique".
            n_results (int): The number of results to retrieve. Defaults to 10.
            history (list): The conversation history. Defaults to [].
        
        Returns:
            list: the answer, the list of document used as context, a suggested follow-up question.
        """
        # 1. Handle "yes" response
        if query.lower().strip() in ["yes", "oui", "sí", "yep", "sure", "ok", "okay", "yes please", "yes pls", "oui svp", "oui stp", "please do"]:
            last_follow_up = None
            if history:
                for msg in reversed(history):
                    if msg.get('role') == 'assistant':
                        content = msg.get('content', '')
                        match = re.search(r'<follow_up>(.*?)</follow_up>', content, re.DOTALL)
                        if match:
                            last_follow_up = match.group(1).strip()
                            break
            
            if last_follow_up:
                self.console.print(f"[cyan]Affirmative response detected. Substituting query with: {last_follow_up}[/cyan]")
                query = last_follow_up

        # 2. Embedding query
        yield {"type": "status", "message": "Embedding query..."}
        try:
            query_embedding = self._get_embedding(text=query)
        except Exception as e:
            self.console.print(f"[red]Error generating query embedding: {e}[/red]")
            yield {"type": "error", "message": f"Error generating query embedding: {e}"}
            return

        # 3. Get results using retrieve
        yield {"type": "status", "message": "Retrieving documents..."}
        self.console.print("********** Query: ", query, style="bold yellow")
        try:
            formatted_results = self.retrieve(query_embedding, topic=topic, n_results=n_results)
        except Exception as e:
            self.console.print(f"[red]Error querying Pinecone: {e}[/red]")
            yield {"type": "error", "message": f"Error querying Pinecone: {e}"}
            return
        
        # 4. Determine system instruction based on topic
        system_instruction = None
        if topic.lower() == "manrique":
            system_instruction = MANRIQUE_PROMPT
        
        # 5. detect language of the query
        detected_language = self.detect_language(query)
        if detected_language:
            system_instruction += "\n<Language for Response> " + detected_language + " </Language for Response>"
        print("********** Query: ", query)
        print("language: ", detected_language)

        # 6. Generate answer
        yield {"type": "status", "message": "Generating multimodal response..."}
        result = self.generate_answer(query, formatted_results, history=history, system_instruction=system_instruction)
        answer = result["answer"]
        follow_up = result["follow_up"]
        
        self.console.print("********** LLM Answer: ", Markdown(answer), style="bold yellow")
        if follow_up:
             self.console.print("********** Suggested Follow-up: ", follow_up, style="bold cyan")
        
        yield {
            "type": "data",
            "answer": answer,
            "results": formatted_results,
            "follow_up": follow_up
        }


if __name__ == "__main__":
    pass
