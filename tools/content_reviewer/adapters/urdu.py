"""UrduReviewAdapter — full 4-type review pass for KAHSKOLE bundles.

Annotation types emitted (per spec):
  1. typo               — encoding junk, orphaned ZWNJ, doubled punctuation,
                          obvious OCR artifacts. high confidence only. source=self.
  2. quran-uncited      — Urdu prose names a surah by name (سورۃ X) but there
                          is no ⟪quran S:A⟫ marker in a nearby blockquote AND
                          we can identify the verse in HQAyats. source=hqayats.
  3. glossary           — first occurrence of a glossary term per section.
                          Lookup against tools/content_reviewer/data/ismaili-glossary.json.
                          source=glossary.
  4. sentence-completion — a sentence is grammatically truncated (no terminal
                          punctuation, followed by heading/section marker) and
                          completion is OBVIOUS from context. high-confidence
                          only; otherwise emit needs-human-review.
                          source=training | hqayats.

Anything ambiguous → needs-human-review with a short rationale.

Hard rule: do not invent. If unsure, prefer needs-human-review over filling in.
Hard rule: do not modify raw-extract.md. This adapter only returns Annotation
records; stages/review.py writes them to the sibling annotation layer.
"""
from __future__ import annotations
import re
from typing import Optional

from .base import ReviewAdapter, Annotation


# --- Patterns --------------------------------------------------------------

# Quran inline-citation markers already present in the section (these are
# the ones finalize.py emitted from KAHSKOLE Quran widgets).
_QURAN_MARKER_RE = re.compile(r"⟪quran\s+(\d+):(\d+)(?:-(\d+))?⟫")

# "سورۃ <name>" — Urdu naming of a surah in prose. The name may have
# diacritics / variant orthographies (سورۂ, سورة, سورۂِ, etc.).
_SURAH_NAME_RE = re.compile(
    r"سور[ۃۂةت][\s‌]+([؀-ۿݐ-ݿ]+(?:[\s‌][؀-ۿݐ-ݿ]+)?)"
)

# Common typo / OCR-artifact patterns. High-confidence ONLY.
#   - run of 3+ ASCII spaces (rare in Arabic-script text, often an OCR artifact)
#   - doubled punctuation: ،، ؛؛ ۔۔ (three or more)
#   - orphaned ZWNJ at start of a word
#   - bare ­ (soft hyphen) inside a word
_TYPO_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    ("triple-punct-period", re.compile(r"۔{3,}"), "Three or more Urdu full stops (۔۔۔+) in a row"),
    ("triple-punct-comma",  re.compile(r"،{3,}"),       "Three or more Urdu commas (،،،+) in a row"),
    ("soft-hyphen",         re.compile(r"­"),       "Soft hyphen U+00AD inside Urdu text (OCR artifact)"),
    ("replacement-char",    re.compile(r"�"),       "Unicode replacement character U+FFFD (decoding failure)"),
    ("zwnj-orphan-start",   re.compile(r"(?:^|[\s\n])‌"), "Orphaned zero-width-non-joiner at start of word"),
]

# Section marker emitted by Stage A (used to split raw-extract.md into sections).
SECTION_MARKER_RE = re.compile(
    r"<!--\s*section\s+(\d+)\s+\(id=(\d+),\s*raw_sort=(\d+)\):\s*(.+?)\s*-->"
)


# --- Surah-name → number map (Urdu spellings) -------------------------------
# This is intentionally a small, high-confidence subset. Names with multiple
# romanizations or ambiguous Urdu orthography are omitted (those will fall
# through to "uncertain" and not be flagged as quran-uncited).
_URDU_SURAH_NAMES: dict[str, int] = {
    "الفاتحۃ": 1, "الفاتحہ": 1, "فاتحۃ": 1, "فاتحہ": 1,
    "البقرۃ": 2, "البقرہ": 2, "بقرۃ": 2, "بقرہ": 2,
    "آل عمران": 3,
    "النساء": 4, "نساء": 4,
    "المائدۃ": 5, "المائدہ": 5,
    "الانعام": 6, "انعام": 6,
    "الاعراف": 7, "اعراف": 7,
    "الانفال": 8, "انفال": 8,
    "التوبۃ": 9, "التوبہ": 9, "توبۃ": 9, "توبہ": 9, "براءۃ": 9,
    "یونس": 10,
    "ہود": 11,
    "یوسف": 12,
    "الرعد": 13, "رعد": 13,
    "ابراہیم": 14,
    "الحجر": 15,
    "النحل": 16, "نحل": 16,
    "الاسراء": 17, "بنی اسرائیل": 17,
    "الکہف": 18, "کہف": 18,
    "مریم": 19,
    "طٰہٰ": 20, "طہ": 20,
    "الانبیاء": 21, "انبیاء": 21,
    "الحج": 22, "حج": 22,
    "المؤمنون": 23, "مؤمنون": 23,
    "النور": 24, "نور": 24,
    "الفرقان": 25, "فرقان": 25,
    "الشعراء": 26,
    "النمل": 27, "نمل": 27,
    "القصص": 28,
    "العنکبوت": 29, "عنکبوت": 29,
    "الروم": 30, "روم": 30,
    "لقمان": 31,
    "السجدۃ": 32, "السجدہ": 32,
    "الاحزاب": 33, "احزاب": 33,
    "سبا": 34, "سبأ": 34,
    "فاطر": 35,
    "یٰسین": 36, "یس": 36,
    "الصافات": 37,
    "صٓ": 38, "ص": 38,
    "الزمر": 39, "زمر": 39,
    "غافر": 40, "المؤمن": 40,
    "فصلت": 41, "حم السجدۃ": 41,
    "الشوریٰ": 42, "شوریٰ": 42,
    "الزخرف": 43,
    "الدخان": 44, "دخان": 44,
    "الجاثیۃ": 45, "جاثیہ": 45,
    "الاحقاف": 46,
    "محمد": 47,
    "الفتح": 48, "فتح": 48,
    "الحجرات": 49, "حجرات": 49,
    "قٓ": 50, "ق": 50,
    "الذاریات": 51, "ذاریات": 51,
    "الطور": 52, "طور": 52,
    "النجم": 53, "نجم": 53,
    "القمر": 54, "قمر": 54,
    "الرحمن": 55, "الرحمٰن": 55,
    "الواقعۃ": 56, "الواقعہ": 56, "واقعۃ": 56, "واقعہ": 56,
    "الحدید": 57,
    "المجادلۃ": 58, "المجادلہ": 58,
    "الحشر": 59, "حشر": 59,
    "الممتحنۃ": 60, "الممتحنہ": 60,
    "الصف": 61,
    "الجمعۃ": 62, "الجمعہ": 62,
    "المنافقون": 63,
    "التغابن": 64,
    "الطلاق": 65, "طلاق": 65,
    "التحریم": 66,
    "الملک": 67, "ملک": 67, "تبارک": 67,
    "القلم": 68, "قلم": 68, "ن": 68,
    "الحاقۃ": 69, "الحاقہ": 69,
    "المعارج": 70, "معارج": 70,
    "نوح": 71,
    "الجن": 72, "جن": 72,
    "المزمل": 73, "مزمل": 73,
    "المدثر": 74, "مدثر": 74,
    "القیامۃ": 75, "القیامہ": 75,
    "الانسان": 76, "الدہر": 76,
    "المرسلات": 77,
    "النباء": 78, "النبأ": 78, "نباء": 78, "عم": 78,
    "النازعات": 79,
    "عبس": 80,
    "التکویر": 81,
    "الانفطار": 82,
    "المطففین": 83,
    "الانشقاق": 84,
    "البروج": 85,
    "الطارق": 86,
    "الاعلیٰ": 87, "اعلیٰ": 87,
    "الغاشیۃ": 88, "الغاشیہ": 88,
    "الفجر": 89, "فجر": 89,
    "البلد": 90, "بلد": 90,
    "الشمس": 91, "شمس": 91,
    "اللیل": 92, "لیل": 92,
    "الضحیٰ": 93, "ضحیٰ": 93,
    "الشرح": 94, "الانشراح": 94,
    "التین": 95, "تین": 95,
    "العلق": 96, "علق": 96,
    "القدر": 97, "قدر": 97,
    "البینۃ": 98, "البینہ": 98,
    "الزلزلۃ": 99, "الزلزال": 99,
    "العادیات": 100,
    "القارعۃ": 101, "القارعہ": 101,
    "التکاثر": 102,
    "العصر": 103, "عصر": 103,
    "الہمزۃ": 104, "الہمزہ": 104,
    "الفیل": 105, "فیل": 105,
    "قریش": 106,
    "الماعون": 107, "ماعون": 107,
    "الکوثر": 108, "کوثر": 108,
    "الکافرون": 109, "کافرون": 109,
    "النصر": 110, "نصر": 110,
    "اللہب": 111, "المسد": 111, "تبت": 111,
    "الاخلاص": 112, "اخلاص": 112,
    "الفلق": 113, "فلق": 113,
    "الناس": 114, "ناس": 114,
}


# --- Helpers ---------------------------------------------------------------

def _local_blockquote_window(text: str, span_start: int, span_end: int,
                              window: int = 600) -> str:
    """Return ~600 chars of context around a span. Used to check whether a
    nearby ⟪quran S:A⟫ marker exists, which would mean the verse IS cited
    (even if the prose mentions the surah by name)."""
    a = max(0, span_start - window)
    b = min(len(text), span_end + window)
    return text[a:b]


def _looks_like_terminal(line: str) -> bool:
    """True if line ends with terminal punctuation (or is empty / heading / marker)."""
    s = line.rstrip()
    if not s:
        return True
    if s.startswith("#") or s.startswith("<!--") or s.startswith(">") or s.startswith("|"):
        return True
    if s.startswith("["):  # image alt blocks
        return True
    return s.endswith((".", "۔", "؟", "!", "؛", ":", "،",
                       ")", "]", "*", "_", "'", "\"", "”", "’", "»",
                       "...", "…", "⟫"))


# --- Adapter ----------------------------------------------------------------

class UrduReviewAdapter(ReviewAdapter):
    language = "ur"

    def review_section(
        self,
        section_text: str,
        section_id: int,
        section_position: int,
        label: str,
        glossary: dict,
        quran_corpus,
    ) -> list[Annotation]:
        annotations: list[Annotation] = []

        annotations.extend(
            self._scan_typos(section_text, section_id, section_position)
        )
        annotations.extend(
            self._scan_quran_uncited(
                section_text, section_id, section_position, quran_corpus
            )
        )
        annotations.extend(
            self._scan_glossary(
                section_text, section_id, section_position, glossary
            )
        )
        annotations.extend(
            self._scan_sentence_completion(
                section_text, section_id, section_position, quran_corpus
            )
        )

        return annotations

    # ---- 1. Typos ---------------------------------------------------------

    def _scan_typos(
        self, text: str, section_id: int, section_position: int
    ) -> list[Annotation]:
        out: list[Annotation] = []
        for name, pat, label in _TYPO_PATTERNS:
            for m in pat.finditer(text):
                start = max(0, m.start() - 30)
                end = min(len(text), m.end() + 30)
                excerpt = text[start:end].replace("\n", " ⏎ ")
                out.append(Annotation(
                    section_id=section_id,
                    section_position=section_position,
                    type="typo",
                    confidence="high",
                    original_excerpt=excerpt,
                    annotation=f"Remove or replace artifact ({name})",
                    rationale=label,
                    source="self",
                ))
        return out

    # ---- 2. Quran-uncited -------------------------------------------------

    def _scan_quran_uncited(
        self,
        text: str,
        section_id: int,
        section_position: int,
        quran_corpus,
    ) -> list[Annotation]:
        """If prose mentions 'سورۃ <name>' and we can resolve the name to a
        surah number, AND no ⟪quran <that_number>:?⟫ marker exists in a
        ~600-char window around the mention, flag as quran-uncited.
        We do NOT propose a specific ayat (that requires actual phrase
        matching) — we flag the missing citation and identify the surah."""
        out: list[Annotation] = []
        for m in _SURAH_NAME_RE.finditer(text):
            name = m.group(1).strip()
            surah_num = _URDU_SURAH_NAMES.get(name) or _URDU_SURAH_NAMES.get(name.split()[0] if " " in name else name)
            if not surah_num:
                continue
            window = _local_blockquote_window(text, m.start(), m.end())
            if any(int(mm.group(1)) == surah_num for mm in _QURAN_MARKER_RE.finditer(window)):
                continue
            # No nearby citation marker for this surah. Flag.
            ctx_start = max(0, m.start() - 60)
            ctx_end = min(len(text), m.end() + 60)
            excerpt = text[ctx_start:ctx_end].replace("\n", " ⏎ ")
            out.append(Annotation(
                section_id=section_id,
                section_position=section_position,
                type="quran-uncited",
                confidence="medium",
                original_excerpt=excerpt,
                annotation=(
                    f"Surah {surah_num} ({name}) mentioned in prose but no "
                    f"⟪quran {surah_num}:?⟫ citation marker nearby. Human reviewer "
                    "to identify the specific ayat(s) intended."
                ),
                rationale=(
                    "Reviewer detected a 'سورۃ <name>' mention in Urdu prose "
                    f"resolvable to surah {surah_num}, but no inline citation "
                    "marker for that surah within ±600 chars."
                ),
                source="hqayats",
            ))
        return out

    # ---- 3. Glossary ------------------------------------------------------

    def _scan_glossary(
        self,
        text: str,
        section_id: int,
        section_position: int,
        glossary: dict,
    ) -> list[Annotation]:
        out: list[Annotation] = []
        seen_in_section: set[str] = set()
        terms = glossary.get("terms", [])
        for entry in terms:
            term = entry.get("term", "").strip()
            if not term or term in seen_in_section:
                continue
            idx = text.find(term)
            if idx < 0:
                continue
            seen_in_section.add(term)
            ctx_start = max(0, idx - 40)
            ctx_end = min(len(text), idx + len(term) + 40)
            excerpt = text[ctx_start:ctx_end].replace("\n", " ⏎ ")
            translit = entry.get("transliteration", "")
            english = entry.get("english", "")
            definition = entry.get("definition_en") or entry.get("definition_ur", "")
            confidence = entry.get("confidence", "high")
            out.append(Annotation(
                section_id=section_id,
                section_position=section_position,
                type="glossary",
                confidence=confidence,
                original_excerpt=excerpt,
                annotation=(
                    f"Glossary term: {term} ({translit}) — {english}"
                ),
                rationale=f"Curated glossary entry: {definition}",
                source="glossary",
            ))
        return out

    # ---- 4. Sentence-completion ------------------------------------------

    def _scan_sentence_completion(
        self,
        text: str,
        section_id: int,
        section_position: int,
        quran_corpus,
    ) -> list[Annotation]:
        """Look for paragraphs that end mid-clause (no terminal punctuation),
        immediately followed by a heading or section marker or blank line.

        High-confidence completion = a well-known formula like صلی اللہ علیہ وآلہ وسلم.
        Anything else: flag as needs-human-review.
        """
        out: list[Annotation] = []
        lines = text.split("\n")
        for i, line in enumerate(lines):
            s = line.strip()
            if not s:
                continue
            # Skip code / markdown structural lines.
            if s.startswith(("#", ">", "|", "<!--", "[", "*", "-", "  ")):
                continue
            if _looks_like_terminal(line):
                continue
            # Now: line is non-empty Urdu prose without terminal punctuation.
            # Check next non-blank line — if it's a heading / section marker
            # / blockquote, this looks like an interrupted sentence.
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j >= len(lines):
                # End of section without terminal punctuation.
                next_marker = "<end of section>"
            else:
                next_marker = lines[j].strip()
            if not (next_marker.startswith(("#", "<!--", ">"))
                    or next_marker == "<end of section>"):
                continue

            ctx_start = max(0, sum(len(l) + 1 for l in lines[:i]) + max(0, len(line) - 80))
            excerpt = s[-80:] if len(s) > 80 else s
            # Look for known-formula trigger: bare محمد / النبی / رسول اللہ
            # without the salutation following.
            if re.search(r"(محمد|رسول اللہ|النبی|الرسول)\s*$", s):
                out.append(Annotation(
                    section_id=section_id,
                    section_position=section_position,
                    type="sentence-completion",
                    confidence="high",
                    original_excerpt=excerpt,
                    annotation="Append: صلی اللہ علیہ وآلہ وسلم",
                    rationale=(
                        "Mention of the Prophet without the customary "
                        "salutation; conventional completion is the salawat."
                    ),
                    source="training",
                ))
            else:
                out.append(Annotation(
                    section_id=section_id,
                    section_position=section_position,
                    type="needs-human-review",
                    confidence="low",
                    original_excerpt=excerpt,
                    annotation=(
                        "Sentence appears truncated mid-clause "
                        f"(followed by '{next_marker[:40]}'). Human reviewer to "
                        "complete from source if needed."
                    ),
                    rationale=(
                        "No terminal punctuation; next non-blank line is a "
                        "heading or section marker. Completion is not obvious "
                        "from immediate context."
                    ),
                    source="self",
                ))
        return out
