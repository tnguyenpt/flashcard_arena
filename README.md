📘 README.md — AI Flashcards Arena
🃏 AI Flashcards Arena
<p align="center"> <img src="/mnt/data/3b6c3eca-92d2-465c-a355-142835609f83.png" width="800"> </p> <p align="center"> <b>Upload → Extract → Generate → Study → Quiz</b><br> Built with <b>FastAPI</b>, <b>OpenAI</b>, <b>Streamlit</b>, and <b>Docker</b>. </p> <p align="center"> <img src="https://img.shields.io/badge/Python-3.11-blue" /> <img src="https://img.shields.io/badge/FastAPI-Backend-009688" /> <img src="https://img.shields.io/badge/Streamlit-Frontend-FF4B4B" /> <img src="https://img.shields.io/badge/OpenAI-API-black" /> <img src="https://img.shields.io/badge/Docker-Ready-0db7ed" /> </p>

AI Flashcards Arena is a smart flashcard generator that transforms PDFs or text into high-quality flashcards using OpenAI. It includes full study/quiz modes, local deck storage, and one-command Docker deployment.
---
Demo
<p align="center">
  <img src="assets/demo.gif" width="900">
</p>
---
🚀 Features
✅ AI Flashcard Generation
- OpenAI-powered flashcards using gpt-4.1-mini
- Controls for difficulty and style
- Clean JSON schema
- Automatic fallback to a deterministic rule-based generator if AI fails
---
📄 File Upload & Text Extraction
- PDF extraction via pdfplumber
- TXT parsing via chardet
- In-app preview of extracted text
---
🎓 Study & Quiz Modes
- Study mode with expandable Q/A
- Quiz mode with:
- Free-response answering
- Intelligent answer matching
- Scoring + progress tracking
- Skip, reveal, next/previous
---
💾 Deck Storage
- Persistent deck saving to /frontend/decks/*.json
- Load any previous deck
- Perfect for long-term study
---
🐳 Full Docker Support
- Backend and frontend run in separate containers
- One command to start everything
- .env support for your OpenAI key
- Ideal for demos & deployment
---
🏗️ Architecture
flashcard_arena/
│
├── backend/               # FastAPI backend
│   ├── app.py             # API routes, AI logic, fallback generator
│   └── services/
│       └── cards.py       # Rule-based flashcard generator
│
├── frontend/              # Streamlit UI
│   ├── app.py             # Upload, extraction, generate, study, quiz
│   └── decks/             # Saved decks
│
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── requirements.txt
└── .env.example
---
🛠️ Local Development Setup (No Docker) (via bash)
1. Create & activate venv 
python3 -m venv venv
source venv/bin/activate       # Mac/Linux
# OR
.\venv\Scripts\activate        # Windows
2. Install dependencies
pip install -r requirements.txt
3. Set your API key
export OPENAI_API_KEY=sk-...
4. Run backend
uvicorn backend.app:app --reload --port 8000
Docs: http://127.0.0.1:8000/docs
5. Run frontend
cd frontend
streamlit run app.py
---
🐳 Running with Docker (recommended)
1. Create .env
OPENAI_API_KEY=sk-your-key-here
2. Start everything
From project root:
docker compose up --build
Services will be available at:
- Frontend (Streamlit): http://localhost:8501
- Backend (FastAPI): http://localhost:8000/docs
---
📡 API Endpoints
GET /health - Check service status.
POST /upload - Extract text from PDF or TXT.
POST /cards/generate
Generate flashcards:
{
  "text": "source text",
  "n": 10,
  "difficulty": "medium",
  "style": "mixed"
}
Response:
{
  "cards": [{ "q": "...", "a": "..." }],
  "mode": "ai",
  "fallback_error": null
}
---
🌐 Deployment
This project is fully ready for deployment on:
Fly.io (recommended)
Railway
Render
HuggingFace Spaces (Streamlit-friendly)
DigitalOcean
Any Docker-compatible cloud provider
Docker Compose makes it simple to run frontend + backend anywhere.
---
🧭 Roadmap
Multiple-choice flashcard generation
Fill-in-the-blank (cloze deletion)
PDF chapter auto-chunking
Local vector search for semantic flashcard lookup
Dark mode enhancements
VS AI mode (Arena Aspect of App)
---
📜 License
MIT — free to use, modify, and share.
---
✨ Author
Built by Tony Nguyen as part of an AI engineering + product portfolio.
Features: AI integration, full-stack architecture, containerization, UI/UX workflow, and ML-assisted content generation.