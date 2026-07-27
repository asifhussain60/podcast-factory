# RCA practice — root-cause analysis for podcast-factory

Standing practice as of 2026-07-22 (Asif's directive: "Begin doing RCAs so we
can stop repeating the same mistakes").

## When an RCA is mandatory

Write one whenever ANY of these is true:

1. **Paid work was discarded or repeated** — a model pass re-run because its
   output was lost, overwritten, or wrong (the trigger for RCA-001).
2. **A defect crossed a quality gate** — challenger / publication review /
   render checks / smoke passed while the deliverable was wrong.
3. **A human caught what the pipeline should have** — reader-detected defects
   are detection failures by definition.
4. **The same class of mistake appears a second time** — repetition converts
   an annoyance into a mandatory RCA.

Small one-off bugs fixed at root in the same session do NOT need an RCA — the
commit message carries the story.

## Format

Use [`_template.md`](_template.md) — the Google SRE postmortem structure
(summary / impact / root causes / trigger / resolution / detection / action
items / lessons / timeline), sourced from
[dastergon/postmortem-templates](https://github.com/dastergon/postmortem-templates)
(cloned 2026-07-22; pick a different template from that collection if an
incident's shape demands it).

Analysis discipline, always:

- **Blameless.** Causes are design, process, detection, and change-management
  — never a person.
- **5 Whys** to reach root causes; stop at causes the project can actually
  change.
- **Root cause ≠ trigger.** The trigger is the event; root causes are why the
  system let the event do damage.
- **Every action item lands somewhere** — a fix in this session, a spawned
  task chip, or an explicit "accepted risk" line. No orphan recommendations.
- **Timeline in EST**, reconstructed from git/ledgers, not memory.

## Naming

`YYYY-MM-DD-<short-slug>.md`, dated by the day the RCA is written.

## Index

| ID | Date | Title | Status |
|---|---|---|---|
| RCA-001 | 2026-07-22 | [Composer snapshots froze un-articulated prose across 8 of 9 chapters](2026-07-22-composer-snapshots-froze-unarticulated-prose.md) | Resolved — SHIP-READY; AI-2/6/7 open |
| RCA-002 | 2026-07-27 | [Composer autosave wrote four corruptions into a publication-bound book.md](2026-07-27-composer-autosave-wrote-corruption-into-book-md.md) | Resolved — tree restored; AI-1…AI-5 open |
