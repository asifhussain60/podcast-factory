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

Repeating "Imam Abu Hamid Muhammad al-Ghazali" across 30 references in a 15-minute episode is fatiguing to the listener and consumes airtime that should carry argument. The alias is how human podcasts handle it; NotebookLM does not do it by default.

### Required clause in `00-framing.md`

Under "Pronunciation hooks":

```
Name discipline. Use each long name in full ONCE on first occurrence, then
use the short alias for every subsequent reference:
  - Imam Abu Hamid Muhammad al-Ghazali  →  Ghazali
  - Hatim bin Ism al-Asamm              →  Haatim
  - Shaqiq al-Balkhi                    →  Shaqeeq
  - Sufyan al-Thawri                    →  Sufyan
  - <add any long name in this episode>
```

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

## R-PHONETICHOOKS · Pronunciation hooks reference the shared manifest

### Rule

The customize prompt's "Pronunciation hooks" section MUST cite specific terms from `content/_shared/arabic/03-arabic-english-manifest.md` for every Arabic term that appears in the chapter, using the canonical phonetic spelling exactly. No ad-hoc respellings; no variants across episodes.

### Why

The shared manifest exists so the same term sounds the same across the entire series. The framing's pronunciation hooks are how the manifest reaches NotebookLM. Drift here is drift everywhere.

### Auto-detect pattern

Cross-reference every Arabic term flagged in `02-key-passages.md` against the manifest. Any term in the chapter that does not appear with its canonical phonetic in the framing's Pronunciation hooks → flag.

### Auto-fix or flag

**AUTO-FIX** when the term is in the manifest (insert the canonical phonetic). **FLAG (P0)** when the chapter contains a phonetic spelling that disagrees with the manifest (drift — must be resolved by edit).

### Authority for challenger

`podcast-challenger` Loop **C1** (existing) + **C2** (existing) — already enforced.

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

- 2026-05-17 — Seeded with R-WELCOME, R-NOREPEAT, R-NOBACKGROUND, R-NAMEALIAS, R-NOINTERRUPT, R-PHONETICHOOKS, R-SUMMARYTAIL, R-NOMETA. Externalized from scattered references across SKILL.md and notebooklm-best-practices.md.
