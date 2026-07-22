"""Knowledge package — atom schema, pronunciation, and TTS-term helpers.

The phase-0h extractor/librarian scaffolding was superseded by the DB-backed
`intelligence/` package and deleted 2026-06-10. Current modules:
- `_atom_schemas`          — atom validation + canonical term IDs (live)
- `pronunciation_ledger`   — cross-book pronunciation record (live)
- `pronunciation_patterns` — pronunciation heuristics (live)
- `term_render`            — deterministic TTS term renderer (live)
- `categorize_atoms`, `fill_etymology_phonetics` — manual operator CLIs

The legacy JSONL `augmenter.py` was deleted 2026-07-18 (never wired; the live
augment path is `intelligence/augmenter.py`).

Authority:
- Spec: `_workspace/plan/architecture.md` (Intelligence Layer section)
- Live augment path/agent: `intelligence/augmenter.py` + `podcast-librarian`
- Library: `content/knowledge-base/`
"""
