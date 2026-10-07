import streamlit as st
from utils.ui import repo,select_document,action,empty_state
from services.analytics import snapshot,display_date

st.title('Library')
st.caption('Your materials, notes and learning history, saved for the next session.')
st.session_state.setdefault('_library_query',st.session_state.get('search_query',''))
query = st.text_input('Search materials, concepts and flashcards',key='_library_query',persist_state='session',placeholder='Try transformers...')
materials = repo().documents()
if query.strip():
    matches = repo().search(query)
    st.caption(f'{len(matches)} matches')
    for i,match in enumerate(matches):
        with st.container(border=True):
            st.caption(match['type']); st.write(match['label'])
            if st.button('Open result',key=f'search_open_{i}'):
                select_document(match['document_id'])
    if not matches:
        st.caption('No results. Try another concept or part of a material title.')
elif not materials:
    empty_state('Your Library is waiting','Create a Study Kit to save your first learning material.')
else:
    for material in materials:
        stats = snapshot(repo(),material['id'])
        with st.container(border=True):
            st.subheader(material['title'])
            st.caption(f"{material['file_type']} · {material['word_count']:,} words · Added {display_date(material['created_at'])}")
            st.caption('Last studied '+display_date(material['last_studied']))
            st.caption(f"Mastery {stats['mastery']:.0f}% · {stats['due']} cards due" if stats['mastery'] is not None else f"Not assessed · {stats['due']} cards due")
            with st.container(horizontal=True):
                if st.button('Open',key=f"open_{material['id']}",type='primary'):
                    select_document(material['id'])
                if st.button('Continue studying',key=f"continue_{material['id']}"):
                    select_document(material['id'],'flashcards')
            with st.expander('Manage material'):
                title = st.text_input('Rename material',value=material['title'],key=f"rename_text_{material['id']}",max_chars=200)
                if st.button('Save title',key=f"rename_{material['id']}"):
                    with action():
                        repo().rename(material['id'],title); st.rerun()
                if st.button('Regenerate Study Kit',key=f"regenerate_{material['id']}"):
                    from services.study_service import generate_kit
                    with action('Could not regenerate this Study Kit. Your previous kit remains saved.'):
                        with st.status('Reading material...',expanded=True) as status:
                            generate_kit(repo(),material['id'],repo().preferences(),lambda m:status.update(label=m),force=True)
                            status.update(label='Study Kit updated',state='complete')
                        select_document(material['id'])
                if st.button('Delete material',key=f"delete_{material['id']}",icon=':material/delete:'):
                    with action():
                        repo().trash(material['id'])
                        if st.session_state.get('selected_document') == material['id']:
                            st.session_state.selected_document = None; st.session_state.pending_document = None
                            repo().set_active_document(None)
                        st.session_state.notice = 'Material moved to Trash. You can restore it below.'
                        st.rerun()
deleted = [d for d in repo().documents(include_deleted=True) if d['deleted_at']]
if deleted:
    with st.expander('Trash'):
        for material in deleted:
            st.write(material['title'])
            if st.button('Restore',key=f"restore_{material['id']}"):
                with action():
                    repo().restore(material['id']); st.rerun()
