# backend/services/cards.py
import re
from typing import List, Tuple

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[A-Za-z][A-Za-z'-]{3,}")  # 4+ letters, allow hyphens/apostrophes

def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def _split_sentences(text: str) -> List[str]:
    text = _clean(text)
    if not text:
        return []
    parts = _SENT_SPLIT.split(text)
    return [s.strip() for s in parts if 20 <= len(s.strip()) <= 240]

def _pick_mask_word(sentence: str) -> Tuple[str, int]:
    candidates = [(m.group(0), m.start()) for m in _WORD.finditer(sentence)]
    if not candidates:
        return "", -1
    stop = {"this","that","with","from","which","their","there","these","those","where","after","before","because","while"}
    long_good = [c for c in candidates if len(c[0]) >= 6 and c[0].lower() not in stop]
    if long_good:
        long_good.sort(key=lambda t: (-len(t[0]), t[1]))
        return long_good[0]
    candidates.sort(key=lambda t: (-len(t[0]), t[1]))
    return candidates[0]

def generate_cards(text: str, n: int = 10) -> List[dict]:
    """
    Simple cloze generator:
    - split into sentences
    - blank one word with '_____'
    - q = sentence with blank; a = hidden word
    """
    sentences = _split_sentences(text)
    cards = []
    for s in sentences:
        word, pos = _pick_mask_word(s)
        if not word:
            continue
        q = s[:pos] + "_____" + s[pos + len(word):]
        cards.append({"q": q.strip(), "a": word})
        if len(cards) >= n:
            break
    return cards

