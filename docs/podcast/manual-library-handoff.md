# Manual library handoff — promotion workflow

**Purpose:** Document how content surfaced during podcast episode authoring (quotable lines, clinical anecdotes) gets PROPOSED to the memoir libraries — and how the journal-side operator PROMOTES it. This is the single channel through which the podcast skill influences memoir content. There is no automatic feed.

**Authority:** [`_workspace/plan/podcast-plan.yaml`](../../_workspace/plan/podcast-plan.yaml) `principles[P-7]` (Manual handoff for cross-skill content, never automatic) and [`framework.md`](../../framework.md) §"Cowork-Canonical-Writes".

---

## 0. The contract in one paragraph

When an episode authoring pass surfaces a quote or clinical anecdote that might belong in the memoir's libraries, the podcast skill writes a structured **proposal** to `BOOK_DIR/_system/episode-drafts/EP##-<slug>/proposed-library-entries.md` (schema_version 1). The journal-side operator reviews the proposal and, if approved, manually moves entries into `content/babu-memoir/_system/quotes-library.txt` or `content/babu-memoir/_system/clinic-library.txt`. The promotion is **always** a human-reviewed step; there is no automatic promotion script.

**The podcast skill NEVER writes directly to `content/babu-memoir/**`** — that boundary is enforced at runtime by [`scripts/podcast/_boundary_check.py`](../../scripts/podcast/_boundary_check.py) (P1.1).

---

## 1. The proposal file

### 1.1 Path
```
_workspace/<category>/<book-slug>/_system/episode-drafts/<episode-id>/proposed-library-entries.md
```

For example, after authoring Episode 2 of Ayyuhal Walad:
```
content/drafts/ayyuhal-walad/_system/episode-drafts/EP02-hatim-eight-benefits/proposed-library-entries.md
```

### 1.2 Schema (version 1)

```yaml
---
schema_version: 1
book_slug: <book-slug>
episode_id: EP##-<slug>
generated_by: scripts/podcast/_proposal_writer.py
generated_at: <ISO-8601 UTC>
---

## Quotes proposed for content/babu-memoir/_system/quotes-library.txt
- text: '...'
  attribution: '...'
  source_ref: '<book + chapter + page>'
  episode_context: '<one-line — why this quote landed in this episode>'
  confidence: high|medium|low

## Clinical anecdotes proposed for content/babu-memoir/_system/clinic-library.txt
- title: '...'
  summary: '<2-3 sentences>'
  source_ref: '<...>'
  episode_context: '<...>'

## Promotion ledger (journal side writes here when promoted)
- quote_id: <hash>
  promoted_at: <ISO-8601>
  promoted_to: content/babu-memoir/_system/quotes-library.txt#<line-anchor>
```

The proposal file is **append-once / promote-once**:

- The podcast skill writes the file ONCE per episode authoring pass.
- The journal-side operator appends to the `## Promotion ledger` section for each promoted entry.
- The proposal file is never deleted; it's the audit trail.

### 1.3 Schema validation

Every field in the frontmatter is required:
- `schema_version: 1` (integer)
- `book_slug` (string)
- `episode_id` (string, format `EP##-<slug>`)
- `generated_by` (string; canonical value `scripts/podcast/_proposal_writer.py`)
- `generated_at` (ISO-8601 UTC timestamp)

Authored by [`scripts/podcast/_proposal_writer.py`](../../scripts/podcast/_proposal_writer.py). The challenger Loop B3 (schema check) validates the frontmatter; an invalid proposal blocks ship.

---

## 2. When the podcast skill writes a proposal

During Phase 11-per-chapter authoring, when the chapter contains:
- A quotable line attributed to a named author / scholar / Imam, AND that line would extend the memoir's quotes-library;
- A clinical / human-experience anecdote from the source whose shape matches `content/babu-memoir/_system/clinic-library.txt`.

The producer populates a `ProposalBundle` and calls `_proposal_writer.write_proposal(book_dir, bundle)`. The proposal is written to the episode draft directory; the rest of the bundle continues normally.

**The producer does NOT consult the memoir's existing libraries.** It only surfaces candidates. Deduplication is the journal-side operator's responsibility.

---

## 3. The journal-side promotion workflow

When the operator wants to promote entries:

```bash
# 1. List all open proposals across all books
find content/podcast/library -name "proposed-library-entries.md" -type f

# 2. Review a specific proposal
cat content/drafts/<slug>/_system/episode-drafts/<ep>/proposed-library-entries.md

# 3. Promote selected entries:
#    a. Open content/babu-memoir/_system/quotes-library.txt
#    b. Manually insert the quote (the operator decides phrasing + section placement)
#    c. Note the line anchor where it landed
#    d. Append a promotion ledger row to the proposal file
```

The promotion is **always** a human operation. There is no `promote.py` script. Reasons:

1. **Authoring judgment.** The memoir's voice + section structure requires human selection (which quotes belong, which to skip, where each goes).
2. **Deduplication.** The operator owns the canonical libraries; the podcast skill doesn't.
3. **Audit trail.** Manual promotion forces a deliberate decision per entry, which the ledger captures.

---

## 4. Drift detection

If a proposal sits unpromoted for an extended period, it indicates either (a) the operator hasn't reviewed it, or (b) the proposal contains nothing worth promoting. Both are valid states; neither is an error.

The journal skill's `journal-challenger` agent reviews proposed entries during its `Category B` (boundary) pass — it flags proposals older than 30 days but does not auto-promote.

---

## 5. What this workflow does NOT do

- **It does not auto-promote.** No script moves content from proposed-library-entries.md to babu-memoir libraries.
- **It does not validate semantic fit.** The journal-side operator decides whether a quote BELONGS in the memoir.
- **It does not edit the memoir's chapter text.** Promotion adds entries to LIBRARIES (quotes, clinical anecdotes); chapter integration is a separate journal authoring decision.
- **It does not give the podcast skill any read access to memoir files.** The podcast skill writes proposals blind to what's already in the libraries.

---

## 6. Cross-references

- [`scripts/podcast/_proposal_writer.py`](../../scripts/podcast/_proposal_writer.py) — the writer module.
- [`scripts/podcast/_boundary_check.py`](../../scripts/podcast/_boundary_check.py) — runtime enforcement that podcast doesn't write to babu-memoir directly.
- `_workspace/plan/podcast-plan.yaml` `principles[P-7]` — the contract this workflow implements.
- `framework.md` §"Cowork-Canonical-Writes" — the cross-skill authority rule.
- `skills-staging/podcast/SKILL.md` §"Manual library handoff" — operator-facing summary.
