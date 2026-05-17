# TurboScribe transcripts

NotebookLM Audio Overview transcripts for *Ayyuhal Walad*. One file per episode, slug-aligned with `chapters/chNN-<slug>.txt` and `episodes/EP##-<slug>.txt`.

## Provenance

Generated via NotebookLM's *Audio Overview* feature after the matching `chapters/chNN-<slug>.txt` was uploaded as the source and the matching `episodes/EP##-<slug>.txt` was pasted into the Customize prompt box. The audio overview is then transcribed via **TurboScribe** (https://turboscribe.ai, manual subscription) and the resulting `.txt` (or `.srt` / `.vtt`) is dropped into this folder by Asif. Nothing in the pipeline writes here — human input only.

## Naming convention

`EP##-<slug>.transcript.txt` — slug matches `chapters/ch##-<slug>.txt` and `episodes/EP##-<slug>.txt` exactly (1:1 chapter ↔ episode ↔ transcript mapping per skill invariants). Rename TurboScribe's auto-generated filename to this form before or right after dropping. SRT preferred for timestamps; TXT acceptable.

## How these files are used

`scripts/podcast/audit_transcript.py <BOOK_DIR> <EP##-slug>` reads the transcript and writes a per-episode markdown audit report to `_system/audit-EP##-<slug>.md`. The report measures:

- phonetic doublings (`Sahih Sitta, sahasita` pattern; R-PHONETICS-OUT)
- mangled names (e.g., `tassel wolf` for *Tasawwuf*)
- modernization injections (R-NOMODERNIZE DENY list)
- surprise-noise loops (R-NOSURPRISE DENY list)
- welcome-opening violations (R-WELCOME)
- honorific repetition (R-HONORIFIC-ONCE)
- abbreviated work titles (R-NO-ABBREVIATION)
- filler-injection density (R-NOINTERRUPT)

Each baseline audit then becomes the regression artifact against which the next NotebookLM upload is measured.

## History

- 2026-05-17 — These 5 transcripts (originally named after the auto-generated NotebookLM titles) drove the architectural pivot from inline phonetic guides (in chapter files) to imperative pronunciation directives (in customize prompts). See `skills-staging/podcast/SKILL.md` Invariant 5 (post-2026-05-17 revision) and the v1.3 entry in `.github/agents/podcast-challenger.agent.md` Version section. Originally lived under `truboscribe/`, briefly moved to `transcripts/` (intended canonical/inbox split), then consolidated back to a single `turboscribe/` folder — Asif drops slug-aligned transcripts here directly; no two-stage canonicalization.
