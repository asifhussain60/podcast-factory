# Pipeline fixes from al-anwaar-al-lateefah augmentation transcript audit

> Generated 2026-06-16 from an audit of all 91 augmentation transcripts under
> `content/Islamic/al-anwaar-al-lateefah/augmentation/` (7 lecture sets: ansaar-bhai,
> ibrahim-2011, ibrahim-2015, mabda-maad-gh-2022, mabda-maad-2002, misc, hazrat-zia —
> Gemini direct-audio transcripts of code-switched Urdu/Arabic Ismaili lectures).
> Method: deterministic sweep (734K words) + 3 content-audit passes.

**Verdict:** transcripts are high-quality (0 sentence-level repetition loops, 0 encoding
errors, negligible `[unclear]`). The items below are systemic pipeline gaps to fix/enhance
**before the main source lectures are processed.**

**ACTION: add each P1–P7 below to the pipeline-fix backlog. Do NOT re-implement the
"Already done" items — pull them first.**

---

## Already done (on `develop` and branch `Islamic/al-anwaar-al-lateefah` — pull, don't redo)
- **Audio multi-volume intake** + `.MP3` (uppercase) case-drop fix — `scripts/podcast/intake_book.py` (`_intake_volume_from_audio`, `_discover_mp3s`), `scripts/podcast/_work_manifest.py`.
- **Durable corpus sync** — `scripts/podcast/intelligence/corpus_sync.py` (export/rebuild/verify; additive INSERT-OR-IGNORE; `--safe` shrink-guard) + pre-commit auto-export hook in `infra/git-hooks/pre-commit`. `knowledge.db` stays gitignored; per-type JSONL are the committed source of truth.
- **Arabic restoration (partial)** — `scripts/podcast/restore_arabic.py`: `repair-glossary` (fixes Arabic-in-`phonetic` field misassignment, zero-LLM), `enrich-atoms` (canonical Quran Arabic via `source_library_mirror.quran_ayat_lookup`, zero-LLM), `enrich-quotes` (verified-model Arabic via metered Anthropic SDK — NOT `claude -p`, per DR-015). Corpus = 245 atoms; 49/49 Quran have canonical Arabic; 14 quote/hadith verified; 89 English-translation quotes flagged in `content/knowledge-base/_conflicts/arabic-review.jsonl`.
- **Manual content fix** — garbled `Mumbai` → `Munba'ith` (28×, the First-Emanation term ASR snapped to the city name).

---

## Findings to add to the list

### [P1 — HIGH] Transcription prompt drops recited Arabic into bracket placeholders
`TRANSCRIBE_PROMPT` in `scripts/podcast/transcribe_audio_book.py` lets Gemini emit
stage-directions (`[Recitation of Al-Fatihah]`, `[Du'a in Arabic]`, `[Prayer]`) and DROP
the recited Arabic. Audit found 36 such drops (27 du'a/prayer, 9 Quran-recitation) across
40 files. **Fix:** strengthen the prompt to never bracket-and-drop recited Arabic — require
transliteration (and identify canonical text), reserve `[unclear]` only for truly inaudible
audio. *Fix at the point of capture before the source run.*

### [P2 — HIGH] No canonical transliteration / garbled-term normalization pass
Per-file Gemini passes share no glossary → pervasive drift (`da'wat`/`da'wah`,
`'aql-e-awwal` variants, `Qa'im`/`Qaim`, `Namiyah`/`Namiyya`, `-e-`/`-i-` ezafe, curly vs
straight apostrophes, capitalization) AND hard garbled terms where ASR snaps an unfamiliar
Arabic word to a known one (e.g. `Mumbai`=`Munba'ith`). **Fix:** a canonical-term
glossary/style-sheet + deterministic normalization post-pass (known-garbled map +
canonical-form map) after transcription, before chapter authoring. This is also what makes
the reader glossary/Arabic-toggle matching reliable.

### [P3 — HIGH] No downstream Arabic-script restoration for audio books (the original P0)
Audio transcription is transliteration-only, so the reader's "Show Arabic" toggle has
nothing to show. The toggle reads `_system/glossary.yml` `arabic_script` + (to be added)
inline passage markers. `fill_glossary_arabic.py` only fills from OCR, which audio books
lack. **Fix (remaining restore_arabic steps):** (a) restore canonical Arabic for dropped
recitations/verses (Al-Fatihah = Quran 1:1–7 etc.) via `quran_ayat_lookup` — free; flag
non-canonical du'as; (b) emit inline `⟪ar|translit|script⟫` passage markers + teach the
reader (`plan-dashboard/src/lib/reader/glossary.ts` + `chapter-viewer.css`) to render
multi-word Arabic under the toggle; (c) `_book_compose.py` audio branch (consume restored
Arabic instead of requiring OCR ground truth); (d) extend the book-challenger Arabic-SCRIPT
gate; (e) auto-run for `source_kind=audio` Islamic books + a deterministic ship-gate in
`validate_ship_ready.py` that blocks publish below an Arabic-coverage threshold.

### [P4 — MEDIUM] Decoding-loop / paragraph-duplication not detected
A Gemini decoding loop produced an 838-char verbatim block repeated in
`hazrat-zia/lec02.txt` (offsets ~49860 and ~51519, with distinct content B between the
copies; boundaries split mid-token, so a blind cut loses content). The existing
`_dup_ratio` sentence-level check missed it. **Fix:** add block/paragraph-level
verbatim-duplication detection to `transcribe_audio_book.py` + the chunking retry;
reconstruct the intended single pass; distinguish legitimate rhetorical refrains.

### [P5 — MEDIUM] Empty/short transcript accepted silently
`transcribe_audio_book.py` wrote a 0-word transcript with no error/flag when Gemini
returned empty (`ibrahim-2015/lec17`, real 2.5MB audio → 0 words on two attempts =
source-audio problem). **Fix:** detect empty/suspiciously-short transcripts (words vs
`source_bytes` ratio), flag loudly, optionally retry with chunking, surface in the
ship-gate. (Also: check the original `17 Maghrib Sabaq` audio file — likely silent/corrupt.)

### [P6 — MEDIUM] `build_glossary.py` field misassignment
Some audio-era glossaries store Arabic in `phonetic`, the Roman match-token in
`transliteration`, and leave `arabic_script` empty — so the reader (which matches
`phonetic` against Roman prose) never matches and the overlay is empty. `restore_arabic.py
repair-glossary` fixes existing files; **root-fix `build_glossary.py`** so new books get the
correct shape (phonetic = Roman token, arabic_script = Arabic).

### [P7 — LOW] Native-script leakage + paragraph-structure inconsistency
~30+ native-script tokens left mid-English (Devanagari `अरे`/`साहब`; Arabic
`البعث`/`جاری`/`اشاره`) across ~24 files; 6 files are a single unbroken line (no paragraph
breaks) hurting downstream chunking. **Fix:** prompt rule forbidding native-script output +
a post-pass to romanize leaked tokens and normalize paragraph structure.

---

**Priority:** P1–P3 are blocking for the source run; P4–P6 strongly recommended; P7 cosmetic.
Confirm once added to the list. Do not start implementing until the list is agreed.
