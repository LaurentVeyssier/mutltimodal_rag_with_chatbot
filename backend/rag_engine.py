import fitz  # PyMuPDF
import chromadb
# from sentence_transformers import SentenceTransformer
from PIL import Image
import base64
import io
import uuid
import os
import requests
from rich.console import Console
from rich.markdown import Markdown
import google.generativeai as genai
from manrique_excerpts import excerpts_1, excerpts_2
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("JINA_AI_API_TOKEN")


url = "https://api.jina.ai/v1/embeddings"

DEFAULT_PROMPT = "You are a helpful assistant. Answer the user's question based ONLY on the following context."
MANRIQUE_PROMPT = ("You speack as if you are Cesar Manrique. "
"You articulate your responses as Cesar Manrique would when he lived in the 1960-70s after he returned to Lanzarote for NYC. "
f"To help you with Manrique expression and style, here is an excerpt from a conversation with Cesar Manrique: \n\n{excerpts_1 +'\n' + excerpts_2}\n\n"
"Always answer in the same language as the question below (French -> français, English -> english, Spanish -> español)"
"Answer the question based on the context.")



class RAGEngine:
    def __init__(self, db_path="./chroma_db",use_stderr=False):
        self.console = Console(stderr=use_stderr)
        self.client = chromadb.PersistentClient(path=db_path)
        self.collections = {}
        # Initialize default collection
        self._get_collection("manrique")
        # Use CLIP for both text and image embeddings to have a shared vector space
        # self.model = SentenceTransformer('clip-ViT-B-32') # too weak no image in results
        # we use jinaai v4 model for embeddings instead https://jina.ai/embeddings/

        # Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("Warning: GEMINI_API_KEY not found in environment variables.")
        else:
            genai.configure(api_key=api_key)
            self.llm = genai.GenerativeModel('gemini-2.0-flash')

    def _get_collection(self, name: str):
        if name not in self.collections:
            self.collections[name] = self.client.get_or_create_collection(name=name)
        return self.collections[name]

    def list_topics(self):
        return [c.name for c in self.client.list_collections()]

    def ingest_file(self, file_path: str, topic: str = "manrique"):
        collection = self._get_collection(topic)
        doc = fitz.open(file_path)
        text_pages_count = 0
        images_count = 0
        
        for page_num, page in enumerate(doc):
            # 1. Extract Text
            text = page.get_text()
            if text.strip():
                self._add_text_to_db(text, file_path, page_num+1, collection)
                text_pages_count += 1
            
            # 2. Extract Images
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Validate image
                try:
                    image = Image.open(io.BytesIO(image_bytes))
                    if image.mode != "RGB":
                        image = image.convert("RGB")
                    self._add_image_to_db(image, file_path, page_num+1, img_index, collection)
                    images_count += 1
                except Exception as e:
                    print(f"Failed to process image {img_index} on page {page_num+1}: {e}")
        
        self.console.print(f"Ingestion complete: {text_pages_count} text pages and {images_count} images processed.", style="bold green")


    def _get_embedding(self, text: str = None, image: base64 = None):
        if text is None and image is None:
            raise ValueError("At least one of text or image must be provided")
        elif text is not None and image is not None:
            raise ValueError("Only one of text or image can be provided")
        elif text is not None:
            payload = {
                "model": "jina-embeddings-v4",
                "task": "text-matching",
                "input": [
                    {"text": text},
                ]
            }
        elif image is not None:
            payload = {
                "model": "jina-embeddings-v4",
                "task": "text-matching",
                "input": [
                    {"image": image},
                ]
            }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }

        response = requests.post(url, json=payload, headers=headers)
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

    def _add_image_to_db(self, image: Image.Image, file_path: str, page_num: int, img_index: int, collection):
        #embedding = self.model.encode(image).tolist()

        doc_id = str(uuid.uuid4())
        
        # For images, we might not store the raw image in ChromaDB 'documents' field as it expects string.
        # We can store a description or placeholder, and maybe save the image to disk if we want to retrieve it later.
        # For this simple app, we'll just store a placeholder in 'documents' and metadata.
        # Ideally, we should save the image to a static folder and store the path.
        
        # Let's save image to a static folder
        images_dir = "static/images"
        os.makedirs(images_dir, exist_ok=True)
        image_filename = f"{os.path.basename(file_path)}_{page_num}_{img_index}.png"
        image_path = os.path.join(images_dir, image_filename)
        image.save(image_path)

        def encode_image(path):
            with open(path, "rb") as f:
                image_bytes = f.read()
            return base64.b64encode(image_bytes).decode("utf-8")
        img_base64 = encode_image(image_path)

        embedding = self._get_embedding(image=img_base64)

        collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=["[IMAGE]"], # Placeholder
            metadatas=[{
                "type": "image",
                "source": file_path,
                "page": page_num,
                "image_path": image_path
            }]
        )

    def generate_answer(self, query: str, context: list, system_instruction: str = None):
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
                image_path = item['metadata'].get('image_path')
                if image_path and os.path.exists(image_path):
                    try:
                        img = Image.open(image_path)
                        parts.append(f"- [Image on page {item['metadata']['page']}]: ")
                        parts.append(img)
                        parts.append("\n")
                    except Exception as e:
                        print(f"Error loading image {image_path}: {e}")
                        parts.append(f"- [Error loading image on page {item['metadata']['page']}]\n")
                else:
                    parts.append(f"- [Image not found on page {item['metadata']['page']}]\n")
        
        parts.append(f"\nQuestion: {query}\n\nAnswer:")
        
        try:
            response = self.llm.generate_content(parts)
            return response.text
        except Exception as e:
            return f"Error generating answer: {e}"

    def retrieve(self, query: str, topic: str = "manrique", n_results: int = 5):
        collection = self._get_collection(topic)
        query_embedding = self._get_embedding(text=query)

        if topic.lower() == "manrique":
            n_results = 15

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

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

    def search(self, query: str, topic: str = "manrique", n_results: int = 5):
        # Get results using retrieve
        formatted_results = self.retrieve(query, topic, n_results)
        
        # Determine system instruction based on topic
        system_instruction = None
        if topic.lower() == "manrique":
            system_instruction = MANRIQUE_PROMPT
        
        # Generate answer
        answer = self.generate_answer(query, formatted_results, system_instruction=system_instruction)
        self.console.print("********** LLM Answer: ", Markdown(answer), style="bold yellow")
        
        return {
            "answer": answer,
            "results": formatted_results
        }


if __name__ == "__main__":
    pass