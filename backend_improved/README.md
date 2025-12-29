# Manrique Backend 🧠

A FastAPI-powered Multimodal RAG Engine that bridges document intelligence with conversational AI.

## 🚀 Core Features

- **Multimodal Ingestion**: Extracts text using `PyMuPDF` and renders page context to help the LLM "see" and describe extracted images.
- **Smart Image Descriptions**: Batch-processes images through Google Gemini, providing the original PDF page as context for high-accuracy description generation.
- **Multimodal retrieval**: Retrieved chunks of text and full-sized images are provided to the LLM as context. when an image-associated vector is retrieved, the original image is provided to the LLM in addition to its pre-processed description. The model can therefore "see" the image and "read" the text for an optimal use of the image as context. This allows the model to perfectly integrate an image as a visual element in its response.
- **Multi-tenant Topics**: Supports namespaces (topics) in Pinecone to separate different sets of documents.
- **Automated Language Handling**: Uses `lingua` to detect query language, ensuring the LLM persona responds in the user's preferred language.
- **Observability**: Fully instrumented with `Langfuse` and `GoogleGenAIInstrumentor` for tracing and quality monitoring.

## ☁️ Cloud Service Integrations

### 1. LLM: Google Gemini
- **Purpose**: Powering the "César Manrique" persona and logical reasoning.
- **Integration**: Used via `google-genai` SDK. Supports fallback models if the primary model is overloaded.

### 2. Vector DB: Pinecone Cloud
- **Purpose**: Semantic search storage. Vectors for image retrieval are calculated on the image description.
- **Integration**: Utilizes serverless/cloud indexes with namespace support for topic segregation.

### 3. Image Storage: Google Cloud Storage (GCS)
- **Purpose**: Storing extracted images with public-read URLs for the frontend.
- **Integration**: Uses `google-cloud-storage` for direct upload during the ingestion pipeline.

### 4. Embeddings: Jina AI API
- **Purpose**: Converting text chunks and image descriptions into high-dimensional vectors.
- **Model**: `jina-embeddings-v4`. Multimodal / multilingual embedding model convinient to handle source documents in multiple languages and produce embeddings for images and text. Can be run locally or using jina AI API.

### 5. Tracing: Langfuse Platform
- **Purpose**: End-to-end tracing of retrieval and generation.
- **Integration**: `@observe` decorators on critical methods.

## 🛠️ API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/upload` | Upload a PDF, extract content, generate embeddings, and store in Pinecone/GCS. |
| `POST` | `/chat` | Send a query and chat history to receive a RAG-powered answer. |
| `GET` | `/topics` | List available namespaces (document groups) in the database. |

## ⚙️ Configuration (.env)

Essential variables required in `backend_improved/.env`:
- `GOOGLE_CLOUD_PROJECT` & `GCS_BUCKET_NAME`
- `GEMINI_API_KEY`, `GEMINI_MODEL_NAME`, `GEMINI_FALLBACK_MODEL_NAME`
- `PINECONE_API_KEY`, `PINECONE_INDEX_HOST`
- `JINA_AI_API_TOKEN`, `JINA_AI_EMBEDDING_URL`
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
- `ALLOW_UPLOAD` (set to `true` or `false`)

This last variable is used to control whether the upload fastapi endpoint is accessible. It is recommended to set it to `false` to prevent unauthorized uploads.
