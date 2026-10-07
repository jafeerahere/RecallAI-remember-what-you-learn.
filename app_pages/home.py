import streamlit as st
from utils.ui import repo,ingestion_panel,select_document
from services.analytics import snapshot,greeting,display_date

st.caption(greeting())
st.title('What do you want to learn today?')
st.write('Turn anything you learn into knowledge you remember.')
with st.container(border=True):
    ingestion_panel('home',compact=True)
st.subheader('Continue Learning')
materials = repo().documents()
if not materials:
    st.caption('Your recent material will appear here after you create your first Study Kit.')
else:
    for material in materials[:3]:
        stats = snapshot(repo(),material['id'])
        with st.container(border=True):
            st.subheader(material['title'])
            st.caption('Last studied '+display_date(material['last_studied']))
            with st.container(horizontal=True):
                st.caption(f"Mastery {stats['mastery']:.0f}%" if stats['mastery'] is not None else 'Mastery not assessed')
                st.caption(f"{stats['due']} flashcards due today")
                st.caption(f"Quiz accuracy {stats['accuracy']:.0f}%" if stats['accuracy'] is not None else 'No quiz attempts yet')
                if st.button('Continue',key=f"home_continue_{material['id']}",icon=':material/arrow_forward:'):
                    select_document(material['id'])
st.subheader('Today')
stats = snapshot(repo())
with st.container(horizontal=True):
    st.metric('Cards Due',stats['due'],border=True)
    st.metric('Weak Concepts',stats['weak'],border=True)
    st.metric('Quiz Accuracy',f"{stats['accuracy']:.0f}%" if stats['accuracy'] is not None else 'Not assessed',border=True)
    st.metric('Study Materials',stats['materials'],border=True)
st.subheader('Understand → Connect → Remember → Test → Master')
for stage,description in [('Understand','Turn complex material into clear notes.'),('Connect','Discover concepts and their source passages.'),
                          ('Remember','Practice recall with scheduled flashcards.'),('Test','Use questions selected from your learning history.'),
                          ('Master','Focus your next review on concepts that need work.')]:
    st.markdown(f'**{stage}** · {description}')
