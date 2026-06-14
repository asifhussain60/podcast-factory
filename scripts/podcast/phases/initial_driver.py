"""phases/initial_driver.py — run_initial + _drive_authoring_through_0f.

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import REPO_ROOT  # noqa: E402
from _progress import initial_state, read_state, update_phase, write_state  # noqa: E402
from _rules import CONSUMER_CATEGORIES, ISLAMIC_SCHOLARLY_PROFILE, phase_capabilities  # noqa: E402
from _content_profile import resolve_content_profile  # noqa: E402
from _authoring import AuthoringError, AuthoringHalt, author_phase_0b, author_phase_0c, author_phase_0ci, author_phase_0d, author_phase_0e  # noqa: E402
from _contract_validation import validate_book_contracts  # noqa: E402  # FIX 14: 0d post-write gate
from phases.preflight import preflight_initial  # noqa: E402
from phases.scaffold import phase_branch, phase_scaffold, phase_0a_ingest, phase_git_commit  # noqa: E402
from phases.source_ingest import phase_0a_ingest_source_md  # noqa: E402
from phases.series_plan import phase_0f_write_series_plan  # noqa: E402
from phases.preflight import _run_chapter_set_check  # noqa: E402
from phases.source_review_gate import run_source_review_gate  # noqa: E402


from _subprocess import err as _err, info as _info  # noqa: E402


def _guard_before_phase(book_dir: Path, phase_id: str, log=_info) -> None:
    """Verify the previous phase's key artifacts before entering *phase_id*.

    Raises AuthoringError if a prerequisite is missing.  Most phases are stubs
    (log only) — 0e has a real check because episode-drafts from 0d are the
    only signal that chapter design succeeded before enrichment spends tokens.
    Add substance to stubs as each guard proves its value in practice.
    """
    sys_dir = book_dir / "_system"

    if phase_id == "0c":
        # Stub: 0b must have populated the book; unified-book.md is the primary artifact.
        ub = sys_dir / "unified-book.md"
        if ub.exists() and ub.stat().st_size > 500:
            log(f"  guard-0c: unified-book.md present ({ub.stat().st_size // 1024}kB) ✓")
        else:
            log("  guard-0c: (stub) unified-book.md not found — proceeding cautiously")

    elif phase_id == "0d":
        # Stub: 0c phonetic pass must be done; unified-book.md still the key artifact.
        ub = sys_dir / "unified-book.md"
        if ub.exists() and ub.stat().st_size > 500:
            log(f"  guard-0d: unified-book.md present ({ub.stat().st_size // 1024}kB) ✓")
        else:
            log("  guard-0d: (stub) unified-book.md not found — proceeding cautiously")

    elif phase_id == "0e":
        # Real check: 0d must have produced chapter txts + contracts. (NOT
        # _system/episode-drafts/ — those are written by the per-chapter
        # authoring loop long after 0e; checking them here dead-blocked every
        # fresh run at enrichment.)
        chapter_txts = sorted((book_dir / "chapters").glob("ch*.txt"))
        contracts = sorted((book_dir / "chapter-contracts").glob("*.yml"))
        if not chapter_txts:
            raise AuthoringError(
                phase="0e",
                message=("Guard-0e FAIL: no ch*.txt chapter files under "
                         "chapters/ — phase 0d may not have produced output."),
                manual_fallback="Re-run with: --retry-phase 0d",
            )
        if not contracts:
            raise AuthoringError(
                phase="0e",
                message=("Guard-0e FAIL: no contract .yml files under "
                         "chapter-contracts/ — phase 0d incomplete."),
                manual_fallback="Re-run with: --retry-phase 0d",
            )
        log(
            f"  guard-0e: {len(chapter_txts)} chapter(s) + {len(contracts)} contract(s) present ✓"
        )

    else:
        # Stub for 0b, 0ci, and any future phases.
        log(f"  guard-{phase_id}: (stub) no artifact pre-checks defined yet ✓")


def _gate_0d_contracts(book_dir: Path) -> None:
    """FIX 14 — Phase-0d post-write contract gate.

    Validates EVERY freshly written chapter-contracts/*.yml with the single
    shared validator (_contract_validation.validate_contract_full) and fails
    Phase 0d loudly BEFORE 0e runs, so the pipeline can never again hand the
    per-chapter loop a contract that extract or pipeline_lint will refuse
    (debate-with-no-block, slug/chapter-file rename mismatch, host roles
    outside the R-HOST-ROLE-PARITY enums, bad enum values, …).
    """
    failures = validate_book_contracts(book_dir)
    if not failures:
        _info(f"  gate-0d: all chapter contracts pass unified validation ✓")
        return
    lines: list[str] = []
    for slug, findings in failures:
        for f in findings:
            lines.append(f"  {slug}: {f}")
    raise AuthoringError(
        phase="0d",
        message=(
            f"Phase-0d contract gate FAIL: {len(failures)} contract(s) would be "
            f"refused downstream by extract/pipeline_lint:\n" + "\n".join(lines)
        ),
        manual_fallback=(
            "Fix chapter-contracts/<slug>.yml (or rename the matching chapters/ch*.txt\n"
            "file) so every finding above clears, then re-run: --retry-phase 0d\n"
            "Canonical rules: scripts/podcast/_contract_validation.py"
        ),
    )


def resolve_phase_profile(book_dir: Path, category: str | None) -> str:
    """Resolve the content_profile that drives phase-skip decisions for a book.

    Reads the book's declared content_profile, then applies the consumer
    compatibility shim: a consumer book that predates content_profile (category in
    CONSUMER_CATEGORIES, profile still defaulting to islamic_scholarly) routes as
    consumer_explainer so phonetics/enrichment stay skipped. Extracted so the
    routing decision is unit-testable (test_routing_capabilities.py).
    """
    profile = resolve_content_profile(book_dir)
    if profile == ISLAMIC_SCHOLARLY_PROFILE and (category or "") in CONSUMER_CATEGORIES:
        return "consumer_explainer"
    return profile


def derive_slug(pdf_path: Path) -> str:
    """Stem of the PDF, lowercased, non-alphanumeric → hyphen, collapsed."""
    import re
    stem = pdf_path.stem.lower()
    s = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return re.sub(r"-+", "-", s)


def _series_config_length_tier(book_dir: Path) -> str | None:
    """length_tier from _system/series-config.yaml, or None when absent/invalid."""
    cfg_path = book_dir / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return None
    try:
        import yaml
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    tier = str(cfg.get("length_tier") or "").strip()
    return tier if tier in ("default_deep_dive", "longer", "extended") else None


def _drive_authoring_through_0f(book_dir: Path, title: str, stop_after: str | None = None) -> int:
    """Run Phases 0b → 0c → 0d → 0e → 06a → 0f-halt. Used by run_initial AND --resume.

    When *stop_after* names an authoring phase (0b/0c/0d/0e), the driver
    halts cleanly the moment that phase completes — the phase block stays
    ``completed`` while the top-level ``phase_status`` is set to ``halted`` so the
    dispatcher re-enters here on the next ``--resume`` and skips the already-done
    phase. This powers per-step manual review without bypassing state-tracking or
    commits. Default (None) preserves the run-to-next-gate behaviour.
    """
    book_slug = book_dir.name
    state = read_state(book_dir) or {}
    config = state.get("config") or {}
    # Tier precedence: explicit intake config > the book's series-config.yaml
    # (the human-editable surface, e.g. density-standard re-runs) > "extended".
    length_tier = (config.get("length_tier")
                   or _series_config_length_tier(book_dir)
                   or "extended")
    unit_mode = config.get("unit_mode", "auto")
    category = config.get("category", "books")
    # Phase-skip decisions are driven by the book's content_profile via the single
    # capability table (phase_capabilities), NOT the legacy `category` tag — a
    # `books`-category item can be Islamic OR technical, and only the profile knows.
    # Compatibility shim (clean transition): a consumer book that predates
    # content_profile (category in CONSUMER_CATEGORIES, profile still defaulting to
    # islamic_scholarly) is routed as consumer_explainer so phonetics/enrichment stay
    # skipped — the historical behaviour. Pinned by test_routing_capabilities.py.
    profile = resolve_phase_profile(book_dir, category)
    caps = phase_capabilities(profile)

    def _run_0b(bd: Path) -> None:
        author_phase_0b(bd, log=_info)

    def _run_0c(bd: Path) -> None:
        if caps.skip_phonetics:
            _info(f"phase 0c · skipped for profile '{profile}' (no Arabic transliteration needed)")
            return
        author_phase_0c(bd, log=_info)

    def _run_0ci(bd: Path) -> None:
        # Skip guard: if 0d is already completed, this book pre-dates the feature — no-op.
        if "0d" in completed:
            _info("phase 0ci · 0d already completed (pre-feature book) — skipping")
            return
        author_phase_0ci(bd, log=_info)

    def _run_0d(bd: Path) -> None:
        author_phase_0d(bd, length_tier=length_tier, unit_mode=unit_mode, log=_info)
        _gate_0d_contracts(bd)

    def _run_0e(bd: Path) -> None:
        if caps.skip_enrichment:
            _info(f"phase 0e · skipped for profile '{profile}' (no doctrinal enrichment for this content type)")
            return
        author_phase_0e(bd, log=_info)

    # 0literary (per-chapter revoice) retired from the active flow 2026-06-04:
    # nothing consumes chapters/literary/ after the build_episode_txt wiring fix,
    # and the revoice now lives in PDF path (the companion book). The symbol stays
    # in _progress.PHASES (state-file back-compat) and the _literary.py helpers
    # stay (reused by _book_compose).
    phase_map = [
        ("0b", _run_0b, "phase 0b English refinement (chunked)"),
        ("0c", _run_0c, "phase 0c phonetic pass (chunked)"),
        ("0ci", _run_0ci, "phase 0ci book intelligence gap analysis"),
        ("0d", _run_0d, f"phase 0d chapter design (tier={length_tier}, unit={unit_mode})"),
        ("0e", _run_0e, "phase 0e enrichment"),
    ]
    completed = {
        p for p, blk in state.get("phases", {}).items()
        # A "halted" phase has done its LLM work and only paused for human review.
        # Running --resume IS the human's review acknowledgement — skip the phase
        # rather than re-running it (and re-spending the LLM call).
        if blk.get("status") in ("completed", "halted")
    }

    for phase_id, fn, subject in phase_map:
        if phase_id in completed:
            _info(f"phase: {phase_id} · already completed, skipping")
            continue
        try:
            _guard_before_phase(book_dir, phase_id, log=_info)
        except AuthoringError as e:
            update_phase(book_dir, phase=phase_id, status="failed",
                         error=str(e), extras={"manual_fallback": e.manual_fallback})
            _err(f"phase {phase_id} guard failed: {e}")
            if e.manual_fallback:
                _err("fix:")
                for line in e.manual_fallback.splitlines():
                    _err(f"  {line}")
            return 3
        _info(f"phase: {phase_id} · {subject} (LLM shellout)")
        update_phase(book_dir, phase=phase_id, status="running")
        try:
            fn(book_dir)
        except AuthoringHalt as e:
            # Phase completed its core work but requires human review before the next phase.
            # Commit the phase output, then halt cleanly (status="halted", not "failed").
            update_phase(book_dir, phase=phase_id, status="halted",
                         error=str(e), extras={"manual_fallback": e.manual_fallback})
            phase_git_commit(book_dir, f"podcast({book_slug}): {subject} [halted for review]")
            _info("")
            _info("─" * 72)
            _info(f"Phase {phase_id} · HALTED — human review required")
            _info(f"  {e}")
            if e.manual_fallback:
                _info("")
                _info("  Next steps:")
                for line in e.manual_fallback.splitlines():
                    _info(f"    {line}")
            _info("─" * 72)
            return 0
        except AuthoringError as e:
            update_phase(book_dir, phase=phase_id, status="failed",
                         error=str(e), extras={"manual_fallback": e.manual_fallback})
            _err(f"phase {phase_id} failed: {e}")
            if e.manual_fallback:
                _err("manual fallback:")
                for line in e.manual_fallback.splitlines():
                    _err(f"  {line}")
            return 3
        update_phase(book_dir, phase=phase_id, status="completed")
        phase_git_commit(book_dir, f"podcast({book_slug}): {subject}")

        if phase_id == "0d":
            _run_chapter_set_check(book_dir, log=_info)

        # Per-step review: halt cleanly after the requested phase. The block stays
        # 'completed' (set above); we only flip the top-level phase_status to
        # 'halted' so the dispatcher re-enters and skips this phase next resume.
        if stop_after and phase_id == stop_after:
            raw_state = read_state(book_dir) or {}
            raw_state["phase_status"] = "halted"
            write_state(book_dir, raw_state)
            _info("")
            _info("─" * 72)
            _info(f"Phase {phase_id} complete · halted (--stop-after {stop_after}).")
            _info("  Review this transformation, then resume the next phase, e.g.:")
            _info(f"    python3 scripts/podcast/orchestrate_book.py --resume {book_slug} --stop-after <next-phase>")
            _info("  (omit --stop-after to run forward to the next review gate)")
            _info("─" * 72)
            return 0

    # Phase 06a — source review gate (Wave I). Runs after 0e, before 0f.
    _06a_done = "06a" in completed
    if _06a_done:
        _info("phase: 06a · already completed, skipping")
    else:
        _info("phase: 06a · source review gate (Haiku companion-source review)")
        update_phase(book_dir, phase="06a", status="running")
        try:
            gate = run_source_review_gate(book_dir)
        except Exception as e:  # noqa: BLE001
            update_phase(book_dir, phase="06a", status="failed", error=str(e))
            _err(f"phase 06a failed: {e}")
            return 2
        if gate.approved:
            # Gate file already carried approved=True — mark done and fall through
            update_phase(book_dir, phase="06a", status="completed")
            _info("phase: 06a · already approved, advancing to series plan")
        else:
            # Halt for human review. update_phase stores the block with status=halted;
            # we then patch the top-level phase_status to the R4-guard sentinel value.
            update_phase(
                book_dir,
                phase="06a",
                status="halted",
                extras={"gate_warnings": len(gate.warnings)},
            )
            raw_state = read_state(book_dir) or {}
            raw_state["phase_status"] = "awaiting_human_review"
            write_state(book_dir, raw_state)
            phase_git_commit(book_dir, f"podcast({book_slug}): phase 06a source review gate — awaiting human review")
            _info("")
            _info("─" * 72)
            _info("Phase 06a complete · halted for human review.")
            _info(f"  {len(gate.warnings)} warning(s) in review-gate.json")
            _info("  Review and approve via:")
            _info(f"    http://localhost:4322/book-review/{book_slug}")
            _info(f"    python3 scripts/podcast/approve_book.py {book_slug}")
            _info("  Then resume:")
            _info(f"    python3 scripts/podcast/orchestrate_book.py --resume {book_slug}")
            _info("─" * 72)
            return 3

    _info("phase: 0f · assembling series-plan.md for human review")
    update_phase(book_dir, phase="0f", status="running")
    try:
        plan_path = phase_0f_write_series_plan(book_dir, title)
    except RuntimeError as e:
        update_phase(book_dir, phase="0f", status="failed", error=str(e))
        _err(str(e))
        return 2
    update_phase(
        book_dir,
        phase="0f",
        status="halted",
        extras={"series_plan_path": str(plan_path.relative_to(REPO_ROOT))},
    )
    phase_git_commit(book_dir, f"podcast({book_slug}): phase 0f series plan written; awaiting human review")

    _info("")
    _info("─" * 72)
    _info(f"Phase 0f complete · halted for human review.")
    _info("")
    _info(f"Review the series plan:")
    _info(f"  {plan_path.relative_to(REPO_ROOT)}")
    _info("")
    _info(f"Resume when approved:")
    _info(f"  python3 scripts/podcast/orchestrate_book.py --resume {book_slug}")
    _info("─" * 72)
    return 0


def _drive_source_ready_through_0f(book_dir: Path, state: dict) -> int:
    """Drive pre-written source books (SKIP_OCR_CATEGORIES) from source-ready → 0f halt.

    Called when phase='source-ready', phase_status='pending'|'failed'.
    Runs Phase 0a (local .md ingest, no Azure) then hands off to
    _drive_authoring_through_0f for 0b → 0d → 0e → 0f.

    Branch and scaffold are assumed done — the book_dir already exists with
    source/ populated. Only the pipeline processing phases run here.
    """
    book_slug = book_dir.name
    category = state.get("category", "explainers")
    title = _read_book_title_local(book_dir) or book_slug.replace("-", " ").title()

    phases_done = {
        p for p, blk in state.get("phases", {}).items()
        if blk.get("status") == "completed"
    }

    # ── Mark branch + scaffold completed (done out-of-band for source-ready books)
    for synthetic_phase in ("pre-flight", "branch", "scaffold"):
        if synthetic_phase not in phases_done:
            update_phase(book_dir, phase=synthetic_phase, status="completed")

    # ── Phase 0a — local source-md ingest (no Azure) ──────────────────────
    if "0a" not in phases_done:
        _info(f"phase: 0a · ingesting pre-written .md sources from {book_slug}/source/")
        update_phase(book_dir, phase="0a", status="running")
        try:
            phase_0a_ingest_source_md(book_dir, category, book_slug)
        except RuntimeError as e:
            update_phase(book_dir, phase="0a", status="failed", error=str(e))
            _err(str(e))
            return 2
        update_phase(book_dir, phase="0a", status="completed")
        phase_git_commit(book_dir, f"podcast({book_slug}): phase 0a source-md ingest")
    else:
        _info("phase: 0a · already completed (source-md ingest), skipping")

    # ── Phases 0b → 0f (existing driver handles everything) ───────────────
    # Category-aware routing in _refine, _chapter_design, _enrichment, _framing
    # already handles 'explainers' and 'sites' correctly. 0c is automatically
    # skipped via SKIP_PHONETICS_CATEGORIES in author_phase_0c.
    return _drive_authoring_through_0f(book_dir, title)


def _read_book_title_local(book_dir: Path) -> str | None:
    """Best-effort title from BOOK_DIR/_README.md (mirrors resume_dispatcher)."""
    readme = book_dir / "_README.md"
    if not readme.exists():
        return None
    for line in readme.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("# Podcast — "):
            return line[len("# Podcast — "):].strip()
    return None


def run_initial(args: argparse.Namespace) -> int:
    pdf_path = Path(args.pdf_path).resolve()
    slug = args.slug or derive_slug(pdf_path)
    category = args.category
    title = args.title or pdf_path.stem.replace("-", " ").replace("_", " ").title()
    author = args.author

    _info(f"orchestrate_book: initial run — slug={slug} · category={category}")
    fails = preflight_initial(pdf_path, slug, category)
    if fails:
        _err("pre-flight FAILED:")
        for f in fails:
            _err(f"  · {f}")
        return 1

    _info("pre-flight: OK")
    from _branching import branch_name as _branch_name
    _expected = _branch_name(category, slug)
    _info(f"phase: branch · creating {_expected}")
    try:
        phase_branch(slug, category)
    except RuntimeError as e:
        _err(str(e))
        return 2

    _info(f"phase: scaffold · {category}/{slug}")
    try:
        book_dir = phase_scaffold(category, slug, title, author)
    except RuntimeError as e:
        _err(str(e))
        return 2

    state = initial_state(slug, category)
    state["config"] = {
        "length_tier": args.length_tier,
        "unit_mode": args.unit_mode,
    }
    write_state(book_dir, state)
    update_phase(book_dir, phase="pre-flight", status="completed")
    update_phase(book_dir, phase="branch",     status="completed")
    update_phase(book_dir, phase="scaffold",   status="completed",
                 extras={"book_dir": str(book_dir.relative_to(REPO_ROOT))})
    phase_git_commit(book_dir, f"podcast({slug}): scaffold book directory")

    _info(f"phase: 0a · Azure OCR + Translation on {pdf_path.name}")
    update_phase(book_dir, phase="0a", status="running")
    try:
        phase_0a_ingest(book_dir, pdf_path, category, slug)
    except RuntimeError as e:
        update_phase(book_dir, phase="0a", status="failed", error=str(e))
        _err(str(e))
        return 2
    update_phase(book_dir, phase="0a", status="completed")
    phase_git_commit(book_dir, f"podcast({slug}): phase 0a Azure ingest")

    return _drive_authoring_through_0f(book_dir, title)
