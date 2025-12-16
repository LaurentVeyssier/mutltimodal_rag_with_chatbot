from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from fastapi import Form
import shutil
import os
import logfire
from langfuse import observe, get_client
from rag_engine import RAGEngine
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# OBSERVABILITY
# --------------- LOGFIRE ------------------------
# logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))
# logfire.instrument_fastapi(app)

# --------------- PHOENIX ------------------------
# from observability import tracer_provider_phoenix
# tracer = tracer_provider_phoenix.get_tracer(__name__)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
# Ensure the directory exists relative to where we run the script
# If running from project root, this should be 'backend_improved/static/images'
# But if running from backend_improved, it is 'static/images'
# We will assume running from backend_improved for simplicity in testing, or adjust based on CWD.
# Let's make it robust.
# Path to directory containing current file being run
BASE_DIR = Path(__file__).resolve().parent
os.makedirs(BASE_DIR / "static" / "images", exist_ok=True) 
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Initialize RAG Engine
rag_engine = RAGEngine()

class QueryRequest(BaseModel):
    query: str
    topic: Optional[str] = "manrique"
    history: Optional[List[dict]] = []

class QueryResponse(BaseModel):
    answer: str
    results: List[dict]

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), topic: str = Form("manrique")):
    try:
        file_location = f"temp_{file.filename}"
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        
        # Process the file
        rag_engine.ingest_file(file_location, topic=topic)
        
        # Clean up
        os.remove(file_location)
        
        return {"message": f"Successfully processed {file.filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=QueryResponse)
#@tracer.chain(name="chat")
@observe(name="chat")
async def chat(request: QueryRequest):
    try:
        response = rag_engine.search(request.query, topic=request.topic, history=request.history)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/topics")
#@tracer.chain(name="get_topics")
@observe(name="get_topics")
async def get_topics():
    try:
        topics = rag_engine.list_topics()
        return {"topics": topics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
