"""Source-based mixed assessment with adaptation from recorded concept mastery."""
import re
import random
from database.repositories import stable_id

def normalize_answer(value):
    value = re.sub(r'[^\w\s]', '', str(value).casefold())
    return re.sub(r'^(?:a|an|the)\s+', '', ' '.join(value.split()))

def grade_answer(question, answer):
    # Short answers expect the concept name, not an unvalidated semantic essay grade.
    return normalize_answer(answer) == normalize_answer(question['correct_answer'])

def validate_question(question):
    if not question.get('source') or not question.get('question') or not question.get('correct_answer'):
        return False
    if question['type'] == 'MCQ':
        options = question.get('options',[])
        return len(options) == 4 and len(set(normalize_answer(o) for o in options)) == 4 and sum(o == question['correct_answer'] for o in options) == 1
    if question['type'] == 'True / False':
        return question['options'] == ['True','False'] and question['correct_answer'] in question['options']
    return question['type'] == 'Short Answer'

def adapt_questions(pool, concepts, length=5, difficulty='Adaptive', types=None, seed=0, focus=None):
    if (length not in [5,10,15] and not (length == 1 and focus)) or difficulty not in ['Adaptive','Easy','Medium','Hard']:
        raise ValueError('Choose a quiz length of 5, 10 or 15 and a supported difficulty.')
    types = ['MCQ','True / False','Short Answer'] if types is None else types
    if not types or any(t not in ['MCQ','True / False','Short Answer'] for t in types):
        raise ValueError('Select at least one supported question type.')
    status = {c['id']:c for c in concepts}
    ordered = sorted(pool, key=lambda q:(0 if q['concept_id'] == focus else 1,
        status.get(q['concept_id'],{}).get('score',0),status.get(q['concept_id'],{}).get('evidence_count',0)))
    # Weak concepts are offered first. Add one alternate form for a concept
    # with repeated mistakes, while keeping question text distinct.
    selected = ordered[:length]
    weak = [q for q in ordered if 0 < status.get(q['concept_id'],{}).get('evidence_count',0) and status[q['concept_id']]['score'] < 40]
    if weak and len(selected) >= 3 and not focus:
        selected[-2] = weak[0]
    questions, seen = [], set()
    for i, base in enumerate(selected):
        row = status.get(base['concept_id'],{})
        level = difficulty if difficulty != 'Adaptive' else ('Hard' if row.get('score',0) >= 70 else 'Medium' if row.get('score',0) >= 40 else 'Easy')
        kind = 'Short Answer' if level == 'Hard' and 'Short Answer' in types else types[(i+seed)%len(types)]
        used_types = {q['type'] for q in questions if q['concept_id'] == base['concept_id']}
        if kind in used_types:
            kind = next((t for t in types if t not in used_types),kind)
        question = dict(base)
        question.update(type=kind,difficulty=level)
        if kind == 'True / False':
            answer = base['correct_answer']
            wrong = next(o for o in base['options'] if o != answer)
            use_true = (i+seed)%2 == 0
            statement = re.sub(r'(?<!\w)' + re.escape(answer) + r'(?!\w)', answer if use_true else wrong,base['source'],flags=re.I)
            question.update(question='According to this material, is this statement correct?\n\n'+statement,
                            options=['True','False'],correct_answer='True' if use_true else 'False',
                            explanation='The supporting passage states: '+base['source'])
        elif kind == 'Short Answer':
            question.update(question=base['question']+'\n\nWrite the concept name.', options=[])
        elif level == 'Easy':
            distractors = base.get('distractor_candidates',[])[-3:]
            if len(distractors) == 3:
                question['options'] = [base['correct_answer']] + distractors
                random.Random(seed+i).shuffle(question['options'])
            question['question'] = base['question'] + '\n\nChoose the concept that fits the passage.'
        elif level == 'Medium':
            question['question'] = base['question'] + '\n\nUse the relationship described in the passage.'
        identity = (question['question'],question['correct_answer'])
        if identity in seen or not validate_question(question):
            continue
        question['id'] = stable_id(base['id'],kind,level,seed)
        seen.add(identity); questions.append(question)
    return questions
