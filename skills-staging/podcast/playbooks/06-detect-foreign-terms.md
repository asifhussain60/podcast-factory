# Stage 06 — Detect Foreign Terms

**Purpose:** Identify every non-Latin-script term, phrase, and devotional expression in the source so they can be phonetically transcribed in Stage 07. The skill is script-family-agnostic — Arabic, Hebrew, Sanskrit, Greek, Persian, Urdu, Mandarin (Han), and any other non-Latin script.

## Input

- `WORK_DIR/_cleaned/normalized.md`

## Output

- `WORK_DIR/_lexicon/detected-terms.yml` — every detected non-Latin term with location and language-family classification.
- `WORK_DIR/_lexicon/script-summary.md` — overview of which scripts appear in this source.

## Detection method

### 1. Unicode block scanning

Scan the cleaned text for characters outside the Basic Latin and Latin-1 Supplement blocks. Group hits by Unicode block:

| Unicode block | Script family | Notes |
|---|---|---|
| Arabic (U+0600–U+06FF) + Arabic Supplement | Arabic | Includes Persian, Urdu when they use Arabic script |
| Hebrew (U+0590–U+05FF) | Hebrew | |
| Greek (U+0370–U+03FF) + Greek Extended | Greek | |
| Cyrillic (U+0400–U+04FF) | Cyrillic | |
| Devanagari (U+0900–U+097F) | Sanskrit / Hindi / other | |
| CJK Unified Ideographs (U+4E00–U+9FFF) | Han (Chinese) | |
| Hiragana, Katakana | Japanese | |
| Hangul Syllables | Korean | |
| Bengali, Tamil, Gujarati, Gurmukhi, etc. | Indic scripts | |
| Coptic, Syriac, Aramaic | Ancient/liturgical | |

For each script family detected, record:
- Total character count.
- Number of distinct terms (whitespace-separated runs).
- Sample locations (first 5 occurrences with line numbers).

### 2. Term boundary detection

For each non-Latin character run:
- A "term" is bounded by whitespace, Latin script, or punctuation.
- For scripts without whitespace word boundaries (e.g., Chinese, Japanese, Thai), use script-appropriate segmentation (jieba for Chinese, MeCab for Japanese) — if these libraries aren't available, treat each consecutive non-Latin character group as one term and flag in script-summary.md.

### 3. Phrase detection

Some entries are multi-term devotional phrases (e.g., الحمد لله رب العالمين). Detect by:
- Two or more non-Latin terms separated only by whitespace and Arabic-script punctuation.
- Phrase appears in a context that suggests devotional or liturgical use (preceded by quote marks, "saying:", "exclaimed:", "praised:", etc.).
- Phrase appears in the master lexicon's devotional phrases section already.

Mark detected phrases as `type: phrase` rather than `type: term`.

### 4. Language disambiguation

Some scripts serve multiple languages. Disambiguate where possible:
- Arabic script + Persian-specific characters (ژ، گ، چ، پ) → Persian
- Arabic script + Urdu-specific characters → Urdu
- Devanagari + Sanskrit vocabulary → Sanskrit; else Hindi (default)
- Han script alone → Chinese; with hiragana/katakana → Japanese

If disambiguation is uncertain, record `language: "uncertain"` and let Stage 07 handle.

### 5. Master lexicon cross-reference

For every detected term, check if it (or its phonetic equivalent) already exists in `JOURNAL_DIR/reference/translations-glossary.md` Podcast Pronunciation Lexicon section:

- **Exact match** (original-script form in lexicon) → reuse existing phonetic + meaning.
- **Phonetic-equivalent match** (lexicon has only phonetic form, no original script) → match by transliteration similarity. If ≥ 0.85 confidence, reuse existing entry.
- **No match** → flag as new term; Stage 07 will generate phonetic, Stage 08 will propose for lexicon addition.

## detected-terms.yml format

```yaml
script_summary:
  arabic:
    distinct_terms: 47
    distinct_phrases: 8
    total_occurrences: 312
  greek:
    distinct_terms: 3
    distinct_phrases: 0
    total_occurrences: 5

terms:
  - id: T-001
    original: "الله"
    script: arabic
    language: arabic
    type: term
    occurrences:
      - section: 1
        line: 14
        context: "...praise be to الله, who..."
      - section: 1
        line: 47
        context: "...trust in الله and..."
    lexicon_status: matched
    matched_phonetic: "Allaah"
    matched_meaning: "God"

  - id: T-002
    original: "ولاية"
    script: arabic
    language: arabic
    type: term
    occurrences:
      - section: 3
        line: 12
        context: "...the ولاية of the Imam is..."
    lexicon_status: matched
    matched_phonetic: "Wilaayah"
    matched_meaning: "spiritual authority, guardianship"

  - id: T-003
    original: "قاضي النعمان"
    script: arabic
    language: arabic
    type: phrase
    occurrences:
      - section: 2
        line: 88
        context: "...as قاضي النعمان wrote..."
    lexicon_status: new
    proposed_phonetic: "Qadi al-Numan"
    proposed_meaning: "Qadi al-Numan, Fatimid jurist (10th century)"
    needs_lexicon_proposal: true
```

## script-summary.md format

```markdown
# Script Summary — [Source Title]

Scripts detected in this source:

## Arabic
- 47 distinct terms, 8 distinct phrases, 312 total occurrences
- Matched against master lexicon: 38 terms / 6 phrases
- New (will be proposed for lexicon): 9 terms / 2 phrases

## Greek
- 3 distinct terms, 0 phrases, 5 occurrences
- Matched: 0; New: 3

## Disambiguation flags
- 2 Arabic-script terms could not be cleanly disambiguated as Arabic vs Persian — defaulted to Arabic.
```

## What happens with detected terms

After this stage:
- **Matched terms** go to Stage 08 (pronunciation projection) directly using existing lexicon entries.
- **New terms** go to Stage 07 (phonetic generation) for transcription, then to Stage 08 for projection AND to Stage 12 staging file (`06-library-proposals.md`) for proposed lexicon addition.

## Failure modes

- A script is detected for which the skill has no transliteration support → flag in `script-summary.md`, write `WORK_DIR/UNSUPPORTED-SCRIPT.md` listing what's needed, but continue (terms will remain as-is in non-podcast outputs; podcast-ready output will substitute `[term: meaning]` placeholders pending user resolution).

## What this stage does NOT do

- Does not generate phonetic spellings (that's Stage 07).
- Does not modify the cleaned text (Stage 12 does substitutions for audio output).
- Does not propose lexicon additions (Stage 08 / Library Cross-Pollination handles that).
