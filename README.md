# Management Radar

Management Radar is a lightweight Flask-based research and Q&A prototype for tracking company management commentary from cached disclosures and interview transcripts. It stores source material in SQLite, retrieves relevant passages by keyword match, and answers analyst questions with evidence-backed snippets instead of making up unsupported claims.

This project is designed to run fully offline with local data and is suitable for demoing an evidence-grounded company intelligence workflow.

## Why this project exists

The app helps a user answer questions like:

- What is management saying about growth or margin expansion?
- What are the key themes in recent company commentary?
- Which sources support a management claim?

The workflow is intentionally simple and reliable:

1. Seed local sources and cached document text
2. Chunk text into searchable passages
3. Retrieve matching evidence for a question
4. Generate a grounded answer with the relevant source snippet

## Features

- Searchable company source library with cached transcripts and disclosed documents
- SQLite-backed retrieval layer for evidence search
- Topic tagging based on management themes such as growth, margin, AI, risk, and expansion
- Analyst chat interface that responds from retrieved evidence
- Offline-safe default dataset for demo and local development
- Small, testable Python project structure

## Tech stack

- Python 3
- Flask
- SQLite
- pandas
- pypdf
- youtube-transcript-api
- pytest

## Project structure

```text
management_radar/
├── app.py                     # Flask app and retrieval logic
├── disclosure_links.csv       # Source metadata for seeded company documents
├── requirements.txt           # Python dependencies
├── README.md                  # Project overview and setup instructions
├── NOTES.md                   # Design notes and rationale
├── data/
│   ├── cache/                 # Downloaded or cached source text files
│   ├── default_sources.csv    # Default source seed data
│   └── management_radar.db    # SQLite database generated on first run
├── static/
│   ├── app.js                 # Front-end logic for UI interactions
│   └── style.css              # Styling for the dashboard
├── templates/
│   └── index.html             # Main application page
├── tests/
│   └── test_core.py           # Smoke tests for chunking, tagging, and answer generation
└── .gitignore                 # Git ignore rules (if present in your repo)
```

## Prerequisites

Before running the app, make sure you have:

- Python 3.10 or newer
- pip installed
- A terminal or command prompt

## Quick start

Clone the repository and move into the project folder:

```bash
git clone <your-repository-url>
cd management_radar
```

Create and activate a virtual environment:

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install project dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the application:

```bash
python app.py
```

Open the app in your browser:

```text
http://127.0.0.1:5000
```

## How the app works

When the app starts, it automatically:

- creates the `data/` folder if needed
- sets up the SQLite database
- loads default company source metadata
- downloads or caches relevant source files when possible
- chunks the text into searchable passages
- indexes the passages for retrieval

The app is intentionally local-first. It does not depend on a live LLM or external API to function.

## Data and source handling

The project includes a small local dataset for demo use. Cached sources are stored under `data/cache/`, and the generated database is created at `data/management_radar.db`.

If a source fails to fetch or a transcript is unavailable, the system gracefully falls back to a conservative answer such as:

> I do not have direct evidence in the cached sources to answer that question confidently.

This is intentional and helps avoid hallucinated output.

## Testing

Run the automated smoke tests with:

```bash
pytest
```

The test suite covers:

- text chunking behavior
- topic tagging
- answer generation for missing evidence

## Typical usage

Once the app is running:

1. Open the web interface.
2. Review the company timeline and sources.
3. Ask a management-related question in the chat panel.
4. Review the returned evidence snippets and citations.

Example questions:

- What is management saying about expansion plans?
- What are the key risks highlighted by the company?
- How is AI or digital transformation being discussed?
- What evidence supports the margin outlook?

## Notes for GitHub upload

This repository is intended to be easy to run from a fresh clone. To keep setup friction low:

- dependencies are pinned in `requirements.txt`
- default data is local and offline-safe
- no API keys are required for the base app to run

If you later want to upgrade the app with a true LLM integration, the current retrieval pipeline is structured to support plugging in a model on top of the cached evidence rather than replacing the retrieval logic.

## License

This project does not currently include a formal license file. If you are publishing it publicly on GitHub, consider adding a license such as MIT or Apache 2.0 before release.

## Troubleshooting

### Module import errors

Make sure your virtual environment is active and dependencies are installed:

```bash
python -m pip install -r requirements.txt
```

### App does not open in the browser

Check that the server is still running and that the port is not already in use. If needed, restart with:

```bash
python app.py
```

### Database or cache not being created

Ensure the project folder is writable. The app creates `data/` and `data/cache/` automatically when it starts.

## Contributing

This project is small and intentionally simple. You can extend it by:

- adding more source types
- improving retrieval quality
- adding better topic taxonomies
- connecting the evidence to an external LLM
- expanding the UI for company comparison and trend tracking
