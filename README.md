# César Manrique Chatbot 🎨🏝️

A multimodal RAG (Retrieval-Augmented Generation) chatbot dedicated to the life and work of César Manrique. This assistant can answer questions based on ingested PDF documents, providing both text answers and relevant image sources.

## 🏗️ Architecture Overview

The project consists of a **FastAPI backend** and a **Next.js frontend**, heavily integrated with various cloud services to provide a high-performance, multimodal exploration experience.

### Backend (`/backend_improved`)
- **Multimodal RAG**: Processes PDFs to extract text and images.
- **Image Intelligence**: Uses Gemini to generate descriptions for extracted images within their original PDF context. Image descriptions are used to help the LLM "see" and describe extracted images.
- **Hybrid Retrieval**: Stores both text and image metadata in Pinecone for semantic search. Image description are used to compute embeddings of the image for image retrieval. Both image description and the image itself are provided as context to the (multimodal) LLM.
- **Language Detection**: Automatically detects user query language and responds accordingly.

### Frontend (`/frontend`)
- **Modern UI**: Clean, artistic interface built with Next.js and Tailwind CSS.
- **Interactive Chat**: Real-time interaction with the AI persona.
- **Source Transparency**: Accordion view for sources showing the exact page and document (PDF) where information was retrieved whether this is a text chunk or an image.
- **Document Ingestion**: Direct UI for uploading new PDF documents to the knowledge base.

## ☁️ Cloud Services & Integrations

The "Manrique Chatbot" is built for the cloud:

| Service | Purpose |
| :--- | :--- |
| **Google Gemini** | LLM for generating answers and describing images. |
| **Pinecone Cloud** | Vector database for high-speed semantic retrieval. |
| **Google Cloud Storage (GCS)** | Persistent storage for processed images. |
| **Jina AI API** | Advanced embeddings for text and image descriptions. |
| **Langfuse platform** | Observability and tracing for monitoring LLM interactions. |
| **Vercel** | Frontend hosting and deployment. |
| **Render** | Backend API hosting. |

## 📁 Project Structure

```text
cesar_manrique_chatbot/
├── backend_improved/     # FastAPI application & RAG Engine
├── frontend/             # Next.js 15+ application
└── README.md             # This file
```

## 🚀 Quick Start

### 1. Backend Setup
```bash
cd backend_improved
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -r requirements.txt
python main.py
```
*Make sure to configure the `.env` file with your API keys.*

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 📜 License
This project is for educational and artistic preservation purposes.
