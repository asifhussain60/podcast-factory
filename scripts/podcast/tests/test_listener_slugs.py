"""test_listener_slugs.py — what `deploy_listener.sh --all` may and may not push.

Three properties, and each one is a mistake that was actually made while building
this: a book already on the site must not be dropped because this repo still
calls it a draft; a book never sent must not be swept in by a command whose
everyday use is pushing a note; and a slug whose folder is gone must not take the
whole sweep down with it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _listener_slugs import listener_slugs, resolve  # noqa: E402

# (slug, status) as `iter_content` reports it.
REPO = [
    ("the-master-and-the-disciple", "published"),
    ("degrees-of-excellence", "draft"),
    ("ayyuhal-walad", "published"),
    ("kitab-al-riyad", "draft"),
]


def test_pushes_every_book_the_listener_has_been_sent():
    found = resolve(["ayyuhal-walad", "the-master-and-the-disciple"], REPO)
    assert found.deploy == ["ayyuhal-walad", "the-master-and-the-disciple"]
    assert found.missing == []


def test_keeps_maintaining_a_book_this_repo_still_calls_a_draft():
    # The live case: degrees-of-excellence is a DRAFT here and is on the site.
    # Filtering by repo status would silently stop updating it — the site would
    # go stale for a book nobody had removed from anything.
    found = resolve(["degrees-of-excellence"], REPO)
    assert found.deploy == ["degrees-of-excellence"]


def test_never_sweeps_in_a_book_that_has_never_been_sent():
    # kitab-al-riyad is in the repo and not on the Listener. Sending it would
    # upload its whole recording library from a command that was asked to push
    # some notes. It is not deployed — and it is not silently ignored either.
    found = resolve(["ayyuhal-walad"], REPO)
    assert "kitab-al-riyad" not in found.deploy


def test_names_a_published_book_that_has_never_been_sent():
    found = resolve(["ayyuhal-walad"], REPO)
    assert found.unsent == ["the-master-and-the-disciple"]
    # A draft that was never sent is not reported: nothing about it is pending.
    assert "kitab-al-riyad" not in found.unsent


def test_drops_a_slug_whose_content_is_gone_rather_than_failing_the_run():
    # `load_book` exits the process on the first slug it cannot find, so one
    # stale row would otherwise stop a sweep of a dozen healthy books.
    found = resolve(["ayyuhal-walad", "a-book-since-renamed"], REPO)
    assert found.deploy == ["ayyuhal-walad"]
    assert found.missing == ["a-book-since-renamed"]


def test_reads_the_slugs_out_of_wranglers_chatty_output():
    noisy = '⛅️ wrangler 4.118.0\nRemote database\n[{"results":[{"slug":"a"},{"slug":"b"}],"success":true}]'
    assert listener_slugs(noisy) == ["a", "b"]


def test_refuses_output_it_cannot_parse_rather_than_returning_nothing():
    # An empty list would make --all a command that deploys nothing and reports
    # success, which is the one failure nobody would notice.
    with pytest.raises(ValueError):
        listener_slugs("wrangler: command not found")
