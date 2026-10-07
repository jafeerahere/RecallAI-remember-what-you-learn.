import streamlit as st
import re
from sentence_transformers import SentenceTransformer
from keybert import KeyBERT

from utils.config import EMBEDDING_MODEL

@st.cache_resource(max_entries=2, show_spinner=False)
def load_embeddings(model_id=EMBEDDING_MODEL):
    import os
    import torch
    torch.set_num_threads(4)
    try:
        return SentenceTransformer(model_id, device='cpu', local_files_only=True)
    except OSError:
        if os.getenv('RECALLAI_OFFLINE','0') == '1':
            raise
        return SentenceTransformer(model_id, device='cpu')

@st.cache_resource(max_entries=2, show_spinner=False)
def load_keybert():
    return KeyBERT(model=load_embeddings())

def extract_keywords(text, top_n=10):
    # Average sentence embeddings to represent the whole document without
    # silently truncating it to MiniLM's first input window.
    from core.preprocessing import load_nlp
    from sklearn.feature_extraction.text import CountVectorizer
    doc = load_nlp()(text)
    sentences = [s.text for s in doc.sents]
    from core.embeddings import encode_texts
    vectors = encode_texts(tuple(sentences))
    document_embedding = vectors.mean(axis=0, keepdims=True)
    candidates = set()
    if doc.has_annotation('DEP'):
        for chunk in doc.noun_chunks:
            phrase = re.sub(r'^(?:a|an|the|this|that|these|those|its|their)\s+', '', chunk.text.lower()).strip()
            if chunk.root.pos_ in ('NOUN', 'PROPN') and 1 <= len(phrase.split()) <= 3 and len(phrase) >= 3:
                candidates.add(phrase)
    vectorizer = CountVectorizer(ngram_range=(1, 3), stop_words=None,
                                vocabulary=sorted(candidates)[:2000]) if candidates else CountVectorizer(
                                    ngram_range=(1, 3), stop_words='english', max_features=2000)
    return [(p, float(s)) for p, s in load_keybert().extract_keywords(
        text, doc_embeddings=document_embedding,
        vectorizer=vectorizer,
        top_n=top_n, use_mmr=True, diversity=.3)]
