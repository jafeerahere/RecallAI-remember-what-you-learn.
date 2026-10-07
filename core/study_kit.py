"""Enrich the existing study pipeline; preserve its public output keys."""
import time
import re
from utils.config import DEPTHS, validate_preferences
from core.ingestion import source_location
from database.repositories import concept_id, stable_id

def cover_sections(items, segments, count):
    from core.flashcards import spread_items
    first = {}
    for item in items:
        first.setdefault(source_location(item['source'],segments).get('section','Document'),item)
    essential = list(first.values())
    if len(essential) >= count:
        return spread_items(essential,count)
    ids = {item['question'] for item in essential}
    other = [item for item in items if item['question'] not in ids]
    return essential + spread_items(other,count-len(essential))

def create_study_kit(document, preferences, progress=None):
    from utils.helpers import build_study_kit
    from core.flashcards import select_facts
    from core.concepts import structured_concepts, structured_notes, must_remember, exam_questions, knowledge_tree
    from core.retrieval import index_segments
    prefs = validate_preferences(preferences)
    depth = DEPTHS[prefs['depth']]
    start = time.perf_counter()
    notify = progress or (lambda message:None)
    notify('Reading material...')
    length = {'Concise':'Short','Balanced':depth['length'],'Detailed':'Detailed'}[prefs['generation']]
    # Build enough MCQs to support a varied later quiz without rerunning inference.
    kit = build_study_kit(document['text'],length,200,prefs['chunk_size'] or depth['chunk_size'],
                          200,depth['concepts'],progress)
    kit['cards'] = cover_sections(kit['cards'],document['segments'],prefs['flashcards'])
    kit['quiz'] = cover_sections(kit['quiz'],document['segments'],max(15,prefs['quiz_length']))
    kit['settings']['requested_questions'] = prefs['quiz_length']
    notify('Structuring content...')
    facts = select_facts(kit['text'],kit['keywords'])
    targets = {item['answer'].lower() for item in kit['cards']+kit['quiz']}
    selected_facts = [fact for fact in facts if fact['answer'].lower() in targets]
    concepts = structured_concepts(document['id'],kit['text'],kit['keywords'],selected_facts,document['segments'])
    by_name = {re.sub(r'^(?:a|an|the)\s+','',c['answer'],flags=re.I).lower():c for c in concepts}
    for item in kit['cards'] + kit['quiz']:
        name = re.sub(r'^(?:a|an|the)\s+','',item['answer'],flags=re.I).strip()
        c = by_name.get(name.lower())
        if not c:
            continue
        item.update(id=stable_id(document['id'],item['question'],item['answer']), concept=c['name'], concept_id=c['id'],
                    difficulty='Hard' if len(item['source'].split()) > 40 else 'Medium' if len(item['source'].split()) > 20 else 'Easy',
                    location=source_location(item['source'],document['segments']))
    kit['cards'] = [c for c in kit['cards'] if 'concept_id' in c]
    kit['quiz'] = [q for q in kit['quiz'] if 'concept_id' in q]
    # Concept explanation support is a source excerpt; verification still checks provenance and similarity.
    from core.verifier import verify_items
    concepts = verify_items(concepts,kit['text'])
    kit.update(concepts=concepts, notes=structured_notes(document['segments'],concepts),
               must_remember=must_remember(kit['text'],facts,document['segments']),exam_prep=exam_questions(concepts),
               knowledge_map=knowledge_tree(document['title'],concepts,document['segments']),
               takeaways=[c['source'] for c in concepts if c['importance'] == 'High'][:5],
               revision_minutes=max(1,round((len(kit['summary'].split())+len(kit['cards'])*30)/150)),
               estimated_difficulty='Advanced' if len(kit['keywords']) >= 25 else 'Intermediate' if len(kit['keywords']) >= 12 else 'Introductory',
               preferences=prefs, schema_version=2)
    notify('Preparing source search...')
    t = time.perf_counter()
    chunks = index_segments(document['id'],document['segments'])
    kit['timings']['Retrieval indexing'] = time.perf_counter()-t
    kit['timings']['Total pipeline'] = time.perf_counter()-start
    notify('Finalizing Study Kit...')
    return kit,chunks
