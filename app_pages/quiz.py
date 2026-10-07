import uuid
import streamlit as st
from utils.ui import repo,require_kit,source_evidence,action
from services.study_service import start_quiz
from core.quiz_engine import grade_answer
from core.export import results_csv

st.title('Quiz')
st.caption('Test your recall and use the feedback to plan your next review.')
document,kit = require_kit('Ready when you are','Create a Study Kit to prepare source-based practice questions.')
preferences = {**repo().preferences(), **kit.get('preferences',{})}
state = st.session_state.get('quiz_session')
if state and state['document_id'] != document['id']:
    state = None
st.subheader(document['title'])

def answer_input(q,i,quiz_id):
    key = f'answer_{quiz_id}_{i}'
    if q['type'] == 'Short Answer':
        return st.text_input('Write the concept name',key=key,persist_state='session')
    return st.radio('Choose your answer',q['options'],index=None,key=key,persist_state='session')

def show_result(attempt):
    st.success(f"Score: {attempt['correct']} / {attempt['total']} · Accuracy: {attempt['accuracy']:.1f}%")
    st.progress(attempt['accuracy']/100)
    for i,row in enumerate(attempt['answers'],1):
        q = row['question']
        with st.expander(f"{i}. {'Correct' if row['correct'] else 'Incorrect'} · {q['concept']}",expanded=True):
            st.write(q['question'])
            st.write('Your answer: '+row['answer']); st.write('Correct Answer: '+q['correct_answer'])
            st.write(q['explanation']); source_evidence(q,document)
            if not row['correct']:
                st.badge('Needs Revision',color='orange')
                with st.container(horizontal=True):
                    if st.button('Review Concept',key=f"review_concept_{i}"):
                        st.session_state.focus_concept = q['concept_id']
                        st.switch_page('app_pages/progress.py')
                    if st.button('Generate Another Question',key=f"another_{i}"):
                        with action('Could not prepare a new question for this concept.'):
                            seed = len(repo().attempts(document['id']))
                            quiz_id,questions = start_quiz(repo(),document['id'],1,'Adaptive',seed=seed,focus=q['concept_id'])
                            st.session_state.quiz_session = {'quiz_id':quiz_id,'document_id':document['id'],'questions':questions,
                                'difficulty':'Adaptive','feedback':'After submission','attempt_id':uuid.uuid4().hex,'answers':{},'position':0}
                            st.rerun()
                    if st.button('Create Flashcards',key=f"new_cards_{i}"):
                        from services.study_service import add_concept_flashcard
                        with action():
                            add_concept_flashcard(repo(),document['id'],q['concept_id'])
                            st.toast('A source-based card was added to your deck.')
    st.download_button('Export results · CSV',results_csv(attempt),'recallai-quiz-results.csv','text/csv',key='quiz_results_export',on_click='ignore')

if not state:
    if not kit['quiz']:
        st.info('Add more distinct concepts to this material, then regenerate its Study Kit.')
    else:
        with st.form('quiz_preferences'):
            length = st.selectbox('Questions',[5,10,15],index=[5,10,15].index(preferences['quiz_length']))
            difficulty = st.selectbox('Difficulty',['Adaptive','Easy','Medium','Hard'],index=['Adaptive','Easy','Medium','Hard'].index(preferences['difficulty']))
            types = st.multiselect('Question types',['MCQ','True / False','Short Answer'],default=['MCQ','True / False','Short Answer'])
            feedback = st.selectbox('Feedback',['After submission','Immediate'],index=['After submission','Immediate'].index(preferences['feedback']))
            if st.form_submit_button('Start quiz',type='primary'):
                with action('Could not prepare this quiz. Try different question settings.'):
                    focus = st.session_state.pop('quiz_focus',None)
                    seed = len(repo().attempts(document['id']))
                    quiz_id,questions = start_quiz(repo(),document['id'],1 if focus else length,difficulty,types,seed,focus)
                    st.session_state.quiz_session = {'quiz_id':quiz_id,'document_id':document['id'],'questions':questions,
                        'difficulty':difficulty,'feedback':feedback,'attempt_id':uuid.uuid4().hex,'answers':{},'position':0}
                    st.rerun()
        st.caption('Adaptive mode prioritizes weak concepts. Strong concepts move toward short-answer recall. Requested lengths may be reduced when there are not enough reliable source questions.')
elif state.get('completed'):
    attempt = repo().attempt(state['attempt_id'])
    if attempt:
        show_result(attempt)
    if st.button('Try another quiz',type='primary'):
        st.session_state.pop('quiz_session',None); st.rerun()
else:
    questions = state['questions']
    if state['feedback'] == 'After submission':
        answers = {}
        with st.form('quiz_answers'):
            for i,q in enumerate(questions):
                with st.container(border=True):
                    st.caption(f"QUESTION {i+1} / {len(questions)} · {q['type']} · {q['difficulty']}")
                    st.write(q['question'])
                    answers[i] = answer_input(q,i,state['quiz_id'])
            if st.form_submit_button('Submit answers',type='primary'):
                with action('Could not save your quiz results. Please try again.'):
                    repo().submit_quiz(state['quiz_id'],answers,state['difficulty'],state['attempt_id'])
                    state['completed'] = True
                    st.session_state.quiz_session = state
                    st.rerun()
    else:
        i = state['position']; q = questions[i]
        st.progress(i/len(questions),text=f'Question {i+1} of {len(questions)}')
        st.caption(q['type']+' · '+q['difficulty']); st.write(q['question'])
        with st.form('immediate_answer'):
            answer = answer_input(q,i,state['quiz_id'])
            if st.form_submit_button('Check answer',disabled=i in state['answers']):
                if answer is None or not str(answer).strip():
                    st.warning('Enter an answer first.')
                else:
                    state['answers'][i] = answer
                    st.session_state.quiz_session = state
                    st.rerun()
        if i in state['answers']:
            passed = grade_answer(q,state['answers'][i])
            st.success('Correct') if passed else st.warning('Incorrect')
            st.write('Correct Answer: '+q['correct_answer']); st.write(q['explanation']); source_evidence(q,document)
            if st.button('Finish quiz' if i == len(questions)-1 else 'Next question',type='primary'):
                with action('Could not save this quiz. Please try again.'):
                    if i == len(questions)-1:
                        repo().submit_quiz(state['quiz_id'],state['answers'],state['difficulty'],state['attempt_id'])
                        state['completed'] = True
                    else:
                        state['position'] += 1
                    st.session_state.quiz_session = state
                    st.rerun()
        st.caption('Progress is saved after the complete quiz is submitted.')
attempts = repo().attempts(document['id'])
if attempts:
    with st.expander('Previous scores'):
        from services.analytics import display_date
        for attempt in attempts[:10]:
            st.caption(f"{display_date(attempt['created_at'])} · {attempt['correct']}/{attempt['total']} · {attempt['accuracy']:.0f}% · {attempt['difficulty']}")
