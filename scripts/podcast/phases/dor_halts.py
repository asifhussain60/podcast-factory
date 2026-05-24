"""Halt-with-DoR runners for W1 phases the autonomous loop cannot safely auto-execute.

Each phase declares: PHASE_ID, DESCRIPTION, DOR (blockers/assumptions/ambiguities/
operator-action), DETECT_FILES + DETECT_MARKERS. If the operator hand-ships the
deliverable (files appear with markers), the runner auto-marks acceptance.
Otherwise it halts with the DoR breakdown.

These runners are deterministic, side-effect-free outside acceptance marking,
and safe to run on every autonomous tick.
"""
from __future__ import annotations

from pathlib import Path

from ._base import PhaseResult
from ._dor_halt import DoR, build_halted_result, is_done

REPO_ROOT = Path(__file__).resolve().parents[3]


def _make(
    phase_id: str,
    description: str,
    dor: DoR,
    detect_files: tuple[Path, ...],
    detect_markers: tuple[str, ...] = (),
) -> type:
    """Factory: return a phase-runner module-like object exposing
    PHASE_ID / DESCRIPTION / is_done / execute."""
    class _Runner:
        PHASE_ID = phase_id
        DESCRIPTION = description
        DOR = dor
        DETECT_FILES = detect_files
        DETECT_MARKERS = detect_markers

        @staticmethod
        def is_done(repo_root: Path | None = None) -> bool:
            return is_done(detect_files, detect_markers)

        @staticmethod
        def execute(repo_root: Path | None = None) -> PhaseResult:
            if is_done(detect_files, detect_markers):
                return PhaseResult(
                    phase_id=phase_id, status="done",
                    message=f"{phase_id} deliverable detected on disk (operator hand-shipped).",
                    rows_marked=[phase_id],
                    evidence_paths=[str(f) for f in detect_files],
                )
            return build_halted_result(phase_id, description, dor, detect_files)

    _Runner.__name__ = f"P{phase_id.replace('.', '_')}_Runner"
    return _Runner


# ── P2.1 — Tiny-book fixture ─────────────────────────────────────────────────
p2_1 = _make(
    "P2.1",
    "scripts/podcast/tests/e2e/fixtures/tiny-book/ — 3-chapter synthetic source",
    DoR(
        blockers=(
            "Fixture content must be hand-authored to satisfy P2.1 acceptance: "
            "3 chapters, ~5k words, ≥1 Arabic phrase, ≥1 numeric claim for Loop N.",
        ),
        assumptions=(
            "Synthetic content can be authored without Azure (text-only, no PDF).",
            "Total per-pass cost must remain <$0.50 (P2.1 metric); this constrains chapter length.",
            "Loop N numeric claim should be unsourced (testing the P0 detection) OR sourced+annotated.",
        ),
        ambiguities=(
            "Should the synthetic source mimic Islamic-philosophical register or a generic format? "
            "Recommend matching Ayyuhal Walad's register so the same prompts work.",
            "Should the fixture include intentional `[VERIFY CITATION]` markers to exercise Loop A failure modes?",
        ),
        operator_action=(
            "Create scripts/podcast/tests/e2e/fixtures/tiny-book/{source.md,raw-extract.md} with:\n"
            "  • 3 chapter sections separated by H2 headers\n"
            "  • ~5,000 words total\n"
            "  • At least one Arabic phrase (italicized + phonetic-rendered)\n"
            "  • At least one numeric claim ('three companions', 'seven X') for Loop N\n"
            "Also: scripts/podcast/tests/e2e/{__init__.py,conftest.py}"
        ),
    ),
    detect_files=(
        REPO_ROOT / "scripts/podcast/tests/e2e/__init__.py",
        REPO_ROOT / "scripts/podcast/tests/e2e/conftest.py",
        REPO_ROOT / "scripts/podcast/tests/e2e/fixtures/tiny-book/source.md",
    ),
)


# ── P2.2 — Sunny-day E2E ─────────────────────────────────────────────────────
p2_2 = _make(
    "P2.2",
    "scripts/podcast/tests/e2e/test_full_pipeline.py — sunny-day E2E",
    DoR(
        blockers=(
            "P2.1 must ship first (tiny-book fixture is the input).",
            "Test needs to mock Azure DocIntel/Translator/Speech OR run real but cheap.",
            "Test needs to mock `claude -p` OR run real but cheap.",
        ),
        assumptions=(
            "End-to-end run is <15 min wall-clock, <$1 cost (P2.2 metric).",
            "Mocks return canned artifacts deterministically (so test is reproducible).",
            "Sunny-day asserts the full PHASE_ORDER advance and ALL artifact files exist.",
        ),
        ambiguities=(
            "Mock strategy: (a) intercept subprocess.run calls; (b) replace _azure module entirely; "
            "(c) HTTP-level mock of Azure endpoints? Choose ONE and document.",
            "Heartbeat assertion: P7 not shipped yet — assert heartbeat.json existence only OR skip.",
            "Cost-ledger assertion: P6.1 ledger should be appended; mock model should return canned usage line.",
        ),
        operator_action=(
            "After P2.1 lands, author scripts/podcast/tests/e2e/test_full_pipeline.py that:\n"
            "  • Spins a tmp book dir, copies tiny-book fixture\n"
            "  • Mocks subprocess.run for claude -p AND _azure.* calls\n"
            "  • Runs orchestrate_book.py --no-gate\n"
            "  • Asserts state.json, refined-english.md, _phonetics.md, _chunks/*, "
            "    chapter-contracts/*, chapters/*.txt, halt at 09-series-plan gate\n"
            "  • Asserts no 'NO ARTIFACT' log line\n"
            "  • Asserts numeric-disambiguation-register.md present"
        ),
    ),
    detect_files=(REPO_ROOT / "scripts/podcast/tests/e2e/test_full_pipeline.py",),
    detect_markers=("def test_", "orchestrate_book"),
)


# ── P2.3 — Rainy-day E2E ─────────────────────────────────────────────────────
p2_3 = _make(
    "P2.3",
    "scripts/podcast/tests/e2e/test_failure_modes.py — artifact-missing / refusal / kill-resume",
    DoR(
        blockers=("P2.1 + P2.2 ship first.",),
        assumptions=(
            "Mock can inject rc=0-no-write to exercise the P5.2 raise path.",
            "Resume-after-kill test can use checkpointed .out.md files (orchestrator already supports).",
        ),
        ambiguities=(
            "`--retry-phase` semantic across the rename — confirm it accepts canonical phase names only "
            "(P8.6 enforces no aliases).",
        ),
        operator_action=(
            "Author scripts/podcast/tests/e2e/test_failure_modes.py asserting:\n"
            "  • Mock claude -p returning rc=0 with no file write → ChunkingError/AuthoringError raised\n"
            "  • Kill mid-window → resume re-processes only missing windows\n"
            "  • --retry-phase on a 'failed' 06-phonetics returns to that phase"
        ),
    ),
    detect_files=(REPO_ROOT / "scripts/podcast/tests/e2e/test_failure_modes.py",),
    detect_markers=("def test_",),
)


# ── P2.4 — Wire E2E into CI ─────────────────────────────────────────────────
p2_4 = _make(
    "P2.4",
    ".github/workflows/podcast-e2e.yml — E2E CI gate on PRs",
    DoR(
        blockers=("P2.2 + P2.3 test files exist + green.",),
        assumptions=(
            "GitHub Actions runner has Python 3.14 (or close); use setup-python action.",
            "Tests run with mocks (no live Azure / claude -p in CI).",
        ),
        ambiguities=(
            "Path-filter trigger: should the workflow fire on every push to scripts/podcast/, or only on PRs to develop? "
            "Recommend PR-only to develop.",
        ),
        operator_action=(
            "Create .github/workflows/podcast-e2e.yml that:\n"
            "  • Triggers on pull_request affecting scripts/podcast/**\n"
            "  • Sets up python 3.14, installs requirements (when P8.1 lands)\n"
            "  • Runs `python -m unittest discover -s scripts/podcast/tests/`\n"
            "  • Fails CI on non-zero exit\n"
            "Update SKILL.md to document the gate."
        ),
    ),
    detect_files=(REPO_ROOT / ".github/workflows/podcast-e2e.yml",),
    detect_markers=("on:", "pull_request", "unittest"),
)


# ── P2.5 — Learning-loop E2E + regression-harness CI gate ───────────────────
p2_5 = _make(
    "P2.5",
    "scripts/podcast/tests/e2e/test_learning_loop.py + podcast-learning-loop.yml",
    DoR(
        blockers=("P2.1 + P2.2 first; mock infrastructure required.",),
        assumptions=(
            "test_challenger.py exists today (verified) and stays green on develop.",
            "Mock challenger can emit canned findings (1 P1 + 2 P2) deterministically.",
        ),
        ambiguities=(
            "Mock challenger placement: subprocess intercept vs. dependency injection? "
            "Recommend subprocess intercept since the trainer flow shells out via claude -p.",
        ),
        operator_action=(
            "Author test_learning_loop.py asserting findings → patterns → proposals → "
            "regression-green → health written. Author podcast-learning-loop.yml CI workflow."
        ),
    ),
    detect_files=(
        REPO_ROOT / "scripts/podcast/tests/e2e/test_learning_loop.py",
        REPO_ROOT / ".github/workflows/podcast-learning-loop.yml",
    ),
    detect_markers=("findings.jsonl",),
)


# ── P2.6 — Golden-fixture refinement determinism ────────────────────────────
p2_6 = _make(
    "P2.6",
    "scripts/podcast/tests/e2e/test_refinement_determinism.py + golden refined-english.md",
    DoR(
        blockers=(
            "P2.1 tiny-book fixture first.",
            "First-run authority: ONE refinement pass on the tiny-book must execute to author the golden. "
            "This is a one-time live `claude -p` call (~$0.50 budget).",
        ),
        assumptions=(
            "Subsequent test runs replay against the committed golden (no live LLM).",
            "Levenshtein ratio + structural-key parity is sufficient determinism contract (the LLM is "
            "stochastic at the token level; we want bounded-similarity, not byte-identity).",
        ),
        ambiguities=(
            "What's the right Levenshtein library? python-Levenshtein has a C extension; rapidfuzz is "
            "the better-supported drop-in. Recommend rapidfuzz (pure Python fallback available).",
        ),
        operator_action=(
            "1. Run author_phase_0b ONCE on the tiny-book to author the golden file.\n"
            "2. Commit the golden with marker 'GOLDEN-ESTABLISHED: tiny-book v1'.\n"
            "3. Author test_refinement_determinism.py asserting subsequent runs match within tolerance."
        ),
    ),
    detect_files=(
        REPO_ROOT / "scripts/podcast/tests/e2e/test_refinement_determinism.py",
        REPO_ROOT / "scripts/podcast/tests/e2e/fixtures/tiny-book/golden/refined-english.md",
    ),
)


# ── P4.4b — Loop N regression fixture ───────────────────────────────────────
p4_4b = _make(
    "P4.4b",
    "_learning/fixtures/loop_n_numeric_invented/{input.txt,expected.json}",
    DoR(
        blockers=(
            "P4.5 must define Loop N's check IDs first; the fixture's expected.json cites them.",
        ),
        assumptions=(
            "test_challenger.py can be extended without breaking the 7 existing fixtures.",
            "The fixture is a minimal chapter excerpt asserting 'twelve regions' without enumeration.",
        ),
        ambiguities=(
            "Check ID name: 'N1-INVENTED-ENUMERATION' suggested by the YAML; final ID lives in Loop N spec.",
        ),
        operator_action=(
            "After Loop N spec lands (P4.5), create:\n"
            "  • content/podcast/.skill/_learning/fixtures/loop_n_numeric_invented/input.txt (chapter excerpt)\n"
            "  • content/podcast/.skill/_learning/fixtures/loop_n_numeric_invented/expected.json (1 P0 finding)\n"
            "Update scripts/podcast/test_challenger.py to cover the fixture; assert 8/8 green."
        ),
    ),
    detect_files=(
        REPO_ROOT / "content/podcast/.skill/_learning/fixtures/loop_n_numeric_invented/input.txt",
        REPO_ROOT / "content/podcast/.skill/_learning/fixtures/loop_n_numeric_invented/expected.json",
    ),
)


# ── P4.5 — Challenger Loop N spec ───────────────────────────────────────────
p4_5 = _make(
    "P4.5",
    ".github/agents/podcast-challenger.agent.md — Loop N (numeric/symbolic) spec",
    DoR(
        blockers=(
            "Challenger agent currently lives in infra/claude-agents/ + .claude/agents/ — NOT in "
            ".github/agents/ yet. P8.8 (W2) migrates it. P4.5 should land in BOTH current locations "
            "AND be carried into .github/agents/ during P8.8.",
        ),
        assumptions=(
            "The 5 Loop N checks + severity ladder (P0/P1/P2) are defined in podcast-plan.yaml P4.5 spec.",
            "Loop N's reads_normative includes 06-abjad-numerals.md + numeric-symbolic-disambiguation.md.",
        ),
        ambiguities=(
            "Check IDs naming convention: N1, N2 ... vs. N-INVENTED-ENUMERATION etc. Pick one.",
            "Should Loop N run on EVERY chapter or only chapters flagged with numeric claims in 03-source-integrity-notes.md? "
            "Recommend every chapter (cheap scan; conservative).",
        ),
        operator_action=(
            "1. Author the Loop N section in infra/claude-agents/podcast-challenger.md\n"
            "2. Mirror to .claude/agents/podcast-challenger.md (byte-identical post-suffix-strip)\n"
            "3. Stage the same Loop N for the eventual .github/agents/podcast-challenger.agent.md (P8.8)\n"
            "4. Bump CHALLENGER_VERSION in scripts/podcast/_rules.py to 1.9 (or whatever next minor)"
        ),
    ),
    detect_files=(
        REPO_ROOT / "infra/claude-agents/podcast-challenger.md",
        REPO_ROOT / ".claude/agents/podcast-challenger.md",
    ),
    detect_markers=("Loop N", "Numeric/Symbolic", "P0", "invented"),
)


# ── P4.6 — Phase 07-chapter-design numeric scan ─────────────────────────────
p4_6 = _make(
    "P4.6",
    "scripts/podcast/_authoring.py — Phase 07-chapter-design numeric-scan prompt step",
    DoR(
        blockers=(
            "Edits the chapter-design phase prompt — INVASIVE; must be guarded by P2.2 sunny-day test "
            "remaining green.",
        ),
        assumptions=(
            "The orchestrator only FLAGS numeric ambiguities; it does NOT invent decodings. Resolution "
            "happens in per-chapter scaffolding (P4.7) and challenger Loop N (P4.5).",
            "Output file is BOOK_DIR/_system/source/text/numeric-disambiguation-register.md.",
        ),
        ambiguities=(
            "Register file schema: free-form markdown vs. structured table? Recommend table with columns "
            "(claim, chapter, status, source, instruction) matching the per-book scaffolding pattern.",
        ),
        operator_action=(
            "Edit author_phase_0d (now 07-chapter-design) prompt to scan for numeric claims, abjad "
            "ciphers, anachronistic glosses. Emit numeric-disambiguation-register.md. "
            "Add test that mock-fixture with 'twelve regions' produces a register row."
        ),
    ),
    detect_files=(REPO_ROOT / "scripts/podcast/_authoring.py",),
    detect_markers=("numeric-disambiguation-register",),
)


# ── P4.7 — Master & Disciple Ch-02 scaffolding ──────────────────────────────
p4_7 = _make(
    "P4.7",
    "Master & Disciple Ch-02 NotebookLM scaffolding — Numeric Disambiguation updates",
    DoR(
        blockers=(
            "Per-book scaffolding under content/drafts/the-master-and-the-disciple/_notebooklm/. "
            "Files exist (8 system + 8 chapter scaffolds verified earlier) but Numeric Disambiguation "
            "content not yet woven in.",
        ),
        assumptions=(
            "Full ambiguity register is in _workspace/plan/numeric-symbolic-disambiguation-plan.md §3.",
            "12 jazāʾir + 7 seas RESOLVED; sphere-cipher + 5th-intermediary NEEDS HUMAN REVIEW.",
        ),
        ambiguities=(
            "Should the per-book scaffolding edits happen via challenger-driven authoring or by hand? "
            "Recommend hand-edit since the source material (§3 of plan doc) is explicit.",
        ),
        operator_action=(
            "Apply the 4 file updates per plan doc §3:\n"
            "  • _notebooklm/02-glossary.md (5 new entries: Twelve Jazāʾir, Seven Seas Yaʿqūbī, etc.)\n"
            "  • _notebooklm/03-source-integrity-notes.md (Numeric register + Anachronism register tables)\n"
            "  • _notebooklm/ch02-scaffolding.md (Numeric Disambiguation section + NotebookLM instructions)\n"
            "  • _notebooklm/06-human-review-checklist.md (§J with 9 checkboxes + escalation)"
        ),
    ),
    detect_files=(
        REPO_ROOT / "content/drafts/the-master-and-the-disciple/_notebooklm/03-source-integrity-notes.md",
        REPO_ROOT / "content/drafts/the-master-and-the-disciple/_notebooklm/ch02-scaffolding.md",
    ),
    detect_markers=("Numeric/Symbolic", "Anachronism", "Twelve Jazāʾir"),
)


# ── P5.3 — kitab-al-riyad resume ────────────────────────────────────────────
p5_3 = _make(
    "P5.3",
    "Resume content/drafts/kitab-al-riyad — drive 05-refine-english to 09-series-plan",
    DoR(
        blockers=(
            "REQUIRES EXPLICIT AZURE SPEND APPROVAL. Estimated $15-25 per the YAML resume_target_kitab_al_riyad block.",
            "P5.1 + P5.2 must be on develop (P5.1 already shipped; P5.2 shipped on this branch).",
            "book/kitab-al-riyad must be rebased onto current develop without state.json corruption.",
        ),
        assumptions=(
            "State.json at content/drafts/kitab-al-riyad/_system/ resumes cleanly.",
            "Azure DI/Translator quotas have headroom for 260p of refinement + phonetic + chapter-design + enrichment.",
            "Operator is present to monitor cost-ledger and abort if predicted cost > $50 cap.",
        ),
        ambiguities=(
            "Should this run on a feature branch or directly on book/kitab-al-riyad? "
            "Recommend cherry-pick P5.1+P5.2 onto book/kitab-al-riyad then resume there.",
            "Should P6.1 cost-ledger integration with _chunking.py + _authoring.py land BEFORE this resume? "
            "If not, the ledger won't capture per-call costs (only the per-run total). "
            "STRONG RECOMMENDATION: ship P6.1 integration first.",
        ),
        operator_action=(
            "1. Confirm Azure spend approval ($15-25 estimated).\n"
            "2. (Optional but recommended) Land P6.1 integration with _chunking.py + _authoring.py first.\n"
            "3. Rebase book/kitab-al-riyad onto current develop.\n"
            "4. cd to repo root, run: python3 scripts/podcast/orchestrate_book.py --resume kitab-al-riyad\n"
            "5. Monitor heartbeat (when P7 ships) or tail logs; halt if cost-ledger summing > $40.\n"
            "DO NOT auto-execute under launchd. This is a manual, monitored run."
        ),
    ),
    detect_files=(
        REPO_ROOT / "content/drafts/kitab-al-riyad/_system/source/text/refined-english.md",
    ),
)


# ── P6.3 — Soft/hard cost caps ──────────────────────────────────────────────
p6_3 = _make(
    "P6.3",
    "Soft warning $20 / hard halt $50 cost caps with CLI + state.config overrides",
    DoR(
        blockers=(
            "Soft-warning path needs P7 heartbeat (W2) to surface the warning visibly to the operator.",
            "Hard-halt path needs orchestrate_book.py integration with _cost_ledger sum check before "
            "Phase 07-chapter-design transition.",
        ),
        assumptions=(
            "Defaults: soft $20 / hard $50 — locked by Q2 resolution.",
            "CLI flags + state.config keys override the defaults.",
            "P6.1 cost-ledger writer is in place (shipped on this branch).",
        ),
        ambiguities=(
            "Should the hard halt save partial work or roll back? Recommend save + halt; operator decides next.",
            "Soft warning destination pre-P7: stderr only? Heartbeat (when shipped)? Both?",
        ),
        operator_action=(
            "1. Add --cost-cap-soft / --cost-cap-hard flags to orchestrate_book.py argparse.\n"
            "2. Add state.config.cost_cap_soft / cost_cap_hard read paths.\n"
            "3. Before Phase 07-chapter-design transition, call cost_ledger_summary on the book; "
            "if total > cost_cap_hard, raise AuthoringError(phase='cost-cap').\n"
            "4. At Phase 04 + 05 + 06 transitions, if total > cost_cap_soft, emit stderr warning "
            "(and heartbeat label, once P7 ships).\n"
            "5. Add e2e tests."
        ),
    ),
    detect_files=(REPO_ROOT / "scripts/podcast/orchestrate_book.py",),
    detect_markers=("cost_cap_hard", "cost_cap_soft"),
)


# ── P6.4 — Trainer cost-ledger hook ─────────────────────────────────────────
p6_4 = _make(
    "P6.4",
    "podcast-trainer.agent.md Protocol §3.5 reads cost-ledger.jsonl + emits cost-context",
    DoR(
        blockers=(
            "Edits .github/agents/podcast-trainer.agent.md — agent-spec file, careful diff required.",
            "_authoring.py invoke_trainer prompt extension needed.",
        ),
        assumptions=(
            "Trainer can read cost-ledger.jsonl via the standard file-read tool path.",
            "Trainer outputs end-line audit with `cost-context: $X.XX` field.",
        ),
        ambiguities=(
            "Cost overrun threshold for the P1 cost-commentary tombstone: 20% per YAML. Confirm.",
        ),
        operator_action=(
            "1. Edit .github/agents/podcast-trainer.agent.md — add Protocol §3.5 (read cost-ledger; surface remediation).\n"
            "2. Edit invoke_trainer() prompt in scripts/podcast/_authoring.py to instruct the read.\n"
            "3. Add a test that mock-trainer with $60 ledger (against $50 default) surfaces a cost-commentary tombstone in _learning/promoted/ or _learning/archive/.\n"
            "4. Bump Q3 closed_at to today's date in podcast-plan.yaml."
        ),
    ),
    detect_files=(REPO_ROOT / ".github/agents/podcast-trainer.agent.md",),
    detect_markers=("cost-ledger", "cost-context"),
)
