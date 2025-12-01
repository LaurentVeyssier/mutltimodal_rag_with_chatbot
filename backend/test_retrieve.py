from rag_engine import RAGEngine
import json

def test_retrieve():
    print("Initializing RAG Engine...")
    engine = RAGEngine()
    
    query = "What did Manrique say about architecture?"
    print(f"\nTesting retrieve with query: '{query}'")
    
    results = engine.retrieve(query)
    
    print(f"\nResults found: {len(results)}")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    test_retrieve()
