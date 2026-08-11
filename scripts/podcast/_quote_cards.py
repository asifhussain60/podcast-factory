#!/usr/bin/env python3
"""_quote_cards.py — the four-quotation-card contract, checked rather than remembered.

WHAT THIS GUARDS. On 2026-08-09 a quotation stopped being prose set apart and became
one of four CARDS — Qur'an, prophetic tradition, verse, and the saying that is the
default. Each is a tinted plate with a centred header, an outlined mark and its own ink,
and none of them has a border. Asif converged that design over a sample page before
anything touched the site, and that page is still on disk at
`plan-dashboard/public/_specimen-quote-tiers.html` (served at
`http://localhost:4322/_specimen-quote-tiers.html`). It is the APPROVED REFERENCE: what
the cards look like there is what the reading edition owes its reader.

WHY A CHECK EXISTS AT ALL. The design is spread across six files that nothing held
together — the rules in one stylesheet, the markup in two renderers that must agree, the
inlining step that puts the stylesheet into the PDF, and a per-book JSON in which a
person declares which quotation is which. Every one of them fails SILENTLY and in the
same direction: the card degrades to the default plate, or to no plate at all, and the
page still renders. `pf-compose-fix` is the tool that looks at a chapter and says what is
wrong with it, and until now it could report a chapter clean while every quotation in it
had lost its card.

THE SPECIMEN IS NOT MIRRORED BYTE-FOR-BYTE, DELIBERATELY. Its stylesheets are inlined
copies taken the day it was approved, and they have already drifted in ways that mean
nothing — a gradient reformatted onto one line, a `.q-cite` rule deleted the same day it
was drafted. Comparing the files would fire on formatting forever and be switched off
within a week. What is checked instead is the DESIGN the specimen shows: four cards,
four inks, no border, a header per kind, the Qur'an's gold rules, and the two-column
verse grid that collapses on its container. Those are the things whose absence a reader
would see.

NOTHING HERE REPAIRS ANYTHING. A missing CSS rule is a design change and belongs to
whoever is changing the design; an orphaned declaration cannot be re-keyed without
guessing which quotation a person meant. Both are reported and left standing, which is
the same contract `stale-provenance` had before its refresh existed.

Rule ids are `QC-NNN` and are cited, never restated — the wording lives here and in the
specimen's own comments.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

#: Repo root, from `scripts/podcast/_quote_cards.py`.
REPO = Path(__file__).resolve().parents[2]

#: The approved reference. Its URL on the dev server is the one Asif opens.
SPECIMEN = REPO / "plan-dashboard" / "public" / "_specimen-quote-tiers.html"
SPECIMEN_URL = "http://localhost:4322/_specimen-quote-tiers.html"

#: Where each half of the contract lives.
CSS = REPO / "plan-dashboard" / "src" / "styles" / "quote-typography.css"
PRINT_RENDERER = REPO / "plan-dashboard" / "scripts" / "lib" / "book-html.mjs"
SCREEN_RENDERER = REPO / "plan-dashboard" / "src" / "lib" / "reader" / "markdown.ts"
PDF_DRIVER = REPO / "plan-dashboard" / "scripts" / "render-book-pdf.mjs"

#: The four kinds, in the order the specimen presents them. `quran` is the audit's
#: answer and can never be declared by hand; the other three are declared by a person
#: in `_system/quote-kind.json` — see `plan-dashboard/scripts/lib/quote-kind.mjs`,
#: which is the one definition of both the id list and the key.
KINDS = ("quran", "hadith", "poem", "quote")

#: The kinds a person may declare. Mirrors `QUOTE_KIND_IDS`; `quran` is absent for the
#: reason that file gives — a second way to assert scripture is a second answer that has
#: to agree with the first.
DECLARABLE = ("hadith", "poem", "quote")

#: The ink token each kind's plate, header and Arabic are all mixed from. `quote` reads
#: `--q-said-ink` because the default card is the SAYING, which is what that token has
#: been called since before the cards existed; renaming it would be a rename, not a fix.
INK = {"quran": "q-quran-ink", "hadith": "q-hadith-ink", "poem": "q-poem-ink", "quote": "q-said-ink"}


def _rule(rule_id: str, guarantee: str, path: Path, requirements: list[tuple[str, str]]) -> dict:
    return {"id": rule_id, "guarantee": guarantee, "path": path, "requirements": requirements}


def _card_rules() -> list[dict]:
    """The contract, as (what a reader would lose, where it is written, what must be there).

    Each requirement is a label and a regex searched over the whole file. Regexes rather
    than a parse because the question is only ever "is this declaration still here": a CSS
    parser would buy precision this check has no use for and a dependency it should not
    have.
    """
    plate = "|".join(f"blockquote\\.k-{k}" for k in KINDS)
    return [
        _rule(
            "QC-010",
            "the four cards exist at all — a quotation is drawn as a Qur'an, a prophetic "
            "tradition, a verse or a saying",
            CSS,
            [(f".k-{kind}", rf"blockquote\.k-{kind}\b") for kind in KINDS],
        ),
        _rule(
            "QC-020",
            "every card is a plate and NOT a frame — an outline round a quotation reads as "
            "a UI control, a tinted plate reads as a page",
            CSS,
            [
                ("all four selectors share one plate rule", rf"(?s)({plate}).{{0,400}}border:\s*0\b"),
                ("the plate is rounded", r"border-radius:\s*\d"),
            ],
        ),
        _rule(
            "QC-030",
            "each card is tinted from its OWN ink, so a book that changes an ink moves its "
            "cards with it and nothing is kept in step by hand",
            CSS,
            [
                (
                    f".k-{kind} plate mixed from --{INK[kind]}",
                    rf"blockquote\.k-{kind}[^{{]*\{{[^}}]*color-mix\([^)]*var\(--{INK[kind]}\)",
                )
                for kind in KINDS
            ],
        ),
        _rule(
            "QC-040",
            "the four inks are declared — without one, a card's plate, header and Arabic all "
            "fall back together and two kinds become indistinguishable",
            CSS,
            [(f"--{token}", rf"--{token}\s*:\s*#") for token in dict.fromkeys(INK.values())],
        ),
        _rule(
            "QC-050",
            "each kind has its own header band with its own outlined mark",
            CSS,
            [(f".q-band--{kind} sets its mark", rf"\.q-band--{kind}[^{{]*\{{[^}}]*--q-orn-src:") for kind in KINDS],
        ),
        _rule(
            "QC-060",
            "the mark is drawn as a stroke through a mask, so it takes the ink of the card it "
            "sits in rather than carrying a colour of its own",
            CSS,
            [("\\.q-orn is masked", r"\.q-orn[^{]*\{[^}]*mask:\s*var\(--q-orn-src\)")],
        ),
        _rule(
            "QC-070",
            "the Qur'an card keeps the filled bar that heads it, carrying the chapter and "
            "verse — what set that card above the other three until 2026-08-11 was a pair of "
            "gold rules, and the bar replaced them",
            CSS,
            [
                (
                    "the bar is filled from --q-quran-bar",
                    r"\.q-band--quran[^{]*\{[^}]*background:\s*var\(--q-quran-bar\)",
                ),
                ("and reads in its own ink", r"\.q-band--quran[^{]*\{[^}]*color:\s*var\(--q-quran-bar-ink\)"),
                ("it bleeds to the card's edge", r"\.q-band--quran[^{]*\{[^}]*margin:\s*-"),
                ("and rounds off the card's top", r"\.q-band--quran[^{]*\{[^}]*border-radius:\s*8px 8px 0 0"),
                (
                    "the panel is framed in the same brown a step lighter",
                    r"blockquote\.k-quran[^{]*\{[^}]*border:\s*2px solid var\(--q-quran-bar-edge\)",
                ),
            ],
        ),
        _rule(
            "QC-075",
            "the other three cards name their kind at one end of the header and, when a person "
            "recorded one, the speaker at the other — an attribution is printed only where "
            "somebody wrote it down, and never inferred from the prose",
            CSS,
            [
                ("the speaker sits after the rule", r"\.q-by[^{]*\{[^}]*order:"),
                ("the rule runs between the two", r"\.q-band::after[^{]*\{[^}]*flex:\s*1"),
            ],
        ),
        _rule(
            "QC-080",
            "verse is set as two columns — the gutter running down the block is what makes a "
            "poem read AS a poem to someone who cannot read the words",
            CSS,
            [
                ("the grid is two equal columns", r"\.q-verse[^{]*\{[^}]*grid-template-columns:\s*1fr 1fr"),
                ("and runs right to left", r"\.q-verse[^{]*\{[^}]*direction:\s*rtl"),
                ("a lone hemistich spans both", r"\.q-verse \.bayt-solo[^{]*\{[^}]*grid-column:"),
            ],
        ),
        _rule(
            "QC-090",
            "the collapse to one column is keyed to the COLUMN, not the window — a poem sits "
            "in a narrow measure on a wide screen all the time (the editor pane, a printed page)",
            CSS,
            [
                ("the poem card is a container", r"blockquote\.k-poem[^{]*\{[^}]*container-type:\s*inline-size"),
                ("and the collapse is a container query", r"(?s)@container[^{]*\{\s*\.q-verse"),
            ],
        ),
        _rule(
            "QC-100",
            "the cards stay legible on dark paper — the Composer's Kindle setting, where the "
            "base inks sit at about 1.6:1 and are not readable",
            CSS,
            [
                (f".k-{kind} lifts its ink on dark paper", rf'data-paper="dark"[^{{]*blockquote\.k-{kind}')
                for kind in KINDS
            ],
        ),
        _rule(
            "QC-110",
            "the PRINT renderer still stamps the markup those rules select — the PDF is the "
            "deliverable, and a rule with nothing to select fails silently",
            PRINT_RENDERER,
            [
                ("the card class", r'`\s*k-\$\{kind\}`|" k-quran"'),
                ("the header band", r"q-band q-band--\$\{kind\}"),
                ("the outlined mark", r'class="q-orn"'),
                ("the speaker", r'class="q-by"'),
                ("the verse grid", r'class="q-verse"'),
                ("the lone hemistich", r"bayt-solo"),
            ],
        ),
        _rule(
            "QC-120",
            "the SCREEN renderer stamps the same markup — the Compose tab is where the book is "
            "verified, so a card that differs there is a verification against the wrong page",
            SCREEN_RENDERER,
            [
                ("the header band", r"q-band q-band--\$\{kind\}"),
                ("the outlined mark", r'class="q-orn"'),
                ("the speaker", r'class="q-by"'),
                ("the verse grid", r'class="q-verse"'),
                ("the lone hemistich", r"bayt-solo"),
            ],
        ),
        _rule(
            "QC-130",
            "the PDF driver still inlines the stylesheet — the print page loads no stylesheet "
            "of its own, so dropping this line removes every card from the printed book",
            PDF_DRIVER,
            [("quote-typography.css is inlined", r'"quote-typography\.css"')],
        ),
        _rule(
            "QC-140",
            "the approved reference still shows all four tiers, so what Asif checks against "
            f"cannot quietly lose one ({SPECIMEN_URL})",
            SPECIMEN,
            [(f"the {kind} card", rf"k-{kind}\b") for kind in KINDS],
        ),
    ]


def card_rule_findings() -> list[tuple[str, str, str]]:
    """(rule id, file, what is missing) for every part of the contract not on disk.

    Empty means the cards the specimen shows can still be drawn. This reads the repo,
    not the book — the same answer for every slug, which is why `compose_fix` prints it
    once above the chapters rather than per chapter.
    """
    findings: list[tuple[str, str, str]] = []
    for rule in _card_rules():
        path: Path = rule["path"]
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            findings.append((rule["id"], _rel(path), "the file is missing"))
            continue
        for label, pattern in rule["requirements"]:
            if not re.search(pattern, text):
                findings.append((rule["id"], _rel(path), label))
    return findings


def print_quote_card_findings(report: dict) -> None:
    """Both halves of the card contract, for `compose_fix`'s report.

    Lives here rather than in the caller so the wording of a rule and the wording of its
    finding cannot drift apart. Printed above the chapters because neither half is
    chapter-scoped, and printed on every run rather than behind a flag — a check nobody
    sees until they ask for it is a check that does not find anything.
    """
    broken = report.get("quote_card_rules") or []
    if broken:
        print(
            f"\n  quote-card rules: {len(broken)} part(s) of the approved card design are no longer\n"
            "  on disk. Every one fails silently — the card degrades to the default plate, or to\n"
            f"  no plate at all, and the page still renders. Reference: {SPECIMEN_URL}"
        )
        for rule_id in dict.fromkeys(hit[0] for hit in broken):
            print(f"      {rule_id}  {guarantee_for(rule_id)}")
            for _, path, missing in (h for h in broken if h[0] == rule_id):
                print(f"          missing from {path}: {missing}")

    orphans = report.get("orphaned_quote_kind") or []
    if orphans:
        print(
            f"\n  orphaned-quote-kind: {len(orphans)} quotation(s) a person marked as a prophetic\n"
            "  tradition, a verse or a saying whose declaration no longer matches the page. Each\n"
            "  one now prints in the default card and a verse loses its two columns. Not repaired:\n"
            "  re-keying means choosing which quotation was meant."
        )
        for chapter_key, line, kind, why in orphans[:5]:
            print(f"      {kind:7} {line[:52]}")
            print(f"              in {chapter_key!r} — {why}")


def guarantee_for(rule_id: str) -> str:
    """The one-line reason a rule exists, for a report that has to explain itself."""
    for rule in _card_rules():
        if rule["id"] == rule_id:
            return rule["guarantee"]
    return ""


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


# ── the per-book half: declarations that no longer point at anything ──────────


def quote_kind_key(lines: list[str]) -> str:
    """A quotation's key: its first non-empty line, trimmed.

    MIRRORS `quoteKindKey` in `plan-dashboard/scripts/lib/quote-kind.mjs`, and takes the
    block's RAW LINES for the reason that file gives at length: both renderers join a
    quotation's lines into paragraphs before rendering, so a three-line poem is ONE
    paragraph and keying on it asks for a string no human ever wrote.
    """
    for line in lines:
        text = str(line or "").strip()
        if text:
            return text
    return ""


def read_quote_kind(book_dir: Path) -> dict[str, dict[str, str]]:
    """`_system/quote-kind.json` → {chapter key: {first line: kind}}, or {}.

    Unreadable, absent or malformed yields {} — the same tolerance the reader has, and
    for the same reason: an edition draws every quotation in the default card rather
    than failing to render.

    TWO FORMS, and both are read: `"…": "hadith"` is schema v1, and
    `"…": {"kind": "hadith", "by": "The Prophet"}` adds the speaker the card prints at
    the right of its header. MIRRORS `readQuoteKind` in
    plan-dashboard/scripts/lib/quote-kind.mjs, which is where the two forms are
    described at length. Only the KIND is kept here: everything downstream of this
    function asks which card a quotation is drawn in, and nothing asks who said it —
    but a reader that understood only the old form would have dropped every declaration
    written in the new one and reported the whole book as un-declared.
    """
    path = book_dir / "_system" / "quote-kind.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: dict[str, dict[str, str]] = {}
    for chapter, declarations in (raw.get("chapters") or {}).items():
        if not isinstance(declarations, dict):
            continue
        kept = {}
        for line, declared in declarations.items():
            kind = declared if isinstance(declared, str) else (declared or {}).get("kind")
            if kind in DECLARABLE:
                kept[str(line).strip()] = kind
        if kept:
            out[str(chapter)] = kept
    return out


def orphaned_quote_kinds(book_dir: Path) -> list[tuple[str, str, str, str]]:
    """(chapter key, first line, declared kind, why) for declarations pointing at nothing.

    A declaration is filed under its quotation's own first line, inside its chapter's
    Composer key. Edit either and the declaration stops matching: the block silently
    reverts to the default saying card, which is the conservative direction — it never
    dresses a saying as scripture — but it is still the human's decision quietly
    discarded. A verse loses its two columns and prints as a ragged block.

    THIS TOOL IS ONE OF THE THINGS THAT CAUSES IT. `compose_fix --fix` rewrites chapter
    text: deleting a duplicated Arabic run out of the top of a blockquote re-keys every
    declaration under it. That is the argument for checking it here rather than in a
    site gate — the repair and the damage are one command apart.

    Never repaired. Re-keying means choosing which quotation a person meant, and on a
    religious edition an inferred attribution is a claim nobody made.
    """
    from _book_defects import blocks, chapters
    from _book_edits import anchor_key

    declared = read_quote_kind(book_dir)
    if not declared:
        return []
    try:
        md = (book_dir / "book" / "book.md").read_text(encoding="utf-8")
    except OSError:
        return []

    live: dict[str, set[str]] = {}
    for heading, body in chapters(md):
        keys = {
            quote_kind_key([line.lstrip(">").strip() for line in lines])
            for kind, lines in blocks(body)
            if kind == "quote"
        }
        live[anchor_key(heading)] = {k for k in keys if k}

    orphans: list[tuple[str, str, str, str]] = []
    for chapter_key, declarations in declared.items():
        if chapter_key not in live:
            for line, kind in declarations.items():
                orphans.append((chapter_key, line, kind, "no chapter has this key any more"))
            continue
        for line, kind in declarations.items():
            if line not in live[chapter_key]:
                orphans.append((chapter_key, line, kind, "no quotation in that chapter opens with this line"))
    return orphans
