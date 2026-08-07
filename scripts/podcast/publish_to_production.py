#!/usr/bin/env python3
"""Put one book live on the Podcast Factory Library, in one act, and PROVE it.

This is what the "Publish to production" button on the Book Composer runs. It
carries a finished book the whole way — accepts its Companion cards, transcribes
any new episode, pushes its text and recordings to the deployed database and
bucket, turns the book's visibility on, and then reads the live database back to
confirm every one of those things actually happened.

WHY THE VERIFICATION STEP IS NOT OPTIONAL
-----------------------------------------
A zero exit code is not evidence (Asif, 2026-08-06). `wrangler` reports success
for an UPDATE that matched no rows; a media row can exist with its object
missing; and the visibility flip is one statement whose WHERE clause is exactly
the kind of thing that fails silently. So the run does not report success on the
strength of the commands it issued — it asks the deployed database what is
actually there and compares it with the book on disk. A publish that cannot prove
itself is reported as unverified and leaves the Composer's button lit.

WHAT IT DOES NOT DO, AND WHY
----------------------------
It ships NO CODE (Asif, 2026-08-06). `deploy_listener.sh` deploys the Worker,
sweeps branches and pushes `main`; that is a great deal of git for a button
labelled "publish this book", and a book going live must not be able to change
what the site's software does. If the deployed Worker is behind this checkout,
the run SAYS SO and stops there.

It does NOT open the book to every signed-in reader. `open_to_all` stays where it
was, on the admin screen, because who may read a book is a separate decision from
whether the book is finished. See `_production_publish.publish_sql`.

USAGE
-----
    python3 scripts/podcast/publish_to_production.py <slug>
        [--no-accept]        leave unreviewed Companion cards unreviewed
        [--skip-transcripts] do not transcribe new episodes
        [--skip-media]       text, cards and print edition only — no recordings
        [--rebuild-pdf]      re-render the reading edition before pushing it
        [--dry-run]          say what would happen; change nothing, anywhere
        [--json]             one NDJSON event per line (what the button reads)

Every step is reported as it happens rather than at the end: pushing a book's
recordings takes minutes, and a command that says nothing for minutes is one
nobody trusts enough to leave running.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _paths import REPO_ROOT, find_content  # noqa: E402
from _production_publish import (  # noqa: E402
    accept_all_notes,
    account_ok,
    book_fingerprint,
    cloudflare_env,
    code_behind,
    count_cards,
    count_unreviewed,
    pending_changes,
    publish_sql,
    require_slug,
    verify,
    visibility,
    write_stamp,
)

LISTENER = REPO_ROOT / "listener"


class Reporter:
    """Progress, in whichever of the two shapes the caller asked for."""

    def __init__(self, *, as_json: bool) -> None:
        self.as_json = as_json

    def emit(self, event: str, **fields: object) -> None:
        if self.as_json:
            print(json.dumps({"event": event, **fields}), flush=True)
            return
        if event == "step":
            print(f"\n== {fields.get('name')}", flush=True)
        elif event == "error":
            print(f"  ! {fields.get('text')}", file=sys.stderr, flush=True)
        elif event == "check":
            print(
                f"  {'OK  ' if fields.get('ok') else 'FAIL'} {fields.get('name')} — {fields.get('detail')}", flush=True
            )
        elif event == "done":
            print(f"\n{fields.get('text')}", flush=True)
        else:
            print(f"  {fields.get('text')}", flush=True)

    def step(self, name: str) -> None:
        self.emit("step", name=name)

    def log(self, text: str) -> None:
        self.emit("log", text=text)

    def warn(self, text: str) -> None:
        self.emit("warn", text=text)

    def error(self, text: str) -> None:
        self.emit("error", text=text)


def run(argv: list[str], report: Reporter, *, cwd: Path = REPO_ROOT) -> int:
    """Run a child and forward its output line by line as it arrives.

    Line-buffered and merged (stderr into stdout) on purpose: the caller is a
    person watching a progress panel, and a failure that arrives after the
    success it contradicts is worse than no output at all.
    """
    proc = subprocess.Popen(
        argv,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            report.log(line)
    return proc.wait()


def d1_execute(sql: str, report: Reporter) -> int:
    """One statement against the DEPLOYED database."""
    return run(
        ["npx", "wrangler", "d1", "execute", "podcast-listener", "--remote", "--command", sql, "--yes"],
        report,
        cwd=LISTENER,
    )


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Put one book live on the Podcast Factory Library.")
    parser.add_argument("slug")
    parser.add_argument("--no-accept", action="store_true", help="leave unreviewed Companion cards unreviewed")
    parser.add_argument("--skip-transcripts", action="store_true", help="do not transcribe new episodes")
    parser.add_argument("--skip-media", action="store_true", help="text, cards and print edition only")
    parser.add_argument("--rebuild-pdf", action="store_true", help="re-render the reading edition first")
    parser.add_argument("--dry-run", action="store_true", help="say what would happen; change nothing")
    parser.add_argument("--json", action="store_true", help="one NDJSON event per line")
    parser.add_argument(
        "--state",
        action="store_true",
        help="report whether this book has anything to publish, and exit",
    )
    return parser.parse_args(argv)


def report_state(slug: str, book_dir: Path, *, as_json: bool) -> int:
    """What the Publish button needs to know, and nothing that costs anything.

    Reads the book off disk only — no network, no Cloudflare, no token. The
    Composer asks for this on every page load, so it has to be free; the
    expensive question ("is it REALLY live") is answered by the verification at
    the end of a publish and recorded in the stamp this reads.
    """
    state = pending_changes(book_dir)
    state["slug"] = slug
    state["unreviewed"] = count_unreviewed(book_dir)
    state["cards"] = count_cards(book_dir)
    if as_json:
        print(json.dumps(state), flush=True)
    else:
        print(f"{slug}: {state['reason']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = Reporter(as_json=args.json)

    try:
        slug = require_slug(args.slug)
    except ValueError as error:
        report.error(str(error))
        return 2

    found = find_content(slug)
    if not found:
        report.error(f"no book on disk for {slug}")
        return 2
    book_dir = found[2]

    if args.state:
        return report_state(slug, book_dir, as_json=args.json)

    dry = ["--dry-run"] if args.dry_run else []
    started = datetime.now(timezone.utc)
    now = started.isoformat(timespec="seconds").replace("+00:00", "Z")

    # --- 0. The account ------------------------------------------------------
    #
    # FIRST, before a single write, and for the reason `deploy_listener.sh`
    # checks it first: wrangler on this machine is logged in as a different
    # Cloudflare account, so a run without the token does not fail — it publishes
    # somewhere with no zone and looks like it worked. The token is put into this
    # process's environment so every child and every in-process query inherits
    # it; it is never printed.
    report.step("Cloudflare account")
    try:
        os.environ.update(cloudflare_env())
    except RuntimeError as error:
        report.error(str(error))
        return 2
    ok, who = account_ok(dict(os.environ), LISTENER)
    if not ok:
        report.error(who)
        return 2
    report.log(f"ok — {who}")

    # --- 1. The Companion cards ---------------------------------------------
    #
    # Before the push rather than after, because the push reads the cards off
    # disk. Accepting them afterwards would leave the live copy correct and the
    # repo's own record of what shipped one step behind.
    report.step("Companion cards")
    pending = count_unreviewed(book_dir)
    if args.no_accept:
        report.log(f"leaving {pending} card(s) unreviewed, as asked")
    elif args.dry_run:
        report.log(f"would accept {pending} unreviewed card(s)")
    elif pending:
        result = accept_all_notes(book_dir, now=now)
        for name in result.unreadable:
            report.warn(f"left alone, could not be read: {name}")
        report.log(f"accepted {result.accepted} card(s) across {result.files} chapter file(s)")
    else:
        report.log("nothing unreviewed")

    # --- 2. The reading edition ---------------------------------------------
    #
    # Optional, and off unless asked: rendering takes about a minute, and a book
    # whose PDF is already current should not pay for it on every publish.
    if args.rebuild_pdf:
        report.step("Reading edition")
        if args.dry_run:
            report.log("would re-render book/book.pdf")
        elif run([sys.executable, "scripts/podcast/build_book_pdf.py", str(book_dir)], report) != 0:
            report.error("the PDF did not render — nothing has been published")
            return 1

    # --- 3. Transcripts ------------------------------------------------------
    #
    # Ahead of the content push, because the push records the transcript it finds
    # on disk and cannot record one written afterwards. Keyed on the file already
    # existing, so re-publishing a book costs nothing; only a genuinely new
    # episode is paid for. Never fatal — a book whose transcription failed should
    # still reach the site, with that episode simply lacking one.
    if args.skip_transcripts:
        report.step("Transcripts")
        report.log("skipped, as asked")
    else:
        report.step("Transcripts")
        if run([sys.executable, "scripts/podcast/ensure_transcripts.py", slug, *dry], report) != 0:
            report.warn("transcription failed — continuing; those episodes ship without one")

    # --- 4. Text, cards, recordings -----------------------------------------
    report.step("Content")
    if run([sys.executable, "scripts/podcast/publish_to_listener.py", slug, "--remote", *dry], report) != 0:
        report.error("the content push failed — nothing was made visible")
        return 1

    report.step("Media")
    if args.skip_media:
        report.log("skipped, as asked — recordings already in the bucket are untouched")
    elif run([sys.executable, "scripts/podcast/upload_listener_media.py", slug, "--remote", *dry], report) != 0:
        report.error("uploading failed — the book is live but incomplete, and still not visible")
        return 1

    # --- 5. Visibility -------------------------------------------------------
    #
    # LAST of the writes, and only if everything above succeeded. A book becomes
    # readable at the moment it is complete, never before — which is what makes a
    # failed run safe to simply run again.
    report.step("Visibility")
    if args.dry_run:
        report.log(f"would run: {publish_sql(slug)}")
        report.emit("done", text="dry run — nothing changed", slug=slug, dryRun=True, verified=False, checks=[])
        return 0

    if d1_execute(publish_sql(slug), report) != 0:
        report.error("the book is live but could not be made visible")
        return 1
    state = visibility(slug, remote=True)
    if state is not None:
        report.log(f"status is now '{state.get('status')}'")
        if not state.get("open_to_all"):
            report.log("not open to everyone — only people you have granted it can read it")

    # --- 6. Prove it ---------------------------------------------------------
    report.step("Verifying")
    expected: dict[str, object] = {"cards": count_cards(book_dir), "since": now}
    if args.skip_media:
        # Nothing was uploaded this run, so an incomplete bucket is the state we
        # were asked to leave alone rather than a failure of this publish.
        expected["skip_media"] = True
    checks = verify(slug, book_dir, remote=True, expected=expected)
    if args.skip_media:
        checks = [c for c in checks if c["name"] != "media uploaded"]
    for c in checks:
        report.emit("check", name=c["name"], ok=c["ok"], detail=c["detail"])

    verified = bool(checks) and all(c["ok"] for c in checks)
    write_stamp(book_dir, now=now, fingerprint=book_fingerprint(book_dir), checks=checks)

    # --- 7. Is the site's code behind? --------------------------------------
    report.step("Site code")
    fresh = code_behind(REPO_ROOT)
    if not fresh["known"]:
        report.log(f"unknown — {fresh['why']}")
    elif fresh["behind"]:
        report.warn(
            f"the live site runs code from {fresh['deployed']}, {fresh['behind']} commit(s) behind. "
            "This publish did not change that: run scripts/podcast/deploy_listener.sh --worker-only."
        )
    else:
        report.log("up to date")

    report.emit(
        "done",
        text=(
            f"{slug} is live and verified at https://podcast-factory.safinaverse.com"
            if verified
            else f"{slug} was published but could NOT be verified — see the failed checks above"
        ),
        slug=slug,
        verified=verified,
        cardsAccepted=0 if args.no_accept else pending,
        checks=checks,
        dryRun=False,
    )
    return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
