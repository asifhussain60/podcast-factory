"""KAHSKOLE adapter — Urdu scholarly content with embedded Arabic Quran widgets.

Hierarchy: Binder → BinderChapters → ChapterTopics → TopicDataUnicode (HTML).
Optional inline-citation cleanup: KAHSKOLE Quran widget tables get replaced
with clean blockquotes sourced from HQAyats (the in-DB Quran corpus).
Optional curated citations: TopicAyats per-topic linkages, rendered as a
'Verses referenced' footer that dedups against inline citations.
"""
from __future__ import annotations
import re
from typing import Optional

from ..db import query_json
from ..slugify import slugify_urdu
from .base import (
    SourceAdapter,
    BookIds,
    BookMeta,
    Section,
    AdapterLabels,
    QuranCorpus,
)


# KAHSKOLE database name (note: the DB is "KASHKOLE" but the adapter/folder
# uses "kashkole" — historical naming inconsistency, preserved for compatibility).
DB = "KASHKOLE"


# Match a flattened KAHSKOLE Quran widget block (post-html_to_md).
# Header line: "سورۃ <name> { N:N }" or "{ N:N-M }",
# middle: any number of lines (duplicate headers, Arabic ayat lines),
# terminator: a line starting with a digit followed by Urdu text (translation).
_QURAN_WIDGET_RE = re.compile(
    r"(سورۃ\s+[^\n]+?\{\s*(\d+)\s*:\s*(\d+)(?:\s*-\s*(\d+))?\s*\}[^\n]*\n"
    r"(?:[^\n]*\n)*?"
    r"\d+\s+[^\n]+\n)",
    re.MULTILINE,
)

# Inline Quran citation markers emitted by _render_quran_block.
_INLINE_QURAN_MARKER_RE = re.compile(r"⟪quran (\d+):(\d+)(?:-(\d+))?⟫")


class KashkoleQuranCorpus:
    """Cache HQAyats lookups; one row per ayat.

    HQAyats contains <I>, <P> tags in some translation fields; we strip them.
    """

    def __init__(self):
        self._by_key: Optional[dict[tuple[int, int], dict]] = None

    def _load(self) -> None:
        if self._by_key is not None:
            return
        rows = query_json(DB, """
            SELECT SurahNumber AS surah, AyatNumber AS ayat,
                   AyatUNICODE AS arabic, AyatTranslation AS english,
                   UrduTranslation AS urdu, Chapter AS surah_name,
                   Translation_Asad AS english_asad
            FROM HQAyats
            FOR JSON PATH;""")
        for r in rows:
            for k in ("english", "urdu", "english_asad", "arabic"):
                if r.get(k):
                    r[k] = re.sub(r"<[^>]+>", "", r[k]).strip()
                    r[k] = re.sub(r"\s+", " ", r[k])
        self._by_key = {(r["surah"], r["ayat"]): r for r in rows}

    def get(self, surah: int, ayat: int) -> Optional[dict]:
        self._load()
        return self._by_key.get((surah, ayat))

    def get_range(self, surah: int, start: int, end: int) -> list[dict]:
        self._load()
        out = []
        for a in range(start, end + 1):
            row = self._by_key.get((surah, a))
            if row:
                out.append(row)
        return out


def _render_quran_block(
    corpus: QuranCorpus,
    surah: int,
    start: int,
    end: Optional[int],
    source_note: str = "",
) -> str:
    """Emit a clean markdown blockquote for one or a range of Quran ayats."""
    end = end or start
    ayats = corpus.get_range(surah, start, end)
    if not ayats:
        return (
            f"> *(Quran {surah}:{start}"
            f"{('-' + str(end)) if end != start else ''} "
            f"— not found in HQAyats)*"
        )
    surah_name = ayats[0].get("surah_name") or ""
    range_str = f"{surah}:{start}" if end == start else f"{surah}:{start}-{end}"

    out: list[str] = []
    out.append(f"> ⟪quran {range_str}⟫")
    arabic_joined = " ".join((a["arabic"] or "").strip() for a in ayats if a.get("arabic"))
    if arabic_joined:
        out.append(f"> ⟪ar:{arabic_joined}⟫")
    english_lines = [(a.get("english") or "").strip() for a in ayats]
    english_joined = " ".join(e for e in english_lines if e)
    if english_joined:
        out.append(f"> *{english_joined}*")
    urdu_lines = [(a.get("urdu") or "").strip() for a in ayats]
    urdu_joined = " ".join(u for u in urdu_lines if u)
    if urdu_joined:
        out.append(f"> {urdu_joined}")
    citation = f"Quran {range_str}"
    if surah_name:
        citation = f"Quran {range_str} — *{surah_name.strip()}*"
    if source_note:
        citation = f"{citation} ({source_note})"
    out.append(f"> — **{citation}**")
    return "\n".join(out)


class KashkoleAdapter(SourceAdapter):
    source_name = "wisdom"
    source_language = "ur"
    labels = AdapterLabels(
        shelf_label="binder",
        book_label="chapter",
        section_label="topic",
    )

    def __init__(self):
        self._quran_corpus: Optional[KashkoleQuranCorpus] = None

    # ---- Required: book resolution + sections ------------------------------

    def resolve_book(self, ids: BookIds) -> BookMeta:
        binder = query_json(DB, f"""
            SELECT BinderID AS id, BinderName AS name, BinderOrder AS sort_key
            FROM Binders WHERE BinderID = {ids.shelf_id} FOR JSON PATH;""")[0]

        bc = query_json(DB, f"""
            SELECT bc.BinderChapterOrder AS book_sort_key,
                   c.ChapterID AS id, c.ChapterName AS name
            FROM BinderChapters bc
            JOIN Chapters c ON c.ChapterID = bc.ChapterID
            WHERE bc.BinderID = {ids.shelf_id} AND bc.ChapterID = {ids.book_id}
            FOR JSON PATH;""")[0]

        all_binders = query_json(DB,
            "SELECT BinderID AS id FROM Binders "
            "ORDER BY BinderOrder, BinderID FOR JSON PATH;")
        shelf_prefix = [b["id"] for b in all_binders].index(ids.shelf_id) + 1

        chaps_in_binder = query_json(DB, f"""
            SELECT ChapterID AS id FROM BinderChapters
            WHERE BinderID = {ids.shelf_id}
            ORDER BY BinderChapterOrder, ChapterID FOR JSON PATH;""")
        book_prefix = [c["id"] for c in chaps_in_binder].index(ids.book_id) + 1

        return BookMeta(
            source_name=self.source_name,
            source_language=self.source_language,
            shelf_id=binder["id"],
            shelf_name=binder["name"],
            shelf_sort_key=binder["sort_key"],
            shelf_prefix=shelf_prefix,
            shelf_slug=slugify_urdu(binder["name"], binder["id"]),
            book_id=bc["id"],
            book_name=bc["name"],
            book_sort_key=bc["book_sort_key"],
            book_prefix=book_prefix,
            book_slug=slugify_urdu(bc["name"], bc["id"]),
        )

    def get_book_sections(self, ids: BookIds) -> list[Section]:
        topics = query_json(DB, f"""
            SELECT ct.ChapterTopicOrder AS raw_sort,
                   t.TopicID AS id, t.TopicName AS name,
                   t.TopicNameEnglish AS name_en,
                   td.TopicUnicode AS html
            FROM ChapterTopics ct
            JOIN Topics t ON t.TopicID = ct.TopicID
            LEFT JOIN TopicDataUnicode td ON td.TopicID = t.TopicID
            WHERE ct.ChapterID = {ids.book_id}
            ORDER BY ct.ChapterTopicOrder
            FOR JSON PATH;""")

        sections: list[Section] = []
        for pos, t in enumerate(topics, 1):
            label = t["name"] or f"Topic {t['id']}"
            extras = {}
            if t.get("name_en"):
                extras["name_en"] = t["name_en"]
            sections.append(Section(
                position=pos,
                id=t["id"],
                raw_sort=t["raw_sort"],
                label=label,
                html=t.get("html"),
                extras=extras,
            ))
        return sections

    # ---- Optional: Quran corpus + inline citation cleanup ------------------

    def get_quran_corpus(self) -> KashkoleQuranCorpus:
        if self._quran_corpus is None:
            self._quran_corpus = KashkoleQuranCorpus()
        return self._quran_corpus

    def cleanup_inline_citations(
        self, md: str, corpus: Optional[QuranCorpus]
    ) -> tuple[str, list[dict]]:
        if corpus is None:
            return md, []
        replacements: list[dict] = []

        def _sub_quran(m: re.Match) -> str:
            full = m.group(1)
            surah = int(m.group(2))
            start = int(m.group(3))
            end = int(m.group(4)) if m.group(4) else None
            rendered = _render_quran_block(
                corpus, surah, start, end, source_note="inline widget"
            )
            replacements.append({
                "surah": surah,
                "start_ayat": start,
                "end_ayat": end or start,
                "raw_widget_chars": len(full),
            })
            return "\n" + rendered + "\n"

        rewritten = _QURAN_WIDGET_RE.sub(_sub_quran, md)
        return rewritten, replacements

    # ---- Optional: curated citations from TopicAyats -----------------------

    def get_section_curated_citations(self, section_id: int) -> list[dict]:
        rows = query_json(DB, f"""
            SELECT Surah AS surah, Ayat AS ayat
            FROM TopicAyats
            WHERE TopicID = {section_id}
            ORDER BY Surah, Ayat
            FOR JSON PATH;""")
        return [{"surah": int(r["surah"]), "ayat": int(r["ayat"])} for r in rows]

    def render_curated_citation_footer(
        self,
        section_body_md: str,
        refs: list[dict],
        corpus: Optional[QuranCorpus],
    ) -> str:
        if not refs or corpus is None:
            return ""
        inline_pairs: set[tuple[int, int]] = set()
        for m in _INLINE_QURAN_MARKER_RE.finditer(section_body_md):
            s = int(m.group(1))
            start = int(m.group(2))
            end = int(m.group(3)) if m.group(3) else start
            for a in range(start, end + 1):
                inline_pairs.add((s, a))

        novel = [
            r for r in refs
            if (int(r["surah"]), int(r["ayat"])) not in inline_pairs
        ]
        if not novel:
            return ""

        out: list[str] = [
            "\n*Verses referenced in this topic (curated linkage from "
            f"KAHSKOLE.TopicAyats — {len(novel)} of {len(refs)} not already "
            "cited above):*\n"
        ]
        for r in novel:
            s, a = int(r["surah"]), int(r["ayat"])
            out.append(_render_quran_block(corpus, s, a, None, source_note="TopicAyats"))
            out.append("")
        return "\n".join(out)
