import re
from core.preprocessing import load_nlp

def select_facts(text, keywords):
    facts, seen = [], set()
    generic = {'text', 'language', 'a word', 'word', 'words', 'a token', 'token', 'tokens',
               'this task', 'this process', 'the model', 'a model', 'information', 'content', 'a statement',
               'learning','process','system','a system','these models','a field','a sentence'}
    doc = load_nlp()(text)
    for sentence in doc.sents:
        source = sentence.text.strip()
        if not 6 <= len(source.split()) <= 80:
            continue
        # Definition subjects and noun phrases give meaningful cloze targets.
        candidates = []
        match = re.match(r'^(.{3,65}?)\s+(?:is|are|refers to|uses|allows|enables|identifies|removes|measures|produces|represents|evaluates|schedules|compares|learns|seeks|studies|predicts|adjusts|applies|generates|selects|divides|combines)\s', source, re.I)
        if match and ',' not in match.group(1) and len(match.group(1).split()) <= 6 and not re.match(r'^(?:During|Unlike|For|This|That|These)\b',match.group(1)):
            candidates.append(match.group(1))
        candidates.extend(p for p, _ in keywords)
        for answer in candidates:
            answer = answer.strip()
            pattern = re.compile(r'(?<!\w)' + re.escape(answer) + r'(?!\w)', re.I)
            if answer.lower() in seen or answer.lower() in generic or len(answer) < 3 or not pattern.search(source):
                continue
            question = pattern.sub('______', source)
            facts.append({'question': 'Which concept completes this statement?\n\n' + question,
                          'answer': pattern.search(source).group(), 'source': source})
            seen.add(answer.lower())
            break
    return facts

def spread_items(items, count):
    """Cover the whole material rather than selecting only its opening paragraphs."""
    if len(items) <= count:
        return items
    if count <= 1:
        return items[:max(0,count)]
    return [items[round(i*(len(items)-1)/(count-1))] for i in range(count)]

def generate_flashcards(text, keywords, count=10):
    return spread_items(select_facts(text, keywords),count)
