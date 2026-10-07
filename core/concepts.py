"""Structure source excerpts. Explanations remain quotations from the material."""
import re
from core.ingestion import source_location
from database.repositories import concept_id, stable_id

def structured_concepts(document_id, text, keywords, facts, segments):
    from core.preprocessing import load_nlp
    sentences = [s.text.strip() for s in load_nlp()(text).sents]
    concepts, seen = [], set()
    candidates = [(f['answer'], None, f['source']) for f in facts] + [(phrase,score,None) for phrase,score in keywords]
    for name, relevance, source in candidates:
        cleaned = re.sub(r'^(?:a|an|the)\s+', '', name, flags=re.I).strip()
        if cleaned.lower() in seen or cleaned.lower() in {'text','content','material','words','tokens','language'}:
            continue
        if not source:
            source = next((s for s in sentences if re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)',s,re.I)),None)
        if not source:
            continue
        concepts.append({'id':concept_id(document_id,cleaned),'name':cleaned,'answer':name,
                         'explanation':source,'source':source,'location':source_location(source,segments),
                         'importance':'High' if relevance is None else 'Medium' if relevance >= .45 else 'Low',
                         'relevance':float(relevance) if relevance is not None else None})
        seen.add(cleaned.lower())
    if concepts:
        import numpy as np
        from core.embeddings import encode_texts
        mean = encode_texts(tuple(sentences)).mean(axis=0)
        mean /= max(float(np.linalg.norm(mean)),1e-12)
        vectors = encode_texts(tuple(c['name'] for c in concepts))
        for concept,vector in zip(concepts,vectors):
            concept['relevance'] = float(vector @ mean)
    return concepts

def structured_notes(segments, concepts):
    notes = []
    groups = {}
    for segment in segments:
        title = segment.get('section') or 'Key ideas'
        group = groups.setdefault(title,{'heading':title,'explanation':'','points':[],'location':{k:v for k,v in segment.items() if k != 'text'}})
        for concept in concepts:
            if concept['source'] in segment['text'] and concept['source'] not in group['points']:
                group['points'].append(concept['source'])
        if not group['points']:
            from core.preprocessing import load_nlp
            group['points'].extend(s.text.strip() for s in list(load_nlp()(segment['text']).sents)[:3])
        if not group['explanation']:
            group['explanation'] = group['points'][0] if group['points'] else segment['text']
    for group in groups.values():
        group['points'] = list(dict.fromkeys(group['points']))
        notes.append(group)
    return notes

def must_remember(text, facts, segments):
    from core.preprocessing import load_nlp
    groups = {}
    for fact in facts:
        category = 'Definitions' if re.search(r'\b(is|are|refers to)\b',fact['source']) else 'Relationships and important facts'
        groups.setdefault(category,[]).append({'text':fact['source'],'location':source_location(fact['source'],segments)})
    for sentence in load_nlp()(text).sents:
        source = sentence.text.strip()
        category = 'Formulas' if re.search(r'\b\w+\s*=\s*\S+',source) else 'Dates' if re.search(r'\b(?:19|20)\d{2}\b|\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b',source) else None
        if category:
            groups.setdefault(category,[]).append({'text':source,'location':source_location(source,segments)})
    return {k:list({entry['text']:entry for entry in v}.values()) for k,v in groups.items() if v}

def exam_questions(concepts):
    result = {'Short answer':[], 'Medium answer':[], 'Long answer':[]}
    for i, concept in enumerate(concepts[:12]):
        level = ['Short answer','Medium answer','Long answer'][i%3]
        stem = {'Short answer':'Define', 'Medium answer':'Explain the role of', 'Long answer':'Discuss the description and relationships of'}[level]
        result[level].append({'question':f"{stem} {concept['name']} using the material.",
                              'answer_outline':[concept['source']], 'source':concept['source'], 'location':concept['location']})
    return result

def knowledge_tree(title, concepts, segments):
    groups = {}
    for concept in concepts:
        groups.setdefault(concept['location'].get('section','Key concepts'),[]).append(concept['id'])
    return {'root':title,'groups':[{'name':name,'concept_ids':ids} for name,ids in groups.items()]}
