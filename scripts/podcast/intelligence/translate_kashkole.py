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

from _authoring._core import _run_claude_p_with_retry, pure_text_call_options  # noqa: E402
from _kashkole_translation import (  # noqa: E402
    PROMPT_VERSION,
    TITLE_INSTRUCTION,
    body_prompt,
    check,
    windows_of,
)
from _paths import REPO_ROOT  # noqa: E402

MIRROR = REPO_ROOT / "content" / "knowledge-base" / "mirror.db"
STANDARD = REPO_ROOT / "docs" / "standards" / "book-articulation.md"

CALL_TIMEOUT = 900
CALL_RC_RETRIES = 1
DEAD_STREAK_LIMIT = 2
KASHKOLE_RUN_DIR = REPO_ROOT / "_workspace" / "reviews" / "wisdom-audit"


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

CREATE TABLE IF NOT EXISTS topic_translation_window (
  topic_id       INTEGER NOT NULL,
  window_index   INTEGER NOT NULL,
  total_windows  INTEGER NOT NULL DEFAULT 0,
  rendered       TEXT NOT NULL DEFAULT '',
  source_sha     TEXT NOT NULL,
  window_sha     TEXT NOT NULL,
  source_chars   INTEGER NOT NULL DEFAULT 0,
  output_chars   INTEGER NOT NULL DEFAULT 0,
  model          TEXT NOT NULL DEFAULT '',
  prompt_version TEXT NOT NULL DEFAULT '',
  standard_sha   TEXT NOT NULL DEFAULT '',
  run_id         TEXT NOT NULL DEFAULT '',
  translated_at  TEXT NOT NULL DEFAULT '',
  status         TEXT NOT NULL DEFAULT 'ok',
  concerns       TEXT NOT NULL DEFAULT '[]',
  PRIMARY KEY (topic_id, window_index)
);
CREATE INDEX IF NOT EXISTS idx_topic_translation_window_source
  ON topic_translation_window (topic_id, source_sha, window_sha, prompt_version);
"""


def source_sha(name: str, body: str) -> str:
    h = hashlib.sha256()
    h.update((name or "").encode("utf-8"))
    h.update(b"\x00")
    h.update((body or "").encode("utf-8"))
    h.update(b"\x00")
    h.update(PROMPT_VERSION.encode("utf-8"))
    return h.hexdigest()


def window_sha(text: str, *, index: int, total: int) -> str:
    h = hashlib.sha256()
    h.update(f"{PROMPT_VERSION}\x00{index}\x00{total}\x00".encode("utf-8"))
    h.update((text or "").encode("utf-8"))
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


def pending(db: sqlite3.Connection, *, force: bool = False, binder: str | None = None) -> list[sqlite3.Row]:
    """Topics still needing a rendering, longest first.

    Longest first so the tail of a long run is cheap short topics rather than the
    312,000-character one nobody wants to discover at hour six.
    """
    params: list[str] = []
    where = ""
    if binder:
        where = "WHERE t.binder = ?"
        params.append(binder)
    rows = db.execute(
        f"""SELECT t.topic_id, t.name, t.binder, t.chapter, t.body_plain
            FROM fts_topics t {where}
            ORDER BY t.chapter COLLATE NOCASE, length(coalesce(t.body_plain,'')) DESC,
                     t.topic_id""",
        params,
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
    last = ""
    for attempt in range(CALL_RC_RETRIES + 1):
        rc, out, err = _run_claude_p_with_retry(
            prompt,
            timeout=CALL_TIMEOUT,
            book_dir=KASHKOLE_RUN_DIR,
            phase="kashkole-translate",
            step=step if attempt == 0 else f"{step}-rc-retry-{attempt}",
            log=lambda msg: print(msg, flush=True),
            **pure_text_call_options(),
        )
        if rc == 0:
            text = (out or "").strip()
            if text:
                return text
            last = "empty rendering"
        else:
            last = f"claude -p rc={rc}: {(err or '')[:200]}"
        if attempt < CALL_RC_RETRIES:
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(last or "empty rendering")


def _read_window(db: sqlite3.Connection, *, tid: int, index: int, source_hash: str, win_hash: str) -> str | None:
    row = db.execute(
        """SELECT rendered FROM topic_translation_window
           WHERE topic_id=? AND window_index=? AND source_sha=? AND window_sha=?
             AND prompt_version=? AND status='ok'""",
        (tid, index, source_hash, win_hash, PROMPT_VERSION),
    ).fetchone()
    if row and (row["rendered"] or "").strip():
        return str(row["rendered"]).strip()
    return None


def _store_window(
    db: sqlite3.Connection,
    *,
    tid: int,
    index: int,
    total: int,
    rendered: str,
    source_hash: str,
    win_hash: str,
    source_chars: int,
    run_id: str,
) -> None:
    with _write_lock:
        db.execute(
            """INSERT INTO topic_translation_window
                 (topic_id, window_index, total_windows, rendered, source_sha, window_sha,
                  source_chars, output_chars, model, prompt_version, standard_sha, run_id,
                  translated_at, status, concerns)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(topic_id, window_index) DO UPDATE SET
                 total_windows=excluded.total_windows, rendered=excluded.rendered,
                 source_sha=excluded.source_sha, window_sha=excluded.window_sha,
                 source_chars=excluded.source_chars, output_chars=excluded.output_chars,
                 model=excluded.model, prompt_version=excluded.prompt_version,
                 standard_sha=excluded.standard_sha, run_id=excluded.run_id,
                 translated_at=excluded.translated_at, status=excluded.status,
                 concerns=excluded.concerns""",
            (
                tid,
                index,
                total,
                rendered,
                source_hash,
                win_hash,
                int(source_chars),
                len(rendered or ""),
                "claude -p (subscription default)",
                PROMPT_VERSION,
                standard_sha(),
                run_id,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "ok",
                "[]",
            ),
        )
        db.commit()


def translate_topic(row: sqlite3.Row, *, run_id: str) -> dict:
    """Render one topic. Returns the row to store."""
    name = row["name"] or ""
    body = (row["body_plain"] or "").strip()
    tid = row["topic_id"]
    source_hash = source_sha(name, body)

    name_en = ""
    if name:
        name_en = _call(f"{TITLE_INSTRUCTION}\n\n--- URDU TITLE ---\n{name}\n\n--- ENGLISH TITLE ---", f"title-{tid}")
        # A model that answers a title request with a sentence has misread it.
        name_en = name_en.splitlines()[0].strip().strip('"').strip() if name_en else ""

    parts = windows_of(body)
    local_db = connect()
    rendered: list[str] = []
    for i, window in enumerate(parts, start=1):
        win_hash = window_sha(window, index=i, total=len(parts))
        cached = _read_window(local_db, tid=tid, index=i, source_hash=source_hash, win_hash=win_hash)
        if cached is not None:
            rendered.append(cached)
            continue
        tail = " ".join(rendered[-1].split()[-60:]) if rendered else ""
        out = _call(body_prompt(row, window, part=i, total=len(parts), tail=tail), f"body-{tid}-{i}")
        _store_window(
            local_db,
            tid=tid,
            index=i,
            total=len(parts),
            rendered=out,
            source_hash=source_hash,
            win_hash=win_hash,
            source_chars=len(window),
            run_id=run_id,
        )
        rendered.append(out)
    local_db.close()

    body_en = "\n\n".join(p for p in rendered if p).strip()
    status, concerns = check(body, body_en) if body else ("ok", [])

    return {
        "topic_id": tid,
        "name_en": name_en,
        "body_en": body_en,
        "source_sha": source_hash,
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


def status_report(db: sqlite3.Connection, *, binder: str | None = None) -> dict:
    params: list[str] = []
    where = ""
    if binder:
        where = "WHERE binder = ?"
        params.append(binder)
    total = db.execute(f"SELECT count(*) FROM fts_topics {where}", params).fetchone()[0]
    subst = db.execute(
        f"SELECT count(*) FROM fts_topics {where} {'AND' if where else 'WHERE'} length(coalesce(body_plain,''))>200",
        params,
    ).fetchone()[0]
    join_where = "WHERE t.binder = ?" if binder else ""
    done = db.execute(
        f"SELECT count(*) FROM topic_translation tr JOIN fts_topics t ON t.topic_id=tr.topic_id {join_where}",
        params,
    ).fetchone()[0]
    by_status = {
        r[0]: r[1]
        for r in db.execute(
            f"""SELECT tr.status, count(*)
                FROM topic_translation tr JOIN fts_topics t ON t.topic_id=tr.topic_id
                {join_where} GROUP BY tr.status""",
            params,
        )
    }
    chars = db.execute(
        f"""SELECT coalesce(sum(tr.output_chars),0)
            FROM topic_translation tr JOIN fts_topics t ON t.topic_id=tr.topic_id
            {join_where}""",
        params,
    ).fetchone()[0]
    source_chars = db.execute(
        f"SELECT coalesce(sum(length(coalesce(body_plain,''))),0) FROM fts_topics {where}", params
    ).fetchone()[0]
    done_source_chars = db.execute(
        f"""SELECT coalesce(sum(length(coalesce(t.body_plain,''))),0)
            FROM fts_topics t JOIN topic_translation tr ON tr.topic_id=t.topic_id
            {join_where}""",
        params,
    ).fetchone()[0]
    return {
        "binder": binder,
        "topics": total,
        "substantial": subst,
        "translated": done,
        "remaining": len(pending(db, binder=binder)),
        "source_chars": source_chars,
        "translated_source_chars": done_source_chars,
        "remaining_source_chars": source_chars - done_source_chars,
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
    ap.add_argument("--binder", help="translate/status only one exact binder name")
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
        print(json.dumps(status_report(db, binder=args.binder), indent=2, ensure_ascii=False))
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
            if not (r["body_plain"] or "").strip():
                status, concerns = "ok", []
            else:
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

    todo = pending(db, force=args.force, binder=args.binder)
    if args.topic:
        wanted = set(args.topic)
        topic_params: list[object] = []
        topic_where = ""
        if args.binder:
            topic_where = "WHERE binder=?"
            topic_params.append(args.binder)
        todo = [
            r
            for r in db.execute(
                f"SELECT topic_id, name, binder, chapter, body_plain FROM fts_topics {topic_where}",
                topic_params,
            )
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
    ok = failed = dead_streak = 0
    stopped = False

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        remaining = iter(todo)
        futures = {}
        submitted = 0
        for _ in range(max(1, args.workers)):
            try:
                row = next(remaining)
            except StopIteration:
                break
            submitted += 1
            futures[pool.submit(translate_topic, row, run_id=run_id)] = row
        n = 0
        while futures:
            for fut in as_completed(list(futures), timeout=None):
                break
            row = futures[fut]
            del futures[fut]
            n += 1
            try:
                rec = fut.result()
                store(db, rec, run_id)
                ok += 1
                dead_streak = 0
                flag = "" if rec["status"] == "ok" else f"  [{rec['status']}]"
                print(
                    f"  [{n}/{len(todo)}] {rec['topic_id']:>5} "
                    f"{rec['source_chars']:>7,}→{rec['output_chars']:>7,} chars "
                    f"({rec['windows']}w){flag}",
                    flush=True,
                )
            except Exception as exc:  # a failed topic must not stop the corpus
                failed += 1
                dead_streak += 1
                print(f"  [{n}/{len(todo)}] {row['topic_id']:>5} FAILED: {str(exc)[:150]}", flush=True)
                if dead_streak >= DEAD_STREAK_LIMIT:
                    stopped = True
                    for f in futures:
                        f.cancel()
                    futures.clear()
                    print(
                        f"STOPPING: {dead_streak} consecutive topic failures; "
                        "this looks like an exhausted or unreachable model. Re-run to resume.",
                        flush=True,
                    )
                    break
            if stopped:
                break
            try:
                next_row = next(remaining)
            except StopIteration:
                continue
            submitted += 1
            futures[pool.submit(translate_topic, next_row, run_id=run_id)] = next_row

    mins = (time.monotonic() - t0) / 60
    print(f"\ndone: {ok} rendered, {failed} failed, {mins:.1f} min")
    print(json.dumps(status_report(db, binder=args.binder), indent=2, ensure_ascii=False))
    return 0 if failed == 0 and not stopped else 1


if __name__ == "__main__":
    raise SystemExit(main())
