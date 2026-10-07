import json
from pathlib import Path
import pytest
from core.ingestion import from_text
from database.repositories import Repository
from services.study_service import generate_kit, start_quiz

@pytest.fixture(scope='module')
def product(tmp_path_factory):
    repo = Repository(tmp_path_factory.mktemp('product') / 'recallai.sqlite3')
    material = from_text(Path('data/sample_notes.txt').read_text(encoding='utf-8'),'AI, NLP and Transformers')
    identifier,_ = repo.save_document(material)
    stages = []
    kit,cached = generate_kit(repo,identifier,repo.preferences(),stages.append)
    assert not cached and 'Finalizing Study Kit...' in stages
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/product-kit.json').write_text(json.dumps(kit,indent=2),encoding='utf-8')
    return repo,identifier,kit

@pytest.mark.integration
def test_complete_kit_and_retrieval(product):
    from services.chat_service import answer_question, ABSTAIN
    repo,identifier,kit = product
    assert kit['summary'] and kit['notes'] and kit['concepts'] and kit['exam_prep']['Long answer']
    assert len(kit['cards']) == 10 and len(kit['quiz']) >= 5
    document = repo.document(identifier)
    assert all(c['source'] in document['text'] for c in kit['concepts']+kit['cards']+kit['quiz'])
    assert all(len(c['embedding']) == 384 for c in repo.chunks(identifier))
    assert generate_kit(repo,identifier,repo.preferences())[1]
    response = answer_question(repo,identifier,'What does attention mean?')
    assert response['sources'] and 'attention' in response['answer'].lower()
    assert all(s['text'] in document['text'] for s in response['sources'])
    assert answer_question(repo,identifier,'What is the capital of Argentina?')['answer'] == ABSTAIN
    assert answer_question(repo,identifier,'What is the difference between BERT and GPT?')['sources']
    assert answer_question(repo,identifier,'Quiz me on transformers')['sources']

@pytest.mark.integration
def test_reviews_quiz_and_exports(product):
    from core.quiz_engine import validate_question
    from core.export import notes_markdown, flashcards_csv, results_csv, study_kit_pdf
    from pypdf import PdfReader
    from io import BytesIO
    repo,identifier,kit = product
    card = repo.cards(identifier)[0]
    repo.review_card(card['id'],'Good','review-id')
    repo.review_card(card['id'],'Good','review-id')
    assert repo.cards(identifier)[0]['state']['reviews'] == 1
    quiz_id,questions = start_quiz(repo,identifier,5,'Adaptive',seed=1)
    assert all(validate_question(q) for q in questions)
    assert {'MCQ','True / False','Short Answer'} <= {q['type'] for q in questions}
    answers = {i:q['correct_answer'] for i,q in enumerate(questions)}
    answers[0] = 'Incorrect test answer'
    result = repo.submit_quiz(quiz_id,answers,'Adaptive','attempt-id')
    assert result['correct'] == len(questions)-1
    before = len(repo.events(identifier))
    repo.submit_quiz(quiz_id,answers,'Adaptive','attempt-id')
    assert len(repo.events(identifier)) == before
    assert any(c['evidence_count'] for c in repo.concepts(identifier))
    assert notes_markdown(repo.document(identifier),kit).startswith('# AI')
    assert b'question,answer,concept' in flashcards_csv(repo.cards(identifier))
    assert b'user_answer' in results_csv(result)
    pdf = study_kit_pdf(repo.document(identifier),kit)
    text = ' '.join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
    assert 'Structured notes' in text and 'Quiz practice' in text and 'Source:' in text
    Path('artifacts/product-study-kit.pdf').write_bytes(pdf)

@pytest.mark.integration
def test_cached_version_reactivation(product):
    from copy import deepcopy
    from services.study_service import fingerprint
    repo,identifier,kit = product
    alternate = deepcopy(kit)
    alternate['preferences']['flashcards'] = 5
    alternate['cards'] = alternate['cards'][:5]
    repo.save_kit(identifier,fingerprint(repo.document(identifier),alternate['preferences']),alternate,repo.chunks(identifier))
    assert len(repo.cards(identifier)) == 5
    restored,cached = generate_kit(repo,identifier,kit['preferences'])
    assert cached and len(restored['cards']) == 10
    assert len(repo.cards(identifier)) == 10
    assert repo.kit(identifier)['preferences']['flashcards'] == 10
    assert any(c['state']['reviews'] == 1 for c in repo.cards(identifier))
