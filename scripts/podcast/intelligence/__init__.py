"""Intelligence layer — public API for the podcast pipeline.

B1: extractor — claude -p per chapter → scratch JSONL
B2: librarian — scratch JSONL → knowledge DB (dedup / conflict)
B3: augmenter — DB-backed doctrine injection into episode text
B0: wisdom_ingest_knowledge — Kashkole corpus → doctrine atoms
"""

from .augmenter import augment_episode_text, fetch_atoms_for_tags
from .extractor import ExtractionSummary, extract_atoms_for_book, extract_chapter
from .librarian import MergeReport, merge_into_library

__all__ = [
    "extract_chapter",
    "extract_atoms_for_book",
    "ExtractionSummary",
    "merge_into_library",
    "MergeReport",
    "augment_episode_text",
    "fetch_atoms_for_tags",
]
