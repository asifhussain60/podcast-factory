# Spiritual Ethos — handoff prompt

Paste the block below into Claude Code on the Mac Studio, in the
`podcast-factory` repo. It is written to be read cold: it carries the decisions,
the state, and the four traps that already cost this book a night.

---

```
Continue processing the book `spiritual-ethos` through the podcast-factory
pipeline. Read this whole brief before running anything.

WHERE IT STANDS
Branch `Islamic/spiritual-ethos`, pushed. Pull it first:
  git fetch --all --prune && git checkout Islamic/spiritual-ethos && git pull
State: phase=0d, phase_status=pending, last_completed_phase=0ci. Everything
through the corpus gap analysis is done and committed. Chapter design is next
and must be run fresh.

WHAT THE BOOK IS
Three chapters plus both appendices of Reza Shah-Kazemi's *Justice and
Remembrance*, captured as 61 Kindle screenshots, OCR'd through Azure, and
assembled into five chapters: the three essays, then the First Sermon of Nahj
al-Balagha and the Letter of Ali (ع) to Malik al-Ashtar as chapters four and
five. Source of truth is `_system/source/text/raw-extract.md` (76,348 words).
`raw-extract.faithful.md` beside it is the pre-weave original — never delete it;
it is what a re-weave reads from.

WHAT IS ALREADY WOVEN IN
Asif taught this exact material as a 20-session series (KSessions group 7,
"Spiritual Ethos Of Ali"). All five chapters have his teaching merged INTO the
prose — one voice, no visible seam, and no duplicated content. Verified: the
woven book repeats LESS than the original (9.2 vs 13.7 repeated phrases per
1,000 words), no Quran reference lost, chapter five kept its direct address to
Malik. Provenance is in `_system/source/weave-provenance.json`. Do not re-weave;
it is done.

ASIF'S DECISIONS — these are settled, do not re-ask
- He is "Ali (ع)" everywhere, both the reading edition and the podcast sources.
  Do not substitute a roman "(as)".
- Episode count and lengths: the planner decides. `length_tier` is deliberately
  unset.
- `the-master-and-the-disciple` is the gold standard for book creation.
- Chapters 4 and 5 (the Sermon, the Letter) must keep their second-person direct
  address. If the articulation pass flattens them into exposition, AUTO-REVERT
  those two chapters to the faithful text through the Book Composer and say so.
- Stop at the FINALIZE halt. Do not run publish_to_library.py. Do not deploy.

WHAT TO RUN
  python3 scripts/podcast/orchestrate_book.py --resume spiritual-ethos --retry-phase 0d
Then drive it through the halt gates (0ci, 06a, 0f) with
`--resume spiritual-ethos`, naming each gate you clear and what it proposed, and
stop at finalize. The reading edition (book.md + PDF) is built AT the finalize
halt and does NOT need NotebookLM audio, so the run reaches it unattended.

FOUR TRAPS THAT ALREADY COST THIS BOOK A NIGHT
1. `--retry-phase X` re-runs the GATE, not the pass. The pass checkpoints per
   source chapter in `_system/source/text/_chunks/<phase>/sc-NNN.done`. To
   genuinely re-run 0d you must also delete `_chunks/0d/`, `chapters/ch*.txt`
   and `chapter-contracts/*.yml` — otherwise it reports an identical result and
   you will think it re-ran.
2. The watchdog prints "PRE-FLIGHT FAILURE (rc=1): working tree dirty" for ANY
   rc=1. It is usually wrong. Scroll UP in
   `_workspace/logs/orchestrator-spiritual-ethos.log` to the real Python
   traceback and fix that.
3. A dirty tree does block `--resume`. Commit the book's own artifacts
   (`git add -A content/Islamic/spiritual-ethos`), then
   `git restore plan-dashboard/src/data/dashboard-snapshot.json _learning/findings.jsonl`
   — both churn on every commit via hooks and will never stay clean.
4. Never kill `watch_orchestrator.sh` on a healthy run: SIGTERM reaches the live
   orchestrator. If you must stop a run, stop the watchdog FIRST, then the
   orchestrator, then remove `_system/watchdog.json`.

THE KNOWN OPEN ISSUE — read the new chapter-set report before continuing
The previous 0d design raised 1 P0 and 8 P1s. The P0 was trivial (a chapter 66
words under its declared band — that is a band-DECLARATION mismatch; correct the
band in the chapter contract). The P1s matter more: 74 shared 12-word passages
between `gazing-on-the-good` and `remembrance-as-polish-for-the-heart`, and 83
between `state-and-society` and `the-letter-to-malik-classes-and-conduct` — the
same content taught twice. Some overlap is structural, because Shah-Kazemi
quotes the Letter at length in his commentary AND the Letter is printed whole as
chapter five. But 74 passages between two chapters both derived from the
remembrance material looks like the segmentation genuinely duplicated content.
If the fresh design shows the same overlap, STOP and tell Asif rather than
re-running a third time. "No duplicate content" was his one hard rule.

MONITORING
Arm a 5-minute heartbeat (CronCreate `*/5 * * * *`). Each tick: check the
watchdog and orchestrator are alive AND that `_system/cost-ledger.jsonl` is
advancing — alive but frozen >15 minutes is a stall, not a quiet patch. Render
`python3 scripts/podcast/book_status_card.py spiritual-ethos` verbatim in a
fenced block. Times in EST, 12-hour. Real money only (Azure/Gemini); claude -p
is flat-rate and costs nothing. End the heartbeat at the finalize halt.

DONE MEANS
Chapters written, episode framings written, `book/book.md` articulated, and
`book/book.pdf` rendered — all reviewable at
`/studio/spiritual-ethos/compose` on the Astro Site (`cd plan-dashboard && npm run dev`).
Report chapter count, episode titles, book.md word count, whether the PDF
rendered, every halt gate you auto-confirmed, and the chapters 4/5
direct-address check.
```

---

## Not in git — recover these on the MacBook before you move on

- **`stash@{0}`** on the MacBook holds your Master and Disciple Composer edits
  (`composer-edits.json` + `book/book.md`). Git never pushes stashes.
  `git stash pop stash@{0}` there.
- **`kindle_images/`** is gitignored, so the 61 original screenshots stay on the
  MacBook. The tracked copies under `_system/source/images/` are byte-identical
  and are what the pipeline reads, so nothing is lost for processing.

## Pipeline fixes made for this book, already on the branch

Three pre-existing defects surfaced because this is the first book whose Arabic
arrives from an outside source rather than its own OCR. All fixed at the root:

1. `arabic_integrity.py` — the pre-0a baseline never included the source text,
   so 999 legitimately-woven Arabic runs read as model inventions.
2. `_authoring/_refine.py` — 0b was told to preserve Arabic *transliteration*
   and never *script*; it silently dropped twelve runs.
3. `_authoring/_refine.py` — the `⟪ar:…⟫` marker was unexplained, so the pass
   read it as an instruction to romanize.

Arabic integrity now passes clean: zero drops, zero inventions, zero vowel drift.
