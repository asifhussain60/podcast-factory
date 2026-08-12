"""_annotation_policy.py — which Arabic terms deserve an inline annotation, and how.

The rule, in Asif's words (2026-07-22): annotations "should ONLY be used once and
intelligently. Every single Arabic term should not have a translation with it.
Only where it helps the reader, and then it should not be repeated." Terms with a
recognized English form — Mount Sinai, Quran, hadith, famous names — simply speak
English.

That is also how professional reading editions handle this material. The working
conventions (Chicago-style practice for translated scholarly trade books):

  * a technical term the book TEACHES is introduced once — name, script — and
    thereafter used plainly; the glossary, not the running text, carries detail;
  * a term with an established English form is printed in that form with no
    apparatus at all;
  * famous persons take their conventional English spelling; only an obscure name
    earns script, once, in citation form;
  * incidental foreign words get nothing.

The pipeline had the opposite behaviour: every glossary term with script was
annotated at first mention of every chapter, mechanically — so Joseph, Sinai and
Adam carried script they did not need while the book's own vocabulary lost its
name entirely.

THE SHAPE. Each glossary entry may carry two new fields:

    annotation_class:    teach | familiar | name | silent | work_title
    english_equivalent:  the recognized English form, when one exists

The CLASSIFICATION is a judgment call, so it is made by a model — ONCE per book —
and written into `_system/glossary.yml` where a human can read and override every
line (the learning-loop rule: suggestions are visible and durable, never silent).
The APPLICATION is deterministic: `_book_inline_arabic` reads the classes and
never consults a model. The two never blur: the model proposes a class and an
English equivalent; it can never touch `arabic_script`, which stays curated —
that is what keeps fabricated spellings structurally impossible here.

What each class means downstream (enforced in `_book_inline_arabic`):

    teach      first use IN THE BOOK gets the SCRIPT — `his gate (باب)` when the
               prose glosses the term, `the natiq (الناطق)` when the prose uses
               the term itself. Never repeated. (Until 2026-08-02 a gloss kept
               the romanisation beside the script, `(bab, باب)`; Asif's rule is
               now zero Latin-script Arabic inside a gloss, and the script is
               vowelled by 5a-vowelling so it reads for someone who needs it.)
    familiar   no annotation, ever. The English form IS the word.
    name       first use in the book gets the script appended, once. The
               romanisation stays — it is how an English reader says the name.
    silent     no annotation, ever.
    work_title a book the text CITES. Never annotated — and where the prose
               already glosses it in English, `_book_work_titles` prints that
               English alone: `Ihya al-Ulum ad-Din (Revival of the Knowledge of
               the Path to God)` becomes `Revival of the Knowledge of the Path to
               God`. Its own class rather than `silent` because silence would
               only stop the script being added and still leave the reader two
               names for one book, the unreadable one first (Asif, 2026-08-05).
    (absent)   legacy behaviour — first use per chapter — so books that predate
               the policy compose exactly as before until they are classified.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

import yaml
from _glossary_io import load_glossary, save_glossary

ANNOTATION_CLASSES = ("teach", "familiar", "name", "silent", "work_title")
_CLASS_FIELD = "annotation_class"
_EQUIV_FIELD = "english_equivalent"
_REASON_FIELD = "annotation_reason"
_REPORT_NAME = "annotation-policy-report.json"
_CLASSIFY_TIMEOUT = 900
#: Terms per classifier call. Mirrors fill_glossary_arabic.BATCH_SIZE — the same
#: reasoning (a prompt small enough to finish inside the timeout), and the same
#: number so the two batching schemes are not gratuitously different.
_CLASSIFY_BATCH = 40


class AnnotationPolicyError(ValueError):
    """A policy field nobody recognises. Raised, not defaulted, for the same
    reason the pipeline knobs raise: a typo here silently changes what prints."""


def load_policy(book_dir: Path) -> dict[str, dict[str, str]]:
    """phonetic -> {"class": ..., "english_equivalent": ...} for classified entries.

    Entries without a class are simply absent — the annotation pass treats them
    with its legacy behaviour. An unrecognised class raises.
    """
    entries = _load_glossary_entries(book_dir)
    policy: dict[str, dict[str, str]] = {}
    for e in entries:
        cls = str(e.get(_CLASS_FIELD) or "").strip().lower()
        if not cls:
            continue
        if cls not in ANNOTATION_CLASSES:
            raise AnnotationPolicyError(
                f"glossary.yml: {e.get('phonetic')!r} has {_CLASS_FIELD}: {cls!r} — "
                f"not one of {', '.join(ANNOTATION_CLASSES)}"
            )
        policy[str(e.get("phonetic") or "").strip()] = {
            "class": cls,
            "english_equivalent": str(e.get(_EQUIV_FIELD) or "").strip(),
        }
    return policy


def _load_glossary_entries(book_dir: Path) -> list[dict[str, Any]]:
    path = Path(book_dir) / "_system" / "glossary.yml"
    try:
        entries, _top = load_glossary(path)
    except Exception:
        return []
    return entries


def _usage_count(book_md_text: str, phonetic: str) -> int:
    if not phonetic:
        return 0
    return len(re.findall(rf"(?<![\w-]){re.escape(phonetic)}(?![\w'’-])", book_md_text))


def _classifier_prompt(book_title: str, rows: list[dict[str, Any]]) -> str:
    return f"""You are the terminology editor for a professional English reading edition of an
Arabic scholarly work: "{book_title}". Classify each glossary term below into exactly one
annotation class, following the conventions professional translators use for trade editions
of this material:

  teach     A technical term this book itself TEACHES — its own doctrinal/technical
            vocabulary that an interested reader should be able to NAME and look up.
            It will be introduced once, in Arabic script, and then used plainly.
  familiar  Has an established English form that educated readers already recognize
            (e.g. Quran, hadith, imam as a common noun, Mount Sinai, Kaaba, famous
            prophets and caliphs). Prints as plain English with no apparatus.
  name      A person or place WITHOUT a familiar English form. The romanisation stays
            (it is how the reader says it) and the Arabic script appears once.
  silent    An annotation would not help the reader at all (grammatical fragments,
            phrases that are translated in running prose anyway, terms too minor to
            introduce formally).
  work_title The title of a BOOK the text cites — the author's other works, or any
            work named in passing. Never annotated, and where the prose already
            gives an English translation beside it the edition prints only that
            translation. Use this for every cited work, never `name`: a book is
            not a person whose romanisation is how a reader says them.

Rules:
- Judge by what helps a reader with no Arabic. When in doubt between teach and silent,
  ask: would a careful reader want to cite or search this term? If yes, teach.
- famous figures of scripture and early Islam are familiar; obscure transmitters,
  local figures and the author are name.
- For familiar terms, give the recognized English form in "english_equivalent"
  (e.g. "Mount Sinai", "Quran"). Otherwise leave it empty.
- Do NOT output Arabic script anywhere. You are classifying, not transcribing.
- Every input term MUST appear exactly once in the output.

TERMS (JSON): each has the romanised term, its English sense when recorded, the context
of its first appearance, and how often it occurs in the book.
{json.dumps(rows, ensure_ascii=False, indent=1)}

OUTPUT: a JSON array only, no prose, one object per term:
  {{"phonetic": "...", "class": "teach|familiar|name|silent|work_title",
    "english_equivalent": "...", "reason": "<one short sentence>"}}"""


def _parse_classification(raw: str) -> list[dict[str, str]]:
    """The model's JSON array, tolerantly extracted, strictly validated."""
    text = (raw or "").strip()
    match = re.search(r"\[.*\]", text, re.S)
    if not match:
        raise AnnotationPolicyError("classifier returned no JSON array")
    items = json.loads(match.group(0))
    if not isinstance(items, list):
        raise AnnotationPolicyError("classifier output is not a list")
    out: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        cls = str(item.get("class") or "").strip().lower()
        if cls not in ANNOTATION_CLASSES:
            raise AnnotationPolicyError(f"classifier proposed unknown class {cls!r} for {item.get('phonetic')!r}")
        equiv = str(item.get("english_equivalent") or "").strip()
        # The model must never smuggle script into the glossary through this
        # field — script stays curated. Reject rather than strip, so a confused
        # response is visible instead of silently half-used.
        if re.search(r"[؀-ۿ]", equiv):
            raise AnnotationPolicyError(f"classifier put Arabic in english_equivalent for {item.get('phonetic')!r}")
        out.append(
            {
                "phonetic": str(item.get("phonetic") or "").strip(),
                "class": cls,
                "english_equivalent": equiv,
                "reason": str(item.get("reason") or "").strip(),
            }
        )
    return out


def propose_annotation_policy(
    book_dir: Path,
    *,
    log=print,
    classifier: Callable[[str], str] | None = None,
    only_unclassified: bool = True,
) -> dict[str, Any]:
    """ONE model call classifying this book's glossary. Returns a report.

    Writes the proposed class into each glossary entry (`annotation_class`,
    `english_equivalent`, `annotation_reason`) and a review report to
    `_system/annotation-policy-report.json`. A human edits the glossary to
    override any line; re-running with ``only_unclassified=True`` (the default)
    never touches an entry that already carries a class, so a human decision is
    durable across re-proposals.
    """
    book_dir = Path(book_dir).resolve()
    path = book_dir / "_system" / "glossary.yml"
    entries = _load_glossary_entries(book_dir)
    if not entries:
        log("    annotation-policy: no glossary — nothing to classify")
        return {"classified": 0, "skipped": 0}

    book_md = book_dir / "book" / "book.md"
    body = book_md.read_text(encoding="utf-8") if book_md.exists() else ""
    meta_title = _book_title(book_dir)

    targets = [e for e in entries if not (only_unclassified and str(e.get(_CLASS_FIELD) or "").strip())]
    if not targets:
        log("    annotation-policy: every term already classified — nothing to do")
        return {"classified": 0, "skipped": len(entries)}

    rows = [
        {
            "phonetic": str(e.get("phonetic") or "").strip(),
            "english": str(e.get("english") or "").strip(),
            "first_seen": str(e.get("first_seen_snippet") or "").strip()[:120],
            "occurrences_in_book": _usage_count(body, str(e.get("phonetic") or "").strip()),
            "has_script": bool(str(e.get("arabic_script") or "").strip()),
        }
        for e in targets
    ]

    def _classify(batch: list[dict]) -> dict[str, dict]:
        prompt = _classifier_prompt(meta_title, batch)
        if classifier is not None:
            raw = classifier(prompt)
        else:
            from _authoring._core import _run_claude_p_with_retry, pure_json_call_options

            rc, out, err = _run_claude_p_with_retry(
                prompt,
                timeout=_CLASSIFY_TIMEOUT,
                book_dir=book_dir,
                phase="0book-annotation-policy",
                step="classify-glossary",
                log=log,
                **pure_json_call_options(),
            )
            if rc != 0:
                raise AnnotationPolicyError(f"classifier failed rc={rc}: {str(err)[:200]}")
            raw = out
        return {p["phonetic"]: p for p in _parse_classification(raw) if p["phonetic"]}

    # BATCHED, and written after each batch (2026-08-02).
    #
    # This was one call over every unclassified term, and it REFUSED a partial
    # answer — correctly, because a half-classified book prints two conventions:
    # an unclassified term falls back to `legacy`, which annotates once per
    # CHAPTER instead of once per book. But the refusal threw away the batches
    # that HAD succeeded, and the caller records the raise as a skip, so one
    # omitted term out of 182 left the entire book unclassified and MORE
    # annotated than before. The check is right; its scope was wrong.
    #
    # Now: 40 at a time (mirroring `fill_glossary_arabic.BATCH_SIZE`), each batch
    # written before the next is attempted, one retry for a batch's omissions.
    # A batch that fails twice still raises — but everything before it is durable
    # and `only_unclassified=True` makes the next run resume for free.
    by_phonetic = {str(e.get("phonetic") or "").strip(): e for e in entries}
    all_proposed: dict[str, dict] = {}
    classified = 0
    for start in range(0, len(rows), _CLASSIFY_BATCH):
        batch = rows[start : start + _CLASSIFY_BATCH]
        proposed = _classify(batch)
        missing = [r["phonetic"] for r in batch if r["phonetic"] not in proposed]
        if missing:
            retry = _classify([r for r in batch if r["phonetic"] in missing])
            proposed.update(retry)
            missing = [r["phonetic"] for r in batch if r["phonetic"] not in proposed]
        if missing:
            save_glossary(path, entries, {"schema_version": 1})  # keep what worked
            raise AnnotationPolicyError(
                f"classifier omitted {len(missing)} term(s) twice: {', '.join(missing[:5])} "
                f"({classified} already classified and saved)"
            )
        all_proposed.update(proposed)
        for phonetic, p in proposed.items():
            e = by_phonetic.get(phonetic)
            if not e:
                continue
            e[_CLASS_FIELD] = p["class"]
            if p["english_equivalent"]:
                e[_EQUIV_FIELD] = p["english_equivalent"]
            e[_REASON_FIELD] = p["reason"]
            classified += 1
        save_glossary(path, entries, {"schema_version": 1})
        if len(rows) > _CLASSIFY_BATCH:
            log(f"    annotation-policy: {min(start + _CLASSIFY_BATCH, len(rows))}/{len(rows)} classified")

    # Through the ONE writer (2026-08-02). This used to be `yaml.safe_dump`, which
    # emits `- phonetic: x` at column 0 unquoted — valid YAML that three
    # hand-rolled Python parsers and the site's reader all failed to match, so the
    # three books this function had touched read back as ZERO entries. One of
    # those readers then wrote its result, which is how a full glossary could be
    # replaced by an empty one behind a "non-blocking" log line.
    save_glossary(path, entries, {"schema_version": 1})
    report = {
        "schema": "book.annotation-policy/v1",
        "classified": len(all_proposed),
        "skipped": len(entries) - len(targets),
        "by_class": {c: sum(1 for p in all_proposed.values() if p["class"] == c) for c in ANNOTATION_CLASSES},
        "proposals": sorted(all_proposed.values(), key=lambda p: (p["class"], p["phonetic"].lower())),
    }
    (book_dir / "_system" / _REPORT_NAME).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    log(
        "    annotation-policy: "
        + ", ".join(f"{report['by_class'][c]} {c}" for c in ANNOTATION_CLASSES)
        + f" ({report['skipped']} already classified, left alone)"
    )
    return report


def _book_title(book_dir: Path) -> str:
    meta = Path(book_dir) / "meta.yml"
    if meta.exists():
        try:
            data = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
            return str(data.get("title") or book_dir.name)
        except Exception:
            return book_dir.name
    return book_dir.name


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: python3 _annotation_policy.py <BOOK_DIR> [--all]", file=sys.stderr)
        return 2
    only_unclassified = "--all" not in sys.argv
    try:
        propose_annotation_policy(Path(args[0]), only_unclassified=only_unclassified)
        return 0
    except AnnotationPolicyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
