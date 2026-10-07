def chunk_sentences(sentences, token_count, max_tokens=400):
    """Preserve sentences. Reject overlong sentences instead of truncating them."""
    chunks, current = [], []
    for sentence in sentences:
        if token_count(sentence) > max_tokens:
            raise ValueError('One sentence exceeds the model input budget. Split that sentence or increase the chunk size.')
        candidate = ' '.join(current + [sentence])
        if current and token_count(candidate) > max_tokens:
            chunks.append(' '.join(current))
            current = []
        current.append(sentence)
    if current:
        chunks.append(' '.join(current))
    return chunks
