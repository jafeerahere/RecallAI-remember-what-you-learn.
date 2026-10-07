from pathlib import Path
from streamlit.testing.v1 import AppTest
from database.repositories import Repository

ROOT = Path(__file__).resolve().parents[1]

def test_pages_and_empty_input(tmp_path,monkeypatch):
    monkeypatch.setenv('RECALLAI_DB_PATH',str(tmp_path/'empty.sqlite3'))
    app = AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    assert not app.exception and not app.error
    assert 'learn today' in app.title[0].value
    for page in ['workspace','notes','flashcards','quiz','ask','progress','library','settings','home']:
        app.switch_page(f'app_pages/{page}.py').run()
        assert not app.exception and not app.error, page
    app.switch_page('app_pages/workspace.py').run()
    app.selectbox(key='workspace_depth').select('Deep').run()
    assert app.selectbox(key='workspace_cards').value == 20
    assert app.selectbox(key='workspace_difficulty').value == 'Hard'
    app.selectbox(key='workspace_depth').select('Quick').run()
    assert app.selectbox(key='workspace_cards').value == 5
    assert app.selectbox(key='workspace_difficulty').value == 'Easy'
    app.button(key='workspace_create').click().run()
    assert any('Add learning material' in e.value for e in app.error)

def test_failed_generation_is_friendly(tmp_path,monkeypatch):
    import services.study_service
    monkeypatch.setenv('RECALLAI_DB_PATH',str(tmp_path/'failure.sqlite3'))
    def unavailable(*args,**kwargs):
        raise OSError('Offline model weights are missing: diagnostic test failure')
    monkeypatch.setattr(services.study_service,'generate_kit',unavailable)
    app = AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    app.switch_page('app_pages/workspace.py').run()
    app.button(key='workspace_sample').click().run()
    app.button(key='workspace_create').click().run()
    assert not app.exception
    assert any('Could not create your Study Kit' in error.value for error in app.error)
    assert all('OSError' not in error.value for error in app.error)

def test_unwritable_database_is_friendly(tmp_path,monkeypatch):
    # A directory cannot be opened as a SQLite file, even with broad permissions.
    monkeypatch.setenv('RECALLAI_DB_PATH',str(tmp_path))
    app = AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    assert not app.exception
    assert any('Your Library could not open' in error.value for error in app.error)
