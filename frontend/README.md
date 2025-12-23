# Manrique Frontend 🎨

A premium, interactive web interface for exploring the legacy of César Manrique through AI.

## ✨ Features

- **Artistic Design**: A high-impact UI inspired by Manrique's aesthetic, featuring glassmorphism and grayscale contrast.
- **AI Persona Chat**: A conversational window with César's digital twin, powered by a multimodal RAG engine. The chatbot can answer questions about the legacy of César Manrique and provide relevant sources used for AI answers. The responses are enriched with relevant captioned images.
- **Smart Source Viewer**:
  - Automatically identifies and displays sources used for AI answers.
  - Supports both text chunks and images.
  - Displays the source PDF filename and specific page number.
- **Dynamic Suggested Questions**: Offers a set of relevant starting points for exploration. Each answer is completed with a suggested follow-up question to deep dive into the topic.
- **Document Management**: Dedicated upload section to expand the chatbot's knowledge base.

## 🛠️ Tech Stack

- **Framework**: [Next.js 16+](https://nextjs.org/) (App Router).
- **Styling**: [Tailwind CSS 4](https://tailwindcss.com/) with artistic gradients and typography.
- **Components**: [Radix UI](https://www.radix-ui.com/) and [Lucide Icons](https://lucide.dev/).
- **Markdown Rendering**: [React Markdown](https://github.com/remarkjs/react-markdown) with GFM and custom image handling.
- **API Communication**: [Axios](https://axios-http.com/).

## ☁️ Integrations & Deployment

### 1. Backend Connectivity
- The frontend connects to a FastAPI backend hosted on **Render**.
- Environment variable `NEXT_PUBLIC_API_URL` defines the base path for all chat and upload requests.

### 2. Deployment
- Optimized for deployment on **Vercel**.
- Automated builds and preview environments are recommended for development.

## ⚙️ Environment Variables

Create a `frontend/.env` file:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000  # Development backend
# Or your production backend URL (render)
```

## 🚀 Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```
2. Run the development server:
   ```bash
   npm run dev
   ```
3. Open [http://localhost:3000](http://localhost:3000) in your browser (local development) or [https://cesar-manrique-chatbot.vercel.app](https://cesar-manrique-chatbot.vercel.app) (production).
