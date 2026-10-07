# RecallAI

**Remember what you learn.**

## Overview

RecallAI turns learning material into a saved Study Kit, then helps you practise and track what you remember. Its learning loop is **Understand → Connect → Remember → Test → Master**.

This repository contains the complete Streamlit application, document processing, local AI pipeline, SQLite repositories, learning services, sample material and tests. Personal Library data, credentials, virtual environments and downloaded weights are excluded.

## Features

- Home dashboard and nine pages: Home, Study Workspace, AI Notes, Flashcards, Quiz, Ask RecallAI, Progress, Library and Settings.
- PDF, DOCX, PPTX and TXT uploads, pasted notes and an AI/NLP/Transformers sample.
- Study Kits with summaries, structured notes, explained concepts, supporting passages, must-remember facts, exam prompts and a section-based Knowledge Map.
- Hidden-answer flashcards, Again/Hard/Good/Easy ratings and lightweight spaced review scheduling.
- MCQ, True/False and concept-name short answers, immediate or end-of-quiz feedback, weak-concept priority and focused revision.
- Document-specific questions with semantic retrieval, real source locations and insufficient-evidence abstention.
- Saved Library, chat, review schedules, completed scores, mastery and preferences. Rename, regenerate, search, move to Trash and restore materials.
- Actual-content Markdown/PDF notes, CSV cards/results, complete kit PDF and JSON exports.
- Optional reference-based ROUGE and semantic evaluation in Developer/System Details.

## How RecallAI works

1. Extract text and source locations, then normalize and segment sentences.
2. Summarize every source chunk and rank important phrases with KeyBERT/MiniLM.
3. Organize actual source sentences into notes, concepts, facts and exam outlines.
4. Build source-based flashcards and questions with semantic distractors, preserving evidence.
5. Index passage embeddings for chat and record practice to update revision priorities.

Quick, Standard and Deep adjust summary detail and concept coverage. Changing depth suggests appropriate card counts and quiz difficulty, which remain adjustable. Models are lazy-loaded with `st.cache_resource`; deterministic embeddings use bounded `st.cache_data`. Content hashes and generation fingerprints reuse unchanged kits rather than running inference on every interaction.

### Source support and retrieval

Original cards, concepts and MCQs pass source support when their answer is an exact span in their passage, the passage occurs in the material, and answer/passage cosine similarity is at least 0.20. This checks consistency, not factual truth. Derived questions keep their underlying source evidence.

Ask RecallAI uses normalized 384-dimensional passage vectors, cosine top-k retrieval and sentence reranking. Default top-k is four and the similarity threshold is 0.30. Conservative lexical checks reject unsupported targets. Answers quote actual passages with extracted locations. If evidence is insufficient, the app says: "I couldn't find enough information about that in this material."

### Mastery

Quiz correctness contributes 0/1. Again/Hard/Good/Easy contributes 0/0.4/0.8/1. The latest five events receive increasing weights from oldest to newest. A consecutive-mistake penalty and evidence factor keep a single success from implying mastery:

```text
w = sum(i * value_i) / sum(i), for the latest n <= 5 events
mastery = round(clamp((100*w - min(15, 5*latest_consecutive_zeros))
                     * min(total_events/5, 1), 0, 100), 1)
```

No events show Not studied yet. Needs Work is below 40, Learning below 70, Strong below 90 and Mastered at least 90. Mastery and review intervals are transparent heuristics, not scientifically validated measures.

## Screenshots

No mock screenshots are presented as a live product. Browser screenshots will be added after the deployed interface has been verified. The current UI is covered by automated Streamlit widget journeys; PDF exports have also been rendered and visually reviewed.

## Technology stack

Python 3.11, Streamlit 1.64, CPU PyTorch, Transformers, sentence-transformers, KeyBERT, spaCy, NLTK, NumPy, scikit-learn, pandas and SQLite. pypdf, python-docx and python-pptx extract documents; ReportLab produces PDFs. python-dotenv loads optional local configuration and rouge-score supports optional summary evaluation.

`requirements.txt` lists only application runtime dependencies. Test tooling is separate in `requirements-dev.txt`. The historical Windows environment snapshot in `requirements-lock.txt` is not the cloud installation file.

## Architecture

```text
app.py                  Streamlit entry point, navigation and material selection
app_pages/              Nine product pages
core/                   NLP, ingestion, retrieval, quizzes, mastery and exports
database/               SQLite schema, transactions and repositories
services/               Document, study, chat and analytics orchestration
utils/                  Shared UI, configuration, logging and pipeline helpers
data/sample_notes.txt   AI, NLP and Transformers sample
scripts/audit_publish.py Secret/path audit that does not print secret values
tests/                  Core, integration, persistence and UI tests
.github/workflows/ci.yml Linux dependency and actual-model validation
.streamlit/config.toml  Existing native indigo theme
```

Pages call services, which coordinate core modules and repositories. Model interfaces wrap the existing summarizer, encoder and deterministic source-question fallback. PostgreSQL and a separate generative question adapter are future work.

## Supported file types

| Input | Extracted evidence locations |
| --- | --- |
| Paste / UTF-8 TXT | Markdown sections and paragraphs |
| PDF | Embedded text and original page numbers |
| DOCX | Headings, paragraphs and tables in document order |
| PPTX | Slide titles, text, grouped shapes and tables; slide numbers |

Uploads are limited to 20 MB, 250,000 normalized characters and 500 PDF pages. Study Kit creation needs at least 50 words. Expanded Office archives are bounded. Scanned/image-only PDFs need OCR elsewhere; encrypted, corrupted and empty files receive useful errors. Editing extracted text switches to paragraph locations to prevent stale page/slide citations.

## Installation

Use Python 3.11:

```sh
git clone https://github.com/jafeerahere/RecallAI-remember-what-you-learn..git
cd RecallAI-remember-what-you-learn.
python -m venv .venv
```

Activate the environment for your platform:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```sh
# Linux / macOS
source .venv/bin/activate
```

Then install runtime dependencies:

```sh
python -m pip install -r requirements.txt
```

Linux installs CPU-only PyTorch to avoid unnecessary CUDA packages. The spaCy English model is explicitly included, so no separate download command is required. T5 and MiniLM weights download on first use and are subsequently cached. No paid API key is needed.

## Run locally

From the activated project environment:

```sh
streamlit run app.py
```

Alternatively use `python -m streamlit run app.py` with the environment's interpreter. Open [the local app](http://localhost:8501). Ctrl+C stops a terminal server.

To run tests:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m pip check
```

Tests use actual pretrained models for summaries, concepts, retrieval and the Streamlit learning journey. Model downloads and CPU inference make integration tests slower than unit tests.

## Models used

- [Falconsai/text_summarization](https://huggingface.co/Falconsai/text_summarization), the existing T5-small summary checkpoint.
- [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), normalized 384-dimensional embeddings and semantic ranking.
- spaCy `en_core_web_sm` 3.8.0 for linguistic analysis; NLTK `TreebankWordTokenizer` needs no downloaded corpus.
- KeyBERT plus structured extraction for concepts.
- Deterministic grounded question generation with semantic distractors. A separate generative question model is not configured.

No model was silently replaced or trained from scratch. Questions and chat use source-based fallbacks rather than unrestricted generated answers. No benchmark results are prefilled.

## Privacy

Inference runs in the app server process. On your laptop that is your local machine; on Community Cloud it is the hosting server, not a visitor's browser. Initial model downloads contact Hugging Face. No external answer API is configured.

SQLite defaults to `data/private/recallai.sqlite3`. It stores normalized material, source locations, kit versions, vectors, concepts, cards, reviews, completed quizzes/answers, mastery, chat and preferences. Upload binaries are read in memory and not saved. Trash retains records for restoration; permanent purge is not implemented.

The app has **one shared profile**. Anyone with access can view that Library; authentication and tenant isolation are not implemented. Use non-sensitive sample material for a public demo. Ordinary reruns retain SQLite data while the same server filesystem exists, but Community Cloud's filesystem is temporary and can reset on reboot or redeployment. Export anything you need to retain.

`.env`, `.env.*`, secrets, personal databases, logs, uploads, virtual environments and model caches are ignored. `.env.example` contains optional configuration names and safe defaults, not credentials.

## Deployment

Deploy on Streamlit Community Cloud with:

| Setting | Value |
| --- | --- |
| Repository | `jafeerahere/RecallAI-remember-what-you-learn.` |
| Branch | `main` |
| Main file path | `app.py` |
| Python version | `3.11` in Advanced settings |
| Required secrets | None |

Follow [DEPLOYMENT.md](DEPLOYMENT.md) for exact steps, configuration names and live validation. The trailing period is part of the repository name.

Model weights total about 333 MB. A local Windows test process was observed near 1.4 GB private memory, which is not a Linux peak measurement or a cloud capacity guarantee. Community Cloud resources are limited and can change; verify the live sample before relying on the deployment. Large inputs or concurrent users can exhaust memory. Durable production storage requires an external backend. No deployment success or durable cloud persistence is implied by a local test.

## Limitations

- English extracted text only, without OCR or scanned-image understanding.
- Summaries can omit, repeat or introduce unsupported details; review them against the original notes.
- Notes and chat use source excerpts. Conservative retrieval may reject valid paraphrases; no external/general-knowledge mode is configured.
- Questions assess concept recall and source relationships. Distractors may be ambiguous; short answers require the concept name, not essay grading.
- Exam outlines are practice prompts, not predictions. Source support, importance, difficulty, reading time, mastery and schedules are heuristics.
- Sparse material can yield fewer cards/questions than requested. A sentence beyond model context needs splitting.
- Library search is lexical; semantic retrieval is limited to the selected document.
- One shared profile and temporary cloud storage; no authentication, cloud sync, permanent Trash purge or multi-user conflict handling.

## Roadmap

Durable storage and authentication, calibrated retrieval evaluation, improved question pedagogy, a tested generative question adapter, OCR, semantic Library search and permanent deletion controls. Later work includes audio/YouTube import, meeting tools, team collaboration and mobile access.

## Live Demo

A live Community Cloud URL has not yet been verified. This section will contain the actual URL only after successful deployment and feature checks. The local address is not a public deployment.
