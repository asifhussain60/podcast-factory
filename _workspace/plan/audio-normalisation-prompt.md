# Prompt — run this on the Mac Studio

Copy everything below the line into a fresh Claude Code session in
`~/PROJECTS/podcast-factory` on the Mac Studio.

---

The podcast library's recordings are encoded five different ways, because each
book kept whatever its source happened to be. Five books still ship at 127–256
kbps stereo; the rest of the library is already at or below 64 kbps. I want one
spoken-word profile applied to those five, and I want localhost and the live site
holding the same bytes for every file when you are done.

**Work one book at a time.** Re-encode a book, verify it completely, get my
sign-off, push it to production, verify it there — and only then start the next
book. Do not batch the re-encodes and do not run ahead. Tick the boxes in
`_workspace/plan/audio-normalisation-checklist.md` as you pass each gate and
commit that file as you go; it is the run's memory if this session ends.

## The profile, and why it is not negotiable downward

48 kbps, mono, 22.05 kHz, container preserved. `scripts/podcast/downsize_audio.py`
is the only tool that applies it — do not hand-roll ffmpeg. It already refuses to
encode up, refuses to touch the `Audio/` masters or `source/`, promotes the
original into `Audio/` before overwriting anything, and rejects any encode whose
duration moves more than 0.25 s. That last guard matters more than it looks:
read-along cues are absolute seconds into the episode file, so a shifted timeline
would silently desynchronise every highlighted sentence in the book.

Measured here on Ayyuhal Walad episode 1: 129 kbps stereo → 51 kbps mono,
27.9 MB → 11.1 MB, duration drift 0.000 s.

## Before you start anything

1. `bash scripts/start-session.sh`, and confirm the working tree is clean.
   Another session may be working in this repo — never stage or revert a file you
   did not change.
2. `ffmpeg -version` and `ffprobe -version` both answer.
3. `python3 scripts/podcast/audio_parity.py --problems` — this compares the SHA-256
   of every recording on disk against what localhost and production each recorded.
   **The recordings are gitignored**, so this machine's copy arrived by some route
   git never saw, and this is the only thing that proves it is the same audio the
   site is serving. Expect `same=73  unpublished=277`. The 277 are the Dostoyevsky
   audiobooks, which are on disk but not published — leave them alone.
   **If any of the five target books reports anything but `same`, stop and tell me.**
   Re-encoding a file this machine holds a different version of would replace the
   live recording with a different one.
4. `python3 scripts/podcast/downsize_audio.py` with no arguments — a dry run over
   the whole library. It should plan 48 files across exactly five books, 1,012 MB
   → 378 MB. If the count differs, something changed since this was written; tell
   me rather than proceeding.

## The books, smallest first

`sharh-al-masail-ghulam-hussain` (5 files) → `ayyuhal-walad` (4) →
`degrees-of-excellence` (6) → `the-master-and-the-disciple` (20) →
`spiritual-ethos` (13).

Smallest first is deliberate — the first book is five files, so the first trip
through the whole gate sequence is cheap and proves the loop before the twenty-file
book.

## For each book, in order

**1. Confirm the starting state.**
`python3 scripts/podcast/audio_parity.py --slug <slug>` — every file `same`.

**2. Re-encode.**
`python3 scripts/podcast/downsize_audio.py --slug <slug>` first, read the plan,
then `--apply`. Read every line of the output. A file that reports `SKIPPED` was
left at its original encoding and names why; that is safe but it is not done, so
report it rather than moving on.

**3. Check read-along survived.** All five books have
`book/narration/manifest.json`, whose cues index into these files by absolute
second. For each chapter, confirm the recorded `duration_s` still matches the
file on disk and no cue ends after the recording does. The re-encode should have
drifted 0.000 s — if any chapter is off, stop.

**4. Update localhost.** Both commands, in this order:
`python3 scripts/podcast/publish_to_listener.py <slug>` then
`python3 scripts/podcast/upload_listener_media.py <slug>`.
The publish step is what makes the upload work at all: `upload_listener_media`
only pushes rows where `uploaded_at IS NULL`, and these rows are still stamped
from the previous encode. `publish_to_listener` notices the file's SHA-256
changed and clears the stamp. Uploading without publishing first does nothing and
looks like success.

**5. Stop and let me listen.** Tell me the book is ready on
`http://localhost:5273`. I will play an episode and tell you whether it still
sounds like the book. **Nothing goes to production before I say so** — this is a
firm rule in this repo, and a passing test is not a substitute for my ears.

**6. Update production.** The same two commands with `--remote` appended.
Note that `publish_to_listener` deliberately never writes `content_unit.status`
or `open_to_all`; visibility is not yours to change and nothing here should make
a book more or less visible than it already is.

**7. Prove the bytes are actually there.** Fetch an episode back from
`https://podcast-factory.safinaverse.com` and check the status is 200, the
`content-length` equals the new file size, and the content type is audio. A
`media_asset` row can exist with no object behind it, so the row is not evidence.
Then `python3 scripts/podcast/audio_parity.py --slug <slug>` — every file `same`
again, now at the new size.

**8. Confirm nothing else moved.** The book page still lists the same number of
episodes as before, and `cd listener && npm test` is green.

**9. Tick the boxes** in the checklist, commit with a message naming the book and
the bytes saved, and only then start the next book.

## When all five are done

- `python3 scripts/podcast/downsize_audio.py` reports nothing left above the floor.
- `python3 scripts/podcast/audio_parity.py --problems` reports no `MISMATCH`.
- Push once, at the end — this repo batches pushes to `develop` because GitHub
  Actions minutes are metered and every push starts a build.

## Things that will bite you

- **`npm run deploy` exits non-zero even when it worked.** It reads a zone
  endpoint the token is denied, after uploading. Read the `Uploaded` line, not the
  exit code.
- **`wrangler r2 bucket info` lags by hours** and will claim a full bucket is
  empty. Verify by fetching an object back, never by asking the bucket.
- **Every remote command must resolve to the `asifhussain60@gmail.com` account.**
  Check before any remote write.
- **Never read the Cloudflare token's value.** It is in the macOS keychain and the
  scripts read it themselves; existence checks only.
- **No code is being deployed here.** This is content only. Do not run
  `deploy_listener.sh` — it sweeps branches and pushes `main`, which is far more
  than this task asked for.
