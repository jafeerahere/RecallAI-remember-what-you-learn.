import streamlit as st
from utils.ui import repo,action,active_material
from utils.config import SUMMARY_MODEL,EMBEDDING_MODEL,db_path,processing_location

st.title('Settings')
st.caption('Set your study defaults and inspect optional system information.')
preferences = repo().preferences()
with st.form('settings_form'):
    st.subheader('Study Preferences')
    depth = st.selectbox('Default Study Depth',['Quick','Standard','Deep'],index=['Quick','Standard','Deep'].index(preferences['depth']))
    length = st.selectbox('Default Quiz Length',[5,10,15],index=[5,10,15].index(preferences['quiz_length']))
    difficulty = st.selectbox('Default Quiz Difficulty',['Adaptive','Easy','Medium','Hard'],index=['Adaptive','Easy','Medium','Hard'].index(preferences['difficulty']))
    cards = st.selectbox('Flashcards per Study Kit',[5,10,20],index=[5,10,20].index(preferences['flashcards']))
    generation = st.selectbox('Generation',['Concise','Balanced','Detailed'],index=['Concise','Balanced','Detailed'].index(preferences['generation']))
    feedback = st.selectbox('Quiz feedback',['After submission','Immediate'],index=['After submission','Immediate'].index(preferences['feedback']))
    with st.expander('Advanced Settings'):
        override = st.checkbox('Override automatic chunk sizing',value=preferences['chunk_size'] is not None)
        chunk = st.slider('Chunk size',200,440,preferences['chunk_size'] or 400,20)
        retrieval = st.slider('Retrieval top-k',1,8,preferences['retrieval_k'])
        st.caption('Summarization: '+SUMMARY_MODEL)
        st.caption('Embeddings: '+EMBEDDING_MODEL)
        st.caption('Generation uses two beams, no repeated 3-grams and per-chunk output limits of 64, 128 or 192 tokens.')
    if st.form_submit_button('Save preferences',type='primary'):
        with action():
            repo().save_preferences({'depth':depth,'quiz_length':length,'difficulty':difficulty,'flashcards':cards,
                                    'generation':generation,'feedback':feedback,'chunk_size':chunk if override else None,'retrieval_k':retrieval})
            st.success('Your study preferences are saved.')
st.subheader('Privacy and storage')
st.badge('Processing: '+processing_location(),color='violet')
st.write('The implemented models run on the app server. First use may download weights from Hugging Face. Text is stored in the app Library; no external answer API is configured.')
st.caption('This version uses one shared profile. Anyone with access to this app can view it. Community Cloud storage is temporary, so export material you need to keep. Authentication and cloud sync are future work.')
with st.expander('Developer/System Details'):
    st.caption('Database: '+str(db_path()))
    st.write('Notes → preprocessing → sentence-aware chunks → summary and concepts → questions and flashcards → source support → retrieval, study and progress')
    st.write('Support checks combine passage provenance, an exact concept span and answer/source cosine similarity of at least 0.20. This threshold is a heuristic, not a correctness guarantee.')
    st.write('Mastery uses the latest five recorded actions, weighted 1 to n from oldest to newest. Quiz correctness is 0 or 1; flashcard ratings Again, Hard, Good and Easy are 0, 0.4, 0.8 and 1. Subtract 5 per consecutive zero, capped at 15, then multiply by min(total actions / 5, 1). Clamp to 0–100.')
    document = active_material()
    kit = repo().kit(document['id']) if document else None
    if kit:
        st.write({'Sentences':kit['sentences'],'Tokens':kit['tokens'],'Summary chunks':kit['chunks']})
        import pandas as pd
        st.dataframe(pd.DataFrame(kit['timings'].items(),columns=['Stage','Seconds']),hide_index=True)
        questions = kit['quiz']
        with st.container(horizontal=True):
            st.metric('Generated questions',len(questions),border=True)
            st.metric('Passing source-support checks',sum(q['verified'] for q in questions),border=True)
            st.metric('Average support score',f"{sum(q['support_score'] for q in questions)/len(questions):.2f}" if questions else 'N/A',border=True)
        st.caption('Question generation time: '+f"{kit['timings']['Question generation']:.2f} seconds")
        st.caption('Times are measured from the saved generation run. First runs include downloads and initialization.')
        st.subheader('Optional summary evaluation')
        st.caption('ROUGE measures reference overlap. Semantic similarity is not factual accuracy.')
        reference = st.text_area('Human reference summary',key='evaluation_reference')
        if st.button('Evaluate summary',key='evaluate_summary'):
            if not reference.strip():
                st.info('Enter a reference summary first. Scores are only calculated against an actual reference.')
            else:
                with action('Summary evaluation could not finish. Try a shorter reference.'):
                    from rouge_score import rouge_scorer
                    from core.embeddings import encode_texts
                    scores = rouge_scorer.RougeScorer(['rouge1','rouge2','rougeL'],use_stemmer=True).score(reference,kit['summary'])
                    st.dataframe(pd.DataFrame({k:{'Precision':v.precision,'Recall':v.recall,'F1':v.fmeasure} for k,v in scores.items()}).T)
                    vectors = encode_texts((reference,kit['summary']))
                    st.metric('Reference semantic similarity',f'{float(vectors[0] @ vectors[1]):.3f}')
                    st.caption('Long evaluation texts can exceed the embedding context. Use concise references.')
    st.subheader('Scope and roadmap')
    st.write('Implemented: English text and document extraction, study kits, retrieval, local persistence, practice, scheduling, learning history and exports.')
    st.write('Future: authentication, cloud sync, lecture/audio transcription, YouTube import, meeting tools, team collaboration and a mobile app. OCR, essay grading and multilingual study are not implemented.')
