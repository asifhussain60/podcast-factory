"""KSESSIONS adapter — stub.

Source: mostly English teaching content. Hierarchy: Group → Category → Session
→ SessionTranscript. Different schema from KAHSKOLE; not yet implemented.

When implementing, the SQL queries below (lifted from the Phase 1
_workspace/kashkole-ksessions/scripts/extract.py KSESSIONS sketch) are a
starting point — verify against the live KSESSIONS schema before trusting them.
"""
from __future__ import annotations

from .base import (
    SourceAdapter,
    BookIds,
    BookMeta,
    Section,
    AdapterLabels,
)


# Reference SQL templates (NOT YET VERIFIED — do not enable until checked):
#
#   resolve_book / group:
#     SELECT GroupID AS id, GroupName AS name, GroupID AS sort_key
#     FROM Groups WHERE GroupID = <shelf_id>
#
#   resolve_book / category:
#     SELECT CategoryID AS id, CategoryName AS name, SortOrder AS book_sort_key
#     FROM Categories WHERE CategoryID = <book_id>
#
#   get_book_sections / sessions:
#     SELECT s.Sequence AS raw_sort, s.SessionID AS id, s.SessionName AS name,
#            s.Description AS description, s.SessionDate AS session_date,
#            s.IsActive AS is_active, st.Transcript AS html
#     FROM Sessions s
#     LEFT JOIN SessionTranscripts st ON st.SessionID = s.SessionID
#     WHERE s.GroupID = <shelf_id> AND s.CategoryID = <book_id>
#     ORDER BY s.Sequence


class KsessionsAdapter(SourceAdapter):
    source_name = "ksessions"
    source_language = "en"
    labels = AdapterLabels(
        shelf_label="group",
        book_label="category",
        section_label="session",
    )

    def resolve_book(self, ids: BookIds) -> BookMeta:
        raise NotImplementedError(
            "KsessionsAdapter is scaffolded but not implemented. "
            "Verify SQL templates against live KSESSIONS schema before enabling."
        )

    def get_book_sections(self, ids: BookIds) -> list[Section]:
        raise NotImplementedError(
            "KsessionsAdapter is scaffolded but not implemented. "
            "Verify SQL templates against live KSESSIONS schema before enabling."
        )

    # Note: KSESSIONS may not have an in-DB Quran corpus or curated citations.
    # The base-class no-op defaults for get_quran_corpus,
    # cleanup_inline_citations, get_section_curated_citations, and
    # render_curated_citation_footer are correct for now.
