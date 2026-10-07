import streamlit as st
from utils.ui import repo,require_kit,action
from services.chat_service import answer_question
from core.export import location_label

st.title('Ask RecallAI')
st.caption('Ask about your material. Answers quote relevant source passages.')
document,kit = require_kit('Start a conversation with your material','Create a Study Kit and ask RecallAI to find explanations and evidence.')
st.subheader(document['title'])
messages = repo().chat(document['id'])
for message in messages:
    with st.chat_message(message['role']):
        st.write(message['content'])
        if message['sources']:
            with st.expander('Sources'):
                for source in message['sources']:
                    st.caption(document['title']+' · '+location_label(source['location']))
                    st.write(source['text'])
prompt = st.chat_input('Ask about this material...',key='ask_prompt',submit_mode='disable',max_chars=2000)
if not messages:
    examples = ['What does attention mean?','What is the difference between BERT and GPT?','What are the five most important concepts?','What should I revise first?']
    with st.container(horizontal=True):
        for i,example in enumerate(examples):
            if st.button(example,key=f'ask_example_{i}'):
                prompt = example
if prompt:
    with st.chat_message('user'):
        st.write(prompt)
    with st.chat_message('assistant'):
        with action('Could not search your material. Try again in a moment.'):
            with st.status('Finding relevant passages...',expanded=False) as status:
                response = answer_question(repo(),document['id'],prompt,repo().preferences()['retrieval_k'])
                repo().save_chat(document['id'],prompt,response)
                status.update(label='Sources checked',state='complete')
            st.rerun()
