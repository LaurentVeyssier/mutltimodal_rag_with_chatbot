from fastmcp import FastMCP
from rag_engine import RAGEngine
import os, json

# Initialize FastMCP server
mcp = FastMCP("RAG Server")

# Initialize RAG Engine
# We initialize it here so it's ready when tools are called
rag_engine = RAGEngine(use_stderr=True)


@mcp.tool()
def search(query: str, topic: str = "manrique") -> str:
    """
    Perform a RAG search on a specific topic and return the answer.
    
    Args:
        query: The question or query to search for.
        topic: The topic collection to search in (default: "manrique").
    """
    result = rag_engine.search(query, topic=topic)
    return result["answer"]


@mcp.tool()
def retrieve(query: str, topic: str = "manrique") -> str:
    """
    Retrieve raw context from the RAG system without generating an answer.
    Useful for agents that want to generate their own answer.
    
    Args:
        query: The question or query to search for.
        topic: The topic collection to search in (default: "manrique").
    """
    results = rag_engine.retrieve(query, topic=topic)
    
    # Return results as JSON string so the client can parse it
    # and handle images if needed.
    return json.dumps(results)

@mcp.tool()
def ingest_file(file_path: str, topic: str = "manrique") -> str:
    """
    Ingest a PDF file into the RAG system.
    
    Args:
        file_path: Absolute path to the PDF file to ingest.
        topic: The topic collection to ingest into (default: "manrique").
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
    
    try:
        rag_engine.ingest_file(file_path, topic=topic)
        return f"Successfully ingested {file_path} into topic '{topic}'"
    except Exception as e:
        return f"Error ingesting file: {str(e)}"

@mcp.tool()
def list_topics() -> list[str]:
    """
    List all available topics/collections in the RAG system.
    """
    return rag_engine.list_topics()

if __name__ == "__main__":
    mcp.run(transport="stdio")
