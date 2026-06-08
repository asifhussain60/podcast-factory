---
schema_version: 1
book_slug: asaas-al-taveel-vol-1
emitted_by: volume-scaffold-2026-06-08
emitted_at: 2026-06-08T00:00:00Z
---

# Content range -- asaas-al-taveel-vol-1

```yaml
body_starts_at_page: 33      # Chapter 1 (Adam) opens here; transcript line ~398
body_ends_at_page: 75        # Adam cycle closes here; transcript line 1013
include_author_preface: false  # author's intro pp. 21-27 content is in transcript L213+; page anchors present
include_author_toc: false      # no TOC in this volume slice
front_matter_summary: |
  Pages 1-32: cover (1-4), editor's intro by Arif Tamir (5-20), author's
  introduction (21-27). Included in the transcript slice as context;
  not counted as episode source material.
back_matter_summary: |
  None -- volume ends at page 75 (end of Adam chapter).
  Back matter (indexes, French intro) is in the full-book slug only.
```

## Volume notes

This volume covers the Pre-text (pages 1-32) and Chapter 1: Adam (pages 33-75),
split from the full-book asaas-al-taveel slug (pages 1-416).

Transcript line range: 1-1013 (1,013 lines, approximately 24,443 words).

Phase 0a and 0b were completed on the full-book slug. The transcript was sliced
by split_transcript_asaas.py --vol 1 and normalized by sanitize_text() (469
substitutions: typographic punctuation normalization).

## Page-marker gap status (inherited from full-book, relevant windows for Vol 1)

| Window | Input pages | Status | Notes |
|---|---|---|---|
| win-003 | 19-27 | Restored | Author's intro anchors present via semantic splice |
| win-007 | 53-61 | Deferred | Body content; continuous prose; per-page citation precision degraded for this span |
