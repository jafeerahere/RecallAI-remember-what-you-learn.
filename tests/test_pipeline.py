import pytest
from core.chunking import chunk_sentences
from core.preprocessing import preprocess
from utils.helpers import score_quiz

def test_empty_and_short():
    with pytest.raises(ValueError, match='Add some notes'):
        preprocess('  ')
    with pytest.raises(ValueError, match='50 words'):
        preprocess('Short note.')

def test_chunking_preserves_every_sentence():
    sentences = ['One complete sentence.', 'Another complete sentence.', 'The final sentence.'] * 100
    chunks = chunk_sentences(sentences, lambda s:len(s.split()), 12)
    assert ' '.join(chunks) == ' '.join(sentences)
    assert all(len(c.split()) <= 12 for c in chunks)
    with pytest.raises(ValueError, match='One sentence'):
        chunk_sentences(['word ' * 15], lambda s:len(s.split()), 12)

def test_scoring():
    qs = [{'correct_answer':'A'}, {'correct_answer':'B'}]
    assert score_quiz(qs, {0:'A',1:'C'}) == (1,2,50)
    assert score_quiz(qs, {0:'A',1:'B'}) == (2,2,100)
    assert score_quiz([], {}) == (0,0,0)

@pytest.mark.integration
def test_real_pipeline():
    from pathlib import Path
    from utils.helpers import build_study_kit
    notes = Path('data/sample_notes.txt').read_text()
    kit = build_study_kit(notes)
    assert kit['summary'] and len(kit['keywords']) >= 5
    assert 5 <= len(kit['cards']) <= 10
    assert len(kit['quiz']) == 5
    for q in kit['quiz']:
        assert len(q['options']) == len(set(o.lower() for o in q['options'])) == 4
        assert q['options'].count(q['correct_answer']) == 1
        assert q['correct_answer'].lower() not in q['question'].lower()
        assert q['source'] in kit['text']
        assert 0 <= q['support_score'] <= 1
    assert score_quiz(kit['quiz'], {i:q['correct_answer'] for i,q in enumerate(kit['quiz'])})[2] == 100

@pytest.mark.integration
def test_long_document_and_weak_evidence():
    from pathlib import Path
    from core.summarizer import generate_summary, load_summarizer
    from core.keywords import load_embeddings
    from core.verifier import verify_items
    from core.quiz_generator import generate_quiz
    text = Path('data/sample_notes.txt').read_text() * 3
    summary, chunks = generate_summary(text, 'Short', 200)
    assert chunks > 5 and summary
    assert load_summarizer() is load_summarizer()
    assert load_embeddings() is load_embeddings()
    item = {'question':'What is this?', 'answer':'Bananas', 'source':'Attention compares tokens.'}
    assert not verify_items([item], text)[0]['verified']
    assert generate_quiz('A single concept is defined here.', [], 5) == []
