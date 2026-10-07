"""A small, replaceable cosine vector index with persistent source metadata."""
import re
import numpy as np
from core.ingestion import normalize
from database.repositories import stable_id
from utils.config import EMBEDDING_MODEL

def index_segments(document_id, segments):
    from core.preprocessing import load_nlp
    from core.keywords import load_embeddings
    from core.chunking import chunk_sentences
    from core.embeddings import encode_texts
    model = load_embeddings()
    count = lambda s: len(model.tokenizer.encode(s, add_special_tokens=True, verbose=False))
    chunks = []
    for segment in segments:
        sentences = [s.text.strip() for s in load_nlp()(segment['text']).sents]
        for text in chunk_sentences(sentences, count, min(220, model.max_seq_length-8)):
            location = {k:v for k,v in segment.items() if k != 'text'}
            chunks.append({'id':stable_id(document_id,len(chunks),text), 'document_id':document_id,
                           'text':text,'location':location,'model':EMBEDDING_MODEL})
    if chunks:
        vectors = encode_texts(tuple(c['text'] for c in chunks))
        for chunk, vector in zip(chunks,vectors):
            chunk['embedding'] = vector.tolist()
    return chunks

def retrieve(query, chunks, top_k=4, threshold=.3):
    if not query.strip() or not chunks:
        return []
    from core.embeddings import encode_texts
    model = chunks[0]['model']
    vector = encode_texts((query,), model)[0]
    matrix = np.asarray([c['embedding'] for c in chunks], dtype=np.float32)
    similarities = matrix @ vector
    order = np.argsort(-similarities)
    return [{**chunks[int(i)],'similarity':float(similarities[i])} for i in order[:top_k] if similarities[i] >= threshold]

def relevant_sentences(query, passages, count=4):
    from core.preprocessing import load_nlp
    from core.embeddings import encode_texts
    candidates = []
    for passage in passages:
        candidates.extend({'text':s.text.strip(), 'chunk':passage} for s in load_nlp()(passage['text']).sents if len(s.text.split()) >= 4)
    if not candidates:
        return []
    vectors = encode_texts(tuple([query]+[c['text'] for c in candidates]),passages[0]['model'])
    scores = vectors[1:] @ vectors[0]
    ranked = sorted(range(len(candidates)), key=lambda i:float(scores[i]), reverse=True)
    chosen, seen = [], set()
    for i in ranked:
        text = candidates[i]['text']
        if text.lower() not in seen and scores[i] >= .3:
            chosen.append({**candidates[i],'similarity':float(scores[i])}); seen.add(text.lower())
        if len(chosen) == count:
            break
    return chosen
