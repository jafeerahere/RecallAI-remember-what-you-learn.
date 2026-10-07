"""Transparent, unvalidated learning heuristic based only on recorded events."""
from datetime import datetime, timedelta, timezone

def mastery_score(events):
    # Most recent five ratings: quiz correct=1/incorrect=0; card Again=0,
    # Hard=.4, Good=.8, Easy=1. Weight oldest->newest by 1..n.
    # Evidence factor=min(total events/5,1). Subtract 5 per consecutive
    # zero-valued event, capped at 15, before applying that factor.
    recent = events[-5:]
    if not recent:
        return 0.0
    values = [float(e['value']) for e in recent]
    mean = sum((i+1)*v for i,v in enumerate(values)) / sum(range(1,len(values)+1))
    mistakes = 0
    for value in reversed(values):
        if value > 0:
            break
        mistakes += 1
    return round(max(0., min(100., (100*mean - min(15,5*mistakes)) * min(1.,len(events)/5))), 1)

def mastery_label(score):
    return 'Needs Work' if score < 40 else 'Learning' if score < 70 else 'Strong' if score < 90 else 'Mastered'

def schedule_review(state, rating, now=None):
    if rating not in ['Again','Hard','Good','Easy']:
        raise ValueError('Choose Again, Hard, Good or Easy.')
    now = now or datetime.now(timezone.utc)
    reviews = state.get('reviews',0) + 1
    previous = state.get('interval_days',0)
    interval = {'Again':0, 'Hard':max(1, previous*1.2), 'Good':1 if reviews == 1 else max(3,previous*2),
                'Easy':4 if reviews == 1 else max(4,previous*2.5)}[rating]
    due = now + (timedelta(minutes=10) if rating == 'Again' else timedelta(days=interval))
    return {'reviews':reviews, 'success_count':state.get('success_count',0)+int(rating in ['Good','Easy']),
            'interval_days':round(interval,2), 'next_review':due.isoformat(),
            'difficulty':'Hard' if rating in ['Again','Hard'] else 'Medium' if rating == 'Good' else 'Easy'}
