# Quranic / Classical Arabic Letter Phonetic Guide

Letter-level phonetic reference for every Arabic consonant and long vowel. The
podcast skill consults this on every chapter that contains Arabic — the manifest
in [03-arabic-english-manifest.md](03-arabic-english-manifest.md) gives the
canonical respelling for whole words; this file is what you fall back to when
respelling a word that has no manifest entry yet.

**No Arabic script.** Letters are named by their canonical Latin name. The
"sound" column describes the classical Arabic articulation (the
*makhraj* — point of articulation in the mouth, throat, or chest); the "ASCII
respell" column gives what to write so a TTS engine reproduces it.

---

## 1. The 28 Letters

| # | Letter name | Sound (classical) | ASCII respell | Notes / engine reliability |
|---|-------------|-------------------|---------------|----------------------------|
| 1 | alif | Long open `a` as in *father* | `aa` | Always double when long. The bare carrier (hamzat al-wasl) is silent and dropped. |
| 2 | baa | Plain `b` as in *boy* | `b` | Reliable everywhere. |
| 3 | taa | Plain `t` as in *tea* | `t` | Reliable. The feminine `taa marbuta` at word-end becomes `t` only when continued in iDaafah, otherwise drops to `h` / silent. |
| 4 | thaa | Voiceless `th` as in *think* | `th` | Reliable. Engines that confuse with `dh` rarely; if so, use `th-` with a hyphen. |
| 5 | jeem | English `j` as in *jam* | `j` | Reliable. (Egyptian colloquial reads as hard `g` — do not use here.) |
| 6 | Haa (heavy) | Breathy pharyngeal H — no English equivalent; tighten the throat | `h` | Approximated. Engines cannot produce the pharyngeal — `h` is the agreed compromise. |
| 7 | khaa | Velar fricative as in Scottish *loch* or German *Bach* | `kh` | Approximated as hard `k`. Acceptable. Fallback: `k`. |
| 8 | daal | Plain `d` as in *day* | `d` | Reliable. |
| 9 | dhaal | Voiced `th` as in *this* | `th` (preferred) or `dh` | Engines mangle `dh` more often than `th`. Default to `th` unless context demands the distinction from thaa. |
| 10 | raa | Tapped / lightly trilled `r` (Spanish-like) | `r` | Reliable. Doubled (`rr`) when shadda is present. |
| 11 | zay | Plain `z` as in *zoo* | `z` | Reliable. |
| 12 | seen | Plain `s` as in *see* | `s` | Reliable. |
| 13 | sheen | Plain `sh` as in *shoe* | `sh` | Reliable. |
| 14 | Saad (emphatic) | Emphatic `s` — back of tongue raised, darker timbre | `s` | The emphatic colour is lost in English TTS. Acceptable tradeoff. |
| 15 | Daad (emphatic) | Emphatic `d` — Arabic's unique "Daad of the Arabs" | `d` | Emphasis lost; `d` is the agreed compromise. |
| 16 | Taa (emphatic) | Emphatic `t` — back of tongue raised | `t` | Emphasis lost. |
| 17 | Zaa (emphatic) | Emphatic `dh` / `z` — back of tongue raised, voiced | `z` | Emphasis lost. Some traditions transliterate `zh`; do not — engines mangle. |
| 18 | ayn | Voiced pharyngeal — vibrate the throat with the vowel | drop the letter; let the adjacent vowel carry, with a hyphen marking the break | NEVER write `'` or `ʿ` — engines speak the apostrophe or drop the syllable. Pattern: `'Abd → ab-d`, `Ali → a-lee`, `Ta'aala → ta-aa-laa`. |
| 19 | ghayn | Voiced velar fricative — French `r` / Parisian *Paris* | `gh` | Approximated as hard `g`. Acceptable. Fallback: `g`. |
| 20 | faa | Plain `f` as in *fun* | `f` | Reliable. |
| 21 | qaaf | Deep uvular `k` — back of the tongue against the uvula | `q` (preferred) or `k` | Engines pronounce `q` as English `q` (kw) inconsistently. Fallback `k`. |
| 22 | kaaf | Plain `k` as in *key* | `k` | Reliable. |
| 23 | laam | Plain `l` as in *light* | `l` | Reliable. In *Allaah* the `ll` is geminated and darkened — the doubled `ll` plus `aa` gives the right weight. |
| 24 | meem | Plain `m` as in *moon* | `m` | Reliable. |
| 25 | noon | Plain `n` as in *net* | `n` | Reliable. |
| 26 | haa (light) | Plain `h` as in *hat* | `h` | Reliable. Distinct from heavy Haa (#6) in classical Arabic; in respelling both become `h`. |
| 27 | waw | Consonant `w` as in *we`; long vowel `oo` as in *moon* | `w` (consonant) or `oo` (long vowel) | Reliable. Context decides: `wa` (and) is consonant; `noor` (light) is long vowel. |
| 28 | yaa | Consonant `y` as in *yes*; long vowel `ee` as in *see* | `y` (consonant) or `ee` (long vowel) | Reliable. Context decides: `yawm` (day) is consonant; `deen` (religion) is long vowel. |

### Special markers (not numbered letters but essential)

| Marker | Sound | ASCII respell | Notes |
|--------|-------|---------------|-------|
| hamza | Glottal stop as in the catch in *uh-oh* | omit; let the syllable break carry it (often via hyphen) | NEVER write `'`, `ʾ`, `ʿ`. Example: `Qur'aan → qur-aan`, `du'aa → du-aa`. |
| shadda | Doubling of the preceding consonant (gemination) | double the consonant: `bb`, `dd`, `ll`, `mm`, `nn`, `rr`, `ss`, `tt`, `zz` | Critical for *Allaah*, *muhammad*, *salam*. |
| sukun | No vowel on the consonant (cluster) | natural in English respell; just write the consonants adjacent | Example: *bism* (in the name of) → `bism`. |
| fatha (short `a`) | Short `a` as in *cat* / *hat* | `a` | Reliable. |
| kasra (short `i`) | Short `i` as in *bit* | `i` | Reliable. |
| damma (short `u`) | Short `u` as in *put* | `u` | Reliable. |
| tanween (–an / –in / –un) | Final nunation on indefinite nouns | `-an` / `-in` / `-un` | Often dropped in pausal reading; only write it when reading a verse fully vocalized. |

---

## 2. Short Vowel vs Long Vowel — the most common mistake

| Spelled as | Actual sound | Correct respell |
|------------|--------------|-----------------|
| Single `a` (e.g. `salam`) | Engines collapse to schwa → "SAL-um" | **sa-laam** (double the long alif) |
| Single `i` (e.g. `rajim`) | Engines collapse to short i → "RAJ-im" | **ra-jeem** (double the long yaa-as-vowel) |
| Single `u` (e.g. `nur`) | Engines collapse to short u → "NUR" | **noor** (double the long waw-as-vowel) |

**Rule of thumb**: if the syllable carries primary stress AND the Arabic original
has a long vowel (alif, long waw, or long yaa), double the vowel in the respell.

---

## 3. Sun and Moon Letters (al- assimilation)

When the definite article `al-` precedes a "sun letter," the `l` assimilates to
the following consonant and the consonant doubles. When it precedes a "moon
letter," the `l` is pronounced normally.

**Sun letters** (14): taa, thaa, daal, dhaal, raa, zay, seen, sheen, Saad, Daad,
Taa, Zaa, laam, noon.
- `al-shams` (the sun) → **ash-shams** — the `l` becomes `sh`.
- `al-raheem` (the merciful) → **ar-raheem**.
- `al-noor` (the light) → **an-noor**.

**Moon letters** (14): alif, baa, jeem, Haa, khaa, ayn, ghayn, faa, qaaf, kaaf,
meem, haa, waw, yaa.
- `al-qamar` (the moon) → **al-qamar** — the `l` is pronounced.
- `al-Hamdu` (the praise) → **al-Hamdu** (note: this is the *al-hamdulillaah*
  opening; `h` here is moon).
- `al-jannah` (the garden / paradise) → **al-jannah**.

In TTS respellings, **write the assimilation explicitly**: `ar-raheem`, not
`al-raheem`. Engines will not assimilate on their own.

---

## 4. Quick respelling worked-examples

Walk-through using the rules above.

### *Bismillaah ir-Rahmaan ir-Raheem* (In the name of Allah, the Most Compassionate, the Most Merciful)

1. `bi` (short i) + `sm` (cluster) + `il-laah` (assimilation of definite article
   into Allaah; the geminated `ll` is the shadda; long alif → `aa`).
2. `ir-rah-maan` — sun letter `r`, assimilation → `ir-` not `al-`; long alif at
   end → `aan`.
3. `ir-ra-heem` — same sun-letter assimilation; long yaa-as-vowel → `eem`.

**Final respell**: `bis-mil-laah ir-rah-maan ir-ra-heem`

### *A'oodhu billaahi minash-shaytaanir-rajeem* (I seek refuge in Allah from the rejected Satan)

1. `a` (short a, the hamza opens it) + `oo` (long waw) + `thoo` (using `th` for
   dhaal, more reliable than `dh`) → **`aoothoo`** or **`a-oo-thoo`** with hyphens.
2. `bil-laahi` (sun-letter assimilation `bi + al + laahi`; geminated `ll`).
3. `mi-nash-shay-taa-nir-ra-jeem` — multiple assimilations and the long alif in
   *shaytaan*.

**Final respell**: `a-oo-thoo bil-laah-i mi-nash-shay-taa-nir-ra-jeem`

---

## 5. When in doubt

1. Check [03-arabic-english-manifest.md](03-arabic-english-manifest.md) — the
   term may already be canonical.
2. If not, draft using this guide.
3. Test on the actual TTS engine the episode uses.
4. Lock the chosen spelling in the book's `_system/pronunciation.md` AND propose
   the addition to the manifest.

The substitution policy in [04-common-term-substitutions.md](04-common-term-substitutions.md)
may also resolve the question by replacing the Arabic with a clean English form.

---

*Letter names follow the conventional Latin transliteration used in classical
Arabic instruction. The "ASCII respell" column reflects what works empirically
across NotebookLM, ElevenLabs, and OpenAI TTS as of 2026-05-17.*
