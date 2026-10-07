from core.quiz_engine import adapt_questions,validate_question,grade_answer
import pytest

def pool():
    return [{'id':f'q{i}','concept_id':f'c{i}','concept':f'Concept {i}',
             'question':f'Which concept fits? ______ describes process {i}.','answer':f'Concept {i}',
             'correct_answer':f'Concept {i}','source':f'Concept {i} describes process {i}.',
             'explanation':f'Concept {i} describes process {i}.','options':[f'Concept {i}','Other A','Other B','Other C'],
             'distractor_candidates':['Other A','Other B','Other C','Far A','Far B','Far C'],
             'verified':True,'support_score':.5} for i in range(5)]

def test_adaptive_priority_and_difficulty():
    concepts = [{'id':f'c{i}','score':90 if i == 0 else 10 if i == 2 else 50,'evidence_count':5} for i in range(5)]
    questions = adapt_questions(pool(),concepts,5,'Adaptive')
    assert questions[0]['concept_id'] == 'c2'
    assert any(q['concept_id'] == 'c0' and q['type'] == 'Short Answer' and q['difficulty'] == 'Hard' for q in questions)
    assert all(validate_question(q) for q in questions)
    focused = adapt_questions(pool(),concepts,1,'Adaptive',focus='c2')
    assert len(focused) == 1 and focused[0]['concept_id'] == 'c2'

def test_question_validation_and_short_grading():
    with pytest.raises(ValueError,match='quiz length'):
        adapt_questions(pool(),[],0,'Easy')
    with pytest.raises(ValueError,match='supported difficulty'):
        adapt_questions(pool(),[],5,'Unknown')
    with pytest.raises(ValueError,match='at least one'):
        adapt_questions(pool(),[],types=[])
    bad = {**pool()[0],'type':'MCQ','options':['same','Same','other','different']}
    assert not validate_question(bad)
    q = {**pool()[0],'type':'Short Answer','correct_answer':'Tokenization'}
    assert grade_answer(q,'the tokenization!')
    assert not grade_answer(q,'Not tokenization')
    assert not grade_answer(q,'embeddings')
