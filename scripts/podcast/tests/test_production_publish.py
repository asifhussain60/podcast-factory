"""The Publish button's two dangerous halves, pinned.

Everything in `_production_publish.py` either REWRITES A FILE ASIF WROTE IN or
WRITES THE COLUMN THAT MAKES A BOOK PUBLIC. Both fail quietly when they fail:
an over-broad accept stamps somebody else's note with today's date and nothing
says so, and a visibility statement with the wrong WHERE clause reports success
having matched no rows. These tests are the only thing standing between either
and production.

The verification helpers are exercised where they are pure. `verify` itself
talks to the deployed database and is not simulated here — a fake wrangler would
pin the shape of a mock rather than the shape of D1, which is exactly the kind of
test that passes while the thing it names is broken.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
# The publisher's own suite already builds the real schema from every migration
# and a minimal book. Borrowing both is what lets the composition below be tested
# against the schema production actually runs, rather than a second copy of it.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _production_publish import (  # noqa: E402
    ACCOUNT_ID,
    accept_all_notes,
    accept_notes_in_doc,
    book_fingerprint,
    cloudflare_env,
    code_behind,
    count_cards,
    count_unreviewed,
    pending_changes,
    publish_sql,
    require_slug,
    write_stamp,
)

NOW = "2026-08-06T18:00:00Z"


def note(nid: str, **kw):
    base = {"id": nid, "kind": "explanation", "body": "The five conditions are named later.", "quote": "q"}
    base.update(kw)
    return base


def book(tmp_path: Path, chapters: dict[str, list[dict]] | None = None, prose: str = "# One\n") -> Path:
    directory = tmp_path / "the-book"
    (directory / "book").mkdir(parents=True)
    (directory / "book" / "book.md").write_text(prose, encoding="utf-8")
    notes_dir = directory / "_system" / "companion-notes"
    notes_dir.mkdir(parents=True)
    for key, notes in (chapters or {}).items():
        (notes_dir / f"{key}.json").write_text(
            json.dumps({"slug": "the-book", "chapter": key, "notes": notes}, indent=2) + "\n",
            encoding="utf-8",
        )
    return directory


# ─── the slug is the only reason the SQL is safe ─────────────────────────────
def test_a_slug_that_could_carry_sql_is_refused() -> None:
    """`publish_sql` interpolates. That is safe ONLY because nothing matching
    SLUG_RE can carry a quote, so the refusal is load-bearing, not hygiene."""
    for bad in ("a'; DROP TABLE content_unit;--", "Slug", "with space", "", "-lead", "trail-"):
        with pytest.raises(ValueError):
            require_slug(bad)


def test_a_real_slug_passes_and_reaches_the_statement() -> None:
    assert require_slug("the-master-and-the-disciple")
    assert "'the-master-and-the-disciple'" in publish_sql("the-master-and-the-disciple")


# ─── visibility ──────────────────────────────────────────────────────────────
def test_publishing_writes_status_and_says_nothing_about_who_may_read() -> None:
    """Asif's answer 1a, in one assertion. Making a book readable and opening it
    to every signed-in reader are different decisions, and this statement is the
    first one only — an `open_to_all` here would silently make it both."""
    sql = publish_sql("a-book")
    assert "status = 'published'" in sql
    assert "open_to_all" not in sql


def test_publishing_updates_and_can_never_create_a_book() -> None:
    """An INSERT here would be a second answer to what a content unit is, and it
    would create one with no chapters, no title and no bucket."""
    sql = publish_sql("a-book").upper()
    assert sql.startswith("UPDATE")
    assert "INSERT" not in sql


def test_the_two_halves_compose_into_exactly_one_change(tmp_path: Path) -> None:
    """The whole design, executed against the real schema.

    The pipeline's own tests prove it leaves a book invisible; this proves the
    button's statement is what makes it visible AND that it changes nothing else.
    `open_to_all` staying 0 through a full publish is Asif's answer 1a as a fact
    about a row rather than a claim about a string.
    """
    from publish_to_listener import build_sql
    from test_publish_to_listener import a_book, db_with_schema  # the real migrations

    conn = db_with_schema()
    conn.executescript(build_sql(a_book(tmp_path), published_at=NOW, commit=None))
    assert conn.execute("SELECT status, open_to_all FROM content_unit WHERE slug='test-book'").fetchone() == (
        "draft",
        0,
    )

    conn.executescript(publish_sql("test-book"))
    assert conn.execute("SELECT status, open_to_all FROM content_unit WHERE slug='test-book'").fetchone() == (
        "published",
        0,
    )


def test_publishing_one_book_makes_no_other_book_visible(tmp_path: Path) -> None:
    """The WHERE clause, which is the one thing here that fails silently: an
    UPDATE that matched every row would report exactly the same success."""
    from test_publish_to_listener import db_with_schema

    conn = db_with_schema()
    before = conn.execute("SELECT count(*) FROM content_unit WHERE status='published'").fetchone()[0]
    conn.executescript(publish_sql("kitab-al-riyad"))
    after = conn.execute("SELECT count(*) FROM content_unit WHERE status='published'").fetchone()[0]
    assert after == before + 1
    assert conn.execute("SELECT status FROM content_unit WHERE slug='kunooz-al-hikmah'").fetchone()[0] == "draft"


# ─── accepting cards ─────────────────────────────────────────────────────────
def test_only_proposed_notes_move() -> None:
    doc = {
        "notes": [
            note("student:aaa", review="proposed"),
            note("student:bbb", review="kept"),
            note("uuid-of-a-note-asif-wrote"),  # no review key at all
        ]
    }
    assert accept_notes_in_doc(doc, now=NOW) == 1
    assert doc["notes"][0]["review"] == "kept"
    assert doc["notes"][1]["review"] == "kept"
    assert "review" not in doc["notes"][2]


def test_a_note_without_a_review_field_is_left_completely_alone() -> None:
    """ABSENT means kept — every note written before the field existed, and every
    note Asif wrote by hand. Stamping those with today's date would rewrite his
    own notes to record something that did not happen to them."""
    his = note("uuid-1")
    doc = {"notes": [his]}
    accept_notes_in_doc(doc, now=NOW)
    assert his == note("uuid-1"), "not one field moved"


def test_accepting_touches_review_and_updatedAt_and_nothing_else() -> None:
    """Mirrors `store.server.ts acceptNote`. Accepting is a judgement ABOUT a
    note, never an edit OF one — every extra field written is a field at risk."""
    before = note("student:aaa", review="proposed", anchor="a", etymology=["x"], createdAt="old")
    doc = {"notes": [dict(before)]}
    accept_notes_in_doc(doc, now=NOW)
    after = doc["notes"][0]
    assert after["review"] == "kept" and after["updatedAt"] == NOW
    for key, value in before.items():
        if key != "review":
            assert after[key] == value


def test_nothing_moves_means_nothing_is_stamped() -> None:
    """A run with nothing to accept must leave the document byte-identical, or
    every publish produces a diff of dates and the real ones stop standing out."""
    doc = {"notes": [note("student:aaa", review="kept")], "updatedAt": "yesterday"}
    assert accept_notes_in_doc(doc, now=NOW) == 0
    assert doc["updatedAt"] == "yesterday"


def test_a_malformed_note_does_not_stop_the_ones_around_it() -> None:
    doc = {"notes": ["not a note", note("student:aaa", review="proposed"), None]}
    assert accept_notes_in_doc(doc, now=NOW) == 1


def test_an_unreadable_file_is_named_and_never_rewritten(tmp_path: Path) -> None:
    """The 2026-07-28 loss in miniature: a document that is merely unreadable to
    us is not an empty one, and writing over it destroys notes."""
    directory = book(tmp_path, {"one": [note("student:aaa", review="proposed")]})
    broken = directory / "_system" / "companion-notes" / "two.json"
    broken.write_text("{ this is not json", encoding="utf-8")

    result = accept_all_notes(directory, now=NOW)
    assert result.accepted == 1
    assert any("two.json" in name for name in result.unreadable)
    assert broken.read_text(encoding="utf-8") == "{ this is not json"


def test_counting_matches_what_accepting_would_do(tmp_path: Path) -> None:
    """The dialog quotes the count before anything happens; if the two could
    disagree, Asif would agree to a number and a different one would move."""
    directory = book(
        tmp_path,
        {
            "one": [note("student:a", review="proposed"), note("student:b", review="kept")],
            "two": [note("student:c", review="proposed"), note("uuid-d")],
        },
    )
    expected = count_unreviewed(directory)
    assert expected == 2
    assert accept_all_notes(directory, now=NOW).accepted == expected


def test_cards_counted_for_verification_are_the_ones_that_publish(tmp_path: Path) -> None:
    """MIRRORS `_listener_companion.read_companion`, which keeps a note only if
    its body has text. A count that included the empty ones would fail the
    verification on every book that has one."""
    directory = book(
        tmp_path,
        {"one": [note("student:a"), note("student:b", body="   "), note("student:c", body="")]},
    )
    assert count_cards(directory) == 1


# ─── the fingerprint and the stamp ───────────────────────────────────────────
def test_the_button_lights_when_prose_changes(tmp_path: Path) -> None:
    directory = book(tmp_path, {"one": [note("student:a")]})
    before = book_fingerprint(directory)
    (directory / "book" / "book.md").write_text("# One\n\nA new sentence.\n", encoding="utf-8")
    assert book_fingerprint(directory) != before


def test_the_button_lights_when_a_card_changes(tmp_path: Path) -> None:
    directory = book(tmp_path, {"one": [note("student:a")]})
    before = book_fingerprint(directory)
    path = directory / "_system" / "companion-notes" / "one.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["notes"][0]["body"] = "A different explanation."
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    assert book_fingerprint(directory) != before


def test_a_recompose_producing_identical_text_does_not_light_the_button(tmp_path: Path) -> None:
    """The fingerprint is CONTENT, never mtimes. Otherwise the button stops
    meaning "there is something to publish" and starts meaning "something ran"."""
    directory = book(tmp_path, {"one": [note("student:a")]})
    before = book_fingerprint(directory)
    (directory / "book" / "book.md").write_text("# One\n", encoding="utf-8")  # rewritten, identical
    assert book_fingerprint(directory) == before


def test_a_book_never_published_is_pending(tmp_path: Path) -> None:
    directory = book(tmp_path, {"one": [note("student:a")]})
    state = pending_changes(directory)
    assert state["pending"] and "never published" in state["reason"]


def test_a_publish_that_failed_its_checks_leaves_the_button_lit(tmp_path: Path) -> None:
    """THE reason the stamp records `verified` instead of merely existing. A run
    whose checks failed must not leave behind a record that later reads as "this
    book is live and current" — that is the assumption Asif asked to remove."""
    directory = book(tmp_path, {"one": [note("student:a")]})
    write_stamp(
        directory,
        now=NOW,
        fingerprint=book_fingerprint(directory),
        checks=[{"name": "visible", "ok": False, "detail": "status is 'draft'"}],
    )
    state = pending_changes(directory)
    assert state["pending"] and "could not be verified" in state["reason"]


def test_a_verified_publish_of_unchanged_content_is_not_pending(tmp_path: Path) -> None:
    directory = book(tmp_path, {"one": [note("student:a")]})
    write_stamp(
        directory,
        now=NOW,
        fingerprint=book_fingerprint(directory),
        checks=[{"name": "visible", "ok": True, "detail": "status is 'published'"}],
    )
    assert pending_changes(directory)["pending"] is False


def test_editing_after_a_verified_publish_lights_it_again(tmp_path: Path) -> None:
    directory = book(tmp_path, {"one": [note("student:a")]})
    write_stamp(
        directory,
        now=NOW,
        fingerprint=book_fingerprint(directory),
        checks=[{"name": "visible", "ok": True, "detail": "ok"}],
    )
    (directory / "book" / "book.md").write_text("# One\n\nEdited.\n", encoding="utf-8")
    state = pending_changes(directory)
    assert state["pending"] and "changed since" in state["reason"]


def test_a_stamp_with_no_checks_is_not_a_verified_publish(tmp_path: Path) -> None:
    directory = book(tmp_path, {"one": [note("student:a")]})
    write_stamp(directory, now=NOW, fingerprint=book_fingerprint(directory), checks=[])
    assert pending_changes(directory)["pending"] is True


# ─── is the live site behind? ────────────────────────────────────────────────
def test_no_deploy_record_answers_unknown_rather_than_up_to_date(tmp_path: Path) -> None:
    """A wrong "up to date" is worse than no answer: it tells Asif the live site
    is running code it may not be."""
    assert code_behind(tmp_path)["known"] is False


def test_a_deploy_record_that_is_not_a_commit_answers_unknown(tmp_path: Path) -> None:
    (tmp_path / "listener").mkdir()
    (tmp_path / "listener" / ".deployed-commit").write_text("not-a-sha\n", encoding="utf-8")
    assert code_behind(tmp_path)["known"] is False


# ─── the account ─────────────────────────────────────────────────────────────
def test_the_account_id_matches_the_deploy_script() -> None:
    """Two answers to "which Cloudflare account" is how a book gets published to
    the one that does not hold the safinaverse.com zone — where it looks
    published and is unreachable."""
    deploy = (SCRIPT_DIR / "deploy_listener.sh").read_text(encoding="utf-8")
    assert ACCOUNT_ID in deploy


def test_cloudflare_token_whitespace_is_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    """The macOS keychain value can carry a newline; Wrangler turns that into an
    invalid Authorization header unless every whitespace character is removed."""
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "abc\n123\t")

    env = cloudflare_env()

    assert env["CLOUDFLARE_API_TOKEN"] == "abc123"
    assert env["CLOUDFLARE_ACCOUNT_ID"] == ACCOUNT_ID
