# Stage 07 — Generate Phonetic Transcriptions

**Purpose:** For every new term detected in Stage 06 (those marked `lexicon_status: new`), generate a podcast-ready English phonetic transcription.

## Input

- `WORK_DIR/_lexicon/detected-terms.yml` (entries with `lexicon_status: new`)

## Output

- Updated `WORK_DIR/_lexicon/detected-terms.yml` with `proposed_phonetic` and `proposed_meaning` filled for every new term.
- `WORK_DIR/_lexicon/phonetic-generation-log.md` — method used per term, alternatives considered.

## Phonetic style rules — uniform across languages

The skill produces **pronunciation-friendly** transcriptions optimized for English text-to-speech, not academically rigorous transliterations. The same term should always produce the same phonetic — deterministic.

### Universal style guidance

1. **Long vowels doubled.** Arabic `ā` → `aa`. Sanskrit `ī` → `ee`. Hebrew `ô` → `oo`.
2. **Avoid diacritics.** No macrons, breves, dots, or special marks in the output. English-keyboard letters only, plus hyphens for syllable separation.
3. **Hyphenate multi-syllable terms** where stress matters (for example, a three-syllable name like "[Name-Sec-ond]" or a four-syllable name like "[Al-Name-Pa-tronym]"). Single syllables stay un-hyphenated.
4. **Honor existing convention.** If a term has a widely-recognized English spelling that pronounces correctly (e.g., "Muhammad", "Buddha", "Krishna"), use it.
5. **Apostrophes for glottal stops** only when essential for distinct pronunciation: `Da'i`, `Ta'wil`.
6. **Capitalize proper nouns** including divine names, prophet names, place names.
7. **Avoid the letter Q** for the Arabic ق unless the term is widely known with Q (e.g., "Qur'an"). Prefer phonetic K-equivalents otherwise.
8. **Avoid X, KH, GH digraphs** when a simpler alternative reads correctly. Use them when no simpler form works (`Shaykh`, `Bakh-ta-ree`).

### Per-script transliteration tables

**Arabic / Persian / Urdu (Arabic script):**

| Arabic char | Phonetic | Notes |
|---|---|---|
| ا | aa (long) or a (short) | Context-dependent |
| ب | b | |
| ت | t | |
| ث | th | as in "thin" |
| ج | j | |
| ح | h | (heavier than ه but transcribed as h for clarity) |
| خ | kh | |
| د | d | |
| ذ | dh | as in "this" |
| ر | r | |
| ز | z | |
| س | s | |
| ش | sh | |
| ص | s | |
| ض | d | |
| ط | t | |
| ظ | z | |
| ع | (use vowel after) or just absent | Often hardest to render |
| غ | gh | |
| ف | f | |
| ق | q or k | Keep q in well-known terms; else k |
| ك | k | |
| ل | l | |
| م | m | |
| ن | n | |
| ه | h | |
| و | w (consonant), oo (long vowel), o (short) | Context |
| ي | y (consonant), ee (long vowel), i (short) | Context |
| ء | ' (apostrophe) | Glottal stop |

**Hebrew:**

| Hebrew char | Phonetic |
|---|---|
| א | (silent or glottal); use following vowel |
| ב / בּ | v / b |
| ג | g |
| ד | d |
| ה | h |
| ו | v or oo (vowel) |
| ז | z |
| ח | ch (as in Bach) |
| ט | t |
| י | y or ee |
| כ | k or ch |
| ל | l |
| מ | m |
| נ | n |
| ס | s |
| ע | (silent or guttural); use following vowel |
| פ / פּ | f / p |
| צ | tz |
| ק | k |
| ר | r |
| ש | sh or s |
| ת | t |

**Sanskrit (Devanagari):**

| Devanagari | Phonetic |
|---|---|
| अ / आ | a / aa |
| इ / ई | i / ee |
| उ / ऊ | u / oo |
| ए / ऐ | e / ai |
| ओ / औ | o / au |
| क ख ग घ | k kh g gh |
| च छ ज झ | ch chh j jh |
| ट ठ ड ढ ण | t th d dh n (retroflex; render simply) |
| त थ द ध न | t th d dh n |
| प फ ब भ म | p ph b bh m |
| य र ल व | y r l v |
| श ष स ह | sh sh s h |

**Greek (Ancient and Modern):**

| Greek char | Phonetic |
|---|---|
| Α α | a |
| Β β | v (modern) or b (classical) — pick by source period |
| Γ γ | g |
| Δ δ | d (classical) or dh (modern) |
| Ε ε | e |
| Ζ ζ | z |
| Η η | ee (modern) or eh (classical) |
| Θ θ | th |
| Ι ι | ee or i |
| Κ κ | k |
| Λ λ | l |
| Μ μ | m |
| Ν ν | n |
| Ξ ξ | x |
| Ο ο | o |
| Π π | p |
| Ρ ρ | r |
| Σ σ ς | s |
| Τ τ | t |
| Υ υ | y or ee (modern) |
| Φ φ | f |
| Χ χ | ch (as in Bach) |
| Ψ ψ | ps |
| Ω ω | oh |

**Other scripts:**

For Cyrillic, use standard scientific transliteration with phonetic adjustments. For East Asian scripts, prefer the most common Romanization (pinyin without tone marks for Mandarin, Hepburn for Japanese, revised Romanization for Korean). Document the system used in `phonetic-generation-log.md`.

## Meaning generation

For each new term, generate a concise English meaning (1–8 words) that the podcast can use as context. Sources for meaning:

1. **Source-internal context.** If the source defines the term immediately, use that.
2. **Tradition whitelist.** If the detected tradition file `traditions/<name>.yml` includes the term in `signal_terms`, use the whitelist's gloss.
3. **Standard reference** (only if the above fail). Use a concise neutral gloss. Mark in log as "external gloss" so the user can verify.
4. **Stop and ask.** If no reliable meaning can be determined, leave `proposed_meaning: NEEDS_REVIEW` and flag in log.

## Deterministic output

The same source run twice should produce identical phonetic transcriptions for the same terms. Achieve this by:

- Always applying transliteration tables in the same order.
- When multiple valid phonetics exist, pick the first per the table.
- Cache decisions in the lexicon — once a term is in the master lexicon, subsequent runs reuse it.

## phonetic-generation-log.md format

```markdown
# Phonetic Generation Log — [Source Title]

## Per-term generation

### T-003 — قاضي النعمان (proposed: Qadi al-Numan)
Method: Per Arabic transliteration table + Honor existing convention rule
  – ق → q (well-known historical name; widely transcribed as Qadi)
  – ا → aa
  – ض → d
  – ي → ee/i (vowel context: i)
  – ا → a (definite article ال)
  – ل → l
  – ن → n
  – ع → (silent, vowel follows: u)
  – م → m
  – ا → aa
  – ن → n
  → Qadi al-Numan

Meaning generation: Source-internal context (introduced at section 2, line 88 as "Fatimid jurist of the 4th/10th century")
  → proposed_meaning: "Qadi al-Numan, Fatimid jurist (10th century)"

Alternatives considered: "Al-Qaa-dee an-Nu'-maan" (strict phonetic) — rejected for break with widely-known English convention.
```

## Failure modes

- No transliteration table for a detected script → `WORK_DIR/UNSUPPORTED-SCRIPT.md`, pause.
- Term meaning cannot be reliably determined → mark `NEEDS_REVIEW`, continue; final review by user before apply.

## What this stage does NOT do

- Does not write to the master lexicon (Stage 08 + apply does that via staging).
- Does not modify the source text (Stage 12 does substitutions).
- Does not generate the per-source pronunciation guide (Stage 08).
