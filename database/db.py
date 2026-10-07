from contextlib import contextmanager
import sqlite3
from pathlib import Path

SCHEMA = '''
CREATE TABLE IF NOT EXISTS documents (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, file_type TEXT NOT NULL, content_hash TEXT UNIQUE NOT NULL,
 text TEXT NOT NULL, segments TEXT NOT NULL, warnings TEXT NOT NULL, word_count INTEGER NOT NULL,
 created_at TEXT NOT NULL, last_studied TEXT NOT NULL, deleted_at TEXT);
CREATE TABLE IF NOT EXISTS study_kits (
 id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
 fingerprint TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(document_id,fingerprint));
CREATE TABLE IF NOT EXISTS document_chunks (
 id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
 text TEXT NOT NULL, location TEXT NOT NULL, embedding TEXT NOT NULL, model TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS concepts (
 id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
 name TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS flashcards (
 id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
 concept_id TEXT REFERENCES concepts(id) ON DELETE CASCADE, payload TEXT NOT NULL,
 state TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS learning_events (
 id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
 concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE, kind TEXT NOT NULL,
 value REAL NOT NULL CHECK(value BETWEEN 0 AND 1), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS flashcard_reviews (
 id TEXT PRIMARY KEY REFERENCES learning_events(id) ON DELETE CASCADE,
 card_id TEXT NOT NULL REFERENCES flashcards(id) ON DELETE CASCADE, rating TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS mastery_scores (
 concept_id TEXT PRIMARY KEY REFERENCES concepts(id) ON DELETE CASCADE, score REAL NOT NULL,
 evidence_count INTEGER NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS quizzes (
 id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
 payload TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS quiz_questions (
 id TEXT PRIMARY KEY, quiz_id TEXT NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
 concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE, position INTEGER NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS quiz_attempts (
 id TEXT PRIMARY KEY, quiz_id TEXT NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
 document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE, correct INTEGER NOT NULL,
 total INTEGER NOT NULL, accuracy REAL NOT NULL, difficulty TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS user_answers (
 attempt_id TEXT NOT NULL REFERENCES quiz_attempts(id) ON DELETE CASCADE,
 question_id TEXT NOT NULL REFERENCES quiz_questions(id) ON DELETE CASCADE,
 answer TEXT NOT NULL, correct INTEGER NOT NULL, PRIMARY KEY(attempt_id,question_id));
CREATE TABLE IF NOT EXISTS chat_messages (
 id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
 role TEXT NOT NULL, content TEXT NOT NULL, sources TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS preferences (profile TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS events_concept ON learning_events(concept_id,created_at);
CREATE INDEX IF NOT EXISTS attempts_document ON quiz_attempts(document_id,created_at);
PRAGMA user_version=1;
'''

@contextmanager
def connection(path):
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        with conn:
            yield conn
    finally:
        conn.close()

def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connection(path) as conn:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.executescript(SCHEMA)
