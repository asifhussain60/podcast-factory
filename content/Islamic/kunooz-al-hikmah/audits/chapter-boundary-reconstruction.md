# Chapter Boundary Reconstruction

Date: June 24, 2026
Book: Kunooz al-Hikmah

## Decision

The chapter set was re-evaluated against the approved concept-density rule: each chapter should carry no more than three teaching concepts, with opening hooks and landing summaries treated as structural frames rather than new concepts.

No teaching concept was moved across chapters. Whole-section relocation was rejected because it would break already-approved doctrinal arcs and create thinner neighboring chapters. The imbalance came from boundary labeling and overlong frame prose, not from misplaced doctrine.

## Reconstruction Applied

- Chapter 1: reclassified the threshold astonishment as the opening frame.
- Chapter 3: reclassified and tightened the wall-and-map setup as the opening frame.
- Chapters 5, 6, 7, 8, and 9: reclassified final synthesis sections as chapter landings.
- Chapter 9: tightened landing and closing frame prose to bring the raw chapter-size spread under the set-balance threshold.

These edits preserve all teaching content while ensuring the auditor reads each chapter as three teaching concepts plus frame material.

## Validation

`chapter_density_audit.py --slug kunooz-al-hikmah --violations-only` reports: all chapters within density target.

Final chapter concept counts:

| Chapter | Words | Teaching concepts | Status |
|---|---:|---:|---|
| 1 | 4,734 | 3 | PASS |
| 2 | 4,476 | 3 | PASS |
| 3 | 6,327 | 3 | PASS |
| 4 | 5,985 | 3 | PASS |
| 5 | 5,910 | 3 | PASS |
| 6 | 4,588 | 3 | PASS |
| 7 | 5,750 | 3 | PASS |
| 8 | 5,929 | 3 | PASS |
| 9 | 6,389 | 3 | PASS |
| 10 | 6,006 | 3 | PASS |
| 11 | 5,896 | 3 | PASS |
| 12 | 5,584 | 3 | PASS |
| 13 | 4,696 | 3 | PASS |

## Boundary Rule For Future Passes

When a section only introduces the chapter's question, names the concepts that follow, or summarizes what the chapter has landed, it should be framed as an opening or landing section. It should not be counted as one of the three teaching concepts unless it introduces new doctrine of its own.
