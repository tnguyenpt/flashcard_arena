# frontend/app.py
import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import re
from difflib import SequenceMatcher

import streamlit as st
import requests

# -------------------------------
# Config
# -------------------------------
# Use env var for deployment / Docker; fall back to local dev
API = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="AI Flashcards Arena", page_icon="🃏", layout="wide")
st.markdown("<style>:root { --primary-color: white; }</style>", unsafe_allow_html=True)

# -------------------------------
# Deck persistence helpers (file-based)
# -------------------------------
BASE_DIR = Path(__file__).parent
DECKS_DIR = BASE_DIR / "decks"
DECKS_DIR.mkdir(parents=True, exist_ok=True)

def list_deck_files():
    """Return list of deck filenames (newest → oldest)."""
    decks = sorted(
        [p for p in DECKS_DIR.glob("*.json")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return decks

def save_deck_to_file(cards: List[Dict[str, str]], deck_name: Optional[str] = None) -> Path:
    """
    Save current cards to a JSON file.
    cards should be JSON-serializable (e.g. list[dict] with 'q' and 'a').
    """
    if not cards:
        raise ValueError("No cards to save")

    if not deck_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        deck_name = f"deck_{timestamp}.json"
    else:
        deck_name = deck_name.strip()
        if not deck_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            deck_name = f"deck_{timestamp}.json"
        elif not deck_name.endswith(".json"):
            deck_name += ".json"

    path = DECKS_DIR / deck_name
    with path.open("w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
    return path

def load_deck_from_file(path: Path) -> List[Dict[str, str]]:
    """Load a deck (list of cards) from a JSON file."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

# -------------------------------
# Helpers for answer checking
# -------------------------------
def _normalize(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

def is_correct(user: str, gold: str) -> bool:
    u, g = _normalize(user), _normalize(gold)
    if not u or not g:
        return False
    if u == g:
        return True
    # allow small typos for longer answers
    return len(g) >= 5 and SequenceMatcher(None, u, g).ratio() >= 0.87

# -------------------------------
# Session state
# -------------------------------
def ensure_state():
    ss = st.session_state
    ss.setdefault("uploaded_text", "")
    ss.setdefault("cards", [])           # deck: List[{"q","a"}]
    ss.setdefault("mode", "study")       # "study" | "quiz"
    # quiz state
    ss.setdefault("quiz_idx", 0)         # current index
    ss.setdefault("quiz_reveal", False)  # only used when revealing
    ss.setdefault("quiz_correct", 0)
    ss.setdefault("quiz_seen", 0)
    ss.setdefault("quiz_history", [])    # [{i, result, user?}]
    # input handling (widget-owned value + clear flag)
    ss.setdefault("quiz_answer", "")     # value owned by text_input(key="quiz_answer")
    ss.setdefault("quiz_feedback", "")   # "", "correct", "incorrect"
    ss.setdefault("quiz_last_idx", None) # track card changes
    ss.setdefault("quiz_clear", False)   # flag: clear input BEFORE rendering widget

ensure_state()

def reset_quiz():
    ss = st.session_state
    ss["quiz_idx"] = 0
    ss["quiz_reveal"] = False
    ss["quiz_correct"] = 0
    ss["quiz_seen"] = 0
    ss["quiz_history"] = []
    ss["quiz_answer"] = ""
    ss["quiz_feedback"] = ""
    ss["quiz_last_idx"] = None
    ss["quiz_clear"] = False

def load_deck_into_session(cards: List[Dict[str, str]]):
    st.session_state["cards"] = cards or []
    reset_quiz()

# -------------------------------
# Title + Sidebar
# -------------------------------
st.title("🃏 AI Flashcards Arena")
st.caption("FastAPI + Streamlit • Upload → Extract → Generate → Quiz")

with st.sidebar:
    st.subheader("Backend")
    try:
        r = requests.get(f"{API}/health", timeout=3)
        st.success(f"Health: {r.json().get('status', '?')}")
        st.caption(r.json())
    except Exception as e:
        st.error(f"Backend unreachable: {e}")

    st.divider()
    st.subheader("💾 Decks")

    # Save current deck
    if st.session_state.get("cards"):
        st.markdown("**Save current deck**")
        default_name = datetime.now().strftime("deck_%Y%m%d_%H%M")
        deck_name_input = st.text_input(
            "Deck name (optional)",
            value=default_name,
            key="deck_name_input",
        )
        if st.button("Save deck"):
            try:
                path = save_deck_to_file(st.session_state["cards"], deck_name_input)
                st.success(f"Saved: {path.name}")
            except Exception as e:
                st.error(f"Failed to save deck: {e}")
    else:
        st.info("No cards to save yet. Generate a deck first.")

    st.markdown("---")
    st.markdown("**Load existing deck**")

    deck_files = list_deck_files()
    if deck_files:
        deck_labels = [p.name for p in deck_files]
        selected_label = st.selectbox(
            "Choose a deck",
            options=deck_labels,
            key="deck_select",
        )
        if st.button("Load selected deck"):
            try:
                idx = deck_labels.index(selected_label)
                path = deck_files[idx]
                loaded_cards = load_deck_from_file(path)
                load_deck_into_session(loaded_cards)
                st.success(f"Loaded: {path.name}")
            except Exception as e:
                st.error(f"Failed to load deck: {e}")
    else:
        st.caption("No saved decks yet.")

# -------------------------------
# 1) Upload → Extract Text
# -------------------------------
st.header("1) Upload Text Source (PDF or TXT)")
uploaded = st.file_uploader("Upload a .pdf or .txt", type=["pdf", "txt"])

cols = st.columns([1, 1, 2])
with cols[0]:
    if uploaded is not None:
        st.write(f"Selected: **{uploaded.name}**")
with cols[1]:
    if st.button("Extract text") and uploaded is not None:
        try:
            files = {
                "file": (
                    uploaded.name,
                    uploaded.getvalue(),
                    uploaded.type or "application/octet-stream",
                )
            }
            with st.spinner("Extracting…"):
                r = requests.post(
                    f"{API}/upload",
                    files=files,
                    params={"include_text": True},
                    timeout=60,
                )
                r.raise_for_status()
            data = r.json()
            full_text = data.get("text") or data.get("preview") or ""
            st.session_state["uploaded_text"] = full_text
            st.success(
                f"Extracted {len(full_text)} characters from "
                f"{data.get('filename', uploaded.name)}"
            )
        except Exception as e:
            st.error(f"Upload failed: {e}")

if st.session_state["uploaded_text"]:
    with st.expander("Preview extracted text"):
        txt = st.session_state["uploaded_text"]
        st.write(txt[:3000] + ("..." if len(txt) > 3000 else ""))

st.divider()

# -------------------------------
# 2) Generate Flashcards
# -------------------------------
st.header("2) Generate Flashcards")

src = st.radio("Choose source", ["Use uploaded text", "Paste text manually"], horizontal=True)
seed_text = st.session_state["uploaded_text"] if src == "Use uploaded text" else ""
text_input = st.text_area(
    "Text to generate flashcards from:",
    value=seed_text,
    height=220,
    placeholder="Paste text or use uploaded text above…",
)

cols2 = st.columns([1, 1, 1, 2])
with cols2[0]:
    n_cards = st.slider("Number of cards", 5, 30, 10)
with cols2[1]:
    shuffle_opt = st.checkbox("Shuffle (simple client-side)", value=False)
with cols2[2]:
    if st.button("Generate Cards"):
        if not text_input.strip():
            st.warning("Please provide text (upload or paste).")
        else:
            try:
                with st.spinner("Generating cards..."):
                    resp = requests.post(
                        f"{API}/cards/generate",
                        json={"text": text_input, "n": n_cards},
                        timeout=60,
                    )
                    resp.raise_for_status()
                cards = resp.json().get("cards", [])
                if shuffle_opt:
                    cards = cards[::-1]  # quick client-side shuffle
                load_deck_into_session(cards)
                st.success(f"Generated {len(cards)} cards")
            except Exception as e:
                st.error(f"Generation failed: {e}")
with cols2[3]:
    st.selectbox(
        "Mode",
        options=["study", "quiz"],
        index=0 if st.session_state["mode"] == "study" else 1,
        key="mode",
    )

st.divider()

# -------------------------------
# 3) Study Mode (expanders)
# -------------------------------
def render_study_mode():
    cards = st.session_state["cards"]
    if not cards:
        st.info("No cards to study yet. Generate a deck above or load one from the sidebar.")
        return
    st.subheader("Study Mode")
    for i, c in enumerate(cards, 1):
        with st.expander(f"Q{i}: {c['q']}"):
            st.markdown(f"**Answer:** {c['a']}")

# -------------------------------
# 4) Quiz Mode (type your answer)
# -------------------------------
def render_quiz_mode():
    ss = st.session_state

    cards = ss["cards"]
    if not cards:
        st.info("No cards to quiz. Generate a deck above or load one from the sidebar.")
        return

    st.subheader("Quiz Mode (type your answer)")
    total = len(cards)
    idx = ss["quiz_idx"]
    seen = ss["quiz_seen"]
    correct = ss["quiz_correct"]

    # If navigated to a NEW card: clear via flag (applied before widget)
    if ss["quiz_last_idx"] != idx:
        ss["quiz_reveal"] = False
        ss["quiz_feedback"] = ""
        ss["quiz_clear"] = True
        ss["quiz_last_idx"] = idx

    st.write(f"Progress: {seen}/{total} • Score: {correct} correct")
    st.progress(0 if total == 0 else min(1.0, seen / total))

    card = cards[idx]
    st.markdown(f"**Q:** {card['q']}")

    # Clear the input BEFORE creating the widget this run
    if ss["quiz_clear"]:
        ss["quiz_answer"] = ""
        ss["quiz_clear"] = False

    # ---- Input + Check (ENTER submits) ----
    with st.form("quiz_form", clear_on_submit=False):
        st.text_input(
            "Your answer",
            key="quiz_answer",                 # widget owns its own value
            placeholder="Type your answer here…",
        )
        submitted = st.form_submit_button("Check")

    if submitted:
        user = ss.get("quiz_answer", "")
        if user.strip():
            if is_correct(user, card["a"]):
                ss["quiz_feedback"] = "correct"
                ss["quiz_correct"] += 1
                ss["quiz_seen"] += 1
                ss["quiz_history"].append({"i": idx, "result": "correct", "user": user})
                # advance and clear on next render
                ss["quiz_idx"] = (idx + 1) % total
                ss["quiz_clear"] = True
                ss["quiz_reveal"] = False
                st.rerun()
            else:
                ss["quiz_feedback"] = "incorrect"
                ss["quiz_history"].append({"i": idx, "result": "attempt", "user": user})
        else:
            st.warning("Please type an answer before checking.")

    # Feedback banner
    if ss["quiz_feedback"] == "incorrect":
        st.error("Not quite. Try again or reveal the answer.")
    elif ss["quiz_feedback"] == "correct":
        st.success("Correct!")

    # ---- Controls ----
    c1, c2, c3, c4, c5 = st.columns(5)

    def move_prev():
        ss["quiz_idx"] = (ss["quiz_idx"] - 1) % total
        ss["quiz_reveal"] = False
        ss["quiz_feedback"] = ""
        ss["quiz_clear"] = True
        st.rerun()

    def reveal():
        ss["quiz_feedback"] = ""
        ss["quiz_reveal"] = True

    def skip():
        ss["quiz_seen"] += 1
        ss["quiz_history"].append({"i": idx, "result": "skip"})
        ss["quiz_idx"] = (idx + 1) % total
        ss["quiz_reveal"] = False
        ss["quiz_feedback"] = ""
        ss["quiz_clear"] = True
        st.rerun()

    def move_next():
        ss["quiz_idx"] = (ss["quiz_idx"] + 1) % total
        ss["quiz_reveal"] = False
        ss["quiz_feedback"] = ""
        ss["quiz_clear"] = True
        st.rerun()

    with c1:
        st.button("◀ Prev", on_click=move_prev)
    with c2:
        st.button("Skip", on_click=skip)
    with c3:
        st.button("Show Answer", on_click=reveal)
    with c4:
        st.button("Next ▶", on_click=move_next)
    with c5:
        if st.button("Reset Deck"):
            reset_quiz()
            st.rerun()

    # Only show the answer when explicitly revealed
    if ss.get("quiz_reveal"):
        st.info(f"**Answer:** {card['a']}")

# -------------------------------
# Render selected mode
# -------------------------------
if st.session_state["mode"] == "study":
    render_study_mode()
else:
    render_quiz_mode()

st.divider()
st.caption("Tip: Use Study Mode to review, then Quiz Mode to practice recall with scoring. You can save/load decks from the sidebar.")
