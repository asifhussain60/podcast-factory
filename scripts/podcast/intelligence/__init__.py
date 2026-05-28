"""Intelligence layer — public API for the podcast pipeline.

B1: extractor — claude -p per chapter → scratch JSONL
B2: librarian — scratch JSONL → knowledge DB (dedup / conflict)
B3: augmenter — DB-backed doctrine injection into episode text
B0: kashkole_ingest_knowledge — Kashkole corpus → doctrine atoms
"""
from .extractor import extract_chapter, extract_atoms_for_book, ExtractionSummary
from .librarian import merge_into_library, MergeReport
from .augmenter import augment_episode_text, fetch_atoms_for_tags

__all__ = [
    "extract_chapter",
    "extract_atoms_for_book",
    "ExtractionSummary",
    "merge_into_library",
    "MergeReport",
    "augment_episode_text",
    "fetch_atoms_for_tags",
]
