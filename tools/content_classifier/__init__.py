"""content_classifier — read-only KAHSKOLE/KSESSIONS taxonomy analyzer.

Builds a proposal document at _workspace/plan/wisdom-taxonomy-r*-proposal.md
listing dedup candidates and chapter-retitle proposals. Does NOT modify any
bundle, the SQL source, or bundle.yml metadata. Output is purely advisory.

The byte-faithful invariant of the source-extractor bundles is preserved.
"""
