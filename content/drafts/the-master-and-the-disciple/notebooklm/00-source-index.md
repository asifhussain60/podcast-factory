# NotebookLM Source Index: *The Master and the Disciple*

**Read this file FIRST when you set up the NotebookLM notebook.**
It tells NotebookLM (and the human operator) what every file in this directory is, what role it plays, and how it should be used.

This index is the **podcast scaffolding** layer. The chapter prose itself remains untouched in the parent directory. Nothing in this `_notebooklm/` directory is the original work — these files are editorial guidance about how to present the work.

---

## Series identity

**Work:** *The Master and the Disciple* / *Kitaab al-Aa'lim wal-Ghulaam*
**Tradition:** Early Ismaili Shi'i. Associated with Ja'far ibn Mansoor al-Yaman — **say "associated with," not "definitively authored by"** unless a verified critical edition resolves the attribution.
**Form:** Dramatic dialogue. Knowledge is earned, tested, lived. Not a manual; not self-help.
**Series premise:** How does a seeker become capable of receiving true knowledge? The book traces that formation through gratitude, covenant, symbolic interpretation, rank, family conflict, communal testing, and the recognition of living guidance.

---

## File roles (the source-role ambiguity, resolved)

The directory contains both **source material** (the work itself, refined for narration) and **production metadata** (information about how the source was prepared). NotebookLM must NOT confuse the two. The following table is authoritative.

| File | Role | Use in NotebookLM |
|---|---|---|
| `Ch-00-Before-the-Door-Opens.txt` | **Listener preface** — editorial orientation to the work | Episode 0 source. Frames how to enter the series. Not part of the original Arabic text. |
| `Ch-01-Scholar and Seeker - Refined.md` | **Primary chapter** — refined source text | Episode 1 source. Refined from the original. Contains labeled `[Editorial Clarification]` paragraphs (modern analogies). |
| `Ch-02-Oath and Cosmic Origins - Refined.md` | **Primary chapter** | Episode 2 source. Densest cosmology. |
| `Ch-03-The Inner Dimensions - Refined.md` | **Primary chapter** | Episode 3 source. Egg analogy, three levels. |
| `Ch-04-The Greater Shaykh - Refined.md` | **Primary chapter** | Episode 4 source. Naming ceremony, ownership. |
| `Ch-05-Father and Community - Refined.md` | **Primary chapter** | Episode 5 source. Family debate. |
| `Ch-06-The Ultimate Truth - Refined.md` | **Primary chapter** | Episode 6 source. The climactic theological debate. |
| `Ch-07-The-Living-Rope.txt` | **Thematic epilogue / finale** — editorial synthesis essay | Episode 7 source. Not part of the original Arabic text — it is a contemporary synthesis written to help the listener carry the book into daily life. |
| `Source and Editorial Notes.md` | **Production / source-integrity notes** | Reference material. Tells the operator how the refinement was done and which quotations need verification. **Do NOT** treat this as episode content. |
| `Final Review Report.md` | **Production metadata** | Reference material only. Internal record of what was produced. **Do NOT** turn this into episode content. |

### Scaffolding files (this directory)

Everything under `_notebooklm/` is podcast scaffolding — editorial guidance about how to present the work, NOT source text:

| File | Role |
|---|---|
| `00-NotebookLM-Source-Index.md` | This file. Master orchestration document. |
| `01-pronunciation-guide.md` | Central pronunciation table with stress cues. |
| `02-glossary.md` | Listener-facing glossary of technical terms. |
| `03-source-integrity-notes.md` | Consolidated table of every quotation/attribution/theological claim that needs human verification before publication. |
| `04-do-not-say-guardrails.md` | Specific anti-patterns NotebookLM must avoid. |
| `05-episode-arc.md` | Series map: per-episode core question, tension, model. |
| `06-human-review-checklist.md` | Pre-publication gate. |
| `ch00-scaffolding.md` … `ch07-scaffolding.md` | Per-chapter Source Card, Episode Intelligence, Host Questions, Listener Difficulty, Review Lens, Episode Opener/Closer, NotebookLM Instruction. |

---

## How to upload to NotebookLM

NotebookLM allows up to 50 sources per notebook. The recommended bundle is **all 17 files in this book directory**, uploaded as separate sources so NotebookLM can cite each correctly. Then the operator pastes the **per-episode customize prompt** (assembled from the relevant `chNN-scaffolding.md` Episode Intelligence + Host Questions + NotebookLM Instruction + relevant Do Not Say + relevant entries from the pronunciation guide) into the Customize box.

| Upload order | File set |
|---|---|
| 1 | `_notebooklm/00-NotebookLM-Source-Index.md` (this file — orientation) |
| 2 | `_notebooklm/01-pronunciation-guide.md` |
| 3 | `_notebooklm/02-glossary.md` |
| 4 | `_notebooklm/03-source-integrity-notes.md` |
| 5 | `_notebooklm/04-do-not-say-guardrails.md` |
| 6 | `_notebooklm/05-episode-arc.md` |
| 7 | `Source and Editorial Notes.md` (production metadata) |
| 8 | `Final Review Report.md` (production metadata) |
| 9–16 | `Ch-00…Ch-07` (the source files in chapter order) |
| 17 | `_notebooklm/chNN-scaffolding.md` for the episode being produced this session |

For a single-episode session, the operator may upload a smaller subset: master index + that episode's chapter + that episode's scaffolding + pronunciation + glossary + Do Not Say + source-integrity.

---

## Editorial separation contract

Every file in this scaffolding directory adheres to the four-layer separation rule from `podcast-best-practices.md` §"Required Editorial Separation":

| Label | Meaning | Authority |
|---|---|---|
| `[Source Text]` | The work's own words (refined into English phonetic transcription where needed). | Original — uses the work's voice. |
| `[Editorial Clarification]` | Translator/editor explanation, modern analogy, or paraphrase. | Editorial — uses the editor's voice. |
| `[Podcast Host Cue]` | Question or instruction for the podcast host (NotebookLM). | Editorial — directed at the production layer. |
| `[NotebookLM Instruction]` | Direct instruction to NotebookLM about how to generate audio. | Editorial — directed at the AI. |

**NotebookLM must NEVER quote `[Editorial Clarification]`, `[Podcast Host Cue]`, or `[NotebookLM Instruction]` content as if it were `[Source Text]`.** These are scaffolding, not the work.

---

## Series premise (one paragraph for the host)

This is a story about formation, not transmission. A young man encounters a scholar, becomes a seeker, takes an oath, learns to read the visible world as symbolic of an inner order, meets a greater Shaykh, returns to confront his father, debates a learned outsider, and finally helps a community come to truth without rage. The book argues that knowledge is a trust, not a possession; that the outward form (Sharee-ah) and the inner meaning (baatin) belong together; that guidance after prophecy is living, not merely archival; and that the gateway into all of this is gratitude that becomes action. The Ismaili tradition is the home of this teaching — present it as that tradition's specific contribution to Islamic intellectual life, not as generic Islam.

---

## Recommended episode count

**Option A (recommended): 8 episodes** — Episode 0 (Before the Door Opens) + Episodes 1–6 (one per primary chapter) + Episode 7 (The Living Rope as finale).

**Option B: 4 episodes** — for a tighter season:

1. Episode 1: Seeking and Gratitude (Ch 00–01)
2. Episode 2: Oath, Symbol, and Inner Meaning (Ch 02–03)
3. Episode 3: Authority, Family, and Community (Ch 04–05)
4. Episode 4: The Living Rope and Daily Practice (Ch 06–07)

Use Option A by default; Option B only when the host needs a shorter season for a different listener fit.

---

## How to revise this directory

- The chapter prose files in the parent directory are **frozen** unless the operator explicitly asks for a prose rewrite.
- Scaffolding files in this directory are **the editing surface**. Update them when host questions evolve, when human review resolves a flagged claim, or when listener feedback identifies a misframing.
- After any change here, re-read `06-human-review-checklist.md` before publication.
