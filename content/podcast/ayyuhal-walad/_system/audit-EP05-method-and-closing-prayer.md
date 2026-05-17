# Transcript Audit · EP05-method-and-closing-prayer

**Transcript:** `podcast/ayyuhal-walad/transcripts/EP05-method-and-closing-prayer.transcript.txt`
**Word count:** 3120
**Audit tool:** `scripts/podcast/audit_transcript.py` v1.0 (2026-05-17)

## Verdict: **REGRESSION**

- P0 hits (architecture failures): **18**
- P1 hits (drift signals): **20**

## Phonetic doublings · R-PHONETICS-OUT (P0)

Pattern: `Term, term-phonetic` — the hosts read the transliteration AND its respelled phonetic. Indicates either inline phonetics survived in the chapter file or the framing's `## Pronunciation` block was not in imperative form.

**Count:** 6

- `The, one-year limit is`
- `du'a, du'a`
- `you, you`
- `you, you`
- `tawakul, tawakul`
- `sahasita, sahasita`

## Mangled names (P0)

Known-mangling lookup: each canonical name is scanned against its empirically-observed mangled forms.

| Canonical | Mangled form | Count |
|---|---|---|
| `Ayyuhal Walad` | `ayyuhaw walad` | 2 |
| `Nahj al-Balagha` | `najah balala` | 1 |
| `Sahih Sitta` | `sahasita` | 2 |
| `Azwaj al-Mutahharat` | `aswaja al-mutaharat` | 2 |
| `Aisha Siddiqa` | `aisha siddhika` | 2 |
| `Fard al-ayn` | `fard al-an` | 1 |
| `Fard Kifaya` | `fard ki efaya` | 1 |

## Welcome-opening violations · R-WELCOME (P0)

| Phrase | Count |
|---|---|
| `Welcome to our` | 1 |

## Modernization injections · R-NOMODERNIZE (P1) · density 2.9 per 1k words

| Phrase | Count |
|---|---|
| `21st century` | 2 |
| `deep dive` | 2 |
| `social media` | 1 |
| `algorithm` | 1 |
| `screen time` | 1 |
| `notification` | 1 |
| `attention economy` | 1 |

## Surprise-noise loops · R-NOSURPRISE (P1) · density 3.5 per 1k words

| Phrase | Count |
|---|---|
| `exactly` | 4 |
| `Exactly` | 4 |
| `right?` | 2 |
| `it's fascinating` | 1 |

## Honorific repetitions · R-HONORIFIC-ONCE (P1)

Each form allowed exactly once per chapter; the transcript should reflect ≤1 expansion per honorific phrase form.

**None detected.**

## Abbreviated work titles · R-NO-ABBREVIATION (P1)

**None detected.**

## Filler interjections · R-NOINTERRUPT (P2) · density 2.2 per 1k words

| Phrase | Count |
|---|---|
| `Right.` | 4 |
| `Yeah,` | 1 |
| `right,` | 1 |
| `Right,` | 1 |

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

