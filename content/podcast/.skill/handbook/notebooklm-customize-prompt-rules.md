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
  - <Long full name #1>  →  <short alias #1>
  - <Long full name #2>  →  <short alias #2>
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
[... one imperative line per term that appears in the chapter ...]

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

`podcast-challenger` Loop **M** (modernization audit) — updated 2026-05-18 to honor the named-artifact-vs-practical-analogy distinction. Loop M ALSO scans the most recent transcript (if available under `BOOK_DIR/turboscribe/EP##-<slug>.transcript.txt`) for injected named artifacts.

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

- 2026-05-18 — **Conversation choreography rules + R-NOMODERNIZE softening.** Added R-SURPRISE-MOVE (separate-prep illusion via planted handoffs — at least one moment per episode), R-RESET (single-sentence reset between major beat-groups in spines >5 beats), R-CADENCE (short-to-medium sentence rhythm under Tone constraints), R-NOFORMAL (DENY block extension for formal-essay transitions: `Firstly`, `In conclusion`, `Moving on to`, etc.). Softened R-NOMODERNIZE: the failure mode is *naming the modern artifact* (Twitter, algorithm, etc.), not *using a contemporary parallel* — modern-life practical analogies are now explicitly permitted when they help the listener recognize a classical concept in lived experience. The DENY list of named platforms remains intact; the rule adds a positive permission paragraph. New checks in `podcast-challenger` Category R (R1–R4). Driven by a quality-baseline review showing the prior R-NOMODERNIZE formulation over-restricted analogies and suppressed pedagogical comparisons, and that the framing lacked explicit signals for the separate-prep illusion, reset moments, and cadence/transition discipline.
- 2026-05-17 (later) — **Empirical pivot from passive lists to imperative directives.** Added R-PRONUNCIATION-IMPERATIVE (replaces passive `*term*: phonetic` pattern that empirically did not change NotebookLM behavior — see audit notes in [`worked-examples.md` §5](worked-examples.md#5--empirical-evidence-motivating-r-phonetics-out-r-nomodernize-r-nosurprise)). Added R-NOMODERNIZE (DENY list including Twitter, X, social media, algorithm, content creator, etc. — soft "do not modernize" prose was being ignored). Added R-NOSURPRISE (DENY list for "wow", "it's chilling", "it's devastating", "right?", "exactly", etc. — surprise loops appeared >40 times across the audited episodes). Added R-NO-READ-PROMPT (single-line guard against the hosts reading the prompt aloud). Deprecated R-PHONETICHOOKS.
- 2026-05-17 — Seeded with R-WELCOME, R-NOREPEAT, R-NOBACKGROUND, R-NAMEALIAS, R-NOINTERRUPT, R-PHONETICHOOKS, R-SUMMARYTAIL, R-NOMETA. Externalized from scattered references across SKILL.md and notebooklm-best-practices.md.
