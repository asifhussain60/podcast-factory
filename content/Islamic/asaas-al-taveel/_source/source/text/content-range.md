---
schema_version: 1
book_slug: asaas-al-taveel
emitted_by: claude-on-mac-studio-primary (Asif's resume A approval, 2026-05-21)
emitted_at: 2026-05-21T13:50:00Z
---

# Content range — asaas-al-taveel

Per `operator-review.md` §7 (Asif approved recommended defaults 2026-05-21). Phase 0d/0e/11 honor this once P4.10 ships; until then this file is a forward-looking artifact (per `operator-review.md` §8 caveat).

```yaml
body_starts_at_page: 33      # Chapter 1 (Ādam) opens here; refined line 398
body_ends_at_page: 368       # Chapter 6 (Muḥammad) closes here; refined line 8091
include_author_preface: false  # author's intro pp. 21-27 content is in refined L213+; page anchors restored 2026-05-21 via Option-A splice
include_author_toc: false      # author's own TOC at pp. 369-372 — structural-only
front_matter_summary: |
  Pages 1-32: cover (1-4), editor's intro by Arif Tāmir (5-20), author's
  introduction (21-27 — content at refined L213+, page anchors restored
  via Option-A semantic splice 2026-05-21; win-003 page-marker stripping
  fully recovered for this window).
back_matter_summary: |
  Pages 369-408: indexes — names of prophets/figures clusters at pp. 402-408
  (cross-reference for EP01's glossary). Pages 409-416: French editor's
  intro re-OCR'd as if body content (Phase 0a artifact; pure duplication).
```

## §2 page-marker gap status (post-Option-A splice 2026-05-21)

| Window | Input pages | Status | Resolution |
|---|---|---|---|
| win-003 | 19-27 (editor's intro tail + author's intro) | ✅ RESTORED | Semantic-alignment splice from raw-extract.md anchors; 9 of 9 page anchors now in refined |
| win-007 | 53-61 (Ādam cycle body) | ⚠ DEFERRED | Body content; will be processed by Phase 0c/0d/0e as continuous prose; per-page citation precision degraded for this span only |
| win-010 | 80-87 (Nūḥ cycle body) | ⚠ DEFERRED | Same — body content; one hallucinated marker present (sanity-check during Phase 0d) |
| win-016 | 130-139 (Ibrāhīm cycle body) | ⚠ DEFERRED | Same |
| win-019 | 161-169 (Ibrāhīm/Mūsā body) | ⚠ DEFERRED | Same |
| win-029 | 252-258 (Mūsā cycle body) | ⚠ DEFERRED | Same |
| win-038/039 | 323-335 (Muḥammad cycle body) | ⚠ DEFERRED | Same — includes the John Paraclete quote at refined L7135 |
| win-046 | 379-384 (back-matter) | ⚠ MINOR | Lost 1 marker (p. 382); back-matter is SKIPPED per body_ends_at_page=368, so not citation-critical |
| win-049 | 407-416 (French RTL tail) | ⚠ MINOR | Lost 1 marker (p. 410); French tail is SKIPPED per body_ends_at_page=368, so not citation-critical |

**Net citation precision after Option-A partial splice**: Editor's intro + author's introduction (pp. 1-27) is fully anchored. Body chapters 1-6 (pp. 33-368) are anchored at chapter boundaries and at all preserved page anchors; ~58 pages of body content (within 5 windows) are unanchored but content is intact and Phase 0c/0d/0e can process them as continuous prose.

## Approved §§ summary

| § | Decision | Approved by | Notes |
|---|---|---|---|
| 1 | No specific translation issues flagged | Asif default | — |
| 2 | Option A (re-run/splice) — applied to win-003 only (pp. 19-27); other windows deferred as body content | Asif option A | Resume default per operator-review.md |
| 3 | 12 pre-seeded glossary terms accepted | Asif default | Will land in `_system/concept-glossary.md` during Phase 0e |
| 4 | 11 pre-seeded pronunciation hints accepted | Asif default | Will land in `_system/mangle-map.md` during Phase 0e |
| 5 | No free-form notes | Asif default | — |
| 6 | Chapter slug `chNN-natiq-N-<topic>` (Recommended) | Asif default | Phase 0d will emit slugs per `chapters-rationale.md` mapping |
| 7 | Body 33-368; skip front matter + back matter + French RTL tail | Asif default | This file |
| 8 | Approved + Option I (resume now, accept ~$5-7 LLM overhead from whole-transcript processing pending P22.impl/P4.10 ship) | Asif option I | Phase 0c launches next |
