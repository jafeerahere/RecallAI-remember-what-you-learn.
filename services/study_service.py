import json
import hashlib
from utils.config import SUMMARY_MODEL, EMBEDDING_MODEL, validate_preferences

PIPELINE_VERSION = '2.0.0'

def fingerprint(document, preferences):
    payload = {'hash':document['content_hash'],'preferences':validate_preferences(preferences),
               'version':PIPELINE_VERSION,'summary_model':SUMMARY_MODEL,'embedding_model':EMBEDDING_MODEL}
    return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()

def generate_kit(repo, document_id, preferences, progress=None, force=False):
    document = repo.document(document_id)
    if not document:
        raise ValueError('Open a material from your Library first.')
    key = fingerprint(document,preferences)
    if not force:
        cached = repo.kit(document_id,key)
        chunks = repo.chunks(document_id) if cached else []
        if cached and chunks and all(c['model'] == EMBEDDING_MODEL for c in chunks):
            if progress:
                progress('Opening your saved Study Kit...')
            # Re-selecting an older cached preference set must also reactivate
            # its deck and make it the kit shown by the next page rerun.
            # save_kit preserves review state for stable card IDs.
            repo.save_kit(document_id,key,cached,chunks)
            return cached,True
    from core.study_kit import create_study_kit
    kit,chunks = create_study_kit(document,preferences,progress)
    repo.save_kit(document_id,key,kit,chunks)
    return kit,False

def start_quiz(repo, document_id, length=5, difficulty='Adaptive', types=None, seed=0, focus=None):
    from core.quiz_engine import adapt_questions
    kit = repo.kit(document_id)
    if not kit or not kit['quiz']:
        raise ValueError('This material needs more distinct concepts to create a quiz.')
    if focus and not any(q['concept_id'] == focus for q in kit['quiz']):
        raise ValueError('There is no reliable quiz question for this concept yet. Create a source-based flashcard instead.')
    questions = adapt_questions(kit['quiz'],repo.concepts(document_id),length,difficulty,types,seed,focus)
    if not questions:
        raise ValueError('No reliable questions could be prepared for these settings.')
    return repo.save_quiz(document_id,questions),questions

def add_concept_flashcard(repo, document_id, concept_id):
    from database.db import connection
    from database.repositories import stable_id,now_iso
    concept = next((c for c in repo.concepts(document_id) if c['id'] == concept_id),None)
    if not concept:
        raise ValueError('This concept is no longer available.')
    payload = concept['payload']
    card = {'id':stable_id(document_id,concept_id,'definition-card'), 'concept_id':concept_id,
            'concept':concept['name'],'question':f"Explain {concept['name']} using the material.",
            'answer':payload['source'], 'source':payload['source'], 'location':payload['location'],
            'difficulty':'Medium'}
    from core.verifier import verify_items
    card = verify_items([card],repo.document(document_id)['text'])[0]
    state = {'next_review':now_iso(),'reviews':0,'success_count':0,'interval_days':0,'difficulty':'Medium'}
    with connection(repo.path) as db:
        db.execute('INSERT INTO flashcards VALUES (?,?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET active=1',
                   (card['id'],document_id,concept_id,json.dumps(card),json.dumps(state)))
    return card
