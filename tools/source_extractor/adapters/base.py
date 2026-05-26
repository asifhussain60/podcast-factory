"""SourceAdapter — the seam between database-specific schema knowledge
(this adapter) and pipeline-generic stages (in stages/).

Each upstream SQL database (KAHSKOLE, KSESSIONS, ...) ships one adapter.
Stages call adapter methods generically; they never branch on adapter identity.

Required methods describe the source's structure (a 2-level hierarchy of
shelf → book → sections). Optional hooks let an adapter inject source-specific
cleanup (e.g., KAHSKOLE's HQAyats Quran widget replacement) without polluting
the stages.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass(frozen=True)
class BookIds:
    """Unique identifier for one book within a source DB.

    Both keys are ints; meaning depends on adapter:
      KAHSKOLE: shelf_id=BinderID, book_id=ChapterID
      KSESSIONS: shelf_id=GroupID, book_id=CategoryID
    """
    shelf_id: int
    book_id: int


@dataclass(frozen=True)
class AdapterLabels:
    """Human-readable level names for the source's hierarchy."""
    shelf_label: str   # e.g., "binder" | "group"
    book_label: str    # e.g., "chapter" | "category"
    section_label: str # e.g., "topic" | "session"


@dataclass
class Section:
    """One section within a book (topic, session, etc.)."""
    position: int           # 1-based position within book
    id: int                 # source DB id
    raw_sort: int           # original sort key in DB
    label: str              # display name (may be in source language)
    html: Optional[str]     # raw HTML payload — None for empty/image-only sections
    extras: dict = field(default_factory=dict)  # adapter-specific (name_en, date, ...)


@dataclass
class BookMeta:
    """Resolved book metadata + filesystem placement."""
    source_name: str        # "kashkole" | "ksessions"
    source_language: str    # "ur" | "en"
    shelf_id: int
    shelf_name: str
    shelf_sort_key: int
    shelf_prefix: int       # 1-based filesystem prefix (ordering of shelves)
    shelf_slug: str
    book_id: int
    book_name: str
    book_sort_key: int
    book_prefix: int        # 1-based filesystem prefix within shelf
    book_slug: str


class QuranCorpus(Protocol):
    """Minimal interface for adapters that expose a Quran lookup table."""
    def get(self, surah: int, ayat: int) -> Optional[dict]: ...
    def get_range(self, surah: int, start: int, end: int) -> list[dict]: ...


class SourceAdapter(ABC):
    """Abstract base class. Concrete adapters implement schema-specific logic."""

    # ---- Required: identity ------------------------------------------------

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Stable lowercase id used in filesystem paths and meta.yml. e.g. 'kashkole'."""

    @property
    @abstractmethod
    def source_language(self) -> str:
        """BCP-47 language tag of the source text. e.g. 'ur', 'en'.

        Drives the podcast pipeline's translation phase (skip when 'en')."""

    @property
    @abstractmethod
    def labels(self) -> AdapterLabels:
        """Human-readable level names for the shelf/book/section hierarchy."""

    # ---- Required: resolve a book ------------------------------------------

    @abstractmethod
    def resolve_book(self, ids: BookIds) -> BookMeta:
        """Look up shelf + book metadata, compute filesystem prefixes + slugs."""

    @abstractmethod
    def get_book_sections(self, ids: BookIds) -> list[Section]:
        """Return ordered list of sections within the book. Empty sections
        (image-only, no transcript) are still included with html=None so
        meta can record them."""

    # ---- Optional hooks (defaults: no-op) ----------------------------------

    def get_quran_corpus(self) -> Optional[QuranCorpus]:
        """Return an in-database Quran corpus if the source has one
        (e.g., KAHSKOLE.HQAyats). Returns None when the source does not."""
        return None

    def cleanup_inline_citations(
        self, md: str, corpus: Optional[QuranCorpus]
    ) -> tuple[str, list[dict]]:
        """Replace adapter-specific inline citation widgets (KAHSKOLE Quran
        tables in flattened markdown) with clean blockquotes sourced from the
        adapter's corpus.

        Returns (rewritten_md, replacement_records). Default: no-op."""
        return md, []

    def get_section_curated_citations(self, section_id: int) -> list[dict]:
        """Return adapter-curated citation references for a section
        (e.g., KAHSKOLE.TopicAyats per Topic). Default: empty list."""
        return []

    def render_curated_citation_footer(
        self,
        section_body_md: str,
        refs: list[dict],
        corpus: Optional[QuranCorpus],
    ) -> str:
        """Render a 'verses referenced in this section' footer that dedups
        against citations already inlined in section_body_md.

        Default: empty string."""
        return ""
