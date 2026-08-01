---
postprod_version: 1.0
episode: EP04-worship-alms-and-war-void-without-the-imam
chapter_ref: ch04d-worship-alms-and-war-void-without-the-imam
archetype: scholarly-deep-dive
content_profile: islamic_scholarly / deep_dive / extended / traditional
verdict: BLOCKED
p0_count: 1
p1_count: 4
p2_count: 4
duration_min: 34.5
duration_target_min: 50-60
audited: 2026-08-01
---

# Postprod Audit — EP04-worship-alms-and-war-void-without-the-imam

## Pairing
Audio `m4a/ch04d-worship-alms-and-war-void-without-the-imam.m4a` (34.5 min) paired to `chapters/ch04d-worship-alms-and-war-void-without-the-imam.txt` by exact stem match.
Transcript `m4a/transcripts/ch04d-worship-alms-and-war-void-without-the-imam.transcript.txt` (6070 words), mirrored at `transcripts/EP04-worship-alms-and-war-void-without-the-imam.transcript.txt`.
Confidence: exact. No inference required, no ambiguity.

## What held

The chapter's hardest structure survives intact: the newborn-knows-nothing argument, the donkey and the dog as proof that knowledge is not natural, the chain of teachers ending in one taught by God, the hujja and the legal excuse against God, the circle / the number one / the dot with the explicit correction that the "one" is **not** the Creator, the qibla and imam sharing a root, the twenty-seven-fold multiplier located in the leader rather than the crowd, the intention-must-match rule, the guarantor principle, the khums replacing what the family was forbidden, the bayt al-mal, and — best of all — the fork against the jurists laid out in both prongs exactly as the source builds it. Quran 16:78, 14:37, 9:103 all licensed and correct. "The four Sunni school-founders" is the framing's own label, used correctly. The conclusion lands on "the purified progeny of Taha and Yasin," which is the source's own phrase.

## Findings

### PR-PJ-01a (P0) — Host names spoken in the first six words, one of them wrong; spine deliveries announced
*"Welcome I am John and I'm Anna you are joining us for an in-depth conversation..."*
"John" and "Hannah" are the framing's internal host directives. They are spoken here as an introduction, and the second is rendered **Anna**, not Hannah — so the series introduces a host by a name it does not use anywhere else. "John" is spoken again mid-episode (*"I don't buy that yet, John"*).
Worse, both spine repeats are announced as spine repeats:
*"It requires us to state the spine of this argument verbatim for the second time because we now see it applied to the heaviest machinery of society."*
*"Which brings us back for the third and final time to the unyielding core of the author's vision. We must state the spine verbatim one last time."*
`R-RECURRING-THESIS` asks for three verbatim repetitions. It does not ask the hosts to count them out loud. Also present: *"He does this using the third and final analogy permitted in his framework"* and *"This is our second permitted analogy."*

### PR-PJ-02 (P1) — The say-it-once rule broken seven times, all in the same shape
Every framing says "Say each term ONCE. Never say the original spelling and the English form back-to-back." This episode does exactly that, seven times:
*"He introduces the qibla. The prayer direction."* / *"This gathering centers around the kutbah. The sermon."* / *"The author introduces the institution of Zakat. So the alms."* / *"they were given the Comes. The 5th."* / *"Only the legitimate leader rightfully holds the Bait al-Mal. A public treasury."* / *"he turns to the hoodood. The prescribed penalties."* / *"You need what is called walaya. So the bond of allegiance or lawful authority."*
This is the same defect the pipeline already has a permanent guard against on the source side (`R-PRONUNCIATION-DOUBLE` in `build_episode_txt.py`). The guard cannot see the output, which is exactly why it reappears here.

### PR-PJ-09 (P1) — An unrequested impartiality disclaimer
*"and just to be absolutely clear from the outset we are going to unpack the classical Ismaili reading of these practices we are impartially reporting the architecture of this world ... Yeah, we aren't taking sides in theological disputes here. We're just treating the argument with the rigor it demands."*
The framing asks the hosts to qualify doctrine as "the classical Ismaili reading" — a scholarly attribution. It does not ask for a neutrality statement. What the hosts added is an editorial stance, delivered in the first minute, on a book being read for a traditional Ismaili audience. It also trips `DEEP_DIVE_SELF_REFERENCE_PATTERNS` ("we are going to unpack").

### PR-PC-01 / PR-PJ-04 (P1) — Forbidden vocabulary
*"Oh, wow. I mean, that is a profound"* — "wow" is on every framing's forbidden list.

### PR-PD-03 (P2) — Zakat described as optional, then contradicted one sentence later
*"The author introduces the institution of Zakat. So the alms. Yes. Now, we have to be clear, this is an optional charity. This isn't tossing a few coins in a box when you feel generous. This is a fundamental pillar of the law, a required structural purification of your wealth."*
The two sentences cannot both be true. Almost certainly a dropped "not" in transcription — **but if the audio says it, an episode about the alms opens its alms section by calling zakat optional.** Verify by ear.

### PR-PE-04 (P2) — Microcosm/macrocosm inverted
*"If the macrocosm of a daily ritual requires absolute synchronized obedience in both your body and your mind, then the macrocosm of a believer's entire life requires the exact same synchronized obedience."*
Both halves are called the macrocosm. The source's move is the lesser case proving the greater; naming both terms identically destroys the inference the sentence is making.

### PR-PF-01 (P2) — The strongest internal-critique move is dropped
The source closes the war argument with al-Shafi'i's own confession: "Had it not been for the Commander of the Faithful, Ali b. Abi Talib, we would not have known how to fight the rebels, nor how to distinguish the rebel from the rightful believer." An opponent's founder testifying for the first imam is the sharpest thing in the chapter and it is not in the episode. Also dropped: Quran 4:64 on the Messenger's intercession, and the Saturday / Ramadan / one-hour-of-the-day extension of the summit pattern into the calendar.

### PR-PB-01 (P2) — "ranks of the mission" generalized away
The source: "exactly as the imam needs no other rank **in the hierarchy of the mission** in his age, while every rank needs him." The episode: *"Every other shape, every other rank in society or religion relies on that center."* The daawa hierarchy becomes "society or religion."

### PR-PG-01 (P2) — Filler
"Exactly" x20, " Yeah," x11, "wow" x1 in 6,070 words.

## Hallucination sweep — clean
No invented citation, no invented history. The twenty-seven-fold multiplier, the four masters and their four contradictory verdicts, the squalid bargain, the mirror-image line, the walaya requirement, Taha and Yasin — every one is in `chapters/ch04d-*.txt`. This is the cleanest episode in the series on traceability.
