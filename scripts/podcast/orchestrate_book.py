#!/usr/bin/env python3
"""orchestrate_book.py — Autonomous book-to-NotebookLM pipeline driver (Phase A + B + C).

PURPOSE

  Deterministic Python driver for the `podcast-orchestrator` agent. v2 plan
  shipped Phases A + B + C in a single coherent landing (see
  docs/architecture/podcast-orchestrator.html §10):

    Phase A · Driver pre-flight → Phase 0a (Azure ingest)
    Phase B · Per-chapter convergence loop (3 outer × 5 inner = 15 max)
    Phase C · Trainer invocation (substrate-driven, regression-gated)

  Pipeline (initial run):
    pre-flight → branch → scaffold → 0a (Azure) → 0b (English refinement) →
    0c (phonetic pass) → 0d (chapter design) → 0e (enrichment) →
    0f-halt (writes series-plan.md, exits for human review)

  Pipeline (--resume after Phase 0f approval):
    per-chapter (extract → frame → build → converge) → 0g (register) →
    trainer (substrate-driven) → merge book/<slug> → develop → done

  Phase 0b–0e LLM authoring shells out to `claude -p` via `_authoring.py`
  with phase-specific prompts. Each phase asserts a non-empty output
  artifact; failure halts the orchestrator with a manual-fallback message
  the human can follow via the conversational `/podcast` skill, then
  `--resume` picks up at the next deterministic checkpoint.

  State lives in `<BOOK_DIR>/_system/orchestrator-state.json` (atomic
  tmpfile + rename). `--status <slug>` renders it without modification.
  `--resume <slug>` reads it and advances from `last_completed_phase`.

USAGE

  orchestrate-book initial:
    python3 scripts/podcast/orchestrate_book.py <pdf-path> [--slug SLUG]
        [--category books|articles|...]  [--title "Book Title"]
        [--author "Author Name"]

  orchestrate-book resume:
    python3 scripts/podcast/orchestrate_book.py --resume <book-slug>

  orchestrate-book status:
    python3 scripts/podcast/orchestrate_book.py --status <book-slug>

EXIT CODES

  0   — phase completed successfully (book at next checkpoint or all done)
  1   — pre-flight failed (refuse-with-fix-command path)
  2   — runtime error during a phase (state.json carries the details)
  3   — halted at LLM-authoring boundary; manual --resume after /podcast

DOES NOT MODIFY anything outside `content/podcast/library/<category>/<slug>/`
and `_workspace/Books/`. Git operations are limited to the active book
branch; never pushes to main; never force-pushes.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Local imports (these live next to this script).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _progress import (  # noqa: E402
    ORCHESTRATOR_VERSION,
    initial_state,
    read_state,
    render_status,
    update_phase,
    write_state,
)
from _authoring import (  # noqa: E402
    AuthoringError,
    author_phase_0b,
    author_phase_0c,
    author_phase_0d,
    author_phase_0e,
    author_framing,
    invoke_trainer,
)
from _convergence import (  # noqa: E402
    MAX_OUTER_ITERATIONS,
    ChapterOutcome,
    converge_chapter,
    render_outcome,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LIBRARY_ROOT = REPO_ROOT / "content" / "podcast" / "library"
SCAFFOLD_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "scaffold_book.py"
INGEST_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "ingest_source.py"
EXTRACT_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "extract_chapter.py"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "build_episode_txt.py"
AZURE_PROBE = REPO_ROOT / "scripts" / "podcast" / "test_azure_connectivity.py"

ALLOWED_CATEGORIES = ("books", "articles", "documents", "lectures", "interviews", "letters")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


# ─── tiny utilities ──────────────────────────────────────────────────────────


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a subprocess; return (rc, stdout, stderr). No exceptions on non-zero."""
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _git(*args: str) -> tuple[int, str, str]:
    return _run(["git", *args], cwd=REPO_ROOT)


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def _info(msg: str) -> None:
    print(msg)


def _book_dir(book_slug: str) -> Path | None:
    """Resolve <slug> to library/<category>/<slug>/ if it exists."""
    matches = [p for p in LIBRARY_ROOT.glob(f"*/{book_slug}") if p.is_dir()]
    return matches[0] if len(matches) == 1 else None


# ─── slug derivation ─────────────────────────────────────────────────────────


def derive_slug(pdf_path: Path) -> str:
    """Stem of the PDF, lowercased, non-alphanumeric → hyphen, collapsed."""
    stem = pdf_path.stem.lower()
    s = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    s = re.sub(r"-+", "-", s)
    return s


# ─── pre-flight hard gates ───────────────────────────────────────────────────


def _in_preflight_artifacts_mode(slug: str, category: str) -> bool:
    """True when curated preflight artifacts exist on disk but Phase 0a has not run.

    Convention (added 2026-05-19, Air redesign A+B+C+E+F integration): operators
    may pre-stage `_system/registry.md`, `_system/concept-glossary.md`, and
    `_system/source/` BEFORE invoking orchestrate_book.py. In that mode the strict
    `is-on-develop`, `dir-not-exists`, `remote-not-exists` gates would block
    legitimate first runs. Detect the mode here and relax those gates.
    """
    book_dir = LIBRARY_ROOT / category / slug
    registry = book_dir / "_system" / "registry.md"
    state    = book_dir / "_system" / "orchestrator-state.json"
    # Preflight-artifacts mode = curated registry present, but pipeline never ran
    return registry.exists() and not state.exists()


def preflight_initial(pdf_path: Path, slug: str, category: str) -> list[str]:
    """Return list of failure reasons. Empty list = pass."""
    fails: list[str] = []
    preflight_mode = _in_preflight_artifacts_mode(slug, category)

    # 1. Azure connectivity
    rc, _, _ = _run([sys.executable, str(AZURE_PROBE)])
    if rc != 0:
        fails.append(
            "Azure connectivity probe failed. Run: "
            f"python3 {AZURE_PROBE.relative_to(REPO_ROOT)}"
        )

    # 2. Working tree clean
    rc, out, _ = _git("status", "--porcelain")
    if rc != 0 or out.strip():
        fails.append(
            "working tree not clean. Run `git status` and commit / stash first."
        )

    # 3. On a valid starting branch for the run mode.
    #    - Normal initial run: must be on `develop`.
    #    - Preflight-artifacts mode: also accept `feat/podcast-w1-foundation`
    #      (where the preflight artifacts were authored) and `book/<slug>`
    #      (operator pre-cut the per-book branch).
    rc, branch, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    branch = branch.strip() if rc == 0 else ""
    valid_branches = {"develop"}
    if preflight_mode:
        valid_branches |= {"feat/podcast-w1-foundation", f"book/{slug}"}
    if branch not in valid_branches:
        fails.append(
            f"current branch is '{branch}'; expected one of {sorted(valid_branches)}. "
            "Run: git checkout " + (sorted(valid_branches)[0] if not preflight_mode else f"book/{slug}")
        )

    # 4. PDF exists + readable
    if not pdf_path.exists() or not pdf_path.is_file():
        fails.append(f"PDF not found or not a file: {pdf_path}")
    elif pdf_path.stat().st_size == 0:
        fails.append(f"PDF is empty: {pdf_path}")

    # 5. Slug valid + uncollided locally
    #    - Normal: BOOK_DIR must not exist.
    #    - Preflight-artifacts mode: BOOK_DIR is expected to exist with curated
    #      artifacts; orchestrator-state.json absence already confirmed this is
    #      a fresh initial run (not a stale partial state).
    if not SLUG_RE.match(slug):
        fails.append(f"slug invalid: {slug!r} (lowercase, hyphens, alphanumerics only)")
    elif (LIBRARY_ROOT / category / slug).exists() and not preflight_mode:
        fails.append(
            f"slug collides with existing book at "
            f"{(LIBRARY_ROOT / category / slug).relative_to(REPO_ROOT)}. "
            "Use --resume or pick a different slug."
        )

    # 6. Slug uncollided remotely
    #    - Normal: remote book/<slug> must not exist.
    #    - Preflight-artifacts mode: accept remote book/<slug> only if it points
    #      at the same commit as the local branch (operator pre-pushed).
    if SLUG_RE.match(slug):
        rc, out, _ = _git("ls-remote", "--heads", "origin", f"book/{slug}")
        if rc == 0 and out.strip():
            remote_sha = out.split()[0] if out else ""
            rc2, local_sha, _ = _git("rev-parse", f"book/{slug}")
            local_sha = local_sha.strip() if rc2 == 0 else ""
            if not (preflight_mode and remote_sha and local_sha and remote_sha == local_sha):
                fails.append(
                    f"remote branch 'book/{slug}' already exists. "
                    "Either pick a different slug or use --resume."
                )

    # 7. Category allowed
    if category not in ALLOWED_CATEGORIES:
        fails.append(
            f"category {category!r} not in {ALLOWED_CATEGORIES}"
        )

    return fails


def preflight_resume(book_slug: str) -> tuple[Path | None, list[str]]:
    """Return (book_dir, failures). Empty list = pass."""
    fails: list[str] = []
    book_dir = _book_dir(book_slug)
    if book_dir is None:
        fails.append(
            f"no library directory matches book-slug {book_slug!r} under "
            f"{LIBRARY_ROOT.relative_to(REPO_ROOT)}"
        )
        return None, fails

    # 1. State file exists
    state = read_state(book_dir)
    if state is None:
        fails.append(
            f"no orchestrator state at "
            f"{(book_dir / '_system' / 'orchestrator-state.json').relative_to(REPO_ROOT)}. "
            "Was this book started via orchestrate_book.py?"
        )

    # 2. Working tree clean
    rc, out, _ = _git("status", "--porcelain")
    if rc != 0 or out.strip():
        fails.append("working tree not clean. Commit or stash first, then --resume.")

    # 3. On matching branch
    rc, branch, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    branch = branch.strip() if rc == 0 else ""
    if branch != f"book/{book_slug}":
        fails.append(
            f"current branch is {branch!r}; expected 'book/{book_slug}'. "
            f"Run: git checkout book/{book_slug}"
        )

    return book_dir, fails


# ─── phase runners ───────────────────────────────────────────────────────────


def phase_branch(book_slug: str) -> None:
    """Create + push the book branch. Idempotent on already-on-branch."""
    rc, branch, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    branch = branch.strip() if rc == 0 else ""
    target = f"book/{book_slug}"
    if branch == target:
        _info(f"  already on {target}, skipping branch creation")
        return
    rc, _, err = _git("checkout", "-b", target)
    if rc != 0:
        raise RuntimeError(f"`git checkout -b {target}` failed: {err}")
    rc, _, err = _git("push", "-u", "origin", target)
    if rc != 0:
        # Non-fatal — remote push can be retried; book branch is local-valid.
        _err(f"`git push -u origin {target}` failed: {err}\n  (continuing with local-only branch)")


def phase_scaffold(category: str, book_slug: str, title: str, author: str | None) -> Path:
    """Shell out to scaffold_book.py. Returns the BOOK_DIR.

    In preflight-artifacts mode (BOOK_DIR pre-staged with curated registry + glossary +
    source/), passes --allow-existing so the scaffold fills in only missing stubs
    (pronunciation.md, mangle-map.md, etc.) without clobbering the curated artifacts.
    """
    cmd = [
        sys.executable,
        str(SCAFFOLD_SCRIPT),
        category,
        book_slug,
        title,
    ]
    if author:
        cmd += ["--author", author]
    if _in_preflight_artifacts_mode(book_slug, category):
        cmd += ["--allow-existing"]
    rc, out, err = _run(cmd)
    if rc != 0:
        raise RuntimeError(f"scaffold_book.py failed (rc={rc}):\n{err}\n{out}")
    book_dir = LIBRARY_ROOT / category / book_slug
    if not book_dir.is_dir():
        raise RuntimeError(f"scaffold did not create {book_dir}")
    return book_dir


def phase_0a_ingest(book_dir: Path, pdf_path: Path, category: str, book_slug: str) -> None:
    """Shell out to ingest_source.py for Azure OCR + Translation."""
    cmd = [
        sys.executable,
        str(INGEST_SCRIPT),
        str(pdf_path),
        "--book-slug", book_slug,
        "--category", category,
    ]
    rc, out, err = _run(cmd)
    if rc != 0:
        raise RuntimeError(f"ingest_source.py failed (rc={rc}):\n{err}\n{out}")
    raw = book_dir / "_system" / "source" / "text" / "raw-extract.md"
    if not raw.exists() or raw.stat().st_size == 0:
        raise RuntimeError(f"Phase 0a did not produce a non-empty {raw}")


def phase_git_commit(book_dir: Path, subject: str) -> None:
    """Stage everything under BOOK_DIR + commit with the given subject."""
    rel = book_dir.relative_to(REPO_ROOT)
    rc, _, err = _git("add", str(rel))
    if rc != 0:
        raise RuntimeError(f"`git add {rel}` failed: {err}")
    rc, out, _ = _git("status", "--porcelain")
    if not out.strip():
        _info(f"  nothing to commit for: {subject}")
        return
    rc, _, err = _git("commit", "-m", subject)
    if rc != 0:
        raise RuntimeError(f"`git commit` failed: {err}")


# ─── Phase 0f — write series plan + halt for human review ─────────────────────


SERIES_PLAN_TEMPLATE = """# Series Plan — {title}

**Book slug:** `{book_slug}`
**Branch:** `{branch}`
**Generated:** {ts}
**Orchestrator:** v{orch_version}
**Unit mode:** `{unit_mode}`
**Status:** AWAITING HUMAN APPROVAL

---

## Human-reviewed sections

### Length tier (AI recommendation)

**Tier:** `{length_tier}`
**Rationale:** {tier_rationale}

### Essentiality recommendations

Episodes the LLM flagged as **optional**, **bonus**, or **skip** during Phase 0d
content analysis. CORE episodes are not listed (the default; cannot be removed
without breaking the arc). To act on a `skip` recommendation, delete the
contract + chapter file before resuming.

{essentiality_table}

### Episode list

Columns:
- **Format** — `deep_dive` (Mentor+Student exposition) | `debate` (named voices clash + arbiter) | `narrative` (historical/biographical) | `interview` (Q&A)
- **Essential** — `core` | `optional` | `bonus` | `skip` (see Essentiality recommendations above)
- **Upload** — file to drop in NotebookLM's *Sources* panel
- **Customize** — file whose contents go in NotebookLM's *Customize* box (written by Phase 0g)
- **Length cue** — what to declare in the customize prompt's opening directive
- **Hosts** — host pairing for NotebookLM's customize prompt

{chapter_list_table}
{source_map_section}
---

## Audit-trail-only sections (no human review)

### Audience (orchestrator config default)
{audience}

### Angle (orchestrator config default)
{angle}

### Host dynamic (AI-selected per chapter)
{host_dynamic_table}

---

## NotebookLM input checklist (per-episode workflow)

After Phase 0g writes the per-episode customize prompts, for each episode:

1. **Open NotebookLM** → "+ New notebook" (or use existing per-book notebook)
2. **Sources panel** → "+ Add source" → "Upload from file" → select the file
   listed in the **Upload** column of the Episode list
3. **Customize panel** (top right) → "Customize" → paste the entire contents of
   the **Customize** file
4. The customize prompt already declares: length cue, host pairing, format
   (deep_dive vs debate), focus areas, pronunciation block, tone constraints
5. **Generate** → ~10–15 min for NotebookLM to render audio
6. **Download** the MP3 → save at `audio/EP##-<slug>.mp3`
7. **Transcribe** via `python3 scripts/podcast/transcribe_episode.py`
   → drops at `transcripts/EP##-<slug>.transcript.txt`
8. **Audit** via `python3 scripts/podcast/audit_transcript.py <BOOK_DIR> EP##-<slug>`
   — catches Arabic pronunciation drift, missing phonetic cues, fabricated quotes
9. If audit flags issues: edit `pronunciation.md` overrides → re-paste customize
   prompt → re-generate

---

## Next step

Review the **Length tier**, **Essentiality recommendations**, **Episode list**,
and (if shown) **Source-chapter → episode map**.

If everything looks correct: `python3 scripts/podcast/orchestrate_book.py --resume {book_slug}`

If an episode's segmentation, title, format, or host_dynamic needs fixing: edit
the relevant `chapter-contracts/<slug>.yml` and `chapters/ch##[a-z]?-<slug>.txt`,
then re-invoke `--resume`. The orchestrator detects the change and re-validates.

If the tier choice is wrong: edit every `chapter-contracts/<slug>.yml` to
the desired `length_target`, then re-invoke `--resume`.

If you want to change unit mode (chapter ↔ section ↔ auto), reset Phase 0d:
  `python3 scripts/podcast/orchestrate_book.py --resume {book_slug} --retry-phase 0d`
(then edit `_system/orchestrator-state.json` `config.unit_mode` before resuming)
"""


def phase_0f_write_series_plan(book_dir: Path, title: str) -> Path:
    """Assemble the series-plan.md from the contracts + chapter files written by 0d/0e.

    Returns the path written. Does NOT halt — the caller (`run_initial`)
    updates state to `phase=0f, status=halted` and exits.
    """
    import yaml as _yaml  # local import keeps PyYAML optional for --status-only callers
    from datetime import datetime, timezone

    book_slug = book_dir.name
    contracts_dir = book_dir / "chapter-contracts"
    chapters_dir = book_dir / "chapters"
    out_path = book_dir / "_system" / "series-plan.md"

    contracts: list[tuple[str, dict]] = []
    for yml in sorted(contracts_dir.glob("*.yml")):
        try:
            with yml.open("r", encoding="utf-8") as f:
                data = _yaml.safe_load(f) or {}
        except _yaml.YAMLError:
            raise RuntimeError(f"chapter contract failed to parse: {yml}")
        contracts.append((yml.stem, data))

    # Sort by episode_number so the series-plan tables read in narrative order,
    # not alphabetical-by-slug. Contracts missing episode_number fall to the end.
    contracts.sort(key=lambda t: t[1].get("episode_number") or 9999)

    if not contracts:
        raise RuntimeError(
            f"Phase 0f: no chapter contracts under {contracts_dir}. "
            "Phase 0d should have produced them."
        )

    # Tier (assume all contracts share the same length_target; flag if not)
    tiers = {c[1].get("length_target", "extended") for c in contracts}
    if len(tiers) == 1:
        length_tier = next(iter(tiers))
        tier_rationale = (
            "All chapters target the same length tier — series is balanced."
        )
    else:
        length_tier = "MIXED · author resolves"
        tier_rationale = (
            f"Chapters declare mixed tiers ({sorted(tiers)}). Pick one in the "
            "contracts before resuming."
        )

    # Length-cue lookup: maps length_target to the customize-prompt opening directive
    LENGTH_CUE = {
        "short_dive": '"target a 12–18 minute conversation"',
        "extended": '"target a 30–45 minute conversation"',
        "longer": '"target a 45–60 minute conversation"',
    }
    # Host-display lookup: maps host_dynamic field to a NotebookLM-friendly label
    HOST_DISPLAY = {
        "curious_mind + scholar_companion": "Mentor + Scholar Companion",
        "advocate_a + advocate_b + arbiter": "Advocate A + Advocate B + Arbiter",
        "advocate + arbiter": "Advocate + Arbiter",
        "narrator + companion": "Narrator + Companion",
        "interviewer + subject": "Interviewer + Subject",
    }

    # Chapter list table — extended schema (format, essential, NotebookLM input cues)
    rows = [
        "| # | Title | Words | Tier | Format | Essential | Upload (NotebookLM source) | Customize | Length cue | Hosts |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for slug, data in contracts:
        ch_num = data.get("episode_number", "?")
        title_ = data.get("title", slug)
        target = data.get("length_target", "?")
        fmt = data.get("episode_format", "deep_dive")
        essential = data.get("essential", "core")
        host_dyn = data.get("host_dynamic", "curious_mind + scholar_companion")
        host_disp = HOST_DISPLAY.get(host_dyn, host_dyn)
        length_cue = LENGTH_CUE.get(target, '"(set length cue)"')
        ch_file = next(chapters_dir.glob(f"ch*-{slug}.txt"), None)
        words = len(ch_file.read_text(encoding="utf-8").split()) if ch_file else "?"
        upload = f"`chapters/{ch_file.name}`" if ch_file else "(missing)"
        customize = f"`episodes/EP{ch_num:02d}-{slug}.txt`" if isinstance(ch_num, int) else f"`episodes/EP{ch_num}-{slug}.txt`"
        rows.append(
            f"| {ch_num} | {title_} | {words} | {target} | **{fmt}** | "
            f"{essential} | {upload} | {customize} (TBD post-0g) | {length_cue} | {host_disp} |"
        )
    chapter_list_table = "\n".join(rows)

    # Essentiality table — surface only non-CORE recommendations
    ess_rows = [
        "| # | Slug | Essential? | Why |",
        "|---|---|---|---|",
    ]
    non_core = [
        (s, d) for s, d in contracts
        if d.get("essential", "core") != "core"
    ]
    if non_core:
        for slug, data in non_core:
            ch_num = data.get("episode_number", "?")
            essential = data.get("essential", "?")
            why = data.get("essential_rationale", "(no rationale provided)")
            ess_rows.append(f"| {ch_num} | `{slug}` | **{essential}** | {why} |")
    else:
        ess_rows.append(
            "| — | — | — | All episodes flagged `core`. No essentiality concerns. |"
        )
    essentiality_table = "\n".join(ess_rows)

    # Audience / angle from the first contract (all should agree post-0d)
    first = contracts[0][1]
    audience = first.get("audience", "(not set — see chapter-contracts/<slug>.yml)").strip()
    angle = first.get("angle", "(not set)")

    # Host dynamic per chapter (AI-selected)
    host_rows = ["| Chapter | Host dynamic | Rationale |", "|---|---|---|"]
    for slug, data in contracts:
        hd = data.get("host_dynamic", "curious_mind + patient_teacher")
        # If the contract carries a rationale field, use it; otherwise leave blank
        rationale = data.get("host_dynamic_rationale", "")
        host_rows.append(f"| `{slug}` | {hd} | {rationale} |")
    host_dynamic_table = "\n".join(host_rows)

    state = read_state(book_dir) or {}
    config = state.get("config", {})
    unit_mode = config.get("unit_mode", "auto")

    # If a source-chapter map exists, inline it as its own section.
    source_map_path = book_dir / "_system" / "source" / "text" / "source-chapter-map.md"
    if source_map_path.exists() and source_map_path.stat().st_size > 0:
        source_map_section = (
            "\n### Source-chapter → episode map\n\n"
            f"{source_map_path.read_text(encoding='utf-8').strip()}\n"
        )
    else:
        source_map_section = ""

    body = SERIES_PLAN_TEMPLATE.format(
        title=title,
        book_slug=book_slug,
        branch=state.get("branch", f"book/{book_slug}"),
        ts=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        orch_version=ORCHESTRATOR_VERSION,
        unit_mode=unit_mode,
        length_tier=length_tier,
        tier_rationale=tier_rationale,
        essentiality_table=essentiality_table,
        chapter_list_table=chapter_list_table,
        source_map_section=source_map_section,
        audience=audience,
        angle=angle,
        host_dynamic_table=host_dynamic_table,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body, encoding="utf-8")
    return out_path


# ─── Phase 0g — register the series ─────────────────────────────────────────


def phase_0g_register(book_dir: Path) -> None:
    """Append episode rows to PODCAST_ROOT/.skill/registry.md (idempotent).

    This is a deterministic deferred step — Phase 0d already wrote per-chapter
    contracts; 0g surfaces the series in the cross-book registry so subsequent
    `validate_registry.py` runs see it.
    """
    registry = REPO_ROOT / "content" / "podcast" / ".skill" / "registry.md"
    if not registry.exists():
        # Brand-new repo or never-initialized registry — leave alone.
        return
    book_slug = book_dir.name
    contracts_dir = book_dir / "chapter-contracts"
    if not contracts_dir.is_dir():
        return

    import yaml as _yaml
    existing = registry.read_text(encoding="utf-8")
    new_lines: list[str] = []
    for yml in sorted(contracts_dir.glob("*.yml")):
        with yml.open("r", encoding="utf-8") as f:
            data = _yaml.safe_load(f) or {}
        ep = data.get("episode_number", "?")
        slug = data.get("slug", yml.stem)
        title = data.get("title", slug)
        source_type = data.get("source_type", "book-chapter")
        # Idempotent — skip if a row already mentions this slug
        if f"`{slug}`" in existing:
            continue
        new_lines.append(
            f"| EP{ep:02d} | {title} | `{slug}` | {source_type} | drafted | "
            f"{book_slug} | — |"
            if isinstance(ep, int) else
            f"| EP{ep} | {title} | `{slug}` | {source_type} | drafted | {book_slug} | — |"
        )
    if new_lines:
        with registry.open("a", encoding="utf-8") as f:
            f.write("\n".join(new_lines) + "\n")


# ─── Phase Per-chapter — extract + frame + build + converge ──────────────────


def per_chapter_pass(book_dir: Path, chapter_slug: str) -> ChapterOutcome:
    """Run the full per-chapter pipeline for one chapter.

    extract → author framing → build episode .txt → converge via challenger.
    Returns the convergence ChapterOutcome.
    """
    book_slug = book_dir.name

    # Resolve the chapter file FIRST — extract_chapter.py expects a ref of the
    # form `<book-slug>/<filename-stem-with-ch##-prefix>`, not `<book>:<slug>`.
    # (Bug X1 from 2026-05-21: the old `<book>:<slug>` colon form was interpreted
    # as a literal path and failed every chapter; the contract slug doesn't carry
    # the `ch##-` prefix that the on-disk filename does.)
    chapter_file = next((book_dir / "chapters").glob(f"ch*-{chapter_slug}.txt"), None)
    if chapter_file is None:
        return ChapterOutcome(
            chapter_slug=chapter_slug,
            final_verdict="FAILED",
            outer_iterations=0,
            fixer_attempts=0,
            p0_remaining=0, p1_remaining=0, p2_remaining=0,
            notes=[f"chapter file missing for slug {chapter_slug} "
                   f"(expected at chapters/ch*-{chapter_slug}.txt)"],
        )
    chapter_ref = f"{book_slug}/{chapter_file.stem}"

    # 1. Extract — scaffolds the episode-draft folder + bundle from the contract.
    rc, out, err = _run(
        [sys.executable, str(EXTRACT_SCRIPT), chapter_ref]
    )
    if rc != 0:
        return ChapterOutcome(
            chapter_slug=chapter_slug,
            final_verdict="FAILED",
            outer_iterations=0,
            fixer_attempts=0,
            p0_remaining=0, p1_remaining=0, p2_remaining=0,
            notes=[f"extract_chapter.py failed for {chapter_ref!r}: rc={rc}: {err.strip()[:200]}"],
        )

    # 2. Author framing — LLM call.
    try:
        author_framing(book_dir, chapter_slug)
    except AuthoringError as e:
        return ChapterOutcome(
            chapter_slug=chapter_slug,
            final_verdict="FAILED",
            outer_iterations=0,
            fixer_attempts=0,
            p0_remaining=0, p1_remaining=0, p2_remaining=0,
            notes=[f"framing authoring failed: {e}"],
        )

    # 3. Build the episode .txt — deterministic gate. We already resolved
    #    chapter_file above; derive the EP##-<slug> id from its name.
    chap_num = chapter_file.stem.split("-", 1)[0][2:]
    episode_id = f"EP{chap_num}-{chapter_slug}"
    rc, out, err = _run([sys.executable, str(BUILD_SCRIPT), str(book_dir), episode_id])
    if rc != 0:
        return ChapterOutcome(
            chapter_slug=chapter_slug,
            final_verdict="FAILED",
            outer_iterations=0,
            fixer_attempts=0,
            p0_remaining=0, p1_remaining=0, p2_remaining=0,
            notes=[f"build_episode_txt.py failed: rc={rc}: {err.strip()[:300]}"],
        )

    # 4. Convergence loop via _convergence.py.
    return converge_chapter(book_dir, chapter_slug)


# ─── Phase Merge — book/<slug> → develop ─────────────────────────────────────


def phase_merge_to_develop(book_slug: str) -> None:
    """Fast-forward develop + merge book branch with --no-ff. Never touches main."""
    branch = f"book/{book_slug}"
    rc, _, err = _git("checkout", "develop")
    if rc != 0:
        raise RuntimeError(f"`git checkout develop` failed: {err}")
    rc, _, err = _git("pull", "--ff-only", "origin", "develop")
    if rc != 0:
        # Non-fatal — local merge can still proceed without remote pull.
        _err(f"warning: `git pull --ff-only origin develop` failed: {err}")
    rc, _, err = _git(
        "merge",
        "--no-ff",
        branch,
        "-m",
        f"Merge branch '{branch}' into develop",
    )
    if rc != 0:
        raise RuntimeError(f"`git merge --no-ff {branch}` failed: {err}")
    rc, _, err = _git("push", "origin", "develop")
    if rc != 0:
        _err(f"warning: `git push origin develop` failed: {err}\n  (local merge preserved)")


# ─── driver ──────────────────────────────────────────────────────────────────


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

    # Create the BOOK_DIR (scaffold), then write initial state into it.
    _info("pre-flight: OK")
    _info(f"phase: branch · creating book/{slug}")
    try:
        phase_branch(slug)
    except RuntimeError as e:
        _err(str(e))
        return 2

    _info(f"phase: scaffold · {category}/{slug}")
    try:
        book_dir = phase_scaffold(category, slug, title, author)
    except RuntimeError as e:
        _err(str(e))
        return 2

    # Initialize the state file now that BOOK_DIR exists.
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

    # ── Phases 0b–0e — LLM authoring via claude -p shellout ────────────────
    return _drive_authoring_through_0f(book_dir, title)


def _drive_authoring_through_0f(book_dir: Path, title: str) -> int:
    """Run Phases 0b → 0c → 0d → 0e → 0f-halt. Used by run_initial AND --resume."""
    book_slug = book_dir.name

    state = read_state(book_dir) or {}
    config = state.get("config", {})
    length_tier = config.get("length_tier", "extended")
    unit_mode = config.get("unit_mode", "auto")

    # Per-phase wrappers so each gets its phase-specific config + log routing.
    def _run_0b(bd: Path) -> None:
        author_phase_0b(bd, log=_info)

    def _run_0c(bd: Path) -> None:
        author_phase_0c(bd, log=_info)

    def _run_0d(bd: Path) -> None:
        author_phase_0d(bd, length_tier=length_tier, unit_mode=unit_mode, log=_info)

    def _run_0e(bd: Path) -> None:
        author_phase_0e(bd, log=_info)

    phase_map = [
        ("0b", _run_0b, "phase 0b English refinement (chunked)"),
        ("0c", _run_0c, "phase 0c phonetic pass (chunked)"),
        ("0d", _run_0d, f"phase 0d chapter design (tier={length_tier}, unit={unit_mode})"),
        ("0e", _run_0e, "phase 0e enrichment"),
    ]
    # Only skip phases marked completed in state.phases[ph].
    completed = {
        p for p, blk in state.get("phases", {}).items()
        if blk.get("status") == "completed"
    }

    for phase_id, fn, subject in phase_map:
        if phase_id in completed:
            _info(f"phase: {phase_id} · already completed, skipping")
            continue
        _info(f"phase: {phase_id} · {subject} (LLM shellout)")
        update_phase(book_dir, phase=phase_id, status="running")
        try:
            fn(book_dir)
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

    # Phase 0f — assemble series-plan.md and halt.
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


def _drive_per_chapter_and_after(book_dir: Path) -> int:
    """After Phase 0f approval, drive per-chapter loop + 0g + trainer + merge."""
    book_slug = book_dir.name

    # Resolve chapter slugs from the chapter contracts (canonical source after 0d).
    contracts_dir = book_dir / "chapter-contracts"
    chapter_slugs = sorted(p.stem for p in contracts_dir.glob("*.yml"))
    if not chapter_slugs:
        _err(
            f"no chapter contracts under {contracts_dir} — "
            "Phase 0d should have produced them. Cannot proceed."
        )
        return 2

    state = read_state(book_dir) or {}
    completed_chapter_slugs = set(
        state.get("phases", {}).get("per-chapter", {}).get("completed_slugs", [])
    )

    update_phase(book_dir, phase="per-chapter", status="running")
    outcomes: list[ChapterOutcome] = []
    for slug in chapter_slugs:
        if slug in completed_chapter_slugs:
            _info(f"phase: per-chapter[{slug}] · already shipped, skipping")
            continue
        _info(f"phase: per-chapter[{slug}] · extract → frame → build → converge")
        outcome = per_chapter_pass(book_dir, slug)
        outcomes.append(outcome)
        _info(render_outcome(outcome))
        if outcome.final_verdict == "FAILED":
            update_phase(
                book_dir,
                phase="per-chapter",
                status="failed",
                error=f"chapter {slug} failed: {'; '.join(outcome.notes[-3:])}",
                extras={
                    "completed_slugs": sorted(completed_chapter_slugs),
                    "failed_slug": slug,
                },
            )
            _err(f"chapter {slug} failed; halting per-chapter loop.")
            return 2

        completed_chapter_slugs.add(slug)
        # Commit the chapter's chunk of work on the book branch.
        phase_git_commit(
            book_dir,
            f"podcast({book_slug})[{slug}]: {outcome.final_verdict} "
            f"(iter={outcome.outer_iterations} · P0={outcome.p0_remaining} "
            f"P1={outcome.p1_remaining})",
        )
        update_phase(
            book_dir,
            phase="per-chapter",
            status="running",
            extras={"completed_slugs": sorted(completed_chapter_slugs)},
        )

    update_phase(
        book_dir,
        phase="per-chapter",
        status="completed",
        extras={"completed_slugs": sorted(completed_chapter_slugs)},
    )

    # Phase 0g — register the series in the cross-book registry.
    _info("phase: 0g · register series in registry.md")
    update_phase(book_dir, phase="0g", status="running")
    try:
        phase_0g_register(book_dir)
    except RuntimeError as e:
        update_phase(book_dir, phase="0g", status="failed", error=str(e))
        _err(str(e))
        return 2
    update_phase(book_dir, phase="0g", status="completed")
    phase_git_commit(book_dir, f"podcast({book_slug}): phase 0g register series")

    # Trainer pass — substrate-driven rule promotion (regression-gated).
    _info("phase: trainer · invoke podcast-trainer on the book branch")
    update_phase(book_dir, phase="trainer", status="running")
    try:
        invoke_trainer(book_dir)
    except AuthoringError as e:
        # Trainer failure is NOT fatal — the book still merges to develop.
        update_phase(
            book_dir, phase="trainer", status="failed",
            error=str(e),
            extras={"manual_fallback": e.manual_fallback},
        )
        _err(f"trainer pass failed (non-fatal): {e}")
    else:
        update_phase(book_dir, phase="trainer", status="completed")

    # Merge to develop.
    _info("phase: merge · book branch → develop")
    update_phase(book_dir, phase="merge", status="running")
    try:
        phase_merge_to_develop(book_slug)
    except RuntimeError as e:
        update_phase(book_dir, phase="merge", status="failed", error=str(e))
        _err(str(e))
        return 2
    update_phase(book_dir, phase="merge", status="completed")
    update_phase(book_dir, phase="done",  status="completed")

    _info("")
    _info("─" * 72)
    _info(f"Book {book_slug}: SHIPPED.")
    _info("Per-chapter outcomes:")
    for o in outcomes:
        _info(render_outcome(o))
    _info("─" * 72)
    return 0


def run_resume(args: argparse.Namespace) -> int:
    slug = args.resume
    _info(f"orchestrate_book: resume — slug={slug}")
    book_dir, fails = preflight_resume(slug)
    if fails:
        _err("pre-flight FAILED:")
        for f in fails:
            _err(f"  · {f}")
        return 1

    assert book_dir is not None
    state = read_state(book_dir)
    if state is None:
        _err("state file missing despite pre-flight pass — abort")
        return 2

    # --retry-phase: reset the named phase's status to pending so the loop re-runs it.
    retry_phase = getattr(args, "retry_phase", None)
    if retry_phase:
        if retry_phase not in state.get("phases", {}):
            _err(f"--retry-phase: unknown phase {retry_phase!r}. Known: {sorted(state.get('phases', {}).keys())}")
            return 1
        _info(f"  --retry-phase {retry_phase}: resetting status to 'pending'")
        block = state["phases"][retry_phase]
        block["status"] = "pending"
        block.pop("ts_completed", None)
        block.pop("manual_fallback", None)
        state["phase"] = retry_phase
        state["phase_status"] = "pending"
        # If we're retrying an authoring phase, also clear any later 'completed' marks
        # so the downstream order is rebuilt from this point.
        order = ("0b", "0c", "0d", "0e")
        if retry_phase in order:
            idx = order.index(retry_phase)
            for later in order[idx + 1:]:
                lb = state["phases"].get(later, {})
                if lb.get("status") == "completed":
                    _info(f"  --retry-phase: clearing downstream {later} (was completed)")
                    lb["status"] = "pending"
                    lb.pop("ts_completed", None)
        # last_completed_phase walks back to the predecessor.
        canonical = ("pre-flight", "branch", "scaffold", "0a", "0b", "0c", "0d", "0e",
                     "0f", "0g", "per-chapter", "trainer", "merge", "done")
        if retry_phase in canonical:
            i = canonical.index(retry_phase)
            state["last_completed_phase"] = canonical[i - 1] if i > 0 else None
        write_state(book_dir, state)
        # Re-read for the rest of run_resume.
        state = read_state(book_dir) or state

    last = state.get("last_completed_phase") or ""
    current_phase = state.get("phase") or ""
    current_status = state.get("phase_status") or ""

    _info(f"  last completed:  {last or '(none)'}")
    _info(f"  current phase:   {current_phase}  [{current_status}]")

    # If we halted at 0f, this is the post-human-approval resume — drive Phase B + C.
    if current_phase == "0f" and current_status == "halted":
        plan = book_dir / "_system" / "series-plan.md"
        if not plan.exists() or plan.stat().st_size == 0:
            _err(f"series-plan.md missing at {plan} — cannot resume after 0f.")
            return 2
        _info("Phase 0f gate cleared (human approved by re-invoking --resume).")
        return _drive_per_chapter_and_after(book_dir)

    # If we halted mid-0a (Azure ingest failure — e.g., transient network blip
    # during Translator), re-run ingest from the PDF in _system/source/.
    if current_phase == "0a" and current_status in ("failed", "pending"):
        category = state.get("category", "books")
        source_dir = book_dir / "_system" / "source"
        pdfs = sorted(source_dir.glob("*.pdf"))
        if not pdfs:
            _err(f"No PDF found in {source_dir.relative_to(REPO_ROOT)} — cannot retry 0a.")
            return 2
        if len(pdfs) > 1:
            _err(
                f"Multiple PDFs in {source_dir.relative_to(REPO_ROOT)}: "
                f"{[p.name for p in pdfs]}. Keep one and retry."
            )
            return 2
        pdf_path = pdfs[0]
        _info(f"phase: 0a · re-running Azure ingest on {pdf_path.name}")
        update_phase(book_dir, phase="0a", status="running")
        try:
            phase_0a_ingest(book_dir, pdf_path, category, slug)
        except RuntimeError as e:
            update_phase(book_dir, phase="0a", status="failed", error=str(e))
            _err(str(e))
            return 2
        update_phase(book_dir, phase="0a", status="completed")
        phase_git_commit(book_dir, f"podcast({slug}): phase 0a Azure ingest (retry)")
        title = _read_book_title(book_dir) or slug.replace("-", " ").title()
        return _drive_authoring_through_0f(book_dir, title)

    # If we halted mid-0b/0c/0d/0e (LLM-authoring failure), retry from there.
    if current_phase in ("0b", "0c", "0d", "0e") and current_status in ("failed", "halted", "pending"):
        # Derive title from the BOOK_DIR's _README.md or use the slug as a fallback.
        title = _read_book_title(book_dir) or slug.replace("-", " ").title()
        _info(f"resuming LLM-authoring phases from {current_phase} (status={current_status})")
        return _drive_authoring_through_0f(book_dir, title)

    # If we're past 0a and the state shows authoring is complete, advance to 0f.
    if last in ("0a",) or (last in ("0b", "0c", "0d", "0e") and current_status == "completed"):
        title = _read_book_title(book_dir) or slug.replace("-", " ").title()
        return _drive_authoring_through_0f(book_dir, title)

    # If we halted mid-per-chapter, resume the loop (it tracks completed_slugs).
    if current_phase == "per-chapter" and current_status in ("failed", "halted", "running"):
        return _drive_per_chapter_and_after(book_dir)

    # If we already merged, nothing to do.
    if current_phase == "done":
        _info("This book has already shipped. Nothing to resume.")
        return 0

    _info("")
    _info(f"  No automated action for current phase '{current_phase}'. State file:")
    _info(f"    {(book_dir / '_system' / 'orchestrator-state.json').relative_to(REPO_ROOT)}")
    return 3


def _read_book_title(book_dir: Path) -> str | None:
    """Best-effort title extraction from BOOK_DIR/_README.md."""
    readme = book_dir / "_README.md"
    if not readme.exists():
        return None
    for line in readme.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("# Podcast — "):
            return line[len("# Podcast — "):].strip()
    return None


def run_status(args: argparse.Namespace) -> int:
    slug = args.status
    book_dir = _book_dir(slug)
    if book_dir is None:
        _err(f"no library directory matches book-slug {slug!r}")
        return 1
    state = read_state(book_dir)
    if state is None:
        _err(
            f"no orchestrator state at "
            f"{(book_dir / '_system' / 'orchestrator-state.json').relative_to(REPO_ROOT)}"
        )
        return 1
    print(render_status(state))
    return 0


# ─── CLI ─────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="orchestrate-book",
        description="Autonomous book-to-NotebookLM pipeline driver (Phase A + B + C).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  Initial:  orchestrate-book _workspace/Books/foo.pdf --slug foo --category books\n"
            "  Resume:   orchestrate-book --resume foo\n"
            "  Status:   orchestrate-book --status foo\n"
        ),
    )
    p.add_argument("pdf_path", nargs="?",
                   help="path to the source PDF (initial run only)")
    p.add_argument("--slug",
                   help="book slug (default: derived from PDF filename)")
    p.add_argument("--category", default="books",
                   choices=ALLOWED_CATEGORIES,
                   help="library subdirectory (default: books)")
    p.add_argument("--title",
                   help='book title (default: derived from PDF filename)')
    p.add_argument("--author", default=None,
                   help="book author (optional)")
    p.add_argument("--resume", metavar="SLUG",
                   help="resume an orchestrator run for the named book slug")
    p.add_argument("--status", metavar="SLUG",
                   help="render the current state for the named book slug")
    p.add_argument("--retry-phase", metavar="PHASE_ID", default=None,
                   help=(
                       "(used with --resume) reset the named phase's status to 'pending' "
                       "and re-run it. Useful after fixing a 'failed' phase. "
                       "Example: --resume foo --retry-phase 0b"
                   ))
    p.add_argument("--length-tier", default="extended",
                   choices=("default_deep_dive", "longer", "extended"),
                   help=(
                       "target episode length tier (initial run only; persisted in state). "
                       "default_deep_dive=1.8-2.8k words, longer=2.8-4.5k, extended=5.5-9.5k. "
                       "Default: extended."
                   ))
    p.add_argument("--unit-mode", default="auto",
                   choices=("chapter", "section", "auto"),
                   help=(
                       "Phase 0d episode segmentation (initial run only; persisted in state). "
                       "chapter=one episode per source chapter (small books); "
                       "section=split every chapter into sections; "
                       "auto=LLM decides per chapter based on tier band (recommended). "
                       "Default: auto."
                   ))
    p.add_argument("--version", action="version",
                   version=f"orchestrate_book.py v{ORCHESTRATOR_VERSION}")
    return p


def main() -> int:
    args = build_parser().parse_args()

    if args.status:
        return run_status(args)
    if args.resume:
        return run_resume(args)
    if not args.pdf_path:
        _err("either <pdf-path> (initial) or --resume <slug> or --status <slug> is required")
        return 1
    return run_initial(args)


if __name__ == "__main__":
    sys.exit(main())
