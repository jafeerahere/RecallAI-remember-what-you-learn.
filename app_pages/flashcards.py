from datetime import datetime,timezone
import streamlit as st
from utils.ui import repo,require_kit,source_evidence,action
from core.mastery import mastery_label
from core.export import flashcards_csv
from services.analytics import display_date

st.title('Flashcards')
st.caption('Try to recall the answer, then tell RecallAI how it went.')
document,kit = require_kit('Nothing to review yet','Create a Study Kit and RecallAI will turn your material into flashcards.')
cards = repo().cards(document['id'])
due = [c for c in cards if datetime.fromisoformat(c['state']['next_review']) <= datetime.now(timezone.utc)]
st.subheader(document['title'])
st.caption(f'{len(due)} cards ready to review · {len(cards)} in this deck')
mode = st.segmented_control('Review deck',['Due now','All cards'],default='Due now',key='card_deck',persist_state='session') or 'Due now'
deck = due if mode == 'Due now' else cards
if not deck:
    st.success('You are up to date. Choose All cards to practice ahead of schedule.')
else:
    card_ids = [c['id'] for c in deck]
    if st.session_state.get('review_card_id') not in card_ids:
        st.session_state.review_card_id = card_ids[0]
    selected = st.selectbox('Choose a card',card_ids,format_func=lambda key:next(c['payload']['concept'] for c in deck if c['id'] == key),
                            key='review_card_id',persist_state='session')
    row = next(c for c in deck if c['id'] == selected)
    card = row['payload']
    with st.container(border=True):
        st.caption(card['concept']+' · '+row['state']['difficulty'])
        st.write(card['question'])
        st.caption(f"{row['state']['reviews']} reviews · Next review {display_date(row['state']['next_review'])}")
        if row['state']['reviews']:
            st.caption(f"Mastery {row['mastery']:.0f}% · {mastery_label(row['mastery'])}")
        if st.button('Show Answer',key=f"show_{selected}",icon=':material/visibility:'):
            st.session_state.revealed_card = selected
        if st.session_state.get('revealed_card') == selected:
            st.subheader(card['answer'])
            source_evidence(card,document)
            with st.container(horizontal=True):
                for rating in ['Again','Hard','Good','Easy']:
                    if st.button(rating,key=f'rate_{rating}_{selected}'):
                        with action('Could not save your review. Please try again.'):
                            repo().review_card(selected,rating)
                            st.session_state.revealed_card = None
                            st.session_state.notice = 'Review saved. Your next review is scheduled.'
                            st.rerun()
st.download_button('Export flashcards · CSV',flashcards_csv(cards),'recallai-flashcards.csv','text/csv',on_click='ignore')
