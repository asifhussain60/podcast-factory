# NotebookLM Customize-Prompt Rules

**Normative.** This file is the single source of truth for what an episode's `00-framing.md` (which becomes the customize-prompt `episodes/EP##-<slug>.txt`) **must** and **must not** carry.

**Read by**: the podcast skill (Phase 3 + Phase 4 step 1) AND the `podcast-challenger` agent (Loops F + H + I + J + K). If this file and `notebooklm-best-practices.md` disagree, **this file wins** — best-practices is guidance, this is contract.

**Authority for the agent**: each rule below ends with `Authority for challenger:` naming the exact check ID that enforces it. If you add a rule here, add the matching check there.

---

## R-WELCOME · Welcome opening + episode summary

### Rule

The customize prompt MUST direct the two hosts to open the episode with a **welcome message** followed by a **brief summary of what is being discussed or debated**, before any source content is engaged. The welcome opens, the summary lands the listener inside the argument.

### Why

NotebookLM Audio Overviews otherwise default to "today we'll discuss…" boilerplate or jump cold into source quotes. A 15-to-30 second welcome+summary opener gives the listener orientation and a reason to keep listening.

### Required template in `00-framing.md`

Under the framing's "Opening directive" section, include verbatim (or with equivalent steering language):

```
Open the episode with a brief welcome (1 sentence) followed by a 2–3 sentence
summary naming the source, the central tension being discussed, and the
question the conversation will land. Do not open with "today we'll discuss"
or "in this episode" — open in the voice of someone genuinely glad the
listener showed up.
```

### Auto-detect pattern

Scan `00-framing.md` for the trigger phrase "welcome" within an Opening directive section. Absence → flag.

### Auto-fix or flag

**AUTO-FIX** when the framing has an Opening section but no welcome clause (insert the template above). **FLAG (P1)** when the framing has no Opening section at all (authoring decision).

### Authority for challenger

`podcast-challenger` Loop **H1** (welcome opening present) + **H2** (summary clause present).

---

## R-NOREPEAT · Anti-repetition

### Rule

The customize prompt MUST direct hosts NOT to repeat the same point, citation, framing, or rhetorical move within the same episode. When a beat has been made, it stays made; the conversation advances or it cuts.

### Why

NotebookLM has a known tendency to circle back to "the big idea" several times per episode. Listeners experience this as padding. The framing must explicitly forbid it.

### Required clause in `00-framing.md`

Under "Anti-noise rules":

```
Do not restate the central thesis more than twice across the conversation
(once at the open, once at the close). Do not re-cite a quote already cited.
Do not summarize what was just said. Each beat lands once; the next beat
moves forward.
```

### Auto-detect pattern

Scan `00-framing.md` for the substring "restate", "re-cite", or an equivalent anti-repetition directive in the Anti-noise section. Absence → flag.

### Auto-fix or flag

**AUTO-FIX** (insert the clause if Anti-noise section exists but lacks anti-repetition language). **FLAG (P1)** if Anti-noise section is absent.

### Authority for challenger

`podcast-challenger` Loop **I1** (anti-repetition clause present).

---

## R-RECURRING-THESIS · Central settled formula appears VERBATIM at three anchor points

### Rule

The chapter's central settled formula — drawn from the chapter contract's `anchor_passages` field — MUST appear in the episode VERBATIM at **three** anchor points:

 1. The **open** (Beat 1 — Crisis), as the answer the listener will hear three times.
 2. The **pivot** (Beat 4 of R-DRAMATIC-ARC), as the move that escapes the failed answers.
 3. The **close** (Beat 6 — Stakes + question), as the line the listener carries away.

Do NOT paraphrase. Do NOT abbreviate. Do NOT vary the wording. The verbatim repetition is the rule's whole point: the listener should be able to recite the formula by the end of the episode.

R-RECURRING-THESIS coexists with R-NOREPEAT: the central thesis is the ONE thing the framing is permitted to restate, and it is restated EXACTLY THREE times. Anything else still falls under R-NOREPEAT's "do not restate".

### Why

Empirical (2026-05-21 audit of *Kitab al-Riyad* Ch07 transcript): the chapter's central settled formula (`contact does not require resemblance — it requires rank, receptivity, and transmitted power`) was stated once in the transcript and never returned to. The listener finished the episode without the formula lodged. The fix is structural: anchor the formula at three predictable points (open, pivot, close), each verbatim. By the close, the formula is the listener's takeaway.

### Required clause in `00-framing.md`

Under `## Opening directive` AND `## Three-part focus` (Beat 4 + Beat 6 / Landing):

```
R-RECURRING-THESIS. The central thesis — <verbatim formula from
contract.anchor_passages> — MUST appear exactly three times in the episode,
VERBATIM: once at the opening (Beat 1), once at the pivot (Beat 4), once
at the close (Beat 6). Do not paraphrase. Do not abbreviate. Do not vary
the wording. The listener should leave able to recite it.
```

### Auto-detect pattern

If the chapter contract carries an `anchor_passages` field (or equivalent thesis-string), search the framing for that exact string. Required: ≥3 occurrences (open + pivot + close) — count occurrences in framing of the contract's verbatim thesis. If contract anchor is not available, fallback: scan for the substring `R-RECURRING-THESIS` AND the instruction to "appear … three times" / "VERBATIM" within the framing.

### Auto-fix or flag

**FLAG (P1)**. Authoring decision — picking the verbatim thesis line from the chapter's anchor passages is editorial.

### Authority for challenger

`podcast-challenger` Loop **H5** (recurring-thesis clause present AND thesis appears 3× verbatim in framing) — new check added 2026-05-21 (X16). Surface as Category H finding. Transcript-side: Loop M extends to count thesis-verbatim occurrences in the audio; <3 fires P1, >3 fires P2.

---

## R-NOBACKGROUND · No irrelevant historical background

### Rule

The customize prompt MUST direct hosts to focus on the source's main content. Historical background about the book, author, translator, century, school of thought, or genealogy is included ONLY when pertinent to the central tension AND introduced ONCE — never repeated.

### Why

Audio Overviews drift into Wikipedia-style author biographies that consume 2–3 minutes of the episode while teaching the listener nothing about the actual ideas. Background should serve the argument, never substitute for it.

### Required clause in `00-framing.md`

Under "Three-part focus" or "Anti-noise rules":

```
Stay on the source's main content — the ideas, the arguments, the
contradictions. Historical or biographical background (the author's
century, school, lineage, translator) is mentioned ONLY when it directly
explains the argument under discussion, and ONLY ONCE per episode. Do
not open with biographical context. Do not return to it after first
mention.
```

### Auto-detect pattern

Scan `00-framing.md` for the substring "main content" or "biographical" in a focus/anti-noise section. Absence → flag.

### Auto-fix or flag

**AUTO-FIX** when an appropriate section exists (insert the clause). **FLAG (P1)** otherwise.

### Authority for challenger

`podcast-challenger` Loop **I2** (no-irrelevant-background clause present).

---

## R-NAMEALIAS · Long names → short alias after first use

### Rule

The customize prompt MUST direct hosts to use a person's full name ONCE per episode (on first reference), then use a short alias for every subsequent reference. The alias is the most pronounceable shortened form, drawn from `content/_shared/arabic/05-name-alias-policy.md` for Arabic/Islamic figures or from common usage for others.

### Why

Repeating a long ceremonial author name (e.g. an honorific-prefixed multi-token full name) across 30 references in a 15-minute episode is fatiguing to the listener and consumes airtime that should carry argument. The alias is how human podcasts handle it; NotebookLM does not do it by default. (Concrete examples of long names mapped to short aliases live at [`worked-examples.md` §3](worked-examples.md#3--name-alias-clause-for-the-customize-prompt).)

### Required clause in `00-framing.md`

Under "Pronunciation hooks":

```
Name discipline. Use each long name in full ONCE on first occurrence, then
use the short alias for every subsequent reference:
 - <Long full name #1> → <short alias #1>
 - <Long full name #2> → <short alias #2>
 - <add any long name appearing in this episode>
```

The aliases come from `content/_shared/arabic/05-name-alias-policy.md` (for Arabic/Islamic figures) or from common usage for others. A worked instance of this block from one book lives at [`worked-examples.md` §3](worked-examples.md#3--name-alias-clause-for-the-customize-prompt).

### Auto-detect pattern

Scan `00-framing.md` for a "Name discipline" or "Name aliases" subsection under Pronunciation hooks. Absence when the chapter contains any name longer than 3 tokens → flag.

### Auto-fix or flag

**AUTO-FIX** when the alias is in `content/_shared/arabic/05-name-alias-policy.md` (insert the line for each long name found in the chapter). **FLAG (P1)** when a long name appears in the chapter but has no alias in the policy file (authoring decision — propose alias, accept, add to policy).

### Authority for challenger

`podcast-challenger` Loop **J1** (alias clause present) + **J2** (every long name in the chapter has a documented alias).

---

## R-NAMEDISCIPLINE · Arabic figure names appear once; rotate among English aliases thereafter

### Rule

Arabic figure names (`al-Kirmani`, `al-Sijistani`, `Abu Hatim al-Razi`, etc.) MUST appear in full ONLY ONCE per episode, on first mention, with an English appositive that establishes who the figure is (e.g. "Hamid al-Din Ahmad al-Kirmani, the author of Kitab al-Riyad"). Every subsequent reference rotates among **3–4 English aliases** drawn from a per-book rotation-set documented at `BOOK_DIR/_system/name-aliases.yml`. The Driver and Color hosts pick DIFFERENT aliases per turn so the same English alias does not repeat consecutively. The Arabic name does not return after the first occurrence — its second mention is what triggers NotebookLM to mangle it.

Stricter than R-NAMEALIAS: R-NAMEALIAS allows the short alias to be the Arabic surname (`al-Kirmani`); R-NAMEDISCIPLINE forbids that — every post-first reference is English.

### Why

Empirical (2026-05-21 audit of *Kitab al-Riyad* Ch07 transcript): NotebookLM's voice model mangled `al-Kirmani` into 8+ distinct variants across a 30-minute episode (kerr-MAH-nee, al-Quraymani, al-Karmani, etc.); `al-Hayuli` into 7+ variants. The pattern: the model successfully voices the Arabic name on first mention, then drifts on every subsequent occurrence. R-NAMEALIAS told the hosts "use a short alias" without enforcing that the alias be ENGLISH; the hosts chose `al-Kirmani` itself as the short alias and triggered the drift. R-NAMEDISCIPLINE closes that gap: the second occurrence is English; the third is a different English; the fourth is a third English; rotation prevents alias-monotony.

### Required clause in `00-framing.md`

Under a new `## Name discipline` section (or appended to Pronunciation hooks):

```
Name discipline. Each figure named below appears in full ONCE on first
mention, with the English appositive shown. Every subsequent reference
ROTATES among the listed English aliases — the Driver and Color hosts
pick different aliases per turn. The Arabic figure-name does not return
after the first occurrence.

<Figure 1>
 - First mention: <full Arabic name>, <English appositive>
 - Rotation: <english alias 1> / <english alias 2> / <english alias 3> / <english alias 4>
 - Do NOT say "<Arabic name>" more than once.

<Figure 2>
 - ...
```

Rotation sets per book live in `BOOK_DIR/_system/name-aliases.yml`. A worked instance is in the v2 lab framing for KaR Ch07 (`_system/ch07-lab/v2-revised/framing.md`).

### Auto-detect pattern

Scan `00-framing.md` for a `## Name discipline` section (or equivalent header). Within it, look for at least one rotation set — a line containing `Rotation:` or `→` followed by 3+ English aliases separated by `/` or `,`. Absence → flag.

### Auto-fix or flag

**FLAG (P1)**. Authoring decision — the rotation set per figure is editorial, not deterministic.

### Authority for challenger

`podcast-challenger` Loop **J3** (Name discipline section present + rotation sets ≥3 aliases) — new check added 2026-05-21 (X15). Surface as Category J finding when the section is missing or any figure has fewer than 3 English aliases.

---

## R-NOINTERRUPT · Host interruption avoidance

### Rule

The customize prompt MUST direct the two hosts to let each other complete a thought. No mid-sentence interjections. No talking over. A host may pick up where the other left off, but only after a beat.

### Why

NotebookLM's default voice acting includes a "natural conversation" pattern that frequently injects "yeah", "right", "exactly" mid-sentence. In long-form serious content this reads as nervous chatter and weakens the argument. The framing must forbid it.

### Required clause in `00-framing.md`

Under "Host dynamic" or "Anti-noise rules":

```
Conversation discipline. Each host completes a thought before the other
responds. No interjections ("yeah", "right", "exactly") inside the other
host's sentence. No talking over. The other host may pick up the thread
after a brief pause, but only after the first host has landed.
```

### Auto-detect pattern

Scan `00-framing.md` for the substring "interjection" or "talking over" or "completes a thought" in Host dynamic or Anti-noise. Absence → flag.

### Auto-fix or flag

**AUTO-FIX** when Host dynamic or Anti-noise section exists (insert clause). **FLAG (P1)** when neither section exists.

### Authority for challenger

`podcast-challenger` Loop **K1** (interruption-avoidance clause present).

---

## R-CHALLENGER-FRICTION · Color host pushes back ≥3 times per episode

### Rule

The Color host (Host B — `scholar_companion` or `advocate_b`) MUST push back against the Driver's or the author's claims **at least three times** per episode, using genuine doubt patterns drawn from this catalog:

 - "I don't buy that yet…"
 - "That sounds like wordplay…"
 - "Isn't this just replacing X with Y…"
 - "How is this different from hiding the problem under a different word…"
 - "If <X> isn't <body-category>, what is it actually?"

Three is the floor; four is preferred for debate-format chapters. The Color host's role is **friction**, not chorus — the listener's representative against premature certainty.

**FORBIDDEN as the Color host's first sentence in any turn**:

 - "That is a remarkably precise…"
 - "That beautifully maps…"
 - "That is the perfect translation…"
 - "That captures the essence…"
 - "Exactly"
 - "Perfect way to put it"
 - "That is fascinating"
 - "That is brilliant"

The Color host opens with doubt, counter-citation, or counter-question — never with affirmation of the prior turn.

### Why

Empirical (2026-05-21 audit of *Kitab al-Riyad* Ch07 transcript): the Color host opened ≥5 distinct turns with `That is a remarkably precise…` / `That beautifully maps…` / similar agreeable framings. The transcript read as a chorus where the Color host's role was to validate the Driver's setups rather than test them. The Color host is supposed to be the listener — the one who has not yet been persuaded — but defaults to being the Driver's enthusiastic second. Naming the pushback patterns explicitly AND banning the agreeable openers as first sentences forces the model toward genuine dialectical role.

### Required clause in `00-framing.md`

Under `## Host dynamic` (alongside the `scholar_companion + curious_mind` declaration), AND under `## Central tensions to reach`:

```
The Color host's role in this episode is GENUINE CHALLENGER, not supportive
explainer. The Color host MUST push back AT LEAST THREE times across the
episode using one of these patterns (three is the floor; four preferred):

 - "I don't buy that yet…"
 - "That sounds like wordplay…"
 - "Isn't this just replacing X with Y…"
 - "How is this different from hiding the problem under a different word…"

Per `## Central tensions to reach`, each tension carries an explicit
*Color host pushback (required):* line modeling one of the patterns above.

Forbidden as the Color host's first sentence: "That is a remarkably
precise…", "That beautifully maps…", "That is the perfect translation…",
"That captures the essence…", "Exactly", "Perfect way to put it",
"That is fascinating", "That is brilliant". The Color host opens with
doubt or counter-question, not affirmation.
```

### Auto-detect pattern

Scan `## Host dynamic` OR `## Central tensions` for: (a) presence of `challenger` or `pushback` language, AND (b) at least 2 of the required pushback patterns ("I don't buy", "sounds like wordplay", "Isn't this just replacing", "How is this different"). Absence of either → flag.

### Auto-fix or flag

**FLAG (P1)**. Authoring decision — the per-tension pushback lines must be filled in with chapter-specific content.

### Authority for challenger

`podcast-challenger` Loop **K2** (challenger-friction clause + pushback-pattern catalog present) — new check added 2026-05-21 (X16). Surface as Category K finding. Transcript-side loop M extends to count forbidden-opener firings.

---

## R-SURPRISE-MOVE · Separate-prep illusion via planted handoffs

### Rule

The framing MUST direct the conversation choreography to include **at least one moment per episode** where one host introduces a passage, citation, or question that the other host has not led with, and the other host reacts in real time. The reaction is genuine, not staged. Mechanical alternation (Host A asks → Host B answers → Host A asks → Host B answers) is forbidden.

### Why

NotebookLM's default two-host pattern is rhythmic Q-and-A. Listeners experience this as scripted. A planted "surprise move" — Host A drops a quote Host B has not framed, or Host B raises a counter-citation Host A has not invited — produces the cadence of two people who prepared separately. The episode reads as conversation, not as interview.

### Required clause in `00-framing.md`

Under "Host dynamic" → "Conversation choreography" (create the subsection if absent):

```
Plant at least one moment where one host introduces a passage, citation,
or question from the source that the other has not led toward. The other
host reacts to it in real time — taking it on directly, not deferring or
sidestepping. This breaks the rhythm of alternating Q-and-A and signals
to the listener that the hosts prepared separately. Do not stage the
surprise; let the planted passage carry the weight.
```

### Auto-detect

Scan `00-framing.md` for "Conversation choreography" subsection (or substring "plant at least one moment" / "prepared separately") within Host dynamic. Absence → flag.

### Auto-fix

**AUTO-FIX** (insert the canonical clause) when Host dynamic section exists. **FLAG (P1)** when Host dynamic itself is missing.

### Authority for challenger

`podcast-challenger` Loop **R1** (separate-prep illusion clause present) — new check added 2026-05-18.

---

## R-RESET · Reset moments between beats

### Rule

When the discussion spine has more than five beats, the framing MUST direct the hosts to insert a **reset moment** between major beat groups: a single sentence from one host re-anchoring where the conversation is, before the next beat begins. A reset is not a recap of the episode — it is a marker that names what just landed and what the next move opens.

### Why

Above five beats, NotebookLM's defaults compress past the seams: the listener loses thread, and the second half of the episode feels like a different conversation from the first. A scripted reset re-anchors without breaking conversational flow. One sentence is enough; more becomes lecture summary.

### Required clause in `00-framing.md`

Under "Three-part focus" → "Pacing" (or new "Reset moments" sub-section):

```
Between major beats, insert a single-sentence reset — one host names what
just landed, then the next beat begins. Examples:
- "So the diagnosis is in. Now the question becomes — what does it ask
 the reader to do?"
- "We've been on the inside of the experience. Let me step back and ask
 who else in the tradition was making this argument."
A reset is one sentence. It does not summarize the episode; it marks the
seam. Do not over-anchor; one reset per major beat-group is enough.
```

### Auto-detect

Scan `00-framing.md` for the substring "reset" or "single-sentence reset" within Three-part focus / Pacing / Reset moments subsection. Absence in framings whose discussion spine has >5 beats → flag.

### Auto-fix

**AUTO-FIX** (insert the canonical clause) when the framing has >5 beats in its discussion spine AND no reset directive. **FLAG (P2)** when the framing has ≤5 beats and the clause is absent (advisory only — short episodes don't need resets).

### Authority for challenger

`podcast-challenger` Loop **R2** (reset clause present when warranted) — new check added 2026-05-18. The challenger reads the discussion spine's beat count to determine whether R2 applies.

---

## R-DRAMATIC-ARC · Debate-format chapters follow a 6-beat dramatic arc

### Rule

Debate-format chapters' `## Three-part focus` (or equivalent host-spine section) MUST be structured as a **6-beat dramatic arc**, not as a topic-list. The beats:

 1. **Crisis (open)** — name the central tension with weight. The Color host raises it; the Driver does not reassure too quickly.
 2. **Failed answer A** — the first attempted answer, presented as reasonable so the listener respects it before it breaks.
 3. **Failed answer B** — a second attempted answer, also presented as reasonable. Both failed answers are honest attempts.
 4. **Pivot (verbatim thesis)** — the move that escapes both. The chapter's settled formula (from `contract.anchor_passages`) lands here VERBATIM for the second time (cf. R-RECURRING-THESIS).
 5. **Non-bodily correction (or domain-specific corrections)** — the body of the chapter's argument: each error in failed answers A and B is replaced with the correct relational/categorical structure.
 6. **Stakes + question (close)** — political, ethical, or human stakes; the chapter's recurring thesis appears VERBATIM for the third time; close on a bridge question to the next episode, NOT a recap.

Each beat lands ONCE. Beat 4 carries the thesis verbatim. Non-debate chapters may use a different spine (linear exposition, biographical arc, etc.) — R-DRAMATIC-ARC applies when the chapter contract names `debate` or `dialectic` as its mode.

### Why

Empirical (2026-05-21 audit of *Kitab al-Riyad* Ch07 transcript): the v1 framing carried a `## Three-part focus` topic-list (Focus 1, Focus 2, Focus 3) without dramatic structure. NotebookLM produced a transcript where the central tension was named and resolved within minutes; listeners got information but no suspense. The 6-beat arc preserves dialectical tension: the listener does not know which answer wins until Beat 4, and Beats 5–6 do the structural work of replacing failed body-categories with relational ones. Topic-listing collapses this into a single declarative push.

### Required clause in `00-framing.md`

Under `## Three-part focus` (rename to `## Six-beat arc` if the spine is debate-format), enumerate each beat with the marker `Beat N — <name>`:

```
The chapter's argumentative spine is a 6-beat dramatic arc. Each beat lands
once; the central thesis is repeated VERBATIM at Beat 4. Walk these in order.

Beat 1 — Crisis (open). <name the crisis with weight>
Beat 2 — Failed answer A. <attempted answer; let it be reasonable>
Beat 3 — Failed answer B. <second attempted answer; also reasonable>
Beat 4 — Pivot (VERBATIM THESIS). <the move that escapes both; thesis verbatim>
Beat 5 — Non-bodily correction. <body of the argument; replacements>
Beat 6 — Stakes + question. <human/political stakes; thesis verbatim; bridge question>
```

### Auto-detect pattern

Scan `## Three-part focus` (or equivalent) for either: (a) presence of `Beat 1`, `Beat 2`, …, `Beat 6` markers (≥6 beats) for debate-format chapters; OR (b) explicit declaration of the crisis / failed-answer / pivot / correction / stakes structure (substring scan for `Crisis`, `Failed answer`, `Pivot`, `Stakes`). Absence of both for a debate-format chapter → flag.

### Auto-fix or flag

**FLAG (P1)**. Authoring decision — the 6 beats must be filled in with chapter-specific content.

### Authority for challenger

`podcast-challenger` Loop **H4** (dramatic-arc structure present for debate-format chapters) — new check added 2026-05-21 (X16). Surface as Category H finding.

---

## R-CADENCE · Short-to-medium sentence rhythm

### Rule

The framing MUST include a cadence directive under Tone constraints: short-to-medium sentences with varied rhythm. Long compound sentences with three or more subordinate clauses are forbidden. The pace is conversation, not lecture.

### Why

NotebookLM defaults to declarative-essay sentence structure when its source is dense prose (classical translations, scholarly essays). The result reads-aloud as a podcast voicing a read-aloud essay. An explicit cadence directive bends the voice model toward conversational sentence lengths.

### Required clause in `00-framing.md`

Under "Tone" or "Tone constraints":

```
Cadence: short-to-medium sentences with varied rhythm. Mix simple
declarative sentences with occasional longer ones. Avoid sentences that
chain three or more subordinate clauses ("which", "that", "where") in
sequence. The pace is conversation, not lecture; the hosts are thinking
out loud, not reading.
```

### Auto-detect

Scan `00-framing.md` Tone section for substring "cadence" or "short-to-medium" or "thinking out loud". Absence → flag.

### Auto-fix

**AUTO-FIX** (insert the canonical clause) when Tone section exists. **FLAG (P2)** when Tone section itself is missing.

### Authority for challenger

`podcast-challenger` Loop **R3** (cadence clause present) — new check added 2026-05-18.

---

## R-NOFORMAL · No formal-essay transitions

### Rule

The customize prompt's `## Do not` block MUST include the banned formal-essay transition phrases. The hosts speak as friends thinking together, not as a writer reading section dividers aloud.

### Why

NotebookLM defaults to essay-structural transitions when its source is dense exposition. "Firstly", "Secondly", "Moving on", "In conclusion", and "Furthermore" are the tells. Banning the specific tokens is enforceable; banning "formal language" generically is not (same lesson as R-NOMODERNIZE).

### Required clause inside the `## Do not` block

```
Do NOT use formal-essay transitions. Do not say: "Firstly", "Secondly",
"Thirdly", "Furthermore", "Moreover", "In conclusion", "To summarize",
"To begin with", "To start", "Moving on to", "Let us turn to", "Lastly",
"Last but not least", "All in all". These belong to written essays, not
to two people thinking out loud. Transitions in conversation happen via
pacing (a beat, a question, a re-anchor) — not via section dividers.
```

### Auto-detect

Scan `00-framing.md`'s `## Do not` section for the canonical formal-transition deny phrases. Absence → flag.

### Auto-fix

**AUTO-FIX** (insert the clause) when the `## Do not` section exists. **FLAG (P1)** when it does not (the M1 + M2 fix will create it, then R-NOFORMAL augments).

### Authority for challenger

`podcast-challenger` Loop **R4** (formal-transition deny present) — new check added 2026-05-18. Loop M also scans the most recent transcript for occurrences of the banned phrases.

---

## R-PRONUNCIATION-IMPERATIVE · Pronunciation directives in imperative voice

### Rule

The customize prompt's `## Pronunciation` block MUST be a series of **imperative directives** addressed to NotebookLM, not a passive list of terms with phonetic respellings beside them. Each line follows the form:

```
Pronounce "<term>" as "<phonetic>". Say it as one fluent word. Do not spell it. Do not pause.
```

The block MUST end with:

```
Do not read this guidance aloud. The phonetics above are for the voice model only.
```

This rule supersedes R-PHONETICHOOKS' passive-list pattern. The change pairs with chapter-side R-PHONETICS-OUT: phonetics no longer live inline in the chapter at all; they live here, in imperative form, where NotebookLM's voice model uses them silently.

### Why

Empirical evidence (transcript audit, May 2026 — the failure modes are detailed in [`worked-examples.md` §5](worked-examples.md#5--empirical-evidence-motivating-r-phonetics-out-r-nomodernize-r-nosurprise)): a passive pronunciation list — `*<Term>*: <pho-net-ic>` — produces no behavior change in NotebookLM's voice model. The hosts mangle the term across episodes. An imperative directive (`Pronounce "<Term>" as "<pho-net-ic>". Say it as one fluent word.`) is acted on. The `Do not read this guidance aloud` tail prevents the hosts from announcing the pronunciation list.

The canonical phonetic spelling for each term MUST still come from `content/_shared/arabic/03-arabic-english-manifest.md`; drift between this block and the manifest is a P0 failure. Per-book overrides live in `BOOK_DIR/_system/pronunciation.md`.

### Required block in `00-framing.md`

```
## Pronunciation

Pronounce "<Term 1>" as "<pho-net-ic 1>". Say it as <one fluent word | N fluent words>.
Pronounce "<Term 2>" as "<pho-net-ic 2>". Say it as one fluent word. Do not spell it.
[... one imperative line per term that appears in the chapter...]

Do not read this guidance aloud. The phonetics above are for the voice model only.
```

A worked block from one book (filled with real terms) lives at [`worked-examples.md` §4](worked-examples.md#4--pronunciation-block-for-the-customize-prompt).

### Auto-detect

Scan `## Pronunciation` block: every non-blank line MUST start with `Pronounce "` or `Do not`. Lines matching the legacy passive-list pattern (`* term: phonetic` or `term — phonetic`) are violations.

### Auto-fix

**AUTO-FIX** (deterministic): convert each legacy passive-list line `*Term*: Pho-net-ic` to `Pronounce "Term" as "Pho-net-ic". Say it as one fluent word.` Append the `Do not read this guidance aloud.` tail if missing.

### Authority for challenger

`podcast-challenger` Loop **C5** (imperative-form audit) — new check added 2026-05-17. Drift from `03-arabic-english-manifest.md` remains under Loop **C1** + **C2**.

---

## R-NOMODERNIZE · No named modern platforms or products; analogies welcome

### Rule

The customize prompt MUST forbid the hosts from naming specific modern platforms, products, or internet-culture artifacts (the DENY list below). **Generic modern-life practical analogies are explicitly ALLOWED and encouraged** when they illuminate a classical concept the listener might otherwise struggle with. The distinction is *named-modern-artifact* (banned) vs *modern-life situation* (allowed).

Banned: `Twitter`, `algorithm`, `doomscrolling`, `content creator`.
Allowed: "imagine a parent worrying about their child's choices", "the way someone might rehearse what they want to say before a difficult conversation", "the experience of comparing yourself to a coworker who got promoted".

The angle in `faithful_exposition` mode is to keep the conversation in the source's register; the listener can still receive a contemporary practical analogy as long as it doesn't name a modern platform or internet artifact.

### Required `## Do not` block in `00-framing.md`

```
## Do not (forbidden vocabulary and framings)

Do NOT name modern platforms, products, or internet-culture artifacts. The
hosts do not mention any of: Twitter, X, social media, algorithm, content
creator, internet troll, reply guy, YouTube comment, TikTok, Instagram,
podcast, livestream, app, screen time, notification, attention economy,
21st century, "in our modern world", quote-tweet, hashtag, follower count,
like, share, repost, doomscroll, hot take, cognitive behavioral therapy,
productivity framework, life hack, self-help, wellness, mindfulness app,
dopamine hit, deep dive.

DO use modern-life practical analogies when they help the listener
recognize a classical concept in lived experience — a parent worrying
about a child, an employee resenting a coworker, the experience of
preparing for a difficult conversation, learning a craft over years.
These analogies illuminate the source without dragging in named modern
platforms or internet artifacts. Each analogy lands in a single beat and
returns to the source; it does not replace the source.
```

### Why

Empirical evidence (transcript audit, May 2026 — full inventory in [`worked-examples.md` §5](worked-examples.md#5--empirical-evidence-motivating-r-phonetics-out-r-nomodernize-r-nosurprise)): the failure mode is NotebookLM naming specific modern platforms (`internet troll`, `reply guy`, `algorithmic envy machines`) which break the angle. **The failure mode is *naming the artifact*, not *using a contemporary parallel***. The earlier formulation of this rule over-restricted: it banned all modern analogies, which suppressed pedagogically valuable comparisons. The corrected formulation bans the named-artifact pollution while permitting the practical analogies that help a 2026 listener recognize an 1100 CE concept.

### Auto-detect

Two scans:
- **Negative**: `## Do not` section contains at least the canonical platform-deny list. Absence → flag.
- **Positive**: framing includes the "DO use modern-life practical analogies" paragraph (or equivalent permission). Absence → flag (P2 advisory — the framing is workable without it, but the angle is needlessly tight).

### Auto-fix

**AUTO-FIX** (insert the canonical block including both Do-not and Do paragraphs) when the framing has no `## Do not` section. **FLAG (P1)** when the negative block exists but is missing required DENY entries. **AUTO-FIX (P2)** to insert the positive paragraph when the negative block exists but the permission is absent.

### Authority for challenger

`podcast-challenger` Loop **M** (modernization audit) — updated 2026-05-18 to honor the named-artifact-vs-practical-analogy distinction. Loop M ALSO scans the most recent transcript (if available under `BOOK_DIR/transcripts/EP##-<slug>.transcript.txt`) for injected named artifacts.

---

## R-ANALOGY-CAP · Enumerate 3–5 governing analogies upfront; no mid-episode invention

### Rule

The framing's `## Tone constraints` MUST enumerate **exactly 3–5 GOVERNING ANALOGIES** for the episode, declared upfront, each tied to a specific beat. Hosts MAY elaborate on these; hosts MAY NOT introduce new analogies mid-episode. Each governing analogy is named, tied to a beat, and bounded ("Use for X. Do not extend beyond Beat N.").

**Soft target**: 5 for dense philosophical chapters. **Hard minimum**: 3. **Hard maximum**: 5 (above 5 produces analogy-fatigue regardless of beat-binding).

Forbidden analogies (i.e. the v1 catalog from KaR Ch07) MUST be listed by name in the `## Do not` block when the framing is iterating off a prior baseline that over-used analogies — this prevents the model from reaching for the same fatigue-pattern analogies.

### Why

Empirical (2026-05-21 audit of *Kitab al-Riyad* Ch07 v1 transcript): NotebookLM produced **14+ distinct analogies** across a 30-minute episode (solar panels, cathedral, ladder/mountain/valley, fulcrum, pie chart, sphere, political map/border, wax-seal, plus 6 others). Each analogy individually was reasonable; cumulatively the listener experienced fatigue and lost track of which analogy mapped to which beat. The fix is structural: enumerate 3–5 analogies upfront, bind each to a beat, and forbid mid-episode invention. The v2 lab framing uses 3 (footprint, messenger, light-on-glass-and-stone), each elaborated deeply.

### Required clause in `00-framing.md`

Under `## Tone constraints`:

```
THREE-to-FIVE governing analogies. No mid-episode invention.

This episode uses EXACTLY <N> governing analogies, declared upfront. Each
is tied to a specific beat. Hosts may elaborate; hosts MAY NOT introduce
new analogies mid-episode.

 - Analogy 1 — <name> (Beat <n>). <description>. Use for <X>. Do not extend
   beyond Beat <n>.
 - Analogy 2 — <name> (Beat <n>). <description>. Use for <X>.
 - Analogy 3 — <name> (Beat <n>). <description>. Use for <X>.
 [- Analogy 4 — ...]
 [- Analogy 5 — ...]

Forbidden mid-episode analogies (the v1 list): <enumerate any forbidden
analogies that the prior baseline over-used>. If a host feels the urge for
a fresh analogy, recur to one of the <N> above, or return to the source's
own image.
```

### Auto-detect pattern

Scan `## Tone constraints` for a list of analogies — list items (`-`, `*`, or `Analogy N —`) within the section. Count the analogies. Validate: count is between 3 and 5 inclusive. Absence of any enumeration → flag. Count outside [3, 5] → flag.

### Auto-fix or flag

**FLAG (P1)**. Authoring decision — selecting and binding analogies to beats is editorial.

### Authority for challenger

`podcast-challenger` Loop **L1** (analogy-cap enumeration present AND count ∈ [3, 5]) — new check added 2026-05-21 (X16). Surface as Category L finding. Transcript-side scan: Loop M extends to count distinct analogies that appear in the audio; >5 fires P1.

---

## R-NOSURPRISE · No surprise-noise loops

### Rule

The customize prompt MUST forbid the surprise-reaction vocabulary that NotebookLM's voice model defaults to. The DENY list below is minimum; extend per book.

### Required clause inside the `## Do not` block

```
Do NOT perform surprise. Do not say: "wow", "that's so interesting", "it's
chilling", "it's devastating", "it's terrifying", "it's profound", "it's
fascinating", "it's amazing", "oh my god", "right?", "exactly", "no
way". Do not gasp. Do not repeat the previous host's last word as a
single-word reaction. Trust the listener to register weight without being
told.
```

### Required POSITIVE companion (added 2026-05-18 via the learning pipeline)

The DENY list alone empirically still leaves a vacuum the model fills with adjacent surprise vocabulary. Every framing MUST also carry a positive directive — placed alongside the DENY clause inside the `## Do not` block — that tells the hosts what to do instead:

```
When something in the source genuinely lands as new, name what is new in
ONE short clause that advances the argument ("the move he just made is
strict", "the citation chain stops there"), then continue. Do not pad
with reaction interjections. The reaction IS the next substantive sentence.
```

Promoted from `_learning/proposals/2026-05-18-tx-surprise-density-ayyuhal-walad-ep02-hatim-eight-benefits.md` on 2026-05-18 after 5× firings of distinct surprise vocabulary (`wow / Wow / right? / exactly / Exactly`) in a single transcript despite the DENY clause being present in the framing. The DENY list is necessary but not sufficient; the positive directive closes the gap.

### Why

Empirical evidence: across the 5 transcripts, surprise-noise loops appeared >40 times. "It's chilling", "It's devastating", "It's terrifying" appeared together in one episode 6 times. Tone constraint prose ("no wow loops") is too soft; a DENY list of specific phrases is enforceable. The positive companion (above) further redirects the host's prosodic energy into argument-advancing speech rather than affect.

### Auto-detect

Scan `00-framing.md`'s `## Do not` section for the canonical surprise-deny phrases AND the positive companion paragraph (key phrase: "name what is new in ONE short clause"). Absence of either → flag.

### Auto-fix

**AUTO-FIX** (insert the DENY clause AND the positive companion paragraph together) when the `## Do not` section exists. **FLAG (P1)** when it does not.

### Authority for challenger

`podcast-challenger` Loop **M** (shared with modernization audit; Loop M is the empirical-transcript loop). Loop also scans the transcript file for surprise-noise frequency.

---

## R-NO-READ-PROMPT · Customize prompt is not read aloud

### Rule

The customize prompt MUST end with a single explicit line directing the hosts NOT to read its contents aloud:

```
Do not read this prompt aloud. The instructions above shape the conversation but are never spoken.
```

### Why

NotebookLM has been observed reading customize-prompt directives as if they were content. The line above prevents the failure mode without changing the prompt's structure.

### Auto-detect

Scan the framing for the literal sentence (or close variant). Absence → flag.

### Auto-fix

**AUTO-FIX** (insert the sentence at the end of the framing, after the Pronunciation block).

### Authority for challenger

`podcast-challenger` Loop **F7** (final-line directive) — new check added 2026-05-17.

---

## R-PHONETICHOOKS · DEPRECATED in favor of R-PRONUNCIATION-IMPERATIVE

### Rule

DEPRECATED 2026-05-17. The passive `*term*: phonetic` list pattern was empirically shown not to change NotebookLM voice-model behavior. See R-PRONUNCIATION-IMPERATIVE above.

### Migration

Existing framings carrying a passive Pronunciation list MUST be auto-converted to the imperative form. The deterministic conversion rule lives in the auto-fix section of R-PRONUNCIATION-IMPERATIVE.

---

## R-SUMMARYTAIL · Closing landing, not a recap

### Rule

The customize prompt MUST direct hosts to close on the unresolved tension, an open question, or a single sharp line — NEVER a summary of what was just discussed. The listener does not need to be told what they just heard.

### Why

Recap-style closings ("so today we covered…") are the most listener-hostile move NotebookLM makes by default. The framing must forbid it.

### Required clause in `00-framing.md`

Under "Three-part focus" → "Landing":

```
Close on the unresolved tension, a question, or a single sharp line. Do
not recap what was discussed. Do not say "so today we covered…". The
listener already heard it.
```

### Auto-detect pattern

Scan `00-framing.md` for a "Landing" subsection containing "tension", "question", or "no recap" language.

### Auto-fix or flag

**AUTO-FIX** when a Landing subsection exists (insert clause). **FLAG (P1)** otherwise.

### Authority for challenger

`podcast-challenger` Loop **H3** (closing-landing clause present).

---

## R-NOMETA · No meta-prose about the file itself

### Rule

The customize prompt MUST NOT describe itself ("this customize prompt directs…", "in the following framing…", "the goal of this prompt is…"). Address NotebookLM directly. Speak in the imperative.

### Why

Meta-prose in the customize prompt confuses NotebookLM's parser and can cause the hosts to read instructions aloud as if they were source content. This is the highest-severity NotebookLM failure mode.

### Auto-detect pattern

Substring scan + regex for `META_PROSE_TELLS` and `META_PROSE_REGEX_TELLS` already defined in `scripts/podcast/build_episode_txt.py`.

### Auto-fix or flag

**FLAG (P0)** always. `build_episode_txt.py` refuses to emit the episode txt if any tell fires; the agent escalates to author.

### Authority for challenger

`podcast-challenger` Loop **B1** (existing, structural counterpart in the build script).

---

## Maintenance protocol

When adding a new rule:

1. Append a new `## R-<NAME>` section to this file following the same structure (Rule / Why / Required clause / Auto-detect / Auto-fix or flag / Authority).
2. Add the matching check to `.github/agents/podcast-challenger.agent.md` in the appropriate Loop section.
3. Update `skills-staging/podcast/SKILL.md` session-start protocol if the rule applies during authoring (Phase 3).
4. Add a one-line entry to the revision log below.

When deprecating a rule:

1. Mark it `## R-<NAME> · DEPRECATED` and explain why.
2. Remove the matching check from the agent.
3. Note in the revision log.

---

## Revision log

- 2026-05-21 — **Five new structural rules promoted from `scripts/podcast/_authoring.py` prompt strings (X14, X15, X16 framework guards).** Added R-NAMEDISCIPLINE (Arabic figure names once on first mention with English appositive; thereafter rotate among 3–4 English aliases per `BOOK_DIR/_system/name-aliases.yml` — closes the gap in R-NAMEALIAS where the Arabic surname was allowed as the alias). Added R-DRAMATIC-ARC (debate-format chapters use a 6-beat arc: crisis → failed-A → failed-B → pivot → non-bodily correction → stakes+question; topic-listing collapses dialectical tension). Added R-CHALLENGER-FRICTION (Color host MUST push back ≥3 times per episode using a fixed catalog of doubt patterns; named agreeable openers forbidden as first sentences). Added R-ANALOGY-CAP (3–5 governing analogies enumerated upfront, bound to beats; no mid-episode invention — corrects the v1 KaR Ch07 baseline's 14+ analogy fatigue). Added R-RECURRING-THESIS (chapter's settled formula from `contract.anchor_passages` appears VERBATIM at three anchor points: open, pivot, close — fixes the once-and-never-again pattern observed in KaR Ch07 v1). Each rule carries its empirical motivation from the 2026-05-21 audit of *Kitab al-Riyad* Ch07 v1 transcript. Matching validator functions added to `scripts/podcast/build_episode_txt.py` (P1 flags, not hard fails — challenger pass escalates). Coordinated with `notebooklm-source-chapter-rules.md` R-NO-MANUSCRIPT-META (chapter-side companion guarding Phase 0e enrichment against emitting manuscript-history meta-prose).
- 2026-05-18 — **Conversation choreography rules + R-NOMODERNIZE softening.** Added R-SURPRISE-MOVE (separate-prep illusion via planted handoffs — at least one moment per episode), R-RESET (single-sentence reset between major beat-groups in spines >5 beats), R-CADENCE (short-to-medium sentence rhythm under Tone constraints), R-NOFORMAL (DENY block extension for formal-essay transitions: `Firstly`, `In conclusion`, `Moving on to`, etc.). Softened R-NOMODERNIZE: the failure mode is *naming the modern artifact* (Twitter, algorithm, etc.), not *using a contemporary parallel* — modern-life practical analogies are now explicitly permitted when they help the listener recognize a classical concept in lived experience. The DENY list of named platforms remains intact; the rule adds a positive permission paragraph. New checks in `podcast-challenger` Category R (R1–R4). Driven by a quality-baseline review showing the prior R-NOMODERNIZE formulation over-restricted analogies and suppressed pedagogical comparisons, and that the framing lacked explicit signals for the separate-prep illusion, reset moments, and cadence/transition discipline.
- 2026-05-17 (later) — **Empirical pivot from passive lists to imperative directives.** Added R-PRONUNCIATION-IMPERATIVE (replaces passive `*term*: phonetic` pattern that empirically did not change NotebookLM behavior — see audit notes in [`worked-examples.md` §5](worked-examples.md#5--empirical-evidence-motivating-r-phonetics-out-r-nomodernize-r-nosurprise)). Added R-NOMODERNIZE (DENY list including Twitter, X, social media, algorithm, content creator, etc. — soft "do not modernize" prose was being ignored). Added R-NOSURPRISE (DENY list for "wow", "it's chilling", "it's devastating", "right?", "exactly", etc. — surprise loops appeared >40 times across the audited episodes). Added R-NO-READ-PROMPT (single-line guard against the hosts reading the prompt aloud). Deprecated R-PHONETICHOOKS.
- 2026-05-17 — Seeded with R-WELCOME, R-NOREPEAT, R-NOBACKGROUND, R-NAMEALIAS, R-NOINTERRUPT, R-PHONETICHOOKS, R-SUMMARYTAIL, R-NOMETA. Externalized from scattered references across SKILL.md and notebooklm-best-practices.md.
