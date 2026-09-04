"""_production_publish.py — the two things a book needs that publishing will not do.

`publish_to_listener.py` writes a book's text, recordings and Companion cards to
the Podcast Factory Library, and it is FORBIDDEN from touching the two columns
that decide whether anyone can see it (`content_unit.status`, `open_to_all`) — a
test greps it for exactly that. The reason is sound: a pipeline step that can
make a book visible can make a half-finished book visible by accident.

The consequence, unnoticed until 2026-08-06, is that visibility had no writer AT
ALL. `status` is set once, by the seed migration, for the books that existed the
day the database was created; two of the twenty-one are 'published' and nothing
in this repo — no script, no flag, no admin screen — can change that for the
other nineteen or for any book added later.

So this module supplies the missing writer, under the rule that makes the
original prohibition still true: it is reached ONLY from
`publish_to_production.py`, which is reached only because Asif pressed the button
on the Book Composer. The flip is a HUMAN act with a machine behind it, not a
pipeline step. `open_to_all` is deliberately NOT written here (Asif, 2026-08-06,
answering 1a) — turning a book on for everyone signed in is an audience decision,
separate from getting it live, and it keeps its home on the admin screen.

Pure and testable: nothing here spawns wrangler except `visibility`, and nothing
here decides anything the driver could decide differently.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: The slug shape every caller has already validated. Interpolating a slug into
#: SQL is safe only because nothing matching this can carry a quote, and the
#: refusal below is what makes that a fact rather than an assumption.
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def require_slug(slug: str) -> str:
    if not SLUG_RE.match(str(slug or "")):
        raise ValueError(f"not a slug: {slug!r}")
    return slug


# ---------------------------------------------------------------------------
# Accepting the Companion cards
# ---------------------------------------------------------------------------


@dataclass
class AcceptResult:
    """What the accept pass did. `unreadable` is reported, never swallowed."""

    accepted: int = 0
    files: int = 0
    unreadable: list[str] = field(default_factory=list)


def accept_notes_in_doc(doc: dict[str, Any], *, now: str) -> int:
    """Flip this chapter's unreviewed cards to kept. Returns how many moved.

    MIRRORS `companion/store.server.ts acceptNote`, which is the gesture the
    Accept button on the Composer performs, and mirrors it in the narrow sense
    that matters: `review` and `updatedAt`, nothing else. Accepting is a
    judgement ABOUT a note, not an edit OF one, so no other field may move —
    every field written is a field at risk.

    Only `review == "proposed"` is touched. An ABSENT `review` already means kept
    (`explanation-card.ts` renders the "Unreviewed" flag on the explicit string
    alone), so every note written before the field existed, and every note Asif
    wrote himself, is left exactly as it is rather than being stamped with
    today's date for no reason.
    """
    notes = doc.get("notes")
    if not isinstance(notes, list):
        return 0

    changed = 0
    for note in notes:
        if not isinstance(note, dict) or note.get("review") != "proposed":
            continue
        note["review"] = "kept"
        note["updatedAt"] = now
        changed += 1

    if changed:
        doc["updatedAt"] = now
    return changed


def accept_all_notes(book_dir: Path, *, now: str) -> AcceptResult:
    """Accept every unreviewed Companion card in the book.

    A file that will not parse is SKIPPED AND NAMED, never rewritten — the same
    rule as `_student_reader_store.read_doc`, and for the same reason: a document
    that is merely unreadable to us is not an empty one, and writing over it is
    how the 2026-07-28 note loss happened.

    Writing back preserves the on-disk shape (two-space indent, unescaped
    Unicode, trailing newline) so accepting a card produces a diff of the review
    lines and nothing else.
    """
    directory = Path(book_dir) / "_system" / "companion-notes"
    result = AcceptResult()
    if not directory.is_dir():
        return result

    for path in sorted(directory.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            result.unreadable.append(f"{path.name}: {error}")
            continue
        if not isinstance(doc, dict):
            result.unreadable.append(f"{path.name}: not a JSON object")
            continue

        moved = accept_notes_in_doc(doc, now=now)
        if not moved:
            continue
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result.accepted += moved
        result.files += 1

    return result


def count_cards(book_dir: Path) -> int:
    """Companion cards this book would publish — every card with a body.

    MIRRORS `_listener_companion.read_companion`, which keeps a note only if its
    body has text. Counted here so the verification can compare what is live
    against what is on disk without re-rendering the whole book to find out.
    """
    directory = Path(book_dir) / "_system" / "companion-notes"
    if not directory.is_dir():
        return 0

    total = 0
    for path in sorted(directory.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(doc, dict):
            continue
        total += sum(
            1 for note in (doc.get("notes") or []) if isinstance(note, dict) and str(note.get("body") or "").strip()
        )
    return total


def count_unreviewed(book_dir: Path) -> int:
    """How many cards the accept pass WOULD move. Reads nothing else, writes nothing.

    The confirm dialog quotes this before anything happens, so the number Asif
    agrees to is the number that moves.
    """
    directory = Path(book_dir) / "_system" / "companion-notes"
    if not directory.is_dir():
        return 0

    total = 0
    for path in sorted(directory.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(doc, dict):
            continue
        total += sum(
            1 for note in (doc.get("notes") or []) if isinstance(note, dict) and note.get("review") == "proposed"
        )
    return total


# ---------------------------------------------------------------------------
# Visibility
# ---------------------------------------------------------------------------


def publish_sql(slug: str) -> str:
    """The one statement that makes a book readable.

    `status` only. `open_to_all` is absent by design and its absence is the
    policy: this makes the book visible to Asif and to anyone already granted it,
    and says nothing about opening it to every signed-in reader.

    It is an UPDATE, never an INSERT — the row is created by the publish step
    that ran moments earlier, and a statement that could create one here would be
    a second, weaker answer to what a content unit is.
    """
    require_slug(slug)
    return f"UPDATE content_unit SET status = 'published' WHERE slug = '{slug}';"


def visibility(slug: str, *, remote: bool) -> dict[str, Any] | None:
    """This book's two privilege bits as the database currently holds them.

    Returns None when the book has no row at all, which is a different thing from
    a row that is switched off and must not be reported as one.
    """
    from upload_listener_media import d1

    require_slug(slug)
    rows = d1(
        f"SELECT slug, status, open_to_all FROM content_unit WHERE slug = '{slug}'",
        remote=remote,
    )
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# Is the live site running older code than this checkout?
# ---------------------------------------------------------------------------

#: Written by `deploy_listener.sh` after a successful Worker upload, read here.
#: Untracked: it records what THIS machine shipped, and a tracked file would
#: conflict on every deploy while telling a fresh clone something untrue.
STAMP = Path("listener") / ".deployed-commit"

#: Paths whose movement means the deployed Worker is behind. `listener/app` and
#: the config it is built from — NOT the whole directory, or a change to a test
#: or a README would report the site as stale.
CODE_PATHS = (
    "listener/app",
    "listener/workers",
    "listener/package.json",
    "listener/package-lock.json",
    "listener/wrangler.jsonc",
    "listener/vite.config.ts",
)


def code_behind(repo_root: Path) -> dict[str, Any]:
    """How many commits of site code have landed since the Worker was last shipped.

    Reported, never acted on: this button moves a BOOK, and it must not quietly
    start shipping software because a book was ready (Asif, 2026-08-06,
    answering 2a). Every failure answers "unknown" rather than guessing, because
    a wrong "up to date" is worse than no answer.
    """
    import subprocess

    stamp = Path(repo_root) / STAMP
    if not stamp.is_file():
        return {"known": False, "why": "no record of what was last deployed from this machine"}

    commit = stamp.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        return {"known": False, "why": "the deploy record is not a commit id"}

    try:
        out = subprocess.run(
            ["git", "rev-list", "--count", f"{commit}..HEAD", "--", *CODE_PATHS],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        ahead = int(out or "0")
    except (subprocess.CalledProcessError, ValueError, OSError):
        return {"known": False, "why": "that commit is not in this checkout"}

    return {"known": True, "behind": ahead, "deployed": commit[:7]}


# ---------------------------------------------------------------------------
# What was last published, and has anything changed since?
# ---------------------------------------------------------------------------

#: Written after a successful production publish, read by the Book Composer to
#: decide whether its Publish button has anything to do. TRACKED, unlike the
#: deploy stamp above: it is a fact about the BOOK ("this text is what readers
#: have"), it belongs beside the book's other `_system` records, and it should
#: survive a fresh clone.
STAMP_NAME = "production-publish.json"


def stamp_path(book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / STAMP_NAME


def book_fingerprint(book_dir: Path) -> str:
    """One value covering everything a publish would carry to readers.

    The composed prose and the Companion cards, hashed together — the two things
    the Composer can change. Deliberately NOT mtimes: a re-compose that produces
    identical text should not light the Publish button, or the button stops
    meaning "there is something to publish" and starts meaning "something ran".

    Recordings are excluded. They are added by dropping files into `m4a/`, never
    by the Composer, and a fingerprint that moved when they did would make the
    button flicker for a reason its surface cannot explain.
    """
    import hashlib

    digest = hashlib.sha256()
    book_md = Path(book_dir) / "book" / "book.md"
    digest.update(book_md.read_bytes() if book_md.is_file() else b"")

    notes = Path(book_dir) / "_system" / "companion-notes"
    if notes.is_dir():
        for path in sorted(notes.glob("*.json")):
            digest.update(path.name.encode())
            digest.update(path.read_bytes())

    return digest.hexdigest()[:16]


def read_stamp(book_dir: Path) -> dict[str, Any] | None:
    path = stamp_path(book_dir)
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


def write_stamp(book_dir: Path, *, now: str, fingerprint: str, checks: list[dict[str, Any]]) -> Path:
    """Record what went live, and whether it was VERIFIED going live.

    `verified` is stored rather than assumed. A publish whose checks failed must
    not leave a stamp that later reads as "this book is live and current" — the
    Composer treats an unverified stamp as no stamp, so the button stays lit.
    """
    path = stamp_path(book_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "publishedAt": now,
        "fingerprint": fingerprint,
        "verified": all(c.get("ok") for c in checks) if checks else False,
        "checks": checks,
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def pending_changes(book_dir: Path) -> dict[str, Any]:
    """Does this book have anything a publish would change?

    Three answers, and they are not the same thing: never published, published
    but not verified, published and current. The Composer lights its button for
    the first two as well as for a moved fingerprint — a publish that could not
    prove itself is not a publish.
    """
    current = book_fingerprint(book_dir)
    stamp = read_stamp(book_dir)
    if stamp is None:
        return {"pending": True, "reason": "never published to production", "fingerprint": current}
    if not stamp.get("verified"):
        return {"pending": True, "reason": "the last publish could not be verified", "fingerprint": current}
    if stamp.get("fingerprint") != current:
        return {"pending": True, "reason": "chapters or cards changed since the last publish", "fingerprint": current}
    return {
        "pending": False,
        "reason": "live and up to date",
        "fingerprint": current,
        "publishedAt": stamp.get("publishedAt"),
    }


# ---------------------------------------------------------------------------
# Proving it actually landed
# ---------------------------------------------------------------------------


def verify(slug: str, book_dir: Path, *, remote: bool = True, expected: dict[str, int] | None = None) -> list[dict]:
    """Read the LIVE database back and compare it with the book on disk.

    The whole point of this function is that a zero exit code is not evidence.
    `wrangler` can report success for a statement that matched no rows; a media
    upload can leave rows whose object never arrived; and the visibility flip is
    a single UPDATE whose WHERE clause is the one thing nobody would notice
    getting wrong. So every claim the publish makes is asked back of the deployed
    database, by a query written here rather than trusted from there.

    Each check answers with `ok`, what it wanted and what it found, so a failure
    names the discrepancy instead of saying that something went wrong.
    """
    from upload_listener_media import d1

    require_slug(slug)
    want = expected or {}
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    def scalar(sql: str) -> int:
        rows = d1(sql, remote=remote)
        return int(rows[0]["n"]) if rows else 0

    try:
        state = visibility(slug, remote=remote)
    except Exception as error:  # a database we cannot read is a FAILED verification
        check("readable", False, f"could not query the deployed database: {error}")
        return checks

    if state is None:
        check("the book exists", False, "no content row for this slug in the deployed database")
        return checks
    check("the book exists", True, "content row present")

    status = str(state.get("status") or "")
    check("visible", status == "published", f"status is '{status}'")

    # Proof that THIS run wrote the row, not some earlier one. Every other count
    # below would look identical after a publish that silently did nothing, which
    # is the failure this whole function exists to catch.
    since = str(want.get("since") or "")
    if since:
        try:
            rows = d1(f"SELECT published_at FROM unit_detail WHERE slug = '{slug}'", remote=remote)
            stamped = str(rows[0]["published_at"]) if rows else ""
            check("written just now", bool(stamped) and stamped >= since, f"recorded {stamped or 'never'}")
        except Exception as error:
            check("written just now", False, f"could not be read: {error}")

    for table, label, key in (
        ("chapter", "chapters", "chapters"),
        ("companion_note", "Companion cards", "cards"),
        ("episode", "episodes", "episodes"),
    ):
        try:
            found = scalar(f"SELECT COUNT(*) AS n FROM {table} WHERE slug = '{slug}'")
        except Exception as error:
            check(label, False, f"could not be counted: {error}")
            continue
        if key in want:
            check(label, found == want[key], f"{found} live, {want[key]} on disk")
        elif table == "chapter":
            check(label, found > 0, f"{found} live")
        else:
            check(label, True, f"{found} live")

    try:
        total = scalar(f"SELECT COUNT(*) AS n FROM media_asset WHERE slug = '{slug}'")
        up = scalar(f"SELECT COUNT(*) AS n FROM media_asset WHERE uploaded_at IS NOT NULL AND slug = '{slug}'")
        check("media uploaded", total == 0 or up == total, f"{up} of {total} file(s) in the bucket")
    except Exception as error:
        check("media uploaded", False, f"could not be counted: {error}")

    # An episode ROW existing and having its recording LINKED are different
    # facts — a book whose .m4a files were never arranged into m4a/Episodes/
    # (the author's own signal that a recording is finished, per
    # _listener_media.collect_audio) publishes 13-of-13 episode rows and
    # 18-of-18 uploaded files while every one of those episodes has
    # audio_key = NULL, so nothing plays. The two checks above cannot see
    # this — they count rows and uploads, never the join between them. This
    # is what caught it silently slipping through on 2026-08-15.
    try:
        ep_total = scalar(f"SELECT COUNT(*) AS n FROM episode WHERE slug = '{slug}'")
        ep_with_audio = scalar(f"SELECT COUNT(*) AS n FROM episode WHERE slug = '{slug}' AND audio_key IS NOT NULL")
        check(
            "episode audio linked",
            ep_total == 0 or ep_with_audio == ep_total,
            f"{ep_with_audio} of {ep_total} episode(s) have a linked recording"
            + ("" if ep_with_audio == ep_total else " — recordings likely still loose in m4a/, not m4a/Episodes/"),
        )
    except Exception as error:
        check("episode audio linked", False, f"could not be counted: {error}")

    return checks


# ---------------------------------------------------------------------------
# Reaching the right Cloudflare account
# ---------------------------------------------------------------------------

#: The ONLY account this repo publishes to. `wrangler` on this machine is logged
#: in as a DIFFERENT account which does not hold the safinaverse.com zone, so a
#: run that forgets the token does not fail — it quietly publishes somewhere
#: nobody can read. Mirrors the constants in `deploy_listener.sh`.
ACCOUNT_ID = "19cb05067ea7e704f94481df1685ec51"
ACCOUNT_NAME = "asifhussain60@gmail.com"
KEYCHAIN_SERVICE = "cloudflare_api_token"


def cloudflare_env() -> dict[str, str]:
    """The environment every remote step needs, resolved the way the deploy does.

    Environment first, keychain second — the same order and the same keychain
    item as `deploy_listener.sh`, because two ways to answer "which account" is
    how a book ends up published to the wrong one.

    The token is read, never returned to a caller that would print it and never
    logged. Whitespace is stripped: the trailing newline a stored secret usually
    carries produces Cloudflare error 6111 if it survives into the header.

    Raises RuntimeError naming the exact command to fix it — the item is Asif's
    to store, and prompting for it is what keeps the value out of shell history.
    """
    import os
    import subprocess

    token = "".join(os.environ.get("CLOUDFLARE_API_TOKEN", "").split())
    if not token:
        try:
            token = subprocess.run(
                ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as error:
            raise RuntimeError(
                f"no Cloudflare token: not in the environment and no keychain item '{KEYCHAIN_SERVICE}'. "
                f'Store it with: security add-generic-password -U -a "$USER" -s {KEYCHAIN_SERVICE} -w'
            ) from error

    token = "".join(token.split())
    if not token:
        raise RuntimeError(f"the keychain item '{KEYCHAIN_SERVICE}' is empty")

    return {**os.environ, "CLOUDFLARE_API_TOKEN": token, "CLOUDFLARE_ACCOUNT_ID": ACCOUNT_ID}


def account_ok(env: dict[str, str], listener_dir: Path) -> tuple[bool, str]:
    """Does this token resolve to the account that holds safinaverse.com?

    Checked BEFORE anything is written, for the reason in `cloudflare_env`: the
    failure mode of the wrong account is a successful-looking publish to a place
    with no zone, which nobody notices until a reader reports a dead link.
    """
    import subprocess

    from _wrangler import run as wrangler

    try:
        out = wrangler(
            ["npx", "wrangler", "whoami"],
            cwd=str(listener_dir),
            env=env,
            timeout=120,
        ).stdout
    except (OSError, subprocess.SubprocessError) as error:
        return False, f"could not ask Cloudflare who this token is: {error}"

    if ACCOUNT_ID in out:
        return True, ACCOUNT_NAME
    return False, (
        f"this token does not resolve to {ACCOUNT_NAME}. Refusing to publish — the other "
        "account on this machine does not hold the safinaverse.com zone, so anything "
        "published there is unreachable."
    )
