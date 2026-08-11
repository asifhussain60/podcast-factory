"""The delivered-lecture lane: KSESSIONS_DEV -> content/Sessions/<slug>/.

A sibling of `supplication/`, not a branch of the podcast phase machinery. The
audio already exists and is the lecture itself, so nothing here generates an
episode, a framing or a deck; the lane's whole job is to put Asif's own
recordings and the transcripts he wrote for them into the shape
`_listener_book.load_book` already understands.

Three steps, one module each:

    dump.py     read the UTF-16 SQL dump into Group / Session / Transcript
    convert.py  the authored HTML -> the book.md the reader renders
    ingest.py   lay a series down on disk, and the CLI

Deliberately NOT here: transcription (ensure_transcripts.py already asks the
publisher what it is about to ship and fills the gaps), and Arabic resolution
(_book_apparatus runs standalone over the composed book.md).
"""
