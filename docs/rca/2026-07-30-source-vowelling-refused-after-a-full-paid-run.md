> Template from: Betsy Beyer, Chris Jones, Jennifer Petoff, and Niall Richard Murphy. ["Site Reliability Engineering."](https://landing.google.com/sre/book/chapters/postmortem.html).

# A full paid vowelling run was refused at the last gate and discarded (RCA-004)

### Date

2026-07-30 (incident window: 11:31 AM – 12:33 PM EST)

### Authors

Claude (investigation + fix), reviewed by Asif

### Status

RESOLVED 2026-07-30. Both root causes fixed and pinned by shared fixtures in
both halves of the vowelling mirror pair. Re-run relaunched 12:36 PM EST.
Open corrective action: AI-3.

### Summary

The first real run of the new source-vowelling pass over
`the-master-and-the-disciple` completed all 1,360 model calls and was then
refused wholesale by the file-level structural check: the output had 2,101 lines
where the source had 2,106. The refusal was CORRECT — five lines really were
lost — but the pass discarded its entire output, so an hour of wall clock and the
book's whole model spend had to be paid again to find out why.

Two independent defects, both in code added the same day, both in the blind spot
the file-level check exists to cover.

### Impact

No content was corrupted and nothing incorrect was published: the check refused
the write and left `_system/source/ocr/raw-extract.md` untouched. The cost was
~62 minutes of wall clock and one book's worth of Gemini 2.5 Pro calls, thrown
away rather than retained for diagnosis. No other book was affected; the
finished-book backfill (`vowel_book.py`), committed earlier the same session, was
never at risk because it does not run the file-level check.

### Root Causes

**1. `reflow_to_source_whitespace` mis-aligned on an orphan combining mark.**
The repair walks source and candidate in parallel, taking whitespace from the
source and letters-with-their-marks from the candidate. When looking for the
candidate's next letter it skipped whitespace but NOT marks. A scan can leave a
combining mark with no letter under it — one run in this OCR literally begins
with a bare sukun (U+0652) — and that orphan was consumed AS a letter. Every
later letter was then off by one, the walk ran off the end of the candidate, and
the function took its "cannot align" branch and returned the candidate unchanged:
the model's collapsed single line. `rejection_reason` cannot catch that, because
`skeleton()` normalises whitespace before comparing — which is precisely why the
reflow exists. Two lines lost.

**2. The mushaf path never went through any reflow.** A Qur'anic run is replaced
by canonical text from `mirror.db`, and `mushaf_vocalisation` joins the verse's
words with single spaces. A verse the book prints across two lines came back as
one. The character-level reflow could not have helped even if it had been called:
the mushaf is Uthmani, so the letters legitimately differ, the skeletons do not
match, and the function correctly declines. Three lines lost across six verses,
counting each verse once per occurrence in the file.

### Trigger

Running `vowel_source.py the-master-and-the-disciple --apply` against a real OCR
for the first time. Neither defect can appear on the composed-book path
(`vowel_book.py`), whose input is English prose carrying short quoted runs: it has
no page-anchored line structure to lose and few multi-line runs.

### Resolution

- The candidate scan now skips marks as well as whitespace when advancing to the
  next letter, and CARRIES orphan marks into the output rather than dropping
  them, so mark count is preserved. Trailing orphans are handled symmetrically.
- Added `reflow_words_to_source_whitespace`, a word-level companion, and applied
  it to the mushaf replacement. Safe by construction: `mushaf_vocalisation` only
  returns a vocalisation when the words align one to one, which is exactly the
  precondition word-level reflow needs.
- Both fixes landed in `scripts/podcast/_vowelling.py` AND
  `plan-dashboard/scripts/lib/vowelling.mjs` in the same commit, pinned by new
  `reflow` and `reflowWords` groups in `vowelling.fixtures.json` that both halves
  run.
- Verified before re-running by replaying the whole real 2,106-line file through
  `vowel_runs` with a deterministic stand-in model: line delta 0, all 95 page
  markers intact, 1,360 runs marked, 6 verses from the mushaf. Zero spend.

### Detection

The file-level `_structure_complaint` check in `vowel_source.py` — added the same
day, specifically because the per-run gate cannot see page markers or line counts.
It caught both defects on their first real exposure and refused the write.

## Action Items

| ID | Action | Type | Status |
|---|---|---|---|
| AI-1 | Skip marks (and carry orphans) when advancing the candidate cursor | fix | DONE |
| AI-2 | Word-level reflow for mushaf replacements | fix | DONE |
| AI-3 | Keep the refused output at `<name>.vowelled.rejected.md` instead of discarding it, so a refusal is diagnosable without re-paying | mitigate | DONE |
| AI-4 | Pin both defects in the shared fixtures so the Python and JS halves cannot diverge on them | prevent | DONE |
| AI-5 | Verify a whole real file through a deterministic stand-in model before any paid source run | process | DONE |

## Lessons Learned

### What went well

The file-level check earned its place on day one. Both defects were invisible to
the per-run gate BY DESIGN — `skeleton()` normalises whitespace, so a collapsed
line is admissible at the run level — and the whole point of a second check at a
different altitude is to see what the first cannot. It refused the write, named
the reason, and left the provenance file untouched.

Replaying the real file with a deterministic stand-in model reproduced the exact
failure (−5 lines) at zero cost, and then proved the fix at zero cost. That loop
should be the default before any paid run over a whole book.

### What went wrong

A gate that refuses is only half a gate if it also destroys the evidence. The
first refusal cost a full re-derivation to investigate something the output
itself would have shown in seconds.

The reflow was tested against synthetic Arabic that was well-formed. Real OCR is
not: it carries orphan marks, stray digits, and page furniture. The fixture that
would have caught this — a run beginning with a letterless mark — came from the
real file, not from imagination.

### Where we got lucky

The mushaf defect alone loses only three lines, and the orphan defect only two.
Had either fired on a book whose Arabic source is not line-addressed, or had the
structural check compared only page markers and not line count, the loss would
have been silent and would have surfaced much later as a mis-sliced bilingual
edition.

## Timeline

All times EST, 2026-07-30.

- **11:31 AM** — `vowel_source.py the-master-and-the-disciple --apply` launched detached (a first attempt at ~10:52 AM was killed by a session restart; it wrote nothing, correctly).
- **12:12 PM** — liveness confirmed: 8 established sockets, CPU time advancing; network-bound, not hung.
- **12:33 PM** — run completes; `_structure_complaint` refuses: `line count changed (2106 -> 2101)`. No sibling written, working tree clean.
- **12:34 PM** — mushaf substitution identified as one cause; accounts for 3 lines once per-occurrence counts are included, not 5.
- **12:35 PM** — deterministic replay with a stand-in model reproduces −5 exactly; bisecting with `is_quranic` disabled isolates the remaining 2 to a single run beginning with a bare sukun.
- **12:36 PM** — both fixes in, replay shows delta 0; re-run relaunched.
- **12:5x PM** — fixtures + tests added to both halves; 1,825 Python and 21 JS tests green.

## Supporting information

- The offending run: `'ْ توكَل٦ على الله\nإذا عزمت، وتكلم بحكم إذا دعوت...'` — note the leading U+0652 with no letter beneath it, and the inline footnote digit `٦`.
- The verses that lost line breaks: `ليس كمثله\nشيء` (2 occurrences) and `الله عنده فوفاه\nحسابه` (1).
- Related: [[feedback_always_vowel_arabic]] (the rule this pass implements), and the
  same-session commit that fixed two *other* holes in the gate — an over-wide mark
  range that let Arabic-Indic digits be deleted as if they were marks, and the
  absence of any line-structure repair at all.
