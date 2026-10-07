import threading
import torch
import streamlit as st
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from core.chunking import chunk_sentences
from core.preprocessing import load_nlp

from utils.config import SUMMARY_MODEL as MODEL_ID

@st.cache_resource(max_entries=2, show_spinner=False)
def load_summarizer(model_id=MODEL_ID):
    torch.set_num_threads(4)
    import os
    offline = os.getenv('RECALLAI_OFFLINE', '0') == '1'
    # A complete cache should not wait for remote metadata on every new process.
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_id, local_files_only=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_id, local_files_only=True)
    except OSError:
        if offline:
            raise
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_id)
    return tokenizer, model.eval(), threading.RLock()

def generate_summary(text, length='Medium', chunk_size=400):
    tokenizer, model, lock = load_summarizer()
    count = lambda s: len(tokenizer.encode(s, add_special_tokens=True, verbose=False))
    sentences = [s.text for s in load_nlp()(text).sents]
    chunks = chunk_sentences(sentences, count, chunk_size)
    budget = {'Short': 64, 'Medium': 128, 'Detailed': 192}[length]
    def summarize(part):
        inputs = tokenizer('summarize: ' + part, return_tensors='pt')
        with lock, torch.inference_mode():
            output = model.generate(**inputs, max_new_tokens=budget, min_new_tokens=min(24, max(8, count(part)//5)), num_beams=2, no_repeat_ngram_size=3)
        summary = tokenizer.decode(output[0], skip_special_tokens=True).strip()
        if not summary:
            raise ValueError('The model returned an empty summary. Try clearer notes or a different chunk size.')
        return summary
    summaries = [summarize(c) for c in chunks]
    # Each summary is retained; no final pass silently discards later chunks.
    return '\n\n'.join(summaries), len(chunks)
