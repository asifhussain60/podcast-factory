# Podcast Challenger Report — challenger v2.0

**Verdict:** BLOCKED
**Book:** kitab-al-riyad
**Episode:** EP15-tawhid-and-the-critique-of-al-mahsul
**Chapter:** ch15-tawhid-and-the-critique-of-al-mahsul
**Run:** 2026-05-21T20:45:00Z
**Scope:** per-chapter:tawhid-and-the-critique-of-al-mahsul
**Iterations:** 2 (of 5 max; intelligent-break: iter-2 produced identical findings counts with no new auto-fixes)
**Auto-fixes applied:** 26 (B5 prose em-dashes converted to commas)
**P0:** 1 | **P1:** 2 | **P2:** 1
**Score:** 0.00 (Unstable)

---

## Auto-fixes applied

**26 B5 prose em-dashes converted to commas** in `ch15-tawhid-and-the-critique-of-al-mahsul.txt`. Em-dashes in blockquote attribution lines (`— Imam Ali ibn Abi Talib, Nahj al-Balagha`) are structural and were not touched. Em-dashes in section headings were not touched. Only mid-sentence prose dashes were converted.

| # | Rule | Location | Old | New |
|---|---|---|---|---|
| 1 | B5 | ch15 prose | `head of human history — Adam` | `head of human history, and Adam` |
| 2 | B5 | ch15 prose | `most difficult kind — polemic at the rank` | `most difficult kind, polemic at the rank` |
| 3 | B5 | ch15 prose | `The chapter, and with it the whole book — closes on` | `The chapter, and with it the whole book, closes on` |
| 4 | B5 | ch15 prose | `in a *person* — *the Imam* — singled out` | `in a *person*, *the Imam*, singled out` |
| 5 | B5 | ch15 prose | `*Huwa* — the third-person singular pronoun — bears` | `*Huwa*, the third-person singular pronoun, bears` |
| 6–26 | B5 | ch15 prose | (21 additional mid-sentence prose em-dashes converted) | (commas or restructured clauses) |

Em-dash count: 107 → 81 after auto-fixes.

---

## Findings requiring author resolution

### P0 (blocks ship)

#### A1: Nahj al-Balagha citation missing sermon number

- **Signature:** `A1:citation-nahj-no-sermon-number:al-Khutba-al-Ashbah:ch15:line225`
- **File:** `content/podcast/library/books/kitab-al-riyad/chapters/ch15-tawhid-and-the-critique-of-al-mahsul.txt`, line 225
- **Context:** The blockquote attribution reads: `— Imam Ali ibn Abi Talib, *Nahj al-Balagha*, the sermon known as *al-Khutba al-Ashbah* on the impossibility of describing the Lord without falling into limit`. The sermon is identified by name but no sermon number is given. Standard Nahj al-Balagha citation practice (and the book's own pattern in prior chapters) requires both the sermon name and the sermon number so listeners/readers can locate the passage.
- **Note:** *Al-Khutba al-Ashbah* is conventionally numbered Sermon 91 in the Shahudi/Subhi Salih editions, Sermon 186 in some older numbering schemes. The Sermon 91 numbering is standard for English scholarly citations.
- **Suggested fix (one-line edit):** Change the attribution to: `— Imam Ali ibn Abi Talib, *Nahj al-Balagha*, Sermon 91 (*al-Khutba al-Ashbah*), on the impossibility of describing the Lord without falling into limit` — or the author's preferred citation style so long as it includes the sermon number.

---

### P1 (ship-with-caution)

#### F5: Discussion spine (04-discussion-spine.md) all unfilled

- **Signature:** `F5:discussion-spine-all-llm-fill:EP15`
- **File:** `content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP15-tawhid-and-the-critique-of-al-mahsul/04-discussion-spine.md`
- **Context:** All 8 beats contain `[LLM-FILL]` placeholders. Does not affect `episodes/EP15-*.txt` (the episode txt is built from `00-framing.md`'s well-developed Three-part focus). Incomplete sidecar documentation only; P1 because the spine is the steering layer for NotebookLM hosts and its absence leaves them without beat-level guidance.
- **Suggested fix:** Fill beats using the 6 key_tensions and 15 anchor_passages from the chapter contract. Beat seams follow the Three-part focus: Focus 1 (sub-chapters 1–8), Focus 2 (sub-chapters 9–14), Focus 3 (sub-chapters 15–16 + closing settlement). This is the book's closing chapter; filling the spine would complete the series documentation.

#### J2: Full name after first mention at line 237 blockquote

- **Signature:** `J2:full-name-after-first-mention:Imam-Hussain-ibn-Ali:ch15:line237`
- **File:** `content/podcast/library/books/kitab-al-riyad/chapters/ch15-tawhid-and-the-critique-of-al-mahsul.txt`, line 237
- **Context:** First prose mention is at line 235: `Imam Hussain ibn Ali on the Day of Arafa` — full name, correct. The blockquote attribution at line 237 reads: `— (Du'a Arafa of Imam Hussain ibn Ali, the supplication on the Day of Arafa, the closing apophatic section)`. This is a second occurrence of the full form; per R-NAMES/J2, subsequent citations should use the alias `Imam Hussain`.
- **Note:** The verbatim-quote exception applies to the quote body itself, but the parenthetical attribution gloss `(Du'a Arafa of Imam Hussain ibn Ali...)` is author prose, not a verbatim citation. The exception does not apply here.
- **Suggested fix:** Change line 237 attribution to: `— (*Du'a Arafa* of Imam Hussain, the supplication on the Day of Arafa, the closing apophatic section)`

---

### P2 (advisory)

#### B5: 81 residual em-dashes in headings, blockquote attributions, and citations

- **Signature:** `B5:em-dashes-residual-structural:ch15:81-lines`
- **File:** `content/podcast/library/books/kitab-al-riyad/chapters/ch15-tawhid-and-the-critique-of-al-mahsul.txt`
- **Context:** After 26 B5 auto-fixes, 81 lines still contain em-dashes. These are: (a) blockquote attribution dashes (`— Imam Ali ibn Abi Talib, *Nahj al-Balagha*`) — structural per chapter convention; (b) section heading dashes (`## Sub-chapter one — ...`) — structural separators; (c) inline citation context glosses (`the sermon known as *al-Khutba al-Ashbah* — on the impossibility...`) — author voice in attribution lines. None of these are auto-fixable without distorting the chapter's architectural formatting.
- **Suggested fix:** Advisory only. Author may choose to replace heading dashes with colons (`## Sub-chapter one: ...`) for cleaner audio delivery, but this is a style preference.

---

## Health metrics

| Chapter | Words | Chapter tier | Quranic verses | Honorific occurrences | Em-dash lines | Framing words | Verdict |
|---|---|---|---|---|---|---|---|
| ch15-tawhid-and-the-critique-of-al-mahsul | 9,847 | Extended (above 9,500 soft ceiling; within 10,500 hard cap) | 5 (Q3:18, Q42:11, Q6:103, Q57:3, Q112:1–4) | 4 (Adam, Prophet, Imams plural, the Imam) | 81 (post-auto-fix; attribution-structural) | 3,475 | BLOCKED |

**Quranic verse attribution:** Q 3:18 line 55: `(Quran 3:18, author's rendering)` — PASS (resolved in this session). Q 112:1–4: `(Quran 112:1–4, Sahih International)` — PASS. Q 57:3 line 221, Q 6:103 line 223: cited by verse number without named translator — P2 advisory (consistent with chapter's rendering-dense style; not a P0 now that Q3:18 is resolved). Q 42:11 line 106: cited by verse number only — same advisory.

**Hadith attribution:** Sahih al-Bukhari, Book 59, Hadith 3191, narrated by Imran ibn Husayn — fully cited. PASS.

**Non-Quranic citation attribution:**
- *Rahat al-'Aql* (al-Kirmani): full title, no abbreviation. PASS.
- *Ta'wil al-Shara'i'* (Imam al-Mu'izz): full title. PASS.
- *Nahj al-Balagha* (Imam Ali), Sermon al-Khutba al-Ashbah: sermon name given; sermon NUMBER missing (P0 — see above).
- *Du'a Arafa* (Imam Hussain ibn Ali): attributed with context; J2 alias violation at line 237 (P1 — see above).

**Checks that passed cleanly:**
- A3 (translation provenance): Q 3:18 now `(Quran 3:18, author's rendering)` — PASS
- A2 (no [VERIFY CITATION] markers) PASS
- A4 (no source-shifting; quotes framed faithfully) PASS
- A5 (no cross-tradition collapse — Sunni Bukhari hadith used as converging witness, not collapsed with Ismaili tradition) PASS
- N1 (no inline phonetic parens in chapter — all parens are lowercase scholarly bridges with no UPPERCASE respelling segments) PASS
- O1/O2 (no abbreviated work titles in chapter prose) PASS
- O3 (R-HONORIFIC-ONCE: Imam, Prophet, Adam, the Imam — each at first mention only) PASS
- H1/H2/H3 (welcome/closing directives in framing) PASS
- I1/I2 (anti-repetition clauses in framing) PASS
- K1 (no-interrupt directive in framing) PASS
- M1/M2 (DENY blocks: modernize, surprise-noise) PASS
- R1–R5 (choreography: surprise-move clause, reset clause, cadence clause, formal-transition DENY, no-modernize permission) PASS
- J1 (name alias policy declared in framing) PASS
- N2/N4 (pronunciation in imperative form, framing Pronunciation block well-formed) PASS
- F1/F2/F3/F4 (framing structure: Three-part focus, Host dynamic, Tone, Do-not block) PASS
- Contract alignment: angle/format/host_dynamic/length_target/key_tensions/anchor_passages/tone_constraints all match framing PASS
- S1 (orchestrator lock): `phase_status: running` with ts_updated 40+ minutes old — stale lock, not active process. PASS
- Word count: 9,847 within [500, 10,500] hard band; above 9,500 soft ceiling (P2 advisory only) PASS-SOFT
- Framing word count: 3,475 within [150, 3,700] PASS

**Carry-forward P1 items (from 18:30Z and 20:00Z runs — not new findings; not re-emitted):**
- C1: Abu Hatim al-Razi phonetic drift (ar- vs al-) — requires author decision on alias policy or book pronunciation.md override
- C2 (×3): zahir/batin, al-Sadayn, book-lexicon-empty — requires populating `_system/pronunciation.md`
These are systemic gaps in the book-level phonetic ledger. They affect all episodes, not uniquely EP15. Not re-emitted as new findings in this run (already in ledger). Deferred to author as a bulk curation task on `_system/pronunciation.md`.

**Checks skipped (no transcript):** Loop M empirical-transcript scan. No transcript file found at `content/podcast/library/books/kitab-al-riyad/transcripts/EP15-tawhid-and-the-critique-of-al-mahsul.transcript.txt`.

---

## Score

**P0:** 1 | **P1:** 2 | **P2:** 1 | **Chapters in scope:** 1 | **Auto-fixes:** 26

```
penalty = (1 × 1.0 + 2 × 0.2 + 1 × 0.05) / 1 = 1.45
score   = max(0.0, 1.0 − 1.45) = 0.00 (Unstable)
```

One P0 finding (A1: Nahj al-Balagha Sermon 91 citation missing sermon number, line 225) blocks ship. The fix is a one-word edit: insert `Sermon 91` into the attribution. Once resolved, the verdict should shift to SHIP-WITH-CAUTION (2 P1 gaps remain: F5 spine unfilled, J2 line 237 alias). Addressing both P1 items (fill spine beats, correct line 237 alias to "Imam Hussain") would shift the verdict to SHIP-READY.

**Upload path (blocked until P0 resolved):**
1. Source: `content/podcast/library/books/kitab-al-riyad/chapters/ch15-tawhid-and-the-critique-of-al-mahsul.txt`
2. Customize prompt: `content/podcast/library/books/kitab-al-riyad/episodes/EP15-tawhid-and-the-critique-of-al-mahsul.txt`
3. NotebookLM format: Deep Dive / Extended length

---

## Resolution notes

**To unblock (P0 fix — one edit, line 225 of ch15):**

Current:
```
— Imam Ali ibn Abi Talib, *Nahj al-Balagha*, the sermon known as *al-Khutba al-Ashbah* on the impossibility of describing the Lord without falling into limit
```

Required (add sermon number; use whichever edition number the author works from):
```
— Imam Ali ibn Abi Talib, *Nahj al-Balagha*, Sermon 91 (*al-Khutba al-Ashbah*), on the impossibility of describing the Lord without falling into limit
```

After this one edit, re-run `scripts/podcast/build_episode_txt.py` for EP15, then re-invoke `podcast-challenger --chapter tawhid-and-the-critique-of-al-mahsul`.

**P1 resolution path:**

1. J2 (line 237, one edit): Change `Imam Hussain ibn Ali` to `Imam Hussain` in the Du'a Arafa attribution gloss.
2. F5 (spine authoring): Fill the 8 beats in `04-discussion-spine.md` using the chapter contract's key_tensions and anchor_passages. Not required for episode.txt to function — framing's Three-part focus drives NotebookLM. Required to complete series documentation.

**Note on carry-forward C1/C2 P1 items:** These are book-level phonetic ledger gaps predating EP15. They are not new this run and are not re-emitted. They do not affect the episode.txt or the chapter SOURCE content directly. A separate author curation pass on `_system/pronunciation.md` is recommended before the full KaR series ships.

---

## Fixer-pass note (2026-05-21)

- **J2 (line 237):** RESOLVED. Attribution rewritten to `— (*Du'a Arafa* of Imam Hussain, the supplication on the Day of Arafa, the closing apophatic section)`.
- **F5 (04-discussion-spine.md):** DEFERRED. Out of scope for this fixer pass — allowed edits are limited to `chapters/ch*.txt` and `00-framing.md`; the spine sidecar is not in the allowed set. Episode `.txt` is unaffected (built from framing's Three-part focus). Requires a separate authoring pass to complete series documentation.

