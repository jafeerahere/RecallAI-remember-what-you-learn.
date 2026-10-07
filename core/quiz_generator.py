import random
import re
from core.flashcards import select_facts,spread_items
from core.keywords import load_embeddings

def generate_quiz(text, keywords, count=5):
    facts = spread_items(select_facts(text, keywords),200)
    if len(facts) < 4:
        return []
    answers = [f['answer'] for f in facts]
    embeddings = load_embeddings().encode(answers, normalize_embeddings=True)
    quiz = []
    for i, fact in enumerate(facts):
        ranked = sorted(range(len(facts)), key=lambda j: float(embeddings[i] @ embeddings[j]), reverse=True)
        candidates = [answers[j] for j in ranked if j != i and not re.search(r'(?<!\w)' + re.escape(answers[j]) + r'(?!\w)', fact['source'], re.I)
                      and answers[j].lower() not in fact['answer'].lower() and fact['answer'].lower() not in answers[j].lower()]
        distractors = candidates[:3]
        if len(distractors) != 3:
            continue
        options = [fact['answer']] + distractors
        random.Random(fact['source']).shuffle(options)
        quiz.append({**fact, 'options': options, 'correct_answer': fact['answer'],
                     'distractor_candidates':candidates,
                     'explanation': 'The notes state: ' + fact['source']})
    return spread_items(quiz,count)
