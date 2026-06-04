# Source map CORRECTION (discovered 2026-05-29 via OCR)

The filenames + SOURCES.md roles are MISLABELED. Verified by OCR + character analysis:

| Filename | Labeled as | ACTUAL content (verified) |
|---|---|---|
| `arabic-original.pdf` (15pp) | Arabic original | ✅ Arabic original (al-Ghazali) |
| `english-superior.pdf` (160pp) | English translation | ❌ **Arabic** — a 2nd Arabic edition w/ commentary (Dar al-Bashair, "Adab al-Muta'allim wa'l-'Alim", 2010); 100% Arabic script |
| `scholarly.pdf` (65pp) | Scholarly/commentary | ❌ **English** — an academic English translation; 95% Latin, structured by Roman-numeral sections (I–XVII…) with dense footnotes |

## Implications for intake (WC8.1)
- The multi-source set is really: **two Arabic editions** (original + commentary) + **one English
  academic translation**. There is NO modern English source matching the prior run's chapter prose.
- The three sources have **DIFFERENT structures**: the English uses Roman-numeral sections (I–XVII),
  the Arabic editions differ, and the prior pipeline run produced its own **5-chapter** scheme
  (ch01–ch05). Aligning them into a common-denominator core + a single chapter scheme is the real
  intake/reconcile reasoning (content-aware boundaries) — not a mechanical split.
- The English academic translation is an OLD register ("O youth…", "The Vitalizing of the Sciences
  of Religion" = Ihya); the editor's augmented chapters are a MODERN rendering from the prior run.
  So source→augmented spans both a translation and a re-voicing.

## OCR status (cached, local-only)
All three OCR'd via Azure Doc Intelligence S0 → `ocr/{arabic,english,scholarly}.md`. Cost ledger:
`_system/cost-ledger.json` (~$0.37 total). Re-runs are cached (no re-spend).

## TODO when convenient
Rename the files to their true roles (or fix SOURCES.md) so future runs don't trust the labels.
