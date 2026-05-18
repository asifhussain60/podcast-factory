# Debate framing — two-host pedagogical disputation

The `/podcast` skill supports two episode formats. **Deep Dive** (the default) treats the source faithfully and has the two hosts walk through it together. **Debate** has each host adopt a distinct role + position and argue from it, using the source's teachings as argument material. The goal is the same: bring out the teaching. The shape is different.

This document defines the debate format. The deep-dive format lives in `two-host-framing.md`.

---

## When to choose Debate over Deep Dive

Choose Debate when:

- The source contains a proposition that admits more than one defensible reading.
- The teaching is sharpened by being stress-tested rather than merely exposited.
- The historical tradition itself contains opposing positions on the same teaching (Ash'ari vs Mu'tazila, jurists vs Sufis, Sunni vs Shia readings of a shared text).
- The listener will retain the teaching better as the outcome of a disputation than as the conclusion of an exposition.

Choose Deep Dive when:

- The teaching is structural and admits no opposing position (e.g. a list of distilled benefits or a sequence of practices is not a debate).
- The source is narrative or memoir.
- The author's voice is the spine and adding a second position would distort the source.
- The chapter is the first introduction to the source for the listener.

If in doubt, default to Deep Dive. Debate is harder to do well and demands more rigor in the framing.

---

## Vocabulary

- **Proposition** — the single sentence under debate. Phrased as a claim, not a question. (For a concrete instance, see [`worked-examples.md` §6](worked-examples.md#6--debate-framing-worked-example-ep04-four-cautions).)
- **Position** — what each host argues. Phrased as a positive claim, not "the opposite of the other position." Each host's position must be defensible from the source, even if the source ultimately favors one side.
- **Role** — the historical or intellectual perspective each host adopts. Not a personality. The role tells the listener *whose voice is in the room*. Examples: "the orthodox jurist", "the historically-grounded scholar", "the lay practitioner", "the modernist reformer", "the Sufi mystic", "the philosophical rationalist".
- **Source moves** — specific moves each host has available from the source material (quotes, passages, passages-elsewhere-in-the-book, traditions that support the position). Pre-named in the framing so the hosts know their armory.
- **Resolution** — what the debate lands on. One of: `synthesis` (the two positions resolve into a richer reading), `open` (the listener leaves with both positions held in tension), `host_a_concedes` / `host_b_concedes` (one position is shown to be stronger by the source itself), `historical_division` (the debate is named as one the tradition itself never closed).

---

## Default role pairs

Pair the roles against the proposition. A few combinations that have worked in classical scholarly tradition and that the framing can name directly:

### Orthodox jurist + historically-grounded scholar
The first reads the source's prohibitions as categorical. The second reads them in their historical context and notes where the author himself, or the tradition, qualifies them. Best for legal-ethical material (the four cautions, the obligations of the seeker, the conditions for taking a guide).

### Theologian + practitioner
The first argues from the systematic doctrine. The second argues from what actually happens in a lived spiritual life. Best for material on prayer, contemplation, and the inner work (method, supplication, the disciplines of the heart).

### Inside the tradition + outside the tradition
The first speaks as someone for whom the source is normative. The second speaks as a sympathetic reader from outside who finds the teaching valuable but on different grounds. Best for material that crosses traditions (the universality claim in EP02, the four-scripture claim, the architecture of self-knowledge).

### Two perspectives within one tradition (sectarian-internal)
Both hosts inside the same broad tradition but holding different readings — e.g., Sunni jurist + Shia jurist on the qualifications of a teacher; Ash'ari + Maturidi on the role of reason; Sufi-from-the-orthodox-side + Sufi-from-the-philosophical-side on the inner stations.

### Author's defender + author's critic
The first argues the author's case in his strongest form. The second names where the author's position is open to objection (from inside or outside the tradition) and presses the objection. The author's defender then must answer. Best for sharpening a single teaching to its hardest form.

Custom pairs are allowed; declare them explicitly in the framing.

---

## Rules of debate (these go INTO the framing verbatim)

1. **No strawman.** Each host argues the strongest form of their position. If the position has a weakness, the OTHER host names it, not the host holding it.
2. **Source-grounded only.** Every move references the source text, a passage from the same author's larger corpus, or an established tradition the position is anchored in. No appeals to "modern common sense" or "what we know today".
3. **Defended positions stay defended through the episode.** A host may concede a sub-point but does not abandon their named position mid-episode unless the resolution is `host_X_concedes`.
4. **Disagreement is the work, not the failure mode.** The acknowledgment-grammar bans that apply in Deep Dive (no "Exactly", no "Yeah") are SOFTENED in Debate: a host may concede a sub-point with "That's a fair point on X, but..." — the concession must be qualified, followed by a return to the host's main position.
5. **One position at a time.** Each beat surfaces one part of the argument. Hosts do not jump topics. The debate moves through the source's structure.
6. **The proposition is named at the opening.** The opening introduces the proposition, names both positions, and tells the listener that the conversation will work through the disagreement. The proposition is named again at the close, with the resolution.
7. **No verdict from the host.** Neither host announces a winner at the close. The framing's `resolution` field determines what the closing sounds like (synthesis statement, open question, named concession, named historical-division).
8. **The source author's voice is third in the room.** When the author is quoted, the quote is treated as authoritative for that moment, regardless of which host invokes it. The host who invokes the quote does not "win" the moment — both hosts now have a new constraint.

---

## Framing structure (debate format)

Use this scaffold for `00-framing.md` when `episode_format: debate`. The required sections, in order:

1. **Critical pronunciation + citation rules** (same as deep dive; mode-agnostic)
2. **Proposition** — one sentence, phrased as a claim.
3. **Roles + positions** — host_a + host_b each get a role + a position statement + a list of source moves available to them.
4. **Rules of debate** — drop in the rules above verbatim. Optionally adjust rule 4 (concession grammar) per episode.
5. **Audience** — same as deep dive.
6. **Tone constraints** — debate-specific tone (e.g., "firm but not adversarial", "no contempt across positions", "no sarcasm").
7. **Resolution** — name what the close should sound like. Synthesis / open / host_X_concedes / historical_division.
8. **Three-beat shape** — opening (proposition named) → middle (the disagreement worked through) → close (resolution, no host verdict).
9. **Pronunciation** — same as deep dive.
10. **Do not** — same anti-modernize + anti-surprise rules. Plus debate-specific: no ad hominem, no characterizing the other position as foolish, no caricature.
11. **Upload checklist** — same as deep dive.

Sections that are PRESENT in deep dive but absent or modified in debate:
- **Angle** — replaced by `Proposition + Positions`. Debate is its own angle.
- **Central tensions to reach** — replaced by `Source moves`. The tension IS the proposition; the moves are how the hosts work it out.
- **Host dynamic** — replaced by `Roles + positions`. The roles ARE the dynamic.

---

## Worked example

A concrete debate-frame instance (proposition, two host positions with source moves, `historical_division` resolution) drawn from one book lives at [`worked-examples.md` §6](worked-examples.md#6--debate-framing-worked-example-ep04-four-cautions). It is illustrative, not prescriptive — each debate-format episode is bespoke; the framing carries the proposition and positions specific to that chapter.

---

## NotebookLM steering for debate format

NotebookLM's two-host Audio Overview engine has no "debate mode" toggle. The framing carries the entire mode signal. Words that reliably bend the engine toward debate behavior:

- "This episode is structured as a debate, not a deep dive."
- "Host A argues that [position]. Host B argues that [position]. Both positions are defended through the conversation."
- "Disagreement is the spine of this episode. The hosts do not arrive at a single view."
- "Each host stays in their position. They do not switch sides. They concede sub-points only with qualification."
- "The episode does not announce a winner. It [synthesizes / leaves open / names the historical division]."

Avoid steering language that NotebookLM interprets as adversarial entertainment:

- "Battle of ideas", "showdown", "fight" — produces theatrical opposition rather than scholarly debate.
- "Who is right?" as a hook — produces a verdict-driven episode rather than a teaching-driven one.
- "Two views go head-to-head" — same effect as above.

Use the language of disputation, not contest. *Munazara*, not boxing.

---

## What this format does NOT do

- It does not produce a winner-loser outcome unless the contract's `resolution` explicitly says one host concedes.
- It does not present positions as ideological camps. The roles are anchored in the source and its tradition, not in modern political identities.
- It does not require the hosts to fabricate opposing views where the source admits only one. If a chapter has no real proposition under debate, choose Deep Dive instead.
- It does not relax the anti-modernization, anti-surprise, anti-deep-dive-stock-phrase rules. Those still apply.
