"""_vowelled_source.py — where a vowelled copy of an Arabic source stream lives.

WHY A SIBLING RATHER THAN THE FILE ITSELF. `_system/source/ocr/raw-extract.md` is
the record of what Azure OCR actually read off the page, and it is what
`arabic_span_is_grounded` consults to decide whether a verse in the finished book
was COPIED from the source or supplied from a model's memory. Marking it up in
place would destroy that record to gain nothing the sibling does not give, and it
would make the change irreversible; deleting one file undoes this one.

WHY A FINGERPRINT. A sibling is only the vowelling OF a particular OCR. Re-running
Phase 0a rewrites the raw extract, and a sibling left over from the previous
extract would then be preferred silently — the marked text of a document that no
longer exists. Every sibling is therefore recorded against the sha256 of the
source it was made from, and `resolve_arabic_source` hands back the raw file
whenever the two disagree. Stale means ignored, never guessed.

The report also carries the refusal list, so a passage the model could not vowel
is visible in the same place the stats are.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SIBLING_SUFFIX = ".vowelled.md"
REPORT_NAME = "source-vowelling.json"
SCHEMA = "podcast.source-vowelling/v1"


def sibling_for(source: Path) -> Path:
    """The vowelled twin of an Arabic source stream, beside it.

    Idempotent: handed a sibling it returns that same sibling, so a caller that
    resolves before asking cannot produce `raw-extract.vowelled.vowelled.md`.
    """
    source = Path(source)
    if source.name.endswith(SIBLING_SUFFIX):
        return source
    return source.parent / (source.stem + SIBLING_SUFFIX)


def book_dir_for(path: Path) -> Path | None:
    """The book directory a `_system/...` path belongs to, at any nesting depth.

    Walks up to the `_system` directory rather than counting `.parents[N]`, which
    would need a different N for `source/ocr/` than for `source/multi/ocr/`.
    """
    for parent in path.parents:
        if parent.name == "_system":
            return parent.parent
    return None


def fingerprint(path: Path) -> str:
    """sha256 of a source file, or "" when it is not there."""
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report_path(book_dir: Path) -> Path:
    return book_dir / "_system" / REPORT_NAME


def load_report(book_dir: Path) -> dict:
    p = report_path(book_dir)
    if not p.exists():
        return {"schema": SCHEMA, "streams": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # An unreadable report means "nothing is known to be current", which makes
        # every resolve fall back to the raw source. Fail closed, never guess.
        return {"schema": SCHEMA, "streams": {}}
    data.setdefault("streams", {})
    return data


def _rel(book_dir: Path, path: Path) -> str:
    try:
        return path.relative_to(book_dir).as_posix()
    except ValueError:  # pragma: no cover - defensive
        return path.name


def write_atomic(path: Path, text: str) -> None:
    """Write via a temp file in the same directory, then rename.

    A vowelling pass makes hundreds of metered calls; an interrupt part-way
    through the write would otherwise leave a truncated sibling that the resolver,
    seeing a matching fingerprint, would happily prefer.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def record_stream(book_dir: Path, *, source: Path, sibling: Path, stats: dict) -> Path:
    """Record that `sibling` is the vowelling of `source` as it stands right now."""
    report = load_report(book_dir)
    report["schema"] = SCHEMA
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["streams"][_rel(book_dir, source)] = {
        "source_sha256": fingerprint(source),
        "sibling": _rel(book_dir, sibling),
        "stats": stats,
    }
    out = report_path(book_dir)
    write_atomic(out, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return out


def is_current(source: Path) -> bool:
    """True when a vowelled sibling exists AND was made from this exact source."""
    sibling = sibling_for(source)
    if not sibling.exists():
        return False
    book_dir = book_dir_for(source)
    if book_dir is None:
        return False
    entry = load_report(book_dir)["streams"].get(_rel(book_dir, source))
    if not entry:
        return False
    return bool(entry.get("source_sha256")) and entry["source_sha256"] == fingerprint(source)


def resolve_arabic_source(source: Path) -> Path:
    """The vowelled sibling when it is current, otherwise the raw source itself.

    Every reader of an Arabic source stream goes through here, so "is there a
    vowelled copy, and is it still the vowelling of THIS text" is answered in one
    place rather than by four call sites each doing their own suffix swap.
    """
    source = Path(source)
    return sibling_for(source) if is_current(source) else source
