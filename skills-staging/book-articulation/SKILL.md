---
name: book-articulation
description: >
  Articulation contract for book prose in the Podcast Factory pipeline: how a
  stiff, literal, Arabic-calqued English chapter is rewritten into modern, lucid,
  simple English that reads like a professionally published book, including a
  full spelling/grammar copy-edit and list-shape pass — while every teaching,
  speech, quote, image, Arabic run, and enumeration survives intact.
  Backs BOTH the automatic 0book-fluency pass (runs on every translation-edition
  book at compose time) and the Book Composer's on-demand Rearticulate action —
  the two share one prompt builder so they cannot drift apart. MUST be loaded
  for ANY work that rewrites chapter prose for readability: the Rearticulate
  action (scripts/podcast/rearticulate_chapter.py), the book-rearticulator
  agent, the 0book-fluency pass, or edits to the Refine panel's rewrite modes
  (/api/ai/rewrite). TRIGGER: "rearticulate", "articulate this chapter",
  "de-calque", "reads like a translation", "make it read professionally",
  "book-rearticulator". Canonical rule text: docs/standards/book-articulation.md
  (cite REQ-BA-NNN, never restate).
---

# Book Articulation

The full requirement text lives in
[docs/standards/book-articulation.md](../../docs/standards/book-articulation.md)
— cite findings by `REQ-BA-NNN`. This skill is the operational wrapper: what to
run, what gates apply, and the failure mode the contract exists to prevent.

## The failure this contract prevents

The canonical violation (2026-07-27, *The Master and the Disciple* ch. 3): a
generic "clarify" rewrite turned "you have preached and struck the mark" into
"you have preached effectively" — 183 words to 139, every image flattened into
abstraction, one stray "Sheikh" against the book's 24 "Shaykh". Nothing in the
static gates caught it, because register and imagery are semantic. The contract
names them as protected artifacts (REQ-BA-040/050) so a judge can fail them.

## The one-line contract

> Rewrite the grammar as much as you like; the meaning, the artifacts, and the
> images are not yours to touch. Fix spelling and grammar; evaluate real lists
> for bullets or numbering with indentation. Simple English, professional
> register, never shorter, nothing added.

## How articulation runs — two routes, one prompt

- **Automatic:** `0book-fluency` (`scripts/podcast/_book_voice.py`
  `apply_fluency_adapt`) runs over every translation-edition book's faithful
  base at compose time — the default for the whole book, not one chapter.
- **On-demand:** `scripts/podcast/rearticulate_chapter.py <slug> <chapter-key>` —
  resolves the Composer's chapter key to its `##` section through the pipeline's
  own `anchor_key` (NEVER a printed chapter number: the introduction is section
  1) and rewrites one chapter.
- **Shared prompt:** both call `_book_voice_prompts._articulation_prompt` — the
  one builder for the REQ-BA contract — so the automatic pass and the
  one-chapter tool cannot silently diverge.
- **Copy-edit and list structure:** both routes run the same required
  spelling/grammar cleanup (REQ-BA-112) and list-shape judgment (REQ-BA-115).
  The pass may introduce bullets or numbered lists when the prose is genuinely
  list-like, but it must not treat source section numbering, citations, verse
  numbers, or protected quoted material as layout invitations.
- **Shared gates:** both run every window through `revoice_gates` (abridgement,
  teaching loss, Arabic retention, doctrinal P0s, narrative frame, and a leaked
  `===ARTICULATION-NOTES===` marker per REQ-BA-160). A window that fails a gate
  REVERTS to its base — a failed pass is a no-op, never a degradation.
- **Out-of-band notes (REQ-BA-160):** either route may end its output with one
  `===ARTICULATION-NOTES===` block reporting an ambiguity, a comprehension risk,
  or a term worth standardizing — `_book_articulation_notes` strips it before
  gating and files it into that chapter's pass record
  (`editorial_queries` / `comprehension_flags` / `terminology_notes` in
  `_system/book-fluency-report.json` or the rearticulate result). It never
  reaches `book.md`; nothing here is auto-applied.
- **Durability (on-demand route):** the result is recorded in
  `_system/composer-edits.json` through `_book_edits.record_edit`, exactly like
  a human Composer save — it survives re-compose and marks the chapter as
  authored (the Composer remains the singular path for PDF-bound prose changes).
- **Long chapters** window at 4,500 words per the long-chapter rule; each
  window gates and reverts alone.
- **Quality gate:** the `book-rearticulator` agent judges the result against
  REQ-BA-* and the BK-N narrative findings; its convergence action on a failed
  chapter is revert, not re-prompt-until-it-passes.

## When NOT to rearticulate

- The chapter already reads fluently — a near-identical output is a warning,
  not a win; do not spend the call.
- The prose problem is a missing teaching or a factual error — that is a
  compose/challenger problem, not an articulation problem.
- You want a shorter or a simpler-in-content text — abridgement and
  simplification of substance are out of contract (REQ-BA-030/100).
