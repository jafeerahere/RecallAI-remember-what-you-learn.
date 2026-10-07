"""A local default profile. Each operation uses its own atomic connection."""
from datetime import datetime, timezone
import hashlib
import json
import uuid
from database.db import initialize, connection
from core.mastery import mastery_score, schedule_review
from utils.config import DEFAULTS, validate_preferences

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def stable_id(*parts):
    return hashlib.sha256('\x1f'.join(str(p) for p in parts).encode()).hexdigest()[:24]

def concept_id(document_id, name):
    return stable_id(document_id, name.lower().strip())

class Repository:
    def __init__(self, path):
        self.path = str(path)
        initialize(self.path)

    def documents(self, include_deleted=False):
        with connection(self.path) as db:
            return [dict(row) for row in db.execute('SELECT id,title,file_type,word_count,created_at,last_studied,deleted_at FROM documents ' +
                ('' if include_deleted else 'WHERE deleted_at IS NULL ') + 'ORDER BY last_studied DESC')]

    def document(self, identifier):
        with connection(self.path) as db:
            row = db.execute('SELECT * FROM documents WHERE id=? AND deleted_at IS NULL',(identifier,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result['segments'] = json.loads(result['segments']); result['warnings'] = json.loads(result['warnings'])
        return result

    def save_document(self, material):
        identifier, now = uuid.uuid4().hex, now_iso()
        with connection(self.path) as db:
            row = db.execute('SELECT id,deleted_at FROM documents WHERE content_hash=?',(material.content_hash,)).fetchone()
            if row:
                db.execute('UPDATE documents SET deleted_at=NULL,last_studied=? WHERE id=?',(now,row['id']))
                return row['id'], True
            db.execute('INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,NULL)',
                       (identifier,material.title,material.file_type,material.content_hash,material.text,
                        json.dumps(material.segments),json.dumps(material.warnings),len(material.text.split()),now,now))
        return identifier, False

    def rename(self, identifier, title):
        title = title.strip()
        if not title or len(title) > 200:
            raise ValueError('Use a title between 1 and 200 characters.')
        with connection(self.path) as db:
            db.execute('UPDATE documents SET title=? WHERE id=?',(title,identifier))

    def touch(self, identifier):
        with connection(self.path) as db:
            db.execute('UPDATE documents SET last_studied=? WHERE id=?',(now_iso(),identifier))

    def trash(self, identifier):
        with connection(self.path) as db:
            db.execute('UPDATE documents SET deleted_at=? WHERE id=?',(now_iso(),identifier))

    def restore(self, identifier):
        with connection(self.path) as db:
            db.execute('UPDATE documents SET deleted_at=NULL WHERE id=?',(identifier,))

    def preferences(self):
        with connection(self.path) as db:
            row = db.execute('SELECT payload FROM preferences WHERE profile=?',('local',)).fetchone()
        return {**DEFAULTS, **(json.loads(row[0]) if row else {})}

    def save_preferences(self, prefs):
        payload = validate_preferences(prefs)
        with connection(self.path) as db:
            db.execute('INSERT INTO preferences VALUES (?,?) ON CONFLICT(profile) DO UPDATE SET payload=excluded.payload',('local',json.dumps(payload)))

    def active_document(self):
        with connection(self.path) as db:
            row = db.execute('SELECT payload FROM preferences WHERE profile=?',('workspace',)).fetchone()
        return json.loads(row[0]).get('document_id') if row else None

    def set_active_document(self, identifier):
        with connection(self.path) as db:
            db.execute('INSERT INTO preferences VALUES (?,?) ON CONFLICT(profile) DO UPDATE SET payload=excluded.payload',
                       ('workspace',json.dumps({'document_id':identifier})))

    def kit(self, document_id, fingerprint=None):
        with connection(self.path) as db:
            row = db.execute('SELECT payload FROM study_kits WHERE document_id=? ' + ('AND fingerprint=? ' if fingerprint else '') +
                             'ORDER BY created_at DESC LIMIT 1', (document_id,fingerprint) if fingerprint else (document_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def save_kit(self, identifier, fingerprint, kit, chunks):
        with connection(self.path) as db:
            db.execute('INSERT INTO study_kits VALUES (?,?,?,?,?) ON CONFLICT(document_id,fingerprint) DO UPDATE SET payload=excluded.payload,created_at=excluded.created_at',
                       (stable_id(identifier,fingerprint),identifier,fingerprint,json.dumps(kit),now_iso()))
            for concept in kit['concepts']:
                db.execute('INSERT INTO concepts VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,payload=excluded.payload',
                           (concept['id'],identifier,concept['name'],json.dumps(concept)))
            db.execute('UPDATE flashcards SET active=0 WHERE document_id=?',(identifier,))
            for card in kit['cards']:
                state = {'next_review':now_iso(),'reviews':0,'success_count':0,'interval_days':0,'difficulty':card['difficulty']}
                db.execute('INSERT INTO flashcards VALUES (?,?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,active=1',
                           (card['id'],identifier,card['concept_id'],json.dumps(card),json.dumps(state)))
            db.execute('DELETE FROM document_chunks WHERE document_id=?',(identifier,))
            for chunk in chunks:
                db.execute('INSERT INTO document_chunks VALUES (?,?,?,?,?,?)',
                           (chunk['id'],identifier,chunk['text'],json.dumps(chunk['location']),json.dumps(chunk['embedding']),chunk['model']))
            db.execute('UPDATE documents SET last_studied=? WHERE id=?',(now_iso(),identifier))

    def chunks(self, identifier):
        with connection(self.path) as db:
            rows = db.execute('SELECT * FROM document_chunks WHERE document_id=? ORDER BY rowid',(identifier,)).fetchall()
        return [{**dict(r), 'location':json.loads(r['location']), 'embedding':json.loads(r['embedding'])} for r in rows]

    def concepts(self, identifier=None):
        with connection(self.path) as db:
            rows = db.execute('SELECT c.*, COALESCE(m.score,0) AS score, COALESCE(m.evidence_count,0) AS evidence_count, d.title AS document_title '
                'FROM concepts c JOIN documents d ON d.id=c.document_id LEFT JOIN mastery_scores m ON m.concept_id=c.id '
                'WHERE d.deleted_at IS NULL ' + ('AND c.document_id=? ' if identifier else '') + 'ORDER BY score,c.name', (identifier,) if identifier else ()).fetchall()
        return [{**dict(r),'payload':json.loads(r['payload'])} for r in rows]

    def cards(self, identifier=None):
        with connection(self.path) as db:
            rows = db.execute('SELECT f.*,COALESCE(m.score,0) AS mastery, d.title AS document_title FROM flashcards f '
                              'JOIN documents d ON d.id=f.document_id LEFT JOIN mastery_scores m ON m.concept_id=f.concept_id '
                              'WHERE d.deleted_at IS NULL AND f.active=1 ' + ('AND f.document_id=? ' if identifier else ''), (identifier,) if identifier else ()).fetchall()
        return [{**dict(r),'payload':json.loads(r['payload']),'state':json.loads(r['state'])} for r in rows]

    def _update_mastery(self, db, concept):
        events = [dict(r) for r in db.execute('SELECT value FROM learning_events WHERE concept_id=? ORDER BY created_at,rowid',(concept,))]
        db.execute('INSERT INTO mastery_scores VALUES (?,?,?,?) ON CONFLICT(concept_id) DO UPDATE SET score=excluded.score,evidence_count=excluded.evidence_count,updated_at=excluded.updated_at',
                   (concept,mastery_score(events),len(events),now_iso()))

    def review_card(self, card_id, rating, event_id=None):
        event_id = event_id or uuid.uuid4().hex
        with connection(self.path) as db:
            if db.execute('SELECT 1 FROM learning_events WHERE id=?',(event_id,)).fetchone():
                return
            row = db.execute('SELECT * FROM flashcards WHERE id=? AND active=1',(card_id,)).fetchone()
            if not row:
                raise ValueError('This card is no longer available. Open the current deck.')
            state = schedule_review(json.loads(row['state']),rating)
            value = {'Again':0.,'Hard':.4,'Good':.8,'Easy':1.}[rating]
            db.execute('INSERT INTO learning_events VALUES (?,?,?,?,?,?)',(event_id,row['document_id'],row['concept_id'],'flashcard',value,now_iso()))
            db.execute('INSERT INTO flashcard_reviews VALUES (?,?,?)',(event_id,card_id,rating))
            db.execute('UPDATE flashcards SET state=? WHERE id=?',(json.dumps(state),card_id))
            self._update_mastery(db,row['concept_id'])
            db.execute('UPDATE documents SET last_studied=? WHERE id=?',(now_iso(),row['document_id']))

    def save_quiz(self, identifier, questions):
        quiz_id, now = uuid.uuid4().hex, now_iso()
        with connection(self.path) as db:
            db.execute('INSERT INTO quizzes VALUES (?,?,?,?)',(quiz_id,identifier,json.dumps(questions),now))
            for i, question in enumerate(questions):
                db.execute('INSERT INTO quiz_questions VALUES (?,?,?,?,?)',(stable_id(quiz_id,i),quiz_id,question['concept_id'],i,json.dumps(question)))
        return quiz_id

    def submit_quiz(self, quiz_id, answers, difficulty, attempt_id):
        from core.quiz_engine import grade_answer
        with connection(self.path) as db:
            if db.execute('SELECT 1 FROM quiz_attempts WHERE id=?',(attempt_id,)).fetchone():
                return self.attempt(attempt_id)
            quiz = db.execute('SELECT * FROM quizzes WHERE id=?',(quiz_id,)).fetchone()
            if not quiz:
                raise ValueError('This quiz is no longer available. Start a new one.')
            rows = db.execute('SELECT * FROM quiz_questions WHERE quiz_id=? ORDER BY position',(quiz_id,)).fetchall()
            if len(answers) != len(rows) or any(not str(answers.get(i,'')).strip() for i in range(len(rows))):
                raise ValueError('Answer every question before submitting.')
            correct = sum(grade_answer(json.loads(r['payload']),answers[i]) for i,r in enumerate(rows))
            db.execute('INSERT INTO quiz_attempts VALUES (?,?,?,?,?,?,?,?)',
                       (attempt_id,quiz_id,quiz['document_id'],correct,len(rows),100*correct/len(rows),difficulty,now_iso()))
            for i,row in enumerate(rows):
                passed = grade_answer(json.loads(row['payload']),answers[i])
                db.execute('INSERT INTO user_answers VALUES (?,?,?,?)',(attempt_id,row['id'],str(answers[i]),int(passed)))
                db.execute('INSERT INTO learning_events VALUES (?,?,?,?,?,?)',
                           (stable_id(attempt_id,i),quiz['document_id'],row['concept_id'],'quiz',float(passed),now_iso()))
                self._update_mastery(db,row['concept_id'])
            db.execute('UPDATE documents SET last_studied=? WHERE id=?',(now_iso(),quiz['document_id']))
        return self.attempt(attempt_id)

    def attempt(self, attempt_id):
        with connection(self.path) as db:
            row = db.execute('SELECT * FROM quiz_attempts WHERE id=?',(attempt_id,)).fetchone()
            answers = db.execute('SELECT a.*,q.position,q.payload FROM user_answers a JOIN quiz_questions q ON q.id=a.question_id WHERE attempt_id=? ORDER BY q.position',(attempt_id,)).fetchall()
        return {**dict(row),'answers':[{**dict(a),'question':json.loads(a['payload'])} for a in answers]} if row else None

    def attempts(self, identifier=None):
        with connection(self.path) as db:
            return [dict(r) for r in db.execute('SELECT a.*,d.title FROM quiz_attempts a JOIN documents d ON d.id=a.document_id WHERE d.deleted_at IS NULL ' +
                                               ('AND a.document_id=? ' if identifier else '') + 'ORDER BY a.created_at DESC',(identifier,) if identifier else ())]

    def events(self, identifier=None):
        with connection(self.path) as db:
            return [dict(r) for r in db.execute('SELECT e.* FROM learning_events e JOIN documents d ON e.document_id=d.id WHERE d.deleted_at IS NULL ' +
                                               ('AND e.document_id=? ' if identifier else '') + 'ORDER BY e.created_at,e.rowid',(identifier,) if identifier else ())]

    def chat(self, identifier):
        with connection(self.path) as db:
            rows = db.execute('SELECT * FROM chat_messages WHERE document_id=? ORDER BY id',(identifier,)).fetchall()
        return [{**dict(r),'sources':json.loads(r['sources'])} for r in rows]

    def save_chat(self, identifier, prompt, response):
        with connection(self.path) as db:
            db.execute('INSERT INTO chat_messages(document_id,role,content,sources,created_at) VALUES (?,?,?,?,?)',(identifier,'user',prompt,'[]',now_iso()))
            db.execute('INSERT INTO chat_messages(document_id,role,content,sources,created_at) VALUES (?,?,?,?,?)',
                       (identifier,'assistant',response['answer'],json.dumps(response['sources']),now_iso()))
        self.touch(identifier)

    def search(self, query):
        query = query.strip().lower()
        if not query:
            return []
        escaped = query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        pattern = '%' + escaped + '%'
        with connection(self.path) as db:
            result = []
            for kind, table, column in [('Material','documents','text'),('Concept','concepts','payload'),('Flashcard','flashcards','payload')]:
                if table == 'documents':
                    rows = db.execute("SELECT id AS document_id,title AS label FROM documents WHERE deleted_at IS NULL AND (lower(title) LIKE ? ESCAPE '\\' OR lower(text) LIKE ? ESCAPE '\\')",(pattern,pattern)).fetchall()
                else:
                    label = 'c.name' if table == 'concepts' else 'c.payload'
                    rows = db.execute(f"SELECT c.document_id,{label} AS label FROM {table} c JOIN documents d ON d.id=c.document_id WHERE d.deleted_at IS NULL AND lower(c.{column}) LIKE ? ESCAPE '\\'" + (' AND c.active=1' if table == 'flashcards' else ''),(pattern,)).fetchall()
                for row in rows:
                    label = json.loads(row['label'])['question'] if kind == 'Flashcard' else row['label']
                    result.append({'type':kind,'document_id':row['document_id'],'label':label})
        return result[:100]
