# Air Audit — Redesign Integration Review

**Auditor:** Claude Opus 4.7 (parallel-Mac session)
**Audit date:** 2026-05-19
**Branch reviewed:** `feat/podcast-w1-foundation` @ `7a5a50b`
**Scope:** confirm faithful integration of the 2026-05-19 Air redesign proposal (Changes A/B/C/D) plus operator-added Changes E/F. Read-only.

---

## What's faithful

**Change A — per-book concept-glossary** [book-dir-layout.md:93-135](content/podcast/.skill/handbook/book-dir-layout.md#L93-L135)

- Tree entry at line 35 lists `concept-glossary.md ← (optional) per-book conceptual term inventory`. ✓
- Ownership-table row added at line 72 (owner = the book, read by Phase 11 + challenger Category P, written by author/claude-p/extract). ✓
- New §"Per-book concept glossary" section with: distinction table vs. `pronunciation.md` / `mangle-map.md`, the schema block (frontmatter: schema_version, book_slug, generated_by, generated_at, purpose), example body shape with Cosmology/Hermeneutics sub-headings, and the explicit opt-in clause: *"When the file is absent, episodes run as today — no challenger check fires."* All verbatim against the proposal. ✓

**Change B — Pattern 5 Recursive Scaffold** [episode-architecture.md:64-77](content/podcast/.skill/handbook/episode-architecture.md#L64-L77)

- Pattern 5 sits cleanly between Pattern 4 and the "Opening hook" section. ✓
- Beat structure preserved: Ep1 = full template walk-through; Ep2–N beat 1 = 30-sec recap (REQUIRED); middle beats = deltas only; final episode = terminus OR deliberate absence with explicit "Asaas al-Taʾwīl's unwritten 7th chapter on the awaited Qāʾim" callout. ✓
- "Layered ON TOP OF a per-episode beat pattern" language preserved. ✓
- Failure-mode + fixtures clause present (`golden`, `missing-recap`, `wrong-pattern-declared`). ✓
- "Purely additive" / opt-in via `series_pattern: recursive_scaffold` registry key preserved. ✓

**Change C — Asaas preflight artifacts**

- [chapters-rationale.md](content/podcast/library/books/asaas-al-taveel/_system/source/text/chapters-rationale.md): all six natiq page ranges match the appendix table exactly (Adam 33–75, Nūḥ 76–106, Ibrāhīm 107–178, Mūsā 179–298, ʿĪsā 299–314, Muḥammad 315–368, Qāʾim unwritten). Editor's note p. 21 cited. The "Why Phase 0d does NOT auto-re-segment Asaas" section makes the Pattern-5-reuse argument crisply. ✓
- 6-episode preset preserved verbatim (EP01 "The Hidden Code" → EP06 "The Seventh Silence"). Mūsā split across EP03/EP04 with same Yūshaʿ → Yūnus chapter-4 sub-cycle reasoning. ✓
- "Provenance" footer correctly logs MacBook Air authorship, 2026-05-19, multimodal PDF read-only pass. ✓
- [concept-glossary.md](content/podcast/library/books/asaas-al-taveel/_system/concept-glossary.md): 29 entries across 7 domains (Cosmology 7 / Hermeneutics 6 / Neoplatonic 4 / Doctrinal 5 / Honorific 3 / Editorial 2 / Closure 2). Above the ≥20 floor; matches the "~25-30" estimate.
- All proposal-named foundational terms present: nāṭiq, asās, ḥujja, taʾwīl, ẓāhir, bāṭin, mubdaʿ, ʿaql awwal, nafs kulliyya. ✓
- Closure terms present: qāʾim, ghayba, intiẓār + the operator-asked al-sābiʿ and sukūt al-muʾallif. ✓
- Hamza on Qāʾim rendered consistently as `qāʾim` (ʾ glyph) in both files. ✓

**Change D — manifest-driven multi-source ingestion** [podcast-plan.yaml:1984-2160](_workspace/plan/podcast-plan.yaml#L1984-L2160)

- P17.1 `promote_when` updated to PROMOTED-2026-05-19 with both triggers (folder-bundle + Asaas chapter-map preflight) and the "after P9.5 ships clean" sequencing constraint preserved as text. Original trigger preserved in "now superseded" sub-clause for audit trail. ✓
- `extension_change_d` block carries the full manifest schema (schema_version / bundle_kind / voice_mode / documents[]) verbatim from the proposal. ✓
- All 8 ext_acceptance rows present and ordered correctly (.ext.1 manifest validator → .ext.8 single-PDF parity). ✓
- voice_mode risk text imports the proposal's "single biggest risk" framing. ✓
- Files-new list includes all five new adapters + manifest validator + scaffold_bundle.py + parity tests. ✓
- [Voice mode override in two-host-framing.md:45-61](content/podcast/.skill/handbook/two-host-framing.md#L45-L61) — three modes table (single_author / curated_anthology / editor_voice) with when-to-use and at-Phase-11-framing columns. Failure-mode section + default-behavior backward-compat clause present. ✓

**Operator extension E — P21 cross-book learning store** [podcast-plan.yaml:2418-2503](_workspace/plan/podcast-plan.yaml#L2418-L2503)

- `promote_when: ≥3 W3 books shipped` with operator's verbatim motivation quoted. ✓
- SQLite + JSONL audit-log pattern (rebuildable .sqlite from .jsonl) matches the operator's description. ✓
- Acceptance row "cache-hit method=cache-hit ledger row" matches the modelled time savings narrative. ✓
- Goodhart guard via `operator_locked=true` present in schema + acceptance. ✓
- **Architecturally compatible with Change A**: the per-book `concept-glossary.md` is the natural seed corpus for `vocabulary.sqlite` (terms.first_seen_book column fits exactly). ✓

**Operator extension F — P22 transcript-review gate** [podcast-plan.yaml:2292-2416](_workspace/plan/podcast-plan.yaml#L2292-L2416)

- Halt-point heuristic adapts to source type per spec (Arabic-scan → after 0b; English text-layer → after 0a; markdown → after 0a). ✓
- `<book>/english-transcript.md` + `<book>/operator-review.md` written at book top level, not buried under `_system/`. ✓
- `--approve-transcript` + `--skip-transcript-gate` flags both spec'd. ✓
- E2E test `test_operator_review_gate.py` scoped with Levenshtein-delta assertion. ✓
- Acceptance row 2416: "operator-review.md is NEVER overwritten by the orchestrator after initial scaffold" — correct preservation invariant. ✓
- **Architecturally compatible with Change D**: P22 halt-point detection at line 2356 explicitly reads "the source adapter (P17.1) and the source language" — clean dependency. ✓

**Proposal homing**

- [_workspace/plan/research/2026-05-19-redesign-proposal-from-air.md](_workspace/plan/research/2026-05-19-redesign-proposal-from-air.md) — registered in `meta.research_artifacts` (podcast-plan.yaml:84-96) with integrated_in commit + accurate A+B+C+D+E+F summary. ✓
- Integration-decision callouts within the proposal doc (Wave-numbering decision row, "Actual integration outcome" callout at line 282) accurately reflect what shipped. ✓

---

## What drifted (and is it OK)

**Drift 1 — P17.1 wave home: W3.5/W4.0 proposed, W5 chosen — NEEDS REVIEW**

The proposal recommended promoting P17.1 to a new sub-wave W3.5 (between Corpus Validation and Control Plane) or folding into W4.0. The integration kept P17.1 in W5 ([podcast-plan.yaml:267](_workspace/plan/podcast-plan.yaml#L267): `phases: [P17, P17.1, P18, P19, P20, P21]`) and documented the choice in the proposal doc's decision table as "minimizes disruption to `run_wave.py` numbering."

**Verdict: NEEDS REVIEW.** The proposal's "biggest single risk" — Change D landing before P9.5 (Asaas) validates the preflight convention — was supposed to be enforced by *wave gating*. With P17.1 in W5 dispatched via `python3 scripts/podcast/run_wave.py 5 --phase P17` (line 271), there is no machine-enforced barrier between "P9.5 shipped clean" and "Change D code lands." The `promote_when` text says "after P9.5 ships clean" but that's prose, not a check. → Recommend adding either (a) an acceptance row requiring `state.json[asaas-al-taveel].phase_status == complete` before `--phase P17` accepts a dispatch, or (b) explicit ordering guard in `run_wave.py 5` that refuses `--phase P17` until P9.5 done_signal is true.

**Drift 2 — P4.9 identifier scope-creep — OK**

The proposal scoped `P4.9` as a single sub-row under P4 for the `concept-glossary.md` schema doc. The integration broadened P4.9 to bundle all three handbook deltas under one identifier ([acceptance-criteria.md:322-324](_workspace/plan/acceptance-criteria.md#L322-L324)):

- P4.9 ✅ concept-glossary in book-dir-layout.md (Change A)
- P4.9 ✅ Pattern 5 + series_pattern (Change B)
- P4.9 ✅ Voice mode override in two-host-framing.md (Change D prep)

**Verdict: OK.** Reasonable bundling — all three are handbook-only deltas shipped in the same commit. Slight identifier hygiene cost (three rows share one ID) but functionally fine.

**Drift 3 — W2 done_signal does not name P22 — NEEDS REVIEW**

W2 phases list updated to `[P7, P8, P22]` at line 150, but `done_signal` at line 155 still reads "All P7–P8 acceptance rows checked; dashboard reachable…" — does not mention P22 explicitly. The W2 html_summary at lines 182-191 does describe P22, but the gate signal is the load-bearing string.

**Verdict: NEEDS REVIEW.** Minor wording bug — should read "All P7–P8 + P22 acceptance rows checked." If a future automated wave-completion check parses `done_signal`, it could mark W2 done before P22's rows are checked.

**Drift 4 — P22 acceptance row over-narrowly says "Phase 0c+ prompts" — NEEDS REVIEW**

[podcast-plan.yaml:2412](_workspace/plan/podcast-plan.yaml#L2412) reads "Downstream Phase 0c+ prompts include operator-review.md content as <operator-review> XML block when present." This is correct for the Arabic-scan halt-after-0b case (KaR, Asaas) but inaccurate for the English-text-layer/markdown halt-after-0a case — in those, the comments should influence Phase 0b refinement (which is the first downstream phase). The spec body at lines 2400-2403 says "Phase 0b refinement prompt" for the generic case, contradicting the acceptance row's "0c+" wording.

**Verdict: NEEDS REVIEW.** Tighten acceptance row to "downstream phases from the halt point onwards include the `<operator-review>` XML block" to cover both halt cases.

**Drift 5 — Asaas does not yet have `_system/registry.md` with `series_pattern: recursive_scaffold` — OK**

The chapters-rationale.md states "Series pattern: `recursive_scaffold` (declared in registry.md)" but registry.md doesn't exist yet for Asaas (only `_README.md`, `_system/concept-glossary.md`, `_system/source/text/chapters-rationale.md`). The proposal didn't scope registry.md as a preflight artifact — it expects `scaffold_book.py` to create the rest when P9.5 fires.

**Verdict: OK as a preflight scope decision**, but flag as operator action item: when `scaffold_book.py asaas-al-taveel` runs, the auto-scaffolded `_system/registry.md` MUST be hand-edited (or scaffold_book.py extended) to declare `series_pattern: recursive_scaffold` — otherwise Pattern 5's "discussion-spine author reads `series_pattern`" gating will silently default to None and Ep2–6 will re-teach the template.

**Drift 6 — Operator-added doctrinal/honorific/editorial glossary categories — OK**

The proposal's example body shape showed Cosmology + Hermeneutics. The shipped glossary added three additional categories: Doctrinal terms (daʿwa, dāʿī, walāya, ʿiṣma, takhalluq), Honorific & titular (PBUH, AS, amīr al-muʾminīn), Editorial/textual (muqaddima, fihris). All are well-formed listener-glosses and serve the book's vocabulary load.

**Verdict: OK — additive and sound.** Honorific entries are slightly outside the strict "conceptual" definition the schema gives ("listener-gloss per term, what it MEANS") since PBUH/AS are honorifics governed by R-HONORIFIC-ONCE, not new concepts. Either trim them or extend the schema body-shape to allow an "honorific" category. Low priority; not blocking.

---

## What's missing

1. **No machine-enforced gating between P9.5 ship-clean and Change-D code landing.** The proposal explicitly named this as the single sequencing risk. The promote_when text encodes intent; nothing encodes enforcement. See Drift 1.

2. **No `_system/registry.md` stub for Asaas with `series_pattern: recursive_scaffold` declared.** Without it, Pattern 5 is opt-in via a registry key that doesn't yet exist. See Drift 5.

3. **No test surface entry for the Pattern-5 fixtures.** The handbook says fixtures live at `_learning/fixtures/phase_prompts/07-chapter-design/recursive-scaffold/{golden,missing-recap,wrong-pattern-declared}/` but I see no acceptance row in either `podcast-plan.yaml` or `acceptance-criteria.md` requiring these fixtures to be created before Pattern 5 is considered shipped. The handbook entry currently is purely documentary.

4. **P21's `operator_locked` field has no upstream from per-book concept-glossary.** If a future Asaas glossary term promotes to `vocabulary.sqlite`, the operator should be able to mark it locked from the per-book glossary; the schema doesn't yet say how that promotion flows. Pre-promotion concern — not a launch blocker, but record it.

5. **No challenger Category P sub-check rule shipped yet for the "concept-glossary referenced ≥1 OR zero-vocab declared" assertion.** The handbook mentions it (book-dir-layout.md:103) but I found no challenger rule file or acceptance row tracking "ship the Category P concept-glossary check." → Acceptance row should exist under P9.5 or P4.9 saying "challenger Category P emits a finding when concept-glossary.md present AND a framing omits both glossary reference and zero-vocab declaration." (The proposal's P-NEW-2 row covered this; couldn't locate it in the integrated acceptance file.)

---

## Operator action items

1. **Decide the P17.1 sequencing enforcement.** Either (a) add an acceptance row to P17.1 requiring `state.json[asaas-al-taveel].phase_status == complete` before Change-D code lands, or (b) extend `run_wave.py 5 --phase P17` to refuse dispatch until P9.5's done_signal is true. Without this, Change D can ship before Asaas validates the preflight convention. *(Highest-priority — addresses the proposal's single biggest sequencing risk.)*

2. **Fix the two small acceptance-text drifts.** Edit W2 done_signal at podcast-plan.yaml:155 to add "+ P22"; edit P22 acceptance row at line 2412 to say "downstream phases from the halt point onwards" instead of "Phase 0c+." *(5 minutes of cleanup; trivial.)*

3. **Decide registry.md series_pattern seeding for Asaas.** Either hand-write `_system/registry.md` for Asaas now (with `series_pattern: recursive_scaffold`) so it's ready when P9.5 fires, or open a P9.5 sub-task requiring `scaffold_book.py` to seed `series_pattern` from a CLI flag or a co-located override file. Otherwise Pattern-5 gating silently no-ops on Asaas's first run.

4. **Add an acceptance row for the Pattern-5 recursive-scaffold fixtures.** Either under P4.9 or P9.5 — require the three fixtures (`golden`, `missing-recap`, `wrong-pattern-declared`) to exist before Pattern 5 is considered "shipped." Today Pattern 5 is documentation only.

5. **Add the challenger Category P concept-glossary sub-check as an acceptance row.** Track the rule's existence the same way other challenger rules are tracked (under a `P19.x` or `P4.9` row). Without it, the handbook describes a check that won't fire.

---

## Verdict

**SHIP-READY** for the integrated handbook + preflight artifact + plan deltas in commit `efdf323` / `7a5a50b`.

The four proposal changes (A/B/C/D) and the two operator-added extensions (E/F) are coherently integrated, mutually compatible, and faithful to the proposal's design intent. The integration improved the proposal in two places: P22's halt-point heuristic explicitly couples to the P17.1 adapter (clean dependency); P21's vocabulary.sqlite schema natively supports per-book glossary as seed corpus.

The five drift items above are all minor — three are acceptance-text wording bugs (Drifts 2, 3, 4), one is a missing pre-Asaas hand-step (Drift 5), and one is a sequencing-enforcement gap (Drift 1) that should be addressed before any Change-D code lands. None require reverting the integration.

**Recommended ordering**: ship as-is to unblock the KaR transcript review; address operator action items 1–5 in a follow-up commit on `feat/podcast-w1-foundation` before P9.5 fires for Asaas; do NOT block KaR review on these items.
