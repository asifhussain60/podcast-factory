# Transcripts

Slug-aligned transcripts for *Asaas al-Taʾwīl*. One file per episode, named `EP##-<slug>.transcript.txt` to match `chapters/ch##-<slug>.txt` and `episodes/EP##-<slug>.txt` exactly.

## Provenance

NotebookLM renders the Audio Overview from the chapter + customize prompt. The audio is transcribed by `scripts/podcast/transcribe_episode.py` (Azure Speech-to-Text Fast Transcription API) — or, optionally, by any external service — and the result lands here renamed to the slug-aligned form. `transcribe_episode.py` writes here; the rest of the pipeline only reads.

## Consumers

- `scripts/podcast/audit_transcript.py <BOOK_DIR> EP##-<slug>` — empirical drift audit; appends findings to `_learning/findings.jsonl`
- `podcast-challenger` Loop M — empirical-transcript audit
