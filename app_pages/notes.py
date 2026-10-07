import streamlit as st
from utils.ui import require_kit,render_notes,render_concepts,render_tree
from core.export import notes_markdown

st.title('AI Notes')
st.caption('Structured source-based notes, ready for your next revision session.')
document,kit = require_kit('Your notes start here','Create a Study Kit to turn your learning material into organized notes.')
st.subheader(document['title'])
notes,concepts,map_tab = st.tabs(['Structured notes','Concepts','Knowledge Map'],key='notes_tabs',on_change='rerun')
if notes.open:
    with notes:
        render_notes(document,kit)
if concepts.open:
    with concepts:
        render_concepts(document,kit,'notes_concept')
if map_tab.open:
    with map_tab:
        render_tree(document,kit)
st.download_button('Export notes · Markdown',notes_markdown(document,kit),'recallai-notes.md','text/markdown',on_click='ignore')
