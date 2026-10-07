import re
from core.retrieval import retrieve, relevant_sentences

ABSTAIN = "I couldn't find enough information about that in this material."

def answer_question(repo, document_id, prompt, top_k=4):
    document, kit = repo.document(document_id), repo.kit(document_id)
    if not document or not kit:
        return {'answer':ABSTAIN,'sources':[]}
    lowered = prompt.lower()
    selected = []
    # These commands select actual saved study material and attach its evidence.
    if re.search(r'\b(revise first|weak|revise next)\b',lowered):
        concepts = repo.concepts(document_id)
        selected = [c['payload'] for c in concepts[:3]]
        answer = 'Start with these concepts. The order uses your recorded mastery; unstudied concepts come first:\n\n' + '\n'.join('- '+c['name'] for c in selected)
    elif re.search(r'\b(important concepts|key concepts)\b',lowered):
        selected = sorted(kit['concepts'],key=lambda c:c['relevance'],reverse=True)[:5]
        answer = 'The main concepts in this material are:\n\n' + '\n'.join('- '+c['name']+': '+c['explanation'] for c in selected)
    elif re.search(r'\b(quiz me|test me)\b',lowered):
        target = re.sub(r'^.*?(?:quiz me|test me)(?: on| about)?\s*','',lowered).strip()
        candidates = [q for q in kit['quiz'] if not target or target in q['source'].lower() or (target.endswith('s') and target[:-1] in q['source'].lower())]
        if not candidates:
            from core.quiz_generator import generate_quiz
            from core.ingestion import source_location
            pool = generate_quiz(document['text'],kit['keywords'],200)
            candidates = [{**q,'location':source_location(q['source'],document['segments'])} for q in pool
                          if target in q['source'].lower() or (target.endswith('s') and target[:-1] in q['source'].lower())]
        if not candidates:
            return {'answer':ABSTAIN,'sources':[]}
        q = candidates[0]; selected = [q]
        answer = q['question']+'\n\n'+'\n'.join(f'{i+1}. {o}' for i,o in enumerate(q['options']))+'\n\nUse Quiz for scored practice and progress tracking.'
    elif re.search(r'\b(explain this|summarize this|overview|chapter simply)\b',lowered):
        selected = kit['concepts'][:5]
        answer = 'Here is a source-based overview:\n\n'+'\n'.join('- '+c['explanation'] for c in selected)
    else:
        passages = retrieve(prompt,repo.chunks(document_id),top_k)
        sentences = relevant_sentences(prompt,passages,5 if 'difference' in lowered or 'compare' in lowered else 3)
        # Unknown named terms must not be answered just because the surrounding
        # question resembles a known definition. Require meaningful lexical evidence.
        stop = {'what','does','mean','explain','how','why','when','where','which','the','a','an','is','are','in','this',
                'material','chapter','simply','difference','between','and','compare','to','of','do','can','you','please','tell','me'}
        terms = set(re.findall(r'[a-z][a-z0-9-]+',lowered))-stop
        from core.preprocessing import load_nlp
        nouns = {t.text.lower() for t in load_nlp()(prompt) if t.pos_ in ('NOUN','PROPN') and t.text.lower() not in stop}
        corpus = ' '.join(p['text'].lower() for p in passages)
        if nouns and any(not re.search(r'\b'+re.escape(n)+r'\b',document['text'].lower()) for n in nouns):
            return {'answer':ABSTAIN,'sources':[]}
        if terms and not any(re.search(r'\b'+re.escape(t)+r'\b',corpus) for t in terms):
            return {'answer':ABSTAIN,'sources':[]}
        if not sentences:
            return {'answer':ABSTAIN,'sources':[]}
        answer = 'Your material explains this as follows:\n\n'+'\n'.join('- '+s['text'] for s in sentences)
        selected = [{'source':s['text'],'location':s['chunk']['location'],'similarity':s['similarity']} for s in sentences]
    sources, seen = [], set()
    for item in selected:
        passage = item['source']
        if passage in document['text'] and passage not in seen:
            sources.append({'document_id':document_id,'document_name':document['title'],'text':passage,
                            'location':item.get('location',{}),'similarity':item.get('similarity')})
            seen.add(passage)
    return {'answer':answer if sources else ABSTAIN,'sources':sources}
