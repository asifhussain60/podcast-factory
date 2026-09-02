# Audio normalisation — one book at a time

Bring every shippable recording to a single spoken-word encoding profile, and
leave localhost and the live site holding the *same bytes* for every file.

Work one book at a time. A book is not finished until every gate below it passes,
and the next book is not started until the previous one is finished. Tick the
boxes in this file as you go and commit it — it is the run's memory across
sessions and across machines.

## The profile

**48 kbps, mono, 22.05 kHz, container preserved. Approved by Asif on
2026-09-02** after an A/B listening test against the current 127 kbps stereo
encode — he could not tell the two apart, which is the only evidence that
settles "without losing quality". The profile is fixed; do not re-open it.

**One set of audio, and the masters go with it (Asif, 2026-09-02).** A book keeps
exactly ONE copy of each recording, at the profile. The `Audio/` masters — 3.74 GB
across six books — are deleted once the file beside them conforms. This is
irreversible by design: when the master is gone the 48 kbps file is the only copy
in existence, so the profile can never be revised upward for that recording.
Choosing the profile and discarding the masters were one decision, and it is made.

**It is now automatic.** `publish_to_listener` calls `normalise()` on every book it
publishes, so the profile is the pipeline's standard rather than an errand. Running
the tool by hand is still how this backlog gets cleared, but new books need nobody
to remember.

`scripts/podcast/downsize_audio.py` is the only tool that applies it. It never
encodes up, never touches `source/`, prunes masters only after every planned
encode in that book SUCCEEDED, and refuses any encode whose
duration moves more than 0.25 s (read-along cues are absolute seconds into the
file, so a shifted timeline would silently desynchronise every highlighted
sentence). Files already at or below 64 kbps, and files under 2 MB, are left
alone deliberately — see the module docstring for why.

Measured on Ayyuhal Walad episode 1: 129 kbps stereo → 51 kbps mono,
27.9 MB → 11.1 MB (−60%), duration drift **0.000 s**. That episode's clip is
what the listening test used.

## The books, smallest first

| # | Book | Files | Now | After | Saves | Read-along |
|---|---|---|---|---|---|---|
| 1 | `sharh-al-masail-ghulam-hussain` | 5 | 115 MB | 43 MB | 72 MB | yes |
| 2 | `ayyuhal-walad` | 4 | 135 MB | 50 MB | 85 MB | yes |
| 3 | `degrees-of-excellence` | 6 | 151 MB | 56 MB | 95 MB | yes |
| 4 | `the-master-and-the-disciple` | 20 | 286 MB | 107 MB | 179 MB | yes |
| 5 | `spiritual-ethos` | 13 | 325 MB | 121 MB | 204 MB | yes |
| | **Total** | **48** | **1,012 MB** | **378 MB** | **634 MB** | |

Plus **3,834 MB of masters** across six books (the five above and
`purification-of-the-heart`), deleted as each book passes. **Total reclaimed:
about 4.4 GB.**

Smallest first is deliberate: book 1 is five files, so the first pass through the
whole gate sequence costs little and proves the loop before the twenty-file book.

Every other book in the library is already at or below 64 kbps and is **not**
touched. Seventeen of them ship at 63 kbps stereo and have done for months;
re-encoding those would cost a lossy generation to save bytes there is no
pressure to save.

## Per-book gates

Repeat this block for each book. Every gate is a command whose output you read —
a zero exit code is not evidence.

- [ ] **G1 — disk matches production before you start.**
      Every shippable file's SHA-256 equals `media_asset.sha256` in the remote D1.
      A mismatch means this machine's copy is not the audio the site is serving;
      resolve that deliberately before re-encoding, or you will replace the live
      recording with a different one.
- [ ] **G2 — the masters are gone, and only because the encode worked.** A book
      that did not reach the profile on every file reports `[held]` and keeps its
      masters — that is correct, and it means the book is not done. Never delete a
      held master by hand to make the line go away.
- [ ] **G3 — every file re-encoded.** No line reports `SKIPPED`. Any skip names
      its reason: not smaller, or duration moved. Both keep the original, so a
      skip is safe — but it means that file is still at the old profile.
- [ ] **G4 — read-along still aligned.** For a book with
      `book/narration/manifest.json`: each chapter's recorded `duration_s` still
      matches the file on disk, and no cue ends after the recording does.
- [ ] **G5 — localhost updated.** `publish_to_listener` (which clears the upload
      stamp when a file's hash changes) then `upload_listener_media`. Local D1
      now carries the new sha256 and byte count.
- [ ] **G5b — hear it on localhost first.** Open the book on
      `http://localhost:5273`, play an episode, and confirm it sounds right to
      you. Nothing reaches the live site before this. Green gates prove the code
      did what it was told; only you can say the recording still sounds like the
      book.
- [ ] **G6 — production updated.** The same pair with `--remote`. Prod sha256 now
      equals local sha256 equals the file on disk, and `uploaded_at` is set.
- [ ] **G7 — the bytes are really there.** Fetch an episode back from
      `https://podcast-factory.safinaverse.com`: HTTP 200, `content-length`
      equal to the new size, an audio `content-type`. A `media_asset` row can
      exist with no object behind it.
- [ ] **G8 — listen to it.** Open the book on the live site, play an episode,
      scrub into the middle, and confirm the read-along highlight follows the
      voice. This is the gate no script can stand in for.
- [ ] **G9 — nothing else moved.** The book page still lists the same number of
      episodes, and `cd listener && npm test` is green.

## Progress

- [ ] 1. `sharh-al-masail-ghulam-hussain`
- [ ] 2. `ayyuhal-walad`
- [ ] 3. `degrees-of-excellence`
- [ ] 4. `the-master-and-the-disciple`
- [ ] 5. `spiritual-ethos`
- [ ] Final sweep — whole-library dry run reports nothing left above the floor,
      and no audio row differs between local and remote.

## Known divergence, to resolve on the way past

`purification-of-the-heart/audio/ep01.mp3` and `ep02.mp3` are the **only** two of
207 audio rows where localhost and production hold different content (local
564 MB / 512 MB, production 212 MB / 192 MB). Production has the re-encoded
files; this laptop's local store still has the originals. Re-publishing and
re-uploading that book locally settles it. Nothing else in the library diverges.
