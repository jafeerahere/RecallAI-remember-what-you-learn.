# RecallAI upgrade report

## What existed before

The working app had five views, pasted text/TXT intake, local T5 summaries, KeyBERT/MiniLM concepts, source-preserving cloze flashcards and four-option MCQs, scoring, JSON export, optional ROUGE/reference similarity and measured pipeline timings. The active material and answers lived in Streamlit session state, so there was no permanent Library. The six baseline tests passed before changes.

## What changed

1. Replaced the monolithic view selector with nine native pages and shared selection: Home, Study Workspace, AI Notes, Flashcards, Quiz, Ask RecallAI, Progress, Library and Settings.
2. Added real TXT/PDF/DOCX/PPTX extraction, source locations, metadata, file/archive limits and useful failures. Preserved pasted input and expanded the AI/NLP/Transformers sample.
3. Added saved Study Kits with structured section notes, explained concepts, actual-source must-remember categories, takeaways, exam prompts and a reliable section-based Knowledge Map.
4. Replaced normal technical controls with Study Depth and adjustable practice settings. Changing depth suggests appropriate card counts and difficulty; optional system details retain the original evaluation functions.
5. Added persisted semantic passage retrieval and source-based chat with insufficient-evidence abstention.
6. Added SQLite storage, content hashes and kit fingerprints, version reactivation, stable card/concept IDs and transactional learning records.
7. Added hidden-answer cards, Again/Hard/Good/Easy ratings, spaced review scheduling, due counts and real mastery updates.
8. Added mixed assessment, both feedback modes, adaptive concept selection, focused revision, source evidence, revision-card creation and completed quiz history.
9. Added honest analytics, weak/strong areas, native mastery progress columns, current results and learning history.
10. Added persistent Library rename/regenerate/Trash/restore and lexical search across text, concepts and cards.
11. Added actual-content Markdown/CSV/PDF exports, while keeping JSON. PDF content blocks stay together where possible and Unicode fonts are used when available.
12. Added saved preferences, environment configuration, technical logging, native indigo theming, empty states, staged processing and cache-first lazy model loading.
13. Updated dependencies, lock file, privacy exclusions, product documentation and meaningful regression/integration tests.

## Architecture

`app.py` owns Streamlit navigation and shared document selection. `app_pages/` provides the nine views; `utils/ui.py` shares intake, evidence, kits and exports. Services coordinate processing without embedding database logic in pages. The existing NLP modules remain in `core/`, extended by ingestion, retrieval, concepts, assessment, mastery and export modules. SQLite transactions/schema live in `database/db.py`; repositories provide a replaceable storage boundary. Configuration and logging are centralized.

## Exact models and algorithms

- Summary: `Falconsai/text_summarization`, a T5-small summarization checkpoint.
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`, normalized 384-dimensional vectors.
- Linguistic analysis: spaCy `en_core_web_sm` 3.8.0 and NLTK tokenization.
- Concepts: KeyBERT ranking with structured source extraction.
- Questions: deterministic source cloze generation with semantic distractors, plus True/False and concept-name recall variants. A separate generative question model is not configured; the replaceable source-based adapter is the working fallback.
- Chat: local retrieval and quoted evidence. No cloud answer API or conversational LLM is configured.

## Persisted data and location

Default database: `data/private/recallai.sqlite3`, configurable through `RECALLAI_DATA_DIR` and `RECALLAI_DB_PATH`. SQLite WAL and foreign keys are enabled.

Stored entities include documents, chunks/embeddings, kit versions, concepts, cards and schedules, learning events/card ratings, concept mastery, quizzes/questions, completed attempts/answers, chat/messages/sources, preferences and the selected material. Uploaded binary files are not stored. Unsubmitted quiz interaction state remains in the current Streamlit session. Trash is reversible and retains underlying records. Logs rotate under the private data directory.

## Retrieval mechanics

Actual extracted segments are split into complete-sentence chunks fitting the embedding context, normally at most 220 tokens. Chunk text, ID, document ID, source metadata, model ID and vector are persisted. The query is embedded, then NumPy dot products rank normalized vectors by cosine similarity. The default top-k is four; candidates below 0.30 are discarded. Relevant sentences are reranked, and lexical/noun-target checks reject insufficiently supported questions. Answers quote evidence and display actual extraction locations. Special study intents select saved source-backed concepts, practice questions or mastery priorities.

The fallback response is exactly: “I couldn't find enough information about that in this material.” No page/slide location or outside knowledge is invented.

## Source verification

`verify_items` computes normalized answer/source cosine similarity. Passing requires a nonempty answer, an exact answer span in its passage, passage provenance in the normalized material and similarity ≥ 0.20. Labels are Source Supported or Low Support · Review Recommended. Derived quiz forms retain their underlying concept's support result. A consistency check cannot prove truth, and the threshold is not calibrated against a labeled benchmark.

## Exact mastery formula

For the latest `n ≤ 5` chronological events, quiz correctness is 1/0 and Again/Hard/Good/Easy is 0/0.4/0.8/1. Let `N` be total concept events and `z` be consecutive latest zero-valued events:

```text
w = sum(i × value_i, i=1..n) / sum(i, i=1..n)
mastery = round(clamp((100w − min(15, 5z)) × min(N/5, 1), 0, 100), 1)
```

No events show Not studied yet. Ranges are Needs Work <40; Learning <70; Strong <90; Mastered ≥90. The score is a transparent, unvalidated practice heuristic. Overall mastery averages concept scores, with unstudied concepts contributing zero after practice begins.

Again schedules ten minutes later. Hard uses at least one day and grows the prior interval by 1.2. Good starts at one day, then at least three days or twice the previous interval. Easy starts at four days, then at least four days or 2.5 times the prior interval. Actual actions alone update these records.

## Validation

Final validation on 8 October 2026: **21 tests passed in 163.93 seconds** using actual cached pretrained weights. The baseline suite passed six tests before implementation. `pip check` reported no broken requirements, and all application modules compiled successfully.

Tests cover real-model summarization/keywords, normalization and long-document chunking, format extraction and invalid PDFs/Office files, source checks, duplicate/invalid quiz options, short-answer grading, mastery and scheduling, SQLite persistence/idempotency, cached kit reactivation, search, chat citations/abstention, exports, all nine pages and friendly model/database errors.

The automated widget journey loads sample material, creates a real kit, reads notes/map, reviews a card, submits a quiz with a deliberate mistake, adds a revision card and answers a focused question, confirms recorded Progress, asks a cited document question, evaluates an actual reference, restores a fresh session, reopens material, prepares PDF, completes an immediate-feedback quiz, renames/searches material and deletes/restores it. Tests use isolated temporary databases; their prescribed answers are test inputs, not product benchmark numbers.

The running server health endpoint returns `ok` and binds to `127.0.0.1:8501`. The final sample PDF has 16 pages; each contains extractable text. All rendered pages were inspected in a contact sheet, with a separate enlarged check of the card layout. The export contains selectable text, sources, notes, cards, questions and outlines rather than screenshots.

Manual browser screenshots and responsive layout inspection remain incomplete: desktop browser automation was blocked by policy. Widget-level testing and PDF rendering were used for the checks above. No claim of a complete manual browser journey is made.

## Deployment readiness

The app can run on a CPU machine/container with persistent writable storage. It needs public-service work before multi-user deployment: authentication, access controls, backups, bounded jobs and monitoring.

Measured cached weight files: T5 242,042,016 bytes; MiniLM 90,868,376 bytes, about 333 MB total in decimal units. A real test process was observed near 1.4 GB private memory; that observation is not a peak-memory benchmark. Start with at least 4 GB RAM and several GB of disk for a small single-user installation, then measure your workload. Persist both the database directory and Hugging Face cache. Ephemeral hosting loses study history. SQLite and a shared profile suit one instance; replicas require shared storage and user isolation. No incompatible hosting manifest was created.

## Run

From the activated project environment:

```powershell
streamlit run app.py
```

Exact command without activation in this workspace:

```powershell
cd <project-directory>
python -m streamlit run app.py
```

Open [RecallAI](http://localhost:8501).

## Two-minute demo

Cache the models and prepare a sample kit before the timed demo.

| Time | Action |
| --- | --- |
| 0:00–0:20 | Home → Load Sample Notes → Create Study Kit; unchanged saved kit opens quickly |
| 0:20–0:40 | Read Overview/AI Notes; open a concept's source and Knowledge Map |
| 0:40–1:00 | Flashcards → Show Answer → Good; show next review |
| 1:00–1:25 | Complete five quiz questions, miss one, show evidence and revision actions |
| 1:25–1:45 | Show Progress; ask “What does attention mean?” and expand Sources |
| 1:45–2:00 | Reopen Library material, export PDF and refresh to show persistence |

## Known limitations

English text only; no OCR/scanned-image understanding. T5 summaries can omit/repeat/hallucinate. Notes and chat use source excerpts rather than generative rewriting. Conservative retrieval may reject valid paraphrases. There is no general-knowledge switch or standalone generative question model. Questions assess concept recall and source relationships; distractors can be ambiguous, short-answer grading requires concept names and exam outlines are not exam predictions. Sparse materials may produce fewer items. Very long single sentences require splitting. Mastery, difficulty, importance, time estimates, source thresholds and review intervals are heuristics.

Global search is lexical, while semantic retrieval is document-scoped. One local profile is shared by app visitors; authentication, cloud sync, permanent Trash purge, multi-user conflict handling, audio/YouTube import, meetings, teams and mobile access remain future work. Browser/device layout review is still needed. Review generated content against the original notes before relying on it.
