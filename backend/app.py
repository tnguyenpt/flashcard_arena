# backend/app.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import io, chardet, pdfplumber

app = FastAPI()

# CORS so any future web frontend can call the API
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
                # skip pages that fail extraction
                continue
    return "\n\n".join(text_parts).strip()

def extract_text_from_txt(raw: bytes) -> str:
    # best-effort encoding detection
    det = chardet.detect(raw)
    enc = det.get("encoding") or "utf-8"
    try:
        return raw.decode(enc, errors="ignore")
    except Exception:
        return raw.decode("utf-8", errors="ignore")

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
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

    return JSONResponse({
        "filename": file.filename,
        "chars": len(text),
        "preview": text[:1200],  # keep payload small
    })
