---
postprod_version: 1.0
episode: EP02-the-path-of-obedience-and-struggle
chapter_ref: ch02b-the-path-of-obedience-and-struggle
verdict: SHIP-WITH-CAUTION
p0_count: 0
p1_count: 3
p2_count: 2
audited: 2026-06-05
archetype: islamic-scholastic-text (scholarly-deep-dive)
---

# Postprod Audit — EP02: The Path of Obedience and Struggle

## Pairing
Transcript `EP02-the-path-of-obedience-and-struggle.transcript.txt` paired to `ch02b-the-path-of-obedience-and-struggle` by stem match.
Audio `ch02-ayyuhal-walad.m4a` paired by upload position 2.

## Findings

### PR-PA-01 (P1) — Filename drift
m4a file stem `ch02-ayyuhal-walad` does not match canonical `ch02b-the-path-of-obedience-and-struggle`.
**delegate_to: vacuum** — rename to `ch02b-the-path-of-obedience-and-struggle.m4a`

### PR-PC-02 (P1) — Phonetic drift / name discipline
Three name-discipline failures:
1. "Shibli" used by Arabic name (multiple instances) rather than required alias "the Baghdad mystic."
2. "Hasan al-Basri" used by Arabic name (multiple instances) rather than required alias "the early Basran teacher."
3. "Thari" (abbreviated Anglicization of Sufyan al-Thawri) used rather than required alias "the early Kufan ascetic."
The framing name discipline explicitly states for each figure: "Never speak his Arabic name."

### PR-PE-01 (P1) — Archetype drift: model-invented analogy
The operating-system/software analogy ("the prophetic frame is the operating system; fasting on Eid is an app with a fatal error that crashes the machine; lawful intimacy is a basic app that runs flawlessly because it matches the OS") is a model-invented analogy with no basis in the source chapter. The framing explicitly states "No new analogies" and the archetype (§7.1) prohibits invented analogies not sourced from the chapter's own images. The analogy is effective and explanatory but constitutes a protocol violation.
**Author decision required** — see book-level rollup Decision 3.

### PR-PF-02 (P1) — Framing-intent drift: mid-episode spine plant missing
The spine "Worship is another name for obedience" is delivered correctly in the opening. The framing requires it to return verbatim at the mid-episode pivot (between the edge-case section and the Mujahada section). The transcript moves from the edge-case analysis to Mujahada without the verbatim plant. Third plant at close is present. One of three required plants absent.

### PR-PC-03 (P2) — Arabic phrase spoken aloud
The Arabic phrase "Zakartu unniata" (Hasan al-Basri's reply on the cold cup) is spoken aloud in the transcript, meaning NotebookLM spoke the Arabic text. The archetype discipline (§3.1) requires that Arabic text not be spoken; the framing included this phrase as an anchor passage with its English translation. TTS rendering of Arabic will be phonetically unclear. The phrase is present as a verbatim anchor and its English translation immediately follows, so the doctrinal content is intact — this is a P2 audio-clarity issue.

### PR-PG-02 (P2) — Filler: banned interjections
"Right?" used as tag-question approximately 10 times. "Oh" as an interjection multiple times. The framing bans "right?" explicitly. One instance of "Oh wow" detected. These are systemic NotebookLM dialogue patterns that the framing's Do-Not list did not successfully suppress.

## Positive notes
- "The master" used consistently throughout EP02 for Ghazali — name discipline significantly improved over EP01.
- Hasan al-Basri's sigh and the cold-cup story rendered with appropriate restraint — not inflated.
- Four-angel architecture of the night complete and in correct chronological order with the narrowing-then-failing sequence preserved.
- Luqman's testament ("Do not let the rooster prove more intelligent than you") present and accurate.
- The pre-dawn proclamation ("Is there anyone who repents... asks... seeks forgiveness") present.
- Shibli's hadith of the four proportions present in full and accurate.
- False-Sufi polemic correctly framed as defense of true Sufism, not a blanket dismissal.
- Four conditions of the sincere seeker all present and correctly sequenced.
- Opening and closing satisfy the framing's welcome/closing directives.
