"""Shared data shapes and text helpers for Kashkole binder corpus imports."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
for _p in (str(_SCRIPTS), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _arabic_coverage import ARABIC_BODY  # noqa: E402

WISDOM_TRADITION = "fatimid-ismaili"
SOURCE_KIND = "kashkole_binder_translation"
REVIEW_REASON = "kashkole_binder_near_duplicate"
ATOM_PREFIX = "doctrine:kashkole:"
MAX_CHUNK_WORDS = 600
ALLOWED_CONTENT_LEVELS = {"general", "advanced", "taveel", "mamsool", "mabda_maad", "haqaiq", "universal"}

_WORD_RE = re.compile(r"[^\w]+", re.UNICODE)
_QREF_PATTERNS = (
    re.compile(r"⟪\s*quran\s+(\d{1,3})\s*[:.]\s*(\d{1,3})\s*⟫", re.IGNORECASE),
    re.compile(r"\bQ(?:uran)?\s*,?\s*(\d{1,3})\s*[:.]\s*(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?\b", re.IGNORECASE),
    re.compile(r"\bQ(\d{1,3})\s*[:.]\s*(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?\b", re.IGNORECASE),
)
_ARABIC_ADJACENT_QREF_RE = re.compile(
    r"(?<!\d)(\d{1,3}):(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?(?=\s+[" + ARABIC_BODY + r"])"
)
_BRACED_QREF_RE = re.compile(r"\{\s*(\d{1,3}):(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?\s*\}")
_SURAH_THEN_VERSE_RE = re.compile(
    r"\b(?:surah|sura)\s+([a-z][a-z'\-’ ]{1,40}?)\s*,?\s*(?:verse|ayah|ayat)\s+(\d{1,3})\b",
    re.IGNORECASE,
)
_VERSE_THEN_SURAH_RE = re.compile(
    r"\b(?:verse|ayah|ayat)\s+(\d{1,3})\s+of\s+(?:surah|sura)\s+([a-z][a-z'\-’ ]{1,40})\b",
    re.IGNORECASE,
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
    "دعائم الاسلام : طہارت": BinderConfig("دعائم الاسلام : طہارت", "shariat", "mamsool", "general"),
    "علی ابن ابی طالب علیہ السلام": BinderConfig(
        "علی ابن ابی طالب علیہ السلام", "history_sirah", "virtues", "general", "held"
    ),
}

# Binder-level categories are the default, not a license to mislabel a topic
# whose own source context is more specific. These overrides are deliberately
# small and evidence-based: shared salutations are devotional rather than
# ta'wil, explicitly named ta'wil lessons are not general, and the two Wise
# Reminder chapters have distinct pedagogical levels.
TOPIC_CLASSIFICATION_OVERRIDES: dict[int, tuple[str, str, str]] = {
    5679: ("devotional_praise", "spirituality", "general"),
    5680: ("devotional_praise", "spirituality", "general"),
    5681: ("devotional_praise", "spirituality", "general"),
    5683: ("devotional_praise", "spirituality", "general"),
    5783: ("doctrine", "spirituality", "advanced"),
    5785: ("doctrine", "spirituality", "advanced"),
    5787: ("quranic_taveel", "haqaiq", "taveel"),
    6798: ("quranic_taveel", "haqaiq", "taveel"),
    # Prophet Stories: moral and spiritual counsel is reusable at an advanced
    # level without presenting it as inner cosmology.
    1462: ("spirituality", "ethics", "advanced"),
    1464: ("quranic_narrative", "ethics", "advanced"),
    1467: ("spirituality", "ethics", "advanced"),
    1469: ("spirituality", "ethics", "advanced"),
    1471: ("spirituality", "ethics", "advanced"),
    1481: ("spirituality", "ethics", "advanced"),
    1482: ("spirituality", "ethics", "advanced"),
    1223: ("hadith_taveel", "spirituality", "advanced"),
    1225: ("hadith_taveel", "spirituality", "advanced"),
    1226: ("hadith_taveel", "spirituality", "advanced"),
    1330: ("spirituality", "soul_psychology", "advanced"),
}

CHAPTER_CLASSIFICATION_OVERRIDES: dict[tuple[str, str], tuple[str, str, str]] = {
    ("The Wise Reminder", "Miracles of Quran"): ("quranic_studies", "linguistics", "advanced"),
    ("The Wise Reminder", "The Human Spirit"): ("spirituality", "soul_psychology", "advanced"),
    ("قرآنی قصص الانبیا کے حقائق", "نطقا کا بیان"): ("doctrine", "prophetic_authority", "haqaiq"),
    ("دعائم الاسلام : طہارت", "ارکان وضو کے باطنی معنی"): ("taveel", "mamsool", "taveel"),
}

# This chapter is explicitly a draft/mixed holding area. Its topics include
# quotes, definitions, hadith and editing notes, so forcing them all into
# doctrine atoms would be a type error. Translation remains preserved in the
# mirror; corpus insertion waits for deliberate per-item classification.
HELD_CHAPTERS: frozenset[tuple[str, str]] = frozenset({("Quranic Studies", "مسودہ")})
HELD_TOPIC_IDS: frozenset[int] = frozenset(
    {
        1478,  # long outer-story compilation with unattributed transmitted reports
        5741,  # Noah chronology/genealogy and Biblical reports require citation repair
        1483,  # attributed saying should be classified as a quote after provenance review
        1224,  # transmitted report needs provenance review
        1227,  # cat narrative needs provenance review
        1230,  # enumerated legal ruling needs source verification
        1237,  # disputed wiping ruling needs legal-source verification
        1242,  # impurity ruling needs legal-source verification
        1243,  # lavatory teaching needs legal-source verification
        1244,  # enumerated lavatory etiquettes need source verification
        1253,  # feet-wiping citation is image-based and unverified
        1258,  # menstruation teaching needs legal-source review
        1346,  # triple-repetition ruling needs source verification
        816,  # excluded from active corpus: sectarian polemic
        1241,  # excluded from active corpus: broad impurity claim about non-Muslims
        1450,  # excluded from active corpus: denigrating claim about women
    }
)


def config_for_topic(base: BinderConfig, topic_id: int, chapter: str) -> BinderConfig:
    values = TOPIC_CLASSIFICATION_OVERRIDES.get(topic_id)
    if values is None:
        values = CHAPTER_CLASSIFICATION_OVERRIDES.get((base.binder, chapter))
    if values is None:
        return base
    primary, secondary, level = values
    return replace(base, primary_category=primary, secondary_category=secondary, content_level=level)


def topic_is_held(binder: str, chapter: str, topic_id: int | None = None) -> bool:
    return (binder, chapter) in HELD_CHAPTERS or (topic_id is not None and topic_id in HELD_TOPIC_IDS)


def topic_has_classification_override(binder: str, topic_id: int, chapter: str) -> bool:
    return topic_id in TOPIC_CLASSIFICATION_OVERRIDES or (binder, chapter) in CHAPTER_CLASSIFICATION_OVERRIDES


def managed_category_tags() -> frozenset[str]:
    tags = {
        value for config in BINDER_CONFIGS.values() for value in (config.primary_category, config.secondary_category)
    }
    for primary, secondary, _ in (*TOPIC_CLASSIFICATION_OVERRIDES.values(), *CHAPTER_CLASSIFICATION_OVERRIDES.values()):
        tags.update((primary, secondary))
    return frozenset(tags)


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
        for match in pattern.finditer(text or ""):
            _add_quran_range(refs, *match.groups())
    for match in _ARABIC_ADJACENT_QREF_RE.finditer(text or ""):
        _add_quran_range(refs, *match.groups())
    for match in _BRACED_QREF_RE.finditer(text or ""):
        _add_quran_range(refs, *match.groups())

    # Named-surah references are unambiguous and avoid the false positives of
    # treating every bare 11:08 timestamp as scripture.
    try:
        from _book_citations import surah_number
    except ImportError:  # pragma: no cover - standalone utility fallback
        surah_number = lambda _name: 0  # type: ignore[assignment]
    for match in _SURAH_THEN_VERSE_RE.finditer(text or ""):
        surah = surah_number(match.group(1))
        if surah:
            _add_quran_range(refs, str(surah), match.group(2), None)
    for match in _VERSE_THEN_SURAH_RE.finditer(text or ""):
        surah = surah_number(match.group(2))
        if surah:
            _add_quran_range(refs, str(surah), match.group(1), None)
    return sorted(refs, key=lambda r: tuple(int(x) for x in r.split(":")))


def _add_quran_range(refs: set[str], surah_s: str, start_s: str, end_s: str | None = None) -> None:
    surah, start = int(surah_s), int(start_s)
    end = int(end_s) if end_s else start
    if not (1 <= surah <= 114 and 1 <= start <= end <= 286):
        return
    for ayah in range(start, end + 1):
        refs.add(f"{surah}:{ayah}")


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
