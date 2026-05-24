# NotebookLM Format Decision Matrix — *The Master and the Disciple*

**Status:** DRAFT — derived from A/B reference transcripts on 2026-05-24, written before the new orchestrator-generated `chapter-contracts/*.yml` exist. After Phase 0d emits the contracts, the per-chapter authoring step uses this draft to populate the `episode_format` field in each contract. The final matrix in `audits/notebooklm-format-matrix.md` is generated *after* per-chapter convergence and reflects what the challenger actually approved.

## Purpose

When you finish a chapter source bundle and open NotebookLM, you're choosing between two Audio Overview modes:

- **Deep Dive** — the default two-host conversation. Hosts unfold a single argument together. The female voice asks, the male voice teaches. Tone is collaborative.
- **Debate** — two hosts hold opposed positions, defended throughout the episode. Tone is adjudicative. Each host has source-moves; resolution is one of `{synthesis, open, host_a_concedes, host_b_concedes, historical_division}`.

The choice is per-episode, not per-book. The right choice depends on whether the chapter's underlying content **has a built-in two-sided tension that the reader is meant to weigh**, or whether it **unfolds a single unified picture**.

## Heuristic (book-agnostic)

| Signal in the source chapter | Recommended format |
|---|---|
| Single doctrine being unfolded layer by layer (zaahir → baatin, premise → conclusion) | **Deep Dive** |
| Narrative arc with one protagonist and one trajectory | **Deep Dive** |
| Synthesis or summary chapter that ties earlier threads together | **Deep Dive** |
| Two named positions in tension, each held by named figures or schools | **Debate** |
| Choice that costs the protagonist something concrete (rupture with family, loss of standing) where both choices have weight | **Debate** |
| Multiple competing interpretive frameworks the chapter explicitly weighs | **Debate** |
| Chapter where the *reader's* working-out of the question matters more than the *author's* settlement | **Debate** |

The Category P checks in [`podcast-challenger.md`](../../../../infra/claude-agents/podcast-challenger.md) enforce that a `debate` contract has the full block populated (proposition, host_a/host_b positions, source_moves, resolution). The new R-EPISODE-FORMAT-RECOMMENDED in challenger v2.1 elevates the format choice itself to a mandatory contract field.

## What the user did the first time (reference signal)

The previous NotebookLM run produced 8 reference MP3s now living at [`mp3/`](../mp3/) with transcripts at [`audits/ab-reference/transcripts/`](ab-reference/transcripts/). The format choice per chapter:

| Ch | Chapter title (curator-archive naming) | Opening line of reference transcript | Format used |
|---|---|---|---|
| 0 | Before the Door Opens | "This is the brief on the Master and the disciple..." | (intro / orientation) |
| 1 | Scholar and Seeker | "Welcome to this episode on the Master and the Disciple..." | **Deep Dive** |
| 2 | Oath and Cosmic Origins | "Welcome to this episode... I am really excited for this one..." | **Deep Dive** |
| 3 | The Inner Dimensions | "So imagine someone driving their car perfectly..." | **Deep Dive** |
| 4 | Meeting the Hujjah (The Greater Shaykh) | "So welcome to the Deep Dive, everybody..." | **Deep Dive** (explicit) |
| 5 | Father and Community | **"Welcome to the debate."** | **Debate** (explicit) |
| 6 | The Deep Truths | **"Welcome to the debate."** | **Debate** (explicit) |
| 7 | The Living Rope | "I am so excited for this deep dive..." | **Deep Dive** (explicit) |

5 Deep Dive + 2 Debate.

## Why those choices fit the underlying content

| Ch | Why this format fits |
|---|---|
| 1 | Establishes the master-disciple relationship and the disciplines of asking + listening. **One unified picture** is unfolded; the female host's curiosity drives the male host's exposition. Deep Dive is natural. |
| 2 | The covenant scene + the first cosmological teaching. Heavy and slow, but **one argument** — knowledge requires responsibility before explanation. Deep Dive lets the two hosts share the weight without staging it as a dispute. |
| 3 | Peeling **inner dimensions** beneath the outer Sharee-ah. The chapter's structure is a sequence of progressively interior readings, not a fork. Deep Dive matches the in-out spiral. |
| 4 | Meeting the greater Shaykh — **hierarchy of authority**, the disciple's smallness in the presence of the *Hujjah*. The chapter is reverential; staging it as a debate would flatten the awe. Deep Dive holds the deference. |
| 5 | The disciple's clash with his father + the community's hostility. The chapter explicitly holds **two positions in tension**: "speak the truth even at the cost of every relationship" vs "preserve the social peace your forebears built". Each position has source-moves (the father's claim of fitra and inheritance; the disciple's claim of `inna afdhal al-hasanaat ihyaa al-amwaat`). Debate is correct. |
| 6 | The chapter weighs **multiple interpretive frameworks** — literal vs allegorical, surface law vs hidden teaching, who has the right to ta'wil. The reader is meant to follow the contest of readings, not be told the verdict. Debate is correct. |
| 7 | **Synthesis**. The "Living Rope" ties seeker, oath, inner/outer, family, community, and ultimate truth into one practical instruction for daily life. There's no fork here — it's the book closing on a single image. Deep Dive is natural. |

## What to do with this matrix once Phase 0d emits new contracts

After the orchestrator's Phase 0d writes fresh `chapter-contracts/*.yml`, the per-chapter authoring step sets `episode_format: deep_dive` for the unified-doctrine chapters and `episode_format: debate` (with the full `debate` block populated per challenger Category P) for the tension-holding chapters.

The new chapters may not map 1:1 to the curator's original 8. If Phase 0d produces, say, 10 episodes from `refined-english.md`, the mapping rule is:

1. Identify each new episode's source-chapter range from [chapters-rationale.md](../_system/source/text/chapters-rationale.md).
2. Map it to the curator's 8-chapter index above by content theme (not by number).
3. Apply the format choice from the matching row; document the mapping in the contract's `episode_format_rationale` field.

If the new chapter set introduces material the curator's didn't (e.g., a separate episode for ch00's preface, or a split of ch06 into two), the chapter is classified by the heuristic table above — not by the reference choices, since the reference doesn't cover it.

## Per-chapter NotebookLM-button instruction (what you click)

Once the source bundle + framing are ready:

- **Deep Dive episodes (anticipated 1, 2, 3, 4, 7 + new ch00 if separately episode-ized):** upload the source bundle to NotebookLM → paste the framing into the Customize prompt box → click **"Audio Overview"** (default). NotebookLM produces the two-host conversation.
- **Debate episodes (anticipated 5, 6):** same source-bundle upload + same framing-paste → click **"Audio Overview"** → choose the **Debate** mode in the dropdown (where available). If the dropdown doesn't surface "Debate" in your NotebookLM build, the framing's "Welcome to the debate" opening directive + the populated `debate` block in the contract steer NotebookLM into debate-form via the Customize prompt alone.

Caveat: NotebookLM's "Debate" mode is a UI affordance that has shifted across versions. The Customize-prompt steering (proposition stated verbatim at open, two named positions, source-moves named per host, resolution clause at close) survives across UI changes; the dropdown alone does not. Trust the framing, not the button.

---

_Generator note: this draft was written from the A/B reference signal before Phase 0d completed. The final matrix at `audits/notebooklm-format-matrix.md` is generated post-convergence and reflects what the challenger actually approved. The challenger uses the heuristic table above (not the reference-derived per-chapter choices) to validate each new contract — so if Phase 0d emits 10 episodes instead of 8, the matrix grows; if it merges into 6, the matrix shrinks._
