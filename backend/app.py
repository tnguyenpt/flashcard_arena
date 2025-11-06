# backend/app.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field              
from typing import List                            
import io, chardet, pdfplumber

from .services.cards import generate_cards         

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-flashcards-arena"}

def extract_text_from_pdf(raw: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page in pdf.pages:
            try:
                text_parts.append(page.extract_text() or "")
            except Exception:
                continue
    return "\n\n".join(text_parts).strip()

def extract_text_from_txt(raw: bytes) -> str:
    det = chardet.detect(raw)
    enc = det.get("encoding") or "utf-8"
    try:
        return raw.decode(enc, errors="ignore")
    except Exception:
        return raw.decode("utf-8", errors="ignore")

# NOTE: add include_text flag so clients can ask for the full text when needed
@app.post("/upload")
async def upload(file: UploadFile = File(...), include_text: bool = False):  # NEW: include_text
    fname = (file.filename or "").lower()
    raw = await file.read()

    if fname.endswith(".pdf") or file.content_type == "application/pdf":
        text = extract_text_from_pdf(raw)
    elif fname.endswith(".txt") or file.content_type in ("text/plain", "application/octet-stream"):
        text = extract_text_from_txt(raw)
    else:
        raise HTTPException(status_code=400, detail="Please upload a .pdf or .txt file")

    if not text.strip():
        raise HTTPException(status_code=422, detail="No extractable text found in file")

    payload = {
        "filename": file.filename,
        "chars": len(text),
        "preview": text[:1200],  # keep payload small by default
    }
    if include_text:                          # NEW: return full text on demand
        payload["text"] = text
    return JSONResponse(payload)

# ---------- NEW: /cards/generate ----------
class Card(BaseModel):
    q: str
    a: str

class GenerateRequest(BaseModel):
    text: str = Field(..., description="Raw text to turn into flashcards")
    n: int = Field(10, ge=1, le=50, description="Number of cards to generate")

class GenerateResponse(BaseModel):
    cards: List[Card]

@app.post("/cards/generate", response_model=GenerateResponse)
def cards_generate(payload: GenerateRequest):
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="`text` is required.")
    cards = generate_cards(text, n=payload.n)
    if not cards:
        raise HTTPException(status_code=422, detail="Could not generate cards from the provided text.")
    return {"cards": cards}
