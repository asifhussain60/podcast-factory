# Book series-config.yaml setup standard

**Gold-standard reference:** `content/Islamic/the-master-and-the-disciple/_system/series-config.yaml`.

`framework.md` and `docs/standards/book-articulation.md` already name that file
as the reference edition for REQ-BA conformance on the faithful Islamic-
scholarly route — it is the most iterated config in the repo, and every knob
in it carries an inline comment explaining the incident or decision that set
it. When a book has no `series-config.yaml` at all (compose silently falls
back to profile defaults — see `_pipeline_flags._default_knobs`) or one
written before this standard existed, mirror that file's resolved values
rather than re-deriving each knob from first principles.

## Copy as-is (unless the source genuinely disagrees)

- `content_profile: islamic_scholarly` — any Ismaili/Islamic scholarly treatise.
- `book_augmentation: none` — a faithful edition adds nothing beyond the
  source. Only flip to `source_only` when the book explicitly wants
  source-grounded editorial asides; that is a real product decision, ask
  before changing it, not a default to assume.
- `book_voice: faithful`.
- `enable_video: false` / `video_style: none` — unless the book has a
  declared video style already in play.
- `book_pipeline_v2: true`.

## `skip_podcast` — opt a single book out of the episode lane

`skip_podcast: true` skips the per-chapter NotebookLM podcast episode loop
for THIS book only (`_content_profile.skip_podcast`, checked by
`phases/chapter_driver.py`) — no episodes, no upload bundle, no audio
render. Chapters, slide decks, the reading edition, and the read-aloud
narration are unaffected; only the two-host conversation is skipped.

This is a genuinely different switch from `skip_per_chapter` in the
content-type registry (`_content_types.py`), which already exists for
`islamic_session`/`audiobook` — those skip OCR and phonetics too, because
the audio already exists and IS the deliverable. `skip_podcast` is for a
book that still needs OCR + phonetics (read-aloud narration still has to
pronounce Arabic terms correctly) but was never going to be a podcast in
the first place — an editorial choice, not a property of the source medium.
Setting it does NOT change the book's augmentation/voice defaults; it still
gets the normal reading-edition treatment for its profile.

Asif, 2026-09-17 (`isaf-al-talib`): "Not all books should have to go down
the podcast route." Defaults `false` — every existing book is unaffected.

## Never copy verbatim — these are properties of THIS book

- **`narrative_frame`** — a property of the SOURCE, never the template. See
  the decision rule below.
- `density_standard`, `slide_deck_mode`, `episode_planning_mode`,
  `audience_profile`, `conversation_style`, `length_tier`, `voice_cast` — all
  PODCAST episode-planning knobs, not reading-edition knobs. Setting these on
  a book whose episodes are already shipped risks re-triggering Phase 0d
  re-planning for no reason. Leave them unset on a backfill; they only belong
  in a NEW book's config, alongside its own podcast build.

## Deciding `narrative_frame` without asking

Read how the source opens, then apply the rule already locked in
`_narrative.py` / `_pipeline_flags.narrative_frame`:

- Author's own doxology/prayer, first-person "I thought to state each of
  their sayings..." statement of method, ADDRESSED to a reader or a named
  disciple — the address is the form → `first_person_author`.
- The author speaks as "I" but expounds rather than addresses: a delivered
  LECTURE becoming a book → `first_person_expository`. Same person, opposite
  answer on the second question. Choosing `first_person_author` here silences
  REQ-BA-125/126 and leaves the lecture hall on the page — which is what
  happened to both Sessions books before 2026-08-11.
- Anonymous transmission formula ("it has reached us", `بلغنا`) reporting a
  dialogue between named others, with neither party narrating → `transmitted_report`.
- A third-person scholarly editor narrates throughout, no chapter in any
  character's own voice → `external_narrator`.

Two questions, not one: **who narrates** (`person`) and **whether the narration
addresses anyone** (`addresses_reader`). Both are declared per frame in
`_narrative_frames.NARRATIVE_FRAMES`; a new frame must answer both, and a test
refuses one that does not.

Ask Asif only when the source genuinely mixes voices with no clear majority
— the way `degrees-of-excellence` did before its two third-person
introduction chapters were dropped entirely — since that is a real
interpretive call the pipeline cannot make for itself. A book that opens
in one voice and stays there for its whole extent is not that case.

## Prerequisite

`meta.yml` needs `series: {enable_book_branch: true}` or `book_driver.py`
refuses to run any of the five `0book-*` phases at all (its own explicit
refusal message names the fix).

## Backfilling a book that already shipped without a reading edition

Resuming the orchestrator on a `phase: done` book is a hard no-op —
`resume_dispatcher.py` prints "This book has already shipped. Nothing to
resume." and returns. Invoke `phases.book_driver._drive_book_branch(book_dir)`
directly instead: the same function the live pipeline calls at the finalize
halt, run standalone. It is non-blocking and idempotent per phase, matching
the repo's other backfill scripts (`_book_quran.py --slug`,
`normalize_spelling.py`).
