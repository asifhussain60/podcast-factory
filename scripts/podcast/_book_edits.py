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

# The pipeline's own record of what it composed, per chapter, for the run that
# produced the book.md a human is currently looking at. The Composer reads a
# chapter's value out of this file and stores it as the edit's `base_fingerprint`;
# the next replay compares against the same file. Both sides therefore quote ONE
# number produced by ONE computation.
#
# They did not, until 2026-07-21. The Composer hashed the body it read out of the
# LIVE book.md — which by then carried the edition introduction and the
# comprehension bridges — while replay hashed the composed body three steps BEFORE
# the introduction is injected and five before bridges run. For any chapter
# carrying either, the two hashes could not match, so CONFLICT fired permanently
# and every one of the eight reported that day was noise. A conflict warning that
# is always on is worse than none: it teaches the reader to ignore it.
BASE_STAMP_NAME = "composer-base.json"
BASE_STAMP_SCHEMA = "podcast.composer-base/v1"

_HEADING_RE = re.compile(r"(?m)^(##\s+.+)$")

# Characters trimmed from both ends of a heading, spelled out because Python's
# `.strip()` and JavaScript's `.trim()` disagree: JS strips U+FEFF and Python does
# not; Python strips U+0085 and the C0 separators and JS does not. Mirror of the
# same class in plan-dashboard/scripts/lib/anchor-key.mjs.
_TRIM_RE = re.compile("^[\\s\u0085\u001c-\u001f\ufeff]+|[\\s\u0085\u001c-\u001f\ufeff]+$")


def anchor_key(heading: str) -> str:
    """Normalize a heading to a comparable key.

    Mirror of `anchorKey`, which as of 2026-07-20 has exactly ONE implementation on
    the JS side: `plan-dashboard/scripts/lib/anchor-key.mjs`. It previously had
    four byte-identical copies and this docstring named two of them, so "keep them
    in sync" was advice about a set nobody could enumerate. Change one, change the
    other, in the same commit — a divergence silently orphans every saved edit,
    because the replay simply finds no matching chapter.

    Both the digit class and the trim set are written out rather than relying on
    `\\d` and `.strip()`, because the two languages disagree about both:

      digits      Python's `\\d` is Unicode-aware, JavaScript's is ASCII-only, so
                  `## ١. Patience` keyed as `patience` here and `١. patience`
                  there. This is an Arabic-source project.
      whitespace  JS `.trim()` strips the BOM and Python `.strip()` does not;
                  Python strips U+0085 and the C0 separators and JS does not. A
                  leading BOM was the worst of them — it sits before the `##`, so
                  the heading strip did not match either and the key came out as
                  the entire raw heading.

    The trim runs FIRST for that reason, and again at the end. Pasted text is
    exactly where these characters arrive, and pasting into the Composer is the
    path that produces a heading here.
    """
    trimmed = _TRIM_RE.sub("", heading or "")
    without_markup = re.sub(r"<[^>]+>", "", trimmed)
    without_hashes = re.sub(r"^#{1,6}\s+", "", without_markup)
    without_number = re.sub(r"^[0-9٠-٩۰-۹]+\.\s*", "", without_hashes)
    return _TRIM_RE.sub("", without_number).lower()


def fingerprint(text: str) -> str:
    """Stable hash of a chapter body, whitespace-normalized.

    NO LONGER A MIRROR PAIR, deliberately. `composer-edits.ts` used to carry a
    `fingerprintBody` twin, and keeping two hash implementations agreeing across
    two languages was a standing hazard — the BOM alone counts as whitespace to
    JavaScript's `\\s` and not to Python's `str.split()`, and pasted text is exactly
    where a BOM arrives. The TS side now quotes the stamp this function writes
    (`_system/composer-base.json`) instead of computing its own number, so there is
    one implementation and nothing to keep in sync.

    The BOM strip stays because this side still meets pasted text on replay.
    """
    cleaned = (text or "").replace("﻿", "")
    return hashlib.sha256(" ".join(cleaned.split()).encode("utf-8")).hexdigest()[:16]


def sidecar_path(book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / SIDECAR_NAME


class SidecarUnreadable(RuntimeError):
    """The sidecar exists but could not be parsed.

    Raised only on the WRITE path. A reader may fall back to "no edits" and lose
    nothing; a writer that does the same overwrites the file with its own single
    entry and destroys every edit the author ever made.
    """


def load_edits(book_dir: Path, *, strict: bool = False) -> dict[str, Any]:
    """Read the sidecar. ``strict`` refuses to interpret a broken file as empty."""
    path = sidecar_path(book_dir)
    if not path.exists():
        return {"schema": SCHEMA, "edits": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        if strict:
            raise SidecarUnreadable(f"{path} is not readable JSON: {e}") from e
        return {"schema": SCHEMA, "edits": []}
    if not isinstance(data, dict) or not isinstance(data.get("edits"), list):
        if strict:
            raise SidecarUnreadable(f"{path} does not hold a v1 edits list")
        return {"schema": SCHEMA, "edits": []}
    return data


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Write via temp file + rename, so a crash cannot leave a half-written file.

    This matters more here than anywhere else in the pipeline: a truncated sidecar
    is exactly the input that used to make the next save discard every prior edit,
    and a non-atomic write is what manufactures one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def record_edit(
    book_dir: Path,
    *,
    chapter_key: str,
    body_md: str,
    base_fingerprint: str = "",
    saved_at: str = "",
) -> Path:
    """Persist one Composer chapter edit. Last write per chapter wins.

    Raises ``SidecarUnreadable`` rather than starting a fresh file when the
    existing sidecar cannot be parsed — see that exception's docstring.
    """
    book_dir = Path(book_dir)
    data = load_edits(book_dir, strict=True)
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
    _write_json_atomic(path, data)
    return path


def edited_chapter_keys(book_dir: Path) -> set[str]:
    """Anchor keys of every chapter the human has authored through the Composer.

    The Composer is the singular path for PDF-bound chapter changes, so a chapter
    in this set is the AUTHOR'S chapter and the pipeline has no business
    regenerating it. Callers use this to skip the model entirely — see
    ``compose_book_v2``.
    """
    return {str(e.get("chapter_key")) for e in load_edits(book_dir)["edits"] if e.get("chapter_key")}


def edited_body(book_dir: Path, chapter_key: str) -> str | None:
    """The human's saved body for one chapter, or None. Empty bodies are None.

    An empty body is treated as absent for the same reason replay refuses to apply
    one: it would wipe the chapter, and the ship gate counts headings rather than
    prose, so nothing downstream would notice.
    """
    for e in load_edits(book_dir)["edits"]:
        if e.get("chapter_key") == chapter_key:
            body = str(e.get("body_md") or "").strip()
            return body or None
    return None


def base_stamp_path(book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / BASE_STAMP_NAME


def load_base_stamp(book_dir: Path) -> dict[str, str]:
    """Per-chapter composed fingerprints from the last compose. Never raises."""
    path = base_stamp_path(book_dir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        chapters = data.get("chapters")
        return {str(k): str(v) for k, v in chapters.items()} if isinstance(chapters, dict) else {}
    except Exception:
        return {}


def base_fingerprint_for(book_dir: Path, chapter_key: str) -> str:
    """What the Composer records as an edit's ``base_fingerprint``."""
    return load_base_stamp(book_dir).get(chapter_key, "")


def apply_composer_edits(book_dir: Path, *, log=print, force: bool = False) -> dict[str, Any]:
    """Replay every saved Composer edit into book/book.md. Returns a report.

    Runs as the LAST of the text-mutating compose steps so the human's text sits on
    top of whatever the pipeline just regenerated. Chapters with no saved edit are
    untouched.

    Also stamps ``_system/composer-base.json`` — the per-chapter fingerprints the
    Composer will quote back as ``base_fingerprint`` on its next save. That happens
    on EVERY run, edits or not, because a chapter with no edit today is exactly the
    one a human may edit tomorrow.

    ``force`` mirrors the compose flag: without it an edited chapter was never
    regenerated, so its stamp is carried forward unchanged and a conflict is
    impossible by construction. With it the pipeline really did re-compose over the
    author's chapter, and the freshly composed fingerprint is stamped — which is
    what makes the resulting conflict a true statement.
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
    if not book_md.exists():
        return report

    text = book_md.read_text(encoding="utf-8")
    prev_stamp = load_base_stamp(book_dir)
    stamp: dict[str, str] = {}
    parts = _HEADING_RE.split(text)
    out = [parts[0]]
    seen: set[str] = set()
    for i in range(1, len(parts), 2):
        head = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        key = anchor_key(head)
        edit = edits.get(key)
        composed_fp = fingerprint(body)
        if not edit:
            stamp[key] = composed_fp
            out.append(head + "\n\n" + body.strip() + "\n")
            continue
        seen.add(key)
        expected = str(edit.get("base_fingerprint") or "")
        if force:
            # The pipeline was told to re-compose over the author. `body` here is
            # genuinely fresh prose, so its fingerprint is the honest new base.
            current = composed_fp
        else:
            # The chapter was NOT regenerated: `body` is the author's own text,
            # already substituted upstream, so fingerprinting it would compare the
            # edit against itself and report a conflict on every compose.
            current = prev_stamp.get(key, composed_fp)
        stamp[key] = current
        # A conflict means the pipeline regenerated this chapter since the human
        # edited it. The edit still wins — it is their chapter — but they are told,
        # because the improvement they are now overwriting may be one they want.
        #
        # Only compared when a previous stamp EXISTS. Without one, `expected` came
        # from somewhere else — an edit saved before the stamp did, carrying a
        # number the retired TS hash produced — and comparing across two
        # computations is what made this signal meaningless in the first place. An
        # unknown is reported as no conflict, and the honest current value is
        # stamped rather than the legacy one, so the NEXT compose can tell.
        conflict = bool(expected) and key in prev_stamp and expected != current
        record = {"chapter_key": key, "title": head.strip(), "conflict": conflict}
        if conflict:
            report["conflicts"] += 1
            record["composed_fingerprint"] = current
            record["edited_from_fingerprint"] = expected
            log(f"      composer-edits: {key!r} CONFLICT — pipeline regenerated this chapter since the edit")
        edited = str(edit.get("body_md", "")).strip()

        # An EMPTY body would wipe the chapter and keep wiping it on every later
        # compose, and the ship gate would not notice: `gate_b1_book_md_complete`
        # counts `## ` headings, not prose, so a gutted chapter passes B1 and B2.
        # A human deleting a whole chapter through the Composer is not a thing we
        # accept silently.
        if not edited:
            record["skipped"] = "empty edit body — refusing to wipe the chapter"
            report.setdefault("skipped", 0)
            report["skipped"] += 1
            log(f"      composer-edits: {key!r} SKIPPED — empty body would wipe the chapter")
            out.append(head + "\n\n" + body.strip() + "\n")
            report["chapters"].append(record)
            continue

        # No normalisation here, deliberately. This function used to fold
        # transliteration and spelling itself, because it ran AFTER those passes
        # and a Composer-authored chapter would otherwise keep British spellings
        # and scholarly apostrophes. It could not fold in the inline Arabic that
        # way — that pass had already run — so the author's chapters silently lost
        # their script. The replay now runs BEFORE all of them (compose step
        # 5a-replay), so every deterministic pass sees the author's text as part of
        # the book, which is the only version of this that is actually complete.
        report["applied"] += 1
        report["chapters"].append(record)
        out.append(head + "\n\n" + edited + "\n")

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

    # Stamped unconditionally: a chapter nobody has edited is precisely the one
    # somebody may edit next, and the Composer needs a number to quote for it.
    _write_json_atomic(base_stamp_path(book_dir), {"schema": BASE_STAMP_SCHEMA, "chapters": stamp})
    if not edits:
        return report

    _write_json_atomic(book_dir / "_system" / "composer-edits-replay.json", report)
    log(
        f"    composer-edits: {report['applied']} chapter(s) replayed"
        + (f", {report['conflicts']} conflict(s)" if report["conflicts"] else "")
        + (f", {report['orphaned']} orphaned" if report["orphaned"] else "")
    )
    return report
