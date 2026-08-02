#!/usr/bin/env python3
"""Build ayyuhal-walad's Arabic ground truth at the path compose actually reads.

The book HAS an Azure OCR of the Arabic original — `_system/source/multi/ocr/
arabic.md`, 15 pages, paid for at intake — but `_book_compose._load_arabic_pages`
reads `_system/source/ocr/raw-extract.md`, which this book has never had. So every
compose has run with NO Arabic ground truth, and the 82 Arabic runs in the June
edition came from model memory: the same defect already diagnosed for
asaas-al-taveel.

The two files cannot simply be copied into place, because `_arabic_for` keys the
Arabic by the ENGLISH page number: it maps a chapter's `source_line_ranges` into
`refined-english.md` pages and looks those numbers up in the Arabic dict. The
scans do not share a pagination — the English translation runs 30 pages, the
Arabic original 15, printed pages 39-53, and it is bracketed by the tail of one
unrelated treatise and the head of another. Page 4 of one is not page 4 of the
other.

So this re-buckets the Arabic under the English pagination:

  1. Trim to the treatise. Lines 11-441 — the preceding work ends at line 10
     ("نجز الكتاب بكامله", "the book is complete in its entirety") and the
     following one begins at line 442 ("المكاتيب المنتخبة", Imam Rabbani's
     letters). Both boundaries are explicit, not inferred.
  2. Map English line -> Arabic line by piecewise-linear interpolation between
     ANCHORS verified in both texts (below). Global proportional mapping was
     rejected: the measured ratio swings from 1.3 to 2.2 English lines per Arabic
     line, because the English carries the translator's bracketed expansions and a
     blank line between paragraphs. Interpolating between short verified segments
     keeps the error inside a page.
  3. Pad each bucket. A passage that falls in a crack sends the model back to
     memory, which is the whole defect; adjacent context costs a few lines of
     prompt. Padding is one-directional insurance, never a correctness claim.

Every anchor below was read in BOTH files before being written here. Rejected
anchor recorded so it is not re-proposed: English 252 (zawiya/hawiya) against
Arabic 351 (الهاوية) — the Arabic there is "or does he fall into the abyss" in
the sirat passage, a different use of the same word, hundreds of lines away.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BOOK = Path(__file__).resolve().parents[3]  # content/Islamic/ayyuhal-walad
ARABIC_SRC = BOOK / "_system/source/multi/ocr/arabic.md"
ENGLISH = BOOK / "_system/source/text/refined-english.md"
OUT = BOOK / "_system/source/ocr/raw-extract.md"

# The treatise's own extent inside arabic.md (1-based, inclusive).
AR_FIRST, AR_LAST = 11, 441

# (english_line, arabic_line) — each verified in both files.
ANCHORS: list[tuple[int, int, str]] = [
    (60, 17, "introduction: 'one of the students' / إعلم انّ واحدا من الطّلبة"),
    (75, 33, "'My dear beloved son and true friend' / إعلم أيها الولد والمحبّ العزيز"),
    (81, 38, "'Alamatu I'radil / علامة إعراض الله"),
    (86, 40, "'whoever passes forty' / و من جاوز الأربعين"),
    (93, 47, "Inna Ashaddan Nasi / أشدّ النّاس عذابا"),
    (96, 49, "Junayd seen in a dream / و روي أنّ الجنيد"),
    (104, 52, "'do not deprive yourself of deeds' / لا تكن من الأعمال مفلسا"),
    (177, 80, "Hasan al-Basri says / وقال الحسن البصريّ"),
    (252, 128, "Hasan al-Basri, the cold drink / الحسن البصريّ ... أعطي"),
    (295, 140, "the three sounds, the pre-dawn / وصوت المستغفرين بالأسحار"),
    (306, 150, "Luqman's testament / وصايا لقمان الحكيم لابنه"),
    (350, 184, "Shibli's four thousand / حكي أنّ الشّبلي"),
    (360, 192, "Hatim al-Asamm narrative / حاتما الأصمّ"),
    (386, 196, "first benefit / الفائدة الأولى"),
    (392, 201, "second benefit / الفائدة الثّانية"),
    (402, 209, "third benefit / الفائدة الثّالثة"),
    (412, 213, "fourth benefit / الفائدة الرّابعة"),
    (426, 219, "fifth benefit / الفائدة الخامسة"),
    (436, 223, "sixth benefit / الفائدة السّادسة"),
    (452, 226, "seventh benefit / الفائدة السّابعة"),
    (462, 230, "eighth benefit / الفائدة الثّامنة"),
    (474, 235, "Shafeeq's reply / فقال شقيق: وفقك الله تعالى"),
    (519, 266, "Tasawwuf has two qualities / أنّ التّصوّف له خصلتان"),
    (521, 274, "servitude / سألتني عن العبوديّة"),
    (525, 278, "reliance / سألتني عن التّوكّل"),
    (530, 281, "sincerity / سألتني عن الإخلاص"),
    (577, 313, "scholars as physicians / فحذاقة الطبيب"),
    (611, 374, "preaching / طريق الوعظ و النّصيحة"),
    (639, 383, "fourth admonition, gifts from rulers / (و الرّابع) ألاّ تقبل شيئا"),
    (690, 426, "the supplication / ألّهمّ إنّي أسألك من النّعمة تمامها"),
    (700, AR_LAST, "end of the treatise / و الحمد لله ربّ العالمين"),
]

PAD = 3  # Arabic lines of overlap on each side of a bucket.
_PAGE_RE = re.compile(r"<!--\s*PAGE\s*(\d+)\s*-->", re.IGNORECASE)


def english_to_arabic(en_line: int) -> float:
    """Piecewise-linear, clamped to the treatise's extent."""
    pts = [(e, a) for e, a, _ in ANCHORS]
    if en_line <= pts[0][0]:
        e0, a0 = pts[0]
        e1, a1 = pts[1]
        slope = (a1 - a0) / (e1 - e0)
        return max(AR_FIRST, a0 + (en_line - e0) * slope)
    for (e0, a0), (e1, a1) in zip(pts, pts[1:]):
        if e0 <= en_line <= e1:
            return a0 + (en_line - e0) * (a1 - a0) / (e1 - e0)
    return float(AR_LAST)


def main() -> int:
    ar_lines = ARABIC_SRC.read_text(encoding="utf-8").split("\n")
    en_lines = ENGLISH.read_text(encoding="utf-8").split("\n")

    # English page -> [start_line, end_line] (1-based, inclusive).
    starts: list[tuple[int, int]] = []
    for i, ln in enumerate(en_lines, start=1):
        m = _PAGE_RE.search(ln)
        if m:
            starts.append((int(m.group(1)), i))
    pages: dict[int, tuple[int, int]] = {}
    for idx, (pg, start) in enumerate(starts):
        end = starts[idx + 1][1] - 1 if idx + 1 < len(starts) else len(en_lines)
        pages[pg] = (start, end)

    out: list[str] = [
        "<!-- Arabic ground truth for ayyuhal-walad, re-bucketed under the ENGLISH",
        "     pagination of _system/source/text/refined-english.md so that",
        "     _book_compose._arabic_for can look a chapter's pages up directly.",
        "     Text is verbatim from _system/source/multi/ocr/arabic.md (Azure OCR of",
        "     the Arabic original, printed pp. 39-53), lines 11-441 — the treatise",
        "     only, with the neighbouring works trimmed at their explicit boundaries.",
        "     Buckets are anchor-aligned and padded. GENERATED — re-run",
        "     build-raw-extract.py beside this file to rebuild it; the anchor list and",
        "     the method live there. A page marker below is an ENGLISH page number,",
        "     not an Arabic one. -->",
        "",
    ]
    rows: list[tuple[int, int, int, int]] = []
    for pg in sorted(pages):
        en_start, en_end = pages[pg]
        a_start = int(round(english_to_arabic(en_start))) - PAD
        a_end = int(round(english_to_arabic(en_end))) + PAD
        a_start = max(AR_FIRST, a_start)
        a_end = min(AR_LAST, max(a_end, a_start))
        body = [ln for ln in ar_lines[a_start - 1 : a_end] if not ln.strip().startswith("<!-- page")]
        rows.append((pg, en_start, a_start, a_end))
        out.append(f"<!-- page {pg} -->")
        out.extend(body)
        out.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")

    arabic_re = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]{2,}")
    total_runs = len(arabic_re.findall(OUT.read_text(encoding="utf-8")))
    print(f"wrote {OUT}  ({total_runs} Arabic runs)")
    print(f"{'EngPg':>5} {'EngLn':>6} {'ArLines':>12} {'ArLen':>6}")
    for pg, en_start, a0, a1 in rows:
        print(f"{pg:>5} {en_start:>6} {f'{a0}-{a1}':>12} {a1 - a0 + 1:>6}")
    covered = set()
    for _, _, a0, a1 in rows:
        covered.update(range(a0, a1 + 1))
    missing = sorted(set(range(AR_FIRST, AR_LAST + 1)) - covered)
    print(f"\nArabic lines {AR_FIRST}-{AR_LAST} covered: {len(covered)}/{AR_LAST - AR_FIRST + 1}")
    print(f"UNCOVERED: {missing if missing else 'none — every line of the treatise reaches some page'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
