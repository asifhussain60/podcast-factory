"""translate_kashkole.py — the KASHKOLE Wisdom corpus, rendered into English.

WHAT THIS IS FOR. `content/knowledge-base/mirror.db` carries all 1,347 KASHKOLE
topics and every one of them is Urdu: the source dump contains zero `name_en`, so
this is Urdu at source rather than a mirroring loss. Until this pass existed the
corpus could not be cited in English beside KSESSIONS, and the Companion lane
could name a topic but never render it. Asif, 2026-08-06: the corpus must be
rendered into articulate English so it can augment content, etymology and
explanations as ONE unit with KSESSIONS.

IT SUPERSEDES D8 FOR THIS CORPUS. D8 ("HARD, never re-translate") is what kept
`ingest_kashkole.py` from minting topic atoms, and it was right while the only
English available would have been a machine gloss. It is not a prohibition on
rendering the corpus properly; that module's note is updated in the same change
so the two cannot be read as contradicting one another.

WHY `claude -p` AND NOT THE EXISTING TRANSLATOR. `tools/content_translator` is
Azure Translator — literal, per-character, and billed at $10/1M characters, which
is about $91 for this corpus. It produces a gloss, and a gloss is precisely what
D8 exists to keep out of the atom store. This pass targets the SAME articulation
standard the reading editions are held to (`docs/standards/book-articulation.md`,
REQ-BA-*), which is a judgement no phrase-level engine can make, and it runs on
the flat-rate subscription where the repo's cost policy says this work belongs.

WHAT IS WRITTEN, AND WHERE. A new ordinary table, `topic_translation`, beside the
FTS index rather than inside it. `fts_topics` is a virtual table and its columns
are an index, not a record; writing English into it would make the rendering
unversioned, untraceable, and destroyed by the next re-import. Every row here
carries its own provenance — the model, the prompt version, the standard it was
written against, the run, the time, and the SHA of the exact source it came from
— so a rendering can be traced to its input and revised when either end changes.

IDEMPOTENT AND RE-RUNNABLE, which is the property that makes a multi-hour job
safe to interrupt. A topic whose stored `source_sha` still matches its source is
skipped; change the Urdu, or the prompt, and only the affected topics re-run.
`--force` re-runs regardless.

CLI:
    python3 scripts/podcast/intelligence/translate_kashkole.py --dry-run
    python3 scripts/podcast/intelligence/translate_kashkole.py --limit 5
    python3 scripts/podcast/intelligence/translate_kashkole.py --workers 4
    python3 scripts/podcast/intelligence/translate_kashkole.py --status
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
for _p in (str(_SCRIPTS), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _arabic_coverage import ARABIC_BODY, arabic_span_is_grounded  # noqa: E402
from _authoring._core import _run_claude_p, pure_text_call_options  # noqa: E402
from _paths import REPO_ROOT  # noqa: E402

try:
    from _mushaf import is_quranic, mushaf_available
except Exception:  # pragma: no cover - the mirror may be absent on a fresh clone

    def mushaf_available() -> bool:
        return False

    def is_quranic(span: str) -> bool:
        return False


MIRROR = REPO_ROOT / "content" / "knowledge-base" / "mirror.db"
STANDARD = REPO_ROOT / "docs" / "standards" / "book-articulation.md"

# Bumped whenever the instruction below changes in a way that should invalidate
# existing renderings. It is part of the stored provenance and part of the skip
# decision, so a prompt change re-runs the corpus rather than leaving a mixture
# of two vintages that nothing can tell apart.
PROMPT_VERSION = "1.0"

# Windowing. Chosen against the corpus rather than guessed: the median body is
# 2,785 characters and fits whole, while 117 topics exceed 20,000 and one runs to
# 312,374. A whole-body call on those comes back abridged — the failure the
# reading-edition pipeline already learned the hard way and answered with
# windowing (see the long-chapter rule).
WINDOW_CHARS = 3_500
# Only split ABOVE this; below it a body goes in one piece and keeps its shape.
WINDOW_THRESHOLD = 5_000

CALL_TIMEOUT = 900

# Output shorter than this share of its source is an abridgement, not a
# translation. Same 60% floor the rearticulation gate uses, and for the same
# reason: REQ-BA-100 says a rendering is never shorter.
SHORT_RATIO = 0.60


# ---------------------------------------------------------------------------
# The instruction
# ---------------------------------------------------------------------------

_INSTRUCTION = """\
You are rendering a passage of Urdu religious scholarship into English for a \
printed reading edition of the Ismaili wisdom corpus.

This is a TRANSLATION, and it is held to the same standard as the reading \
editions in this library. Follow every rule below exactly.

REGISTER (REQ-BA-010). Modern, lucid, simple English for a general reader, not a \
specialist. Every sentence understandable on first read. Prefer the plain word to \
the ornate one. Simple is not casual: the register stays dignified and bookish — \
no contractions, no marketing tone, no lecture or podcast voice.

DE-CALQUE (REQ-BA-020). Never carry Urdu or Arabic word order, pronoun chains or \
rhetorical scaffolding into the English. Split, merge and reorder sentences \
within a paragraph freely so the English reads as English.

MEANING IS INVARIANT (REQ-BA-030). Every teaching, argument, example, named \
person, citation and enumerated list survives intact. Add NOTHING — no outside \
facts, no modern analogies, no explanatory asides, no bracketed interpolations. \
Drop nothing, summarize nothing, reinterpret nothing.

QUOTATIONS ARE ARTIFACTS (REQ-BA-040). Direct speech, Qur'an verses, hadith, \
poetry and quoted sayings keep their boundaries, their speakers and their \
content. Never add, remove or re-point a speech tag.

ARABIC SCRIPT IS UNTOUCHABLE (REQ-BA-060). This is the rule that matters most \
here, because the source is itself in Arabic script. The URDU PROSE is what you \
translate. Any run of ARABIC quotation inside it — a Qur'an verse, a hadith, a \
prayer, an Arabic phrase the author is quoting rather than writing — is COPIED \
THROUGH VERBATIM, character for character, including its vowel marks. Never \
translate it away, never romanize it, never re-vowel it. Where the Urdu supplies \
a rendering of such a quotation, translate that rendering and keep the Arabic \
beside it.

IMAGERY (REQ-BA-050). Metaphors and parables keep their concrete images. Recast \
the grammar around an image; never replace the image with an abstraction.

TERMS (REQ-BA-070, -080). Render each technical term the same way every time it \
appears. Where an accepted English word carries the meaning, use it. Do not add \
new parenthetical transliterations; keep glosses the source already has.

LENGTH (REQ-BA-100). The English is approximately as long as the Urdu. A \
translation is a rewording, never an abridgement. Keep the paragraph structure of \
the source unless English demands otherwise.

SPELLING (REQ-BA-110). American spelling, the serial comma, periods and commas \
inside closing quotes.

OUTPUT. Return ONLY the English rendering. No preamble, no notes, no commentary, \
no markdown fences, no headings that are not in the source.
"""

_TITLE_INSTRUCTION = """\
Render this Urdu topic title into a short, dignified English title for a printed \
reading edition. Modern, lucid English; title case; no trailing period; no \
transliteration in parentheses; no commentary. Return ONLY the title.
"""


def _context(row: sqlite3.Row) -> str:
    bits = []
    if row["binder"]:
        bits.append(f"Binder: {row['binder']}")
    if row["chapter"]:
        bits.append(f"Chapter: {row['chapter']}")
    if row["name"]:
        bits.append(f"Topic: {row['name']}")
    return "\n".join(bits)


def _body_prompt(row: sqlite3.Row, window: str, *, part: int, total: int, tail: str) -> str:
    head = [_INSTRUCTION, "", "--- CONTEXT (do not translate, for orientation only) ---", _context(row)]
    if total > 1:
        head += [
            "",
            f"This is part {part} of {total} of one topic. Translate ONLY the part "
            "given below. Do not summarize what came before and do not preview what "
            "comes after; the parts are joined verbatim.",
        ]
        if tail:
            head += [
                "",
                "The previous part ended with the following English, for continuity of "
                "terminology and voice. Do NOT repeat it:",
                tail,
            ]
    head += ["", "--- URDU SOURCE ---", window, "", "--- ENGLISH RENDERING ---"]
    return "\n".join(head)


# ---------------------------------------------------------------------------
# Windowing
# ---------------------------------------------------------------------------

_PARA_RE = re.compile(r"\n\s*\n")
# Urdu full stop, Arabic full stop, and the Latin one the corpus also uses.
_SENT_RE = re.compile(r"(?<=[۔.!?])\s+")


def windows_of(body: str, size: int = WINDOW_CHARS) -> list[str]:
    """Split a body at paragraph boundaries, falling back to sentences.

    Never mid-sentence: a window that begins in the middle of a clause gives the
    model no way to know what the subject was, and the join shows it.
    """
    body = (body or "").strip()
    if len(body) <= WINDOW_THRESHOLD:
        return [body] if body else []

    units: list[str] = []
    for para in _PARA_RE.split(body):
        para = para.strip()
        if not para:
            continue
        if len(para) <= size:
            units.append(para)
            continue
        # A single paragraph longer than a window — this corpus has many. Split
        # it at sentence ends, and only if a SENTENCE is longer than a window
        # does anything get cut arbitrarily.
        buf = ""
        for sent in _SENT_RE.split(para):
            if not sent.strip():
                continue
            if len(buf) + len(sent) + 1 > size and buf:
                units.append(buf.strip())
                buf = sent
            else:
                buf = f"{buf} {sent}".strip()
        if buf.strip():
            units.append(buf.strip())

    out: list[str] = []
    buf = ""
    for unit in units:
        if len(buf) + len(unit) + 2 > size and buf:
            out.append(buf.strip())
            buf = unit
        else:
            buf = f"{buf}\n\n{unit}".strip()
    if buf.strip():
        out.append(buf.strip())
    return out


# ---------------------------------------------------------------------------
# Quality gates
# ---------------------------------------------------------------------------

_ARABIC_RUN_RE = re.compile(rf"[{ARABIC_BODY}]+(?:\s+[{ARABIC_BODY}]+)*")


def quranic_runs(text: str, *, min_words: int = 4) -> list[str]:
    """Arabic-script runs in ``text`` the canonical mushaf recognises as scripture.

    Used as a RETENTION check rather than a translation aid. The whole source is
    Arabic script, so "did Arabic survive" is meaningless here — but "did the
    Qur'an verse this passage quotes survive" is exactly the question REQ-BA-060
    is asking on a corpus like this one, and the mushaf can answer it.
    """
    if not mushaf_available():
        return []
    found: list[str] = []
    for run in _ARABIC_RUN_RE.findall(text or ""):
        if len(run.split()) < min_words:
            continue
        try:
            if is_quranic(run):
                found.append(run)
        except Exception:
            continue
    return found


def _normalize(text: str) -> str:
    return " ".join((text or "").split())


def check(source: str, rendered: str) -> tuple[str, list[str]]:
    """`(status, concerns)` for one rendering. Never raises."""
    concerns: list[str] = []
    src, out = _normalize(source), _normalize(rendered)
    if not out:
        return "failed", ["empty rendering"]

    ratio = len(out) / max(1, len(src))
    if ratio < SHORT_RATIO:
        concerns.append(f"abridged: rendering is {ratio:.0%} of the source")

    # A Qur'an verse quoted in the source must still be there.
    #
    # COMPARED ON THE CONSONANTAL SKELETON, via the same `arabic_span_is_grounded`
    # the provenance code uses to ask whether a run was copied rather than
    # remembered. A raw substring test was the first implementation and it was
    # wrong in the way that matters: the renderer wraps a verse in bidi marks and
    # may set it in the mushaf's own spelling, so `in` reported a verse missing
    # while it sat in the output two lines further down. Two of the first three
    # probe topics were flagged for verses that were plainly there.
    for run in quranic_runs(source):
        if not arabic_span_is_grounded(run, rendered):
            concerns.append(f"quranic run not carried through: {run[:40]}")

    status = "short" if any(c.startswith("abridged") for c in concerns) else "ok"
    if any(c.startswith("quranic") for c in concerns):
        status = "short" if status == "short" else "review"
    return status, concerns


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS topic_translation (
  topic_id       INTEGER PRIMARY KEY,
  name_en        TEXT NOT NULL DEFAULT '',
  body_en        TEXT NOT NULL DEFAULT '',
  source_sha     TEXT NOT NULL,
  source_chars   INTEGER NOT NULL DEFAULT 0,
  output_chars   INTEGER NOT NULL DEFAULT 0,
  windows        INTEGER NOT NULL DEFAULT 0,
  model          TEXT NOT NULL DEFAULT '',
  prompt_version TEXT NOT NULL DEFAULT '',
  standard_sha   TEXT NOT NULL DEFAULT '',
  run_id         TEXT NOT NULL DEFAULT '',
  translated_at  TEXT NOT NULL DEFAULT '',
  status         TEXT NOT NULL DEFAULT 'ok',
  concerns       TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_topic_translation_status
  ON topic_translation (status);
"""


def source_sha(name: str, body: str) -> str:
    h = hashlib.sha256()
    h.update((name or "").encode("utf-8"))
    h.update(b"\x00")
    h.update((body or "").encode("utf-8"))
    h.update(b"\x00")
    h.update(PROMPT_VERSION.encode("utf-8"))
    return h.hexdigest()


def standard_sha() -> str:
    try:
        return hashlib.sha256(STANDARD.read_bytes()).hexdigest()[:16]
    except OSError:
        return "absent"


def connect(path: Path = MIRROR) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=60)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def pending(db: sqlite3.Connection, *, force: bool = False) -> list[sqlite3.Row]:
    """Topics still needing a rendering, longest first.

    Longest first so the tail of a long run is cheap short topics rather than the
    312,000-character one nobody wants to discover at hour six.
    """
    rows = db.execute(
        """SELECT t.topic_id, t.name, t.binder, t.chapter, t.body_plain
           FROM fts_topics t ORDER BY length(coalesce(t.body_plain,'')) DESC"""
    ).fetchall()
    if force:
        return rows
    done = {
        r["topic_id"]: r["source_sha"]
        for r in db.execute(
            "SELECT topic_id, source_sha FROM topic_translation WHERE status IN ('ok','short','review')"
        )
    }
    return [r for r in rows if done.get(r["topic_id"]) != source_sha(r["name"] or "", r["body_plain"] or "")]


# ---------------------------------------------------------------------------
# The pass
# ---------------------------------------------------------------------------

_write_lock = threading.Lock()


def _call(prompt: str, step: str) -> str:
    rc, out, err = _run_claude_p(
        prompt,
        timeout=CALL_TIMEOUT,
        phase="kashkole-translate",
        step=step,
        **pure_text_call_options(),
    )
    if rc != 0:
        raise RuntimeError(f"claude -p rc={rc}: {(err or '')[:200]}")
    return (out or "").strip()


def translate_topic(row: sqlite3.Row) -> dict:
    """Render one topic. Returns the row to store."""
    name = row["name"] or ""
    body = (row["body_plain"] or "").strip()
    tid = row["topic_id"]

    name_en = ""
    if name:
        name_en = _call(f"{_TITLE_INSTRUCTION}\n\n--- URDU TITLE ---\n{name}\n\n--- ENGLISH TITLE ---", f"title-{tid}")
        # A model that answers a title request with a sentence has misread it.
        name_en = name_en.splitlines()[0].strip().strip('"').strip() if name_en else ""

    parts = windows_of(body)
    rendered: list[str] = []
    for i, window in enumerate(parts, start=1):
        tail = " ".join(rendered[-1].split()[-60:]) if rendered else ""
        rendered.append(_call(_body_prompt(row, window, part=i, total=len(parts), tail=tail), f"body-{tid}-{i}"))

    body_en = "\n\n".join(p for p in rendered if p).strip()
    status, concerns = check(body, body_en) if body else ("ok", [])

    return {
        "topic_id": tid,
        "name_en": name_en,
        "body_en": body_en,
        "source_sha": source_sha(name, body),
        "source_chars": len(body),
        "output_chars": len(body_en),
        "windows": len(parts),
        "status": status,
        "concerns": json.dumps(concerns, ensure_ascii=False),
    }


def store(db: sqlite3.Connection, rec: dict, run_id: str) -> None:
    with _write_lock:
        db.execute(
            """INSERT INTO topic_translation
                 (topic_id, name_en, body_en, source_sha, source_chars, output_chars,
                  windows, model, prompt_version, standard_sha, run_id, translated_at,
                  status, concerns)
               VALUES (:topic_id,:name_en,:body_en,:source_sha,:source_chars,:output_chars,
                       :windows,:model,:prompt_version,:standard_sha,:run_id,:translated_at,
                       :status,:concerns)
               ON CONFLICT(topic_id) DO UPDATE SET
                 name_en=excluded.name_en, body_en=excluded.body_en,
                 source_sha=excluded.source_sha, source_chars=excluded.source_chars,
                 output_chars=excluded.output_chars, windows=excluded.windows,
                 model=excluded.model, prompt_version=excluded.prompt_version,
                 standard_sha=excluded.standard_sha, run_id=excluded.run_id,
                 translated_at=excluded.translated_at, status=excluded.status,
                 concerns=excluded.concerns""",
            {
                **rec,
                "model": "claude -p (subscription default)",
                "prompt_version": PROMPT_VERSION,
                "standard_sha": standard_sha(),
                "run_id": run_id,
                "translated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
        )
        db.commit()


def status_report(db: sqlite3.Connection) -> dict:
    total = db.execute("SELECT count(*) FROM fts_topics").fetchone()[0]
    subst = db.execute("SELECT count(*) FROM fts_topics WHERE length(coalesce(body_plain,''))>200").fetchone()[0]
    done = db.execute("SELECT count(*) FROM topic_translation").fetchone()[0]
    by_status = {r[0]: r[1] for r in db.execute("SELECT status, count(*) FROM topic_translation GROUP BY status")}
    chars = db.execute("SELECT coalesce(sum(output_chars),0) FROM topic_translation").fetchone()[0]
    return {
        "topics": total,
        "substantial": subst,
        "translated": done,
        "remaining": len(pending(db)),
        "by_status": by_status,
        "english_chars": chars,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="translate at most N topics")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--force", action="store_true", help="re-render even when unchanged")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument(
        "--rescore",
        action="store_true",
        help="re-run the quality gates over stored renderings without translating",
    )
    ap.add_argument("--topic", type=int, action="append", help="one topic id (repeatable)")
    args = ap.parse_args(argv)

    if not MIRROR.exists():
        print(f"mirror not found: {MIRROR}", file=sys.stderr)
        return 2

    db = connect()

    if args.status:
        print(json.dumps(status_report(db), indent=2, ensure_ascii=False))
        return 0

    if args.rescore:
        # A gate is a judgement about a rendering, not part of it. When the gate
        # is corrected — as the Qur'anic-retention check was, after it reported
        # verses missing that were plainly present — the stored verdicts are
        # stale but the English is not, and re-translating the corpus to fix a
        # verdict would be paying for the same words twice.
        moved = 0
        rows = db.execute(
            """SELECT tr.topic_id, tr.status, tr.body_en, t.body_plain
               FROM topic_translation tr JOIN fts_topics t ON t.topic_id = tr.topic_id"""
        ).fetchall()
        for r in rows:
            status, concerns = check(r["body_plain"] or "", r["body_en"] or "")
            if status != r["status"]:
                moved += 1
                print(f"  {r['topic_id']:>5}: {r['status']} → {status}")
            db.execute(
                "UPDATE topic_translation SET status=?, concerns=? WHERE topic_id=?",
                (status, json.dumps(concerns, ensure_ascii=False), r["topic_id"]),
            )
        db.commit()
        print(f"rescored {len(rows)} rendering(s); {moved} changed verdict")
        print(json.dumps(status_report(db), indent=2, ensure_ascii=False))
        return 0

    todo = pending(db, force=args.force)
    if args.topic:
        wanted = set(args.topic)
        todo = [
            r
            for r in db.execute("SELECT topic_id, name, binder, chapter, body_plain FROM fts_topics")
            if r["topic_id"] in wanted
        ]
    if args.limit:
        todo = todo[: args.limit]

    total_chars = sum(len(r["body_plain"] or "") for r in todo)
    total_windows = sum(max(1, len(windows_of(r["body_plain"] or ""))) for r in todo)
    print(
        f"kashkole-translate: {len(todo)} topics, {total_chars:,} source chars, "
        f"~{total_windows + len(todo):,} calls (bodies + titles), workers={args.workers}"
    )
    if args.dry_run:
        for r in todo[:10]:
            print(f"  [{r['topic_id']:>5}] {len(r['body_plain'] or ''):>7,} chars  {(r['name'] or '')[:48]}")
        if len(todo) > 10:
            print(f"  … and {len(todo) - 10:,} more")
        return 0
    if not todo:
        print("nothing to do — every topic is current")
        return 0

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    t0 = time.monotonic()
    ok = failed = 0

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(translate_topic, r): r for r in todo}
        for n, fut in enumerate(as_completed(futures), start=1):
            row = futures[fut]
            try:
                rec = fut.result()
                store(db, rec, run_id)
                ok += 1
                flag = "" if rec["status"] == "ok" else f"  [{rec['status']}]"
                print(
                    f"  [{n}/{len(todo)}] {rec['topic_id']:>5} "
                    f"{rec['source_chars']:>7,}→{rec['output_chars']:>7,} chars "
                    f"({rec['windows']}w){flag}",
                    flush=True,
                )
            except Exception as exc:  # a failed topic must not stop the corpus
                failed += 1
                print(f"  [{n}/{len(todo)}] {row['topic_id']:>5} FAILED: {str(exc)[:150]}", flush=True)

    mins = (time.monotonic() - t0) / 60
    print(f"\ndone: {ok} rendered, {failed} failed, {mins:.1f} min")
    print(json.dumps(status_report(db), indent=2, ensure_ascii=False))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
