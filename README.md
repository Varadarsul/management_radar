# Management Radar

A small end-to-end prototype for the HDFC AMC intern challenge. It ingests cached company disclosures and management interview transcripts, stores them in SQLite, and answers analyst queries with citations to the original source and a timestamp or page reference.

## Features

- Company timeline with source cards and tags
- Local document cache and transcript cache
- SQLite-backed retrieval store
- Chat that answers using retrieved evidence
- HDFC-inspired design with red/navy colour palette

## Quick start

1. Open a terminal in this folder.
2. Create and activate a virtual environment if you want an isolated setup.
3. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
4. Run the app:
   ```bash
   python app.py
   ```
5. Open http://127.0.0.1:5000

## How the app works

- A default dataset for Maruti Suzuki and Infosys is seeded automatically.
- Each source is cached locally under `data/cache/`.
- The SQLite database is created in `data/management_radar.db`.
- The app answers with evidence-based citations and honest "I do not know" fallback text when the database lacks matching passages.

## Project structure

- `app.py` — Flask application and retrieval logic
- `data/` — default sources, cached text, and SQLite database
- `templates/index.html` — single-page dashboard UI
- `static/style.css` — HDFC AMC styling
- `tests/test_core.py` — smoke tests for chunking, tagging, and answer generation

## Notes

- The default dataset is intentionally local and offline-safe so it runs without external API access.
- If you add an LLM API key later, the app can be extended to place the retrieved evidence into a model call rather than relying on rule-based summarization.
