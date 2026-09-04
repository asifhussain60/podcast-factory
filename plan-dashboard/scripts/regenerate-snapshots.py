#!/usr/bin/env python3
"""
regenerate-snapshots.py — Python port of regenerate-snapshots.mjs.
Requires only stdlib + PyYAML (already present in the pipeline venv).

Run from repo root or plan-dashboard/:
    python3 plan-dashboard/scripts/regenerate-snapshots.py
"""

import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).parent
APP = HERE.parent
REPO = APP.parent
DATA = APP / "src" / "data"
CONTENT = REPO / "content"
# Buckets first, then the legacy trees. See the long note on BOOK_ROOTS in
# regenerate-snapshots.mjs — this is its exact mirror. Short version: the single
# `content/drafts` constant that used to live here named a directory deleted on
# 2026-06-04, so "books in flight" had been a structural zero ever since.
# Pinned to scripts/podcast/_content_types.py::BUCKETS — see the note on the same
# constant in regenerate-snapshots.mjs. Being pinned to that mirror alone is what
# let "Supplications" go missing from both for three weeks.
BUCKETS = ("Islamic", "Technical", "Fiction", "Guides", "Supplications", "Sessions", "Audiobook")
BOOK_ROOTS = tuple(CONTENT / b for b in BUCKETS) + (
    CONTENT / "drafts",
    CONTENT / "published" / "books",
)
PLAN_YAML = REPO / "_workspace" / "plan" / "refactor" / "plan.yaml"
WAVE_ACCEPTANCE = REPO / "_workspace" / "plan" / "operations" / "wave-acceptance-checklist.md"
WAVE_EVENTS = REPO / "_workspace" / "plan" / "refactor" / "wave-execution-events.jsonl"
SENTINEL = APP / ".snapshot-version"

# An agent entry's DERIVED fields are re-read from its spec on every run; only
# these are hand-authored in the JSON and therefore merge-preserved. Keep this
# list identical to AGENT_CURATED_FIELDS in regenerate-snapshots.mjs.
AGENT_CURATED_FIELDS = (
    "icon",
    "tone",
    "boundary_in",
    "boundary_out",
    "does_not",
    "cost_profile",
    "failure_mode",
)

WAVE_NUM_BY_LETTER = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def head_commit_iso():
    """Committer date of HEAD (ISO 8601). Console-log only as of 2026-08-05 —
    it used to be stamped into the tracked snapshots too, which meant a file
    could never carry its own not-yet-created commit hash and every run
    produced a metadata-only diff on the NEXT commit, forever. Not written to
    disk anymore.
    """
    try:
        out = subprocess.check_output(
            ["git", "-C", str(REPO), "log", "-1", "--format=%cI"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        return out or now_iso()
    except Exception:
        return now_iso()


def read_json(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def write_json(p, data):
    # ensure_ascii=False mirrors JSON.stringify in regenerate-snapshots.mjs, which
    # emits raw UTF-8. Escaping here would rewrite every em dash as a \\u escape,
    # so a machine without node and a machine with node would thrash these JSONs
    # back and forth on every commit.
    Path(p).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def current_commit():
    try:
        return subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def books_shipped():
    """The published shelf, with episode counts.

    Exact mirror of ``booksShipped`` in regenerate-snapshots.mjs — see the note there.
    Short version: this field was carried forward and computed by nothing, so the
    Overview hero opened with "0 books published, 0 episodes" over two finished books
    and twenty-eight episodes on disk.
    """
    out = []
    for slug in list_books():
        d = book_dir(slug)
        if d is None:
            continue
        state = read_json(d / "_system" / "orchestrator-state.json")
        if not state or state.get("status") != "published":
            continue
        title = book_title(d, slug)
        # One episode is one `EP##-*.txt` framing file. NOT the sibling directories:
        # some books carry a per-episode folder as well and some do not, so counting
        # directories reported 0 for a 20-episode book and double for a 4-episode one.
        episodes = 0
        try:
            episodes = sum(1 for e in (d / "episodes").iterdir() if e.is_file() and re.match(r"^EP\d+.*\.txt$", e.name))
        except Exception:
            pass  # a published book with no episode folder counts zero, not undefined
        out.append(
            {
                "slug": slug,
                "title": title,
                "shipped": state.get("published_at"),
                "episodes": episodes,
            }
        )
    return out


def burn_30d_usd():
    """Real money spent in the 30 days before HEAD, in dollars.

    Exact mirror of ``burn30dUsd`` in regenerate-snapshots.mjs — see the long note
    there. Short version: the Roadmap's "Spend / 30 Days" card summed a key the
    generator never wrote and rendered the resulting zero as a measurement, while the
    per-book ``cost-ledger.jsonl`` files held the priced rows all along. The window
    ends at HEAD's COMMIT time, not wall clock, so an unchanged commit regenerates to
    a byte-identical file. Cents accumulate as integers so the two generators cannot
    drift apart on float addition.
    """
    try:
        end = datetime.fromisoformat(head_commit_iso().replace("Z", "+00:00"))
    except Exception:
        return 0
    start = end - timedelta(days=30)
    cents = 0
    for slug in list_books():
        d = book_dir(slug)
        if d is None:
            continue
        ledger = d / "_system" / "cost-ledger.jsonl"
        try:
            raw = ledger.read_text()
        except Exception:
            continue  # a book that has cost nothing yet has no ledger
        for line in raw.split("\n"):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue  # a torn last line mid-write is not a reason to report nothing
            try:
                usd = float(row.get("cost_usd") or 0)
            except Exception:
                continue
            if not usd:
                continue
            try:
                t = datetime.fromisoformat(str(row.get("ts") or "").replace("Z", "+00:00"))
            except Exception:
                continue
            if t < start or t > end:
                continue
            cents += round(usd * 100)
    return js_number(cents / 100)


def js_number(value):
    """Render a rounded float the way JSON.stringify renders a JS number.

    JS has one number type, so a whole-dollar burn serialises as ``111``; Python's
    ``cents / 100`` is always a float and ``json.dumps`` writes ``111.0``. Every
    rounded money field passes through here so the two generators stay byte-equal.
    """
    return int(value) if float(value).is_integer() else value


def recent_wave_events(limit=15):
    try:
        lines = Path(WAVE_EVENTS).read_text().splitlines()
        rows = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
        return list(reversed(rows[-limit:]))
    except Exception:
        return []


def parse_checklist_done_waves(md):
    done = set()
    if not md:
        return done
    current_wave = None
    wave_rows = wave_checked = 0

    def flush():
        if current_wave is not None and wave_rows > 0 and wave_rows == wave_checked:
            done.add(current_wave)

    for raw in md.splitlines():
        line = raw.strip()
        m = re.match(r"^##\s+Wave\s+(\d+)\b", line, re.IGNORECASE)
        if m:
            flush()
            current_wave = int(m.group(1))
            wave_rows = wave_checked = 0
            continue
        m = re.match(r"^- \[([ xX])\]\s+\*\*P\d+(?:\.\d+\w?)?\*\*", line)
        if current_wave is not None and m:
            wave_rows += 1
            if m.group(1).lower() == "x":
                wave_checked += 1
    flush()
    return done


# One vocabulary out, whatever went in. See the long note on `normalizeStepStatus`
# in regenerate-snapshots.mjs — this is its exact mirror, and the two are
# byte-parity-tested by tests/test_snapshot_regenerator_parity.py. Short version:
# plan.yaml says "finished" eight different ways, the site asks for exactly one of
# them, and on 2026-07-30 that made the Roadmap read 56/140 done when 117 were.
STATUS_DONE = frozenset(
    {
        "complete",
        "completed",
        "done",
        "shipped",
        "built_committed",
        "pilot_complete",
        "resolved",
    }
)


def normalize_step_status(raw):
    s = str(raw or "").strip().lower()
    if not s:
        return "pending"
    # `completed_2026_05_28` and friends: a done marker with the date welded on.
    if s in STATUS_DONE or s.startswith("completed_"):
        return "complete"
    if s in ("in_progress", "in-progress"):
        return "in_progress"
    if s == "deferred":
        return "deferred"
    return "pending"


def derive_step_status(step, wave):
    if isinstance(step.get("status"), str) and step["status"].strip():
        return normalize_step_status(step["status"])
    wave_status = str(wave.get("execution_status") or "").lower()
    if wave_status.startswith("completed"):
        return "complete"
    return "pending"


def list_books():
    """Every book slug, across every bucket. Sorted, so the two generators agree."""
    slugs = set()
    for root in BOOK_ROOTS:
        try:
            entries = list(root.iterdir())
        except Exception:
            continue  # a bucket with no books yet, or a legacy tree already gone
        for e in entries:
            if not e.is_dir():
                continue
            if e.name.startswith("_"):
                continue
            if e.name != e.name.lower():
                continue
            slugs.add(e.name)
    return sorted(slugs)


def book_dir(slug):
    """The book's folder, wherever it lives. None when no root holds it."""
    for root in BOOK_ROOTS:
        p = root / slug
        try:
            if p.is_dir():
                return p
        except Exception:
            pass
    return None


def book_title(d, slug):
    """The book's own name, from meta.yml.

    The state file has no title field at all, so a caller that reaches for one
    there prints the slug forever — which is what `books_in_flight` did until
    2026-08-06 while the shipped shelf beside it read the real title. One helper
    now, so the two lists cannot disagree about what a book is called.

    MIRROR: regenerate-snapshots.mjs::bookTitle.
    """
    try:
        meta = yaml.safe_load((d / "meta.yml").read_text()) or {}
        if isinstance(meta.get("title"), str) and meta["title"].strip():
            return meta["title"].strip()
    except Exception:
        pass  # no meta.yml: the slug is a worse name than the title, but it is a name
    return slug


def book_kind(d):
    """What KIND of book this is — its `content_profile`.

    Read from `_system/series-config.yaml` rather than guessed from the bucket:
    a `books`-category item can be Islamic or Fiction, which is exactly why the
    bucket resolver takes the profile and not the category.

    MIRROR: regenerate-snapshots.mjs::bookKind.
    """
    try:
        cfg = yaml.safe_load((d / "_system" / "series-config.yaml").read_text()) or {}
        if isinstance(cfg.get("content_profile"), str) and cfg["content_profile"].strip():
            return cfg["content_profile"].strip()
    except Exception:
        pass  # no series-config: "unknown" is honest, a guessed profile is not
    return "unknown"


def book_state(slug):
    d = book_dir(slug)
    if d is None:
        return None
    p = d / "_system" / "orchestrator-state.json"
    try:
        if not p.is_file():
            return None
        data = json.loads(p.read_text())
        return {
            "slug": slug,
            "phase": data.get("phase", "unknown"),
            "phase_status": data.get("phase_status", "unknown"),
            "last_completed_phase": data.get("last_completed_phase"),
        }
    except Exception:
        return None


def read_plan_yaml():
    if not PLAN_YAML.exists():
        return None
    try:
        return yaml.safe_load(PLAN_YAML.read_text())
    except Exception:
        return None


def merge_dashboard():
    existing = read_json(DATA / "dashboard-snapshot.json") or {"roadmap": [], "waves": [], "debt": [], "metrics": {}}

    done_waves = set()
    try:
        done_waves = parse_checklist_done_waves(Path(WAVE_ACCEPTANCE).read_text())
    except Exception:
        pass

    slugs = list_books()
    states = [s for s in (book_state(sl) for sl in slugs) if s]
    in_flight = []
    for s in states:
        if s["phase"] == "done" or s["phase_status"] in ("shipped", "merged"):
            continue
        existing_match = next((b for b in (existing.get("books_in_flight") or []) if b["slug"] == s["slug"]), None)
        d = book_dir(s["slug"])
        in_flight.append(
            {
                "slug": s["slug"],
                "title": book_title(d, s["slug"]) if d else s["slug"],
                # DISK WINS. These preferred the previously-snapshotted value, so
                # the first phase a book was ever seen in became the phase it
                # displayed forever: `degrees-of-excellence` sat at
                # "per-chapter-slides/running" for days after finishing
                # 0book-render. A carried-forward value is only right for a field
                # the state file does not hold — which is why cost_to_date_usd
                # below still carries and these two no longer do.
                "phase": s["phase"],
                "phase_status": s["phase_status"],
                "cost_to_date_usd": (existing_match or {}).get("cost_to_date_usd") or 0,
                "kind": book_kind(d) if d else "unknown",
            }
        )

    plan = read_plan_yaml()
    roadmap = list(existing.get("roadmap") or [])
    # Every wave-shaped list in plan.yaml (waves, waves_ghj, waves_o_ph, and any
    # future waves_* section) — entries are dicts with an id + steps. Reading only
    # the first two lists silently hid waves O/PH/WM/SD+ from the dashboard.
    # Document order, NOT sorted() — the roadmap is ordered by wave_order below,
    # and plan.yaml's own sequencing is the authored order. Sorting the keys put
    # waves_bpv2 ahead of waves_ghj, which reordered the whole roadmap away from
    # what the .mjs mirror (insertion order) emits.
    wave_lists = []
    if plan:
        for key, value in plan.items():
            if key == "waves" or key.startswith("waves_"):
                wave_lists.extend(list(value or []))
    all_waves = [w for w in wave_lists if isinstance(w, dict) and w.get("id")]

    if all_waves:
        valid_ids = {step["id"] for wave in all_waves for step in (wave.get("steps") or [])}
        roadmap = [r for r in roadmap if r["id"] in valid_ids]
        existing_by_id = {r["id"]: r for r in roadmap}
        wave_order = [w["id"] for w in all_waves]

        for wave in all_waves:
            for step in wave.get("steps") or []:
                prev = existing_by_id.get(step["id"]) or {}
                entry = {
                    **prev,
                    "id": step["id"],
                    "wave": wave["id"],
                    "title": step.get("title") or prev.get("title") or step["id"],
                    "status": derive_step_status(step, wave),
                    "tier": step.get("tier") or prev.get("tier") or "T1",
                    "depends_on": step.get("depends_on") or prev.get("depends_on") or [],
                    "plain": step.get("plain") or prev.get("plain") or "",
                    "tools": step.get("tools") or prev.get("tools") or [],
                }
                # JSON.stringify drops undefined keys, so the .mjs mirror omits
                # last_touched entirely when neither source carries one. Emitting
                # an explicit null here would diverge from it.
                last_touched = step.get("last_touched") or prev.get("last_touched")
                if last_touched is not None:
                    entry["last_touched"] = last_touched
                wave_num = WAVE_NUM_BY_LETTER.get(wave["id"])
                if wave_num and wave_num in done_waves:
                    entry["status"] = "complete"

                existing_by_id[step["id"]] = entry
                if step["id"] not in {r["id"] for r in roadmap}:
                    roadmap.append(entry)

        roadmap = [existing_by_id.get(r["id"], r) for r in roadmap]
        roadmap.sort(key=lambda r: (wave_order.index(r["wave"]) if r["wave"] in wave_order else 999, str(r["id"])))

    # Wave metadata (id/name/plain) drives the PlanDesign grouping — rebuild it
    # from plan.yaml so an empty `waves` array can never blank the Roadmap page.
    # Letters collide across the waves/waves_ghj groups, so keep one entry per
    # id and prefer the entry that actually carries roadmap steps.
    waves_meta = list(existing.get("waves") or [])
    if all_waves:
        prev_by_id = {w.get("id"): w for w in waves_meta if isinstance(w, dict)}
        picked = {}
        order = []
        for w in all_waves:
            has_steps = bool(w.get("steps"))
            if w["id"] not in picked:
                order.append(w["id"])
                picked[w["id"]] = w
            elif has_steps and not picked[w["id"]].get("steps"):
                picked[w["id"]] = w
        waves_meta = []
        for wid in order:
            w = picked[wid]
            if not w.get("steps"):
                continue  # empty band — no roadmap steps to show
            plain = str(w.get("summary") or "").strip().split("\n")[0] or (prev_by_id.get(wid) or {}).get("plain", "")
            waves_meta.append(
                {
                    "id": wid,
                    "name": w.get("name") or wid,
                    "plain": plain,
                }
            )

    merged = {
        **existing,
        # Deliberately NOT the filename: both regenerators must emit byte-identical
        # snapshots, so neither may stamp which of the two produced this run.
        "generator": "regenerate-snapshots",
        "roadmap": roadmap,
        "waves": waves_meta,
        "books_in_flight": in_flight,
        "metrics": {**(existing.get("metrics") or {}), "burn_30d_usd": burn_30d_usd()},
        "books_shipped": books_shipped(),
        "wave_execution_events": recent_wave_events(),
    }
    # Legacy fields from before 2026-08-05 — see head_commit_iso()'s docstring.
    # Stripped here (not just stopped going forward) so one regen run cleans an
    # already-committed file.
    merged.pop("generated_at", None)
    merged.pop("source_commit", None)
    write_json(DATA / "dashboard-snapshot.json", merged)
    return merged


def merge_architecture():
    p = DATA / "architecture-snapshot.json"
    snap = read_json(p) or {"phases": [], "agents": [], "layers": [], "adrs": [], "modules": [], "archetypes": []}

    # Agents from infra/claude-agents/*.md
    agents_dir = REPO / "infra" / "claude-agents"
    existing_agents = {a["id"]: a for a in (snap.get("agents") or [])}
    agents = []
    try:
        agent_files = sorted(f for f in os.listdir(agents_dir) if f.endswith(".md") and f != "_README.md")
    except Exception:
        agent_files = []

    for f in agent_files:
        agent_id = f[:-3]
        prev = existing_agents.get(agent_id) or {}
        try:
            content = (agents_dir / f).read_text()
            fm_match = re.match(r"^---\n([\s\S]*?)\n---", content)
            fm = {}
            if fm_match:
                try:
                    fm = yaml.safe_load(fm_match.group(1)) or {}
                except Exception:
                    pass
            desc = str(fm.get("description") or "")
            title_case = " ".join(w[0].upper() + w[1:] for w in agent_id.split("-"))
            agents.append(
                {
                    "id": agent_id,
                    "name": title_case,
                    "role": desc.split(".")[0][:80],
                    "icon": "robot",
                    "tone": "neutral",
                    "plain": desc[:237] + "…" if len(desc) > 240 else desc,
                    "what_it_knows": f"See infra/claude-agents/{f}",
                    "boundary_in": "",
                    "boundary_out": "",
                    "does_not": "",
                    "cost_profile": "varies",
                    "failure_mode": "surfaces error and halts",
                }
            )
            for key in AGENT_CURATED_FIELDS:
                if prev.get(key):
                    agents[-1][key] = prev[key]
        except Exception:
            # A transient read failure must not delete an agent already recorded.
            if prev:
                agents.append(prev)

    # ADRs from architecture.md
    arch_path = REPO / "_workspace" / "plan" / "architecture.md"
    adrs = list(snap.get("adrs") or [])
    if arch_path.exists():
        md = arch_path.read_text()
        existing_adrs = {a["id"]: a for a in adrs}
        matches = re.findall(r"\|\s*(DR-\d+)\s*\|\s*\*\*([^*]+)\*\*", md)
        if matches:
            adrs = []
            for adr_id, title in matches:
                adr_id = adr_id.strip()
                title = title.strip()
                adrs.append(existing_adrs.get(adr_id) or {"id": adr_id, "title": title, "plain": title})

    merged = {
        **snap,
        "agents": agents,
        "adrs": adrs,
    }
    merged.pop("generated_at", None)
    merged.pop("source_commit", None)
    write_json(p, merged)


def touch_existing(name):
    p = DATA / name
    data = read_json(p)
    if not data:
        return
    data.pop("generated_at", None)
    data.pop("source_commit", None)
    write_json(p, data)


def main():
    dash = merge_dashboard()
    merge_architecture()
    touch_existing("infrastructure-snapshot.json")

    try:
        SENTINEL.write_text(head_commit_iso() + "\n")
    except Exception:
        pass

    print(f"snapshots regenerated @ {head_commit_iso()}")
    print(f"  source_commit: {current_commit()}")
    print(f"  books in flight: {len(dash['books_in_flight'])}")
    print(f"  roadmap steps: {len(dash['roadmap'])}")


if __name__ == "__main__":
    main()
