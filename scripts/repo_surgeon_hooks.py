"""repo_surgeon_hooks.py — every project script a Claude Code hook points at must exist.

Lives beside repo_surgeon_probe.py, not in it: the probe is at its DR-005 size ceiling.
"""

from __future__ import annotations

import json
import os


def check_hook_targets(probe) -> None:
    """Every project script a Claude Code hook points at must exist and be executable.
    A machine move once left .claude/hooks/ empty while settings.json still named four
    scripts in it, so the site smoke gate, the snapshot regen and the status injection
    all stopped running with no error anywhere."""
    raw = probe.read(".claude/settings.json")
    if not raw:
        return
    try:
        settings = json.loads(raw)
    except ValueError:
        return
    seen: set[str] = set()
    for entries in (settings.get("hooks") or {}).values():
        for entry in entries:
            for hook in entry.get("hooks", []):
                command = str(hook.get("command", ""))
                if not command.startswith("$CLAUDE_PROJECT_DIR/"):
                    continue
                rel = command.removeprefix("$CLAUDE_PROJECT_DIR/").split()[0]
                if rel in seen:
                    continue
                seen.add(rel)
                target = probe.root / rel
                if not target.is_file():
                    probe.add(
                        "P0",
                        "HK-MISSING",
                        f"hook command points at {rel}, which does not exist — the hook silently never runs",
                        ".claude/settings.json",
                        fingerprint=f"HK-MISSING:{rel}",
                    )
                elif not os.access(target, os.X_OK):
                    probe.add(
                        "P0",
                        "HK-NOT-EXECUTABLE",
                        f"hook script {rel} is not executable — the hook fails on every fire",
                        rel,
                        fingerprint=f"HK-NOT-EXECUTABLE:{rel}",
                    )
