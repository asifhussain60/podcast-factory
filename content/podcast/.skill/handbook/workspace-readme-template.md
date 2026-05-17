# Podcast — <Book Title>

**Source:** *<Book Title>* by <Author>. <Translator / edition note if relevant>. Original at [`_system/source/<book-title>.<ext>`](computer:///Users/asifhussain/PROJECTS/journal/content/podcast/<book-slug>/_system/source/<book-title>.<ext>).

**Slug:** `<book-slug>` · **Episodes:** <count> (1:1 chapter↔episode mapping) · **Architecture:** v3.5 (chapter-as-source, phonetics in customize prompt only).

---

## Folder map

```
<book-slug>/
├── _README.md                                you are here
├── chapters/                                 SOURCE — uploaded to NotebookLM as-is
│   └── ch##-<slug>.txt                       (one per designed chapter)
├── episodes/                                 CUSTOMIZE PROMPT — pasted into NotebookLM Customize box
│   └── EP##-<slug>.txt                       (one per chapter, slug-matched)
├── turboscribe/                              POST-PUBLISH TRANSCRIPTS — slug-aligned, dropped by Asif
│   ├── _README.md                            naming convention + consumers
│   └── EP##-<slug>.transcript.txt            (one per generated episode)
└── _system/                                  book-specific authoring state
    ├── source/
    │   ├── <book-title>.<ext>                verbatim original (audit anchor; never modified)
    │   └── text/                             Phase 0a–0c extraction + normalization + phonetics
    ├── episode-drafts/EP##-<slug>/           per-episode framing + scaffolds (00-framing.md is mandatory)
    ├── scratchpad/                           @@-marker workspace (per episode + series-policies)
    ├── pronunciation.md                      book-level overrides (additive to SHARED_ARABIC)
    ├── enrichment-log.md                     attribution sidecar for Phase 0e enrichment
    ├── editorial-notes.md                    flags + provenance + user decisions
    ├── library-proposals.md                  staged additions to journal libraries
    ├── audit-EP##-<slug>.md                  lexical-audit reports (audit_transcript.py output)
    └── challenger-report.md                  podcast-challenger convergence verdict
```

## Two-file deliverable per episode

| File | Role | NotebookLM action |
|---|---|---|
| `chapters/ch##-<slug>.txt` | enriched chapter — **SOURCE** | Upload as the single source file |
| `episodes/EP##-<slug>.txt` | customize prompt — **CUSTOMIZE PROMPT** | Paste into the *Customize* box |

Strict 1:1 mapping enforced: slug after the prefix is identical on both sides. The chapter IS the source — no transformation by `build_episode_txt.py`.

## Post-publish loop

After NotebookLM renders the audio for an episode, Asif transcribes via **TurboScribe** (https://turboscribe.ai, manual subscription) and drops the result into `turboscribe/` as `EP##-<slug>.transcript.txt`. The lexical audit (`scripts/podcast/audit_transcript.py`) reads from there. The `podcast-challenger` Loop M scans the same transcript for modernization injections, phonetic doublings, and mangled names.

## Status

<Fill in: which episodes are drafted, converged, generated, transcribed, audited. Cross-link to `_system/challenger-report.md` and any per-episode audits.>

## Canonical references

- Skill: [`skills-staging/podcast/SKILL.md`](computer:///Users/asifhussain/PROJECTS/journal/skills-staging/podcast/SKILL.md)
- Challenger: [`.github/agents/podcast-challenger.agent.md`](computer:///Users/asifhussain/PROJECTS/journal/.github/agents/podcast-challenger.agent.md)
- Single-chapter fast path: [`.github/agents/podcast-extract.agent.md`](computer:///Users/asifhussain/PROJECTS/journal/.github/agents/podcast-extract.agent.md)
- Cross-series episode index: [`content/podcast/.skill/registry.md`](computer:///Users/asifhussain/PROJECTS/journal/content/podcast/.skill/registry.md)
- Shared Arabic / phonetics authority: [`content/_shared/arabic/`](computer:///Users/asifhussain/PROJECTS/journal/content/_shared/arabic/)
