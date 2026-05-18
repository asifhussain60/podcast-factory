# Transcripts

Slug-aligned transcripts for *The Master and the Disciple*. One file per episode, named `EP##-<slug>.transcript.txt` to match `chapters/ch##-<slug>.txt` and `episodes/EP##-<slug>.txt` exactly.

## Provenance

NotebookLM renders the Audio Overview from the chapter + customize prompt. Transcribe the audio (https://transcripts.ai) and drop the result here, renamed to the slug-aligned form. Nothing in the pipeline writes to this folder — human input only.

## Consumers

- `scripts/podcast/audit_transcript.py <BOOK_DIR> EP##-<slug>` — empirical drift audit
- `podcast-challenger` Loop M — empirical-transcript audit
