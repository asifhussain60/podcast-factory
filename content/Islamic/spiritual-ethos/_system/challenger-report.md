# Podcast Challenger Report

**Book:** spiritual-ethos
**Run:** 2026-08-06 23:20 (challenger v2.6)
**Scope:** per-chapter the-veils-that-do-not-veil (EP10 / ch10b)
**Iterations:** 1 (of 5 max — no auto-fixable path; findings stable, intelligent break)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  ← detected from _system/series-config.yaml
source_tradition: islamic-scholarly → resolves to the `islam` (Nizari Ismaili) doctrinal pack (Hassan = Imam #1)

> Category S1 (async-safety) bypassed per invocation contract: the visible `orchestrate_book.py` process is THIS pipeline's parent, not a concurrent run.

## Prior P0 — RESOLVED (verified this run)

The 2026-08-06 20:45 run BLOCKED on T2/T3: the framing name-discipline block labeled Imam Ja'far al-Sadiq "the sixth Imam" (Twelver ordinal). The fixer pass corrected it to **"the fifth Imam"** in both the framing (line 9) and the chapter (line 61). Verified this run:
- **Source attribution:** `_system/source/text/refined-english.md:852` — "according to Imam Ja'far al-Sadiq … 'Everything has a limit …' … and adds that his father, Imam Muhammad al-Baqir, never ceased invoking." Speaker = al-Sadiq; his father = al-Baqir.
- **Ismaili lineage pack:** Hassan (1), Husayn (2), Zayn al-Abidin (3), al-Baqir (4), **al-Sadiq (5)**. "The fifth Imam" is correct; "the sixth" was the pan-Shia/Twelver ordinal that contradicts the enforced pack.
- **Deterministic re-check:** `_doctrinal.run_doctrinal_checks()` = CLEAN on both chapter and framing. `build_episode_txt.py::assert_doctrinal_clean()` = pass (exit 0).

## Auto-fixes applied (iteration-by-iteration)

None. No finding this run is in the deterministic auto-fix set. The framing-template clauses (M1/K1/R1/R3/R4/R5) are catalog-auto-fixable by insertion, but are deliberately NOT hand-patched here: this book's `00-framing.md` uses a compact format carried consistently across 12 sibling episodes and is signed by `.framing-sig`; inserting verbose blocks into one framing would desync the signature and diverge from the generator. The correct fix is book-wide in the framing generator's template. Surfaced as P2.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### F25-APPARATUS-TABLE — 99-show-notes.md missing the Name and Title Preservation Table
- **File:** content/Islamic/spiritual-ethos/_system/episode-drafts/EP10-the-veils-that-do-not-veil/99-show-notes.md
- **Context:** Build flagged `no '## Name and Title Preservation Table' section header`. F25 wants the written-layer crosswalk (preserved Arabic / transliterations → audio labels) that the TTS-safe audio omits. Published apparatus only; not uploaded to NotebookLM. The challenger does not edit show-notes.
- **Suggested fix:** Author adds the `## Name and Title Preservation Table` section to 99-show-notes.md.

#### N3 — 3 pronunciation terms not settled in the cross-book ledger
- **Context:** Build NOTE — `Quran`, `Sufi`, `Fatimid` carry hand-authored entries in the framing `## Pronunciation` block but have no settled spoken form in the cross-book ledger.
- **Suggested fix:** Settle by ear: `python3 scripts/podcast/run_pronunciation_probe.py spiritual-ethos`. The framing's hand-authored entries are the interim audio guard; not an allowed-file edit for the challenger.

#### CS-P8 — cross-chapter passage duplication (book-scope; involves this chapter)
- **With `dhikr-the-polish-for-hearts`:** 3 shared 12-word passages. Sample begins "from lewdness and iniquity and the remembrance of God is" — this is the shared Qur'an 29:45 quotation (liturgical formula), benign scripture overlap.
- **Note:** the earlier `forgetting-the-self-and-the-name` overlap (the Nasir-i Khusraw ta'wil passage) was reworded by the fixer and no longer appears in the CS scan — resolved.

#### CS-P10 — over-dense: 5 concept sections (target ≤3) (book-scope)
- **File:** chapter H2 map — 5 concept sections vs the ≤3 target. `density_standard: 2` book. Advisory here (the $0 preflight gate owns halting); surfaced for the set view.

#### CS-P5 — chapter-set word-count variance 50% (book-scope)
- min=5,006, max=10,109 words; >30% target. Authoring/resegmentation decision at book level, not a single-chapter fix.

### P2 (advisory)

- **Framing template gaps (M1 partial / K1 / R1 / R3 / R4 / R5):** the framing's `## Do not` block names the core surprise/modernize/anti-background/anti-cross-episode denials (Twitter, social media, algorithm, "wow", "right?") but not the full canonical DENY-modernize platform list, and it carries no explicit interruption-avoidance clause, separate-prep-illusion clause, sentence-cadence directive, formal-transition DENY list, or positive "DO use modern-life analogies" permission paragraph. Not hand-patched (`.framing-sig` desync + sibling-framing divergence); recommend adding to the framing generator's template if wanted book-wide.
- **A3 (translator provenance):** Qur'anic verses are rendered in plain English with no named external translator. These are the source author's (Shah-Kazemi's) own renderings woven into his exposition, so naming Yusuf Ali/Pickthall would be inaccurate. Consistent with the book's `faithful` convention; noted, not blocking.
- **CS-P6 (cross-book term bleed):** common Islamic vocabulary (`tawhid`, `walaya`, `qutb`, `vicegerent`, `Ghadir Khumm`, `al-Sijistani`) across the set matches other books' mangle-maps. Almost certainly false positives on shared terminology; surfaced for human review, never auto-stripped. This chapter itself is not among the P6 hits.
- **B5 (em-dashes):** the chapter prose uses em-dashes (28). The build gate (code authority) does not flag them for book-chapter sources, and the prose is deliberately authored; not auto-fixed.

## Health metrics

| Chapter | Words | Quran citations | Tier diversity | Arabic transliterations (build-flagged) | Inline phonetic parens | Arabic script |
|---|---|---|---|---|---|---|
| ch10b-the-veils-that-do-not-veil | 5,664 | 12 (all plain-English `(chapter N, verse M)`) | 5+ (Qur'an, Imam/Nahj, Sufi ×3, Ismaili, Prophet) | 0 (prior 5 rendered to English labels) | 0 | 1 (ta'wil تأويل) |

Chapter word count (5,664) is inside the contract band `5300-9500`; build passed exit 0. Framing/episode = 714 words (within cap). Doctrinal CLEAN (chapter + framing). N1 clean (no inline phonetic parens); N6 satisfied (Arabic script present). Arc: hook (standing paradox) → the veils that do not veil → nearness/incomparability → the quintessence of worship → paradox+practice synthesis → radical self-effacement close (complete). No meta-prose tells caught by the build gate; no invented dialogue. Q1/Q2 host roles correct (A=scholar male, B=seeker female); H1/H2/H3 present; M2 present.

## Convergence

Iteration 1 terminal: zero auto-fixable findings, all remaining items are author/generator/book-scope decisions. Intelligent break. Verdict SHIP-WITH-CAUTION — no P0; 5 P1 (all author/book-scope, none blocking a clean upload of this chapter).
