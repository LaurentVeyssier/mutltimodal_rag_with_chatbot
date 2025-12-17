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
import chromadb

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


# Path to directory containing current file being run
BASE_DIR = Path(__file__).resolve().parent

class RAGEngine:
    def __init__(self, db_path= BASE_DIR / "chroma_db_improved", use_stderr=False):
        self.console = Console(stderr=use_stderr)
        self.client = chromadb.PersistentClient(path=db_path)
        self.collections = {}
        # Initialize default collection
        self._get_collection("manrique")
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


    def _get_collection(self, name: str):
        if name not in self.collections:
            self.collections[name] = self.client.get_or_create_collection(name=name)
        return self.collections[name]

    def list_topics(self):
        return [c.name for c in self.client.list_collections()]

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
        collection = self._get_collection(topic)
        doc = fitz.open(file_path)
        text_pages_count = 0
        
        extracted_images_info = [] # List of tuples: (image_obj, page_num, img_index)
        pdf_pages = [] # List of page images for context

        self.console.print("Extracting content and rendering pages...", style="bold blue")

        for page_num, page in enumerate(doc):
            # 1. Extract Text
            text = page.get_text()
            if text.strip():
                self._add_text_to_db(text, file_path, page_num+1, collection)
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
                self._add_image_to_db(image, description, file_path, page_num, img_index, collection)
        
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

    def _add_text_to_db(self, text: str, file_path: str, page_num: int, collection):
        #embedding = self.model.encode(text).tolist()
        embedding = self._get_embedding(text=text)
        doc_id = str(uuid.uuid4())
        collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{
                "type": "text",
                "source": file_path,
                "page": page_num
            }]
        )

    def _add_image_to_db(self, image: Image.Image, description: str, file_path: str, page_num: int, img_index: int, collection):
        #embedding = self.model.encode(image).tolist()

        doc_id = str(uuid.uuid4())
        
        # Let's save image to a static folder
        images_dir = "static/images"
        os.makedirs(images_dir, exist_ok=True)
        image_filename = f"{os.path.basename(file_path)}_{page_num}_{img_index}.png"
        image_path = os.path.join(images_dir, image_filename)
        image.save(image_path)

        # Use description for embedding
        embedding = self._get_embedding(text=description)

        collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[description], # Store description instead of placeholder
            metadatas=[{
                "type": "image",
                "source": file_path,
                "page": page_num,
                "image_path": image_path
            }]
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
                # Load the image from the path
                image_path = item['metadata'].get('image_path').replace("\\", "/")
                description = item.get('content', '')
                if image_path and os.path.exists(BASE_DIR / image_path):
                    try:
                        # Convert local path to relative URL for the LLM to use
                        # Assuming image_path is like "static/images/file.png"
                        # We want to return path like "/static/images/file.png"                   
                        image_url = BASE_DIR / image_path          
                        img = Image.open(image_url)
                        parts.append(f"- [Image on page {item['metadata']['page']}]: {description}\n")
                        parts.append(f"  Image URL: /{image_path}\n")
                        parts.append(img)
                        parts.append("\n")
                    except Exception as e:
                        print(f"Error loading image {image_path}: {e}")
                        parts.append(f"- [Error loading image on page {item['metadata']['page']}]\n")
                else:
                    parts.append(f"- [Image not found on page {item['metadata']['page']}]\n")
        
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
        collection = self._get_collection(topic)
        query_embedding = self._get_embedding(text=query)

        if topic.lower() == "manrique":
            n_results = 15

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        self.console.print("********** Query: ", query, style="bold yellow")
        self.console.print("********** VectorDB Results: ", results, style="bold yellow")
        
        # Format results
        formatted_results = []
        if results["ids"]:
            for i in range(len(results["ids"][0])):
                item = {
                    "id": results["ids"][0][i],
                    "score": results["distances"][0][i] if results["distances"] else None,
                    "type": results["metadatas"][0][i].get("type"),
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i]
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