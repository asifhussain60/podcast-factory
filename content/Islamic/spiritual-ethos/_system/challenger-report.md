# Podcast Challenger Report

**Book:** spiritual-ethos
**Run:** 2026-08-06 (challenger v2.6)
**Scope:** per-chapter forgetting-the-self-and-the-name (ch11c) + EP11-forgetting-the-self-and-the-name framing
**content_profile:** islamic_scholarly  ← detected from _system/series-config.yaml
**Iterations:** 1 (of 5 max) — converged on first pass; no safe, non-regressing auto-fix available
**Verdict:** SHIP-WITH-CAUTION

> S1 async-safety gate intentionally bypassed for this invocation — it originates
> from within the parent orchestrate_book.py pipeline that spawned it (per invocation
> context). The parent orchestrator is the caller, not a concurrent independent run.

## Deterministic gates run (authoritative)

| Gate | Result |
|---|---|
| `build_episode_txt.py EP11` (chapter SOURCE + framing) | exit 0 — episode txt emitted; 2 P1 FLAGs + 1 NOTE |
| `check_chapter_set.py` (book scope) | 24 findings (1 P0 on a *different* chapter, 12 P1, 11 P2) |
| `_doctrinal.run_doctrinal_checks` (Category T) | 0 findings — clean |
| Host-parity Q1–Q4 (all 3 sibling framings) | consistent: Host A male/scholar, Host B female/seeker — clean |
| Markers A2/D5 · filler E4 · honorific O1 | clean (no [VERIFY]/[CONTEXT], no filler, honorifics symbol-form once) |

The 7,894-word chapter is IN the `extended` band (5,500–9,500) and is accepted as-is
by the build gate. Em-dashes (38 in chapter) are NOT flagged by current code and were
NOT altered — the legacy B5 auto-fix is not enforced by build_episode_txt.py v2.6.

## Auto-fixes applied

None. Rationale: the authoritative gates require no deterministic fix, and the framing
is deliberately hand-authored with constraints that boilerplate insertion would violate
(source-images-only analogies per Tone constraints; mandated 3× spine repetition via
R-RECURRING-THESIS). Auto-inserting R4/R5/K1/M1 clauses or rewriting 38 em-dashes would
be content authoring against the author's intent, not mechanical cleanup. All items below
are flagged for author resolution.

## Findings requiring author resolution

### P0 (blocks ship) — none on THIS chapter

> Book-scope note (surfaced, does NOT block the per-chapter verdict): `check_chapter_set.py`
> reports a P0 (CS4) on a **different** chapter — `the-letter-of-ali-to-malik-al-ashtar`
> is 10,109 words, over the `extended` band ceiling of 9,500. That chapter, not this one,
> must be rewritten to band or re-split. It is out of this per-chapter scope.

### P1 (ship-with-caution)

#### F20 / R-NO-ARABIC-TRANSLITERATION — Arabic transliterated names in the chapter SOURCE
- **File:** content/Islamic/spiritual-ethos/chapters/ch11c-forgetting-the-self-and-the-name.txt
- **Context:** build sampled `al-Hallaj, al-Kalabadhi, al-Kashani, al-Sadiq`; the chapter also carries `Bayazid, Rumi, Ibn al-'Arabi, Nasir-i Khusraw, al-Ghazali, Ibn 'Ata'illah, Abu 'Uthman, al-Kalabadhi` and the book title `the Mathnawi`. F20 doctrine wants these rendered as English audio labels in the SOURCE that NotebookLM reads. The framing's Name-discipline block already handles the audio side (English roles), but the uploaded chapter still carries the transliterations.
- **Suggested fix:** replace transliterated personal names / book titles in the chapter body with the English role labels the framing already defines (the early Sufi master / the Andalusian master / the reviver-jurist / the Persian poet / his treatise on extinction), or accept as a documented book-wide exception. Authoring decision.

#### F25-APPARATUS-TABLE — show-notes missing the Name and Title Preservation Table
- **File:** content/Islamic/spiritual-ethos/_system/episode-drafts/EP11-forgetting-the-self-and-the-name/99-show-notes.md
- **Context:** no `## Name and Title Preservation Table` header. F25 doctrine: every episode's show-notes carries the written-layer crosswalk (preserved Arabic / transliterations → audio labels) that the TTS-safe audio omits.
- **Suggested fix:** add the apparatus table to 99-show-notes.md (author/producer surface; challenger does not edit show-notes).

#### N3 — pronunciation ledger has no settled spoken form for `fana`, `baqa`
- **File:** content/Islamic/spiritual-ethos/_system/episode-drafts/EP11-forgetting-the-self-and-the-name/00-framing.md:15-16
- **Context:** the `## Pronunciation` block lists `- fana: fana` / `- baqa: baqa`, but neither term is settled in the cross-book pronunciation ledger (build NOTE).
- **Suggested fix:** settle by ear — `python3 scripts/podcast/run_pronunciation_probe.py spiritual-ethos` — which writes the answer to the ledger. Do not hand-edit the framing value (the build recompiles it).

#### CS8 — cross-chapter duplication with `the-veils-that-do-not-veil`
- **File:** content/Islamic/spiritual-ethos/chapters/ch11c-forgetting-the-self-and-the-name.txt
- **Context:** shares 3 distinct 12-word passages with `the-veils-that-do-not-veil` — same content taught twice. Sample: "a batin and the whole labor of the awakened intellect is the…" (the zahir/batin/ta'wil exposition).
- **Suggested fix:** cut the overlapping zahir/batin/ta'wil passage from one chapter so the teaching lands once. Authoring decision — never auto-stripped.

#### CS10 — chapter over-dense (6 concept sections; target ≤3)
- **File:** content/Islamic/spiritual-ethos/chapters/ch11c-forgetting-the-self-and-the-name.txt
- **Context:** concept H2s: The self that remembers · The reality of remembrance · Extinction in remembrance · The Name that is the Named · The effaced friend as the Name (+ synthesis + Closing). Density audit target is ≤3.
- **Suggested fix:** advisory — this is the extended-band closing chapter carrying two mysteries by design; either accept given the length band, or re-split at a concept seam via Phase 0d.

#### CS5 — chapter-set word-count variance 50% (>30%) [book-scope]
- **Context:** min 5,007 / max 10,109 words across the set; driven mainly by the over-band `the-letter-of-ali-to-malik-al-ashtar`.
- **Suggested fix:** rebalance the set (largely resolved by fixing the CS4 P0 above). Authoring decision.

### P2 (advisory)

- **CS6** — chapter contains `tawhid`, which matches `degrees-of-excellence`'s mangle-map (possible cross-book bleed). Almost certainly a false positive: `tawhid` is a common term of art AND is in this book's own `_system/glossary.yml` (with Arabic توحيد). Surfaced for human review; never auto-stripped.
- **Framing R4** — `## Do not` block does not name the formal-essay transitions (Firstly, Secondly, Furthermore, In conclusion, Moving on to, Lastly). Advisory hardening; NOT auto-inserted (build did not require it).
- **Framing K1** — no explicit interruption-avoidance ("conversation discipline") clause in Host dynamic. K2 (named filler words) IS satisfied via the Forbidden-first-words list.
- **Framing M1** — DENY-modernize list in `## Do not` is thin (Twitter, social media, algorithm only); canonical list also names TikTok/YouTube/"21st century"/etc. NOT auto-inserted — build validator passed the framing.

> Deliberately NOT flagged as findings: B5 em-dashes (not enforced by current code);
> R5 modern-analogy permission (would contradict the authored source-images-only Tone
> constraint); A1 hadith reference tails (this book's F20/English-only doctrine and the
> passing build gate intentionally omit bibliographic tails for TTS safety).

## Health metrics

| Chapter | Words | Band | In band? | Arabic script | Doctrinal | Pron. gaps |
|---|---|---|---|---|---|---|
| ch11c-forgetting-the-self-and-the-name | 7,894 | extended (5,500–9,500) | yes | yes (توحيد, تأويل) | clean | 2 (fana, baqa unsettled) |

## Convergence

Iteration 1 produced 0 auto-fixes and a stable finding set → intelligent break.
Verdict: **SHIP-WITH-CAUTION** — zero P0 on this chapter/framing; 6 P1 + 4 P2 flagged
for author resolution. The book as a whole carries one out-of-scope P0 (CS4 on
`the-letter-of-ali-to-malik-al-ashtar`) that must be resolved before a book-wide
SHIP-READY.
