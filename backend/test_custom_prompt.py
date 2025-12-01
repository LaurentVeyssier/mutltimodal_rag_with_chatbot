import os
import sys
from unittest.mock import MagicMock

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from rag_engine import RAGEngine, DEFAULT_PROMPT, MANRIQUE_PROMPT

def test_custom_prompt():
    print("Testing custom prompt logic...")
    
    # Mock the LLM to avoid actual API calls and just check the prompt passed to it
    rag = RAGEngine(db_path="./test_chroma_db_prompt")
    rag.llm = MagicMock()
    rag.llm.generate_content.return_value.text = "Mock Answer"
    
    # Mock collection query to return empty results so we just test prompt construction
    rag.collection = MagicMock() # This might be tricky with the new collections dict, let's mock _get_collection
    rag._get_collection = MagicMock()
    mock_collection = MagicMock()
    mock_collection.query.return_value = {"ids": [], "distances": [], "metadatas": [], "documents": []}
    rag._get_collection.return_value = mock_collection
    
    # Mock embedding to avoid Jina API call
    rag._get_embedding = MagicMock(return_value=[0.1]*768)

    print("\n--- Test 1: Default Topic ---")
    rag.search("hello", topic="general")
    
    # Check what was passed to generate_content
    call_args = rag.llm.generate_content.call_args
    prompt_parts = call_args[0][0]
    prompt_str = "".join([str(p) for p in prompt_parts])
    
    if DEFAULT_PROMPT in prompt_str:
        print("PASS: Default topic used DEFAULT_PROMPT")
    else:
        print(f"FAIL: Default topic prompt mismatch. Got: {prompt_str[:100]}...")

    print("\n--- Test 2: Manrique Topic ---")
    rag.search("hello", topic="manrique")
    
    call_args = rag.llm.generate_content.call_args
    prompt_parts = call_args[0][0]
    prompt_str = "".join([str(p) for p in prompt_parts])
    
    if MANRIQUE_PROMPT in prompt_str:
        print("PASS: Manrique topic used MANRIQUE_PROMPT")
    else:
        print(f"FAIL: Manrique topic prompt mismatch. Got: {prompt_str[:100]}...")

if __name__ == "__main__":
    test_custom_prompt()
