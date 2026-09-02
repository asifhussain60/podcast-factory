#!/usr/bin/env python3
"""downsize_audio.py — bring shippable episode audio down to a target bitrate.

WHY THIS EXISTS. `upload_listener_media.py` moves bytes verbatim — it transcodes
nothing and enforces no size cap. NotebookLM hands back ~257 kbps m4a, and some
books carry 192 kbps mp3, against a 10 GB R2 free tier.

THE TARGET IS A SPOKEN-WORD PROFILE, NOT A BITRATE. Every file this tool touches
is speech — lectures, two-host podcasts, audiobook narration — never music. Bit
rate alone is the wrong dial for it: a 128 kbps STEREO encode of a centred voice
spends half its bits describing a channel difference that is not there. The
profile is therefore 48 kbps, MONO, 22.05 kHz, and each part is load-bearing:

  * mono, because both NotebookLM hosts and every lecture recording are centred;
    downmixing frees the bits rather than discarding anything a listener hears.
  * 22.05 kHz carries ~11 kHz of bandwidth. Speech intelligibility lives below
    8 kHz, so nothing audible in a voice is above the ceiling.
  * 48 kbps mono gives the encoder MORE bits per channel than the 63 kbps stereo
    that 17 of this library's books already ship at and have shipped at for
    months — the profile is calibrated to audio already in the reader's hands,
    not to a number chosen in the abstract.

That is why the old 128 kbps floor is gone. It was set for a stereo-shaped guess
about quality and refused every bitrate that would actually have helped, which is
how five books stayed at 127-256 kbps while the tool reported itself working.

WHAT IT WILL NOT DO, deliberately:

  * It never encodes UP. A file already at or below the floor is reported and
    left alone — re-encoding a 24 kbps Sessions recording to 128 kbps would make
    it bigger AND lossier, which is the exact opposite of the point. The floor is
    a floor, not a target.
  * It never touches `source/`. That is raw source audio, is not uploaded, and is
    the provenance record for a book.
  * It writes NOTHING without `--apply`. Re-encoding is lossy and irreversible, so
    a dry run that prints the whole plan is the default and the only safe habit.

ONE SET OF AUDIO, AND THE MASTERS GO WITH IT (Asif, 2026-09-02). This tool used
to promote each original into `Audio/` and keep it forever, on the reasoning that
a master is the one thing a future re-encode could start from. He has decided
against that, and the decision is informed: he A/B-tested this profile against the
127 kbps stereo encode, could not tell them apart, and does not want two copies of
every recording on disk. `prune_masters` therefore DELETES `Audio/` once the
shipping file beside it conforms — 3.74 GB across six books when this was written.

Be clear about what that costs, because it is not recoverable. When the master is
gone the 48 kbps file is the only copy in existence, so the profile can never be
revised upward for that recording: re-encoding 48 kbps to anything higher only
adds bytes to audio that has already lost what it lost, and NotebookLM cannot
hand back the same episode twice. Choosing the profile and discarding the masters
are one decision, and it has been made.

The ORDER is what keeps that safe. Each conversion goes to a temp file and
replaces the original only after ffmpeg exits clean, the result is actually
smaller, and the duration still matches — so a failed encode leaves the original
untouched. Masters are pruned only after the file beside them already conforms,
never in the same breath as an encode that might still fail.

CLI:
    python3 scripts/podcast/downsize_audio.py                     # every book, dry run
    python3 scripts/podcast/downsize_audio.py --slug <book-slug>  # one book, dry run
    python3 scripts/podcast/downsize_audio.py --slug <s> --apply  # re-encode + prune
    python3 scripts/podcast/downsize_audio.py --keep-masters ...  # leave `Audio/` alone

`publish_to_listener` calls `normalise()` on every book it publishes, so the
profile is the pipeline's standard rather than something anyone has to remember.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _listener_media import EPISODES_DIR, MASTERS_DIR  # noqa: E402
from _paths import CONTENT_ROOT, REPO_ROOT  # noqa: E402

AUDIO_EXT = {".mp3", ".m4a"}

# The spoken-word profile. See the module docstring for why each part is chosen.
DEFAULT_FLOOR_KBPS = 48
SPOKEN_CHANNELS = 1
SPOKEN_SAMPLE_RATE = 22050

# Already-efficient files are left alone REGARDLESS of the floor. 17 of this
# library's books ship at 63 kbps stereo; re-encoding those to 48 kbps mono
# would save about a quarter of their bytes and cost a whole lossy generation on
# audio that is already small. R2 pressure comes from the 127-256 kbps books, so
# spending quality where there is no pressure is a bad trade at any ratio.
KEEP_BELOW_KBPS = 64

# Small files are left alone whatever their bitrate. Every audiobook opens with a
# ~0.1 MB credits clip encoded at 64 kbps; re-encoding all 17 of them would save
# under a megabyte in total while filling the plan with work no one wants to read
# or verify. A saving worth a lossy generation is a saving worth noticing.
MIN_SIZE_BYTES = 2 * 1024 * 1024

# A floor under the floor. Below 32 kbps mono, speech starts to acquire the
# metallic artefacts that make a long lecture tiring rather than merely thinner,
# so the flag stops being an operator choice and becomes a mistake.
ABSOLUTE_FLOOR_KBPS = 32

# Read-along cues are ABSOLUTE SECONDS into the episode file
# (`book/narration/manifest.json`), so an encode that shifts the timeline
# silently desynchronises every highlighted sentence in the book. Encoder delay
# and padding move the duration by a few milliseconds at most; a quarter second
# is far outside that and comfortably inside a cue.
DURATION_TOLERANCE_S = 0.25

# Below this margin a re-encode is not worth the quality loss: a file at 140 kbps
# would save ~8% and lose a generation. Only meaningfully-larger files qualify.
MIN_SAVING_RATIO = 0.15


def _mb(n: int) -> str:
    return f"{n / (1024 * 1024):.1f} MB"


def _rel(path: Path) -> str:
    """A readable path for a log line, and never a reason to abort.

    `relative_to` RAISES for anything outside the repo. Every call here sits
    inside a destructive routine, so a display line that can throw is a display
    line that can leave a prune half-done — cosmetics must not be able to do that.
    """
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def probe_bitrate(path: Path) -> int | None:
    """Bits per second from ffprobe, or None if it cannot be read."""
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=bit_rate",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    raw = r.stdout.strip()
    return int(raw) if r.returncode == 0 and raw.isdigit() else None


def probe_duration(path: Path) -> float | None:
    """Seconds from ffprobe, or None if it cannot be read."""
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def shippable_audio(book_dir: Path) -> list[Path]:
    """The files `_listener_media.collect_audio` would actually upload.

    Everything under `m4a/Episodes/` EXCEPT the `Audio/` masters. Mirrors that
    module's rule rather than restating it loosely — the masters exclusion is the
    whole reason a re-encode here is safe.
    """
    root = book_dir / "m4a" / EPISODES_DIR
    if not root.is_dir():
        return []
    return sorted(
        p
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in AUDIO_EXT and MASTERS_DIR not in p.relative_to(root).parts
    )


def master_dirs(book_dir: Path) -> list[Path]:
    """Every `Audio/` masters folder under this book's `m4a/`.

    Two locations, both real. A book above the session threshold keeps masters at
    `m4a/Episodes/Audio/`; a book below it is deliberately FLAT and keeps them at
    `m4a/Audio/`. Looking in only one place is how a flat book quietly keeps a
    gigabyte nobody accounts for.
    """
    root = book_dir / "m4a"
    if not root.is_dir():
        return []
    return sorted(d for d in root.rglob(MASTERS_DIR) if d.is_dir())


def prune_masters(book_dir: Path, *, apply: bool, log=print) -> tuple[int, int]:
    """Delete the masters this book no longer keeps. Returns (files, bytes).

    Only called once the shipping files already conform, never beside an encode
    that could still fail. `source/` is never reached: this walks `m4a/` only, and
    matches a directory named exactly `Audio`.
    """
    files = 0
    freed = 0
    for masters in master_dirs(book_dir):
        here = [f for f in masters.rglob("*") if f.is_file()]
        if not here:
            continue
        size = sum(f.stat().st_size for f in here)
        files += len(here)
        freed += size
        log(f"  [masters] {len(here)} file(s), {_mb(size)} in {_rel(masters)}")
        if apply:
            shutil.rmtree(masters)
    return files, freed


def reencode(path: Path, floor_kbps: int) -> tuple[bool, str]:
    """Re-encode in place via a temp file. Returns (changed, message).

    The container is deliberately PRESERVED — mp3 stays mp3, m4a stays m4a.
    An asset's R2 key and its `media_asset` primary key both carry the
    extension, so changing the container would orphan the old object and
    rewrite rows in a table whose contract is that a row means "this file is on
    disk". The saving is in the profile, not in the container.

    Nothing replaces the original until the result is smaller AND the same
    length, because read-along cues index into this file by absolute second.
    """
    tmp = path.with_name(f".{path.name}.downsize.tmp{path.suffix}")
    codec = "libmp3lame" if path.suffix.lower() == ".mp3" else "aac"
    r = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-i",
            str(path),
            "-vn",
            "-ac",
            str(SPOKEN_CHANNELS),
            "-ar",
            str(SPOKEN_SAMPLE_RATE),
            "-c:a",
            codec,
            "-b:a",
            f"{floor_kbps}k",
            str(tmp),
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or not tmp.exists():
        tmp.unlink(missing_ok=True)
        return False, f"ffmpeg failed: {r.stderr.strip()[:160]}"
    before, after = path.stat().st_size, tmp.stat().st_size
    if after >= before:
        tmp.unlink(missing_ok=True)
        return False, f"re-encode was not smaller ({_mb(after)} vs {_mb(before)}) — kept original"

    was, now = probe_duration(path), probe_duration(tmp)
    if was is None or now is None:
        tmp.unlink(missing_ok=True)
        return False, "could not read duration before/after — kept original"
    drift = abs(now - was)
    if drift > DURATION_TOLERANCE_S:
        tmp.unlink(missing_ok=True)
        return False, f"duration moved {drift:.2f}s ({was:.2f}s -> {now:.2f}s) — kept original"

    tmp.replace(path)
    return True, f"{_mb(before)} -> {_mb(after)} (saved {_mb(before - after)}, drift {drift:.3f}s)"


def book_dirs(slug: str | None) -> list[Path]:
    found = sorted(
        d
        for bucket in CONTENT_ROOT.iterdir()
        if bucket.is_dir() and not bucket.name.startswith("_")
        for d in bucket.iterdir()
        if d.is_dir() and not d.name.startswith("_")
    )
    return [d for d in found if d.name == slug] if slug else found


def plan_for(book_dir: Path, floor_bps: int, log=print) -> tuple[list[tuple[Path, int, int]], int]:
    """Which of this book's files are worth re-encoding, and how many were not."""
    planned: list[tuple[Path, int, int]] = []
    skipped = 0
    for path in shippable_audio(book_dir):
        bitrate = probe_bitrate(path)
        if bitrate is None:
            log(f"  ?? unreadable bitrate: {_rel(path)}")
            continue
        size = path.stat().st_size
        if size < MIN_SIZE_BYTES or bitrate <= max(floor_bps, KEEP_BELOW_KBPS * 1000):
            skipped += 1
            continue
        projected = int(size * floor_bps / bitrate)
        if (size - projected) / size < MIN_SAVING_RATIO:
            skipped += 1
            continue
        planned.append((path, size, projected))
    return planned, skipped


def normalise(
    book_dir: Path,
    *,
    floor_kbps: int = DEFAULT_FLOOR_KBPS,
    apply: bool = False,
    keep_masters: bool = False,
    log=print,
) -> dict:
    """Bring ONE book to the profile, and drop what it no longer keeps.

    The pipeline's entry point as well as the CLI's — `publish_to_listener` calls
    this before it reads a book, so anything published is at the profile whether
    or not a person remembered to run the tool.

    Masters are pruned only when every planned encode in this book SUCCEEDED. A
    file still above the profile means its master is the only copy of the better
    audio, and a sweep that deleted it because it happened to reach that line
    would throw away the one thing a retry could use.
    """
    planned, skipped = plan_for(book_dir, floor_kbps * 1000, log=log)
    report = {
        "slug": book_dir.name,
        "planned": len(planned),
        "skipped": skipped,
        "encoded": 0,
        "before": sum(size for _p, size, _j in planned),
        "projected": sum(j for _p, _s, j in planned),
        "masters": 0,
        "freed": 0,
    }

    for path, size, projected in planned:
        log(f"  {_rel(path)}")
        log(f"      {_mb(size)} -> ~{_mb(projected)}")

    if apply and planned:
        for path, _size, _projected in planned:
            ok, msg = reencode(path, floor_kbps)
            log(f"  [{'ok' if ok else 'SKIPPED'}] {_rel(path)}: {msg}")
            report["encoded"] += int(ok)

    if keep_masters:
        return report
    # A DRY RUN must show every deletion it would make. Judging the hold on
    # `encoded`, which is always zero when nothing ran, made the preview claim
    # five books would keep masters that `--apply` then deleted — understating a
    # destructive step, which is the one direction a preview must never err in.
    if apply and report["encoded"] < report["planned"]:
        if master_dirs(book_dir):
            log(f"  [held] {book_dir.name}: not every file reached the profile, masters kept")
        return report

    files, freed = prune_masters(book_dir, apply=apply, log=log)
    report["masters"] = files
    report["freed"] = freed
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", help="Only this book (default: every book).")
    ap.add_argument(
        "--floor-kbps",
        type=int,
        default=DEFAULT_FLOOR_KBPS,
        help=(
            f"Target/floor bitrate in kbps (default {DEFAULT_FLOOR_KBPS}, the spoken-word "
            f"profile; hard minimum {ABSOLUTE_FLOOR_KBPS}). Never encodes UP."
        ),
    )
    ap.add_argument("--apply", action="store_true", help="Actually re-encode. Without it, dry run.")
    ap.add_argument(
        "--keep-masters",
        action="store_true",
        help="Leave `Audio/` in place. The library keeps ONE set of audio by default.",
    )
    args = ap.parse_args()

    if args.floor_kbps < ABSOLUTE_FLOOR_KBPS:
        print(
            f"downsize_audio: --floor-kbps {args.floor_kbps} is below the {ABSOLUTE_FLOOR_KBPS} kbps "
            "absolute floor; speech acquires audible artefacts under it.",
            file=sys.stderr,
        )
        return 2

    targets = book_dirs(args.slug)
    if not targets:
        print(f"downsize_audio: no book found for slug {args.slug!r}", file=sys.stderr)
        return 2

    totals = {"planned": 0, "encoded": 0, "skipped": 0, "before": 0, "projected": 0, "masters": 0, "freed": 0}
    for book_dir in targets:
        head_shown = False

        def log(message: str, _book=book_dir) -> None:
            nonlocal head_shown
            if not head_shown:
                print(f"\n{_book.name}")
                head_shown = True
            print(message)

        report = normalise(
            book_dir,
            floor_kbps=args.floor_kbps,
            apply=args.apply,
            keep_masters=args.keep_masters,
            log=log,
        )
        for field in totals:
            totals[field] += report[field]

    print(
        f"\n{totals['planned']} file(s) above {args.floor_kbps} kbps, "
        f"{totals['skipped']} already at/near the floor and left alone."
    )
    if totals["planned"]:
        print(
            f"Audio: {_mb(totals['before'])} -> ~{_mb(totals['projected'])} "
            f"(saving ~{_mb(totals['before'] - totals['projected'])})"
        )
    if totals["masters"]:
        verb = "deleted" if args.apply else "would be deleted"
        print(f"Masters: {totals['masters']} file(s) {verb}, {_mb(totals['freed'])} freed")

    if not args.apply:
        print("\nDRY RUN — nothing was written. Re-run with --apply.")
        return 0

    if totals["encoded"]:
        slug = targets[0].name if len(targets) == 1 else "<slug>"
        # Uploading alone would do NOTHING here. `upload_listener_media` pushes
        # rows where `uploaded_at IS NULL`, and these rows are still stamped from
        # the previous encode. It is `publish_to_listener` that notices the file's
        # sha256 changed and clears the stamp, which is what makes the upload
        # re-push the new bytes. Local and remote are separate stores and both
        # need the pair, or the two ends hold different audio.
        print("\nNext, so both ends hold this same audio:")
        print(f"  python3 scripts/podcast/publish_to_listener.py {slug}")
        print(f"  python3 scripts/podcast/upload_listener_media.py {slug}")
        print(f"  python3 scripts/podcast/publish_to_listener.py {slug} --remote")
        print(f"  python3 scripts/podcast/upload_listener_media.py {slug} --remote")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
