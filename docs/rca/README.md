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
- **"Verified locally" is not evidence for a failure that only happens
  elsewhere.** If a defect manifests only on another platform, another runtime
  version, or only in CI, a local pass distinguishes nothing — state plainly that
  the fix is unverified until it runs where the failure lives. Added after
  RCA-009, where a fix verified with `npm ci` on macOS held for one day because
  the failure was reachable only on Linux.

## Naming

`YYYY-MM-DD-<short-slug>.md`, dated by the day the RCA is written.

## Index

| ID | Date | Title | Status |
|---|---|---|---|
| RCA-001 | 2026-07-22 | [Composer snapshots froze un-articulated prose across 8 of 9 chapters](2026-07-22-composer-snapshots-froze-unarticulated-prose.md) | Resolved — SHIP-READY; AI-2/6/7 open |
| RCA-002 | 2026-07-27 | [Composer autosave wrote four corruptions into a publication-bound book.md](2026-07-27-composer-autosave-wrote-corruption-into-book-md.md) | Resolved — tree restored; AI-1…AI-5 open |
| RCA-003 | 2026-07-28 | [Automated QA session deleted two Companion notes from a live book](2026-07-28-automation-deleted-companion-notes.md) | Resolved — data restored, delete path confirmation-guarded |
| RCA-004 | 2026-07-30 | [A full paid vowelling run was refused at the last gate and discarded](2026-07-30-source-vowelling-refused-after-a-full-paid-run.md) | Resolved — both causes fixture-pinned; AI-3 open |
| RCA-005 | 2026-07-31 | [An editorial aside printed twice, once in the narrator's own voice](2026-07-31-an-editorial-aside-printed-twice-in-the-reading-edition.md) | Resolved — fence matching now form-tolerant; AI-2/3/4 open |
| RCA-006 | 2026-07-31 | [A typographic premise no one could check spread through four stylesheets](2026-07-31-an-unverified-typographic-premise-propagated-by-citation.md) | Resolved — descriptor removed, measurement recorded; AI-2/3 open |
| RCA-007 | 2026-08-01 | [The hosts were handed translations instead of phonetics](2026-08-01-the-hosts-were-handed-translations-instead-of-phonetics.md) | Resolved — block compiled from the ladder, library re-keyed; AI-3/4 open |
| RCA-008 | 2026-08-01 | [A faithful opening was reverted as if the model invented it](2026-08-01-a-faithful-opening-was-reverted-as-if-invented.md) | Resolved — gate made differential, chapter re-articulated; AI-6 open |
| RCA-009 | 2026-08-01 | [The site's CI gates were dead for five days](2026-08-01-the-site-gates-were-dead-for-five-days.md) | Resolved — all three jobs green, first success since 2026-07-27; AI-1…AI-8 all closed |
