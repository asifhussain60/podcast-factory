"""Which books `deploy_listener.sh --all` should push, and which it must not.

`--all` means EVERY BOOK THE LISTENER HAS ALREADY BEEN SENT — not every book this
repo calls published. The difference is deliberate and it is about cost: a book
that has never been sent brings its whole recording library with it, and a
command whose everyday use is "push the notes I just wrote" must not quietly
upload several gigabytes of audio because a book was marked published last week.
A book reaches the Listener the first time by being NAMED; after that `--all`
keeps it current.

"Has been sent" is a row in `unit_detail`, which only publish_to_listener.py
writes. NOT `content_unit`: that is the access record and the seed migration
created a row for every book in the repo, so asking it returns all twenty-one —
including twelve volumes nobody has ever published anywhere.

Nothing is hidden by the rule, which is the other half of it: a book published
here and never sent is REPORTED, by name, every time `--all` runs.

Repo status is deliberately NOT the filter either, and there is a live example of
why: `degrees-of-excellence` is a DRAFT in this repo and is on the Listener. Had
`--all` meant "every book published here", it would have quietly stopped
maintaining a book that is already on the site.

One more filter, and it is a correctness one rather than a policy: a slug can sit
in `content_unit` after its folder has been renamed or removed, and
`publish_to_listener.load_book` exits the whole run on the first slug it cannot
find. Those are dropped from the list and named, so one stale row cannot stop a
sweep of a dozen good books.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _paths import find_content, iter_content, slug_of  # noqa: E402


@dataclass
class Resolution:
    """The answer, split by what the caller should DO with each part."""

    deploy: list[str] = field(default_factory=list)
    """On the Listener and present on disk. These are pushed."""

    missing: list[str] = field(default_factory=list)
    """On the Listener, with no content directory here. Reported, never pushed."""

    unsent: list[str] = field(default_factory=list)
    """Published here and never sent. Reported, so `--all` never looks complete."""


def resolve(listener_slugs: list[str], repo: list[tuple[str, str]]) -> Resolution:
    """Split the two lists into what to push and what to say.

    `repo` is (slug, status) for every book on disk — passed in rather than read
    here so the rule can be tested without a filesystem shaped like the library.
    """
    on_disk = {slug for slug, _ in repo}
    published = {slug for slug, status in repo if status == "published"}
    known = set(listener_slugs)

    return Resolution(
        deploy=sorted(s for s in known if s in on_disk),
        missing=sorted(s for s in known if s not in on_disk),
        unsent=sorted(published - known),
    )


def listener_slugs(wrangler_json: str) -> list[str]:
    """The slugs out of `wrangler d1 execute --json` output.

    wrangler prints progress lines before the payload, so parsing starts at the
    first bracket — the same reading `deploy_listener.sh` does for its invited-
    people count. A shape it cannot read raises, because a silently empty list
    would make `--all` a command that deploys nothing and says it worked.
    """
    at = wrangler_json.find("[")
    if at == -1:
        raise ValueError("no JSON payload in the wrangler output")
    rows = json.loads(wrangler_json[at:])[0]["results"]
    return [str(row["slug"]) for row in rows]


def repo_books() -> list[tuple[str, str]]:
    """(slug, status) for every book in `content/`, works expanded to volumes."""
    return [(slug_of(directory), status) for status, _bucket, directory in iter_content()]


def main(argv: list[str]) -> int:
    """Print three tab-separated lines for the shell: DEPLOY, MISSING, UNSENT.

    Always three, always in this order, even when empty — a caller that reads by
    line prefix cannot then be surprised by a line that is not there.
    """
    if len(argv) != 2:
        print("usage: _listener_slugs.py <wrangler-json>", file=sys.stderr)
        return 2

    try:
        found = resolve(listener_slugs(argv[1]), repo_books())
    except Exception as error:  # noqa: BLE001 — the caller dies on any of them
        print(f"could not read the book list: {error}", file=sys.stderr)
        return 1

    # A last guard against pushing something that is not there: `find_content`
    # is what the publish step itself calls, so this asks the same question the
    # same way rather than trusting the directory scan above to agree with it.
    found.deploy = [slug for slug in found.deploy if find_content(slug) is not None]

    print(f"DEPLOY\t{' '.join(found.deploy)}")
    print(f"MISSING\t{' '.join(found.missing)}")
    print(f"UNSENT\t{' '.join(found.unsent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
