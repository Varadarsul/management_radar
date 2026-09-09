# Notes

## Prompting approach

The core idea was to keep the system simple and reliable: first retrieve exact passages from local cached content, then synthesize an answer around the evidence. This reduces hallucination risk and fits the brief's requirement for grounded answers.

## Accepted decisions

- Used local cached text and transcripts rather than depending on live network fetches, so the app is deterministic and works offline.
- Used SQLite for the retrieval layer, which matches the challenge's requirement for a real database.
- Kept the answer layer heuristic and retrieval-driven rather than fully model-dependent, since the environment may not have a valid API key.

## Rejected / deferred ideas

- Full YouTube transcript integration with a live LLM call was deferred because API credentials and network reliability vary. The prototype still shows the right architecture and graceful handling when transcript sources are missing.
- Complex multi-stage AI summarization was not used in the first pass; the retrieval and keyword-based tagging are enough for a working prototype.

## Security note

- No secrets are stored in code.
- The app explicitly falls back to "I do not have direct evidence" rather than inventing statements when a passage is absent.
