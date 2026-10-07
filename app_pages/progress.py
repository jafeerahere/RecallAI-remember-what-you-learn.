import streamlit as st
import pandas as pd
from utils.ui import repo,empty_state,source_evidence,action,select_document
from services.analytics import snapshot,display_date
from core.mastery import mastery_label

st.title('Progress')
st.caption('See what your recorded practice says about your learning.')
if not repo().documents():
    empty_state('Your learning story starts here','Create a Study Kit, then review cards and answer questions to build your progress.')
    st.stop()
stats = snapshot(repo())
with st.container(horizontal=True):
    st.metric('Overall Mastery',f"{stats['mastery']:.0f}%" if stats['mastery'] is not None else 'Not assessed',border=True)
    st.metric('Quiz Accuracy',f"{stats['accuracy']:.0f}%" if stats['accuracy'] is not None else 'Not assessed',border=True)
    st.metric('Cards Reviewed',stats['reviewed'],border=True)
    st.metric('Study Materials',stats['materials'],border=True)
st.caption('Mastery is a transparent practice heuristic, not a scientifically validated measure. Unstudied concepts contribute zero once practice has begun.')
concepts = stats['concepts']
if focus := st.session_state.get('focus_concept'):
    concept = next((c for c in concepts if c['id'] == focus),None)
    if concept:
        with st.container(border=True):
            st.subheader('Review '+concept['name'])
            st.write(concept['payload']['explanation'])
            source_evidence(concept['payload'],repo().document(concept['document_id']),True)
st.subheader('Concept Mastery')
if concepts:
    rows = [{'Concept':c['name'],'Material':c['document_title'],'Mastery':c['score'] if c['evidence_count'] else None,
             'Status':mastery_label(c['score']) if c['evidence_count'] else 'Not studied yet','Actions':c['evidence_count']}
            for c in sorted(concepts,key=lambda c:(c['document_title'],c['name']))]
    st.dataframe(pd.DataFrame(rows),hide_index=True,column_config={'Mastery':st.column_config.ProgressColumn(
        'Mastery',min_value=0,max_value=100,format='%.0f%%')})
left,right = st.columns(2)
with left:
    st.subheader('Weak Areas')
    weak = [c for c in concepts if c['evidence_count'] and c['score'] < 40]
    if not weak:
        st.caption('No weak areas recorded yet. Quiz results and card reviews will identify them.')
    for c in weak[:8]:
        with st.container(border=True):
            st.write(c['name']); st.badge('Needs Revision',color='orange')
            if st.button('Review Concept',key=f"weak_review_{c['id']}"):
                st.session_state.focus_concept = c['id']; st.rerun()
            with st.container(horizontal=True):
                if st.button('Generate Another Question',key=f"weak_quiz_{c['id']}"):
                    st.session_state.quiz_focus = c['id']; st.session_state.pop('quiz_session',None)
                    select_document(c['document_id'],'quiz')
                if st.button('Create Flashcards',key=f"weak_card_{c['id']}"):
                    from services.study_service import add_concept_flashcard
                    with action():
                        add_concept_flashcard(repo(),c['document_id'],c['id'])
                        st.toast('A revision card was added.')
with right:
    st.subheader('Strong Areas')
    strong = [c for c in concepts if c['evidence_count'] and c['score'] >= 70]
    if not strong:
        st.caption('Keep practicing. Strong areas appear when enough successful actions are recorded.')
    for c in sorted(strong,key=lambda c:c['score'],reverse=True)[:8]:
        st.caption(f"{c['name']} · {c['score']:.0f}% · {mastery_label(c['score'])}")
st.subheader('Quiz History')
if stats['attempts']:
    st.dataframe(pd.DataFrame([{'Date':display_date(a['created_at']),'Material':a['title'],'Score':f"{a['correct']}/{a['total']}",
                               'Accuracy':a['accuracy'],'Difficulty':a['difficulty']} for a in stats['attempts']]),hide_index=True)
else:
    st.caption('Your completed quizzes will appear here.')
st.subheader('Flashcard Progress')
st.caption('Due is a review schedule count. It can overlap the mastery groups below.')
with st.container(horizontal=True):
    st.metric('Due',stats['due'],border=True)
    st.metric('Learning',sum(c['state']['reviews'] > 0 and c['mastery'] < 70 for c in stats['cards']),border=True)
    st.metric('Strong',sum(70 <= c['mastery'] < 90 for c in stats['cards']),border=True)
    st.metric('Mastered',sum(c['mastery'] >= 90 for c in stats['cards']),border=True)
