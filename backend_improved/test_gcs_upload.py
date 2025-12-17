import os
import io
from PIL import Image
from rag_engine import RAGEngine
import uuid

def test_upload():
    print("Testing GCS Upload...")
    
    # Initialize implementation
    try:
        engine = RAGEngine()
        if not engine.storage_client:
            print("FAILURE: GCS Client not initialized. Check Env vars.")
            return
    except Exception as e:
        print(f"FAILURE: Initializing RAGEngine: {e}")
        return

    # Create a dummy image (red square)
    img = Image.new('RGB', (100, 100), color = 'red')
    
    # Mocking what happens in _add_image_to_db but validating the upload part directly
    try:
        filename = f"test_upload_{uuid.uuid4()}.png"
        blob = engine.bucket.blob(filename)
        
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        print(f"Uploading {filename} to {engine.bucket.name}...")
        blob.upload_from_file(img_byte_arr, content_type='image/png')
        
        print("Upload successful!")
        print(f"Public URL: {blob.public_url}")
        print("Please check the URL in your browser to verify.")
        
    except Exception as e:
        print(f"FAILURE: Uploading image: {e}")

if __name__ == "__main__":
    test_upload()
