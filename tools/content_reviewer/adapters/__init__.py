"""Review-adapter registry.

Each (source, language) combination has its own ReviewAdapter. The CLI picks
one based on the source name; adapters internally know their own language.
"""

from __future__ import annotations

from .base import ReviewAdapter
from .english import EnglishReviewAdapter
from .urdu import UrduReviewAdapter

_REGISTRY = {
    "wisdom": UrduReviewAdapter,
    "ksessions": EnglishReviewAdapter,
}


def get_review_adapter(source_name: str) -> ReviewAdapter:
    key = source_name.strip().lower()
    if key not in _REGISTRY:
        raise ValueError(f"No review adapter for source {source_name!r}. Known: {sorted(_REGISTRY)}")
    return _REGISTRY[key]()
