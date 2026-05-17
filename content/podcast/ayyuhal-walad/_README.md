# Podcast — Ayyuhal Walad

**Source:** *Ayyuhal Walad — My Dear Beloved Son (or Daughter)* by Imam Abu Hamid Muhammad al-Ghazali. English translation by Irfan Hasan, from the Urdu rendering of the Arabic original (compiled within *Majmu'a Rasail Imam Ghazali*). Original at [`_system/source/Ayyuhal-Walad.pdf`](computer:///Users/asifhussain/PROJECTS/journal/content/podcast/ayyuhal-walad/_system/source/Ayyuhal-Walad.pdf).

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
│   └── EP##-<slug>.txt                       (one per chapter, slug-matched)
├── turboscribe/                              POST-PUBLISH TRANSCRIPTS — slug-aligned
│   └── _README.md
└── _system/                                  book-specific authoring state
    ├── source/
    │   ├── Ayyuhal-Walad.pdf                 verbatim original (audit anchor; never modified)
    │   └── text/                             Phase 0a–0c extraction + normalization + phonetics
    ├── episode-drafts/EP##-<slug>/           per-episode framing + scaffolds
    ├── scratchpad/                           series-policies
    ├── pronunciation.md                      book-level overrides (additive to SHARED_ARABIC)
    ├── enrichment-log.md                     attribution sidecar for Phase 0e enrichment
    ├── editorial-notes.md                    flags + provenance + user decisions
    └── challenger-report.md                  podcast-challenger convergence verdict
```

## Two-file deliverable per episode

| File | Role | NotebookLM action |
|---|---|---|
| `chapters/ch##-<slug>.txt` | enriched chapter — **SOURCE** | Upload as the single source file |
| `episodes/EP##-<slug>.txt` | customize prompt — **CUSTOMIZE PROMPT** | Paste into the *Customize* box |

Strict 1:1 mapping enforced: slug after the prefix is identical on both sides. The chapter IS the source — no transformation by `build_episode_txt.py`.

## Series intake (pre-committed)

- **Audience:** thoughtful seekers (Muslim and otherwise) drawn to Islamic / Sufi spiritual tradition; the bar is "intelligent listener encountering Ghazali for the first time without academic prerequisites".
- **Angle:** faithful exposition with light personal-application beats — let Ghazali's bite land; do not soften; surface tensions.
- **Host dynamic:** default Curious Mind (Host A) + Patient Teacher (Host B). Host B grounds in tradition; Host A keeps the modern reader's questions live.
- **Length:** Default Deep Dive (~12–15 min) per episode.
- **Chapter count:** 5, following the v3.5 thematic re-segmentation.

## Status

Fresh re-run, 2026-05-17. Prior workspace archived to `_archive/ayyuhal-walad-2026-05-17/`. All five chapter prose, framings, and episode txts authored under v3.5 (no inline phonetics, pronunciation lives in customize prompt only). Build script enforces gates.

## Canonical references

- Skill: [`skills-staging/podcast/SKILL.md`](computer:///Users/asifhussain/PROJECTS/journal/skills-staging/podcast/SKILL.md)
- Challenger: [`.github/agents/podcast-challenger.agent.md`](computer:///Users/asifhussain/PROJECTS/journal/.github/agents/podcast-challenger.agent.md)
- Cross-series episode index: [`content/podcast/_handbook/registry.md`](computer:///Users/asifhussain/PROJECTS/journal/content/podcast/_handbook/registry.md)
- Shared Arabic / phonetics authority: [`content/_shared/arabic/`](computer:///Users/asifhussain/PROJECTS/journal/content/_shared/arabic/)
