# Claude Code Evaluation Prompt — Chapter Density Audit + slow-pod

Paste the block below verbatim into Claude Code.

---

```
I need you to evaluate two deliverables that were built in Cowork and verify they meet their requirements before I integrate them into the pipeline.

## Deliverable 1 — Chapter Density Auditor

**Script:** `scripts/podcast/chapter_density_audit.py`
**Standard doc:** `docs/standards/chapter-density.md`

### What it does
Measures how many concept-level H2 sections each rendered chapter `.txt` file
contains. The target is ≤3 concepts per episode. With a target of 2–3 concepts,
the current 35 chapters across the pipeline fail 26 times — the worst offenders
carry 14–18 concepts and need to be split into 4–6 sub-episodes.

### Evaluate these things

1. Run the auditor and confirm the summary line matches:
   ```
   python3 scripts/podcast/chapter_density_audit.py
   ```
   Expected: "35 chapters total | ✅ 8 PASS | ⚠️ 1 WARN | ❌ 26 FAIL"

2. Run with `--remediate` on the master-and-the-disciple book:
   ```
   python3 scripts/podcast/chapter_density_audit.py \
     --slug the-master-and-the-disciple --remediate
   ```
   Confirm: 5 chapters, all FAIL, each with a split plan showing 4–5 sub-episodes.

3. Run with `--json` and verify the output is valid JSON with the expected
   fields: `book_slug`, `bucket`, `chapter_file`, `concept_count`, `status`,
   `suggested_splits`.

4. Read `docs/standards/chapter-density.md` and evaluate:
   - Does the findings table match the actual audit output?
   - Is the remediation plan actionable within the podcast-factory pipeline
     (phases 0d → preflight_chapter → per-chapter)?
   - Is the proposed smoke-gate addition to `scripts/podcast/phases/preflight_chapter.py`
     safe to add without breaking the existing C2 gate?

5. **One specific thing to check:** the algorithm classifies sections titled
   "Where this episode opens", "What this episode lands" etc. as *frame* sections
   and excludes them from the concept count. Verify this is correct by reading
   `content/Islamic/the-master-and-the-disciple/chapters/ch01a-true-sources-of-knowledge.txt`
   and counting the H2 headings manually. The auditor should report 11 concepts
   (not 13 total H2s, because 2 are frames).

---

## Deliverable 2 — slow-pod.py

**Script:** `scripts/podcast/slow-pod.py`

### What it does
Post-processes downloaded NotebookLM .m4a files into slower .mp3s using
ffmpeg's `atempo` filter (pitch-preserving time-stretch). This is needed
because NotebookLM hosts speak too fast and playback speed controls only work
inside their player, not on downloaded files.

### Evaluate these things

1. Confirm ffmpeg is on PATH, then run a dry-run:
   ```
   python3 scripts/podcast/slow-pod.py \
     --input /path/to/any.m4a --dry-run
   ```
   The command printed must use `atempo`, never `asetrate`. asetrate changes
   pitch and is an automatic reject.

2. Generate a 3-second test tone and process it end-to-end:
   ```
   ffmpeg -y -f lavfi -i "sine=frequency=440:duration=3" -c:a aac /tmp/test.m4a
   python3 scripts/podcast/slow-pod.py --input /tmp/test.m4a --output /tmp/slow-out
   ```
   Then verify:
   - Output file `/tmp/slow-out/test-slow85.mp3` exists
   - `ffprobe` reports `format_name=mp3`
   - Duration ≈ 3.0 / 0.85 = 3.529s ± 2% tolerance
   - Output bitrate is 192k

3. Verify idempotency: run the same command again without `--force`. It must
   print a SKIP line, not reprocess.

4. Verify `--tempo 1.5` exits with code 2 and a clear error message.

5. Check the FR/NFR requirements:
   - FR-1: `--tempo` default=0.85, range 0.5–1.0; sub-0.5 uses chained atempo
   - FR-2: `--input` accepts file OR directory; `--recursive` for subdirs
   - FR-3: `--bitrate` default 192k
   - FR-4: output naming `<stem>-slow<pct>.mp3`
   - FR-5: idempotency + explicit skip logging
   - FR-6: `-map_metadata 0` in ffmpeg command
   - FR-7: `--dry-run` prints commands, executes nothing
   - NFR-1: clear ffmpeg-not-found error with OS-specific install hint
   - NFR-2: zero pip dependencies (stdlib only)
   - NFR-3: kebab-case filename `slow-pod.py`, single file, importable core
   - NFR-4: exit 0 success / 1 partial batch fail / 2 fatal

6. Read the module docstring and confirm the usage examples are accurate.

---

## If you find issues

For the density auditor: the most likely failure point is the frame-section
regex. Check it against the actual chapter headings.

For slow-pod: the most likely failure point is the atempo chain for tempo < 0.5.
Verify `build_atempo_chain(0.25)` returns two chained filters whose product ≈ 0.25.

Report a pass/fail verdict per requirement and fix any FAILs before declaring done.
```
