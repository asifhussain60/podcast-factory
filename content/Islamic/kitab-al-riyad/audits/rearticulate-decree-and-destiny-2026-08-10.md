# Rearticulation audit — "Decree and Destiny" (chapter key: `decree and destiny`)

**Date:** 2026-08-10
**Verdict:** KEPT (second attempt succeeded; the prior attempt's revert is resolved)

## Baseline (pre-run, machine-base translation still sitting in book.md)

- Word count: 4,347 (script) / 4,342 (engine's own base count)
- Arabic-script runs (engine counter, `_book_compose._arabic_run_count`): 53
- Speech-tag pattern: one paragraph per turn — "The author of al-Islah said:", "The author of al-Nusrah said:", "We say:", each followed by its own paragraph
- Enumeration: sixteen numbered "Section N of Chapter Eight" subheadings, unchanged in count and order
- Signature images: the tailor cutting cloth (decree/destiny as estimation vs. elaboration); the pen/tablet/Writer correspondence for the verse "We have created everything according to a measure"; the leaning-wall parable for "I flee from the decree of God to His destiny"; the fire-to-water flight image
- Prior failure: pipeline gate `fluency-14: Arabic runs dropped (57<58)` — one Arabic run vanished in the first rewrite, so the whole chapter reverted and book.md still held the raw machine-base translation going into this run

## What the second run did

- Ran `rearticulate_chapter.py kitab-al-riyad "decree and destiny" --json`
- Result: `status: adapted`, `gates: []`, `windows: 1`, `windows_kept: 1`
- Output word count: 4,173 (about 96% of source length — normal tightening, not abridgement)
- Sidecar `_system/composer-edits.json` recorded the edit for chapter key `decree and destiny`, `saved_at: 2026-08-10T15:05:07Z`, matching the live `book/book.md` content exactly

## Judged against REQ-BA-*

- **REQ-BA-010/020 (lucid modern English):** Confirmed. Calqued constructions are gone — e.g. "As for the saying that the decree is prior... this is an error" became "Those who say decree comes first and destiny second are mistaken." Passive, Arabic-mirroring syntax throughout ("the upshot of his saying is this," "as we have described") was recast into direct, active, contemporary prose without softening the technical argument.
- **REQ-BA-040 (speech and quotation integrity):** Confirmed. Every "The author of al-Islah said:" / "The author of al-Nusrah said:" / "We say:" tag survived, same speakers, same boundaries. Both Quranic ayat and their translations are byte-for-byte identical to the source (`قضي الامر الذي به تستفتيان`, `فَإِذَا قُضِيَتِ ٱلصَّلَوٰةُ`, `إِنَّهُمْ يَرَوْنَهُۥ بَعِيدًۭا وَنَرَاهُ قَرِيبًا`, `إِنَّا كُلَّ شَىْءٍ خَلَقْنَهُ بِقَدَرٍۢ`, `يَمْحُوا۟ ٱللَّهُ مَا يَشَآءُ وَيُثْبِتُ`, `أَفِرُّ مِنْ قَضَاءِ اللَّهِ إِلَى قَدَرِهِ`, `فَوَجَدَا فِيهَا جِدَارًۭا يُرِيدُ أَن يَنقَضَّ فَأَقَامَهُۥ`), including the Prophetic hadith "I flee from the decree of God to His destiny."
- **REQ-BA-050 (signature images intact):** Confirmed. All four images checked in the baseline are still images, not flattened into abstraction: "Decree is like a garment that the tailor first estimates... before he cuts it he estimates it, and he adds and subtracts, widens and narrows"; the Writer/Pen/Tablet correspondence ("the Writer corresponds to إِنَّا... the Pen corresponds to the Intellect... the writing corresponds to the letters"); the leaning wall ("a structure that has leaned so far that it is about to fall... he set it up straight"); and the fire/water flight ("as a man flees from fire, which is a sign of support, to water, which is a sign of exposition").
- **REQ-BA-070 (no variant spellings/terms):** Confirmed. "Decree," "destiny," "Ipseity," "Enunciators," "Executors," "Imams," "the Speaker," "the Foundation" all render exactly as the rest of the book renders them — no new spelling introduced.
- **REQ-BA-100 (one paragraph per speech turn):** Confirmed. Structure matches the original one-turn-per-paragraph pattern under each of the sixteen "Section N" headings.

## The Arabic-retention failure specifically

- Recomputed the engine's own Arabic-run counter against both the pre-run book.md text (via `git show HEAD:...`) and the new sidecar body: **53 runs in, 53 runs out** — no run dropped this time. This is the exact gate that reverted the first attempt; it now passes clean.
- Non-blocking `comprehension_flags` were reported (ambiguous unnamed "He said:" referents in Sections Eleven/Twelve/Fourteen, inherited from the source's own elliptical attribution, not introduced by the rewrite) — these are informational notes, not REQ-BA failures, and don't require action.

## Where this leaves chapter 14

`book/book.md` now holds the rearticulated prose (not the raw machine-base translation that was there before this run), and `_system/composer-edits.json` carries the durable sidecar entry (`saved_at: 2026-08-10T15:05:07+00:00`) that a future re-compose will replay rather than regenerate. Note: `_system/book-fluency-report.json`'s entry for this chapter still displays the OLD failed-run's numbers (`base_words: 4325`, `gates: ["fluency-14: Arabic runs dropped (57<58)"]`) under a re-stamped `status: "composer-edit"` — this is a historical/cosmetic artifact of how that report preserves the last full-pipeline pass before a composer edit supersedes it, not a live gate failure. The live gate state (from the run itself and from independently recomputing the Arabic-run count against both texts) is clean.
