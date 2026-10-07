"""Real-model product journey through native Streamlit widgets."""
from pathlib import Path
import json
import pytest
from streamlit.testing.v1 import AppTest
from database.repositories import Repository

ROOT = Path(__file__).resolve().parents[1]

def button(app,label):
    return next(b for b in app.button if b.label == label)

def healthy(app):
    assert not app.exception and not app.error

@pytest.mark.integration
def test_demo_flow(tmp_path,monkeypatch):
    path = tmp_path/'journey.sqlite3'
    monkeypatch.setenv('RECALLAI_DB_PATH',str(path))
    app = AppTest.from_file(str(ROOT/'app.py'),default_timeout=300).run()
    healthy(app)
    app.switch_page('app_pages/workspace.py').run()
    app.button(key='workspace_sample').click().run()
    assert len(app.text_area(key='workspace_text').value.split()) >= 600
    app.button(key='workspace_create').click().run(timeout=300)
    healthy(app)
    identifier = app.session_state['selected_document']
    repo = Repository(path)
    kit = repo.kit(identifier)
    assert kit['summary'] and kit['notes'] and len(kit['cards']) == 10
    assert repo.chunks(identifier) and len(repo.documents()) == 1
    Path('artifacts/ui-product-kit.json').write_text(json.dumps(kit,indent=2),encoding='utf-8')
    app.switch_page('app_pages/notes.py').run(); healthy(app)
    assert any(n['heading'] in s.value for n in kit['notes'] for s in app.subheader)
    app.session_state['notes_tabs'] = 'Knowledge Map'
    app.run(); healthy(app)
    assert any('Knowledge Map' in s.value for s in app.subheader)
    app.switch_page('app_pages/flashcards.py').run(); healthy(app)
    card_id = app.session_state['review_card_id']
    button(app,'Show Answer').click().run(); healthy(app)
    button(app,'Good').click().run(); healthy(app)
    assert next(c for c in repo.cards(identifier) if c['id'] == card_id)['state']['reviews'] == 1
    app.switch_page('app_pages/quiz.py').run(); healthy(app)
    button(app,'Start quiz').click().run(); healthy(app)
    state = app.session_state['quiz_session']
    assert len(state['questions']) == 5
    for i,q in enumerate(state['questions']):
        answer = q['correct_answer']
        if i == 0:
            answer = next(o for o in q['options'] if o != answer) if q['options'] else 'Incorrect'
        key = f"answer_{state['quiz_id']}_{i}"
        widget = app.text_input(key=key) if q['type'] == 'Short Answer' else app.radio(key=key)
        widget.set_value(answer)
    button(app,'Submit answers').click().run(); healthy(app)
    assert any('4 / 5' in s.value for s in app.success)
    assert len(repo.attempts(identifier)) == 1
    app.button(key='new_cards_1').click().run(); healthy(app)
    assert len(repo.cards(identifier)) == 11
    app.button(key='another_1').click().run(); healthy(app)
    focused = app.session_state['quiz_session']
    assert len(focused['questions']) == 1
    q = focused['questions'][0]
    answer_key = f"answer_{focused['quiz_id']}_0"
    widget = app.text_input(key=answer_key) if q['type'] == 'Short Answer' else app.radio(key=answer_key)
    widget.set_value(q['correct_answer'])
    button(app,'Submit answers').click().run(); healthy(app)
    assert len(repo.attempts(identifier)) == 2
    app.switch_page('app_pages/progress.py').run(); healthy(app)
    assert repo.events(identifier) and any(c['evidence_count'] for c in repo.concepts(identifier))
    assert any(m.label == 'Quiz Accuracy' and m.value == '83%' for m in app.metric)
    app.switch_page('app_pages/ask.py').run(); healthy(app)
    app.chat_input[0].set_value('What does attention mean?').run(); healthy(app)
    assert len(repo.chat(identifier)) == 2 and repo.chat(identifier)[-1]['sources']
    app.switch_page('app_pages/settings.py').run(); healthy(app)
    app.text_area(key='evaluation_reference').set_value('Artificial intelligence includes machine learning. NLP studies language. Transformers use attention to process tokens.')
    app.button(key='evaluate_summary').click().run(); healthy(app)
    assert len(app.dataframe) >= 2
    # Fresh browser session restores the selection, kit and completed actions from SQLite.
    fresh = AppTest.from_file(str(ROOT/'app.py'),default_timeout=300).run()
    healthy(fresh)
    assert fresh.session_state['selected_document'] == identifier
    fresh.switch_page('app_pages/library.py').run(); healthy(fresh)
    fresh.button(key=f'open_{identifier}').click().run(); healthy(fresh)
    assert fresh.session_state['selected_document'] == identifier
    # AppTest needs its own page pointer synchronized after a widget-triggered redirect.
    fresh.switch_page('app_pages/workspace.py').run(); healthy(fresh)
    fresh.button(key='prepare_kit_pdf').click().run(); healthy(fresh)
    assert fresh.session_state['prepared_pdf']['bytes'].startswith(b'%PDF')
    fresh.switch_page('app_pages/quiz.py').run(); healthy(fresh)
    assert len(repo.attempts(identifier)) == 2
    next(s for s in fresh.selectbox if s.label == 'Feedback').set_value('Immediate')
    button(fresh,'Start quiz').click().run(); healthy(fresh)
    immediate = fresh.session_state['quiz_session']
    assert immediate['feedback'] == 'Immediate'
    for i,q in enumerate(immediate['questions']):
        key = f"answer_{immediate['quiz_id']}_{i}"
        widget = fresh.text_input(key=key) if q['type'] == 'Short Answer' else fresh.radio(key=key)
        widget.set_value(q['correct_answer'])
        button(fresh,'Check answer').click().run(); healthy(fresh)
        assert any(s.value == 'Correct' for s in fresh.success)
        button(fresh,'Finish quiz' if i == len(immediate['questions'])-1 else 'Next question').click().run(); healthy(fresh)
    assert len(repo.attempts(identifier)) == 3
    assert repo.attempts(identifier)[0]['accuracy'] == 100
    fresh.switch_page('app_pages/library.py').run(); healthy(fresh)
    fresh.text_input(key=f'rename_text_{identifier}').set_value('Renamed material')
    fresh.button(key=f'rename_{identifier}').click().run(); healthy(fresh)
    assert repo.document(identifier)['title'] == 'Renamed material'
    fresh.text_input(key='_library_query').set_value('transformers').run(); healthy(fresh)
    assert any('matches' in caption.value for caption in fresh.caption)
    fresh.text_input(key='_library_query').set_value('').run()
    fresh.button(key=f'delete_{identifier}').click().run(); healthy(fresh)
    assert not repo.documents()
    fresh.button(key=f'restore_{identifier}').click().run(); healthy(fresh)
    assert repo.document(identifier) and repo.kit(identifier)
