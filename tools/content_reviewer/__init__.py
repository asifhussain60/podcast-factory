"""content_reviewer — annotation-layer reviewer for source-extractor bundles.

Sibling to tools/source_extractor. Reads a finalized bundle, walks every section
of raw-extract.md, and emits an annotation layer at
_system/source/text/editorial-{review.md,annotations.jsonl}. Does NOT modify
raw-extract.md (the source of truth must stay byte-faithful).

After review, `seal` flips bundle.yml.stage from "finalized" to "reviewed" and
flags chapters with needs_human_review.
"""
