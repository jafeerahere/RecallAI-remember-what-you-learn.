"""RecallAI entrypoint. Existing NLP modules remain behind product services."""
import streamlit as st
from utils.ui import repo
from utils.config import processing_location
from utils.logging import get_logger

st.set_page_config(page_title='RecallAI | Remember what you learn',page_icon=':material/neurology:',layout='wide')
try:
    repository = repo()
    documents = repository.documents()
except Exception:
    get_logger().exception('Could not initialize library')
    st.error('Your Library could not open. Check that the data folder is writable, then restart RecallAI.')
    st.stop()

st.session_state.setdefault('selected_document',repository.active_document())
st.session_state.setdefault('draft_text',st.session_state.get('notes_draft',''))
st.session_state.setdefault('draft_title','Untitled material')
if 'pending_document' in st.session_state:
    st.session_state.selected_document = st.session_state.pop('pending_document')
    st.session_state._material_picker = st.session_state.selected_document
identifiers = [d['id'] for d in documents]
if st.session_state.selected_document not in identifiers:
    st.session_state.selected_document = None
if st.session_state.get('_material_picker') not in identifiers:
    st.session_state._material_picker = st.session_state.selected_document

with st.sidebar:
    st.title('RecallAI',icon=':material/neurology:')
    st.caption('Remember what you learn.')

pages = [st.Page('app_pages/home.py',title='Home',icon=':material/home:',default=True),
         st.Page('app_pages/workspace.py',title='Study Workspace',icon=':material/auto_stories:'),
         st.Page('app_pages/notes.py',title='AI Notes',icon=':material/description:'),
         st.Page('app_pages/flashcards.py',title='Flashcards',icon=':material/style:'),
         st.Page('app_pages/quiz.py',title='Quiz',icon=':material/quiz:'),
         st.Page('app_pages/ask.py',title='Ask RecallAI',icon=':material/chat:'),
         st.Page('app_pages/progress.py',title='Progress',icon=':material/insights:'),
         st.Page('app_pages/library.py',title='Library',icon=':material/library_books:'),
         st.Page('app_pages/settings.py',title='Settings',icon=':material/settings:')]
page = st.navigation(pages,position='sidebar',expanded=True)

def change_material():
    identifier = st.session_state._material_picker
    st.session_state.selected_document = identifier
    repository.set_active_document(identifier)
    document = repository.document(identifier) if identifier else None
    if document:
        st.session_state.draft_text = document['text']
        st.session_state.draft_title = document['title']
        st.session_state.draft_material = {k:document[k] for k in ['title','file_type','text','segments','warnings']}

def global_search():
    st.session_state.search_query = st.session_state._global_search
    st.session_state._library_query = st.session_state._global_search
    st.switch_page('app_pages/library.py')

with st.sidebar:
    titles = {d['id']:d['title'] for d in documents}
    st.selectbox('Current material',[None]+identifiers,format_func=lambda value:titles.get(value,'Choose a material'),
                 key='_material_picker',on_change=change_material)
    st.text_input('Search Library',placeholder='Find a topic...',key='_global_search',on_change=global_search)
    st.badge('Processing: '+processing_location(),color='violet',icon=':material/computer:')
    st.caption('One shared profile · Saved on the app server')

if notice := st.session_state.pop('notice',None):
    st.toast(notice,icon=':material/check_circle:')
try:
    page.run()
except Exception:
    get_logger().exception('Page rendering failed: %s',page.title)
    st.error('This page could not load. Your saved material is still in Library. Try refreshing or opening another page.')
