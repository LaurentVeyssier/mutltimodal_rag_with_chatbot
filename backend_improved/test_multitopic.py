import os
import sys
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Add backend directory to path so we can import rag_engine
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from rag_engine import RAGEngine

def create_test_pdf(filename, content):
    c = canvas.Canvas(filename, pagesize=letter)
    c.drawString(100, 750, content)
    c.save()

def test_multitopic():
    print("Setting up test...")
    pdf_a = "test_topic_A.pdf"
    pdf_b = "test_topic_B.pdf"
    
    create_test_pdf(pdf_a, "Secret information about Project A: The eagle has landed.")
    create_test_pdf(pdf_b, "Secret information about Project B: The bear is sleeping.")
    
    rag = RAGEngine(db_path="./test_chroma_db")
    
    print("Ingesting Topic A...")
    rag.ingest_file(pdf_a, topic="Project_A")
    
    print("Ingesting Topic B...")
    rag.ingest_file(pdf_b, topic="Project_B")
    
    print("\n--- Test 1: Query 'eagle' in Project_A ---")
    res_a = rag.search("eagle", topic="Project_A", n_results=1)
    print(f"Answer: {res_a['answer']}")
    if "eagle" in str(res_a['results']) or "eagle" in res_a['answer'].lower():
        print("PASS: Found eagle in Project_A")
    else:
        print("FAIL: Did not find eagle in Project_A")

    print("\n--- Test 2: Query 'eagle' in Project_B ---")
    res_b = rag.search("eagle", topic="Project_B", n_results=1)
    print(f"Answer: {res_b['answer']}")
    if "eagle" not in str(res_b['results']):
        print("PASS: Did NOT find eagle in Project_B")
    else:
        print("FAIL: Found eagle in Project_B (Should not happen)")

    print("\n--- Test 3: Query 'bear' in Project_B ---")
    res_c = rag.search("bear", topic="Project_B", n_results=1)
    print(f"Answer: {res_c['answer']}")
    if "bear" in str(res_c['results']) or "bear" in res_c['answer'].lower():
        print("PASS: Found bear in Project_B")
    else:
        print("FAIL: Did not find bear in Project_B")

    # Cleanup
    if os.path.exists(pdf_a): os.remove(pdf_a)
    if os.path.exists(pdf_b): os.remove(pdf_b)
    # We leave the DB for inspection if needed, or could delete it.

if __name__ == "__main__":
    test_multitopic()
