from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import os

def local_now():
    return datetime.now(ZoneInfo(os.getenv('RECALLAI_TIMEZONE','Asia/Kolkata')))

def greeting(now=None):
    hour = (now or local_now()).hour
    return 'Good morning' if 5 <= hour < 12 else 'Good afternoon' if 12 <= hour < 17 else 'Good evening'

def snapshot(repo, document_id=None):
    concepts, cards, attempts, events = repo.concepts(document_id),repo.cards(document_id),repo.attempts(document_id),repo.events(document_id)
    total = sum(a['total'] for a in attempts)
    now = local_now()
    end = (now+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
    return {'concepts':concepts,'cards':cards,'attempts':attempts,'events':events,
            'mastery':round(sum(c['score'] for c in concepts)/len(concepts),1) if concepts and events else None,
            'accuracy':round(100*sum(a['correct'] for a in attempts)/total,1) if total else None,
            'due':sum(datetime.fromisoformat(c['state']['next_review']) < end for c in cards),
            'weak':sum(c['evidence_count'] > 0 and c['score'] < 40 for c in concepts),
            'reviewed':sum(e['kind'] == 'flashcard' for e in events),
            'materials':1 if document_id and repo.document(document_id) else len(repo.documents()) if not document_id else 0}

def display_date(value):
    if not value:
        return 'Not studied yet'
    return datetime.fromisoformat(value).astimezone(local_now().tzinfo).strftime('%d %b %Y, %I:%M %p')
