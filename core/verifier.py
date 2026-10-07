import re
from core.keywords import load_embeddings

def verify_items(items, document):
    if not items:
        return []
    model = load_embeddings()
    answers = model.encode([i.get('correct_answer') or i.get('answer','') for i in items], normalize_embeddings=True)
    sources = model.encode([i['source'] for i in items], normalize_embeddings=True)
    result = []
    for item, answer_vector, source_vector in zip(items, answers, sources):
        answer = item.get('correct_answer') or item.get('answer','')
        similarity = max(0., min(1., float(answer_vector @ source_vector)))
        exact = bool(re.search(r'(?<!\w)' + re.escape(answer) + r'(?!\w)', item['source'], re.I))
        supported = bool(answer) and bool(item['source']) and item['source'] in document and exact and similarity >= .2
        result.append({**item, 'support_score': similarity, 'verified': supported})
    return result
