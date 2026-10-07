import re
import spacy
import streamlit as st
from nltk.tokenize import TreebankWordTokenizer

@st.cache_resource
def load_nlp():
    try:
        return spacy.load('en_core_web_sm')
    except OSError:
        nlp = spacy.blank('en')
        nlp.add_pipe('sentencizer')
        return nlp

def preprocess(text):
    text = re.sub(r'\s+', ' ', text.replace('\x00', '')).strip()
    if not text:
        raise ValueError('Add some notes before generating your study kit.')
    if len(text.split()) < 50:
        raise ValueError('Please add at least 50 words so there is enough context to study.')
    if len(text) > 250000:
        raise ValueError('Please use a document under 250,000 characters.')
    doc = load_nlp()(text)
    return {'text': text, 'sentences': [s.text.strip() for s in doc.sents if s.text.strip()],
            'tokens': len(TreebankWordTokenizer().tokenize(text)), 'doc': doc}
