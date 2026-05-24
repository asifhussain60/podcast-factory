# Redesign Proposal — Operator-curated Source Bundle → Podcast

**Authored:** 2026-05-19 by Claude Opus 4.7 in a parallel MacBook Air session, delegated by the operator while the primary Mac was running `orchestrate_book.py --resume kitab-al-riyad`.

**Integrated into the plan:** 2026-05-19 by the primary-Mac assistant as commit `efdf323` on branch `feat/podcast-w1-foundation`. Three of four proposed changes (A + B + C) landed directly as handbook + plan + preflight deltas; one (D) is scoped under P17.1's `extension_change_d` block for landing AFTER P9.5 (Asaas) ships clean. Two operator-added changes (E and F) were appended as P21 and P22 respectively.

**Post-integration audit:** 2026-05-19 by claude-opus-4.7 (parallel-Mac session, second pass). Read-only audit of the integrated state. Verdict: SHIP-READY. Surfaced 5 minor drifts and 5 missing items. All gaps closed in a follow-up commit on the same branch — see `research/2026-05-19-redesign-audit-from-air.md` for the audit doc and `meta.research_artifacts` for the cross-link.

**Status:** This document is the source-of-truth narrative for the architectural decisions taken on 2026-05-19. The plan YAML carries the structured deltas; this file carries the *why*.

---

## Problem

The operator (on MacBook Air, parallel session) made three asks across this session that initially looked like separate features but collapse onto one capability when held together:

1. **Asaas analysis (Q1)** — read-only section-mapping pass on Asaas Al-Taveel.pdf (416 pp., Arabic, image-only, scanned 1960 Beirut edition by al-Qadi al-Nu'man, edited by Aref Tamer). Surfaced an unusual structure: six written chapters per natiq (Adam, Nuh, Ibrahim, Musa, 'Isa, Muhammad), wildly uneven (43/31/72/120/16/54 pp.), with the seventh chapter (Qa'im) deliberately not written — the editor states on p. 21 that al-Nu'man stopped because the awaited Qa'im "has not yet come." The book is a recursive batin/ta'wil text: each natiq cycle repeats a fixed cosmological pattern.

2. **Teaching density (Q2)** — "Bring out the details, use this as a teaching mechanism, explain through the conversation of podcasters, but don't make too many episodes." Teaching-mode dialogue requires the source to be quotable (the PDF is image-only Arabic — needs OCR + translation), a sustained glossary of technical vocabulary across episodes, and a recursive scaffold across the episode arc rather than independent self-contained episodes.

3. **Folder ingestion (Q3)** — "Use the podcast agent on a folder containing a bunch of random documents and ask for it to be turned into a podcast. I will define the details of the order but it should still go through the same refinement enrichment process as in the plan being developed."

The operator's gloss across all three: the existing plan handles "one book → podcast" but the operator's actual workflow is "any well-curated source bundle → podcast." The gaps are subtler than "new format mode" — they are (a) book-level conceptual scaffolding (sustained technical vocabulary across episodes), (b) recursive teaching across an episode arc (Ep1 sets the pattern; Ep2–N reuse it), (c) capturing source-structural insight BEFORE the orchestrator hits its series-plan gate, and (d) generalizing source ingestion to multi-document operator-authored bundles without forking the pipeline.

---

## Current state

Files / contracts examined (read-only):

- `_workspace/plan/podcast-plan.yaml` — single execution path, 19 phases, 5 waves; P9.5 already lists Asaas Al-Taveel (416p): full pipeline; metrics recorded; Loop N clean as a W3 acceptance row; P17.1 (W5 deferred, source-adapter registry) has `promote_when: "first non-Arabic-PDF source arrives OR user explicitly opts in"`.
- `_workspace/plan/acceptance-criteria.md` — ~230 checkboxes; P9.5 has the per-book ship-gate rows but no book-specific structural preflight; P17.1 has ~10 rows already specifying adapter registry + arabic_pdf + boundary integration + cost-ledger.
- `content/podcast/.skill/handbook/two-host-framing.md` — default Curious Mind + Scholar Companion personas; Mentor + Student is already an override pattern (line 41); beat-count tiers live in episode-architecture.md.
- `content/podcast/.skill/handbook/debate-framing.md` — Deep Dive vs. Debate is the existing format axis; Mentor+Student is a persona override layered on top, not a third format.
- `content/podcast/.skill/handbook/episode-architecture.md` — four beat-arc patterns; no pattern that explicitly handles "Ep1 builds a conceptual scaffold; Ep2–N reuse it."
- `content/podcast/.skill/handbook/book-dir-layout.md` — book-level `_system/` files (`pronunciation.md`, `mangle-map.md`, `meta-prose-tells.md`, `enrichment-whitelist.md`, ...); no book-level conceptual-glossary artifact; no manifest concept. `_system/source/text/chapters-rationale.md` is Phase 0d's segmentation rationale.
- `scripts/podcast/` — running PID 56236 on the primary Mac is `orchestrate_book.py --resume kitab-al-riyad`, Phase 0b ~50% done. Disjoint from this proposal's touch surface.
- P4 numeric-symbolic disambiguation (already in the plan) is directly relevant to Asaas's 7-natiq / 12-hujja / abjad surface; Loop N is a free pre-existing guardrail.
- P17.1 (W5 deferred) is exactly the adapter-registry scaffold this proposal extends.
- Existing book taxonomy under `content/podcast/library/`: books, articles, documents, lectures, interviews, letters — already accommodates non-book sources at the directory level; the pipeline doesn't yet behave differently per category.

---

## Proposed change

Four additions, ordered smallest to largest. No code changes to `scripts/podcast/` from this Mac — all code-level work is the primary-Mac assistant's job once this proposal is integrated.

### Change A — Per-book concept-glossary artifact (convention + minor handbook delta)

Add a new optional book-level file:

`content/podcast/library/<category>/<slug>/_system/concept-glossary.md`

Frontmatter:

```yaml
schema_version: 1
book_slug: <slug>
generated_by: <human | claude-p | extract>
generated_at: <ISO ts>
purpose: |
  Per-book inventory of technical vocabulary that the listener must
  acquire across episodes. Distinct from pronunciation.md (which is
  phonetic) and mangle-map.md (which is TTS-fix). This file is
  CONCEPTUAL: a one-sentence listener-gloss per term.
```

Body: bulleted terms grouped by domain.

```markdown
## Cosmology
- **natiq** (ناطق): a "speaker prophet" who inaugurates a cosmological cycle.
- **asas** (أساس): the "foundation" — the figure who carries the inner meaning.
- **hujja** (حجة): "proof" — the senior teacher under the imam.

## Hermeneutics
- **ta'wil** (تأويل): allegorical interpretation returning a thing to its first principle.
- **zahir** (ظاهر): the outer/manifest meaning of scripture.
- **batin** (باطن): the inner/hidden meaning — what ta'wil discloses.
```

Read by the per-episode framing author during Phase 11 (per-chapter framing build). Ep1 introduces 8–10 foundational terms; Ep2+ references "see glossary terms already established in Ep1" rather than re-defining.

**Handbook delta:** append a §"Per-book concept glossary" section to `book-dir-layout.md` (≤30 lines). The challenger's Category P (chapter-set design quality) gets one new check: if `concept-glossary.md` exists, every framing must reference ≥1 glossary term OR declare zero-new-vocab.

### Change B — "Recursive scaffold" beat-arc pattern (handbook delta only)

Append Pattern 5 to `episode-architecture.md`:

```markdown
### Pattern 5 — Recursive Scaffold (across-episode pattern)
For sources whose later chapters/cycles REPEAT a structure introduced in
chapter 1 (Ismaili natiq cycles, the 12 imams, Sufi maqamat sequences,
Mishnah tractate parallels). One episode (typically Ep1) does the full
template explanation. Subsequent episodes lean on it.

  - Ep1 beats: full template walk-through (Pattern 1, 2, or 4 internally)
  - Ep2–N beat 1: "Remember the pattern from Ep1 — here it is again with [X]"
  - Ep2–N middle beats: only the *deltas* from the template
  - Final episode: template's terminus OR a deliberate absence
    (e.g., Asaas's unwritten 7th)

Layered ON a per-episode beat pattern. Declare in `_system/registry.md`
with `series_pattern: recursive_scaffold`.

The discussion-spine author (Phase 07-chapter-design + 11-per-chapter)
reads `series_pattern` and emits Ep2+ spines that omit the template re-teach.
Purely additive — does not invalidate any existing spine.
```

### Change C — Asaas Al-Taveel preflight artifact + recommended series-plan preset

Before P9.5 fires, drop a chapter-rationale stub at:

`content/drafts/asaas-al-taveel/_system/source/text/chapters-rationale.md`

Normally a Phase 0d output; for Asaas the section map already exists (read-only product of this session — see appendix). Pre-seeding gives the orchestrator ground truth at Phase 0d and gives the operator a concrete object at the Phase 09-series-plan gate.

**Recommended series-plan preset (operator confirms at Phase 09):**

| EP | Title | Source chapters mapped | Mode |
|---|---|---|---|
| EP01 | The Hidden Code (frame + Adam as template) | Editor's intro + Ch 1 (Adam, pp. 33–75) | Mentor+Student; Pattern 1 (Pressure Build); introduces 8–10 glossary terms |
| EP02 | Floods and Fathers | Ch 2 + Ch 3 (Nuh + Ibrahim, pp. 76–178) | Mentor+Student; Pattern 4; recursive-scaffold reuse |
| EP03 | Moses and the Pharaoh's Court | Ch 4 part 1 (Musa + Yusha, pp. 179–245 approx.) | Mentor+Student; recursive-scaffold |
| EP04 | The Davidic Kings and the Whale | Ch 4 part 2 (Dawud/Sulayman/Yunus/Yahya, pp. 246–298) | Mentor+Student; recursive-scaffold |
| EP05 | Christ Without a Father, Muhammad as Seal | Ch 5 + Ch 6 (Isa + Muhammad, pp. 299–368) | Mentor+Student; recursive-scaffold; introduces 2–3 closure terms |
| EP06 | The Seventh Silence | Editor's note p. 21 + unwritten Qa'im chapter | Pattern 2 (Lens Rotation); shortest (~30 min target) |

Six episodes total. Long-form tier (10–14 beats/episode), ~3–4 hour total runtime. A glossary stub (~25 entries) accompanies the chapter-rationale stub at the same commit.

### Change D — Manifest-driven multi-source ingestion (extends P17.1 forward from W5)

Operator ask (verbatim, 2026-05-19): *"Use the podcast agent on a folder containing a bunch of random documents and ask for it to be turned into a podcast. I will define the details of the order but it should still go through the same refinement enrichment process as in the plan being developed."*

**Evaluation:** This is exactly what P17.1 (Source-adapter registry) was scaffolded for — currently W5-deferred with `promote_when: "first non-Arabic-PDF source arrives OR user explicitly opts in"`. The operator has now explicitly opted in. The architectural cost is small if the abstraction is right; large if it becomes a parallel pipeline. **Recommendation: treat folder-ingestion as the general case and single-book-ingestion as its 1-document special case. The pipeline never forks.**

The unifying abstraction is a manifest file the operator drops into `_system/source/manifest.yml` before Phase 0a fires. Schema:

```yaml
schema_version: 1
bundle_kind: folder | single_pdf | mixed
voice_mode: single_author | curated_anthology | editor_voice
title: "<Bundle Title>"
author_or_curator: "<Asif>"
documents:
  - path: source/file1.pdf
    role: intro | chapter | appendix | sidebar | epigraph
    order: 1
    chapter_slug: <kebab-case>     # only when role: chapter
    adapter: arabic_pdf | english_pdf | markdown | transcript | auto
  - path: source/file2.txt
    role: chapter
    order: 2
    ...
```

The manifest is operator-authored — Phase 0a does NOT auto-derive ordering. Pipeline behavior:

- **Phase 0a (normalization)**: each entry passes through its adapter independently; output `_system/source/text/<order>-<adapter-name>-normalized.md` per file.
- **Phase 0a continued**: a manifest-merge step concatenates per-file normalized outputs in order into a single `normalized.md`, preserving doc boundaries as comment markers (`<!-- DOC: file1.pdf | role: chapter -->`) for downstream phases to honor.
- **Phase 0d (chapter segmentation)**: respects manifest `chapter_slug` declarations — does NOT re-segment within a doc that has `role: chapter` and an explicit slug. Falls back to auto-segmentation only when chapter boundaries are missing from manifest.
- **Phase 07 (chapter design) + Phase 11 (per-chapter)**: read `voice_mode` from manifest. For `curated_anthology`, `meta-prose-tells` and `enrichment-whitelist` apply per-document, not bundle-wide. For `editor_voice`, an explicit editor persona is layered into framing.
- **Phase 09 (series-plan operator gate)**: shows the parsed manifest alongside the auto-derived chapter list; operator confirms or amends.

This makes:

- **Asaas Al-Taveel** a 1-doc manifest with `bundle_kind: single_pdf`, `voice_mode: single_author`, one doc entry pointing at the source PDF, plus `chapters-rationale.md` (Change C) supplying the chapter slugs/page-ranges.
- **A folder bundle** an N-doc manifest with `bundle_kind: folder`, operator-declared ordering, per-doc `role` tags.
- **Existing single-book runs** (kitab-al-riyad et al.) continue working — they get a 1-doc manifest auto-scaffolded by `scaffold_book.py` if absent (backward-compat shim, NOT a forked path).

**Adapter coverage required for Change D launch:**

- `arabic_pdf.py` (P17.1 already designs this)
- `english_pdf.py` (new; thin wrapper over Azure OCR with language hint = `en`)
- `markdown.py` (new; trivial — read file, normalize whitespace, no OCR)
- `transcript.py` (new; expects timestamped transcript format, strips timestamps, preserves speaker tags)
- `auto.py` (new; detects format by extension + first-bytes sniff)

`docx.py`, `html.py`, `image.py` (single-page) — deferred to subsequent adapter PRs, each a ~3-file landing per P17.1's existing walk-through test.

---

## Plan deltas

### Phases — modify

- **P9.5 acceptance row** (in `acceptance-criteria.md` Wave 3 group): add three sub-rows:
  - 📊 P9.5.pre1 — `content/drafts/asaas-al-taveel/_system/source/text/chapters-rationale.md` exists with the 6-chapter natiq map BEFORE `run_wave.py 3 --book asaas-al-taveel` fires
  - 📊 P9.5.pre2 — `content/drafts/asaas-al-taveel/_system/concept-glossary.md` exists with ≥20 glossary entries BEFORE the run fires
  - 📊 P9.5.pre3 — series-plan operator gate (Phase 09) reviewed against the proposed 6-episode preset (operator confirms or amends)

- **P17.1 acceptance rows**: update `promote_when` from "first non-Arabic-PDF source arrives OR user explicitly opts in" to "PROMOTED 2026-05-19 — operator opted in for folder-ingestion + Asaas chapter-map preflight". Existing P17.1 rows remain valid (Protocol conformance + Arabic PDF adapter + boundary check + cost-ledger). Add Change-D extension rows under a new `P17.1.ext` sub-group:

  - P17.1.ext.1 ✅ Manifest schema documented in `book-dir-layout.md`; YAML validator at `scripts/podcast/adapters/_manifest.py`
  - P17.1.ext.2 ✅ Four new adapters (`english_pdf`, `markdown`, `transcript`, `auto`) implement `SourceAdapter` Protocol; parity tests under `tests/adapters/`
  - P17.1.ext.3 ✅ `scaffold_book.py` auto-generates 1-doc manifest stub for new single-source books (backward-compat shim); `scaffold_bundle.py` auto-generates N-doc manifest stub from a folder walk
  - P17.1.ext.4 ✅ `orchestrate_book.py` Phase 0a honors manifest ordering + adapter dispatch; produces concatenated `normalized.md` with doc-boundary comment markers
  - P17.1.ext.5 ✅ Phase 0d respects manifest `chapter_slug` declarations; falls back to auto-segmentation only when manifest is silent
  - P17.1.ext.6 ✅ `voice_mode` field consumed by `_authoring.py` Phase 11; default = `single_author` preserves existing behavior
  - 📊 P17.1.ext.7 — Folder-bundle fixture under `_learning/fixtures/folder_bundle/three-articles/` runs clean through Phase 0a → Phase 11; produces episode txt with cross-doc references intact
  - P17.1.ext.8 ✅ Single-PDF parity: existing W3 corpus books produce byte-identical `refined-english.md` + chapter txt with the auto-scaffolded 1-doc manifest (golden frozen at tiny-book + Ayyuhal Walad)

### Phases — add

- **P4.9** (sub-row under P4): `_system/concept-glossary.md` schema documented in `book-dir-layout.md`; one-line example in the table
- **P-NEW-1** (small enough to fold into W2 polish rather than new phase): append Pattern 5 to `episode-architecture.md` and document `series_pattern` key in `book-dir-layout.md`'s registry section
- **P-NEW-3** (handbook delta supporting Change D `voice_mode`): append §"Voice mode override" (~40 lines) to `two-host-framing.md` under the existing "Override Patterns" section; declare the three modes and what each does at Phase 11 framing time

### Phases — remove

None.

### Phases — re-order

P17.1 promotion: move from W5 (deferred, terminal wave) to a new sub-wave **W3.5** between W3 (Corpus Validation) and W4 (Control Plane). Rationale: the W3 corpus validates Arabic-PDF ingestion (P9.1–P9.7); W3.5 generalizes ingestion to multi-source + non-Arabic-PDF formats; W4 then runs control-plane on the generalized pipeline. Schedule intent: kicked off ONLY after P9.5 (Asaas) ships clean — Asaas validates the `chapters-rationale.md` / manifest preflight convention before scaling to N-doc. Wave acceptance: all P17.1 + P17.1.ext rows checked.

**Alternative if W3.5 is too granular**: fold P17.1 + extensions into W4 as W4.0 (pre-mutation generalization). Operator's call on wave-numbering aesthetics; the work content is identical either way.

> **Integration decision (primary-Mac assistant, 2026-05-19):** Chose to keep P17.1 in W5 with `promote_when` updated to indicate the trigger has fired, rather than restructuring wave membership. This minimizes disruption to `run_wave.py` dispatch numbering (which keys on `run_wave.py 1..5`). The execution-order intent (after P9.5, before W4 mutation-API work) is preserved via the textual `promote_when` block.

---

## Risks + back-out

- **Risk: per-book glossary becomes another half-completed convention** — like `enrichment-whitelist.md` drifts away from real Tier-1 corpus. **Mitigation:** the convention is optional (`book-dir-layout.md` says MAY add, NEVER contradict); when absent, episodes run as today. The new challenger check (CH-NEW) only fires WHEN the file exists.

- **Risk: Pattern 5 (recursive scaffold) misused as a license to under-explain** — episodes feel like sequels you can't enter cold. **Mitigation:** Pattern 5 requires Ep2+ to open with a 30-sec "remember the pattern" recap; the fixture asserts the recap is present.

- **Risk: cost overrun on long-form tier (25 min+) on a 416 pp. book** balloons P5/P7/P11 token spend. **Mitigation:** P6 cost-cap regime ($50 hard cap) is unchanged; orchestrator halts before Phase 07 if breached.

- **Risk: running kitab-al-riyad's Phase 0f gate fires before operator internalizes Pattern 5** — operator picks the wrong pattern for kitab-al-riyad too. **Mitigation:** this proposal does NOT touch kitab-al-riyad's series-plan; the four existing beat patterns remain valid defaults; Pattern 5 is opt-in via `series_pattern: recursive_scaffold`.

- **Risk (Change D): cross-author voice homogenization in folder bundles** — the existing pipeline assumes one author voice per book (`meta-prose-tells.md`, `enrichment-whitelist.md` are per-book). A `bundle_kind: folder` mixing 5 authors will produce hosts who paper over real voice discontinuities, or refinement that flattens distinct voices into one register. **This is the single biggest risk across the arc.** **Mitigation:** the `voice_mode` manifest field — `single_author` (default; current behavior preserved), `curated_anthology` (suppress meta-prose homogenization across doc boundaries; declare distinct voices in framing), `editor_voice` (explicit editor persona narrates the bundle). ~40 lines under `two-host-framing.md`'s "Override Patterns" section. One branch in `_authoring.py` Phase 11; no new agents.

- **Risk (Change D): operator-authored manifests drift, get stale, or are silently wrong** — operator declares 5 docs in order [3,1,2,5,4] but actual desired order is [1,2,3,4,5]; pipeline runs to completion before operator notices the mis-ordering at episode-listen time. **Mitigation:** Phase 0a emits a `manifest-check.md` artifact summarizing the parsed manifest (doc count, total word count, per-doc role, ordering), and the Phase 09 operator gate displays this alongside the chapter list. Bad ordering is caught before Phase 11 spend.

- **Risk (Change D): scope creep** — adapter registry grows organically into a "support every format" wishlist (docx, html, epub, image, audio, video). **Mitigation:** hold the line at 5 adapters for Change D launch (`arabic_pdf`, `english_pdf`, `markdown`, `transcript`, `auto`). Each subsequent adapter is its own ~3-file PR per P17.1's existing walk-through test. No batch landings.

- **Risk (Change D): cost ballooning on heterogeneous bundles** — a folder with one 600 pp. PDF + 12 small markdown files runs full Azure OCR + claude -p refinement on the PDF AND processes 12 small files. **Mitigation:** P6's cost-eta (P10.1) pre-flight check extends to multi-doc; total bundle cost predicted before Phase 0a fires; `--cost-cap-soft` / `--cost-cap-hard` enforced on bundle totals.

- **Back-out:** every change is a file addition under `_system/`, a handbook append, or a new `scripts/podcast/adapters/<x>.py` module. `git revert` on the proposal-landing commit(s); no migrations (manifest is opt-in for existing books — absence triggers the backward-compat 1-doc auto-scaffold); no `schema_version` bump on `state.json`; no in-flight book state affected.

---

## Test surface

### Existing tests that already cover this

- **P2.5 `test_learning_loop.py`** — catches regressions when a new fixture under `_learning/fixtures/phase_prompts/07-chapter-design/recursive-scaffold/` is added
- **P2.6 `test_refinement_determinism.py`** — unchanged; this proposal doesn't touch the refinement prompt
- **P4.4b Loop N fixture** (`loop_n_numeric_invented`) — already covers invented enumerations; directly relevant to Asaas's 7-natiq + 12-hujja numerology. P9.gate "Loop N clean" enforces it.
- **P17.1's `tests/adapters/test_registry.py`** — already specified; covers Protocol conformance + dispatch resolution + UnsupportedSourceError handling
- **P17.1's `tests/adapters/test_arabic_pdf.py`** — golden-fixture parity for the existing Arabic PDF adapter

### New tests (Changes A/B/C)

- `scripts/podcast/tests/e2e/test_concept_glossary.py` — if `_system/concept-glossary.md` exists, every `episode-drafts/EP##-*/00-framing.md` references a glossary slug OR contains the literal "no new technical vocabulary in this episode". Mirror parity with `test_phase_prompts.py` (P19.2).
- `_learning/fixtures/phase_prompts/07-chapter-design/recursive-scaffold/` — three sub-fixtures: golden (passes), missing-recap (fails loud), wrong-pattern-declared (fails loud).
- Challenger Category P sub-check — extend `_rules.py` to emit a P1-severity finding when `concept-glossary.md` exists and a framing omits both glossary reference and zero-vocab declaration (tracked as P-NEW-2 acceptance row).

### New tests (Change D)

- `scripts/podcast/tests/adapters/test_manifest_validator.py` — rejects unknown `role` values, enforces monotonic `order`, requires `chapter_slug` when `role: chapter`, rejects path traversal in `path` field. Parity with `tests/adapters/test_registry.py`.
- `scripts/podcast/tests/e2e/test_folder_bundle.py` — N-file folder ingestion → `normalized.md` → episode txt. 3-doc synthetic fixture at `tests/e2e/fixtures/folder-bundle/` (one markdown, one transcript, one PDF). Asserts: doc-boundary markers preserved in `normalized.md`; `chapter_slug` from manifest used verbatim; episode txt cross-references work.
- `scripts/podcast/tests/e2e/test_single_pdf_manifest_parity.py` — parity test: a single-PDF run with auto-scaffolded 1-doc manifest produces byte-identical `refined-english.md` and chapter txt to the same run pre-Change-D (golden frozen at tiny-book + Ayyuhal Walad dry-run). **This is the backward-compat assurance** — landing Change D MUST NOT regress any existing book's output.
- `scripts/podcast/tests/adapters/test_voice_mode.py` — `voice_mode` flows from manifest into `_authoring.py` Phase 11 prompt context. Three fixtures (`single_author` = current behavior; `curated_anthology` = per-doc meta-prose; `editor_voice` = explicit editor persona). Asserts the prompt contains the appropriate framing snippet for each mode.
- `scripts/podcast/tests/adapters/test_english_pdf.py` / `test_markdown.py` / `test_transcript.py` / `test_auto.py` — one per new adapter; golden-fixture parity per P17.1's existing pattern.

---

## Integration order

**This proposal (Changes A + B + C) can land BEFORE the current kitab-al-riyad orchestrator hits its Phase 0f gate** (~2.5 hours from status update). Justification:

1. Running orchestrator's writes are scoped to `content/drafts/kitab-al-riyad/_system/` — disjoint from this proposal's touch surface.
2. Boundary check is read-only to the orchestrator and won't be confused by additions outside its scope.
3. Handbook entries (A + B) are appends. Asaas preflight (C) creates files under a directory the running orchestrator does not touch.
4. `_phases.py` not modified; no `schema_version` bump; no migration.
5. kitab-al-riyad's Phase 09 decision unaffected — 4 existing patterns remain valid defaults; Pattern 5 is opt-in via `series_pattern`.

**Recommended landing window for A + B + C:** next ~2 hours, on `feat/podcast-w1-foundation`. Single commit ideally; if split: handbook deltas (A + B) first, Asaas preflight artifacts (C) second.

> **Actual integration outcome (primary-Mac assistant, 2026-05-19):** Landed as a single commit `efdf323` on `feat/podcast-w1-foundation`. Included Changes A + B + C plus operator-added Changes E (P21 — cross-book learning store) and F (P22 — operator-review gate after Phase 0a/0b). Change D scoped under P17.1's `extension_change_d` block for landing AFTER P9.5.

**What MUST wait until after kitab-al-riyad ships:** any code edit to `scripts/podcast/`, P8.6 phase rename, any change under `content/drafts/kitab-al-riyad/`. This proposal's A+B+C make none.

**What MUST wait until just before P9.5 fires** (i.e. the W3 corpus invocation specifically for Asaas):

- A walk-through with the operator of the proposed 6-episode preset at the Phase 09-series-plan gate. The preset is a recommendation, not an enforcement.

**Change D sequencing (P17.1 promotion + manifest + multi-adapter):**

- Land **AFTER P9.5 (Asaas) ships clean.** Asaas validates the `chapters-rationale.md` / manifest preflight convention on a single-source book; promoting P17.1 BEFORE Asaas runs would bundle two unproven changes into one debug surface.
- Wave home: W3.5 (new sub-wave between W3 and W4) or W4.0 (folded into W4 as a pre-mutation generalization step). Operator decides numbering aesthetics; work content is identical either way.
- Order within W3.5: (1) manifest schema + validator + handbook delta; (2) `english_pdf` + `markdown` adapters (the cheap two — no Azure dependency for markdown, light wrapper for english_pdf); (3) `scaffold_book.py` backward-compat shim + `scaffold_bundle.py` new helper; (4) folder-bundle E2E test fixture; (5) `transcript` + `auto` adapters; (6) `voice_mode` wiring in `_authoring.py` Phase 11.
- Single-PDF parity is the ship gate: `test_single_pdf_manifest_parity.py` MUST pass on every existing W3 corpus book's golden output. If it fails on any book, Change D does NOT land; the backward-compat shim is broken.
- Folder-bundle validation book: pick a 3-document operator-curated bundle (operator's choice — could be a folder of related articles, conference transcripts + slides + paper, etc.) as the first folder-mode book and run it through W3.5 as the validation case. This is the folder-equivalent of Ayyuhal Walad's role in W3 (the tiniest corpus member).

---

## Holistic recommendation — three asks, one capability

The operator's three asks form an arc that resolves cleanly to one capability rather than three features.

| Ask | The lever | Plan home |
|---|---|---|
| Asaas section map | manifest with `bundle_kind: single_pdf` + `chapters-rationale.md` preflight | Change C |
| Teaching density (Mentor+Student + recursive-scaffold) | persona override (existing) + Pattern 5 (new) + concept-glossary (new) | Changes A + B |
| Folder ingestion | manifest with `bundle_kind: folder` + adapter registry promotion + `voice_mode` | Change D + P17.1 promotion |

The unifying abstraction is the manifest at `_system/source/manifest.yml`. Operator-authored, declarative, replaces nothing: existing book runs auto-generate a 1-doc manifest; downstream phases (refinement, enrichment, chapter design, framing) read manifest fields to specialize behavior. The pipeline never forks. The book case is just "1-document bundle"; the folder case is "N-document bundle"; the Asaas case is "1-document bundle with pre-seeded chapter map."

### Sequencing recommendation

1. **Now** (next ~2 hours, before kitab-al-riyad Phase 0f gate) — land Changes A + B + C. Additive, safe, no code changes; gives the operator a concrete decision-object at the Phase 09 gate when P9.5 eventually fires.
2. **Run P9.5 (Asaas)** — validates the chapter-rationale / manifest preflight convention on a single-source book before scaling to N-doc.
3. **Promote P17.1 forward to W3.5 (or W4.0)**. Design exists; this is "ship it" not "design it."
4. **Land Change D** — extends P17.1 with the manifest schema + 4 additional adapters. Backward-compat shim auto-scaffolds 1-doc manifests for existing single-source books.
5. **Run the first folder-mode validation book** — operator picks the 3-doc bundle; W3.5 ships when that bundle produces a clean episode set AND the single-PDF parity test stays green across the W3 corpus.

### The single biggest risk across the arc

**Cross-author voice homogenization in folder bundles.** The current pipeline assumes one author voice per book. Folder bundles violate this. Mitigation is the `voice_mode` manifest field — declare upfront whether the bundle has one voice (default), is a curated anthology of distinct voices, or is presented through an explicit editor narration. Handbook addition is small (~40 lines under `two-host-framing.md`); implementation cost is one branch in `_authoring.py` Phase 11 — no new agents.

### What I'd say no to (if asked)

- A "smart" auto-folder mode that doesn't require an operator manifest. The operator's stated workflow is "I will define the order" — that's the manifest. Auto-ordering by filename / created-at / heuristic is a footgun and invites the system to choose the wrong order silently. **Force the manifest.**
- Per-document customize prompts. The customize prompt is per-episode, not per-source-doc. Multi-doc episodes share one prompt that names the docs explicitly.
- A new agent or skill. Everything fits in the existing podcast skill + handbook + adapter registry. Spawning a "folder-podcast" agent would fragment the pipeline.
- Pre-Change-D adoption of P17.1 to "unblock other formats." If `english_pdf` and `markdown` adapters land before Asaas validates the preflight convention, two unproven changes ship together; debugging becomes ambiguous. **Hold the line.**
- A "teaching mode" boolean as a third format alongside Deep Dive / Debate. Teaching density is a persona override (Mentor+Student) + a beat pattern (Recursive Scaffold) + a glossary artifact. Three small additions, not a new mode axis.

### What I'd flag for operator confirmation before any of this lands

| Question | Recommendation | Decision (2026-05-19) |
|---|---|---|
| Manifest format: YAML, JSON, or markdown? | YAML — same family as registry.md and chapter contracts | ✅ YAML |
| Manifest location: `_system/source/manifest.yml`, `_system/manifest.yml`, or somewhere else? | `_system/source/manifest.yml` — co-located with raw sources | ✅ `_system/source/manifest.yml` |
| Manifest authoring: hand-authored only, or seeded via a `scaffold_bundle.py` helper? | Both. `scaffold_bundle.py` auto-generates a stub by walking a folder; operator edits before Phase 0a. Hand-authoring also works. | ✅ Both |
| Folder-mode validation book: which 3-doc bundle becomes the first folder-mode validation case? | Operator's choice | Deferred — pick when D lands |
| Wave numbering: W3.5 vs. W4.0 for P17.1 promotion? | No functional difference; aesthetics only. | W4.0 originally chosen; ultimately P17.1 kept in W5 with `promote_when` triggered, to avoid disrupting `run_wave.py` numbering |
| Asaas episode count: hold at 6 (current recommendation), compress to 5, or expand to 7? | 6. Tradeoffs in original Asaas response. | ✅ 6 |

---

## Operator-added extensions integrated alongside the Air proposal (2026-05-19)

Two additional changes emerged from the primary-Mac conversation as the integration was happening:

### Change E — Cross-book learning store (now P21 in W5)

**Operator motivation (verbatim 2026-05-19):** "The cognitive and language load on the LLM should keep reducing drastically from each run. Once you learn patterns and they're stored in some fashion in a local database, it should work. Remember I am the ONLY one using this."

The store is a SQLite + JSONL audit log under `content/podcast/_learning/` that accumulates vocabulary terms, chapter-pattern templates, per-author style profiles, and operator preferences across books. Each phase looks up known terms/patterns BEFORE calling `claude -p`; cache hits skip the LLM entirely with `method=cache-hit` cost-ledger row. Modeled time savings: book 2 ~20-30% faster, book 5 ~40-50% faster, book 10 ~50-60% faster (asymptotic). Phonetic-pass cache-hit rate approaches 80% by book 5.

`promote_when: ≥3 W3 books shipped`. See P21 in `podcast-plan.yaml` for the full schema and acceptance criteria.

### Change F — Operator-review gate after Phase 0b (now P22 in W2)

**Operator motivation (verbatim 2026-05-19):** *"Can I get a full transcription of the book in English since it's being processed entirely anyways? Without that this effort is not worth much. Once you have the full transcript (in English from whatever language) then you should be apply all refinements. You should break for my review and comment based updates before starting the heavy processing cycles."*

The orchestrator halts at the first phase that produces a complete readable English artifact, surfaces it at the book directory top level as `english-transcript.md`, scaffolds an `operator-review.md` review template, and waits for `--approve-transcript`. Halt-point heuristic adapts to source type:

- **Arabic-scanned PDF** (KaR, Asaas, Raahat al-Aqal): halt AFTER Phase 0b. Azure raw OCR (Phase 0a output) is unreadable junk — proper names mangled, sentences scrambled. Phase 0b produces the actual readable English. Halt here.
- **English text-layer PDF**: halt AFTER Phase 0a. Phase 0a produces clean English directly via PDF text extraction.
- **Markdown / transcript source**: halt AFTER Phase 0a. Text is already clean.

Operator's ~5 minutes of review attention happens BEFORE the heavy LLM cycles (phonetic pass, chapter design, enrichment, per-chapter framing), catching OCR/translation issues at the cheapest possible point. The operator's comments are injected into Phase 0c+ prompts as a `<operator-review>` XML block.

`promote_when: PROMOTED 2026-05-19 — operator opted in`. See P22 in `podcast-plan.yaml` for the full halt-point heuristic, spec, and acceptance criteria.

**First manual exercise of P22 workflow (2026-05-19):** KaR orchestrator manually halted at the Phase 0b → 0c boundary via SIGINT + SIGTERM. `english-transcript.md` + `operator-review.md` scaffolded under `content/drafts/kitab-al-riyad/`. Operator review in progress at time of this document being written. Manual halt is the precursor; P22 code lands later to automate.

---

## Appendix — Asaas Al-Taveel section map (source intelligence to seed into chapters-rationale.md)

**Confidence HIGH.** Source: editor's own TOC at PDF pp. 369–372, cross-verified against body الفصل الأول..السادس headers at pp. 76, 107, 165, 315 and names-index clusters at pp. 402–408. Editor's note on p. 21: 7th chapter (Qa'im) deliberately not written.

| # | Natiq | Page range (printed = PDF) | Page count | Intermediate prophets / figures covered |
|---|---|---|---:|---|
| 1 | Adam (آدم) | 33–75 | 43 | Iblis, Habil & Qabil, Shith, Idris; handover to Nuh |
| 2 | Nuh (نوح) | 76–106 | 31 | Hud, Saleh |
| 3 | Ibrahim (ابراهيم) | 107–178 | 72 | Lut, Isma'il, Ishaq, Ya'qub, Yusuf, Ayyub, Shu'ayb |
| 4 | Musa (موسى) | 179–298 | 120 | Yusha' bin Nun, Fir'awn, Talut, Dawud, Sulayman, Yunus, Imran, Zakariya, Yahya |
| 5 | 'Isa (عيسى) | 299–314 | 16 | Maryam, Yusuf the Carpenter, Yahya as baptizer, Hawariyyun |
| 6 | Muhammad (محمد) | 315–368 | 54 | Bahira, Khadija, Abu Talib, 'Ali, Ghadir Khumm, Abu Bakr, 'Umar, 'Uthman, Battle of the Camel |
| 7 | Qa'im (القائم المنتظر) | — | 0 — never written | Editor's note p. 21: deliberately omitted |

Front/back matter: PDF 1–4 cover+blanks · printed 5–24 editor's intro · printed 25–32 author's intro · printed 395–408 indexes · PDF 409–416 French intro (RTL).

---

## Cross-references

- Plan: [`../podcast-plan.yaml`](../podcast-plan.yaml) — see P9.5, P17.1, P21, P22
- Acceptance: [`../acceptance-criteria.md`](../acceptance-criteria.md) — see P9.5.pre1-3, P17.1.ext.1-8, P21 group, P22 group, P4.9
- Asaas preflight artifacts: [`../../../content/drafts/asaas-al-taveel/`](../../../content/drafts/asaas-al-taveel/) (on the same branch `feat/podcast-w1-foundation`)
- KaR halt artifacts: `content/drafts/kitab-al-riyad/{english-transcript,operator-review}.md` on branch `book/kitab-al-riyad`
