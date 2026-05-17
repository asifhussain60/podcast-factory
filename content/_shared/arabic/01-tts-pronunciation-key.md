# Arabic / Islamic TTS Pronunciation Key

Canonical respelling rules so any text-to-speech AI (NotebookLM, ElevenLabs,
OpenAI TTS) pronounces Arabic and Islamic terms correctly in English-language
audio. This file is the engineering layer; the lookup tables live in
[03-arabic-english-manifest.md](03-arabic-english-manifest.md) and the
letter-level guide in [02-quran-letter-phonetics.md](02-quran-letter-phonetics.md).

---

## 1. Instruction Block (paste into the AI / NotebookLM Customize prompt)

> When narrating, render all Arabic and Islamic terms exactly as spelled in the
> provided text. Do not normalize, anglicize, or shorten them. Doubled vowels
> (`aa`, `ee`, `oo`) are intentional long vowels and must be held. Doubled
> consonants are intentional and must be stressed. Hyphens within a phrase
> indicate one connected unit with no pause. Treat these spellings as fixed
> pronunciation guides, not as words to be auto-corrected. Pronounce every
> honorific in full English ("peace and blessings be upon him", "may Allah be
> pleased with him"), never the bare abbreviation (SAW, RA, AS).

---

## 2. Core Principles

| Principle | Rule | Why |
|-----------|------|-----|
| Long vowels | Always double: `aa`, `ee`, `oo` | English TTS clips single vowels to short / schwa sounds |
| Gemination (shadda) | Double the consonant: `ll`, `rr`, `nn` | Forces the held / stressed consonant |
| Liaison | Join words with hyphens within a phrase | Prevents unnatural mid-phrase pauses |
| Stress | Encode via hyphen syllable breaks, never ALL CAPS | Some engines spell all-caps words letter-by-letter |
| No symbols | Never use `'`, `ʿ`, `ʾ`, `ḥ`, macrons | Diacritics cause dropped syllables or spoken artifacts |
| ASCII only | Plain a–z, hyphen | Maximum cross-engine reliability |
| No Arabic script | Identify letters by Latin name (alif, baa, taa…) | Engines stumble on right-to-left glyphs in English text |
| First-occurrence gloss | First time per chapter: `*Sunnah* (SOON-nah; the Prophet's outward and inward way)` | Builds listener vocabulary inside the episode |

---

## 3. Respelling Recipe (for any new term)

1. **Identify the letters.** Walk the Arabic word letter by letter, naming each
   letter from [02-quran-letter-phonetics.md](02-quran-letter-phonetics.md).
2. **Apply the long-vowel rule.** Every long vowel (alif, waw-as-vowel,
   yaa-as-vowel) gets doubled in the respelling.
3. **Apply gemination.** Every shadda (doubled consonant) gets the consonant
   written twice.
4. **Insert liaison hyphens.** Within multi-word phrases that should read as one
   breath (e.g., `as-salaamu alaykum`), join with hyphens.
5. **Cross-check with the manifest.** If the term already appears in
   [03-arabic-english-manifest.md](03-arabic-english-manifest.md), use the
   existing spelling verbatim. Drift across chapters is a quality-gate failure.
6. **Test on the target engine.** NotebookLM, ElevenLabs, and OpenAI TTS each
   handle `dh`, `kh`, `gh` slightly differently. If a respelling fails on the
   first generation, switch to the documented fallback (e.g., `dh → th`,
   `q → k`) and lock the choice in the book's `_system/pronunciation.md`.

---

## 4. Do NOT Allow (common manglings to prevent)

Each entry is a P0 quality-gate finding — the chapter does not ship until fixed.

| Mangled | Correct | Why it happens |
|---------|---------|----------------|
| `rajim` read as "RAJ-im" or "rage-im" | **rajeem** | Single `i` collapses to schwa |
| `shaytan` read as "SHAY-tn" | **shaytaan** | Final consonant cluster, no long vowel |
| `inshaAllah` read as "INSH-uh-luh" | **in-shaaa Allaah** | No liaison, no long vowels |
| `Ameen` read as "AY-men" / "uh-MEN" | **aa-meen** | Single `A` triggers schwa |
| `Allah` read as "AL-uh" | **Allaah** | Final `h` swallowed without the long `aa` |
| Apostrophe spoken aloud as "apostrophe" | drop the apostrophe, encode the glottal as a hyphen | Some engines literalize `'` |
| Pause inserted mid-phrase in hyphen-joined liaison | use hyphens, not spaces | TTS treats spaces as breath points |
| Honorific abbreviation spoken ("S-A-W", "R-A") | spell the honorific out in English | Audio cannot carry typographic abbreviations |

---

## 5. Engine-Specific Notes

### NotebookLM

- Handles `dh`, `kh`, `gh` inconsistently across runs. Test the isti'aadha and
  basmala once per project. If mangled, switch to the `th` fallback (e.g.,
  `aoothoo` instead of `aoodhu`).
- Avoid all-caps whole words — may be spelled letter-by-letter.
- The Customize prompt is the steering surface. Put the Instruction Block
  (§1 above) and the per-episode pronunciation hooks INSIDE the customize prompt
  body, not in the source file. NotebookLM reads the source literally; the
  customize prompt only steers tone and treatment.

### ElevenLabs

- Reliable on doubled vowels and gemination.
- Treat the SSML `<phoneme>` tag as a last resort — prefer respelling, since
  SSML is not portable across engines.

### OpenAI TTS

- Similar profile to NotebookLM on Arabic letters. The `dh → th` fallback is
  the most common adjustment.

### All engines

- Put the Instruction Block AND the term spellings inside the source text that
  the engine reads. TTS reads the source, not your show notes.
- Lock chosen spellings in the per-book `_system/pronunciation.md` so every
  episode in a series renders identically. Re-test only when changing TTS
  engine or voice.

---

## 6. Honorifics — Always Spell Out in Full English

The hosts must speak the full English form, never the typographic
abbreviation. The first-occurrence-per-chapter gloss is the same as the full
form.

| Typographic | Full spoken form |
|-------------|------------------|
| ﷺ / SAW | **peace and blessings of Allah be upon him** |
| (AS) | **peace be upon him** (or **her**, for a female figure) |
| (RA) — male | **may Allah be pleased with him** |
| (RA) — female | **may Allah be pleased with her** |
| (RA) — plural | **may Allah be pleased with them** |
| SWT | **Glorified and Exalted is He** |

---

## 7. Stress Markers

Use **lowercase respellings with hyphens** for syllable breaks. **Use UPPERCASE
only inside parenthetical first-occurrence glosses** when explicitly marking
primary stress:

- Body text: `*Sunnah* (SOON-nah; the Prophet's outward and inward way)`
- Repeat occurrences in the same chapter: `Sunnah` alone, no respelling
- Customize prompt pronunciation hook: `Sunnah → SOON-nah`

Never put a whole word in caps inside body prose — engines may letter-spell.

---

*This file is the engineering layer. Lookup the term in*
*[03-arabic-english-manifest.md](03-arabic-english-manifest.md)*
*before respelling from scratch.*
