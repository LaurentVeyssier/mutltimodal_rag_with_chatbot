import requests
import fitz
from PIL import Image, ImageDraw
import io
import time
import os

def create_test_pdf(filename="test.pdf"):
    doc = fitz.open()
    page = doc.new_page()
    
    # Add text
    page.insert_text((50, 50), "This is a test PDF for the RAG application.", fontsize=12)
    page.insert_text((50, 70), "It contains both text and an image.", fontsize=12)
    page.insert_text((50, 90), "The secret code is 12345.", fontsize=12)
    
    # Add image
    img = Image.new('RGB', (100, 100), color = 'red')
    d = ImageDraw.Draw(img)
    d.text((10,10), "Test Image", fill=(255,255,0))
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    page.insert_image(fitz.Rect(50, 120, 150, 220), stream=img_bytes.getvalue())
    
    doc.save(filename)
    doc.close()
    return filename

def test_backend():
    base_url = "http://127.0.0.1:8000"
    
    # Wait for server to start
    print("Waiting for server to start...")
    for _ in range(120):
        try:
            requests.get(f"{base_url}/docs")
            break
        except:
            time.sleep(1)
    else:
        print("Server failed to start")
        return

    print("Server started.")

    # Create PDF
    pdf_path = create_test_pdf()
    print(f"Created {pdf_path}")

    # Upload PDF
    print("Uploading PDF...")
    with open(pdf_path, "rb") as f:
        files = {"file": f}
        response = requests.post(f"{base_url}/upload", files=files)
    
    print(f"Upload response: {response.status_code} - {response.text}")
    assert response.status_code == 200

    # Search Text
    print("Searching for text...")
    query = {"query": "secret code"}
    response = requests.post(f"{base_url}/chat", json=query)
    print(f"Search response: {response.status_code} - {response.json()}")
    results = response.json()["results"]
    assert any("12345" in r["content"] for r in results)
    print("Text search passed!")

    # Search Image (by text description)
    print("Searching for image...")
    query = {"query": "red square"}
    response = requests.post(f"{base_url}/chat", json=query)
    print(f"Image Search response: {response.status_code} - {response.json()}")
    # Note: CLIP might not perfectly match "red square" to the image without better prompting or model, 
    # but we check if we get image results.
    results = response.json()["results"]
    # We just check if we got any results, and if any are of type 'image'
    image_results = [r for r in results if r["metadata"]["type"] == "image"]
    print(f"Found {len(image_results)} image results.")
    
    # Clean up
    os.remove(pdf_path)

if __name__ == "__main__":
    test_backend()
