import streamlit as st
from utils.ui import ingestion_panel,active_material,repo,render_kit,action
from services.study_service import generate_kit

st.title('Study Workspace')
st.caption('One place to understand your material and prepare your next review.')
left,right = st.columns([2.3,1],gap='large')
with left,st.container(border=True):
    ingestion_panel('workspace')
with right:
    st.subheader('How RecallAI Works')
    for number,title,description in [('01','Understand','Turn complex material into clear notes.'),('02','Connect','Discover important concepts and relationships.'),
                                     ('03','Remember','Practice with intelligent flashcards.'),('04','Test','Challenge yourself with adaptive quizzes.'),
                                     ('05','Master','Focus your review on weak areas.')]:
        with st.container(border=True):
            st.markdown(f'**{number} · {title}**'); st.caption(description)
document = active_material()
if document:
    kit = repo().kit(document['id'])
    if kit:
        render_kit(document,kit)
    else:
        with st.container(border=True):
            st.subheader(document['title'])
            st.caption('This material is saved. Create a Study Kit to prepare notes and practice questions.')
            if st.button('Create kit for saved material',key='saved_create',type='primary'):
                with action('Could not process this material. Try a smaller chapter.'):
                    with st.status('Reading material...',expanded=True) as status:
                        generate_kit(repo(),document['id'],repo().preferences(),lambda message:status.update(label=message))
                        status.update(label='Study Kit ready',state='complete')
                    st.rerun()
