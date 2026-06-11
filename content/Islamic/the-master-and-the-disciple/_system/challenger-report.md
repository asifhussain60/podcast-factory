# Podcast Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-06-11 (challenger v2.5)
**Scope:** per-chapter syllogism-of-divine-justice
**Iterations:** 2 (of 5 max)
**Verdict:** SHIP-WITH-CAUTION
**Content profile:** islamic_scholarly

## Auto-fixes applied

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | B5 | ch18b-syllogism-of-divine-justice.txt | Replaced 32 em-dashes with commas |
| 1 | B1 | ch18b-syllogism-of-divine-justice.txt:45 | "in this chapter" → "here" (file-length self-reference) |
| 1 | K1 | 00-framing.md Host dynamic | Inserted Conversation discipline clause (no interjections, completes-a-thought, qualified concessions only) |
| 1 | I1 | 00-framing.md Host dynamic | Inserted Anti-repetition clause (no restating spine beyond R-RECURRING-THESIS, no re-citing same verse) |
| 1 | H3 | 00-framing.md Host dynamic | Inserted Landing clause (close on unresolved question, not recap) |
| 1 | M1 | 00-framing.md `## Do not` | Extended modernize DENY (cognitive behavioral therapy, deep dive, content creator, YouTube/TikTok, "21st century", "modern world", quote-tweet) + DO-permission for practical analogies |
| 1 | M2 | 00-framing.md `## Do not` | Extended surprise-noise DENY ("so interesting", "chilling", "devastating", "no way") |
| 1 | R4 | 00-framing.md `## Do not` | Added formal-transition DENY (Firstly, Secondly, Furthermore, In conclusion, To summarize, Lastly) + thinking-out-loud cadence |
| 2 | E1 | 00-framing.md (multiple sections) | Compressed Opening / Three-part focus / Pronunciation / Tone to land framing under 4500-char NotebookLM ceiling (final 4499 chars, 730 words) |

After iteration 2, `build_episode_txt.py` passes cleanly and emits `episodes/EP18-syllogism-of-divine-justice.txt` (730 words, customize-prompt-ready).

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION — "Abu Malik" in chapter prose
- **File:** chapters/ch18b-syllogism-of-divine-justice.txt
- **Context:** "Abu Malik" appears throughout as the disciple's name. F20 doctrine asks for an English audio label.
- **Suggested fix:** The framing already maps the disciple → "the disciple" by label. Author may either (a) replace "Abu Malik" with "the disciple" throughout chapter prose, or (b) accept the single Arabic name as a tracked exception (this is the canonical character name from the source dialogue and the book registers it as such).

#### R-NAMEDISCIPLINE — Name discipline rotation not declared
- **File:** _system/episode-drafts/EP18-syllogism-of-divine-justice/00-framing.md
- **Context:** Name discipline section uses "same label every time, no rotation" — but the build's R-NAMEDISCIPLINE expects a `Rotation: a / b / c` line declaring at least three aliases.
- **Suggested fix:** Either add a rotation line for the master (e.g. `the master / the elder / the teacher`) or document the no-rotation choice as a contract override.

#### R-HONORIFIC-BOTH-BOUNDS — Prophet honorific never expanded
- **File:** _system/episode-drafts/EP18-syllogism-of-divine-justice/00-framing.md
- **Context:** The first mention of the Prophet in spoken output requires "peace and blessings of Allah be upon him" exactly once (then never again). The framing carries no Prophet mention at all in this episode (the argument turns on Allah's justice + chosen witnesses generically), so the bound is technically violated 0× ≠ 1×.
- **Suggested fix:** If the hosts will name the Prophet in voice, add a line to Name discipline: "On first mention of the Prophet, say 'peace and blessings of Allah be upon him' once; thereafter no honorific." If they will not name the Prophet at all in this episode, document the exception in the framing.

### P2 (advisory)

None new.

## Health metrics

| Chapter | Words | Em-dashes | "this chapter" | Phonetic gaps | Doctrinal (T) |
|---|---|---|---|---|---|
| ch18b-syllogism-of-divine-justice | 2,395 | 0 (was 32) | 0 (was 1) | 0 | 0 findings |

| Framing | Chars | Words | Sections | NotebookLM ceiling |
|---|---|---|---|---|
| EP18-syllogism-of-divine-justice/00-framing.md | 4,499 | 730 | 7 H2 sections | OK (< 4500) |

## Convergence

Iteration 1 applied 8 auto-fixes (B5, B1, K1, I1, H3, M1, M2, R4). Iteration 2 trimmed the framing to land under the 4500-char NotebookLM Customize-box ceiling without losing any of the inserted steering clauses. Build script `build_episode_txt.py` validates and emits cleanly. Three P1 findings remain — all require authoring judgment (chapter character-name policy, framing rotation declaration, Prophet-honorific bound). No P0.
