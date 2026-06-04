# Asaas al-Taʾwīl (أساس التأويل)

Author: al-Qāḍī al-Nuʿmān (d. 974 CE)
Editor: ʿĀrif Tāmir (1960 Beirut edition)
Source PDF: 416 pages, scanned image-only, Arabic
Plan reference: [`podcast-plan.yaml`](../../../../../_workspace/plan/podcast-plan.yaml) P9.5 (Wave 3 corpus)

## What this book is

A foundational Fatimid esoteric exegesis (*taʾwīl*) of the prophetic narratives in the Qurʾān, organized around the **seven nāṭiqs** — speaker-prophets who each inaugurate a cosmological cycle: Adam, Nūḥ, Ibrāhīm, Mūsā, ʿĪsā, Muḥammad, and the awaited Qāʾim. Under each nāṭiq, the book recounts the stories of the intermediate prophets (the *asās* + *ḥujjas*) who bridge that nāṭiq to the next.

The book is **deliberately incomplete**: the seventh chapter on the Qāʾim was never written. The editor's note on printed page 21 explains: al-Nuʿmān stopped because the awaited Qāʾim "has not yet come." This absence is itself the book's final argument.

## Why this book is a podcast-pipeline test case

Asaas exercises the pipeline's hardest cases at once:

- **Image-only Arabic source** — full Azure OCR + translate path (Phase 0a)
- **Recursive structure** — each nāṭiq cycle repeats a fixed cosmological pattern (calls for episode-architecture.md Pattern 5 — Recursive Scaffold)
- **Heavy numeric/symbolic surface** — 7 nāṭiqs, 12 ḥujjas, abjad ciphers (Loop N guardrail exercise)
- **Uneven section lengths** — 43/31/72/120/16/54/0 pages per nāṭiq cycle (challenges Phase 0d auto-segmentation)
- **Deliberate absence** — the unwritten 7th chapter must be honored as content, not glossed over

## Preflight artifacts pre-seeded (before P9.5 fires)

| File | What it carries |
|---|---|
| `_system/source/text/chapters-rationale.md` | The 6-section nāṭiq map with page ranges (HIGH confidence from editor's TOC) — pre-seeds Phase 0d ground truth |
| `_system/concept-glossary.md` | ~25 conceptual terms across cosmology, hermeneutics, and prophetology |

These are read by the orchestrator at Phase 0d (chapter segmentation) and Phase 11 (per-chapter framing). They are NOT a substitute for the pipeline's own analysis — they are operator-authored ground truth that the pipeline can confirm or amend at the Phase 0f operator gate.

## Recommended series plan (operator confirms at Phase 0f)

Six episodes, Mentor + Student persona override, Pattern 5 (Recursive Scaffold), long-form tier (~30 min each). Episode 6 honors the unwritten 7th chapter as its own subject: the deliberate silence.

Detailed plan lives in `chapters-rationale.md`.
