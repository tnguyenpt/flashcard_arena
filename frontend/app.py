# frontend/app.py
import streamlit as st
import requests

API = "http://127.0.0.1:8000"  # change to your deployed URL later

st.set_page_config(page_title="AI Flashcards Arena", page_icon="🃏")

st.title("🃏 AI Flashcards Arena")
st.caption("Frontend → Backend health check")

col1, col2 = st.columns(2)
with col1:
    if st.button("Ping backend"):
        try:
            r = requests.get(f"{API}/health", timeout=5)
            r.raise_for_status()
            st.success(r.json())
        except Exception as e:
            st.error(f"Request failed: {e}")

with col2:
    st.code(f"GET {API}/health", language="bash")

st.divider()
st.write("If this works, we’re ready to build uploads & flashcards 🚀")

# --- Upload & Extract ---
import streamlit as st
import requests

API = "http://127.0.0.1:8000"

st.subheader("Upload → Extract text")
uploaded = st.file_uploader("Upload a .pdf or .txt", type=["pdf", "txt"])

if uploaded is not None:
    colA, colB = st.columns([1,1])
    with colA:
        st.write(f"Selected: **{uploaded.name}**")
    with colB:
        if st.button("Extract text"):
            try:
                files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type or "application/octet-stream")}
                with st.spinner("Extracting…"):
                    r = requests.post(f"{API}/upload", files=files, timeout=60)
                    r.raise_for_status()
                data = r.json()
                st.success(f"Extracted {data['chars']} characters from {data['filename']}")
                st.text_area("Preview (first ~1,200 chars)", value=data["preview"], height=300)
            except Exception as e:
                st.error(f"Upload failed: {e}")
