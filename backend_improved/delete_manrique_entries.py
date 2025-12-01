import chromadb
import os

def delete_manrique_entries():
    db_path = "./chroma_db"
    client = chromadb.PersistentClient(path=db_path)
    
    try:
        # Get the collection
        collection = client.get_collection(name="manrique")
        count_before = collection.count()
        print(f"Entries in 'manrique' before deletion: {count_before}")
        
        if count_before > 0:
            # Delete all entries
            # ChromaDB requires a filter or list of IDs. To delete all, we can get all IDs first.
            result = collection.get()
            ids = result['ids']
            
            if ids:
                collection.delete(ids=ids)
                print(f"Successfully deleted {len(ids)} entries.")
            else:
                print("No IDs found to delete.")
        else:
            print("Collection is already empty.")
            
        count_after = collection.count()
        print(f"Entries in 'manrique' after deletion: {count_after}")

    except Exception as e:
        print(f"Error accessing collection 'manrique': {e}")
        # It might not exist if it was never created or named differently
        print("Available collections:", [c.name for c in client.list_collections()])

if __name__ == "__main__":
    delete_manrique_entries()
