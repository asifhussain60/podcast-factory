#!/usr/bin/env python3
"""compose_articulate.py — install a hand-off articulated chapter through the
Book Composer's own save path. Engine behind the pf-compose-articulator skill.

SESSIONS-LANE ONLY, by design (Asif, 2026-08-12): a translation-edition book
has a real Arabic SOURCE to stay faithful to, and this tool proves nothing
about that — it only checks that a hand-off rewrite is faithful to the
ENGLISH text already in book.md. That is exactly the Sessions lane's own
question (a lecture transcript being polished into better English, no
foreign-language source in play) and a different, easier one than a
translation edition's. Refuses outright on any book without
`_system/sessions-articulation.json` — the file that only exists for a
Sessions-lane book (written by `sessions/ingest.py`).

WHY THIS EXISTS: the automated `sessions/articulate.py` pass kept timing out
and reverting on Surah Al-Fateha's denser chapters (a runaway response, then
two separate 15-minute-timeout-then-retry cycles on one chapter alone).
Asif tested a GPT-articulated version of that same chapter against this
pipeline's own fidelity gates and it passed clean; he chose to hand-author
the remaining chapters himself and needed a way to get each one into the
book correctly rather than pasting it in by hand.

WHAT "correctly" MEANS, precisely, because it is easy to get almost right:

  1. The chapter is addressed by its EXISTING heading in book.md, never by a
     number and never by the hand-off file's own heading — a hand-off file's
     heading can drift in casing or punctuation from the book's own (this
     tool's first real run found exactly that: "Stages of Love" vs the
     book's own "Stages Of Love"), and installing under the wrong casing
     would fail the pipeline's own heading-survival gate on sight.
  1b. Every inline image the chapter already has (`![](images/<sid>/<file>)`
     — the lecture-slide screenshots `sessions/convert.py` embeds at the
     exact point in the transcript they illustrate) is carried forward, even
     though the hand-off text never saw them and cannot mention them. A
     dropped image whose caption line survives in the rewrite (even
     paraphrased) is reinserted right after it; one whose caption did not
     survive is placed at the same proportional position through the
     chapter. Never silently dropped, never guessed into the middle of an
     unrelated sentence — see `_restore_images`.
  2. The rewrite is checked against `revoice_gates` — the SAME deterministic
     checks `_book_voice.py` runs on every automated window: abridgement,
     runaway length, teaching loss, narrative-opening, Arabic-run count,
     doctrinal P0s, narrative-frame guards (grammatical person, speech-tag
     integrity, enumeration survival), leaked markers. A finding refuses the
     install by default; `--force` overrides it, because a human reviewer
     may know a finding is a false positive (a heading-case mismatch is not
     a content defect) in a way the gate cannot.
  3. Installed exactly like a human Composer save, through the ONE shared
     `_book_edits.write_chapter_body`: one-time `book.md.bak`, the chapter's
     body spliced between its heading and the next `## ` heading (or EOF),
     and the edit recorded quoting `base_fingerprint_for` rather than hashing
     it here — the same fingerprint-source discipline every other writer in
     this pipeline follows, so a later compose can tell truthfully whether
     the book moved underneath this edit.
  1c. Before any of the above is checked, the body is run through
     `_sessions_prose_format.normalize_sessions_prose` — a bare `81:22`
     citation note and a `### Title Arabic` heading followed by its own
     redundant `WALEEJA`-style transliteration are this book's OWN legacy
     transcript conventions, predating the site's quotation-card and house
     citation forms, and `sessions/articulate.py` carries them straight
     through by design (REQ-BA forbids restructuring). Normalized here too,
     so a hand-off chapter matches every other chapter's markup.
  4. The Sessions lane's own articulation ledger
     (`_system/sessions-articulation.json`) is updated to `adapted`, through
     `sessions.articulate._record` — the SAME function the automated pass
     uses — so the status card and any future `articulate.py --resume` see
     this chapter as done rather than re-attempting it.
  5. Refuses while the Astro dev server is up, unless `--allow-composer-open`
     — reusing `compose_fix.composer_is_open`, not a second copy of the
     check. A live Composer autosaves the same file this writes.

Usage:
    python3 scripts/podcast/compose_articulate.py <slug> --list
    python3 scripts/podcast/compose_articulate.py <slug> <chapter> <md-file>              # check only
    python3 scripts/podcast/compose_articulate.py <slug> <chapter> <md-file> --install
    python3 scripts/podcast/compose_articulate.py <slug> <chapter> <md-file> --install --force
    python3 scripts/podcast/compose_articulate.py <slug> <chapter> <md-file> --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _book_arabic_audit import run_arabic_audit  # noqa: E402
from _book_defects import chapters as split_chapters  # noqa: E402
from _book_edits import anchor_key, write_chapter_body  # noqa: E402
from _book_voice_gates import revoice_gates  # noqa: E402
from _paths import find_content  # noqa: E402
from _pipeline_flags import narrative_frame, narrator_subject  # noqa: E402
from _sessions_prose_format import normalize_sessions_prose  # noqa: E402
from compose_fix import composer_is_open  # noqa: E402

_HEADING_RE = re.compile(r"(?m)^(##\s+.+)$")
_IMG_MD_RE = re.compile(r"(?m)^(!\[[^\]]*\]\(([^)]+)\))\s*$")


def _resolve_book_dir(slug: str) -> Path:
    found = find_content(slug)
    if not found:
        raise FileNotFoundError(f"book not found: {slug!r}")
    return found[2]


def _sessions_ledger_path(book_dir: Path) -> Path:
    return book_dir / "_system" / "sessions-articulation.json"


def _require_sessions_lane(book_dir: Path, slug: str) -> None:
    if not _sessions_ledger_path(book_dir).exists():
        raise PermissionError(
            f"{slug!r} has no _system/sessions-articulation.json — this tool is "
            "Sessions-lane only. A translation-edition book has a real Arabic source "
            "to stay faithful to, which a hand-off English rewrite is never checked "
            "against here; use the book-articulation skill's rearticulate_chapter.py "
            "for those instead."
        )


def chapter_headings(book_md: Path) -> list[str]:
    """Every `## ` heading in book.md, in document order."""
    text = book_md.read_text(encoding="utf-8")
    return [m.group(1)[3:].strip() for m in _HEADING_RE.finditer(text)]


def resolve_chapter(book_md: Path, chapter: str) -> str:
    """The book's OWN heading text for `chapter` — never the hand-off file's.

    Matches by exact anchor_key first, then by case-insensitive substring.
    Raises with the candidate list on zero or multiple matches, rather than
    guessing — the same discipline `pf-compose-fix` uses for chapter numbers.
    """
    headings = chapter_headings(book_md)
    key = anchor_key(chapter)
    exact = [h for h in headings if anchor_key(h) == key]
    if len(exact) == 1:
        return exact[0]
    needle = chapter.strip().lower()
    loose = [h for h in headings if needle in h.lower()]
    if len(loose) == 1:
        return loose[0]
    candidates = "\n".join(f"  - {h!r}" for h in headings)
    if not loose and not exact:
        raise ValueError(f"no chapter matches {chapter!r}. Chapters in this book:\n{candidates}")
    raise ValueError(f"{chapter!r} matches more than one chapter:\n{candidates}")


def _chapter_body(book_md: Path, heading: str) -> tuple[str, int, int]:
    """(body, start_line, end_line) — end_line is the next heading's line, or EOF."""
    lines = book_md.read_text(encoding="utf-8").split("\n")
    start = -1
    end = len(lines)
    for i, line in enumerate(lines):
        if line.startswith("## "):
            if start == -1 and line[3:].strip() == heading:
                start = i
            elif start != -1:
                end = i
                break
    if start == -1:
        raise ValueError(f"heading not found in book.md: {heading!r}")
    return "\n".join(lines[start + 1 : end]).strip(), start, end


def _extract_handoff_body(md_path: Path) -> str:
    """The hand-off file's body, with its OWN heading line stripped if present.

    The heading is never trusted — casing/punctuation drift there is exactly
    what cost the first real run a failed gate. Only the book's own heading,
    resolved separately, is ever written.
    """
    lines = md_path.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].startswith("## "):
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(lines).strip()


def _extract_images(body: str) -> list[dict]:
    """Every `![](path)` reference in `body`, in document order, paired with
    the short line immediately above it (its caption, in this book's own
    convention — see `sessions/convert.py`) so a dropped image can be
    re-anchored later even after the surrounding prose is rewritten."""
    lines = body.split("\n")
    images = []
    for i, line in enumerate(lines):
        m = _IMG_MD_RE.match(line.strip())
        if not m:
            continue
        j = i - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        images.append({"markdown": m.group(1), "path": m.group(2), "anchor": lines[j].strip() if j >= 0 else ""})
    return images


def _restore_images(base_body: str, new_body: str) -> tuple[str, list[dict]]:
    """Put back any image `new_body` dropped that `base_body` had.

    A hand-off rewrite is plain text with no way to carry an embedded image
    reference forward — every one of them would silently vanish on install
    without this. Placement: if the image's caption line (or a close
    paraphrase of it) survives anywhere in the rewrite, the image goes right
    after it; otherwise it lands at the same proportional position through
    the chapter, by cumulative word count. Either way it is placed, never
    dropped — this only ever adds lines, so a caller diffing before/after
    sees exactly what moved.
    """
    images = _extract_images(base_body)
    if not images:
        return new_body, []

    present_paths = {m.group(2) for m in _IMG_MD_RE.finditer(new_body)}
    missing = [img for img in images if img["path"] not in present_paths]
    if not missing:
        return new_body, []

    new_lines = new_body.split("\n")
    total_new_words = max(len(new_body.split()), 1)
    total_base_words = max(len(base_body.split()), 1)

    placements = []
    for img in missing:
        target_idx = None
        how = "proportional"
        anchor = img["anchor"].lower()
        if anchor:
            for idx, line in enumerate(new_lines):
                if line.strip().lower() == anchor:
                    target_idx, how = idx, "anchored"
                    break
            if target_idx is None:
                for idx, line in enumerate(new_lines):
                    if anchor in line.lower():
                        target_idx, how = idx, "anchored (partial)"
                        break
        if target_idx is None:
            offset = base_body.find(img["markdown"])
            frac = (len(base_body[:offset].split()) / total_base_words) if offset >= 0 else 1.0
            cum = 0
            for idx, line in enumerate(new_lines):
                cum += len(line.split())
                if cum / total_new_words >= frac:
                    target_idx = idx
                    break
            target_idx = target_idx if target_idx is not None else len(new_lines) - 1
        placements.append((target_idx, img, how))

    for target_idx, img, _how in sorted(placements, key=lambda t: t[0], reverse=True):
        new_lines[target_idx + 1 : target_idx + 1] = ["", img["markdown"], ""]

    restored = [
        {"path": img["path"], "anchor": img["anchor"], "placement": how}
        for _, img, how in sorted(placements, key=lambda t: t[0])
    ]
    return "\n".join(new_lines), restored


def check(book_dir: Path, chapter: str, md_path: Path, *, log=print) -> dict:
    """Run the fidelity gates. Never writes anything."""
    book_md = book_dir / "book" / "book.md"
    heading = resolve_chapter(book_md, chapter)
    base_body, _, _ = _chapter_body(book_md, heading)
    handoff_body = _extract_handoff_body(md_path)
    new_body, images_restored = _restore_images(base_body, handoff_body)
    new_body, format_changes = normalize_sessions_prose(new_body)

    frame = narrative_frame(book_dir)
    subject = narrator_subject(book_dir)
    findings = revoice_gates(base_body, new_body, check_opening=True, frame=frame, narrator_subject=subject)

    base_words, new_words = len(base_body.split()), len(new_body.split())
    result = {
        "heading": heading,
        "base_words": base_words,
        "new_words": new_words,
        "ratio": round(new_words / base_words, 3) if base_words else 0.0,
        "findings": findings,
        "images_restored": images_restored,
        "format_changes": format_changes,
        "body": new_body,
        "clean": not findings,
    }
    log(f"  {heading!r}: {base_words} -> {new_words} words ({result['ratio']}x)")
    if images_restored:
        anchored = sum(1 for r in images_restored if r["placement"].startswith("anchored"))
        log(f"    restored {len(images_restored)} image(s) the hand-off dropped ({anchored} anchored by caption)")
    if format_changes:
        headings = sum(1 for c in format_changes if c["kind"] == "heading-parenthesized")
        cites = sum(1 for c in format_changes if c["kind"].startswith("citation"))
        log(f"    normalized {headings} heading(s) and {cites} bare Qur'an citation(s) to house style")
    if findings:
        for f in findings:
            log(f"    finding: {f}")
    else:
        log("    clean — every deterministic gate passed")
    return result


def install(book_dir: Path, chapter: str, md_path: Path, *, force: bool = False, log=print) -> dict:
    """Check, then write — through the same path a human Composer save uses.

    Refuses on any gate finding unless `force`. Refuses if the Astro dev
    server is up unless the caller already checked `--allow-composer-open`
    (that check lives in `main`, not here, so a library caller decides).
    """
    result = check(book_dir, chapter, md_path, log=log)
    if result["findings"] and not force:
        result["installed"] = False
        result["reason"] = "gate finding(s) present — pass force=True to override"
        return result

    heading = result["heading"]
    new_body = result["body"]  # already has any dropped images restored + prose normalized, by check()
    write_chapter_body(book_dir, heading, new_body)

    key = anchor_key(heading)
    from sessions.articulate import _record as _sessions_record

    _sessions_record(book_dir, key, heading, "adapted")
    run_arabic_audit(book_dir, log=log)

    result["installed"] = True
    log("  installed — book.md updated, Composer edit recorded, ledger marked adapted")
    return result


def retrofit_book(book_dir: Path, *, log=print) -> dict:
    """Apply `normalize_sessions_prose` to EVERY chapter already on disk.

    For a book articulated before this normalizer existed — the citation and
    heading defects were never specific to a hand-off chapter, they came
    straight out of the lecture transcript itself and rode along through
    `sessions/articulate.py` just as faithfully. Only chapters that actually
    change get a Composer edit recorded; nothing else in the book moves.
    """
    book_md = book_dir / "book" / "book.md"
    text = book_md.read_text(encoding="utf-8")
    changed: list[dict] = []
    for heading, body in split_chapters(text):
        new_body, changes = normalize_sessions_prose(body.strip())
        if not changes:
            continue
        write_chapter_body(book_dir, heading, new_body)
        text = book_md.read_text(encoding="utf-8")  # re-read: line offsets shift after every write
        changed.append({"heading": heading, "changes": changes})
        log(f"  {heading!r}: {len(changes)} formatting change(s)")
    if changed:
        run_arabic_audit(book_dir, log=log)
    else:
        log("  nothing to retrofit — every chapter already matches house style")
    return {"chapters_changed": len(changed), "detail": changed}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("chapter", nargs="?", help="a heading or a distinguishing fragment of one")
    ap.add_argument("md_file", nargs="?", type=Path, help="path to the hand-off markdown")
    ap.add_argument("--list", action="store_true", help="print this book's chapter headings and exit")
    ap.add_argument(
        "--retrofit",
        action="store_true",
        help="apply heading/citation house-style normalization to every chapter already on disk, and exit",
    )
    ap.add_argument("--install", action="store_true", help="write, if the gates pass (or --force)")
    ap.add_argument("--force", action="store_true", help="install despite a gate finding")
    ap.add_argument("--allow-composer-open", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        book_dir = _resolve_book_dir(args.slug)
        _require_sessions_lane(book_dir, args.slug)
    except (FileNotFoundError, PermissionError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2

    if args.list:
        for h in chapter_headings(book_dir / "book" / "book.md"):
            print(h)
        return 0

    if args.retrofit:
        pid = composer_is_open()
        if pid and not args.allow_composer_open:
            print(
                f"REFUSED: the Book Composer is running (pid {pid}) and autosaves book.md.\n"
                "Close the tab, or pass --allow-composer-open if you know it is not on this book.",
                file=sys.stderr,
            )
            return 2
        result = retrofit_book(book_dir, log=print)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if not args.chapter or not args.md_file:
        ap.error("chapter and md_file are required unless --list is given")

    if not args.md_file.exists():
        print(f"REFUSED: no such file: {args.md_file}", file=sys.stderr)
        return 2

    log = (lambda *_a, **_k: None) if args.json else print

    try:
        if args.install:
            pid = composer_is_open()
            if pid and not args.allow_composer_open:
                print(
                    f"REFUSED: the Book Composer is running (pid {pid}) and autosaves book.md.\n"
                    "Close the tab, or pass --allow-composer-open if you know it is not on this book.",
                    file=sys.stderr,
                )
                return 2
            result = install(book_dir, args.chapter, args.md_file, force=args.force, log=log)
        else:
            result = check(book_dir, args.chapter, args.md_file, log=log)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("clean", True) and not result.get("installed", False) and not args.install:
        return 1
    return 0 if result.get("clean") or result.get("installed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
