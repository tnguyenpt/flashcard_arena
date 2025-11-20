# backend/app.py
import os
import json
import io

from typing import Optional, List

from openai import OpenAI
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import chardet
import pdfplumber

from .services.cards import generate_cards as generate_basic_cards

# Initialize OpenAI client (reads OPENAI_API_KEY from environment)
client = OpenAI()

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
    text_parts: List[str] = []
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page in pdf.pages:
            try:
                text_parts.append(page.extract_text() or "")
            except Exception:
                # Skip pages that fail to extract
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
async def upload(
    file: UploadFile = File(...),
    include_text: bool = False,
):
    fname = (file.filename or "").lower()
    raw = await file.read()

    if fname.endswith(".pdf") or file.content_type == "application/pdf":
        text = extract_text_from_pdf(raw)
    elif fname.endswith(".txt") or file.content_type in (
        "text/plain",
        "application/octet-stream",
    ):
        text = extract_text_from_txt(raw)
    else:
        raise HTTPException(
            status_code=400, detail="Please upload a .pdf or .txt file"
        )

    if not text.strip():
        raise HTTPException(
            status_code=422, detail="No extractable text found in file"
        )

    payload = {
        "filename": file.filename,
        "chars": len(text),
        "preview": text[:1200],  # keep payload small by default
    }
    if include_text:
        payload["text"] = text
    return JSONResponse(payload)


# ---------- FLASHCARD MODELS ----------


class Card(BaseModel):
    q: str
    a: str


class GenerateRequest(BaseModel):
    text: str = Field(..., description="Raw text to turn into flashcards")
    n: int = Field(10, ge=1, le=50, description="Number of cards to generate")
    difficulty: Optional[str] = Field(
        "medium",
        description="Optional difficulty hint (e.g. easy, medium, hard)",
    )
    style: Optional[str] = Field(
        "mixed",
        description="Optional style hint (e.g. definitions, concepts, mixed)",
    )


class GenerateResponse(BaseModel):
    cards: List[Card]
    mode: str = Field(
        "basic", description="Generation mode: 'ai' or 'basic' (fallback)"
    )
    fallback_error: Optional[str] = Field(
        None,
        description="If basic was used as a fallback, this contains the AI error message",
    )


# ---------- AI FLASHCARD GENERATOR ----------


def generate_ai_cards(req: GenerateRequest) -> List[dict]:
    """
    Use OpenAI to generate flashcards in a strict JSON format:
    {
      "cards": [
        {"q": "...", "a": "..."},
        ...
      ]
    }
    """
    system_prompt = """
You are an assistant that generates high-quality flashcards for spaced repetition.

You MUST output a single JSON object with this exact shape:

{
  "cards": [
    {"q": "question 1", "a": "answer 1"},
    {"q": "question 2", "a": "answer 2"}
  ]
}

Rules:
- Use the 'q' field for the question or prompt.
- Use the 'a' field for the correct answer.
- Do NOT include any additional top-level keys.
- Do NOT include explanations, markdown, or commentary.
- Do NOT wrap the JSON in backticks.
"""

    difficulty_hint = req.difficulty or "medium"
    style_hint = req.style or "mixed"

    user_prompt = f"""
Generate {req.n} high-quality flashcards based on the following source text.

Text:
\"\"\"{req.text}\"\"\"

Requirements:
- Difficulty level: {difficulty_hint}
- Style: {style_hint}
- Focus on the most important concepts, definitions, formulas, or facts.
- Make each card atomic and unambiguous.
- Prefer clear, concise phrasing.
"""

    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.4,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ],
    )

    content = completion.choices[0].message.content
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse AI JSON: {e}")

    cards = data.get("cards")
    if not isinstance(cards, list):
        raise ValueError("AI response did not contain a 'cards' list")

    # Normalize to only include q/a and respect n
    normalized: List[dict] = []
    for item in cards:
        if not isinstance(item, dict):
            continue
        q = item.get("q")
        a = item.get("a")
        if isinstance(q, str) and isinstance(a, str):
            normalized.append({"q": q.strip(), "a": a.strip()})
        if len(normalized) >= req.n:
            break

    if not normalized:
        raise ValueError("AI returned no usable flashcards")

    return normalized


# ---------- /cards/generate ENDPOINT WITH FALLBACK ----------


@app.post("/cards/generate", response_model=GenerateResponse)
def cards_generate(payload: GenerateRequest):
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="`text` is required.")

    # 1) If no API key → skip AI and use basic generator
    if not os.getenv("OPENAI_API_KEY"):
        basic_cards = generate_basic_cards(text, n=payload.n)
        if not basic_cards:
            raise HTTPException(
                status_code=422,
                detail="Could not generate cards from the provided text.",
            )
        return GenerateResponse(
            cards=basic_cards,
            mode="basic",
            fallback_error="No OPENAI_API_KEY set",
        )

    # 2) Try AI first
    try:
        ai_cards = generate_ai_cards(payload)
        return GenerateResponse(
            cards=ai_cards,
            mode="ai",
            fallback_error=None,
        )
    except Exception as e:
        # 3) On any AI error → fallback to basic generator
        fallback_error = str(e)

        basic_cards = generate_basic_cards(text, n=payload.n)
        if not basic_cards:
            # If even the basic generator fails, surface both errors
            raise HTTPException(
                status_code=500,
                detail=f"AI failed and fallback generator also failed: {fallback_error}",
            )

        return GenerateResponse(
            cards=basic_cards,
            mode="basic",
            fallback_error=fallback_error,
        )

