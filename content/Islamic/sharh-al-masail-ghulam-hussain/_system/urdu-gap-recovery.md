# Urdu-source gap recovery — findings

Cross-reference of the five gaps flagged by the Arabic-source pipeline against
the Urdu edition (`_system/source/multi/ocr/urdu.md`, 145 pages), read directly
by Claude rather than through Azure's bulk translator (which came out too
garbled to use for ruling content — see `_system/source/multi/text/urdu-english.md`
for that raw pass, kept for reference only).

Nothing here has been written into any chapter file yet. This is the research
report Asif reviews before that happens.

## Summary

| Item | Status |
|---|---|
| 1. Sale/debt/trade chapter, "severely damaged second half" (riba doctrine, bankruptcy, hire, partnership, pre-emption, loan-for-use, deposit) | **FOUND — full recovery, ready to use** |
| 2. Pledge/shared-wall/marriage chapter, "badly damaged throughout" (pledge + written debt record, shared wall/land division, the marriage argument) | **FOUND — full recovery, ready to use** |
| 3a. The protected/forbidden-to-marry women (mahramat) | **FOUND — full Qur'anic citation recovered; the accompanying genealogy chart is still illegible (OCR flattens the table)** |
| 3b. The four guardians (wali categories) | **FOUND — ready to use** |
| 3c. The nine defects that void a marriage | **NOT a transmission gap** — this Urdu edition ALSO doesn't list them; the author himself refers readers to a different book, *Da'a'im al-Islam*, for the details. Both editions defer on purpose. |
| 3d. The "four divorced women" | **Possible match, not certain** — the only "four women" ruling found (triple-divorced-without-halala, known-forbidden, widow in 'iddah, woman in ihram) only partly fits "divorced women" as a category. Needs a judgment call, not an automatic accept. |
| 3e. The number in the broken divorce directive | **NOT FOUND** — the original gap description doesn't give enough location context to search reliably. |
| 4. *Ila'*, *zihar*, *li'an* definitions | **Not a transmission gap either — the author explicitly declines to cover these three, by name, in his own text**, saying he'll only explain divorce/'iddah/khul' "since these are generally what is needed in practice." This is authorial choice, present in both editions. |
| 4. The "eighth class" of inheritance heirs | **UNCERTAIN** — this edition's inheritance section is headed only through a "fourth class"; no explicit "eighth class" heading was found. May be a different numbering scheme, or a genuine absence. |
| 4. Uncle/aunt inheritance shares | **FOUND but still badly OCR-damaged in this edition too** — the same table-flattening problem as the Arabic source. A fragment survives (paternal/maternal sides splitting a third/two-thirds pattern) but not a clean, complete rule. Needs a column-aware re-OCR before it's usable, not a translation fix. |

## What this means for chapters 2–5

- **Chapters 2 and 3 can be rebuilt now** — both flagged gaps recovered in full from the Urdu edition, cleanly.
- **Chapter 4** gets two solid recoveries (mahramat, four guardians) plus one genuinely resolved non-gap (the nine defects were never covered by the author at all — that's a fact worth stating in the book rather than a hole to fill). Items 3d and 3e stay open.
- **Chapter 5** gets one important correction: *ila'*/*zihar*/*li'an* were never a transmission failure — the author skipped them on purpose in both editions. The uncle/aunt table and the "eighth class" question remain genuinely unresolved.

Full translations and page references for each FOUND item are in the
extraction agent's report (session transcript) — ask Asif before pasting the
long verbatim passages into any chapter; they should go through the same
`translation_edition` fidelity gates as everything else, not be hand-spliced in.
