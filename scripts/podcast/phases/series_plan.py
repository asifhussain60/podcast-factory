"""phases/series_plan.py — Phase 0f series plan + episode resolution helpers.

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.

Exports:
  SERIES_PLAN_TEMPLATE            — human-readable Markdown template
  _resolve_episode_id             — prefer contract.episode_number over filename digits
  _series_numeric                 — read a float flag from series-plan.md
  _series_flag                    — read a bool flag from series-plan.md
  _chapter_cost_so_far            — sum cost-ledger rows for a chapter slug
  phase_0f_write_series_plan      — assemble and write series-plan.md; halt
  phase_0g_register               — append episode rows to cross-book registry
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import REPO_ROOT  # noqa: E402
from _progress import ORCHESTRATOR_VERSION, read_state  # noqa: E402


def _info(msg: str) -> None:
    print(msg)


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def _git(*args: str) -> tuple[int, str, str]:
    proc = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


# ─── Series plan template ─────────────────────────────────────────────────────

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


# ─── Episode resolution helpers ───────────────────────────────────────────────


def _resolve_episode_id(book_dir: Path, chapter_file: Path, chapter_slug: str) -> str:
    """F12: resolve episode ID preferring contract.episode_number.

    Phase 0d may re-sequence episodes (chronological/dialectical pairings) so
    a chapter at `ch07-soul-and-spirit.txt` could be EP04. Read the contract
    and use its `episode_number` when present; fall back to filename digits.
    Returns: `EP{NN}-{chapter_slug}` (two-digit NN if int, raw str otherwise).
    """
    contract_path = book_dir / "chapter-contracts" / f"{chapter_slug}.yml"
    ep_num: int | str | None = None
    if contract_path.exists():
        try:
            import yaml as _yaml
            with contract_path.open("r", encoding="utf-8") as f:
                data = _yaml.safe_load(f) or {}
            ep_num = data.get("episode_number")
        except (OSError, ImportError, Exception):
            ep_num = None
    if ep_num is None:
        chap_prefix = chapter_file.stem.split("-", 1)[0]
        m = re.match(r"ch(\d+)", chap_prefix)
        ep_num = m.group(1) if m else chap_prefix[2:]
    if isinstance(ep_num, int):
        return f"EP{ep_num:02d}-{chapter_slug}"
    s = str(ep_num)
    if s.isdigit():
        return f"EP{int(s):02d}-{chapter_slug}"
    return f"EP{s}-{chapter_slug}"


def _series_numeric(book_dir: Path, flag_name: str, *, default: float) -> float:
    """F35-second: read a numeric flag from series-plan.md.

    Looks for `**<Title-Case-Flag>:** <value>`. Returns `default` if missing.
    """
    plan_path = book_dir / "_system" / "series-plan.md"
    if not plan_path.exists():
        return default
    label = flag_name.replace("_", " ").title()
    needle_lower = f"**{label.lower()}:**"
    try:
        for raw in plan_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.lower().startswith(needle_lower):
                value = line[len(needle_lower):].strip().strip("`").strip("*").strip("$")
                return float(value)
    except (OSError, ValueError):
        return default
    return default


def _chapter_cost_so_far(book_dir: Path, chapter_slug: str) -> float:
    """F35-second: sum cost-ledger.jsonl rows tagged with a chapter slug.

    Reads `_system/cost-ledger.jsonl`; sums `cost_usd` where `step` contains
    the chapter slug. Returns 0.0 if ledger missing or unreadable.
    """
    ledger = book_dir / "_system" / "cost-ledger.jsonl"
    if not ledger.exists():
        return 0.0
    total = 0.0
    try:
        for raw in ledger.read_text(encoding="utf-8").splitlines():
            if not raw.strip() or chapter_slug not in raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if chapter_slug in str(rec.get("step", "")):
                total += float(rec.get("cost_usd", 0) or 0)
    except OSError:
        return 0.0
    return round(total, 4)


def _series_flag(book_dir: Path, flag_name: str, *, default: bool = False) -> bool:
    """Read a boolean flag from series-plan.md.

    Looks for `**<Title-Case-Flag>:** <value>`. Parses true/yes/on/1 as True.
    Returns `default` if missing or on any parse error.
    """
    plan_path = book_dir / "_system" / "series-plan.md"
    if not plan_path.exists():
        return default
    label = flag_name.replace("_", " ").title()
    needle_lower = f"**{label.lower()}:**"
    try:
        for raw in plan_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.lower().startswith(needle_lower):
                value = line[len(needle_lower):].strip().strip("`").strip("*").lower()
                return value in {"true", "yes", "on", "1", "enabled"}
    except OSError:
        return default
    return default


# ─── Phase 0f ────────────────────────────────────────────────────────────────


def phase_0f_write_series_plan(book_dir: Path, title: str) -> Path:
    """Assemble series-plan.md from contracts + chapter files written by 0d/0e.

    Returns the path written. Does NOT halt — the caller updates state to
    `phase=0f, status=halted` and exits to wait for human review.
    """
    import yaml as _yaml
    from datetime import datetime, timezone
    from _branching import branch_name as _branch_name

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

    contracts.sort(key=lambda t: t[1].get("episode_number") or 9999)

    if not contracts:
        raise RuntimeError(
            f"Phase 0f: no chapter contracts under {contracts_dir}. "
            "Phase 0d should have produced them."
        )

    tiers = {c[1].get("length_target", "extended") for c in contracts}
    if len(tiers) == 1:
        length_tier = next(iter(tiers))
        tier_rationale = "All chapters target the same length tier — series is balanced."
    else:
        length_tier = "MIXED · author resolves"
        tier_rationale = (
            f"Chapters declare mixed tiers ({sorted(tiers)}). Pick one in the "
            "contracts before resuming."
        )

    LENGTH_CUE = {
        "short_dive": '"target a 12–18 minute conversation"',
        "extended": '"target a 30–45 minute conversation"',
        "longer": '"target a 45–60 minute conversation"',
    }
    HOST_DISPLAY = {
        "curious_mind + scholar_companion": "Mentor + Scholar Companion",
        "advocate_a + advocate_b + arbiter": "Advocate A + Advocate B + Arbiter",
        "advocate + arbiter": "Advocate + Arbiter",
        "narrator + companion": "Narrator + Companion",
        "interviewer + subject": "Interviewer + Subject",
    }

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
        customize = (
            f"`episodes/EP{ch_num:02d}-{slug}.txt`" if isinstance(ch_num, int)
            else f"`episodes/EP{ch_num}-{slug}.txt`"
        )
        rows.append(
            f"| {ch_num} | {title_} | {words} | {target} | **{fmt}** | "
            f"{essential} | {upload} | {customize} (TBD post-0g) | {length_cue} | {host_disp} |"
        )
    chapter_list_table = "\n".join(rows)

    ess_rows = [
        "| # | Slug | Essential? | Why |",
        "|---|---|---|---|",
    ]
    non_core = [(s, d) for s, d in contracts if d.get("essential", "core") != "core"]
    if non_core:
        for slug, data in non_core:
            ch_num = data.get("episode_number", "?")
            essential = data.get("essential", "?")
            why = data.get("essential_rationale", "(no rationale provided)")
            ess_rows.append(f"| {ch_num} | `{slug}` | **{essential}** | {why} |")
    else:
        ess_rows.append("| — | — | — | All episodes flagged `core`. No essentiality concerns. |")
    essentiality_table = "\n".join(ess_rows)

    first = contracts[0][1]
    audience = first.get("audience", "(not set — see chapter-contracts/<slug>.yml)").strip()
    angle = first.get("angle", "(not set)")

    host_rows = ["| Chapter | Host dynamic | Rationale |", "|---|---|---|"]
    for slug, data in contracts:
        hd = data.get("host_dynamic", "curious_mind + patient_teacher")
        rationale = data.get("host_dynamic_rationale", "")
        host_rows.append(f"| `{slug}` | {hd} | {rationale} |")
    host_dynamic_table = "\n".join(host_rows)

    state = read_state(book_dir) or {}
    config = state.get("config", {})
    unit_mode = config.get("unit_mode", "auto")

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
        branch=state.get("branch") or _branch_name(state.get("category"), book_slug),
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


# ─── Phase 0g — register series ──────────────────────────────────────────────


def phase_0g_register(book_dir: Path) -> None:
    """Append episode rows to PODCAST_ROOT/.skill/registry.md (idempotent).

    Deterministic deferred step — Phase 0d wrote per-chapter contracts;
    0g surfaces the series in the cross-book registry.
    """
    registry = REPO_ROOT / "content" / "podcast" / ".skill" / "registry.md"
    if not registry.exists():
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
