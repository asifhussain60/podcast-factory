#!/usr/bin/env python3
"""Put one book on the Podcast Factory Library target Asif chooses, and PROVE it.

This is what the Publish button on the Book Composer runs. It carries a finished
book the whole way — accepts its Companion cards, transcribes any new episode,
re-records the read-aloud narration for any chapter whose text changed, pushes
its text and recordings to a database and bucket, reads that database back to
confirm every one of those things actually happened, and only then turns the
book's visibility on.

By default it does that twice (Asif, 2026-08-10): once against localhost and once
against the deployed site, so the copy he reviews on `localhost:5273` and the
copy his readers open are the same book. LOCALHOST GOES FIRST, and that order is
the safety property rather than a preference — everything that can fail fails
against the copy nobody reads, and a run that was going to break never touches
the live site. A local failure stops the run; publishing to production after the
rehearsal failed would make the rehearsal pointless.

The Book Composer can also target only localhost or only production (Asif,
2026-08-13). Localhost-only is a rehearsal and does NOT clear the production
publish button's state: the production stamp remains a fact about what real
readers have.

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
        [--skip-narration]   do not re-record chapters whose text changed
        [--skip-media]       text, cards and print edition only — no recordings
        [--target where]      localhost, production, or both (default)
        [--skip-local]       old spelling for --target production
        [--local-audio]      copy recordings to the local bucket too
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

from _listener_book import read_episodes, split_chapters  # noqa: E402
from _narration_plan import narrate  # noqa: E402
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


def d1_execute(sql: str, report: Reporter, *, remote: bool) -> int:
    """One statement against one of the two databases.

    The flag is a parameter rather than a constant because the same book now goes
    to both (Asif, 2026-08-10) and a hardcoded `--remote` in the shared path is
    the way a "publish locally" run silently writes to the live site instead.
    """
    return run(
        [
            "npx",
            "wrangler",
            "d1",
            "execute",
            "podcast-listener",
            "--remote" if remote else "--local",
            "--command",
            sql,
            "--yes",
        ],
        report,
        cwd=LISTENER,
    )


#: The two places a book goes, in the order it goes to them. LOCAL FIRST, and that
#: order is the safety property: everything that can fail — a malformed chapter, a
#: missing recording, a verification that does not add up — fails against the copy
#: nobody reads, and the live site is never touched by a run that was going to
#: break anyway. `label` is what the progress panel shows; `url` is where the book
#: can be looked at afterwards.
TARGETS = (
    {"remote": False, "label": "localhost", "url": "http://localhost:5273"},
    {"remote": True, "label": "production", "url": "https://podcast-factory.safinaverse.com"},
)


def expected_counts(book_dir: Path) -> dict[str, int]:
    """How many chapters and episodes the publisher will write, read off disk.

    The same two readers `publish_to_listener.py` builds its rows from, so the
    number handed to `verify` is the number the INSERTs carried. The remote push
    is one wrangler call per batch with no transaction around them; without
    these, the read-back accepted any chapter count above zero and a run that
    failed between two batches left a half-empty book reported as fine.
    """
    book_md = Path(book_dir) / "book" / "book.md"
    chapters = split_chapters(book_md.read_text(encoding="utf-8")) if book_md.exists() else []
    return {"chapters": len(chapters), "episodes": len(read_episodes(Path(book_dir)))}


def selected_targets(args: argparse.Namespace) -> list[dict]:
    """The destination set for this run, preserving the old CLI spelling."""
    target = "production" if args.skip_local else args.target
    if target == "both":
        return list(TARGETS)
    return [t for t in TARGETS if t["label"] == target]


def push(target: dict, slug: str, book_dir: Path, args, report: Reporter, *, now: str) -> tuple[bool, list[dict]]:
    """Put the book into ONE of the two databases and prove it landed there.

    Content, then recordings, then the read-back, then visibility — the same four
    steps against either site, because a difference between them is a difference
    nobody would find until a reader did. `--remote` is the only thing that
    changes, and the checks are the same checks.

    Visibility is written LAST and only if every check before it passed, so a
    failed run leaves a book that is incomplete AND invisible rather than
    incomplete and readable. That is what makes a failed run safe to simply run
    again. Until 2026-09-04 the flip came before the read-back, which meant a
    read-back that failed had just described a book readers could already open;
    the checks decide the flip now, and "visible" is re-read after it.
    """
    remote, label = target["remote"], target["label"]
    flag = ["--remote"] if remote else []
    dry = ["--dry-run"] if args.dry_run else []
    # RECORDINGS ARE NOT COPIED TO LOCALHOST (Asif, 2026-08-10: "I do not want
    # content copied twice for books"). A recording in the local bucket is a
    # second copy of a file already on the same disk — 0.98 GB of the 1.04 GB it
    # held, in 30 files. Covers, deck pages and the print edition still go, all
    # 60 MB of them, because a local page missing its cover is not the page it is
    # standing in for. `--local-audio` puts them back for the rare case of
    # actually playing an episode locally.
    no_audio = ["--no-audio"] if (not remote and not args.local_audio) else []

    report.step(f"Content · {label}")
    if run([sys.executable, "scripts/podcast/publish_to_listener.py", slug, *flag, *dry], report) != 0:
        report.error(f"the content push to {label} failed — nothing was made visible there")
        return False, []

    report.step(f"Media · {label}")
    if args.skip_media:
        report.log("skipped, as asked — recordings already in the bucket are untouched")
    else:
        if no_audio:
            report.log("recordings are not copied here — they play from the live bucket, not a duplicate")
        if run([sys.executable, "scripts/podcast/upload_listener_media.py", slug, *flag, *no_audio, *dry], report) != 0:
            report.error(f"uploading to {label} failed — the book is there but incomplete, and still not visible")
            return False, []

    if args.dry_run:
        report.step(f"Visibility · {label}")
        report.log(f"would run: {publish_sql(slug)}")
        return True, []

    report.step(f"Verifying · {label}")
    expected: dict[str, object] = {"cards": count_cards(book_dir), "since": now, **expected_counts(book_dir)}
    # The media check asks whether every inventoried file is in the bucket. On
    # localhost the recordings deliberately are not, so asking would fail a
    # correct run — and a check that fails when nothing is wrong is how a
    # verification stops being read. Dropped for the same reason `--skip-media`
    # drops it: the bucket is in the state we asked for, not a broken one.
    skip_media_check = args.skip_media or bool(no_audio)
    if skip_media_check:
        expected["skip_media"] = True
    checks = verify(slug, book_dir, remote=remote, expected=expected)
    if skip_media_check:
        checks = [c for c in checks if c["name"] != "media uploaded"]

    # The site's name travels WITH the check, because both sites report the same
    # check names and a merged list that did not say which one failed would be
    # unreadable in the stamp and in the panel.
    def labelled(found: list[dict]) -> list[dict]:
        return [{**c, "name": f"{c['name']} ({label})", "target": label} for c in found]

    # "visible" is the one check that cannot pass yet on a first publish — it is
    # what the flip below produces — so it does not vote on whether to flip.
    gate = [c for c in checks if c["name"] != "visible"]
    if not gate or not all(c["ok"] for c in gate):
        for c in labelled(checks):
            report.emit("check", name=c["name"], ok=c["ok"], detail=c["detail"])
        report.error(f"the book reached {label} but the read-back does not match the book on disk — not made visible")
        return False, labelled(checks)

    report.step(f"Visibility · {label}")
    if d1_execute(publish_sql(slug), report, remote=remote) != 0:
        report.error(f"the book reached {label} but could not be made visible there")
        return False, labelled(checks)
    state = visibility(slug, remote=remote)
    status = str((state or {}).get("status") or "")
    if state is not None and not state.get("open_to_all"):
        report.log("not open to everyone — only people you have granted it can read it")
    visible = {"name": "visible", "ok": status == "published", "detail": f"status is '{status}'"}
    checks = labelled([*gate, visible])
    for c in checks:
        report.emit("check", name=c["name"], ok=c["ok"], detail=c["detail"])
    return bool(checks) and all(c["ok"] for c in checks), checks


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Put one book live on the Podcast Factory Library.")
    parser.add_argument("slug")
    parser.add_argument("--no-accept", action="store_true", help="leave unreviewed Companion cards unreviewed")
    parser.add_argument("--skip-transcripts", action="store_true", help="do not transcribe new episodes")
    parser.add_argument(
        "--skip-narration",
        action="store_true",
        help="do not re-record chapters whose text changed (they keep their existing audio)",
    )
    parser.add_argument("--skip-media", action="store_true", help="text, cards and print edition only")
    parser.add_argument(
        "--local-audio",
        action="store_true",
        help="copy recordings to the local bucket too (a second copy of files already on this disk)",
    )
    parser.add_argument(
        "--skip-local",
        action="store_true",
        help="old spelling for --target production",
    )
    parser.add_argument(
        "--target",
        choices=("both", "localhost", "production"),
        default="both",
        help="where to publish: both sites, localhost only, or production only",
    )
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

    # Narration is reported, and deliberately does NOT feed `pending`. It is
    # derived from `book.md`, which the fingerprint already covers: prose that
    # changed lights the button on its own, and this step then re-records it. A
    # second input to the same decision could only ever disagree with the first.
    # Wrapped because this runs on every page load — a book with an unreadable
    # manifest must still get an answer about its text and cards.
    try:
        from reader_narration import narration_plan

        plan = narration_plan(book_dir)
        state["narration"] = (
            {"enabled": False, "reason": plan.reason}
            if not plan.enabled
            else {
                "enabled": True,
                "stale": len(plan.render),
                "current": len(plan.current),
                "chapters": [{"title": c.title, "reason": c.reason} for c in plan.render],
            }
        )
    except Exception as error:
        state["narration"] = {"enabled": False, "reason": f"could not be read: {error}"}

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
    targets = selected_targets(args)
    has_production_target = any(t["remote"] for t in targets)

    # --- 0. The account ------------------------------------------------------
    #
    # FIRST before a remote write, and skipped for localhost-only. Local D1 and
    # local media do not need a Cloudflare token, so requiring one for a rehearsal
    # would turn the safest publish target into the hardest one to use.
    if has_production_target:
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

    # --- 3b. The read-aloud narration ---------------------------------------
    #
    # Before the content push and outside the target loop; see `narrate` for why
    # both of those are load-bearing rather than tidy.
    narrate(book_dir, args, report)

    # --- 4. Destination(s), in order ----------------------------------------
    #
    # When both destinations are selected, localhost remains first. When only one
    # is selected, the run does exactly that one thing; no hidden side effect and
    # no surprise production write from a local rehearsal.
    checks: list[dict] = []
    for target in targets:
        ok, target_checks = push(target, slug, book_dir, args, report, now=now)
        checks.extend(target_checks)
        if not ok and not args.dry_run:
            if has_production_target:
                write_stamp(book_dir, now=now, fingerprint=book_fingerprint(book_dir), checks=checks)
            report.emit(
                "done",
                text=f"stopped at {target['label']} — the selected publish did not finish",
                slug=slug,
                verified=False,
                checks=checks,
                dryRun=False,
            )
            return 1

    if args.dry_run:
        report.emit("done", text="dry run — nothing changed", slug=slug, dryRun=True, verified=False, checks=[])
        return 0

    # --- 5. Prove it ---------------------------------------------------------
    #
    # The production stamp is written only when production was selected. A local
    # rehearsal can be verified without pretending readers have the new copy.
    verified = bool(checks) and all(c["ok"] for c in checks)
    if has_production_target:
        write_stamp(book_dir, now=now, fingerprint=book_fingerprint(book_dir), checks=checks)

    # --- 7. Is the site's code behind? --------------------------------------
    if has_production_target:
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
            f"{slug} is live and verified on {' and '.join(t['label'] for t in targets)} — "
            + ", ".join(t["url"] for t in targets)
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
