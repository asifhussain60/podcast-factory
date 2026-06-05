---
postprod_version: 1.0
book_slug: ayyuhal-walad
verdict: SHIP-WITH-CAUTION
total_p0: 0
total_p1: 11
total_p2: 6
audited: 2026-06-05
archetype: islamic-scholastic-text (scholarly-deep-dive)
episodes_audited: 4
---

# Postprod Rollup — O Beloved Son (Ayyuhal-Walad)

## Verdict: SHIP-WITH-CAUTION

Zero P0 findings. Eleven P1 findings across four episodes. Six P2 findings. No hallucinated content.
Video layer can proceed after author review of the four decisions listed below.

## Per-Chapter Summary

| Episode | Title | P0 | P1 | P2 | Verdict |
|---|---|---|---|---|---|
| EP01 | Knowledge Without Action | 0 | 4 | 2 | SHIP-WITH-CAUTION |
| EP02 | The Path of Obedience and Struggle | 0 | 3 | 2 | SHIP-WITH-CAUTION |
| EP03 | The Shaykh and the Disciple's Rule of Life | 0 | 1 | 1 | SHIP-WITH-CAUTION |
| EP04 | Eight Admonitions and a Closing Prayer | 0 | 2 | 1 | SHIP-WITH-CAUTION |

Note: PR-PA-01 (filename drift) appears in all 4 episodes but is counted as one systemic finding delegated to vacuum.

## Full Finding Register

| ID | Loop | Sev | Episode | Summary |
|---|---|---|---|---|
| PR-PA-01 | Filename | P1 | All | m4a stems use ch0N-ayyuhal-walad, not canonical ch0N-slug. Delegate to vacuum. |
| PR-PC-01 | Phonetic | P1 | EP01 | "Ghazali" used by name ~12x instead of "the master." |
| PR-PC-02 | Phonetic | P1 | EP02 | "Shibli," "Hasan al-Basri," "Thari" used by Arabic name instead of required aliases. |
| PR-PC-03 | Phonetic | P2 | EP02 | Arabic phrase "Zakartu unniata" spoken aloud — TTS rendering will be unclear. |
| PR-PC-04 | Phonetic | P2 | EP04 | "Ya Gaffer" instead of "Ya Ghaffar" in closing supplication. TTS homophone error. |
| PR-PE-01 | Archetype | P1 | EP02 | Model-invented OS/software analogy for the Shari'ah — not in source, banned by framing. |
| PR-PF-01 | Framing intent | P1 | EP01 | Spine plants diffuse rather than at structural seams. |
| PR-PF-02 | Framing intent | P1 | EP02 | Mid-episode spine plant missing between edge-cases and Mujahada sections. |
| PR-PF-03 | Framing intent | P1 | EP03 | Mid-episode spine plant missing between eight benefits and Shaykh sections. |
| PR-PF-04 | Framing intent | P1 | EP04 | Mid-episode spine plant not at exact refrainings-to-takings seam. |
| PR-PH-01 | Framing intent | P1 | EP01 | EP01 pre-expounds ~40% of EP02 content. Source-accurate but structurally misplaced. |
| PR-PI-01 | Opening/closing | P1 | EP01 | Opening inverts welcome-then-hook; work not named in first two sentences. |
| PR-PI-02 | Opening/closing | P1 | EP04 | "Al-Malik" rendered as "Al-Amail" in closing signature. |
| PR-PG-01 | Filler | P2 | EP01,EP03,EP04 | "Exactly" as turn-opener by Host B — systemic. |
| PR-PG-02 | Filler | P2 | EP02 | "Right?" as tag and "Oh" interjections — banned by framing. |
| PR-PJ-01 | Protocol | P2 | EP01 | Cold-open fitness analogy not in source and not one of three permitted analogies. |

## Vacuum Delegation Actions

1. Rename content/Islamic/ayyuhal-walad/m4a/ch01-ayyuhal-walad.m4a → ch01a-knowledge-without-action.m4a
2. Rename content/Islamic/ayyuhal-walad/m4a/ch02-ayyuhal-walad.m4a → ch02b-the-path-of-obedience-and-struggle.m4a
3. Rename content/Islamic/ayyuhal-walad/m4a/ch03-ayyuhal-walad.m4a → ch03-the-shaykh-and-the-disciples-rule-of-life.m4a
4. Rename content/Islamic/ayyuhal-walad/m4a/ch04-ayyuhal-walad.m4a → ch04-eight-admonitions-and-a-closing-prayer.m4a

## Author Decisions Required

### Decision 1 — EP01/EP02 content overlap (PR-PH-01) — HIGH PRIORITY
EP01 contains Shibli's hadith, the Mujahada sword, the four conditions of the seeker, and the obedience-principle edge-cases. This material belongs exclusively to EP02 per the chapter contracts. A listener hears this material twice.

Option A: Regenerate EP01 in NotebookLM using a trimmed source upload that excludes the cure-half of ch01a (cut the episode text at the end of the three closing witnesses and the Prophetic hinge, before the obedience-and-struggle content begins).
Option B: Accept the overlap. Update show notes to reflect that EP01 serves as a combined diagnosis-and-cure episode while EP02 provides focused treatment.

### Decision 2 — Name discipline failures (PR-PC-01, PR-PC-02)
"Ghazali" in EP01, and "Shibli," "Hasan al-Basri," "Thari" in EP02 spoken by Arabic name despite aliasing instructions.

Option A: Regenerate affected episodes with tighter framing — add a stronger explicit instruction to never speak the Arabic name and always substitute the alias, with the alias restated in all-caps.
Option B: Accept — the names as spoken are recognizable to listeners and the phonetics are acceptable. Downgrade to cosmetic.

### Decision 3 — Model-invented OS analogy (PR-PE-01)
The OS/software analogy for the Shari'ah in EP02 is effective but was not sourced from the chapter.

Option A: Regenerate EP02 with an explicit additional guard: "The analogy for the Shari'ah must draw only from the source text. Do not invent a technology analogy."
Option B: Accept — the analogy illuminates the concept without distorting it. Add a note in the source-side files that this analogy is approved for future framings of this concept.

### Decision 4 — Al-Malik rendering error (PR-PI-02)
The book's closing signature renders "Al-Malik" as "Al-Amail." This is the letter's final seal.

Option A: Regenerate the final segment of EP04 in NotebookLM with an explicit pronunciation guard for "Al-Malik" (al-MA-lik, 3 syllables).
Option B: Accept — the English description ("the Absolute Sovereign") follows immediately and delivers the doctrinal meaning.

## Doctrinal Fidelity Assessment

High. All major source-chapter content was honored:
- Junaid's dream rendered faithfully and with appropriate weight.
- Eight benefits of Hatim ibn Ism all present with Quranic anchors.
- Four definitions (Tasawwuf, servitude, Tawakkul, Ikhlas) present and precise.
- Full closing supplication intact with all 11 divine names.
- Worshipper-and-angel story present with Allah's verdict verbatim.
- Four-angel architecture of the night complete and in order.
- Theological precision of "grace is not earned but action prepares the ground" preserved.
- No hallucinated claims found across any episode.
