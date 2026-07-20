"""_book_edits.py — Book Composer edits that survive a re-compose.

The Composer is the SINGULAR path for chapter modifications destined for the PDF.
That claim only holds if a Composer edit outlives the next pipeline run, and until
now it did not: `book-md.ts` writes `book/book.md` directly, and `compose_book_v2`
regenerates that file's layers (base -> augment -> voice) on every run. A human
edit was durable "in normal use" — meaning until anything upstream re-ran, at which
point it vanished with no report.

The fix is the sidecar pattern `_book_bridges.py` already established: store the
human's text durably in `_system/composer-edits.json` and REPLAY it as the final
compose step. Same two properties that module leans on:

  * IDEMPOTENT — replaying twice leaves the same file, because a replay rewrites
    a whole chapter body rather than appending to it. Convergence loops re-enter
    constantly.
  * ANCHORED BY HEADING, not by offset. A chapter's `## ` heading is stable across
    a re-voice; prose offsets rot the moment anything upstream changes.

Where this deliberately DIFFERS from bridges: a bridge that loses its anchor is
skipped, because a misplaced sentence is worse than a missing one. A Composer edit
is a whole chapter the human authored, so it is replayed even when the regenerated
base has moved underneath it — and the move is REPORTED as a conflict rather than
being papered over. Losing an author's chapter silently is the one outcome worse
than showing them a stale one.

Not an LLM step. Pure file I/O over two files.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

SIDECAR_NAME = "composer-edits.json"
SCHEMA = "podcast.composer-edits/v1"
_HEADING_RE = re.compile(r"(?m)^(##\s+.+)$")


def anchor_key(heading: str) -> str:
    """Normalize a heading to a comparable key.

    Mirror of `anchorKey` in `plan-dashboard/src/pages/api/studio/book-md.ts` and
    `lib/reader/composer.ts`. Keep the three in sync — a divergence here silently
    orphans every saved edit, because the replay simply finds no matching chapter.
    """
    return re.sub(r"^\d+\.\s*", "", re.sub(r"^#{1,6}\s+", "", re.sub(r"<[^>]+>", "", heading))).strip().lower()


def fingerprint(text: str) -> str:
    """Stable hash of a chapter body, whitespace-normalized."""
    return hashlib.sha256(" ".join((text or "").split()).encode("utf-8")).hexdigest()[:16]


def sidecar_path(book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / SIDECAR_NAME


def load_edits(book_dir: Path) -> dict[str, Any]:
    path = sidecar_path(book_dir)
    if not path.exists():
        return {"schema": SCHEMA, "edits": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"schema": SCHEMA, "edits": []}
    if not isinstance(data, dict) or not isinstance(data.get("edits"), list):
        return {"schema": SCHEMA, "edits": []}
    return data


def record_edit(
    book_dir: Path,
    *,
    chapter_key: str,
    body_md: str,
    base_fingerprint: str = "",
    saved_at: str = "",
) -> Path:
    """Persist one Composer chapter edit. Last write per chapter wins."""
    book_dir = Path(book_dir)
    data = load_edits(book_dir)
    edits = [e for e in data["edits"] if e.get("chapter_key") != chapter_key]
    edits.append(
        {
            "chapter_key": chapter_key,
            "body_md": body_md,
            "base_fingerprint": base_fingerprint,
            "saved_at": saved_at,
        }
    )
    data["schema"] = SCHEMA
    data["edits"] = edits
    path = sidecar_path(book_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def apply_composer_edits(book_dir: Path, *, log=print) -> dict[str, Any]:
    """Replay every saved Composer edit into book/book.md. Returns a report.

    Runs as the LAST compose step so the human's text sits on top of whatever the
    pipeline just regenerated. Chapters with no saved edit are untouched.
    """
    book_dir = Path(book_dir).resolve()
    book_md = book_dir / "book" / "book.md"
    data = load_edits(book_dir)
    edits = {e["chapter_key"]: e for e in data["edits"] if e.get("chapter_key")}
    report: dict[str, Any] = {
        "schema": "podcast.composer-edits-replay/v1",
        "applied": 0,
        "conflicts": 0,
        "orphaned": 0,
        "chapters": [],
    }
    if not edits or not book_md.exists():
        return report

    text = book_md.read_text(encoding="utf-8")
    parts = _HEADING_RE.split(text)
    out = [parts[0]]
    seen: set[str] = set()
    for i in range(1, len(parts), 2):
        head = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        key = anchor_key(head)
        edit = edits.get(key)
        if not edit:
            out.append(head + "\n\n" + body.strip() + "\n")
            continue
        seen.add(key)
        composed_fp = fingerprint(body)
        expected = edit.get("base_fingerprint") or ""
        # A conflict means the pipeline regenerated this chapter since the human
        # edited it. The edit still wins — it is their chapter — but they are told,
        # because the improvement they are now overwriting may be one they want.
        conflict = bool(expected) and expected != composed_fp
        record = {"chapter_key": key, "title": head.strip(), "conflict": conflict}
        if conflict:
            report["conflicts"] += 1
            record["composed_fingerprint"] = composed_fp
            record["edited_from_fingerprint"] = expected
            log(f"      composer-edits: {key!r} CONFLICT — pipeline regenerated this chapter since the edit")
        report["applied"] += 1
        report["chapters"].append(record)
        out.append(head + "\n\n" + str(edit.get("body_md", "")).strip() + "\n")

    orphaned = sorted(set(edits) - seen)
    if orphaned:
        report["orphaned"] = len(orphaned)
        report["orphaned_keys"] = orphaned
        # An orphan means the chapter the edit belonged to no longer exists under
        # that heading — a re-segmentation renamed or merged it. Never guessed at.
        log(f"      composer-edits: {len(orphaned)} orphaned edit(s), chapter heading gone: {', '.join(orphaned[:3])}")

    if report["applied"]:
        new_text = (out[0].rstrip() + "\n\n" + "\n".join(out[1:])).strip() + "\n"
        book_md.write_text(new_text, encoding="utf-8")
    (book_dir / "_system" / "composer-edits-replay.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    log(
        f"    composer-edits: {report['applied']} chapter(s) replayed"
        + (f", {report['conflicts']} conflict(s)" if report["conflicts"] else "")
        + (f", {report['orphaned']} orphaned" if report["orphaned"] else "")
    )
    return report
