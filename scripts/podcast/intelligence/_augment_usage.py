"""Episode augmentation usage-ledger helpers."""

from __future__ import annotations

import json
from pathlib import Path

_EPISODE_LEDGER_NAME = "episode-augment-ledger.json"


def load_episode_ledger(book_dir: Path) -> dict:
    """Load the per-episode augmentation ledger ({episodes: {slug: {...}}})."""
    path = episode_ledger_path(book_dir)
    if not path.exists():
        return {"episodes": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("episodes"), dict):
            return data
    except Exception:
        pass
    return {"episodes": {}}


def episode_ledger_path(book_dir: Path) -> Path:
    return book_dir / "_system" / _EPISODE_LEDGER_NAME


def atoms_used_in_other_episodes(ledger: dict, current_slug: str) -> set[str]:
    """Union of atom IDs injected into every episode except the current slug."""
    used: set[str] = set()
    for slug, entry in (ledger.get("episodes") or {}).items():
        if slug == current_slug:
            continue
        used.update(entry.get("atoms_injected", []) or [])
    return used


def usage_entry(atom: dict, reason: str) -> dict:
    """Compact, review-friendly usage metadata for the anti-repetition ledger."""
    body = atom.get("body") if isinstance(atom.get("body"), dict) else {}
    return {
        "atom_id": atom.get("id"),
        "type": str(atom.get("id", "")).split(":", 1)[0],
        "reason": reason,
        "topic_tags": sorted(set(body.get("topic_tags") or [])),
        "quran_refs": sorted(set(body.get("quran_refs") or [])),
        "source_kind": body.get("source_kind"),
    }


def record_episode_atoms(
    book_dir: Path,
    episode_slug: str,
    atom_ids: list[str],
    *,
    atom_usage: list[dict] | None = None,
) -> None:
    """Write/overwrite this episode's injected-atom list in the ledger."""
    if not episode_slug:
        return
    ledger = load_episode_ledger(book_dir)
    ledger.setdefault("episodes", {})[episode_slug] = {
        "atoms_injected": sorted(set(atom_ids)),
        "atom_usage": sorted(atom_usage or [], key=lambda row: str(row.get("atom_id", ""))),
    }
    path = episode_ledger_path(book_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False), encoding="utf-8")
