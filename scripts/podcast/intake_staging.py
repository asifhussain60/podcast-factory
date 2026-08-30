"""intake_staging.py — staging lifecycle for the Screen-1 file-upload intake (Q6).

Uploaded files (mixed types: PDF / audio / text) land in a per-session STAGING
area and are committed into the canonical ``_source/`` directory ONLY on the final
confirm (Screen 4) — so a half-finished or abandoned intake never leaves partial
files in the real content tree (the "atomically committed on confirm" requirement).

Folder-name safety: the staging root is resolved through ``_paths.SYSTEM_ROOT`` —
NOT a hardcoded ``content``/``library`` literal — so it is ``content/_system/staging/``
today and follows the deferred ``content/`` → ``library/`` rename (Phase 5)
automatically with zero edits.

Each session is a token dir holding the raw files + a ``.staging.json`` manifest
(ordered files, each with id / filename / role). Roles (Q7): exactly one
``primary_source`` per session; audio-as-primary is flagged (needs transcription).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths

ALLOWED_EXT: frozenset[str] = frozenset(
    {
        ".pdf",
        ".mp3",
        ".m4a",
        ".wav",
        ".txt",
        ".md",
        ".docx",
    }
)
AUDIO_EXT: frozenset[str] = frozenset({".mp3", ".m4a", ".wav"})

ROLES: tuple[str, ...] = (
    "primary_source",
    "source_recording",
    "pronunciation_reference",
    "supplementary_text",
)
DEFAULT_ROLE = "supplementary_text"
MANIFEST_NAME = ".staging.json"
# Raised from 500 MB (2026-08-30) — real sermon-length lecture recordings routinely
# exceed it (e.g. a ~570 MB .m4a part). Buffered fully into server memory by the
# upload endpoint (see upload.ts), so this stays a finite cap rather than unbounded —
# 4 GB is comfortably above any file seen so far and well inside what a local Node
# process can safely hold.
MAX_FILE_BYTES = 4 * 1024 * 1024 * 1024  # 4 GB per file


# ── paths ────────────────────────────────────────────────────────────────────
def staging_root() -> Path:
    """Resolver-based staging root (rename-safe): <SYSTEM_ROOT>/staging."""
    return _paths.SYSTEM_ROOT / "staging"


def staging_dir(token: str) -> Path:
    """The per-session staging dir. Guards against path traversal in the token."""
    if not token or "/" in token or "\\" in token or token.startswith("."):
        raise ValueError(f"invalid staging token {token!r}")
    return staging_root() / token


def _manifest_path(token: str) -> Path:
    return staging_dir(token) / MANIFEST_NAME


# ── validation ───────────────────────────────────────────────────────────────
def is_allowed(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXT


def role_for_default(filename: str) -> str:
    """Auto-pick a sensible role: PDFs default to primary, others to supplementary."""
    return "primary_source" if Path(filename).suffix.lower() == ".pdf" else DEFAULT_ROLE


# ── session lifecycle ────────────────────────────────────────────────────────
def new_session() -> str:
    """Create a fresh staging session and return its token."""
    token = uuid.uuid4().hex[:16]
    d = staging_dir(token)
    d.mkdir(parents=True, exist_ok=True)
    _write_manifest(token, {"token": token, "created": time.time(), "files": []})
    return token


def _read_manifest(token: str) -> dict[str, Any]:
    p = _manifest_path(token)
    if not p.is_file():
        return {"token": token, "files": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"token": token, "files": []}
    except Exception:
        return {"token": token, "files": []}


def _write_manifest(token: str, manifest: dict[str, Any]) -> None:
    d = staging_dir(token)
    d.mkdir(parents=True, exist_ok=True)
    p = _manifest_path(token)
    fd, tmp = tempfile_mkstemp(d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def tempfile_mkstemp(d: Path) -> tuple[int, str]:
    import tempfile

    return tempfile.mkstemp(dir=str(d), prefix=".staging.", suffix=".tmp")


def register_file(token: str, filename: str, *, role: str | None = None) -> dict[str, Any]:
    """Record a staged file in the manifest (bytes are written by the caller).

    The safe on-disk name is the file id + original extension; the original
    filename is preserved in the manifest for display. Returns the file record.
    """
    if not is_allowed(filename):
        raise ValueError(f"file type not allowed: {filename!r} (allowed: {sorted(ALLOWED_EXT)})")
    role = role or role_for_default(filename)
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r} (expected one of {ROLES})")
    manifest = _read_manifest(token)
    file_id = uuid.uuid4().hex[:12]
    ext = Path(filename).suffix.lower()
    record = {
        "id": file_id,
        "filename": Path(filename).name,
        "stored_name": f"{file_id}{ext}",
        "role": role,
        "ext": ext,
    }
    manifest.setdefault("files", []).append(record)
    _write_manifest(token, manifest)
    return record


def stored_path(token: str, file_id: str) -> Path | None:
    """Absolute path where a staged file's bytes should/do live."""
    for f in _read_manifest(token).get("files", []):
        if f.get("id") == file_id:
            return staging_dir(token) / f["stored_name"]
    return None


def set_role(token: str, file_id: str, role: str) -> dict[str, Any]:
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}")
    manifest = _read_manifest(token)
    for f in manifest.get("files", []):
        if f.get("id") == file_id:
            f["role"] = role
            _write_manifest(token, manifest)
            return f
    raise KeyError(f"no staged file {file_id!r}")


def remove_file(token: str, file_id: str) -> None:
    manifest = _read_manifest(token)
    kept = []
    for f in manifest.get("files", []):
        if f.get("id") == file_id:
            sp = staging_dir(token) / f["stored_name"]
            if sp.exists():
                sp.unlink()
        else:
            kept.append(f)
    manifest["files"] = kept
    _write_manifest(token, manifest)


def list_files(token: str) -> list[dict[str, Any]]:
    return _read_manifest(token).get("files", [])


# ── role validation (Q7) ─────────────────────────────────────────────────────
def validate_roles(token: str) -> dict[str, Any]:
    """Return {ok, errors[], warnings[]} for the session's role assignment.

    Hard rule: exactly one primary_source. Warn: audio assigned as primary
    (needs transcription before it can drive the pipeline).
    """
    files = list_files(token)
    primaries = [f for f in files if f.get("role") == "primary_source"]
    errors: list[str] = []
    warnings: list[str] = []
    if len(primaries) == 0:
        errors.append("no primary_source — exactly one file must be the primary source")
    elif len(primaries) > 1:
        errors.append(f"{len(primaries)} primary sources — exactly one is allowed")
    for p in primaries:
        if p.get("ext") in AUDIO_EXT:
            warnings.append(f"{p['filename']}: audio as primary needs transcription first")
    return {"ok": not errors, "errors": errors, "warnings": warnings}


# ── commit / sweep ───────────────────────────────────────────────────────────
def commit(token: str, target_source_dir: Path) -> list[dict[str, Any]]:
    """Move staged files into ``target_source_dir`` under their ORIGINAL names.

    Returns the role-tagged ``sources:`` list (path relative to the target's parent
    + role) for the work/volume manifest. The staging dir is removed after commit.
    Raises if role validation fails (no silent partial commit).
    """
    v = validate_roles(token)
    if not v["ok"]:
        raise ValueError("cannot commit — " + "; ".join(v["errors"]))
    target_source_dir = Path(target_source_dir)
    target_source_dir.mkdir(parents=True, exist_ok=True)
    sources: list[dict[str, Any]] = []
    for f in list_files(token):
        src = staging_dir(token) / f["stored_name"]
        dst = target_source_dir / f["filename"]
        if src.exists():
            shutil.move(str(src), str(dst))
        sources.append({"path": f["filename"], "role": f["role"]})
    shutil.rmtree(staging_dir(token), ignore_errors=True)
    return sources


def sweep_stale(*, ttl_hours: float = 24.0, now: float | None = None) -> list[str]:
    """Remove staging sessions older than ttl_hours. Returns swept tokens."""
    root = staging_root()
    if not root.is_dir():
        return []
    now = now if now is not None else time.time()
    swept: list[str] = []
    for d in root.iterdir():
        if not d.is_dir():
            continue
        manifest = _read_manifest(d.name)
        created = manifest.get("created")
        age_h = (now - created) / 3600.0 if isinstance(created, (int, float)) else None
        if age_h is None:
            # No created stamp — fall back to dir mtime.
            age_h = (now - d.stat().st_mtime) / 3600.0
        if age_h > ttl_hours:
            shutil.rmtree(d, ignore_errors=True)
            swept.append(d.name)
    return swept


# ── CLI (JSON contract for the Astro upload endpoint) ────────────────────────
def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="intake staging lifecycle")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("new")
    sp = sub.add_parser("path")
    sp.add_argument("token")
    rg = sub.add_parser("register")
    rg.add_argument("token")
    rg.add_argument("filename")
    rg.add_argument("--role")
    ls = sub.add_parser("list")
    ls.add_argument("token")
    rl = sub.add_parser("set-role")
    rl.add_argument("token")
    rl.add_argument("file_id")
    rl.add_argument("role")
    rm = sub.add_parser("remove")
    rm.add_argument("token")
    rm.add_argument("file_id")
    va = sub.add_parser("validate")
    va.add_argument("token")
    args = p.parse_args(argv)
    try:
        if args.cmd == "new":
            out = {"token": new_session()}
        elif args.cmd == "path":
            out = {"path": str(staging_dir(args.token))}
        elif args.cmd == "register":
            out = {
                "file": register_file(args.token, args.filename, role=args.role),
                "stored_path": str(stored_path(args.token, "") or ""),
            }
            # re-resolve stored path for the just-created id
            out["stored_path"] = str(stored_path(args.token, out["file"]["id"]))
        elif args.cmd == "list":
            out = {"files": list_files(args.token)}
        elif args.cmd == "set-role":
            out = {"file": set_role(args.token, args.file_id, args.role)}
        elif args.cmd == "remove":
            remove_file(args.token, args.file_id)
            out = {"removed": args.file_id}
        else:  # validate
            out = validate_roles(args.token)
    except (ValueError, KeyError) as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 2
    out.setdefault("ok", True)
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
