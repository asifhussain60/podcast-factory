# Worked Examples (illustrative-only)

**Status:** Guidance, not normative. Every rule in this directory's other handbook files is book-agnostic; this file collects the **concrete illustrative blocks** that previously lived inside those rule files. The examples are drawn from real work on *Ayyuhal Walad* (the first podcasted book) — they are kept here for pedagogy. **No script, agent, or rule reads from this file.** Other books are NOT expected to mirror these examples; they exist to show the *shape* of what each rule produces, not to constrain what any one book must contain.

If you are onboarding a new book, read [`book-dir-layout.md`](book-dir-layout.md) for the canonical per-book shape and the normative rule files (`notebooklm-source-chapter-rules.md`, `notebooklm-customize-prompt-rules.md`, `enrichment-sources.md`) for what every chapter and customize prompt MUST satisfy. This file only shows *how those rules looked in practice on one book*.

---

## §1 — `extract_chapter.py` CLI usage

### Re-extract a book chapter (idempotent re-render)

```
$ python3 scripts/podcast/extract_chapter.py ch02-<slug>
# (contract already exists from prior run; bundle re-rendered deterministically)
Extracted EP02-<slug> from ch02-<slug>.txt
  Source bucket: <book-slug>
  Files unchanged: 7
```

Re-running with no contract change is a no-op. This is the idempotency promise.

### First run (contract stub flow)

```
$ python3 scripts/podcast/extract_chapter.py ch01-<slug>
NOTE: no contract found — wrote stub at content/podcast/library/<category>/<book-slug>/chapter-contracts/<slug>.yml. Edit it and re-run with --force.

# Edit the stub: fill audience, key_tensions, tone_constraints, title.

$ python3 scripts/podcast/extract_chapter.py ch01-<slug> --force
Extracted EP01-<slug> from ch01-<slug>.txt
  Source bucket: <book-slug>
  Episode draft: content/podcast/library/<category>/<book-slug>/_system/episode-drafts/EP01-<slug>
  Files written: 7
  Files unchanged: 0

Next: build the customize-prompt episode txt:
  python3 scripts/podcast/build_episode_txt.py content/podcast/library/<category>/<book-slug> EP01-<slug>
```

### Disambiguating an ambiguous chapter ref

```
$ python3 scripts/podcast/extract_chapter.py ch01-introduction
ERROR: chapter ref 'ch01-introduction' matches in 2 books:
    book-a/  →  content/podcast/library/books/book-a/chapters/ch01-introduction.txt
    book-b/  →  content/podcast/library/books/book-b/chapters/ch01-introduction.txt
  Disambiguate by passing `<book-slug>/ch01-introduction` or the full repo-relative path.

$ python3 scripts/podcast/extract_chapter.py book-a/ch01-introduction
Extracted EP01-introduction from ch01-introduction.txt
  Source bucket: book-a
```

---

## §2 — Per-episode scratchpad layout (v3.5)

| Skill | Canonical chapter (the SOURCE) | Per-episode scratchpad |
|---|---|---|
| podcast | `content/podcast/library/<category>/<book-slug>/chapters/ch##-<slug>.txt` | `content/podcast/library/<category>/<book-slug>/_system/episode-drafts/EP##-<slug>/chapter.scratch.md` |

The chapter file is the SOURCE; there is no separate `01-source-primary.md` under v3.5. The scratchpad mirrors the chapter and carries `@@` markers; refinement writes back to the chapter and strips markers.

---

## §3 — Name-alias clause for the customize prompt

The R-NAMEALIAS rule requires a Name discipline block in `00-framing.md` under "Pronunciation hooks". The block's shape is fixed; **what fills it is per-book**. Example from *Ayyuhal Walad* (Ghazali, 11th c.):

```
Name discipline. Use each long name in full ONCE on first occurrence, then
use the short alias for every subsequent reference:
  - Imam Abu Hamid Muhammad al-Ghazali  →  Ghazali
  - Hatim bin Ism al-Asamm              →  Haatim
  - Shaqiq al-Balkhi                    →  Shaqeeq
  - Sufyan al-Thawri                    →  Sufyan
  - <add any long name in this episode>
```

For a different book, the long names will be different. Aliases come from `content/_shared/arabic/05-name-alias-policy.md` if Arabic/Islamic, or from common usage otherwise.

---

## §4 — Pronunciation block for the customize prompt

The R-PRONUNCIATION-IMPERATIVE rule requires every line in `## Pronunciation` to start with `Pronounce "` or `Do not`. **What terms appear is per-book** — drawn from `BOOK_DIR/_system/source/text/_phonetics.md` (the per-book phonetic index built in Phase 0c). Example block from *Ayyuhal Walad*:

```
## Pronunciation

Pronounce "Ayyuhal Walad" as "EYE-yoo-hal WAH-lad". Say it as two fluent words.
Pronounce "Ghazali" as "ghaz-ZAH-lee". Say it as one fluent word.
Pronounce "Tasawwuf" as "ta-SAW-wuf". Say it as one fluent word. Do not spell it.
Pronounce "Tawakkul" as "ta-WAK-kul". Say it as one fluent word.
Pronounce "Ikhlas" as "ikh-LAAS". Say it as one fluent word.
[... one imperative line per term that appears in the chapter ...]

Do not read this guidance aloud. The phonetics above are for the voice model only.
```

A different book's block will name different terms. The canonical phonetic spelling for each term still comes from `content/_shared/arabic/03-arabic-english-manifest.md`; per-book overrides live in `BOOK_DIR/_system/pronunciation.md`.

---

## §5 — Empirical evidence motivating R-PHONETICS-OUT, R-NOMODERNIZE, R-NOSURPRISE

These three rules were added on 2026-05-17 after a transcript audit of the first five podcasted episodes of *Ayyuhal Walad*. Key empirical observations:

- **R-PHONETICS-OUT.** Inline `*Sunnah* (SOON-nah; …)` parens in the chapter produced systematic doublings in the audio — hosts said "Sunnah, soon-nah", "Sahih Sitta, sahasita", "Tasawwuf, tassel wolf". Moving phonetics out of the chapter and into the customize prompt's imperative block eliminated the doublings. Mangled names observed: `tassel wolf` (Tasawwuf), `shakestone noon mystery` (Shaykh Dhul-Nun al-Misri), `Najah Balala` (Nahj al-Balagha).
- **R-NOMODERNIZE.** Across the 5 transcripts, NotebookLM injected ≥14 modernizations — `internet troll`, `reply guy`, `quote tweeting`, `algorithmic envy machines in our pockets`, `content creator taking a massive sponsorship`, `11th century cognitive behavioral therapy`. The framing's soft prose directive ("do not modernize") was ignored; the DENY list of specific words enforced.
- **R-NOSURPRISE.** Surprise-loop phrases (`wow`, `it's chilling`, `it's devastating`, `right?`, `exactly`) appeared >40 times across the 5 episodes despite host-dynamic prose forbidding them. The DENY list enforced.
- **R-NO-ABBREVIATION.** Ghazali's *Ihya Ulum al-Din* was abbreviated in one chapter as `the Ihya`; the host called it `the EI`. Listeners cannot resolve unfamiliar contractions; full work titles required on every mention.

These observations are not unique to the book — any new book that introduces non-English vocabulary, classical-text register, or long author names will hit the same failure modes. The rules generalize; the evidence here just shows *one* book where the rules were first stress-tested.

---

## §6 — Debate-framing worked example (EP04 *Four Cautions*)

The debate format defined in [`debate-framing.md`](debate-framing.md) needs a concrete shape to read. Here is one from *Ayyuhal Walad*:

**Proposition.** Ghazali's prohibition on serving rulers is absolute and admits no exception, even for a sincere scholar invited to advise a just ruler.

**Host A — the orthodox jurist.** Position: the prohibition is categorical. Any contact with worldly power corrupts the heart's orientation. The four cautions are stated in their strongest form precisely because exceptions hollow out the rule.

Source moves available to Host A:
- The text of the four cautions, read in their imperative form.
- The supporting hadith on avoiding the doors of power.
- Ghazali's own statement that the cautions are meant to be ABSOLUTE for the seeker who is not yet established.

**Host B — the historically-grounded scholar.** Position: the prohibition is contextual. Ghazali means the rulers of his time (the late Abbasid courts of his decade), not all rulers in all conditions. A scholar of established interior life serving a just ruler at the ruler's invitation, for the limited purpose of correction, falls outside the prohibition.

Source moves available to Host B:
- Ghazali's own earlier service to viziers in Baghdad.
- The classical Islamic principle of `naseeha` (sincere counsel to leaders) attributed to the Prophet.
- The example of Imam Ali serving as caliph as the paradigm of just rule.
- Ghazali's distinction between *strong* and *weak* engagement with power earlier in the *Ihya*.

**Resolution.** `historical_division` — the tradition itself has held both readings, and the closing names this rather than pretending to a synthesis the tradition didn't reach.

This is illustrative, not prescriptive. Each debate-format episode is bespoke; the framing carries the proposition and positions specific to that chapter.

---

## §7 — Tier 1 enrichment whitelist (book-specific)

[`enrichment-sources.md`](enrichment-sources.md) §1 defines Tier 1 ("the author's own corpus") generically. Each book's actual Tier 1 list lives at `BOOK_DIR/_system/enrichment-whitelist.md`. For *Ayyuhal Walad* (Ghazali), that file enumerates:

- *Ihya Ulum al-Din* (Revival of the Religious Sciences)
- *Kimiya al-Sa'ada* (Alchemy of Happiness)
- *Munqidh min al-Dalal* (Deliverance from Error)
- *Mishkat al-Anwar* (Niche of Lights)
- *Bidayat al-Hidaya* (Beginning of Guidance)
- *Jawahir al-Quran* (Jewels of the Quran)
- *Arba'in* (Forty Steps)
- *Minhaj al-Abidin* (The Path of Worshippers)

A book by a different author lists that author's own corpus instead. The handbook does not name any one author's corpus.
