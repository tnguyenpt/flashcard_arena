# 🃏 AI Flashcards Arena

Upload → Extract → Generate → Study → Quiz.

Built with **FastAPI**, **OpenAI**, **Streamlit**, and **Docker**.

## Product Lens (PM framing)

**Problem:** study material is often dense and passive; learners need fast active recall assets.

**Who it's for:** students and professionals who want to convert notes/PDFs into quiz-ready flashcards quickly.

**Job to be done:** *"Turn my source material into useful cards I can study immediately."*

**MVP Success Criteria:**
- Upload text/PDF and extract readable content
- Generate flashcards quickly with adjustable style/difficulty
- Study and quiz in one flow
- Keep deck history locally for reuse

## Features

- AI flashcard generation (`gpt-4.1-mini`)
- Rule-based fallback generator if AI fails or no API key
- PDF/TXT ingestion and text extraction
- Study mode + quiz mode (fuzzy answer checking)
- Local deck save/load (`frontend/decks/*.json`)
- Dockerized full stack

## Architecture

```text
flashcard_arena/
├── backend/               # FastAPI backend
│   ├── app.py             # API + AI generation + fallback
│   └── services/cards.py  # Rule-based generator
├── frontend/              # Streamlit app
│   ├── app.py
│   └── decks/             # Saved deck files
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
└── requirements.txt
```

## Local setup

```bash
cd /home/clawed/projects/flashcard_arena
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
```

Run backend:

```bash
uvicorn backend.app:app --reload --port 8000
```

Run frontend:

```bash
streamlit run frontend/app.py
```

- Frontend: http://127.0.0.1:8501
- Backend docs: http://127.0.0.1:8000/docs

## Docker setup

Create `.env` in project root:

```env
OPENAI_API_KEY=sk-your-key-here
```

Then:

```bash
docker compose up --build
```

## Key API endpoints

- `GET /health`
- `POST /upload`
- `POST /cards/generate`

`/cards/generate` returns:
- `mode: "ai"` when AI succeeds
- `mode: "basic"` when fallback path is used

## Tradeoffs

- Streamlit for speed over custom frontend complexity
- FastAPI for explicit API boundaries and easier scaling later
- Fallback generator to preserve UX even when LLM path is unavailable

## Suggested screenshots (portfolio)

Add these files under `docs/screenshots/`:

- `upload-and-extract.png`
- `generated-cards-view.png`
- `quiz-mode.png`
- `deck-save-load.png`

When ready, they can be embedded directly in this README.

## Next iteration (portfolio roadmap)

- Add backend endpoint tests with mocked AI
- Add upload size/text length guardrails
- Add richer quiz modes (MCQ/cloze)
- Add cloud persistence option beyond local deck files
