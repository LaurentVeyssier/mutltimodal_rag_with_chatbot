from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from fastapi import Form
import shutil
import os
from rag_engine import RAGEngine

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
os.makedirs("static/images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize RAG Engine
rag_engine = RAGEngine()

class QueryRequest(BaseModel):
    query: str
    topic: Optional[str] = "manrique"

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
async def chat(request: QueryRequest):
    try:
        response = rag_engine.search(request.query, topic=request.topic)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/topics")
async def get_topics():
    try:
        topics = rag_engine.list_topics()
        return {"topics": topics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
