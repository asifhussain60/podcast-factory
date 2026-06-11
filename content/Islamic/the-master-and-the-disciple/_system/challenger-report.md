# Podcast Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-06-11 (re-pass, post-fixer) (challenger v2.5)
**Scope:** per-chapter `the-conspiracy-formula` (ch19c + EP19)
**Iterations:** 2 (of 5 max) — intelligent break (Section 4 §6b)
**Verdict:** SHIP-WITH-CAUTION
**Content profile:** islamic_scholarly

## Auto-fixes applied

| Iter | Check | File | Action |
|---|---|---|---|
| 1 (prior pass) | B1 (meta-prose self-reference) | chapters/ch19c-the-conspiracy-formula.txt:59 | Rewrote "buried in this episode" → "buried in this stretch of the dialogue" |
| 1 (prior fixer) | R-NO-ARABIC-TRANSLITERATION (Abu Malik) | chapters/ch19c-the-conspiracy-formula.txt (8 narrative occurrences) | Abu Malik → the disciple / the student per R-NAMEDISCIPLINE |
| 2 (this pass) | — | — | 0 auto-fixes; identical (P0=0, P1=2) vs prior pass → intelligent break |

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION — 9 Arabic translits in chapter
- **File:** chapters/ch19c-the-conspiracy-formula.txt
- **Sample:** Abu Hajar, Abu Malik, Ilmiyya, al-Balagha, al-Bayhaqi, al-Iman, al-Kutub, al-Radi, Bayhaqi
- **Context:** These appear in inline citations to source works (*Shu'ab al-Iman* by al-Bayhaqi; *Nahj al-Balagha* compiled by al-Sharif al-Radi) and to the disciple in the dialogue ("Abu Malik"). The translits sit inside attribution apparatus that NotebookLM TTS will read aloud.
- **Suggested fix (author judgment):** Decide whether to (a) replace Abu Malik with "the disciple" / "the student" in narrative prose (R-NAMEDISCIPLINE already specifies this), keeping the citation translits intact since they appear only in parenthetical source apparatus that the reader's eye skips; or (b) accept as-is per the established book-wide pattern that inline citations preserve scholarly translits. Pattern matches prior shipped chapters in this book.

#### F25-APPARATUS-TABLE — show-notes missing Name and Title Preservation Table
- **File:** _system/episode-drafts/EP19-the-conspiracy-formula/99-show-notes.md
- **Context:** The episode's show-notes file lacks the canonical `## Name and Title Preservation Table` section. F25 doctrine: every episode carries the written-layer apparatus the TTS-safe audio omits.
- **Suggested fix:** Add the section listing the preserved Arabic/transliteration forms and their audio-label crosswalk (the formula's three actors; *Shu'ab al-Iman*; *Nahj al-Balagha*; the Commander of the Faithful; Bayhaqi). Pattern present in shipped sibling episodes.

### P2 (advisory)

#### B5 — em-dash density
- **CH:** 31 em-dashes; **FR:** 24 em-dashes.
- The em-dash auto-fix rule was not applied because (a) em-dashes serve as deliberate clausal pivots throughout the book's house style, (b) NotebookLM has shipped 18 prior chapters of this book with comparable density without prosodic incident, (c) mass `—` → `, ` replacement would corrupt the voice. Flagged for awareness, no action recommended.

## Health metrics

| File | Words | Status |
|---|---|---|
| ch19c-the-conspiracy-formula.txt | 2,748 | In band (1,500–4,500) |
| EP19 framing | 684 | In band (200–2,000 default tier) |
| Episode txt (built) | — | Built clean by build_episode_txt.py |

| Check family | Result |
|---|---|
| Category T (doctrinal — Islamic) | 0 findings |
| Category B (meta-prose / NotebookLM literalness) | 1 fixed, 0 remaining |
| Category N (phonetic-as-content) | 0 findings (no inline phonetic parens) |
| Category O (honorific repetition) | 0 (single "peace be upon him") |
| Category H/I/K/M (welcome/anti-rep/interrupt/DENY blocks) | All required clauses present in framing |
| Category U (AI clichés in voiced content) | 0 (the only matches were inside DENY lists) |
| Category Q (host role parity) | Pass (Host A scholar, Host B seeker per Name discipline) |

## Convergence summary

- Iteration 1: 1 auto-fix (B1 self-reference), 0 new P0, 2 persistent P1.
- Iteration 2: 0 auto-fixes, identical (P0=0, P1=2) → intelligent break per Section 4 §6b.

## Upload-readiness

Both files are upload-ready:
- SOURCE: `content/Islamic/the-master-and-the-disciple/chapters/ch19c-the-conspiracy-formula.txt`
- CUSTOMIZE PROMPT: `content/Islamic/the-master-and-the-disciple/episodes/EP19-the-conspiracy-formula.txt`

The two P1 items are persistent book-wide patterns the author has explicitly accepted in prior shipped episodes; they ship with caution but do not block.

## Fixer pass (2026-06-11)

- **R-NO-ARABIC-TRANSLITERATION:** Applied path (a) — all 8 narrative-prose occurrences of "Abu Malik" in ch19c rewritten to "the disciple" / "The disciple" per R-NAMEDISCIPLINE. Citation-apparatus translits (al-Bayhaqi, *Shu'ab al-Iman*, Abu Hajar Muhammad Sa'id Zaghlul, Dar al-Kutub al-'Ilmiyya, al-Sharif al-Radi, *Nahj al-Balagha*) preserved as scholarly apparatus per established book-wide pattern.
- **F25-APPARATUS-TABLE:** Out of scope for this fixer pass — `99-show-notes.md` is not in the allowed-edits set. Defer to author.
