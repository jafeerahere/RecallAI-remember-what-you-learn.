from time import perf_counter

def build_study_kit(text, length='Medium', count=5, chunk_size=400, card_count=10, keyword_count=20, progress=None):
    start = perf_counter()
    from core.preprocessing import preprocess
    from core.summarizer import MODEL_ID
    from core.keywords import extract_keywords, EMBEDDING_MODEL
    from core.flashcards import generate_flashcards
    from core.models import LocalSummarizer, SourceQuestionGenerator
    from core.verifier import verify_items
    timings = {}
    def timed(name, fn):
        if progress:
            progress({'Preprocessing':'Reading material...', 'Summarization':'Creating your notes...',
                      'Keyword extraction':'Finding key concepts...', 'Flashcard generation':'Building flashcards...',
                      'Question generation':'Preparing your quiz...', 'Source verification':'Checking source evidence...'}[name])
        t = perf_counter()
        result = fn()
        timings[name] = perf_counter() - t
        return result
    processed = timed('Preprocessing', lambda: preprocess(text))
    clean = processed['text']
    summary, chunks = timed('Summarization', lambda: LocalSummarizer().summarize(clean, length, chunk_size))
    keywords = timed('Keyword extraction', lambda: extract_keywords(clean, keyword_count))
    cards = timed('Flashcard generation', lambda: generate_flashcards(clean, keywords, card_count))
    quiz = timed('Question generation', lambda: SourceQuestionGenerator().generate(clean, keywords, count))
    cards, quiz = timed('Source verification', lambda: (verify_items(cards, clean), verify_items(quiz, clean)))
    timings['Total pipeline'] = perf_counter() - start
    return {'text': clean, 'summary': summary, 'keywords': keywords, 'cards': cards, 'quiz': quiz,
            'sentences': len(processed['sentences']), 'tokens': processed['tokens'], 'chunks': chunks, 'timings': timings,
            'summary_model': MODEL_ID, 'embedding_model': EMBEDDING_MODEL,
            'settings': {'summary_length': length, 'requested_questions': count, 'chunk_budget': chunk_size}}

def score_quiz(questions, answers):
    correct = sum(answers.get(i) == q['correct_answer'] for i, q in enumerate(questions))
    return correct, len(questions), 100 * correct / len(questions) if questions else 0
