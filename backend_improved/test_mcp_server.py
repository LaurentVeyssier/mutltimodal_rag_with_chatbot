from mcp_server import mcp, rag_engine, search, list_topics
import sys

def test_mcp_server():
    print("Verifying RAG Engine initialization...")
    try:
        topics = rag_engine.list_topics()
        print(f"RAG Engine Topics: {topics}")
    except Exception as e:
        print(f"Error calling rag_engine directly: {e}")
        return

    print("\nVerifying MCP Tools...")
    try:
        print(f"Type of 'search': {type(search)}")
        print(f"Dir of 'search': {dir(search)}")
        
        # Try to find the underlying function
        if hasattr(search, 'fn'):
            print("Found 'fn' attribute, attempting to call it...")
            result = search.fn("Who is Cesar Manrique?", topic="manrique")
            print(f"Result from search.fn: {result[:100]}...")
        elif hasattr(search, '__wrapped__'):
             print("Found '__wrapped__' attribute, attempting to call it...")
             result = search.__wrapped__("Who is Cesar Manrique?", topic="manrique")
             print(f"Result from search.__wrapped__: {result[:100]}...")
        else:
            print("Could not find callable underlying function on FunctionTool object.")

    except Exception as e:
        print(f"Error inspecting/calling tools: {e}")

if __name__ == "__main__":
    test_mcp_server()
