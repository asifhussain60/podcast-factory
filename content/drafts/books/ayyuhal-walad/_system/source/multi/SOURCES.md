# Ayyuhal Walad — multi-format source set (live WC8 fixture)

The same book (al-Ghazali, *Ayyuhal Walad* / "O Dear Beloved Son") in multiple languages,
formats, and voices. This is the live fixture for the WC8 multi-source intake work
(common-denominator core + attributed additions → noise-strip → enhance). Dropped by Asif
into `_workspace/inbox/` 2026-05-29; filed + version-controlled here so the sources are never
lost and can be retrieved/restored on demand.

## Committed to git (this folder)

| File | Size | What it is | Role in unification |
|---|---|---|---|
| `pdf/ayyuhal-walad-arabic-original.pdf` | 214 KB, 15 pp | Arabic original (Imam Muhammad Hamid al-Ghazali) | **Authoritative core / spine candidate** (the actual book text) |
| `pdf/ayyuhal-walad-english-superior.pdf` | 3.3 MB | English translation ("superior version") | Translation layer (companion; trust auto-calibrated at intake) |
| `pdf/ayyuhal-walad-scholarly.pdf` | 8.7 MB | Scholarly / commentary edition | Additions layer (explainer/commentary surplus) |
| (existing) `../Ayyuhal-Walad.pdf` | — | The single PDF already in the pipeline pre-WC8 | Prior source of record |

## Lecture media — LOCAL ONLY, never committed (Asif decision 2026-05-29)

12 MP4 lectures, **~13 GB total**: *"Ghazali's Dear Beloved Son Explained — Shaykh Abdullah
Misra"*, episodes 01–12. The **explainer/narrator** source (the pipeline's value is the
**audio**, for transcription).

> **Policy:** the raw video and any extracted audio are **transient local build inputs** — kept
> local, never committed (GitHub rejects >100 MB files anyway), and **deletable once the pipeline
> is built**. They are restorable from YouTube. Only the **TEXT the pipeline produces** from them
> (transcripts → refined source) is committed to git — that text is the durable, restorable
> lecture artifact. Audio is extracted on demand with ffmpeg (free, local, no paid tokens).

Episodes: 01 Introduction · 02 Prophetic Advice · 03 Actions and Intentions · 04 Beneficial
Knowledge · 05 The Summary of Knowledge · 06 Four Essentials for the Seeker · 07 Recognizing
the True Spiritual Guide · 08 Adab with a Spiritual Guide · 09 Language of the Heart · 10 Four
Things to Desist From · 11 Four Things to Desist From (Part 2) · 12 Four Things to Do.

Raw video currently at: `_workspace/inbox/youtube/` (gitignored). Source: YouTube.

## Restore
The PDFs restore with the repo (`git checkout`). The lecture content restores as the committed
**transcript/refined text** the pipeline produces. The raw 13 GB video + extracted audio are
transient/local — re-download from YouTube (or Asif's local archive) if ever needed again.

## How these unify (WC8.1 design)
- **Common denominator (core):** content shared across the Arabic original + English + scholarly
  + the Shaykh's reading → the authoritative spine (Arabic original is the canonical rendering).
- **Additions (attributed layers):** each source's surplus beyond the core — the scholarly
  edition's commentary, the Shaykh's spoken elaboration/examples — tagged by source/role.
- **Then:** noise-strip (filler/asides) + enhance (corpus-verified references, glossary).
- **Engine routing (no wasted paid tokens):** free timestamp/structural alignment + local ffmpeg
  for audio; Gemini for cheap bulk comparison; Claude (Max) for judgment; Azure only for targeted
  transcription/translation of what's actually needed.
