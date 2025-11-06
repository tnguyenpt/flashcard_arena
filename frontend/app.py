# frontend/app.py
import streamlit as st
import requests

API = "http://127.0.0.1:8000"  # change to your deployed URL later

st.set_page_config(page_title="AI Flashcards Arena", page_icon="🃏", layout="wide")

st.title("🃏 AI Flashcards Arena")
st.caption("FastAPI + Streamlit • Upload → Extract → Generate Flashcards")

# =========================
# Sidebar: Backend Health
# =========================
with st.sidebar:
    st.subheader("Backend")
    try:
        r = requests.get(f"{API}/health", timeout=3)
        st.success(f"Health: {r.json().get('status', '?')}")
        st.caption(r.json())
    except Exception as e:
        st.error(f"Backend unreachable: {e}")

st.divider()

# Keep extracted text in session between actions
if "uploaded_text" not in st.session_state:
    st.session_state["uploaded_text"] = ""

# =========================
# 1) Upload → Extract Text
# =========================
st.header("1) Upload Text Source (PDF or TXT)")

uploaded = st.file_uploader("Upload a .pdf or .txt", type=["pdf", "txt"])

colA, colB = st.columns([1, 1])
with colA:
    if uploaded is not None:
        st.write(f"Selected: **{uploaded.name}**")
with colB:
    if st.button("Extract text") and uploaded is not None:
        try:
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type or "application/octet-stream")}
            with st.spinner("Extracting…"):
                # ask backend to include full extracted text in response
                r = requests.post(f"{API}/upload", files=files, params={"include_text": True}, timeout=60)
                r.raise_for_status()
            data = r.json()
            full_text = data.get("text") or data.get("preview") or ""
            st.session_state["uploaded_text"] = full_text
            st.success(f"Extracted {len(full_text)} characters from {data.get('filename', uploaded.name)}")
        except Exception as e:
            st.error(f"Upload failed: {e}")

# Preview extracted text (if any)
if st.session_state["uploaded_text"]:
    with st.expander("Preview extracted text"):
        txt = st.session_state["uploaded_text"]
        st.write(txt[:3000] + ("..." if len(txt) > 3000 else ""))

st.divider()

# =========================
# 2) Generate Flashcards
# =========================
st.header("2) Generate Flashcards")

src = st.radio("Choose source", ["Use uploaded text", "Paste text manually"], horizontal=True)
seed_text = st.session_state["uploaded_text"] if src == "Use uploaded text" else ""
text_input = st.text_area(
    "Text to generate flashcards from:",
    value=seed_text,
    height=220,
    placeholder="Paste text or use uploaded text above…",
)

n_cards = st.slider("Number of cards to generate", min_value=5, max_value=30, value=10)

if st.button("Generate Cards"):
    if not text_input.strip():
        st.warning("Please provide text (upload or paste).")
    else:
        try:
            with st.spinner("Generating cards..."):
                resp = requests.post(
                    f"{API}/cards/generate",
                    json={"text": text_input, "n": n_cards},
                    timeout=60
                )
                resp.raise_for_status()
            cards = resp.json().get("cards", [])
            st.success(f"Generated {len(cards)} cards")
            for i, c in enumerate(cards, 1):
                with st.expander(f"Q{i}: {c['q']}"):
                    st.markdown(f"**Answer:** {c['a']}")
        except Exception as e:
            st.error(f"Generation failed: {e}")

st.divider()
st.caption("Tip: Keep paragraphs reasonably sized for best cloze questions (short fragments may be skipped).")
