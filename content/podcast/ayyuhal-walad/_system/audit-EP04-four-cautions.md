# Transcript Audit · EP04-four-cautions

**Transcript:** `podcast/ayyuhal-walad/transcripts/EP04-four-cautions.transcript.txt`
**Word count:** 3382
**Audit tool:** `scripts/podcast/audit_transcript.py` v1.0 (2026-05-17)

## Verdict: **REGRESSION**

- P0 hits (architecture failures): **7**
- P1 hits (drift signals): **31**

## Phonetic doublings · R-PHONETICS-OUT (P0)

Pattern: `Term, term-phonetic` — the hosts read the transliteration AND its respelled phonetic. Indicates either inline phonetics survived in the chapter file or the framing's `## Pronunciation` block was not in imperative form.

**Count:** 4

- `Al-Hazur, al-hazur`
- `Beware, beware`
- `beware, beware`
- `beware, beware`

## Mangled names (P0)

Known-mangling lookup: each canonical name is scanned against its empirically-observed mangled forms.

| Canonical | Mangled form | Count |
|---|---|---|
| `Ayyuhal Walad` | `a yuhal wallad` | 1 |
| `Riya` | ` rhea.` | 1 |
| `Ihya Ulum al-Din` | ` EI.` | 1 |

## Welcome-opening violations · R-WELCOME (P0)

**None detected.**

## Modernization injections · R-NOMODERNIZE (P1) · density 3.5 per 1k words

| Phrase | Count |
|---|---|
| `Twitter` | 1 |
| `X` | 1 |
| `algorithm` | 1 |
| `content creator` | 1 |
| `internet troll` | 1 |
| `reply guy` | 1 |
| `YouTube comment` | 1 |
| `quote tweet` | 1 |
| `quote tweeting` | 1 |
| `deep dive` | 1 |
| `modern digital lives` | 1 |
| `platforms like` | 1 |

## Surprise-noise loops · R-NOSURPRISE (P1) · density 5.3 per 1k words

| Phrase | Count |
|---|---|
| `Exactly` | 10 |
| `exactly` | 6 |
| `Wow` | 1 |
| `it's devastating` | 1 |

## Honorific repetitions · R-HONORIFIC-ONCE (P1)

Each form allowed exactly once per chapter; the transcript should reflect ≤1 expansion per honorific phrase form.

**None detected.**

## Abbreviated work titles · R-NO-ABBREVIATION (P1)

| Abbreviation | Count |
|---|---|
| `EI.` | 1 |

## Filler interjections · R-NOINTERRUPT (P2) · density 3.5 per 1k words

| Phrase | Count |
|---|---|
| `Right.` | 8 |
| `Yeah,` | 1 |
| `right,` | 1 |
| `Right,` | 1 |
| `right.` | 1 |

## Remediation cheat sheet

| Finding | Action |
|---|---|
| Phonetic doublings | Inspect chapter for surviving inline `(PHO-ne-tic)` parens; verify framing's `## Pronunciation` block uses imperative form per R-PRONUNCIATION-IMPERATIVE. |
| Mangled names | Add explicit `Pronounce "<canonical>" as "<phonetic>". Say it as one fluent word.` line to the framing's Pronunciation block. Check `content/_shared/arabic/03-arabic-english-manifest.md` for canonical spelling. |
| Welcome opening violations | Verify framing carries the R-WELCOME directive; tighten the Opening section to forbid the specific phrase. |
| Modernization injections | Extend the framing's `## Do not` block with the specific phrase; confirm R-NOMODERNIZE canonical list is present. |
| Surprise loops | Extend `## Do not` with the specific phrase; confirm R-NOSURPRISE canonical list is present. |
| Honorific repetition | Audit chapter file with `assert_honorifics_once_only` in `build_episode_txt.py`; strip 2nd+ expansions. |
| Abbreviated titles | Search-and-replace per the `FORBIDDEN_ABBREVIATIONS` map in `build_episode_txt.py`. |

