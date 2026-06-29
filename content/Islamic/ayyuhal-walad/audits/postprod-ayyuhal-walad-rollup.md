---
postprod_version: 1.0
book_slug: ayyuhal-walad
verdict: SHIP-WITH-CAUTION
total_p0: 0
total_p1: 7
total_p2: 9
audited: 2026-06-05
rollup_revision: 2 (EP01 re-audited after dedup regeneration — 2026-06-05)
archetype: islamic-scholastic-text (scholarly-deep-dive)
episodes_audited: 4
---

# Postprod Rollup — O Beloved Son (Ayyuhal-Walad)

## Verdict: SHIP-WITH-CAUTION

Zero P0 findings. Seven P1 findings across EP02–EP04 (none in EP01). Nine P2 findings. No hallucinated content.
The critical EP01/EP02 content overlap (Decision 1 from rollup revision 1) is confirmed resolved by the regeneration. EP01 is now SHIP-READY on its own.
The book-level verdict remains SHIP-WITH-CAUTION due to open P1 findings in EP02–EP04. Author review of Decisions 2–4 required before publishing.

## Per-Chapter Summary

| Episode | Title | P0 | P1 | P2 | Verdict |
|---|---|---|---|---|---|
| EP01 | Knowledge Without Action | 0 | 0 | 4 | SHIP-READY |
| EP02 | The Path of Obedience and Struggle | 0 | 3 | 2 | SHIP-WITH-CAUTION |
| EP03 | The Shaykh and the Disciple's Rule of Life | 0 | 1 | 1 | SHIP-WITH-CAUTION |
| EP04 | Eight Admonitions and a Closing Prayer | 0 | 2 | 1 | SHIP-WITH-CAUTION |

Note: PR-PA-01 (filename drift) applies to all 4 episodes as a systemic P2 item delegated to vacuum.
EP01 P1 count dropped from 4 to 0 following dedup regeneration. EP01 P2 count is 4 (PA-01 filename + three TTS rendering artifacts).

## Full Finding Register

| ID | Loop | Sev | Episode | Summary |
|---|---|---|---|---|
| PR-PA-01 | Filename | P2 | All | m4a stems use ch0N-ayyuhal-walad, not canonical ch0N-slug. Delegate to vacuum. |
| PR-PC-01 | Phonetic | P2 | EP01 | "Ghazali" as "Gaza H. Lee" in opening attribution — 1 occurrence; 28x "the master" throughout. |
| PR-PC-02 | Phonetic | P2 | EP01 | "Iman" rendered as "Eman Ein, E-M-I-N" — TTS phonetic-guide parsing artifact. |
| PR-PC-03 | Phonetic | P2 | EP01 | "Hasan al-Basri, Asan al-Basri" double-render — TTS dropped the H on the second pass. |
| PR-PC-04 | Phonetic | P1 | EP02 | "Shibli," "Hasan al-Basri," "Thari" used by Arabic name instead of required aliases. |
| PR-PC-05 | Phonetic | P2 | EP02 | Arabic phrase "Zakartu unniata" spoken aloud — TTS rendering will be unclear. |
| PR-PC-06 | Phonetic | P2 | EP04 | "Ya Gaffer" instead of "Ya Ghaffar" in closing supplication. TTS homophone error. |
| PR-PE-01 | Archetype | P1 | EP02 | Model-invented OS/software analogy for the Shari'ah — not in source, banned by framing. |
| PR-PF-01 | Framing intent | P1 | EP02 | Mid-episode spine plant missing between edge-cases and Mujahada sections. |
| PR-PF-02 | Framing intent | P1 | EP03 | Mid-episode spine plant missing between eight benefits and Shaykh sections. |
| PR-PF-03 | Framing intent | P1 | EP04 | Mid-episode spine plant not at exact refrainings-to-takings seam. |
| PR-PI-01 | Opening/closing | P1 | EP04 | "Al-Malik" rendered as "Al-Amail" in closing signature. |
| PR-PG-01 | Filler | P2 | EP02 | "Right?" as tag and "Oh" interjections — banned by framing. |

## Resolved Findings (EP01 Regeneration)

The following findings from rollup revision 1 are now closed:

| Old ID | Was | Resolution |
|---|---|---|
| PR-PH-01 (P1) | EP01 pre-expounds ~40% of EP02 content | CLOSED — all EP02 cure-content absent from new transcript |
| PR-PI-01 (P1) | EP01 opening inverts welcome | CLOSED — new opening names work in sentence 1, previews teaching in sentence 2 |
| PR-PF-01 (P1) | EP01 spine plants diffuse | CLOSED — four plants at 1%/40%/78%/97% |
| PR-PC-01 (P1) | "Ghazali" 12–15x by name | DOWNGRADED to P2 — 1 occurrence in opening attribution only |
| PR-PG-01 (P2) | "Exactly" 6x as turn-opener | CLOSED — 2 occurrences, below threshold |
| PR-PJ-01 (P2) | Fitness/biology cold-open analogy | CLOSED — cold-open gone |

## Vacuum Delegation Actions

1. Rename `content/Islamic/ayyuhal-walad/m4a/ch01-ayyuhal-walad.m4a` → `ch01a-knowledge-without-action.m4a`
2. Rename `content/Islamic/ayyuhal-walad/m4a/ch02-ayyuhal-walad.m4a` → `ch02b-the-path-of-obedience-and-struggle.m4a`
3. Rename `content/Islamic/ayyuhal-walad/m4a/ch03-ayyuhal-walad.m4a` → `ch03-the-shaykh-and-the-disciples-rule-of-life.m4a`
4. Rename `content/Islamic/ayyuhal-walad/m4a/ch04-ayyuhal-walad.m4a` → `ch04-eight-admonitions-and-a-closing-prayer.m4a`

## Author Decisions Required

### Decision 2 — Name discipline failures in EP02 (PR-PC-04) — OPEN
"Shibli," "Hasan al-Basri," and "Thari" spoken by Arabic name in EP02 despite aliasing instructions.

Option A: Regenerate EP02 with a stronger explicit instruction — never speak the Arabic name, always substitute the alias, with the alias restated in all-caps and the Arabic name removed entirely from the framing text.
Option B: Accept — the names as spoken are recognizable to listeners and the phonetics are acceptable. Downgrade to cosmetic.

### Decision 3 — Model-invented OS analogy in EP02 (PR-PE-01) — OPEN
The OS/software analogy for the Shari'ah in EP02 is effective but was not sourced from the chapter.

Option A: Regenerate EP02 with an explicit additional guard: "The analogy for the Shari'ah must draw only from the source text. Do not invent a technology analogy."
Option B: Accept — the analogy illuminates the concept without distorting it. Add a note in the source-side files that this analogy is approved for future framings of this concept.

### Decision 4 — Al-Malik rendering error in EP04 (PR-PI-01) — OPEN
The book's closing signature renders "Al-Malik" as "Al-Amail." This is the letter's final seal.

Option A: Regenerate the final segment of EP04 in NotebookLM with an explicit pronunciation guard for "Al-Malik" (al-MA-lik, 3 syllables).
Option B: Accept — the English description ("the Absolute Sovereign") follows immediately and delivers the doctrinal meaning.

## Doctrinal Fidelity Assessment

High across all four episodes. All major source-chapter content honored:
- EP01: Junaid's dream, three Prophetic warnings, lion parable, medicine parable, worshipper-and-angel story, three closing witnesses — all present and accurate.
- EP02: Dawn watch sequence, four-angel architecture, Luqman/rooster, Shari'ah obedience principle, mujahadah doctrine, four conditions of the sincere seeker, Shibli's hadith of four proportions — all present.
- EP03: Eight benefits of Hatim ibn Ism all present with Quranic anchors. Four definitions (Tasawwuf, servitude, Tawakkul, Ikhlas) present and precise.
- EP04: Full closing supplication intact with all 11 divine names.
- No hallucinated claims found across any episode.
