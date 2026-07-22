"""supplication/ — the PDF-only supplication lane (du'a / ziyarat / munajat).

A SIBLING of the podcast pipeline, not a branch inside it.

Why a sibling: the podcast pipeline cannot produce a PDF without also producing
a podcast. `per-chapter` and `finalize` are not skippable by any setting, the
ship gate (`publish_to_library.py`, G1/G2) hard-requires a non-empty `episodes/`
paired 1:1 with `chapters/`, and all five `0book-*` phases run only after the
finalize halt. Relaxing any of that would put every existing book at risk. So
this lane reuses the proven BUILDING BLOCKS (Azure Doc Intelligence OCR, the
Anthropic SDK, the Playwright print renderer) behind its own entry point, its
own state file, and its own gates.

What it produces: exactly one artifact — a facing-column PDF, English left,
original script right. NO episodes, audio, slide decks, or video. Ever.

The lane NEVER imports, calls, or mutates: orchestrate_book, _progress.PHASES,
build_episode_txt, validate_ship_ready, _translation_edition, _book_pipeline_v2,
book-print.css, or render-book-pdf.mjs.

Steps (see driver.py):
    1 intake     → content/Supplications/<slug>/, branch, config
    2 ocr        → _system/source-record.json  (IMMUTABLE after this step)
    3 segment    → units.json, unit boundaries only
    4 review     → HUMAN HALT: merge/split units before any translation spend
    5 translate  → fills each unit's `english`
    6 verify     → the lane's own verbatim + completeness gate
    7 render     → book/<slug>.pdf
    8 deliver

The integrity invariant that makes step 6 provable rather than best-effort:
a unit's `source` is NEVER authored by a model. Models only ever choose
groupings (`line_ids`) and write English. Python re-derives `source` from the
immutable OCR record every time. See schema.derive_source().
"""

from __future__ import annotations
