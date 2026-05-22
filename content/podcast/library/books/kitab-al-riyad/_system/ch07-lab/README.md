# Ch07 Lab — closed-loop test of X15 (name-rotation) + X16 (dramatic-arc / challenger-friction / analogy-cap / recurring-thesis)

## Purpose

This lab folder is a closed-loop test of two framework rules added to the podcast pipeline on 2026-05-21:

- **X15** (name-rotation discipline) — addresses pipeline-debt **F14** (Arabic names mangled 12+ different ways per episode by NotebookLM TTS).
- **X16** (dramatic-arc + challenger-friction + analogy-cap + recurring-thesis) — addresses pipeline-debt **F15** (NotebookLM produces "two hosts unpacking" instead of "explainer vs genuine challenger"; over-explanation; analogy proliferation; thesis stated once).

Both rules ship as Phase 0e (chapter prose) and Phase 0g (framing-gen) prompt patches that take effect on the next orchestrator launch. This lab tests the rules out-of-band on the already-shipped Ch07 — the episode whose audio surfaced both failure modes in the first place — so we can audit the rules' effect on a real NotebookLM regeneration before committing them to all remaining KaR chapters and to future books.

The v1 baseline is the production EP07 as currently shipped (already audited; the failure-mode evidence informed F14 + F15). The v2 revision is a hand-authored re-application of X15 + X16 to the same chapter contract. The test: does NotebookLM, fed v2's chapter + framing, produce dramatically better audio than v1?

## Folder structure

```
_system/ch07-lab/
  README.md                   (this file)
  v1-baseline/
    chapter.txt               (verbatim copy of production ch07 chapter)
    framing.md                (verbatim copy of production EP07 00-framing.md)
    transcript.txt            (the NotebookLM-generated v1 audio transcript)
  v2-revised/
    chapter.txt               (NEW — chapter rewritten under X15 rotation discipline)
    framing.md                (NEW — framing rewritten under X15 + X16 disciplines)
    audit-checklist.md        (NEW — the test card for the v2 audio when it lands)
  v2-results/                 (created by the user once NotebookLM has regenerated)
    transcript.txt            (transcript of the v2-generated audio)
    audio.m4a                 (the regenerated audio file itself, if downloaded)
```

## How to run the test

1. Open NotebookLM and create a new notebook named *Kitab al-Riyad, Episode 7 (Lab v2)*.
2. Upload `v2-revised/chapter.txt` as the SINGLE source for the notebook (do not upload anything else; the v1 chapter should not be in scope for this generation).
3. Paste the entire contents of `v2-revised/framing.md` into NotebookLM's *Customize* prompt box.
4. Select the *Deep Dive* Audio Overview format. Length: *Longer* or *Extended*.
5. Click *Generate*. Wait for the audio to finish rendering.
6. Download the generated audio file as `m4a` and save it to `v2-results/audio.m4a`.
7. Once the audio is available, copy the auto-generated transcript into `v2-results/transcript.txt`.
8. Open `v2-revised/audit-checklist.md` and walk through all 7 rows. Fill in the *v2 result* column with actual counts/observations. Conclude with a verdict.

## What the v2 revision changes (vs v1)

**Chapter prose (chapter.txt):**

- "al-Kirmani" appears ONCE on first mention (in the opening paragraph, with the full English appositive `Hamid al-Din Ahmad al-Kirmani, the author of Kitab al-Riyad`). Every subsequent reference rotates among `the author / the master / our author / he`. v1 used "al-Kirmani" 37 times across 7,593 words; v2 uses it 1 time across 7,822 words.
- `al-Hayuli` appears ONCE on first mention with English gloss `(prime matter)`. Every subsequent reference is "prime matter" or "the substrate". v1 used `al-Hayuli` 30+ times; v2 uses it 1 time.
- `Abu Hatim al-Razi` and `Abu Ya'qub al-Sijistani` each get their full Arabic name + English appositive on first mention; thereafter the rotation set from `name-aliases.yml` applies.
- Book titles (`al-Islah`, `al-Nusra`, `Rahat al-'Aql`) appear in Arabic ONCE with English title in parentheses; thereafter the English title or short alias.
- Honorifics appear at most ONCE per form (F5 discipline).
- All philosophical substance, citations, verbatim chapter quotes, anchor passages, and the argumentative spine are PRESERVED. Only names rotate.

**Framing (framing.md):**

- New `## Critical pronunciation + citation rules (read BEFORE generating)` section opens the framing with the five highest-risk mangles called out explicitly.
- New `## Opening directive` instructs the hosts to lead with the CRISIS (Beat 1 of the 6-beat arc) — the rebutter's universe-disconnection fear, named with weight — BEFORE any solution. The central thesis *"Contact does not require resemblance — it requires rank, receptivity, and transmitted power"* is stated VERBATIM in the opening, at the pivot (Beat 4), and at the close (Beat 6). Three verbatim repetitions, declared mandatory under R-RECURRING-THESIS.
- `## Central tensions to reach` adds explicit R-CHALLENGER-FRICTION pushback patterns per tension — the Color host pushes back with "I don't buy that yet…", "That sounds like wordplay…", "Isn't this just replacing X with Y…", "How is this different from hiding the problem…". At least three of the four pushbacks must appear in the conversation. Forbidden first sentences for the Color host explicitly enumerated.
- `## Host dynamic` declares the Color host's role as genuine challenger, not supportive explainer.
- `## Three-part focus` restructured as the 6-beat dramatic arc (Crisis / Failed A / Failed B / Pivot / Correction / Stakes), with reset moments between Beat 4→5 and Beat 5→6.
- `## Tone constraints` declares THREE governing analogies UPFRONT (footprint, messenger, light-on-glass-and-stone) under R-ANALOGY-CAP. Forbidden mid-episode invention; the v1 list of 14 analogies is explicitly banned.
- `## Pronunciation` block trimmed to terms that genuinely appear in the v2 chapter.
- `## Name discipline` enumerates the first-mention form and rotation set for every figure that appears.
- `## Anti-noise rules` adds the R-RECURRING-THESIS rule explicitly.
- `## Do not` retains v1's content; adds the Color-host-specific banned agreeable openers.

## Citations

The rules under test live in `_workspace/plan/pipeline-debt.md`:
- **F14** — Arabic names mangled by NotebookLM TTS; remediation via X15 (rotation-set discipline at chapter-prose AND framing levels).
- **F15** — "two hosts unpacking" instead of "explainer vs genuine challenger"; remediation via X16 (R-DRAMATIC-ARC + R-CHALLENGER-FRICTION + R-ANALOGY-CAP + R-RECURRING-THESIS in the Phase 0g framing-gen prompt).

The per-figure rotation sets live in `content/podcast/library/books/kitab-al-riyad/_system/name-aliases.yml`.

## Promotion path

If the audit yields "dramatically better":
1. Copy `v2-revised/chapter.txt` → `chapters/ch07-soul-and-spirit-one-substance-or-two.txt` (production).
2. Copy `v2-revised/framing.md` → `_system/episode-drafts/EP07-soul-and-spirit-one-substance-or-two/00-framing.md` (production).
3. Regenerate the episode txt via the standard build step (`build_episode_txt.py` or the orchestrator's Phase 4 step 1).
4. Commit as the new EP07 baseline.
5. Mark F14 + F15 as `Resolved (verified by Ch07 lab)` in `_workspace/plan/pipeline-debt.md`.

If the audit yields "marginally better" or "no change": each failed audit row becomes a new pipeline-debt entry naming the specific failure mode. Iterate on the framing (the chapter prose is the lower-risk artifact; the framing is where X15 + X16 do most of their work).

If the audit yields "worse": revert the X15 + X16 prompt patches; investigate which rule introduced the regression.
