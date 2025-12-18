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


    def generate_image_descriptions(self, images: List[Image.Image], context_pages: List[Image.Image]) -> List[str]:
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


    def ingest_file(self, file_path: str, topic: str = "manrique"):
        # collection = self._get_collection(topic) # Removed for Pinecone
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
            
            # 2. Render Page for Context
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
    def _get_embedding(self, text: str = None, image: base64 = None):
        if text is None and image is None:
            raise ValueError("At least one of text or image must be provided")
        elif text is not None and image is not None:
            raise ValueError("Only one of text or image can be provided")
        elif text is not None:
            payload = {
                "model": EMBEDDING_MODEL,
                "task": "text-matching",
                "input": [
                    {"text": text},
                ]
            }
        elif image is not None:
            payload = {
                "model": EMBEDDING_MODEL,
                "task": "text-matching",
                "input": [
                    {"image": image},
                ]
            }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {EMBEDDING_API_KEY}"
        }

        response = requests.post(EMBEDDING_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    def _add_text_to_db(self, text: str, file_path: str, page_num: int, namespace: str):
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

    def _add_image_to_db(self, image: Image.Image, description: str, file_path: str, page_num: int, img_index: int, namespace: str):
        #embedding = self.model.encode(image).tolist()

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

    #@tracer.chain(name="generate_answer")
    @observe(name="generate_answer")
    def generate_answer(self, query: str, context: list, history: list = [], system_instruction: str = None):
        if not hasattr(self, 'llm'):
            return "LLM not initialized. Please check your API key."
            
        # Start the prompt
        if system_instruction:
            prompt_intro = system_instruction
        else:
            prompt_intro = DEFAULT_PROMPT
            
        parts = [f"{prompt_intro}\n\nContext:\n"]
        
        for item in context:
            if item['type'] == 'text':
                parts.append(f"- {item['content']}\n")
            elif item['type'] == 'image':
                # Load the image from the path (URL or local)
                image_path = item['metadata'].get('image_path', '')
                description = item.get('content', '')
                
                img = None
                try:
                    if image_path.startswith("http"):
                        # Handle URL
                        response = requests.get(image_path, stream=True)
                        response.raise_for_status()
                        img = Image.open(response.raw)
                        parts.append(f"- [Image on page {item['metadata']['page']}]: {description}\n")
                        parts.append(f"  Image URL: {image_path}\n") # Return remote URL
                        parts.append(img)
                        parts.append("\n")
                    elif image_path and os.path.exists(BASE_DIR / image_path):
                        # Handle local path (backwards compatibility)
                        image_url = BASE_DIR / image_path          
                        img = Image.open(image_url)
                        parts.append(f"- [Image on page {item['metadata']['page']}]: {description}\n")
                        parts.append(f"  Image URL: /{image_path}\n")
                        parts.append(img)
                        parts.append("\n")
                    else:
                        parts.append(f"- [Image not found at {image_path} on page {item['metadata']['page']}]\n")
                except Exception as e:
                    print(f"Error loading image {image_path}: {e}")
                    parts.append(f"- [Error loading image on page {item['metadata']['page']}]\n")
        
        if history:
            parts.append("\nConversation History:\n")
            for msg in history:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                parts.append(f"{role.capitalize()}: {content}\n")
        
        parts.append(f"\nQuestion: {query}\n\nAnswer:")
        
        try:
            #response = self.llm.generate_content(parts)
            response = self.llm.models.generate_content(contents=parts, model=self.MODEL_NAME)
            return response.text
        except Exception as e:
            return f"Error generating answer: {e}"

    #@tracer.chain(name="vector_search")
    @observe(name="vector_search")
    def retrieve(self, query: str, topic: str = "manrique", n_results: int = 5):
        query_embedding = self._get_embedding(text=query)

        if topic.lower() == "manrique":
            n_results = 15
        
        try:
            results = self.index.query(
                vector=query_embedding,
                top_k=n_results,
                include_metadata=True,
                namespace=topic
            )
        except Exception as e:
            self.console.print(f"[red]Error querying Pinecone: {e}[/red]")
            return []

        self.console.print("********** Query: ", query, style="bold yellow")
        # self.console.print("********** VectorDB Results: ", results, style="bold yellow")
        
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

    def search(self, query: str, topic: str = "manrique", n_results: int = 5, history: list = []):
        # Get results using retrieve
        formatted_results = self.retrieve(query, topic, n_results)
        
        # Determine system instruction based on topic
        system_instruction = None
        if topic.lower() == "manrique":
            system_instruction = MANRIQUE_PROMPT
        
        # Generate answer
        answer = self.generate_answer(query, formatted_results, history=history, system_instruction=system_instruction)
        self.console.print("********** LLM Answer: ", Markdown(answer), style="bold yellow")
        
        return {
            "answer": answer,
            "results": formatted_results
        }


if __name__ == "__main__":
    pass