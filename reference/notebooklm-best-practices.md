# NotebookLM Audio Overview — Source Structure & Best Practices

**Last synthesized:** 2026-05-16.
**Authoritative status:** This file is the **canonical reference** for any podcast, audio overview, or NotebookLM-targeted artifact produced in this repo. The `podcast` skill, `journal` skill, and any future audio-targeted agent must consult this file before segmenting source content or writing instruction prompts. If NotebookLM's docs change, this file is updated first, then the skills inherit.

**Primary sources (verified 2026-05-16):**
- Google Help — *Generate Audio Overview in NotebookLM* (support.google.com/notebooklm/answer/16212820)
- Google Help — *NotebookLM Help Center* (support.google.com/notebooklm)
- MakeUseOf — *NotebookLM Audio Overviews Custom Prompt Guide* (Apr 2026)
- jeffsu.org — *NotebookLM in 2026: What Changed and What Matters*
- superlore.ai — *NotebookLM Audio Overview Limits 2026: Complete Guide*

---

## 1. Audio Overview formats (canonical, from Google)

NotebookLM ships **four** Audio Overview formats. The skill must declare which one each episode targets, because each format wants a different source shape.

| Format | Hosts | Length character | Best source shape |
|---|---|---|---|
| **Deep Dive (default)** | Two hosts, lively conversation | 12-25 min at Default; up to ~40 min at Longer | Single coherent theme with two or three connected ideas. Hosts unpack and connect — works best when the source itself argues, narrates, or develops a thought. |
| **The Brief** | One speaker | Under 2 min | A tight, focused source where the key takeaways are extractable in ten or so sentences. Avoid when the content has nuance or argument that needs unpacking. |
| **The Critique** | Two hosts, constructive evaluation | 10-20 min | An essay, design doc, or position-piece source that explicitly invites evaluation. Not useful for narrative or devotional content. |
| **The Debate** | Two hosts, formal back-and-forth | 12-25 min | A source presenting a claim that has a real opposing view in the literature. Avoid when the source is monologic or unanimous (e.g., a single-tradition spiritual treatise). |

**For most podcast work — including memoir, spiritual treatise, lectures, sermons, narrative non-fiction — the Deep Dive format is the right choice unless the user specifies otherwise.**

## 2. Length controls (Default / Shorter / Longer)

Google added Length control in May 2025. Currently English-only; other languages will follow. The three settings target roughly:

- **Shorter:** ~6-10 min spoken
- **Default:** ~12-20 min spoken
- **Longer:** ~22-40 min spoken (varies with source volume)

The Audio Overview's actual runtime is a function of: source word count, prompt richness, and the format chosen. The Length toggle nudges the model but does not strictly cap the output.

## 3. Source word-count targets per episode

Synthesized from Google's documented format characteristics, MakeUseOf prompt-design guidance, and observed runtimes from community testing:

| Episode target length | Refined source word count | Notes |
|---|---|---|
| Brief (~2 min) | 200-500 words | A single argument, one decision, one takeaway. |
| Short Deep Dive (~8 min) | 800-1,500 words | One claim with two-to-three supporting pieces. |
| **Default Deep Dive (~15 min)** | **1,800-2,800 words** | **Sweet spot for most podcast work.** A coherent theme that develops, with room for dialogue and analogy without sprawl. |
| Longer Deep Dive (~25 min) | 3,000-4,500 words | Multi-thematic or extended-argument source. Avoid going much past 4,500 — hosts begin to lose narrative thread. |
| Maximum useful per episode | ~5,500 words | Beyond this, NotebookLM either summarizes away content or the conversation becomes superficial. Split into multiple episodes. |

**Hard floor:** episodes under ~500 words feel thin. Hosts have nothing to develop and resort to filler. Bundle thin sections together.

**Hard ceiling:** episodes over ~5,500 words feel rambling. Split.

## 4. The single most important rule: re-segment by content, not by source structure

**Do not honor the source's chapter or section structure when segmenting for Audio Overview.** A book's chapters were designed for a reader, not for an AI host conversation. The right segmentation is:

1. **Thematic coherence** — each episode is one idea or one tightly connected cluster of ideas. Listeners should be able to summarize the episode in one sentence.
2. **Approximately balanced word count** — every episode lands in the 1,800-2,800 word band (Default Deep Dive). Outliers (a brief closing prayer, an unusually long admonition) are documented and either split or accepted with a note.
3. **Natural narrative arc** — each episode has a beginning, middle, and end. The middle is where the host conversation can dwell. Avoid episodes that are just lists.
4. **Forward-only ordering** — episodes follow the source's logical flow even when they don't follow its physical chapters. A listener should be able to listen in order and feel the work unfolding.

Source chapters that are too short for an episode get **merged**. Source chapters that are too long get **split**. The source's table of contents is a hint, not a constraint.

## 5. Prompt design — what hosts must be told

Google's "Customize" prompt box ("What should the AI hosts focus on in this episode?") is the most important lever in the entire system. Default prompts produce generic, drifting episodes. **The skill must generate a rich custom prompt per episode**, structured as:

1. **One-sentence opening directive.** What the hosts say in the first ten seconds. Names the work, names the episode theme, sets the listener's frame.
2. **A three-part Focus block.** Three concrete things the hosts must keep their attention on. Not abstract themes — specific behaviors and decision points the listener should walk away with.
3. **Pronunciation hooks.** Every non-English term, every transliteration, every honorific the hosts will encounter — paired with its phonetic form and brief gloss.
4. **Anti-noise rules.** What the hosts must NOT do — drift into general background, summarize the next episode, abbreviate honorifics, invent supporting material.

Default prompts are 1-2 lines. Skill-generated prompts should be 200-500 words per episode.

## 6. Source format support (early 2026)

NotebookLM accepts: PDF, Google Doc, Google Slides, web URL, plain text, YouTube video, audio file, EPUB. Each source can be up to 500,000 words / 200 MB.

For maximum control, **the skill's deliverable is a refined Markdown file per episode** (one source per episode), not the original PDF. NotebookLM ingests the Markdown cleanly, the refined content is audio-optimized, and the skill controls exactly what each host sees.

## 7. Source-set strategy per episode

Each Audio Overview is generated from **one notebook with one or more sources**. Two patterns work:

- **One refined chapter file per notebook** → one episode. Simplest, gives the host conversation maximum focus. Use this as the default.
- **One refined chapter + the pronunciation guide + the per-episode instructions, all uploaded to the same notebook** → one episode. Gives the hosts explicit phonetic guidance and editorial framing. Use this when the source contains non-English terms or unusual conventions.

The instructions file should be uploaded as a **second source**, not pasted into the prompt box. Sources have higher fidelity than prompts in NotebookLM's current model.

## 8. Plan limits (consumer accounts, May 2026)

| Plan | Sources per notebook | Audio Overviews per day | Word limit per source |
|---|---|---|---|
| Free | 50 | 3-5 | 500,000 |
| Plus (Workspace Standard) | 100 | ~20 | 500,000 |
| Ultra | 300 | 20+ | 500,000 |

A typical podcast project of 6-10 episodes fits inside the Free tier if generated across multiple days.

## 9. Interactive Mode

Interactive Mode allows the listener to pause the Audio Overview and ask the hosts a question. Currently English-only. The hosts answer using the sources, then resume.

For published podcasts, Interactive Mode is irrelevant (the downloaded audio is static). For research or study notebooks where the listener wants to dig in, it's valuable. The skill's refined Markdown files work fluently with Interactive Mode — the source content is exactly what the hosts will draw from when answering.

## 10. Output language

NotebookLM Audio Overviews support 80+ languages including Arabic (Modern Standard and Egyptian Colloquial), Urdu, Persian, Hebrew, and most major world languages. **However:** the skill's `language-policy=preserve-meaning-output-english` default means the refined Markdown is English. To produce a non-English Audio Overview, the user must either (a) instruct NotebookLM to translate during generation, or (b) ask the skill to produce a translated refined Markdown first.

## 11. Sharing and download

Audio Overviews can be downloaded as audio files or shared via link. **Shared links require the notebook to be made public** (Workspace Enterprise/Education accounts cannot make notebooks public). For downstream distribution (Spotify, Apple Podcasts), download the MP3 and ingest into the user's preferred podcast hosting pipeline.

---

## Required reading checklist before any podcast-targeted work

The `podcast` skill, the `journal` skill (for memoir-to-podcast conversion), and any new audio-targeted agent must verify these checks before producing instruction prompts:

- [ ] Has this file been read in the current run?
- [ ] Does the segmentation plan target the Default Deep Dive word-count band (1,800-2,800 refined words per episode)?
- [ ] Are episodes thematically coherent — one sentence per episode summary?
- [ ] Are word counts approximately balanced across the series?
- [ ] Does each per-episode instruction prompt include the four required components (opening, three-part focus, pronunciation hooks, anti-noise rules)?
- [ ] Is the source's chapter structure being treated as a hint, not a constraint?

If any check fails, halt and write `NOTEBOOKLM-COMPLIANCE-FAILED.md` to the run's `_meta/` directory before continuing.

---

## Sources

- [Generate Audio Overview in NotebookLM — Google Help](https://support.google.com/notebooklm/answer/16212820?hl=en)
- [NotebookLM Help Center — Google Help](https://support.google.com/notebooklm/answer/15731776?hl=en)
- [NotebookLM Audio Overviews Custom Prompt — MakeUseOf, Apr 2026](https://www.makeuseof.com/notebooklm-audio-overviews-better-custom-prompt/)
- [NotebookLM in 2026: What Changed and What Matters — Jeff Su](https://www.jeffsu.org/notebooklm-changed-completely-heres-what-matters-in-2026/)
- [NotebookLM Audio Overview Limits 2026 — Superlore](https://superlore.ai/blog/notebooklm-audio-overview-limits-2026)
- [NotebookLM Tips & Tricks 2026 — Shareuhack](https://www.shareuhack.com/en/posts/notebooklm-advanced-guide-2026)
