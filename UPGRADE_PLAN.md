# RecallAI upgrade plan

## Existing application

The original `app.py` has five views, pasted notes and TXT upload, summaries with Falconsai T5-small, KeyBERT/MiniLM concepts, source-preserving cloze flashcards, four-option MCQs, quiz scoring, JSON export and optional ROUGE evaluation. Core processing already lives in separate modules. Models use Streamlit resource caching. Session state stores the active kit, note draft and submitted answers; no permanent storage exists.

The installed environment is Python 3.11, Streamlit 1.64 and Transformers 4.57. Package checks and the running server health check passed. Before UI changes, the original full suite passed: six tests in 235.94 seconds. Original entrypoint, README and UI tests are preserved under ignored `artifacts/baseline/`.

## Upgrade sequence

1. Extend ingestion to TXT, PDF, DOCX and PPTX while retaining text input. Preserve source locations and report extraction failures.
2. Extend the existing pipeline with structured notes, source-backed concepts, must-remember facts and exam questions. Retain summary, flashcards, quizzes and optional evaluation.
3. Add semantic retrieval and passage-based answers, with abstention and real source locations.
4. Add SQLite repositories for documents, kits, embeddings, learning events, quiz attempts, preferences and conversations. Use stable IDs and content hashes.
5. Build Home and Library, then Progress and a transparent mastery calculation.
6. Add adaptive question selection, mixed question types, spaced flashcard reviews, a source-based knowledge tree, search, exports and preferences.
7. Replace the entrypoint's single-file routing with nine native Streamlit pages. Move system details out of the normal learning flow.
8. Run unit, integration and page-flow tests, inspect the running app and rendered PDF export, and document limitations and deployment needs.

## Reliability decisions

- Keep existing models and functions, with compatibility wrappers where necessary.
- Use deterministic source-based question generation as the reliable fallback. No external chat API is required.
- Ask RecallAI retrieves relevant passages and quotes them rather than generating unsupported free-form answers.
- Mastery starts with no evidence, not an invented result. Scores update only after recorded learning actions.
- SQLite is for one local profile. Authentication, cloud sync and collaboration remain roadmap items.
- Generation progress names real stages; no invented percentage or benchmark results.

## Completion status

Implementation and automated validation are complete: 21 tests passed in 163.93 seconds. Final checks cover focused revision questions, reactivation of cached preference versions, graceful model/database failure handling, cache-first loading and grouped PDF export layout. Dependencies and compilation passed; the local server health is `ok`. See `UPGRADE_REPORT.md` for details and outstanding manual browser QA.
