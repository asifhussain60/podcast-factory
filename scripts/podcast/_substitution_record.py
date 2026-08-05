"""The durable record that makes Arabic substitution reversible.

`_book_substitution` swaps a romanized term for its Arabic script, and that swap
cannot invert itself: `_normalize_annotations` undoes an ANNOTATION by reading the
romanization still standing beside the bracket, and substitution deletes exactly
that anchor. Afterwards nothing on the page distinguishes script the pass wrote
from script the SOURCE printed. A pass that cannot invert itself can only ever
ADD — reclassify a term to `familiar` and its English could never come back.

So the pre-substitution body of every chapter is stored here, in
`_system/book-substitutions.json`, the way the Book Composer stores `body_md`.
This module owns that file and the three operations that keep it honest:

    RESTORE      trusted only while the page still fingerprints as the pass's own
                 output; anything else means a human or a later step has been
                 through, and their words outrank the fold.
    TAKE BACK    when a wholesale restore is impossible, `revert_ineligible`
                 still returns the English of terms the gate no longer allows,
                 leaving every later step's work in place.
    RE-STAMP     `restamp_from_final_book` writes the fingerprint from the
                 FINISHED page as the last thing the apparatus does.

That last one is not bookkeeping. The fingerprint used to be stamped where the
substitution happens, with four page-altering steps still to come — American
spelling, the comprehension bridges, the honorific convention, the paragraph
mirror — so it named a chapter that never reached disk. Every later compose read
a mismatch, refused to restore, and dropped the record: `before_md` deleted, and
with it the only copy of the English anywhere.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from _book_edits import anchor_key, fingerprint
from _book_inline_arabic import _SKIP_LINE

RECORD_NAME = "book-substitutions.json"
SCHEMA = "book.substitutions/v1"

_HEADING_RE = re.compile(r"(?m)^(##\s+.+)$")


def record_path(book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / RECORD_NAME


def load_record(book_dir: Path) -> dict[str, Any]:
    path = record_path(book_dir)
    if not path.exists():
        return {"schema": SCHEMA, "chapters": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - an unreadable sidecar is not a broken book
        return {"schema": SCHEMA, "chapters": []}
    if not isinstance(data, dict) or not isinstance(data.get("chapters"), list):
        return {"schema": SCHEMA, "chapters": []}
    return data


def _save_record(book_dir: Path, chapters: list[dict[str, Any]]) -> None:
    path = record_path(book_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps({"schema": SCHEMA, "chapters": chapters}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def _chapters(book_md: str) -> list[tuple[str, str]]:
    """[(heading, body)] for every ``## `` section, in document order."""
    parts = _HEADING_RE.split(book_md)
    return [(parts[i], parts[i + 1] if i + 1 < len(parts) else "") for i in range(1, len(parts), 2)]


def _english_form(before_md: str, phonetic: str) -> tuple[str, int] | None:
    """How the pre-substitution text wrote this term, and how many times.

    Emphasised form preferred, because that is what the articulation pass writes
    and losing the italics would change the page in a second, unrelated way.
    """
    for pattern in (
        rf"(?<![\w*_-])\*{re.escape(phonetic)}\*(?![\w'’-])",
        rf"(?<![\w*_-]){re.escape(phonetic)}(?![\w'’-])",
    ):
        found = re.findall(pattern, before_md, flags=re.IGNORECASE)
        if found:
            return found[0], len(found)
    return None


def _bare_script_spans(body: str, script: str) -> list[tuple[int, int, int]]:
    """(line index, start, end) for script standing in prose, not in a bracket.

    A bracket means the ANNOTATION overlay put it there — `*marifah* (مَعْرِفَة)`
    — and that apparatus is not this pass's to undo.
    """
    spans: list[tuple[int, int, int]] = []
    for i, line in enumerate(body.splitlines(keepends=True)):
        if _SKIP_LINE.search(line):
            continue
        for m in re.finditer(re.escape(script), line):
            head = line[: m.start()]
            if head.count("(") > head.count(")"):
                continue
            spans.append((i, m.start(), m.end()))
    return spans


def revert_ineligible(
    body: str, before_md: str, allowed: list[dict[str, str]], candidates: list[dict[str, str]]
) -> tuple[str, int]:
    """Give the English back for any term the gate no longer allows.

    WHY THIS IS PART OF THE PASS AND NOT A ONE-OFF REPAIR. A gate that gets
    stricter — a term reclassified, a rule tightened, a glossary row corrected —
    leaves script on a page that today's rules would never have put there. The
    wholesale restore above handles that only when the fingerprint still matches,
    which it does not once a later apparatus step has been through. This is the
    narrow move that always works: take back exactly the terms that are no longer
    eligible, and touch nothing else.

    It is what brought 74 substitutions back off four live editions on
    2026-08-03, among them `adam` set as `آدَم` — *Adam the prophet* — in a
    passage that means `عَدَم`, non-existence: "pulling them out of an آدَم, a
    nothingness". No structural check can catch a word that is spelled right and
    means something else; only a reviewer can, which is why an unclassified term
    is not substitutable at all now.

    Conservative twice over. A term is reverted only where the pre-substitution
    text actually held its romanization, and never when the page carries MORE of
    that script than the text held — that surplus came from somewhere else (a
    quotation, the source's own Arabic) and guessing at it would corrupt prose to
    tidy it.
    """
    allowed_scripts = {t["script"].strip() for t in allowed}
    lines = body.splitlines(keepends=True)
    reverted = 0
    for term in candidates:
        script = term["script"].strip()
        if not script or script in allowed_scripts:
            continue
        found = _english_form(before_md, term["phonetic"])
        if not found:
            continue
        english, available = found
        spans = _bare_script_spans("".join(lines), script)
        if not spans or len(spans) > available:
            continue
        for i, start, end in reversed(spans):
            lines[i] = lines[i][:start] + english + lines[i][end:]
            reverted += 1
    return "".join(lines), reverted


def restamp_from_final_book(book_dir: Path, log=lambda _m: None) -> int:
    """Re-stamp every record's ``after_fingerprint`` from the FINISHED book.md.

    The same pattern, and for the same reason, as `_book_edits`' stamp of
    `composer-base.json`: a fingerprint is only useful if it names the text the
    NEXT run will actually find, and this pass runs at 5a-substitute with four
    page-altering steps still to come — American spelling, the comprehension
    bridges, the honorific convention and the paragraph mirror. Stamped there,
    the number described a version of the chapter that never reached disk, so
    every subsequent compose read a mismatch, refused to restore, and (before the
    guard above) discarded the record.

    Called once at the end of `apply_book_apparatus`. Writes only when something
    moved, so a re-render of an unchanged book leaves the sidecar byte-identical.
    """
    book_dir = Path(book_dir)
    book_md = book_dir / "book" / "book.md"
    rows = load_record(book_dir)["chapters"]
    if not rows or not book_md.exists():
        return 0
    bodies = {anchor_key(head): body for head, body in _chapters(book_md.read_text(encoding="utf-8"))}
    changed = 0
    for row in rows:
        body = bodies.get(str(row.get("chapter_key") or ""))
        if body is None:
            continue  # the chapter was renamed or dropped; the record is orphaned, not wrong
        current = fingerprint(body.strip())
        if current != str(row.get("after_fingerprint") or ""):
            row["after_fingerprint"] = current
            changed += 1
    if changed:
        _save_record(book_dir, rows)
        log(f"arabic-substitution: re-stamped {changed} chapter fingerprint(s) from the final book")
    return changed
