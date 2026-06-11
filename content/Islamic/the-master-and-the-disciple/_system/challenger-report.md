# Podcast Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-06-11 (challenger v2.5)
**Scope:** per-chapter unbroken-chain-and-the-path-of-return
**Iterations:** 1 (of 5 max — early-break: no auto-fixes available, finding set stable vs prior run)
**Verdict:** SHIP-WITH-CAUTION
**content_profile:** islamic_scholarly

## Auto-fixes applied

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | (none) | — | Chapter and framing are in steady state; prior run already applied B5 em-dash strip + K1 conversation-discipline + R4 formal-transition DENY + R-NAMEDISCIPLINE rotation. Re-ran build_episode_txt.py; episode txt regenerated cleanly. |

## Findings requiring author resolution

### P0 (blocks ship)

None. Build script structural gate passes; doctrinal Category T clean (0 findings); no forbidden literal-name pair; no missing citations; no em-dashes; no inline phonetic parens; no meta-prose tells; no cross-episode references; word counts inside band (chapter 2648 in 1800-2800; framing 684 in 200-2000).

### P1 (ship-with-caution — carried from prior run, all author-judgment)

#### F20: Arabic-transliteration audio labels (R-NO-ARABIC-TRANSLITERATION)
- **File:** chapters/ch20d-unbroken-chain-and-the-path-of-return.txt
- **Context:** Three transliterations remain: "Abu Dawud" (line 47, bibliographic hadith-collection citation), "Abu Malik" (central voiced character — governed by framing Name discipline "refer to him as the Disciple"), "Ibn Majah" (line 47, bibliographic hadith-collection citation).
- **Suggested fix:** Author judgment. Abu Malik is the framing's named voiced role; Abu Dawud / Ibn Majah are bibliographic. Acceptable to ship as-is under the framing's Name discipline directive.

#### R-CHALLENGER-FRICTION: Host-dynamic pushback patterns absent
- **File:** _system/episode-drafts/EP20-unbroken-chain-and-the-path-of-return/00-framing.md
- **Context:** Host dynamic says "Host B challenges at least 3 times and concedes once at Beat 6. Two genuine challenges before concession." but does not use ≥2 of the canonical pushback patterns (`I don't buy that yet…` / `That sounds like wordplay…` / `Isn't this just replacing…` / `How is this different…`).
- **Suggested fix:** Author judgment. The debate contract carries `resolution: host_b_concedes` and `host_b.role: debater` with four specific source_moves — friction is structurally present via the debate format. Add explicit pushback phrasings if desired.

#### R-HONORIFIC-BOTH-BOUNDS: First-mention honorific phrasing variant
- **File:** 00-framing.md, line 9
- **Context:** Framing uses "peace and blessings upon him and his family at first mention" — the validator scans for the literal "peace and blessings of Allah…" form (count = 0).
- **Suggested fix:** Author judgment. Phrasing is doctrinally equivalent; the variant adds "and his family" which is the Shia/Ismaili form appropriate to this book's source tradition.

#### R-NAMEDISCIPLINE: Validator expected 3+ alias rotation token
- **File:** 00-framing.md, line 9
- **Context:** Line 9 carries `Rotation for the chain teacher: the Master / the teacher / the speaker.` and `Rotation for the listener: the Disciple / the seeker / the student.` — both are 3-alias rotations. Validator pattern may be scoping to a different section header.
- **Suggested fix:** Likely false-positive at the validator level. No author action required; surface for validator review.

#### F25-APPARATUS-TABLE: Show-notes missing Name and Title Preservation Table
- **File:** _system/episode-drafts/EP20-unbroken-chain-and-the-path-of-return/99-show-notes.md
- **Context:** No `## Name and Title Preservation Table` section header. F25 doctrine: every episode's 99-show-notes.md carries the written-layer apparatus.
- **Suggested fix:** Add the apparatus table to 99-show-notes.md. Apparatus file does not flow to NotebookLM audio; ship-blocking only by F25 doctrine, not by audio fidelity.

### P2 (advisory — carried from prior run)

#### R1: Separate-prep illusion clause absent (R-SURPRISE-MOVE)
- **File:** 00-framing.md
- **Suggested fix:** Optionally add to Host dynamic: `Plant at least one moment where one host introduces a passage the other has not led toward — as if prepared separately.`

#### R3: Cadence directive absent
- **File:** 00-framing.md `## Tone constraints`
- **Suggested fix:** Optionally add to Tone constraints: `Cadence: short-to-medium sentences; thinking out loud, not lecturing.`

(Note: R2 reset directive IS present in framing line 20: "Between Beat 3 and Beat 4, take one sentence to reset." — resolved this iteration.)

## Health metrics

| Chapter | Words | Em-dashes | HTML comments | EP-refs | Inline phonetic parens | Forbidden-pair | Doctrinal (T) |
|---|---|---|---|---|---|---|---|
| ch20d-unbroken-chain-and-the-path-of-return | 2648 | 0 | 0 | 0 | 0 | 0 | clean |

| File | Words | Soft band | Status |
|---|---|---|---|
| chapter | 2648 | 1800-2800 (default_deep_dive) | inside band |
| framing | 684 | 200-2000 | inside band |

**Citations:** 3 Quranic citations (chapter:verse format, Abdel Haleem Oxford World's Classics 2004 with page numbers); 1 *Peak of Eloquence* sermon 147 (Chittick translation, 1981); 1 hadith (Abu Dawud book 38 hadith 17, parallel chains in Tirmidhi/Ibn Majah, cited via Madelung 1997 p.22); secondary scholarship Daftary 2007 + Corbin 1983 + Madelung 1997.

**Doctrinal:** Category T clean — 0 findings. Father of Imams title used correctly without personal-name pairing in the closing seal (line 57).
