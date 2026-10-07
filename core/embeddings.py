import streamlit as st
from utils.config import EMBEDDING_MODEL

@st.cache_data(max_entries=16, show_spinner=False)
def encode_texts(texts, model_id=EMBEDDING_MODEL):
    from core.keywords import load_embeddings
    return load_embeddings(model_id).encode(list(texts), normalize_embeddings=True, batch_size=32, show_progress_bar=False)
