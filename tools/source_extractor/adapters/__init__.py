"""Source adapters — one per upstream SQL database.

Each adapter implements SourceAdapter (base.py) and provides:
- Database schema knowledge (which tables, which columns, which joins)
- Filesystem prefix computation (shelf/book ordering)
- Source-language declaration (drives the pipeline's translation phase)
- Optional inline-citation cleanup (e.g., KAHSKOLE Quran widgets via HQAyats)

Stages (stages/) call adapter methods generically — they never branch on
adapter identity.
"""
from .base import SourceAdapter, BookIds, BookMeta, Section, AdapterLabels
from .kashkole import KashkoleAdapter
from .ksessions import KsessionsAdapter


def get_adapter(name: str) -> SourceAdapter:
    """Factory: name → adapter instance."""
    name = name.lower()
    if name in ("kashkole", "kahskole"):
        return KashkoleAdapter()
    if name == "ksessions":
        return KsessionsAdapter()
    raise ValueError(f"Unknown adapter: {name!r}. Known: kashkole, ksessions.")


__all__ = [
    "SourceAdapter",
    "BookIds",
    "BookMeta",
    "Section",
    "AdapterLabels",
    "KashkoleAdapter",
    "KsessionsAdapter",
    "get_adapter",
]
