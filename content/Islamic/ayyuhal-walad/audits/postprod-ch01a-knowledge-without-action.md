---
postprod_version: 1.0
episode: EP01-knowledge-without-action
chapter_ref: ch01a-knowledge-without-action
verdict: SHIP-WITH-CAUTION
p0_count: 0
p1_count: 4
p2_count: 2
audited: 2026-06-05
archetype: islamic-scholastic-text (scholarly-deep-dive)
---

# Postprod Audit — EP01: Knowledge Without Action

## Pairing
Transcript `EP01-knowledge-without-action.transcript.txt` paired to `ch01a-knowledge-without-action` by stem match.
Audio `ch01-ayyuhal-walad.m4a` paired by upload position 1.

## Findings

### PR-PA-01 (P1) — Filename drift
m4a file stem `ch01-ayyuhal-walad` does not match canonical `ch01a-knowledge-without-action`.
**delegate_to: vacuum** — rename to `ch01a-knowledge-without-action.m4a`

### PR-PC-01 (P1) — Phonetic drift / name discipline
"Ghazali" used by Arabic name approximately 12–15 times throughout the episode instead of the required alias "the master." The framing name discipline states "Ghazali → the master. Never speak his Arabic name." NotebookLM did not suppress the name. Impact: mild phonetic inconsistency (TTS produces variable rendering of Arabic names); editorial inconsistency with the name-aliasing protocol.

### PR-PF-01 (P1) — Framing-intent drift: spine placement
The spine "Knowledge alone, without righteous deeds, will not benefit you on the Day of Judgment" is present in the episode but its three required verbatim structural plants (opening / mid-episode pivot / close) are diffuse rather than planted at clear seam positions. The three-repetition structure the framing mandated as structural anchors is not clearly legible as deliberate architecture.

### PR-PH-01 (P1) — Framing-intent drift: pre-expounded EP02 content
EP01 contains approximately 40% of EP02's three-part focus: the "worship is another name for obedience" principle, all four edge-cases (Eid fast, forbidden-hour prayer, unlawfully-occupied ground, lawful intimacy), the full Mujahada sword doctrine, warning against false Sufis, all four conditions of the sincere seeker, and Shibli's hadith of the four proportions. The EP01 framing explicitly states "Do not pre-expound the cure" and identifies the four conditions and Shibli's hadith as EP02 content. NotebookLM generated from the full enriched source file which contains the cure-half. Content is source-accurate but structurally misplaced across episode boundary.
**Author decision required** — see book-level rollup Decision 1.

### PR-PI-01 (P1) — Opening does not satisfy welcome directive
The episode opens with a fitness analogy (cellular respiration / push-up mechanics) without first delivering the required "warm 1–2 sentence welcome in the seeker's voice" that greets the listener, names the work, and previews the teaching. The work (Imam al-Ghazali's letter, O Beloved Son) is named several paragraphs into the episode, not in the opening two sentences.

### PR-PG-01 (P2) — Filler: "Exactly" as turn-opener
"Exactly" used by Host B (female, Hannah) as the first word of a turn approximately 6 times, in direct violation of the framing pushback discipline: "Her first word of a turn must not be 'Exactly,' 'Yeah,' 'Right,' 'Of course,' 'Absolutely.'" "Yeah" also appears as a turn-opener multiple times.

### PR-PJ-01 (P2) — Protocol: non-permitted analogy
The cold open uses a fitness/biology analogy (push-ups, cellular respiration, macronutrient breakdown of green lentils) not present in the source chapter and not among the three permitted analogies for EP01 (warrior-and-lion, medicine-unswallowed, Junaid's scale). The framing states "No new analogies — only the warrior-and-lion, the medicine-unswallowed, Junaid's scale." This is a mild violation — the analogy functions as an effective cold-open hook and does not distort the doctrinal content.

## Positive notes
- Junaid's dream rendered faithfully and with appropriate weight — "all discourses and spiritual signs turned out to be of no avail... certain cycles of Tahajjud were of benefit."
- Lion-and-warrior parable present and accurate.
- Sick-man-and-medicine parable present and accurate; wine punchline included.
- Worshipper-and-angel story present and accurate; Allah's verdict ("Bear witness, all of you, that I have forgiven him") present.
- Three closing witnesses (Commander of the Faithful, early Basran teacher, anonymous intimate) all present.
- Closing ends on the lion-still-charging image and reflective question — correct per framing.
- No hallucinated claims found; all doctrinal content traces to source.
