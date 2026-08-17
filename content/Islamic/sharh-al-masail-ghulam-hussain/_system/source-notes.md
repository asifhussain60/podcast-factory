# Source Notes — Sharh al-Masa'il (Sayyidna Ghulam Hussain)

Human-confirmed provenance notes recorded at the Phase 06a source-review gate,
resolving the warnings in `review-gate.json`. This file is documentation only —
nothing in the pipeline reads it programmatically.

## Madhab

**Ismaili.** Confirmed by Asif (book owner), 2026-08-17. Consistent with the rest
of this repo's Islamic-bucket corpus (Kitab al-Riyad, Ayyuhal Walad, Asas
al-Taweel, etc.), which is exclusively Ismaili source material.

## Chapter division (earning → sales → marriage → inheritance)

**Unconfirmed as original.** No known table of contents or reference edition was
available to verify against. Accepted as-is: the AI-designed chapter boundaries
from Phase 0d stand without further reorganization. If a reference edition
surfaces later, re-verify against `book/source-crosswalk.json`.

## Edition / publication details

**None available.** No publisher, print date, or acquisition source is known for
this PDF. Treated as an undated/unattributed scan, consistent with several other
sources in this corpus.

## Arabic script in the NotebookLM-upload chapters — deferred by design (2026-08-17)

**Decision (Asif, 2026-08-17): ship the per-chapter bundle without inline Arabic
script for now; add it properly once the book reaches its compose stage.**

The podcast-challenger's N6 check (Arabic script must be present in each
Islamic-scholarly chapter, drawn from a book glossary) flagged all five chapters
at P0 on this book. Investigating turned up a genuine tooling gap, not a content
question:

- `build_glossary.py` (the tool N6's own suggested fix names) reads from
  `_system/source/text/_phonetics.md`, a file no pipeline phase has written
  since 2026-06-08. It cannot produce a glossary for this book.
- Its replacement, `harvest_gloss_terms.py`, harvests glossary terms from
  parenthetical glosses inside the composed `book/book.md` — which does not
  exist yet at the per-chapter stage, and this book's chapter prose (a straight
  translation, not an annotated companion edition) does not use that
  parenthetical-gloss style to begin with, so even a finished book.md would
  likely yield nothing for it to harvest.
- The challenger's other suggested fix — setting `translation_policy.
  preserve_arabic_terms: false` in `series-config.yaml` — is not actually
  available: `_translation_contract.py` hard-locks that field to `true` for
  every `translation_edition` book and fails validation if it is turned off.
  `series-config.yaml` was left untouched.

Given neither suggested fix is currently workable, and the underlying compose-
time Arabic-injection pipeline (`vowel_book.py`, `_book_inline_arabic.py` — see
the repo's "Arabic script is ALWAYS vowelled" standing rule) runs automatically
over the assembled `book/book.md` regardless of this per-chapter gap, the gap is
intentionally left open here rather than patched with a fabricated glossary.
`chapters/ch05-maintenance-dissolution-and-inheritance.txt` was moved from
`failed_slugs` to `completed_slugs` in `_system/orchestrator-state.json` by
direct edit (not a challenger pass) to reflect this authorized exception; the
challenger's P0 finding (N6, recorded in a prior `challenger-report.md`) stands
as an accurate, non-silent record of the gap rather than being retroactively
cleared.

**Follow-up, tracked separately:** once `book/book.md` is composed, verify the
book-edition reading text carries proper Arabic script via the standing compose-
time overlay before that stage is considered done. The NotebookLM-upload chapter
text (`chapters/*.txt`) is expected to stay English-transliteration-only
permanently — it is the TTS-facing lane, and the contract's own tone_constraints
already require plain transliteration there for audio safety.
