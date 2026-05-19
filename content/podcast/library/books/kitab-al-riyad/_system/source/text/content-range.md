---
schema_version: 1
book_slug: kitab-al-riyad
generated_by: operator-review
generated_at: 2026-05-19T16:50:00Z
body_starts_at_page: 52
body_ends_at_page: 232
include_author_preface: true
include_author_toc: false
front_matter_summary: |
  Pages 1-51: Editor Arif Tāmir's 1960 Introduction — bios of al-Razi /
  al-Sijistani / al-Kirmani; editor's bibliographic list of al-Kirmani's
  25 works; editing notes (manuscripts A and B from Ivanow); editor's TOC
  summary. Modern editorial apparatus — not the source author's content.
back_matter_summary: |
  Pages 233-254: six indexes — Subject (233-237); Qurʾānic Verses (239-241);
  Manuscripts and Printed Books (243-245); Message—21 footnote index (245-247);
  Names (247-249); Cities and Countries (251-254). Reference apparatus —
  not the source author's content.
---

# Kitab al-Riyad — Content Range Declaration

**Authored:** 2026-05-19 via P22 operator-review gate (`operator-review.md` §7).

## Source structure

The refined English transcript (`refined-english.md`, 3,709 lines, 254 PDF pages) contains three zones:

| Zone | PDF pages | Lines | % of file | Status |
|---|---|---|---:|---|
| Front matter (editor's apparatus) | 1–51 | 1–497 | 13% | **SKIP** |
| Body content (al-Kirmani's own work) | 52–232 | 498–3,127 | 71% | **INCLUDE** |
| Back matter (six indexes) | 233–254 | 3,131–3,709 | 16% | **SKIP** |

## Why these boundaries

**body_starts_at_page: 52** — This is where al-Kirmani's own preface opens: *"And in [matters touching] the paths of monotheism, and the knowledge of the limits of imbalance, I judged that I should cite the sayings of each one of them… I have… titled the Book of al-Riyad… The book gathers ten chapters (abwāb), all of them comprising one hundred and fifty-seven sections (fusūl)."* This passage is al-Kirmani's methodology + dedication and IS content the listener should hear.

**include_author_toc: false** — al-Kirmani's own table of contents (page 53) is structural-only — just lists "Chapter One: The perfection of the soul," "Chapter Two: Intellect and soul" without any content. Skipping it saves token spend without losing material.

**body_ends_at_page: 232** — This is where Bāb 10's last section ends. Pages 233 onward are reference indexes.

## Downstream phase behavior (per P4.10 spec)

When the orchestrator code lands:

- **Phase 0d (chapter segmentation):** drops sections outside `[52, 232]` from `chapters-rationale.md` and `chapters/chNN-*.txt`
- **Phase 0e (enrichment):** only loads body content; cost-ledger row labels skipped page range with `method='content-range-skip'`
- **Phase 11 (per-chapter framing):** only references body content in beat anchors
- **Loop N (numeric-disambiguation):** skips numeric claims whose source page falls outside `[52, 232]` — so the editor's bibliography of al-Kirmani's 25 works (page 31) does NOT trigger "invented enumeration" findings

## Expected savings

~29% of `refined-english.md` skipped. Estimated $3-5 reduction in Phase 0c/0e/11 LLM token spend on this book. Loop N false-positive on editor bibliography prevented.

## Open caveat

P4.10 orchestrator code (`scripts/podcast/_content_range.py` + Phase 0d/0e/11 wiring) is documented in the plan but not yet shipped. Until it ships, this file is a forward-looking artifact — captured at the P22 review gate as the operator's declaration of intent. Future runs of `orchestrate_book.py --resume kitab-al-riyad` will honor it once P4.10 lands.
