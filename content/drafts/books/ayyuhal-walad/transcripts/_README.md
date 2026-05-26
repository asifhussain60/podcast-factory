# Transcripts

Slug-aligned transcripts for *Ayyuhal Walad*. One file per episode, named `EP##-<slug>.transcript.txt` to match `chapters/ch##-<slug>.txt` and `episodes/EP##-<slug>.txt` exactly.

## Provenance

NotebookLM renders the Audio Overview from the chapter + customize prompt. Asif transcribes the audio via Azure Speech-to-Text or an external service (https://transcripts.ai, manual subscription) and drops the result here, renamed to the slug-aligned form. Nothing in the pipeline writes to this folder — human input only.

## Format

SRT preferred (timestamps support pacing analysis); TXT acceptable. File extension stays `.transcript.txt` regardless of the underlying format.

## Consumers

- `scripts/podcast/audit_transcript.py <BOOK_DIR> <EP##-slug>` — lexical audit; writes `_system/audit-EP##-<slug>.md`.
- `.github/agents/podcast-challenger.agent.md` Loop M — empirical-transcript scan for modernization injections, phonetic doublings, mangled names.
