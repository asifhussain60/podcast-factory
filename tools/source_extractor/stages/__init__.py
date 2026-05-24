"""Generic pipeline stages — work against any SourceAdapter.

Stage A (prepare):  adapter -> draft markdown + extracted images + vision-tasks.json
Stage B (vision):   in-conversation with Claude (no code here — see VISION.md)
Stage C (finalize): substitute image placeholders, run adapter cleanup, write final bundle.
"""
