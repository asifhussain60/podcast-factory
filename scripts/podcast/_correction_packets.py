"""Correction packets and the deterministic gates that run before any model does.

A packet is everything a reviewer needs to judge ONE correction, assembled from
disk and the D1 row -- never by asking a model to go and find things (design
9b). It is small, reproducible and auditable: you can read exactly what the
reviewer was shown, and the same inputs always give the same `packet_hash`, so a
verdict made against a proposal that has since been edited is recognisably
stale.

The gates are the cheap, certain half of the workflow. They reuse what the repo
already enforces on every other prose route (`_vowelling`, `_mushaf`,
`_book_voice_gates`, `_book_edits`) instead of restating any of it, so a
correction cannot get past a check a Composer edit would have failed. A gate
failure is a verdict with NO model call: a correction that cannot be resolved to
one place cannot be reviewed by anyone, and telling the moderator so is the
cheapest feedback there is.

`is_quranic` and the Arabic marks-only gate exist because a "typo fix" on
scripture is not a typo fix. A Qur'anic letter change is never sent to a model
and never applied by a script -- it goes to a person.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import _book_edits
from _correction_db import strip_html
from _correction_gates import (  # noqa: F401  (re-exported: the packet module is the public face)
    Gate,
    _arabic_letters,
    _arabic_runs,
    arabic_gate,
    frame_gate,
    gate_summary,
    has_arabic,
    is_quranic_quote,
    quran_gate,
    retention_gate,
    substitution_gates,
    verdict_from_gates,
    word_retention,
)
from _correction_text import (
    BookChapter,
    Hit,
    block_span,
    block_texts,
    find_chapter,
    flatten,
    locate_reader,
    locate_source,
    normalize_text,
    paragraph_of,
    read_chapters,
    spans_overlap,
)

SCHEMA = "podcast.correction-packet/v1"

#: A spoken-lane book's prose is timed against a recording, so a correction may
#: not rewrite more of a chapter than this leaves untouched. The same number the
#: Composer path enforces (`_verbatim_correct`).
SPOKEN_RETENTION_FLOOR = 0.90

#: Buckets whose prose is timed against audio.
SPOKEN_BUCKETS = frozenset({"Sessions", "Audiobook"})

#: Statuses a correction can still change in -- the "live" set for overlap.
LIVE_STATUSES = ("suggested", "open", "accepted")

#: Largest source excerpt embedded in a packet, per source kind.
SOURCE_EXCERPT_CHARS = 8000
#: Pages either side of the estimated page that are included.
SOURCE_PAGE_WINDOW = 1

_PAGE_MARKER_RE = re.compile(r"<!--\s*page\s+(\d+)\s*-->")


# ---------------------------------------------------------------------------
# Book context (loaded once per run)
# ---------------------------------------------------------------------------


def _read_pages(path: Path) -> dict[int, str]:
    """`<!-- page N -->`-delimited text, by page number. Empty if the file is absent."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    parts = _PAGE_MARKER_RE.split(text)
    pages: dict[int, str] = {}
    # split with one capture group -> [pre, n1, body1, n2, body2, ...]
    for i in range(1, len(parts) - 1, 2):
        pages[int(parts[i])] = parts[i + 1].strip()
    return pages


def text_quality(text: str) -> str:
    """clean | noisy | unreliable -- how far a scan's text can be trusted.

    Delegates to `_listener_source_ocr.scan_quality`, the SAME heuristic that rates the scan for the
    moderators' Source pane, so the badge a moderator sees and the quality the reviewer is told can
    never disagree. Only the guard for a page too short to judge lives here: a near-empty page is
    not "clean", it is nothing.
    """
    from _listener_source_ocr import scan_quality

    if len("".join(text.split())) < 40:
        return "unreliable"
    return scan_quality([text])


def quality_override(book_dir: Path) -> str | None:
    """A person's verdict on the scan, from `_system/source/ocr/quality.json`.

    Read by `_listener_source_ocr` — the one place that knows the file's format — so the Source
    pane and the reviewer are told the same thing. A handwritten scan can produce plausible
    letters, no heuristic reading the text alone will call it noisy, and the override wins outright.
    """
    from _listener_source_ocr import _override

    return _override(Path(book_dir))


@dataclass
class BookContext:
    book_dir: Path
    slug: str
    chapters: list[BookChapter]
    rules: dict[str, Any]
    flags: list[dict]
    glossary: list[dict]
    crosswalk: list[dict]
    scan_pages: dict[int, str]
    extracted_pages: dict[int, str]
    composer_keys: set[str]
    composer_edits: list[dict]
    lane_text: dict[str, str] = field(default_factory=dict)  # chapters/*.txt, normalised

    @property
    def spoken(self) -> bool:
        return bool(self.rules.get("spoken_lane"))


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def book_rules(book_dir: Path) -> dict[str, Any]:
    """The book's narrative rules, read through the same knob readers the pipeline uses."""
    import _pipeline_flags as pf

    rules: dict[str, Any] = {"lane": Path(book_dir).parent.name}
    cfg = pf._read_series_config(Path(book_dir))
    rules["content_profile"] = str(cfg.get("content_profile") or "")
    rules["deliverable_mode"] = str(cfg.get("deliverable_mode") or "")
    for key, fn in (
        ("narrative_frame", pf.narrative_frame),
        ("book_voice", pf.book_voice),
        ("narrator_subject", pf.narrator_subject),
        ("source_medium", pf.source_medium),
    ):
        try:
            rules[key] = fn(Path(book_dir), cfg)
        except Exception as exc:  # a bad config must not stop a review; the value is just unknown
            rules[key] = ""
            rules.setdefault("unreadable", []).append(f"{key}: {exc}")
    rules["spoken_lane"] = rules["lane"] in SPOKEN_BUCKETS or rules.get("source_medium") == pf.SOURCE_AUDIO_LECTURE
    return rules


def load_context(book_dir: Path, slug: str | None = None) -> BookContext:
    from _glossary_io import load_glossary

    book_dir = Path(book_dir)
    system = book_dir / "_system"
    try:
        glossary, _ = load_glossary(system / "glossary.yml") if (system / "glossary.yml").exists() else ([], {})
    except Exception:
        glossary = []
    flags = _load_json(system / "arabic-verify-flags.json", [])
    cw = _load_json(book_dir / "book" / "source-crosswalk.json", {})
    lane_text: dict[str, str] = {}
    for f in sorted((book_dir / "chapters").glob("*.txt")) if (book_dir / "chapters").is_dir() else []:
        lane_text[f.name] = normalize_text(f.read_text(encoding="utf-8", errors="replace"))
    edits = _book_edits.load_edits(book_dir).get("edits", [])
    return BookContext(
        book_dir=book_dir,
        slug=slug or book_dir.name,
        chapters=read_chapters(book_dir),
        rules=book_rules(book_dir),
        flags=flags if isinstance(flags, list) else [],
        glossary=glossary,
        crosswalk=list(cw.get("chapters", [])) if isinstance(cw, dict) else [],
        scan_pages=_read_pages(system / "source" / "ocr" / "raw-extract.md"),
        extracted_pages=_read_pages(system / "source" / "text" / "refined-english.md"),
        composer_keys=_book_edits.edited_chapter_keys(book_dir),
        composer_edits=edits,
        lane_text=lane_text,
    )


# ---------------------------------------------------------------------------
# Source span
# ---------------------------------------------------------------------------


def crosswalk_entry(ctx: BookContext, chapter: BookChapter) -> dict | None:
    """The crosswalk row for a chapter: by heading key first, then by printed number.

    Key first because it is identity; number second because the crosswalk spells
    some titles with diacritics the book heading does not ("Rum" / "Rum").
    """
    for e in ctx.crosswalk:
        if _book_edits.anchor_key(str(e.get("title", ""))) == chapter.key:
            return e
    if chapter.number is not None:
        for e in ctx.crosswalk:
            if e.get("index") == chapter.number:
                return e
    return None


def _window(pages: list[int], center: int) -> list[int]:
    i = min(range(len(pages)), key=lambda k: abs(pages[k] - center))
    return pages[max(0, i - SOURCE_PAGE_WINDOW) : i + SOURCE_PAGE_WINDOW + 1]


def source_spans(
    ctx: BookContext,
    chapter: BookChapter,
    *,
    fraction: float,
    flag_page: int | None,
) -> list[dict]:
    """The source text behind a passage, one entry per kind available on disk.

    The chapter's page range comes from the crosswalk. Inside it the passage is
    located by a flag's recorded page when one matches, else PROPORTIONALLY by
    where the paragraph sits in the chapter -- an estimate, labelled as one, and
    widened by a page each side. Sending the whole chapter's source would be
    correct and would defeat the point of a small packet.
    """
    entry = crosswalk_entry(ctx, chapter)
    if not entry:
        return []
    out: list[dict] = []
    for kind, pages_map, key in (
        ("scan", ctx.scan_pages, "arabic_source_pages"),
        ("extracted", ctx.extracted_pages, "source_pages"),
    ):
        chapter_pages = [p for p in (entry.get(key) or entry.get("source_pages") or []) if p in pages_map]
        if not chapter_pages:
            continue
        chapter_pages = sorted(chapter_pages)
        if flag_page is not None and flag_page in chapter_pages:
            chosen, how = _window(chapter_pages, flag_page), "flag-page"
        elif len(chapter_pages) <= 2 * SOURCE_PAGE_WINDOW + 1:
            chosen, how = chapter_pages, "whole-chapter"
        else:
            est = chapter_pages[min(len(chapter_pages) - 1, int(fraction * len(chapter_pages)))]
            chosen, how = _window(chapter_pages, est), "proportional"
        text = "\n\n".join(f"[page {p}]\n{pages_map[p]}" for p in chosen)
        out.append(
            {
                "kind": kind,
                "pages": chosen,
                "chapter_pages": [chapter_pages[0], chapter_pages[-1]],
                "selection": how,
                "quality": (quality_override(ctx.book_dir) or text_quality(text)) if kind == "scan" else "clean",
                "text": text[:SOURCE_EXCERPT_CHARS],
                "truncated": len(text) > SOURCE_EXCERPT_CHARS,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Packet
# ---------------------------------------------------------------------------


def _term_in(text_lower: str, term: str) -> bool:
    term = term.strip().lower()
    return len(term) >= 3 and re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text_lower) is not None


def vocabulary(ctx: BookContext, *texts: str, limit: int = 25) -> list[dict]:
    """Glossary entries for terms present in the given texts, so a reviewer does not
    'correct' a deliberate rendering."""
    from _arabic_coverage import normalize_arabic

    blob = "\n".join(texts)
    lower = blob.lower()
    ar_blob = normalize_arabic(blob)
    found: list[dict] = []
    for e in ctx.glossary:
        terms = [str(e.get("phonetic") or ""), str(e.get("transliteration") or "")]
        script = str(e.get("arabic_script") or "")
        hit = any(_term_in(lower, t) for t in terms if t)
        if not hit and script:
            sk = normalize_arabic(script)
            hit = len(sk) >= 4 and sk in ar_blob
        if hit:
            found.append(
                {k: e[k] for k in ("phonetic", "transliteration", "arabic_script", "english_equivalent") if e.get(k)}
            )
        if len(found) >= limit:
            break
    return found


def _overlaps_stored(a: dict, b: dict) -> bool:
    return (
        a.get("anchor_key") == b.get("anchor_key")
        and a.get("block_index") == b.get("block_index")
        and int(a["start_offset"]) < int(b["end_offset"])
        and int(b["start_offset"]) < int(a["end_offset"])
    )


def build_packet(ctx: BookContext, correction: dict, all_corrections: list[dict]) -> dict:
    """One self-contained packet for one correction. Pure function of its inputs."""
    quote = str(correction["quote"])
    proposed = str(correction["proposed_text"])
    kind = str(correction.get("kind") or "other")
    key = str(correction["anchor_key"])
    chapter = find_chapter(ctx.chapters, key)
    gates: list[Gate] = []

    passage: dict[str, Any] = {"anchor_key": key, "chapter_title": chapter.heading if chapter else None}
    old_para = new_para = ""
    fraction = 0.5
    hits: list[Hit] = []
    if chapter is None:
        gates.append(Gate("quote-resolves", "no", "the chapter no longer exists in the book"))
    else:
        hits = locate_reader(chapter.body, quote)
        if len(hits) == 1:
            gates.append(Gate("quote-resolves", "ok", "the quote is found exactly once in its chapter"))
        elif not hits:
            gates.append(
                Gate("quote-resolves", "no", "the quote is not in the chapter any more (the text has changed)")
            )
        else:
            gates.append(
                Gate(
                    "quote-resolves",
                    "no",
                    f"the quote matches {len(hits)} places in the chapter -- select a longer phrase",
                )
            )

    if chapter is not None and len(hits) == 1:
        h = hits[0]
        blocks = block_texts(chapter.body)
        fraction = (h.block_index + 0.5) / max(len(blocks), 1)
        lo, hi = max(0, h.block_index - 1), min(len(blocks), h.block_index + 2)
        paras = []
        for i in range(lo, hi):
            role = "target" if i == h.block_index else ("before" if i < h.block_index else "after")
            paras.append({"index": i, "role": role, "text": blocks[i]})
        target = blocks[h.block_index]
        passage.update(
            block_index=h.block_index,
            paragraphs=paras,
            marked=target[: h.start] + "[[" + target[h.start : h.end] + "]]" + target[h.end :],
        )
        src_hits = locate_source(chapter.body, quote)
        if len(src_hits) == 1:
            old_para = paragraph_of(chapter.body, *src_hits[0])
            new_para = old_para.replace(_first_match(old_para, quote), proposed, 1)
        else:
            old_para = target
            new_para = target[: h.start] + proposed + target[h.end :]
            gates.append(
                Gate(
                    "applies-cleanly",
                    "warn",
                    "the quote spans formatting in the source text, so a script cannot splice it; it will need a Composer edit by hand",
                )
            )

    # Overlap with another live correction, by the stored anchors (what moderators see).
    others = [c for c in all_corrections if c["id"] != correction["id"] and c.get("status") in LIVE_STATUSES]
    clash = [c["id"] for c in others if _overlaps_stored(correction, c)]
    if clash:
        gates.append(Gate("overlap", "no", f"overlaps another live correction ({', '.join(clash[:3])})"))
    else:
        gates.append(Gate("overlap", "ok", "no other live correction touches this passage"))

    if old_para:
        gates.extend(
            substitution_gates(
                old_para=old_para,
                new_para=new_para,
                quote=quote,
                proposed=proposed,
                kind=kind,
                frame=ctx.rules.get("narrative_frame"),
                narrator_subject=ctx.rules.get("narrator_subject", ""),
            )
        )
    else:  # the script gates still apply to the words alone, with no paragraph to compare
        for g in (quran_gate(quote, proposed), arabic_gate(quote, proposed, kind)):
            if g:
                gates.append(g)

    if chapter is not None and ctx.spoken and old_para:
        new_body = chapter.body.replace(old_para, new_para, 1)
        gates.append(retention_gate(chapter.body, new_body))

    if chapter is not None and chapter.key in ctx.composer_keys:
        gates.append(
            Gate(
                "composer-edit",
                "warn",
                "this chapter already carries a Composer edit; the correction lands on top of it",
            )
        )

    # Prior knowledge: a settled point should not be re-litigated.
    nq = normalize_text(quote).lower()
    np_ = normalize_text(proposed).lower()
    matched_flags = []
    for f in ctx.flags:
        if chapter is None or f.get("chapter") != chapter.number:
            continue
        fq = normalize_text(str(f.get("quote", ""))).lower()
        fs = normalize_text(str(f.get("suggested", ""))).lower()
        if fq and (fq in nq or nq in fq) or (fs and (fs in np_ or np_ in fs)):
            matched_flags.append(
                {k: f.get(k) for k in ("sev", "category", "quote", "suggested", "certainty", "page", "status", "note")}
            )
    flag_page = next((f["page"] for f in matched_flags if isinstance(f.get("page"), int)), None)

    spans = source_spans(ctx, chapter, fraction=fraction, flag_page=flag_page) if chapter is not None else []
    if not spans:
        gates.append(Gate("source-span", "warn", "no source text could be matched to this chapter"))
    else:
        gates.append(Gate("source-span", "ok", f"source found ({', '.join(s['kind'] for s in spans)})"))

    prior_edit = next((e for e in ctx.composer_edits if chapter and e.get("chapter_key") == chapter.key), None)
    near = [
        {"id": c["id"], "status": c["status"], "quote": c["quote"], "proposed_text": c["proposed_text"]}
        for c in others
        if c.get("anchor_key") == key and abs(int(c.get("block_index", 0)) - int(correction.get("block_index", 0))) <= 1
    ]

    other_lane = [name for name, text in ctx.lane_text.items() if nq and nq in text.lower()]
    primary = spans[0]["kind"] if spans else "none"

    claim = {
        "quote": quote,
        "proposed_text": proposed,
        "kind": kind,
        "rationale": strip_html(str(correction.get("rationale_html") or "")),
        "raised_by": correction.get("raised_by"),
        "raised_at": correction.get("raised_at"),
        "origin": correction.get("origin"),
        "certainty": correction.get("certainty"),
    }
    source = {"kind": primary, "spans": spans}
    hash_input = json.dumps({"claim": claim, "passage": passage, "source": source}, sort_keys=True, ensure_ascii=False)
    return {
        "schema": SCHEMA,
        "correction_id": correction["id"],
        "correction_updated": correction.get("updated_at"),
        "slug": ctx.slug,
        "claim": claim,
        "passage": passage,
        "source": source,
        "book_rules": {k: v for k, v in ctx.rules.items() if k != "unreadable"},
        "vocabulary": vocabulary(ctx, passage.get("marked", ""), quote, proposed, *(s["text"] for s in spans)),
        "prior_knowledge": {
            "audit_flags": matched_flags,
            "composer_edit": {"present": prior_edit is not None, "saved_at": (prior_edit or {}).get("saved_at")},
            "other_corrections": near,
        },
        "is_quranic": is_quranic_quote(quote),
        "other_lane": {
            "appears_in": other_lane,
            "note": "chapters/*.txt feeds the podcast, not book.md" if other_lane else "",
        },
        "gates": [g.as_dict() for g in gates],
        "packet_hash": hashlib.sha256(hash_input.encode("utf-8")).hexdigest(),
    }


def _first_match(paragraph: str, quote: str) -> str:
    """The exact text in `paragraph` that the whitespace-flexible quote matched."""
    from _correction_text import _flexible

    m = _flexible(quote).search(paragraph)
    return m.group(0) if m else quote


def gates_of(packet: dict) -> list[Gate]:
    return [Gate(**g) for g in packet["gates"]]


def packets_dir(book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / "corrections" / "packets"


def write_packet(book_dir: Path, packet: dict) -> Path:
    path = packets_dir(book_dir) / f"{packet['correction_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(packet, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


__all__ = [
    "Gate",
    "BookContext",
    "build_packet",
    "load_context",
    "verdict_from_gates",
    "gate_summary",
    "substitution_gates",
    "retention_gate",
    "word_retention",
    "write_packet",
    "block_span",
    "flatten",
    "spans_overlap",
]
