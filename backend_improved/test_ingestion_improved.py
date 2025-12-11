from rag_engine import RAGEngine
import os
import shutil

def test_ingestion_improved():
    print("Initializing RAG Engine (Improved)...")
    # Ensure clean state for test
    if os.path.exists("./chroma_db_improved"):
        shutil.rmtree("./chroma_db_improved")
    
    engine = RAGEngine()
    
    # Use a specific PDF known to have images
    pdf_path = "../xdataset_manrique/works.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF not found at {pdf_path}. Searching...")
        found = False
        for root, dirs, files in os.walk(".."):
            for file in files:
                if file == "works.pdf":
                    pdf_path = os.path.join(root, file)
                    found = True
                    break
            if found: break
        
        if not found:
            print("works.pdf not found. Please provide a PDF with images.")
            return

    print(f"Ingesting {pdf_path}...")
    engine.ingest_file(pdf_path)
    
    query = "Show me the sculpture Fobos"
    print(f"\nTesting search with query: '{query}'")
    
    results = engine.search(query)
    
    print("\nSearch Results:")
    for item in results['results']:
        print(f"- Type: {item['type']}")
        print(f"  Content: {item['content'][:100]}...") # Truncate
        print(f"  Metadata: {item['metadata']}")

    print("\nLLM Answer:")
    print(results['answer'])
    
    if "![" in results['answer'] and "](" in results['answer']:
        print("\nSUCCESS: Markdown image syntax found in answer.")
    else:
        print("\nWARNING: No markdown image syntax found in answer.")

if __name__ == "__main__":
    test_ingestion_improved()
