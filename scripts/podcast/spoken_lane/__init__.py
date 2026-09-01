"""The spoken lane: a recording IS the chapter, and no podcast is generated.

Two content profiles run this lane today and they share everything downstream of
ingest — the six `LANE_STEPS`, the Studio track, the compose-articulate guard and
the publish gates — because the lane is selected by `pipeline_mode:
"sessions_lane"` in a book's own state file, never by its bucket:

    islamic_session   Asif's delivered lectures      -> content/Sessions/<slug>/
    audiobook         published books read aloud     -> content/Audiobook/<slug>/

WHY THIS PACKAGE EXISTS. Until 2026-09-01 the lane had no home of its own: it was
defined by `sessions/ingest.py`, which reads `KSessions.sql`, a hardcoded series
registry and a Google Drive mount — none of which an audiobook has. A second
source could only join the lane by copying that file, which would have left the
lane defined by whichever ingest you happened to copy. Asif's correction was
exact: the spoken track must not need a KSESSIONS ingest.

So the split is by JOB, not by source:

    spoken_lane/scaffold.py   the lane itself — state, phases, skeleton, metadata.
                              Source-agnostic. Every adapter calls it.
    spoken_lane/audiobook.py  one adapter: a container plus a chapter manifest.
    sessions/ingest.py        the other adapter: KSESSIONS. Unchanged in what it
                              reads; it now hands its parse to the scaffolder.

Adding a third spoken source is a new adapter and nothing else.
"""
