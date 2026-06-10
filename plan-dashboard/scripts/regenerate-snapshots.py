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
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).parent
APP = HERE.parent
REPO = APP.parent
DATA = APP / "src" / "data"
DRAFTS = REPO / "content" / "drafts"
PLAN_YAML = REPO / "_workspace" / "plan" / "refactor" / "plan.yaml"
WAVE_ACCEPTANCE = REPO / "_workspace" / "plan" / "operations" / "wave-acceptance-checklist.md"
WAVE_EVENTS = REPO / "_workspace" / "plan" / "refactor" / "wave-execution-events.jsonl"
SENTINEL = APP / ".snapshot-version"

WAVE_NUM_BY_LETTER = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def read_json(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def write_json(p, data):
    Path(p).write_text(json.dumps(data, indent=2) + "\n")


def current_commit():
    try:
        return subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def recent_commits():
    try:
        out = subprocess.check_output(
            ["git", "-C", str(REPO), "log", "-n", "10",
             "--pretty=format:%h|%s|%ad", "--date=short"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
        rows = []
        for line in out.splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                rows.append({"sha": parts[0], "subject": parts[1], "date": parts[2]})
        return rows
    except Exception:
        return []


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


def derive_step_status(step, wave):
    if isinstance(step.get("status"), str) and step["status"].strip():
        return step["status"].strip()
    wave_status = str(wave.get("execution_status") or "").lower()
    if wave_status.startswith("completed"):
        return "complete"
    return "pending"


def list_books():
    try:
        return [
            e.name for e in sorted(DRAFTS.iterdir())
            if e.is_dir() and not e.name.startswith("_") and e.name == e.name.lower()
        ]
    except Exception:
        return []


def book_state(slug):
    p = DRAFTS / slug / "_system" / "orchestrator-state.json"
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
    existing = read_json(DATA / "dashboard-snapshot.json") or {
        "roadmap": [], "waves": [], "debt": [], "metrics": {}
    }

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
        existing_match = next(
            (b for b in (existing.get("books_in_flight") or []) if b["slug"] == s["slug"]),
            None
        )
        in_flight.append({
            "slug": s["slug"],
            "title": (existing_match or {}).get("title") or s["slug"],
            "phase": (existing_match or {}).get("phase") or s["phase"],
            "phase_status": (existing_match or {}).get("phase_status") or s["phase_status"],
            "cost_to_date_usd": (existing_match or {}).get("cost_to_date_usd") or 0,
            "kind": (existing_match or {}).get("kind") or "unknown",
        })

    plan = read_plan_yaml()
    roadmap = list(existing.get("roadmap") or [])
    all_waves = [
        w for w in (list(plan.get("waves") or []) + list(plan.get("waves_ghj") or []))
        if isinstance(w, dict) and w.get("id")
    ] if plan else []

    if all_waves:
        valid_ids = {step["id"] for wave in all_waves for step in (wave.get("steps") or [])}
        roadmap = [r for r in roadmap if r["id"] in valid_ids]
        existing_by_id = {r["id"]: r for r in roadmap}
        wave_order = [w["id"] for w in all_waves]

        for wave in all_waves:
            for step in (wave.get("steps") or []):
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
                    "last_touched": step.get("last_touched") or prev.get("last_touched"),
                }
                wave_num = WAVE_NUM_BY_LETTER.get(wave["id"])
                if wave_num and wave_num in done_waves:
                    entry["status"] = "complete"

                existing_by_id[step["id"]] = entry
                if step["id"] not in {r["id"] for r in roadmap}:
                    roadmap.append(entry)

        roadmap = [existing_by_id.get(r["id"], r) for r in roadmap]
        roadmap.sort(key=lambda r: (
            wave_order.index(r["wave"]) if r["wave"] in wave_order else 999,
            str(r["id"])
        ))

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
            plain = str(w.get("summary") or "").strip().split("\n")[0] \
                or (prev_by_id.get(wid) or {}).get("plain", "")
            waves_meta.append({
                "id": wid,
                "name": w.get("name") or wid,
                "plain": plain,
            })

    merged = {
        **existing,
        "generated_at": now_iso(),
        "source_commit": current_commit(),
        "generator": "regenerate-snapshots.py",
        "roadmap": roadmap,
        "waves": waves_meta,
        "books_in_flight": in_flight,
        "books_shipped": existing.get("books_shipped", []),
        "recent_commits": recent_commits(),
        "wave_execution_events": recent_wave_events(),
    }
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
        if agent_id in existing_agents:
            agents.append(existing_agents[agent_id])
            continue
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
            agents.append({
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
            })
        except Exception:
            pass

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

    merged = {**snap, "generated_at": now_iso(), "source_commit": current_commit(), "agents": agents, "adrs": adrs}
    write_json(p, merged)


def touch_existing(name):
    p = DATA / name
    data = read_json(p)
    if not data:
        return
    data["generated_at"] = now_iso()
    data["source_commit"] = current_commit()
    write_json(p, data)


def main():
    dash = merge_dashboard()
    merge_architecture()
    touch_existing("infrastructure-snapshot.json")

    try:
        SENTINEL.write_text(now_iso() + "\n")
    except Exception:
        pass

    print(f"snapshots regenerated @ {dash['generated_at']}")
    print(f"  source_commit: {dash['source_commit']}")
    print(f"  books in flight: {len(dash['books_in_flight'])}")
    print(f"  roadmap steps: {len(dash['roadmap'])}")
    print(f"  recent commits: {len(dash['recent_commits'])}")


if __name__ == "__main__":
    main()
