"""Shared native Streamlit views. Inference runs only after explicit actions."""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import streamlit as st
from utils.config import ROOT, db_path, processing_location
from utils.logging import get_logger

@st.cache_resource(max_entries=4, show_spinner=False)
def get_repository(path):
    from database.repositories import Repository
    return Repository(path)

def repo():
    return get_repository(str(db_path()))

@contextmanager
def action(message='That action could not finish. Please try again.'):
    try:
        yield
    except ValueError as exc:
        message = str(exc)
        if 'One sentence exceeds' in message:
            message = 'This material contains a very long sentence. Add sentence breaks or split it into smaller sections, then try again.'
        elif 'model returned an empty summary' in message:
            message = 'No usable summary could be created. Try clearer notes or a shorter section.'
        st.error(message)
    except MemoryError:
        get_logger().exception('Memory limit during operation')
        st.error('There is not enough memory for this material. Try a smaller chapter and Quick study depth.')
    except Exception:
        get_logger().exception('Application operation failed')
        st.error(message)

def select_document(identifier, page='workspace'):
    st.session_state.selected_document = identifier
    st.session_state.pending_document = identifier
    repo().set_active_document(identifier)
    repo().touch(identifier)
    document = repo().document(identifier)
    if document:
        st.session_state.draft_text = document['text']
        st.session_state.draft_title = document['title']
        st.session_state.draft_material = {k:document[k] for k in ['title','file_type','text','segments','warnings']}
    st.switch_page(f'app_pages/{page}.py')

def active_material():
    identifier = st.session_state.get('selected_document')
    return repo().document(identifier) if identifier else None

def require_kit(title, description):
    document = active_material()
    kit = repo().kit(document['id']) if document else None
    if not kit:
        empty_state(title,description)
        st.stop()
    return document,kit

def empty_state(title, description):
    with st.container(border=True):
        st.subheader(title)
        st.caption(description)
        if st.button('Create Study Kit', type='primary', key='empty_create', icon=':material/add:'):
            st.switch_page('app_pages/workspace.py')

def source_evidence(item, document, expanded=False, label='Source evidence'):
    from core.export import location_label
    if 'verified' in item:
        st.badge('Source Supported' if item['verified'] else 'Low Support · Review Recommended',
                 color='green' if item['verified'] else 'orange', icon=':material/check_circle:' if item['verified'] else ':material/info:')
    with st.expander(label,expanded=expanded):
        st.caption(document['title']+' · '+location_label(item.get('location',{})))
        st.write(item.get('source',item.get('text','')))
        st.caption('Support means consistency with this material. Review the original source when accuracy matters.')

def ingestion_panel(prefix='workspace', compact=False):
    from core.ingestion import extract_document, from_text, normalize
    from services.study_service import generate_kit
    preferences = repo().preferences()
    st.subheader('Bring your learning material' if compact else 'Add Learning Material')
    st.caption('PDF · DOCX · PPTX · TXT, or paste text. Up to 20 MB per file.')
    st.session_state.setdefault('draft_text',st.session_state.get('notes_draft',''))
    st.session_state.setdefault('draft_title','Untitled material')
    st.session_state.setdefault('draft_material',None)
    title_key, text_key = f'{prefix}_title', f'{prefix}_text'
    if title_key not in st.session_state or st.session_state.get(f'{prefix}_title_synced') != st.session_state.draft_title:
        st.session_state[title_key] = st.session_state.draft_title
    if text_key not in st.session_state or st.session_state.get(f'{prefix}_text_synced') != st.session_state.draft_text:
        st.session_state[text_key] = st.session_state.draft_text
    tabs = st.tabs(['Upload','Paste Text'], key=f'{prefix}_input_tabs', on_change='rerun')
    with tabs[0]:
        upload = st.file_uploader('Upload learning material',type=['pdf','docx','pptx','txt'],key=f'{prefix}_upload',max_upload_size=20)
        if upload:
            payload = upload.getvalue()
            digest = hashlib.sha256(payload+upload.name.encode()).hexdigest()
            if st.session_state.get('upload_digest') != digest:
                with action('Could not read this document. Try saving a fresh copy.'):
                    material = extract_document(payload,upload.name)
                    st.session_state.draft_material = material.to_dict()
                    st.session_state.draft_text,st.session_state.draft_title = material.text,material.title
                    st.session_state[text_key],st.session_state[title_key] = material.text,material.title
                    st.session_state.upload_digest = digest
        if st.button('Load Sample Notes',key=f'{prefix}_sample',icon=':material/description:'):
            sample = (ROOT/'data'/'sample_notes.txt').read_text(encoding='utf-8')
            material = from_text(sample,'Artificial Intelligence, NLP and Transformers','Sample')
            st.session_state.draft_material = material.to_dict()
            st.session_state.draft_text,st.session_state.draft_title = material.text,material.title
            st.session_state[text_key],st.session_state[title_key] = material.text,material.title
    with tabs[1]:
        text = st.text_area('Learning material',key=text_key,height=170 if compact else 290,max_chars=250000,
                            placeholder='Paste a chapter, lecture notes, or an article...',persist_state='session')
        st.session_state.draft_text = text
        st.session_state[f'{prefix}_text_synced'] = text
    title = st.text_input('Material title',key=title_key,max_chars=200,persist_state='session')
    st.session_state.draft_title = title
    st.session_state[f'{prefix}_title_synced'] = title
    text = st.session_state.draft_text
    with st.container(horizontal=True):
        st.caption(f'{len(text.split()):,} words')
        st.caption(f'{len(text):,} characters')
        st.caption(f'{max(1,round(len(text.split())/200)) if text else 0} min read')
    extracted = st.session_state.draft_material
    if extracted and normalize(text) == extracted['text']:
        sections = list(dict.fromkeys(s.get('section','') for s in extracted['segments']))
        st.caption(f'{len(sections)} detected sections · {extracted["file_type"]}')
        for warning in extracted['warnings']:
            st.warning(warning)
    elif extracted:
        st.caption('Edited text uses paragraph source labels. Original page and slide locations are kept only for unchanged extracts.')
    if not compact:
        st.subheader('Study Preferences')
        def apply_depth_defaults():
            chosen = st.session_state[f'{prefix}_depth']
            st.session_state[f'{prefix}_cards'] = {'Quick':5,'Standard':10,'Deep':20}[chosen]
            st.session_state[f'{prefix}_difficulty'] = {'Quick':'Easy','Standard':'Adaptive','Deep':'Hard'}[chosen]
        with st.container(horizontal=True):
            depth = st.selectbox('Study Depth',['Quick','Standard','Deep'],index=['Quick','Standard','Deep'].index(preferences['depth']),key=f'{prefix}_depth',on_change=apply_depth_defaults)
            length = st.selectbox('Quiz',[5,10,15],index=[5,10,15].index(preferences['quiz_length']),key=f'{prefix}_length')
            difficulty = st.selectbox('Difficulty',['Adaptive','Easy','Medium','Hard'],index=['Adaptive','Easy','Medium','Hard'].index(preferences['difficulty']),key=f'{prefix}_difficulty')
            cards = st.selectbox('Flashcards',[5,10,20],index=[5,10,20].index(preferences['flashcards']),key=f'{prefix}_cards')
        st.caption({'Quick':'A fast overview and essential concepts.','Standard':'Balanced notes, concepts and practice.','Deep':'Detailed notes, more concepts, additional flashcards and harder practice.'}[depth]+' You can adjust the practice settings above.')
        preferences = {**preferences,'depth':depth,'quiz_length':length,'difficulty':difficulty,'flashcards':cards}
    if st.button('Create Study Kit',key=f'{prefix}_create',type='primary',icon=':material/auto_awesome:',width='stretch'):
        with action('Could not create your Study Kit. Check your internet connection or try a smaller chapter.'):
            if not text.strip():
                raise ValueError('Add learning material before creating a Study Kit.')
            if len(text.split()) < 50:
                raise ValueError('Add at least 50 words so there is enough context to study.')
            if extracted and normalize(text) == extracted['text']:
                from core.ingestion import Material
                material = Material(title,extracted['file_type'],extracted['text'],extracted['segments'],extracted['warnings'])
            else:
                material = from_text(text,title)
            identifier,duplicate = repo().save_document(material)
            with st.status('Reading material...',expanded=True) as status:
                def stage(message):
                    status.update(label=message)
                    st.caption(message)
                kit,cached = generate_kit(repo(),identifier,preferences,stage)
                status.update(label='Your Study Kit is ready',state='complete',expanded=False)
            st.session_state.selected_document = identifier
            repo().set_active_document(identifier)
            st.session_state.pop('quiz_session',None)
            st.session_state.notice = 'Opened your saved Study Kit.' if cached else 'Your Study Kit is ready.'
            st.session_state.pending_document = identifier
            # Widget was rendered in the entrypoint, so selection updates happen on the next run.
            if compact:
                st.switch_page('app_pages/workspace.py')
            st.rerun()

def render_notes(document, kit):
    for note in kit['notes']:
        with st.container(border=True):
            st.subheader(note['heading'])
            st.write(note['explanation'])
            matched = [c for c in kit['concepts'] if c['source'] in note['points']]
            for concept in matched[:4]:
                st.markdown('**'+concept['name']+'**')
                st.caption(concept['explanation'])
            for point in note['points']:
                if point != note['explanation']:
                    st.markdown('- '+point)
            from core.export import location_label
            st.caption('Source: '+location_label(note['location']))

def render_concepts(document, kit, prefix='concept'):
    status = {c['id']:c for c in repo().concepts(document['id'])}
    for concept in kit['concepts']:
        with st.container(border=True):
            st.subheader(concept['name'])
            st.caption(concept['importance']+' importance')
            st.write(concept['explanation'])
            learned = status.get(concept['id'],{})
            if learned.get('evidence_count'):
                st.progress(learned['score']/100,text=f"{learned['score']:.0f}% mastery")
            else:
                st.caption('Not studied yet')
            source_evidence(concept,document)

def render_tree(document, kit):
    from core.mastery import mastery_label
    status = {c['id']:c for c in repo().concepts(document['id'])}
    st.subheader('Knowledge Map')
    st.caption('Grouped by the sections actually found in this material.')
    st.markdown('**'+document['title']+'**')
    for group in kit['knowledge_map']['groups']:
        with st.expander(group['name'],expanded=True):
            for identifier in group['concept_ids']:
                row = status.get(identifier)
                if row:
                    label = f"{row['score']:.0f}% · {mastery_label(row['score'])}" if row['evidence_count'] else 'Not studied yet'
                    st.markdown(f"- **{row['name']}** · {label}")

def render_kit(document,kit):
    st.subheader(document['title'])
    st.caption('Your Study Kit · '+document['file_type'])
    names = ['Overview','AI Notes','Key Concepts','Must Remember','Flashcards','Quiz','Exam Prep']
    tabs = st.tabs(names,key='kit_tabs',on_change='rerun')
    for name,tab in zip(names,tabs):
        if not tab.open:
            continue
        with tab:
            if name == 'Overview':
                st.write(kit['summary'])
                st.caption('Review the summary against your original material.')
                with st.container(horizontal=True):
                    st.metric('Difficulty estimate',kit['estimated_difficulty'],border=True)
                    st.metric('Revision time',f"{kit['revision_minutes']} min",border=True)
                st.caption('Difficulty is a heuristic based on concept count, not a validated reading-level measure.')
                st.subheader('Important takeaways')
                for takeaway in kit['takeaways']:
                    st.markdown('- '+takeaway)
                render_tree(document,kit)
            elif name == 'AI Notes':
                render_notes(document,kit)
            elif name == 'Key Concepts':
                render_concepts(document,kit)
            elif name == 'Must Remember':
                for category, entries in kit['must_remember'].items():
                    st.subheader(category)
                    for entry in entries:
                        source_evidence({'source':entry['text'],'location':entry['location']},document,True,'Supporting passage')
            elif name == 'Flashcards':
                st.caption(f"{len(kit['cards'])} cards in this kit")
                for card in kit['cards'][:3]:
                    with st.container(border=True):
                        st.write(card['question'])
                        with st.expander('Answer'):
                            st.write(card['answer']); source_evidence(card,document)
                if st.button('Practice flashcards',key='kit_practice_cards',type='primary'):
                    st.switch_page('app_pages/flashcards.py')
            elif name == 'Quiz':
                st.caption(f"{len(kit['quiz'])} source-based practice questions available")
                if st.button('Start a quiz',key='kit_start_quiz',type='primary'):
                    st.switch_page('app_pages/quiz.py')
            else:
                st.caption('Potential exam prompts grounded in the material. These are practice questions, not predictions of an actual exam.')
                for level, questions in kit['exam_prep'].items():
                    st.subheader(level)
                    for q in questions:
                        with st.expander(q['question']):
                            st.write('Answer outline')
                            for point in q['answer_outline']:
                                st.markdown('- '+point)
                            source_evidence(q,document)
    with st.popover('Export Study Kit',icon=':material/download:'):
        from core.export import notes_markdown,flashcards_csv,study_kit_pdf
        st.download_button('Study notes · Markdown',notes_markdown(document,kit),file_name='recallai-notes.md',mime='text/markdown',key='export_notes',on_click='ignore')
        st.download_button('Flashcards · CSV',flashcards_csv(repo().cards(document['id'])),file_name='recallai-flashcards.csv',mime='text/csv',key='export_cards',on_click='ignore')
        signature = hashlib.sha256(json.dumps({'kit':kit,'title':document['title']},sort_keys=True).encode()).hexdigest()
        if st.button('Prepare complete PDF',key='prepare_kit_pdf'):
            with action('Could not prepare the PDF. Try the Markdown export instead.'):
                with st.spinner('Preparing your PDF...'):
                    st.session_state.prepared_pdf = {'document_id':document['id'],'signature':signature,'bytes':study_kit_pdf(document,kit)}
        export = st.session_state.get('prepared_pdf')
        if export and export['document_id'] == document['id'] and export['signature'] == signature:
            st.download_button('Complete Study Kit · PDF',export['bytes'],file_name='recallai-study-kit.pdf',mime='application/pdf',key='download_kit_pdf',on_click='ignore')
        st.download_button('Complete Study Kit · JSON',json.dumps(kit,indent=2),file_name='recallai-study-kit.json',mime='application/json',key='export_json',on_click='ignore')
