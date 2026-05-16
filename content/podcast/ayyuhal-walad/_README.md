# Podcast Run — Ayyuhal Walad

**Status:** dry-run complete on 2 of 7 redesigned episodes (Episode 1 + Episode 5). Awaiting user review before refining the remaining 5.

**Source:** *Ayyuhal Walad — My Dear Beloved Son (or Daughter)* by Imam Abu Hamid Muhammad Al-Ghazali, translated into English by Irfan Hasan from an Urdu translation of the Arabic original.

**Run timestamp:** 2026-05-16
**Slug:** `ayyuhal-walad`

---

## Folder map

```
ayyuhal-walad/
├── _README.md                                          ← you are here
├── _meta/
│   ├── _metadata.yml                                   ← title, author, tone, tradition
│   ├── episodes-metadata.yml                           ← per-episode provenance, ratios, flags
│   ├── raw-text.md                                     ← Stage 02 extraction
│   ├── normalized.md                                   ← Stage 05 cleanup
│   ├── _quality-gates-report.md                        ← Stage 14 verdicts
│   └── _segments/
│       ├── segments.yml                                ← 7-episode design (Stage 09 redesigned)
│       ├── segmentation-rationale.md                   ← why source structure was overridden
│       ├── raw-inventory.yml                           ← legacy 22-section inventory (intermediate)
│       └── section-NN-*.raw.md                         ← per-source-chapter raw extracts
├── 00-source/Ayyuhal-Walad.pdf                         ← verbatim original
├── 01-refined/                                         ← REFINED EPISODES (Stage 12)
│   ├── episode-01-frame-and-first-counsel.md
│   └── episode-05-the-path.md
├── 02-instructions/                                    ← NOTEBOOKLM INSTRUCTIONS (Stage 13)
│   ├── podcast-instructions.md                         ← combined master, 7 episodes
│   ├── episode-01-frame-and-first-counsel.instructions.md
│   └── episode-05-the-path.instructions.md
├── 03-pronunciation.md                                 ← pronunciation guide
├── 04-editorial-notes.md                               ← provenance, flags, user decisions
├── 06-library-proposals.md                             ← staged additions to journal libraries
├── scratchpad/                                         ← @@ MARKER SCRATCHPADS (Stage 12.5)
│   └── episode-01-frame-and-first-counsel.scratch.md
├── _legacy-section-files/                              ← preserved 22-section-style files
└── audio/                                              ← (empty; lands downloaded podcasts later)
```

## Working with `@@` markers

The `scratchpad/` directory carries parallel files for each refined episode. To request changes, open the scratchpad file and drop markers at the lines or paragraphs you want changed. On the next refinement pass, the markers are processed and stripped; the canonical refined episode is rewritten with your changes applied.

**11-verb vocabulary, three propagation tiers** (shared with journal memoir skill — canonical spec at `content/babu-memoir/_system/scratchpad-markers.md`):

- **Local (9):** `@@refine`, `@@replace`, `@@expand`, `@@cut`, `@@move`, `@@note`, `@@merge`, `@@rephrase`, `@@split` — apply only where marked.
- **Mechanical (1):** `@@pronounce(term: phonetic)` — auto-propagates across the series with confirmation.
- **Policy (1):** `@@policy(directive)` — lifted into `series-policies.md`, applies series-wide.

This means you can mark up Episode 1's scratchpad with local edits + pronunciation overrides + style policies, invoke refinement once, and the local edits stay scoped while the pronunciations and policies cascade across the remaining 6 episodes.

**Demo in place on Episode 1:** [`scratchpad/episode-01-frame-and-first-counsel.scratch.md`](computer:///Users/asifhussain/PROJECTS/journal/_workspace/podcast/ayyuhal-walad/scratchpad/episode-01-frame-and-first-counsel.scratch.md) carries 7 user-added markers covering all three tiers — 3 local (`@@note`, `@@expand`, `@@replace`, `@@refine`, `@@rephrase`), 1 mechanical (`@@pronounce(Sunnah: Soon-nah)`), 3 policies (Quranic verse layout, Sufi gloss-only-once, harder closings).

**Policies file:** [`scratchpad/series-policies.md`](computer:///Users/asifhussain/PROJECTS/journal/_workspace/podcast/ayyuhal-walad/scratchpad/series-policies.md) — empty until your first `@@policy` markers are processed.

To process: invoke `/podcast refine episode-01`. The skill will classify markers, prompt you to confirm propagation for Tier 2 + 3, apply local edits to Episode 1, lift policies to `series-policies.md`, and then refine the remaining 6 episodes under the new policies.

## Quality gate verdicts (sample of 2 redesigned episodes)

| Gate | Status |
|---|---|
| 1 — No non-Latin script | **PASS** |
| 2 — No bracketed commentary | **PASS** |
| 2b — No frontmatter in refined files | **PASS** (new gate) |
| 3 — Citation provenance | **PASS** (manual review noted) |
| 4 — Section order preserved | **PASS** |
| 5 — Word count 70-140% | **PASS** (both episodes at 0.77-0.81 ratio) |
| 6 — Implicit citation detection | **PASS** |
| 7 — Per-section determinism | **DEFERRED** |

## What was validated in this dry-run

1. PDF extraction works cleanly (no OCR needed for this source).
2. Tradition auto-detection (islamic, 0.95 confidence) lands correctly.
3. New Stage 12 Hard Rule 5 (paraphrase for articulation, preserve propositional content) operates within Gate 5 envelope.
4. **Content-driven re-segmentation (Stage 09 revised)** collapsed 22 raw sections into 7 thematic episodes with even pacing — Episode 1 demonstrates expansion across a chapter boundary; Episode 5 demonstrates heavy merger of 8 source chapters into one cohesive episode.
5. **Frontmatter rule (Stage 12 + Gate 2b)** — refined episodes contain only the heading and prose; all metadata lives in `_meta/episodes-metadata.yml`.
6. **NotebookLM best-practices reference** — `content/podcast/_system/notebooklm-best-practices.md` is the authoritative source for segmentation targets and prompt design; the skill consults it on every run.
7. **`@@` marker scratchpad capability (Stage 12.5)** — 10-verb vocabulary in place; demo scratchpad on Episode 1; validator extended to scan podcast scratchpads.

## What the user needs to decide before continuing

See `04-editorial-notes.md` for the full list. Two headline decisions:

1. **Are the 2 refined samples ready in quality?** If yes, refine the remaining 5 episodes under the same approach.
2. **Try the scratchpad?** Open the Episode 1 scratchpad, drop a few `@@` markers, then ask me to process them — this validates the refinement-loop ergonomics on real content before committing to the full pipeline.

## Next commands

- `/podcast refine episode-01` — process the Episode 1 scratchpad, apply directives, strip markers, rewrite canonical
- `/podcast continue ayyuhal-walad` — refine remaining 5 episodes
- `/podcast apply ayyuhal-walad` — merge library proposals (available after full run completes)
