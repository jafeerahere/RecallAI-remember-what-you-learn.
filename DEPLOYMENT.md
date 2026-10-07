# Streamlit Community Cloud deployment

## Exact target

- Git URL: `https://github.com/jafeerahere/RecallAI-remember-what-you-learn..git`
- Community Cloud repository: `jafeerahere/RecallAI-remember-what-you-learn.`
- Branch: `main`
- Main file path: `app.py`
- Python: select **3.11** in Advanced settings.
- Dependencies: the root `requirements.txt`. `requirements-dev.txt` adds only test tooling.

The trailing period is part of the repository name. Keep it when entering the repository.

## Deploy

1. Sign in at [Streamlit Community Cloud](https://share.streamlit.io/) and connect the GitHub account with administrative access to the repository.
2. Click **Create app**, then **Yup, I have an app**.
3. Enter the repository, `main`, and `app.py` exactly as above. If suggestions omit it, type the repository manually.
4. Open **Advanced settings** and select Python 3.11. No secret API key is required. Save, then click **Deploy**.
5. Follow build/runtime logs. A homepage loading is only a startup check; also run the sample Study Kit and exercise both AI models.

See the official [deployment instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

## Dependencies and portability

The app uses the same T5 and MiniLM models as the local application. Linux installs CPU-only PyTorch 2.14.1 from the official PyTorch index. It does not need CUDA or a GPU. Runtime versions match the tested local Python 3.11 stack. The spaCy English model is explicitly installed through its hashed wheel URL, so cloud extraction uses the same parser rather than silently falling back to a sentencizer.

Application data paths derive from the project root. PDF exports use a font bundled with ReportLab, with an optional configured font override. Document extraction is pure Python and does not need Office, LibreOffice, OCR or Poppler. NLTK uses `TreebankWordTokenizer` and needs no downloaded tokenizer corpus. The existing native theme is retained.

`.github/workflows/ci.yml` installs the curated dependencies on Linux and runs actual-model tests after pushes. The Windows package snapshot in `requirements-lock.txt` is historical documentation, not the cloud installation file.

## Models and resources

Actual checkpoints:

- `Falconsai/text_summarization` for summaries.
- `sentence-transformers/all-MiniLM-L6-v2` for embeddings and KeyBERT ranking.
- spaCy `en_core_web_sm` 3.8.0 for linguistic extraction.

The primary weight files total about 333 MB. A Windows model-test process was observed using about 1.4 GB private memory. This is not a Linux peak-memory benchmark or a Community Cloud capacity guarantee. Community Cloud has variable resource limits; the official [resource FAQ](https://discuss.streamlit.io/t/faq-this-app-has-gone-over-its-resource-limits/62973) gives approximate historical limits and explicitly says they can change.

This architecture is suitable for a small demo only after live testing confirms memory headroom. Use the sample or a short chapter first. Large files and simultaneous users may exceed the allocation. Models are lazy-loaded with `st.cache_resource`; embeddings use bounded `st.cache_data`, and unchanged kits reuse stored results. No model is replaced or truncated to disguise a resource failure.

If logs show an out-of-memory restart, retain the existing models and investigate measured usage before considering a replacement or an inference service. The project does not claim that Community Cloud provides durable production storage or unrestricted inference resources.

## Storage and privacy

SQLite uses `data/private/recallai.sqlite3` by default. Documents, kits, vectors, chats, card reviews, scores and preferences survive ordinary Streamlit reruns while the same server filesystem exists. **Community Cloud's local filesystem is not durable storage.** Reboots, rebuilds, redeployments or infrastructure changes can remove data. Local testing does not establish cloud durability. Export material that must be kept; durable storage needs a separate future backend.

The database, logs, personal uploads, `.env`, secrets, virtual environments and model caches are excluded from Git. The GitHub project contains the complete application, not private Library data.

All visitors use one shared profile and can view the shared Library. This is not a private multi-user product. Restrict app access or use non-sensitive sample material. Models run on the hosting server; “Local” refers to in-process inference, not computation on each visitor's device. Initial weights download from Hugging Face. No external answer API is configured.

## Secrets and optional configuration

**Required API secrets: none.** The configured models are public and need no Hugging Face or OpenAI token. Do not add GitHub credentials to app secrets.

Optional non-secret configuration names are:

```text
RECALLAI_DATA_DIR
RECALLAI_DB_PATH
RECALLAI_SUMMARY_MODEL
RECALLAI_EMBEDDING_MODEL
RECALLAI_OFFLINE
RECALLAI_TIMEZONE
RECALLAI_PDF_FONT
```

Use root-level TOML entries in Streamlit's Secrets panel if an override is necessary; these become environment variables. The defaults work without secrets. Keep `RECALLAI_OFFLINE` disabled on the first cloud build because weights are not yet cached. Use Linux paths for storage/font overrides. Do not change model IDs without new validation.

See [Community Cloud secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

## Live validation checklist

After a real app URL exists:

1. Confirm homepage and all nine navigation pages load.
2. Load sample notes, create a Study Kit and wait for actual summarization and concept extraction.
3. Read notes/concepts and source passages, reveal/rate a flashcard, then submit a quiz.
4. Confirm recorded results in Progress and reopen the kit from Library.
5. Ask “What does attention mean?” and inspect its sources. Ask an unsupported question and confirm abstention.
6. Upload a non-sensitive TXT/PDF/DOCX/PPTX test file and verify real extraction and a generated kit.
7. Check logs for dependency, download, memory, spaCy, NLTK, PyTorch, path and widget-state errors.
8. Add the verified live URL to README only after successful startup and feature checks. Never infer a URL from a requested subdomain.

## Local command

```sh
streamlit run app.py
```

Activate the project environment first, or use `python -m streamlit run app.py` with its interpreter.
