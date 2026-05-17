# Podcast — Ayyuhal Walad

**Source:** *Ayyuhal Walad — My Dear Beloved Son (or Daughter)* by Imam Abu Hamid Muhammad Al-Ghazali. English translation by Irfan Hasan from an Urdu rendering of the Arabic original. Original at [`_system/source/Ayyuhal-Walad.pdf`](computer:///Users/asifhussain/PROJECTS/journal/content/podcast/ayyuhal-walad/_system/source/Ayyuhal-Walad.pdf).

**Slug:** `ayyuhal-walad` · **Episodes:** 5 (1:1 chapter↔episode mapping) · **Architecture:** v3.5 (chapter-as-source, phonetics in customize prompt only).

---

## Folder map

```
ayyuhal-walad/
├── _README.md                                you are here
├── chapters/                                 SOURCE — uploaded to NotebookLM as-is
│   ├── ch01-frame-and-first-counsel.txt
│   ├── ch02-hatim-eight-benefits.txt
│   ├── ch03-the-path.txt
│   ├── ch04-four-cautions.txt
│   └── ch05-method-and-closing-prayer.txt
├── episodes/                                 CUSTOMIZE PROMPT — pasted into NotebookLM Customize box
│   ├── EP01-frame-and-first-counsel.txt
│   ├── EP02-hatim-eight-benefits.txt
│   ├── EP03-the-path.txt
│   ├── EP04-four-cautions.txt
│   └── EP05-method-and-closing-prayer.txt
├── turboscribe/                              POST-PUBLISH TRANSCRIPTS — slug-aligned, dropped by Asif
│   ├── _README.md                            naming convention + consumers
│   └── EP##-<slug>.transcript.txt            (one per generated episode)
└── _system/                                  book-specific authoring state
    ├── source/
    │   ├── Ayyuhal-Walad.pdf                 verbatim original (audit anchor)
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

Strict 1:1 mapping enforced: slug after the prefix is identical on both sides. The chapter IS the source — no transformation by `build_episode_txt.py`. The episode txt is emitted from `_system/episode-drafts/EP##-<slug>/00-framing.md`.

## Post-publish loop

After NotebookLM renders the audio for an episode, Asif transcribes via **TurboScribe** (https://turboscribe.ai, manual subscription) and drops the result into `turboscribe/` as `EP##-<slug>.transcript.txt`. The lexical audit (`scripts/podcast/audit_transcript.py`) reads from there and writes `_system/audit-EP##-<slug>.md`. The `podcast-challenger` Loop M scans the same transcript for modernization injections, phonetic doublings, and mangled names.

## Status

Episodes 1–5: chapters authored, episode drafts converged through `podcast-challenger` to SHIP-READY (see [`_system/challenger-report.md`](computer:///Users/asifhussain/PROJECTS/journal/content/podcast/ayyuhal-walad/_system/challenger-report.md)). NotebookLM audio rendered for all 5, transcribed via TurboScribe, lexical audit reports in `_system/`. The v3.5 architectural pivot (phonetics out of chapter, into customize prompt) was driven by the empirical failures these 5 transcripts surfaced — see [`challenger-report.md`](computer:///Users/asifhussain/PROJECTS/journal/content/podcast/ayyuhal-walad/_system/challenger-report.md) M3/M4/N findings.

## Canonical references

- Skill: [`skills-staging/podcast/SKILL.md`](computer:///Users/asifhussain/PROJECTS/journal/skills-staging/podcast/SKILL.md)
- Challenger: [`.github/agents/podcast-challenger.agent.md`](computer:///Users/asifhussain/PROJECTS/journal/.github/agents/podcast-challenger.agent.md)
- Single-chapter fast path: [`.github/agents/podcast-extract.agent.md`](computer:///Users/asifhussain/PROJECTS/journal/.github/agents/podcast-extract.agent.md)
- Cross-series episode index: [`content/podcast/_handbook/registry.md`](computer:///Users/asifhussain/PROJECTS/journal/content/podcast/_handbook/registry.md)
- Shared Arabic / phonetics authority: [`content/_shared/arabic/`](computer:///Users/asifhussain/PROJECTS/journal/content/_shared/arabic/)
