"""ReviewAdapter — language-specific review logic.

A ReviewAdapter walks the text of one section and emits Annotation records.
Stages (review.py, seal.py) are generic; they call adapter methods uniformly.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass(frozen=True)
class Annotation:
    """One reviewer annotation about a span of section text.

    `original_excerpt` is a verbatim slice of the raw-extract.md content
    (small — a sentence or phrase). `annotation` is the proposed change or
    note. `rationale` explains the reasoning to the human reviewer.
    `source` indicates which evidence base supports the annotation
    (training | hqayats | glossary | self).
    """
    section_id: int
    section_position: int
    type: str            # "typo" | "quran-uncited" | "glossary" | "sentence-completion" | "needs-human-review"
    confidence: str      # "high" | "medium" | "low"
    original_excerpt: str
    annotation: str
    rationale: str
    source: str

    def to_dict(self) -> dict:
        return asdict(self)


class ReviewAdapter(ABC):
    """Abstract base for language-specific reviewers."""

    @property
    @abstractmethod
    def language(self) -> str:
        """BCP-47 tag of the section text language. e.g., 'ur' | 'en'."""

    @abstractmethod
    def review_section(
        self,
        section_text: str,
        section_id: int,
        section_position: int,
        label: str,
        glossary: dict,
        quran_corpus,
    ) -> list[Annotation]:
        """Walk one section's text. Return list of Annotation."""
