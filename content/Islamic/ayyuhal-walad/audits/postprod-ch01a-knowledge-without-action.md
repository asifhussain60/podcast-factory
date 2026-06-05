---
postprod_version: 1.0
episode: EP01-knowledge-without-action
chapter_ref: ch01a-knowledge-without-action
verdict: SHIP-READY
p0_count: 0
p1_count: 0
p2_count: 4
audited: 2026-06-05
audit_revision: 2 (post-dedup regeneration)
archetype: islamic-scholastic-text (scholarly-deep-dive)
---

# Postprod Audit — EP01: Knowledge Without Action (Revision 2)

## Pairing
Transcript `EP01-knowledge-without-action.transcript.txt` paired to `ch01a-knowledge-without-action` by stem match.
Audio `ch01-ayyuhal-walad.m4a` paired by upload position 1.
Transcript length: 20,835 chars (~3,464 words, approximately 22 minutes).

---

## Primary Check — EP01/EP02 Content Overlap (Dedup Verification)

**RESOLVED.** The regenerated EP01 contains none of the EP02 cure-content that blocked the original audit (PR-PH-01).

Terms confirmed absent from the new transcript:

| EP02 content | Absent |
|---|---|
| mujahadah / mujahada | confirmed absent |
| dawn watch sequence | confirmed absent |
| Four conditions of the sincere seeker | confirmed absent |
| Shibli's hadith of the four proportions | confirmed absent |
| bid'a (innovation) | confirmed absent |
| Taubatun Nasuh (repentance) | confirmed absent |
| Fard Kifayah (communal obligation) | confirmed absent |
| Luqman / rooster testament | confirmed absent |
| Shari'ah obedience-frame edge-cases | confirmed absent |
| Anti-false-Sufi warning | confirmed absent |
| nafs / lower self | confirmed absent |

The six "obedience" occurrences in the new transcript are all legitimate EP01 contexts: the scholar substituting intellectual acquisition for physical obedience, the warrior parable's swing, the worshipper-and-angel story's unconditional servitude. None are the EP02 Shari'ah-prescription framing.

The episode ends correctly on the Prophetic hinge (self-accounting command), the three closing witnesses, and the lion-still-coming final image — without transitioning into the cure.

---

## Findings

### PR-PA-01 (P2) — Filename drift
m4a file stem `ch01-ayyuhal-walad` does not match canonical `ch01a-knowledge-without-action`.
**delegate_to: vacuum** — rename to `ch01a-knowledge-without-action.m4a`
(Unchanged from revision 1; the rename was not executed between audits.)

### PR-PC-01 (P2) — TTS rendering of "Ghazali" in opening attribution
The transcript's opening sentence renders "Ghazali" via TTS as "Gaza H. Lee" (Turboscribe captures what NotebookLM's TTS pronounced). This is a single occurrence in the possessive attribution sentence ("Imam al-Ghazali's … letter to his student"). The episode then uses "the master" 28 times throughout, with no further Arabic-name uses. The name discipline is substantially honored; only the opening attribution sentence uses the Arabic name at all. Severity reduced to P2 (cosmetic; doctrinal integrity unaffected; single occurrence in an attribution context).

### PR-PC-02 (P2) — TTS rendering of "Iman" as "Eman Ein, E-M-I-N"
The hadith defining faith is rendered as "what is known as Eman Ein, E-M-I-N" — the TTS has parsed the phonetic guide `ee-MAAN` as a spoken string "E-M-I-N." The definition that follows ("testimony with the tongue, affirmation with the heart, and action upon the limbs") is complete and correct. Cosmetic artifact from how the phonetic notation was embedded in the framing text.

### PR-PC-03 (P2) — "Asan al-Basri" double-rendering
Hasan al-Basri's name is spoken as "Hasan al-Basri, Asan al-Basri" — the TTS pronounced the name twice, once with the H and once without. Occurs once in the three-closing-witnesses section. The alias "early teacher of the city of Basra" frames the introduction correctly; the double-name is a TTS artifact, not a name-discipline failure.

---

## Previously-Flagged Issues Now Resolved

| Old Finding | Status | Notes |
|---|---|---|
| PR-PH-01 (P1) — EP02 content pre-expounded | RESOLVED | All cure-content absent from new transcript |
| PR-PI-01 (P1) — Opening welcome failure | RESOLVED | New opening names work in sentence 1, previews teaching in sentence 2, plants spine in sentence 3 |
| PR-PF-01 (P1) — Spine plants diffuse | RESOLVED | Four spine plants at 1%, 40%, 78%, 97% — opening / mid-diagnosis / grace-hinge / closing |
| PR-PC-01 (P1) — "Ghazali" 12–15x by name | RESOLVED (P2 remnant) | Now 1 occurrence in opening attribution only; 28x "the master" throughout |
| PR-PG-01 (P2) — "Exactly" as turn-opener 6x | RESOLVED | Now 2 occurrences — below threshold |
| PR-PJ-01 (P2) — Fitness/biology cold-open analogy | RESOLVED | Cold-open analogy gone; episode opens directly on the letter and its verdict |

---

## Anchor Passage Coverage

All required EP01 anchors are present:

| Anchor | Present |
|---|---|
| Prophet's prayer "refuge from knowledge that is of no benefit" | YES |
| 40-year clock warning | YES |
| Scholar's severest torment warning | YES |
| Junaid's dream (great master of the inner path, Tahajjud cycles) | YES |
| Lion-and-warrior parable | YES (4x) |
| Medicine-unswallowed parable | YES (3x) |
| Wine punchline (2,000 pounds of wine) | YES |
| Four Quranic verses including atom's weight | YES |
| Five pillars hadith | YES |
| Iman definition (tongue, heart, limbs) | YES (with TTS artifact — see PC-02) |
| Grace-is-not-earned clarification + "Mercy close to doers of good" | YES |
| Worshipper-and-angel story with Allah's verdict | YES |
| Self-accounting Prophetic hinge | YES |
| Three closing witnesses (Commander of the Faithful / early Basran teacher / anonymous intimate) | YES |
| Lion-still-coming closing image | YES |
| Reflective closing question | YES |

---

## Positive Notes
- The structural architecture of the episode is now clean: diagnosis only, ending at the hinge.
- The spine ("Knowledge alone, without righteous deeds, will not benefit you on the Day of Judgment") is planted four times at architecturally legible positions — opening, mid-diagnosis seam, grace-hinge pivot, closing.
- The Junaid dream is rendered with appropriate weight and correct alias.
- The worshipper-and-angel story is complete including Allah's verdict.
- All three closing witnesses present in the correct order.
- No hallucinated claims. All content traces to source.
- No forbidden vocabulary (podcast, social media, PBUH, or modern-world terms).
