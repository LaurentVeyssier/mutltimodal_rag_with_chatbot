import os
import sys
from rag_engine import RAGEngine
from dotenv import load_dotenv
load_dotenv()

def verify_gcs_setup():
    print("Verifying GCS Setup...")
    
    # Check Env locally just in case
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    print(f"GCS_BUCKET_NAME in env: {bucket_name}")
    
    try:
        engine = RAGEngine()
        if engine.storage_client:
            print("SUCCESS: GCS Client initialized successfully.")
            print(f"Connected to bucket: {engine.bucket.name}")
        else:
            print("FAILURE: GCS Client not initialized (engine.storage_client is None).")
            
    except Exception as e:
        print(f"FAILURE: Error during RAGEngine initialization: {e}")

if __name__ == "__main__":
    verify_gcs_setup()
