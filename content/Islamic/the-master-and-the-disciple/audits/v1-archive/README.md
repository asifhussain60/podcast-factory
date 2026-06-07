# V1 Archive — The Master and the Disciple

Git tag: `archive/the-master-and-the-disciple-v1`  
Commit: `b8dea3f80dd75f79c9ecb8934c4d5d484d0d732b`  
Archived: 2026-06-07

## What V1 was

Full pipeline run completed 2026-05-24 → 2026-05-25. Six episodes shipped via NotebookLM.

| Chapter slug | Words |
|---|---|
| the-call-and-the-covenant | ~9,650 |
| will-command-and-the-seven | ~10,800 |
| world-hereafter-and-the-right-of-wealth | ~10,550 |
| the-greater-shaykh-and-the-naming | ~10,960 |
| father-revealed-and-the-faces-of-seeking | ~9,740 |
| justice-monotheism-and-the-guardians | ~10,840 |

Approach: 6-chapter segmentation; doctrine `v4 + v2.2 + F30 + scaffold-retirement`. Phonetics-first pipeline. Socratic-dialogue archetype.

## Contents of this archive

- `chapters/` — V1 enriched chapter txt files (ch01–ch06)
- `episodes/` — V1 episode (framing) txt files (EP01–EP06)
- `notebooklm-scaffolding/` — V1 chapter upload bundles (ch00–ch07, the files uploaded to NotebookLM)
- `per-episode-audits/` — V1 Claude + Gemini audit reports per episode + 0g summary

## What is NOT here (still in audits/)

- `audits/ab-reference/` — original pre-podcast chapter transcripts (Chapter_1..7 + audio transcript); these are the raw English source used as input to V1
- `audits/baseline-v2.1/` — v2.1 challenger baseline
- `audits/final-review-report.md` + `audits/format-decision-matrix.draft.md` — V1 editorial notes

## How to diff V1 vs V2

```bash
# Compare a specific episode:
diff audits/v1-archive/episodes/EP01-the-call-and-the-covenant.txt \
     episodes/EP01-the-call-and-the-covenant.txt

# Compare all chapters at once:
for f in audits/v1-archive/chapters/*.txt; do
  name=$(basename $f); echo "=== $name ===";
  diff $f chapters/$name | head -20; done
```

To recover the full V1 state in git:
```bash
git checkout archive/the-master-and-the-disciple-v1 -- content/Islamic/the-master-and-the-disciple/
```
