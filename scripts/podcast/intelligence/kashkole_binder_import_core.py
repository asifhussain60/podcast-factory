"""Shared data shapes and text helpers for Kashkole binder corpus imports."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

WISDOM_TRADITION = "fatimid-ismaili"
SOURCE_KIND = "kashkole_binder_translation"
REVIEW_REASON = "kashkole_binder_near_duplicate"
ATOM_PREFIX = "doctrine:kashkole:"
MAX_CHUNK_WORDS = 600
ALLOWED_CONTENT_LEVELS = {"general", "advanced", "taveel", "mamsool", "mabda_maad", "haqaiq", "universal"}

_WORD_RE = re.compile(r"[^\w]+", re.UNICODE)
_QREF_PATTERNS = (
    re.compile(r"⟪\s*quran\s+(\d{1,3})\s*[:.]\s*(\d{1,3})\s*⟫", re.IGNORECASE),
    re.compile(r"\bQ(?:uran)?\s*,?\s*(\d{1,3})\s*[:.]\s*(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"\bQ(\d{1,3})\s*[:.]\s*(\d{1,3})\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class BinderConfig:
    binder: str
    primary_category: str
    secondary_category: str
    content_level: str
    corpus_status: str = "ready"


BINDER_CONFIGS: dict[str, BinderConfig] = {
    "Quranic Studies": BinderConfig("Quranic Studies", "quranic_taveel", "haqaiq", "taveel"),
    "The Wise Reminder": BinderConfig("The Wise Reminder", "quranic_taveel", "spirituality", "taveel"),
    "ISLAM IMAN IHSAN": BinderConfig("ISLAM IMAN IHSAN", "doctrine", "spirituality", "general"),
    "قرآنی قصص الانبیا کے حقائق": BinderConfig("قرآنی قصص الانبیا کے حقائق", "haqaiq", "quranic_narrative", "haqaiq"),
    "توحید مبدع تعالی": BinderConfig("توحید مبدع تعالی", "tawhid", "doctrine", "advanced"),
    "علوم مبدا و معاد": BinderConfig("علوم مبدا و معاد", "mabda_maad", "cosmology", "mabda_maad"),
    "کلمات ربانی کی تاویلات": BinderConfig("کلمات ربانی کی تاویلات", "taveel", "quran_hadith", "taveel"),
    "آداب و اخلاق حسنۃ": BinderConfig("آداب و اخلاق حسنۃ", "akhlaq_adab", "ethics", "general"),
    "غزالی - کیمیائی السعادۃ": BinderConfig("غزالی - کیمیائی السعادۃ", "akhlaq_tazkiyah", "spirituality", "advanced"),
    "منتخب علمی مضامین": BinderConfig("منتخب علمی مضامین", "doctrine", "hikmah", "general"),
    "مسودے": BinderConfig("مسودے", "mixed_manuscripts", "review_required", "advanced"),
    "دعائم الاسلام : صلواۃ": BinderConfig("دعائم الاسلام : صلواۃ", "shariat", "mamsool", "general", "held"),
    "دعائم الاسلام : ولایت": BinderConfig("دعائم الاسلام : ولایت", "shariat", "doctrine", "general", "held"),
    "دعائم الاسلام : الصوم": BinderConfig("دعائم الاسلام : الصوم", "shariat", "mamsool", "general", "held"),
    "دعائم الاسلام : طہارت": BinderConfig("دعائم الاسلام : طہارت", "shariat", "mamsool", "general", "held"),
    "علی ابن ابی طالب علیہ السلام": BinderConfig(
        "علی ابن ابی طالب علیہ السلام", "history_sirah", "virtues", "general", "held"
    ),
}


@dataclass
class TopicRow:
    topic_id: int
    name_ur: str
    binder: str
    chapter: str
    source_body: str
    name_en: str
    body_en: str
    source_sha: str
    source_chars: int
    output_chars: int
    windows: int
    model: str
    prompt_version: str
    standard_sha: str
    run_id: str
    translated_at: str
    status: str
    concerns: list[str]


@dataclass
class AtomCandidate:
    atom_id: str
    text_en: str
    topic: TopicRow
    chunk_index: int
    chunk_count: int
    quran_refs: list[str]
    config: BinderConfig

    @property
    def source_book(self) -> str:
        return f"kashkole-{slugify(self.config.binder)}"

    @property
    def source_chapter(self) -> str:
        return slugify(self.topic.chapter) or str(self.topic.topic_id)

    @property
    def locator(self) -> str:
        return f"topic:{self.topic.topic_id}:chunk:{self.chunk_index}"

    def topic_tags(self) -> list[str]:
        return [
            self.config.primary_category,
            self.config.secondary_category,
            f"binder:{slugify(self.config.binder)}",
            f"chapter:{self.source_chapter}",
            f"topic:{self.topic.topic_id}",
            "kashkole",
        ]

    def body(self) -> dict[str, Any]:
        return {
            "text_en": self.text_en,
            "source_kind": SOURCE_KIND,
            "tradition": WISDOM_TRADITION,
            "binder": self.topic.binder,
            "binder_slug": slugify(self.topic.binder),
            "chapter": self.topic.chapter,
            "chapter_slug": self.source_chapter,
            "topic_id": self.topic.topic_id,
            "topic_title_ur": self.topic.name_ur,
            "topic_title_en": self.topic.name_en,
            "chunk_index": self.chunk_index,
            "chunk_count": self.chunk_count,
            "topic_tags": self.topic_tags(),
            "quran_refs": self.quran_refs,
            "source_sha": self.topic.source_sha,
            "source_chars": self.topic.source_chars,
            "output_chars": self.topic.output_chars,
            "windows": self.topic.windows,
            "model": self.topic.model,
            "prompt_version": self.topic.prompt_version,
            "standard_sha": self.topic.standard_sha,
            "run_id": self.topic.run_id,
            "translated_at": self.topic.translated_at,
        }


@dataclass
class ImportSummary:
    binder: str
    dry_run: bool
    total_topics: int = 0
    translated_topics: int = 0
    eligible_topics: int = 0
    empty_topics: int = 0
    held_topics: int = 0
    candidates: int = 0
    new_atoms: int = 0
    existing_atoms: int = 0
    exact_duplicates: int = 0
    near_duplicates: int = 0
    quran_refs: int = 0
    hydrated_quran_atoms: int = 0
    missing_quran_atoms: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    new_atom_ids: list[str] = field(default_factory=list)
    existing_atom_ids: list[str] = field(default_factory=list)
    exact_duplicate_rows: list[dict[str, Any]] = field(default_factory=list)
    near_duplicate_rows: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "podcast.kashkole-binder-import/v1",
            "binder": self.binder,
            "dry_run": self.dry_run,
            "total_topics": self.total_topics,
            "translated_topics": self.translated_topics,
            "eligible_topics": self.eligible_topics,
            "empty_topics": self.empty_topics,
            "held_topics": self.held_topics,
            "candidates": self.candidates,
            "new_atoms": self.new_atoms,
            "existing_atoms": self.existing_atoms,
            "exact_duplicates": self.exact_duplicates,
            "near_duplicates": self.near_duplicates,
            "quran_refs": self.quran_refs,
            "hydrated_quran_atoms": self.hydrated_quran_atoms,
            "missing_quran_atoms": self.missing_quran_atoms,
            "errors": self.errors,
            "new_atom_ids": self.new_atom_ids,
            "existing_atom_ids": self.existing_atom_ids,
            "exact_duplicate_rows": self.exact_duplicate_rows,
            "near_duplicate_rows": self.near_duplicate_rows,
        }


def normalize(text: str) -> str:
    return _WORD_RE.sub(" ", (text or "").lower()).strip()


def tokens(text: str) -> frozenset[str]:
    return frozenset(t for t in normalize(text).split() if len(t) > 2)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    if slug:
        return slug[:80].strip("-")
    digest = hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:10]
    return f"u-{digest}"


def text_hash(text: str) -> str:
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()[:16]


def quran_refs(text: str) -> list[str]:
    refs: set[str] = set()
    for pattern in _QREF_PATTERNS:
        for surah_s, ayah_s in pattern.findall(text or ""):
            surah, ayah = int(surah_s), int(ayah_s)
            if 1 <= surah <= 114 and 1 <= ayah <= 286:
                refs.add(f"{surah}:{ayah}")
    return sorted(refs, key=lambda r: tuple(int(x) for x in r.split(":")))


def chunk_text(text: str, *, max_words: int = MAX_CHUNK_WORDS) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    words = 0
    for para in paragraphs:
        para_words = len(para.split())
        if buf and words + para_words > max_words:
            chunks.append("\n\n".join(buf).strip())
            buf, words = [], 0
        if para_words > max_words:
            sent_buf: list[str] = []
            sent_words = 0
            for sent in re.split(r"(?<=[.!?۔])\s+", para):
                count = len(sent.split())
                if sent_buf and sent_words + count > max_words:
                    chunks.append(" ".join(sent_buf).strip())
                    sent_buf, sent_words = [], 0
                sent_buf.append(sent)
                sent_words += count
            if sent_buf:
                buf.append(" ".join(sent_buf).strip())
                words += sent_words
            continue
        buf.append(para)
        words += para_words
    if buf:
        chunks.append("\n\n".join(buf).strip())
    return [c for c in chunks if c]


def topic_row_from_sql(row: Any) -> TopicRow:
    try:
        concerns = json.loads(row["concerns"] or "[]")
    except json.JSONDecodeError:
        concerns = [row["concerns"]]
    return TopicRow(
        topic_id=int(row["topic_id"]),
        name_ur=row["name"] or "",
        binder=row["binder"] or "",
        chapter=row["chapter"] or "",
        source_body=row["body_plain"] or "",
        name_en=row["name_en"] or "",
        body_en=row["body_en"] or "",
        source_sha=row["source_sha"] or "",
        source_chars=int(row["source_chars"] or 0),
        output_chars=int(row["output_chars"] or 0),
        windows=int(row["windows"] or 0),
        model=row["model"] or "",
        prompt_version=row["prompt_version"] or "",
        standard_sha=row["standard_sha"] or "",
        run_id=row["run_id"] or "",
        translated_at=row["translated_at"] or "",
        status=row["status"] or "",
        concerns=list(concerns or []),
    )
