"""intelligence/tag_doctrine_concepts.py — WC2 Part 2: doctrine concept-tagging (D19).

The 628 `doctrine` atoms (wisdom teachings) carry no Arabic root and no topic tags,
so the Concept Lens can't surface them. This pass assigns 2-5 concise English concept
tags to each via a cheap Gemini call (mirrors extractor.py's pattern: gemini-2.5-flash,
key from keychain, injectable caller for tests), then writes them to `atom_topic_tags`.
Once tagged, concept_index.py turns those tags into concepts (tag-concepts), so doctrine
becomes concept-searchable.

Additive + idempotent: atoms already carrying tags are skipped; tag writes are
INSERT OR IGNORE. Batched (8 atoms/call) to keep cost low; hard cost cap aborts the run.

CLI:
    python3 scripts/podcast/intelligence/tag_doctrine_concepts.py --dry-run   # count candidates, no LLM, no write
    python3 scripts/podcast/intelligence/tag_doctrine_concepts.py             # tag all untagged doctrine atoms
    python3 scripts/podcast/intelligence/tag_doctrine_concepts.py --limit 20  # tag a sample first
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _db import get_connection

LLMCaller = Callable[[str], "tuple[int, str, str]"]

_GEMINI_MODEL = "gemini-2.5-flash"
_PRICE = {"in": 0.30 / 1e6, "out": 2.50 / 1e6}
BATCH_SIZE = 8
DEFAULT_COST_CAP_USD = 5.0
MIN_TAGS, MAX_TAGS = 2, 5

# A few seed tags steer the model toward a consistent, concise vocabulary that will
# align with the existing root/theme concepts (mercy<->rhm, knowledge<->ilm, etc.).
_SEED_VOCAB = [
    "mercy", "knowledge", "worship", "oneness", "soul", "love", "intellect",
    "faith", "patience", "justice", "prophethood", "imamate", "ethics",
    "eschatology", "cosmology", "purification", "gratitude", "humility",
]

_PROMPT_TMPL = """You are a concept tagger for Fatimid-Ismaili wisdom teachings.
For each numbered passage below, assign {min_tags}-{max_tags} concise, lowercase, single-or-two-word
ENGLISH concept tags naming what the passage is ABOUT (its themes). Prefer reusing common tags
(examples: {vocab}) when they fit; otherwise propose your own. No transliteration, no Arabic.

Return ONLY this JSON, nothing else:
{{"results": [{{"i": <passage number>, "tags": ["tag1", "tag2"]}}, ...]}}

Passages:
{passages}
"""


@dataclass
class TagSummary:
    candidates: int = 0
    tagged: int = 0
    skipped_existing: int = 0
    tags_written: int = 0
    cost_usd: float = 0.0
    batches: int = 0
    errors: list[str] = field(default_factory=list)


def _load_gemini_key() -> str:
    env = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env:
        return env
    out = subprocess.run(
        ["security", "find-generic-password", "-s", "gemini_api_key", "-w"],
        capture_output=True, text=True,
    )
    key = out.stdout.strip()
    if not key:
        raise SystemExit("gemini_api_key not found in env or keychain")
    return key


def _default_llm_caller(prompt: str) -> tuple[int, str, str]:
    system = "You are a precise thematic tagger. Return only valid JSON as instructed."
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{_GEMINI_MODEL}:generateContent?key={_load_gemini_key()}"
    )
    body = json.dumps({
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4096},
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            d = json.loads(resp.read())
        text = d["candidates"][0]["content"]["parts"][0]["text"]
        cost = round(len(prompt) / 4 * _PRICE["in"] + len(text) / 4 * _PRICE["out"], 5)
        return 0, text, str(cost)
    except Exception as exc:  # noqa: BLE001
        return 1, "", str(exc)


def _norm_tag(t: str) -> str:
    return " ".join(str(t).strip().lower().split())[:40]


def _parse(stdout: str) -> dict:
    raw = stdout.strip()
    if raw.startswith("```"):
        raw = "\n".join(l for l in raw.splitlines() if not l.startswith("```")).strip()
    return json.loads(raw)


def _untagged_doctrine(conn) -> list[tuple[str, str]]:
    rows = conn.execute(
        """SELECT a.id, a.body FROM atoms a
           WHERE a.type='doctrine'
             AND NOT EXISTS (SELECT 1 FROM atom_topic_tags t WHERE t.atom_id=a.id)
           ORDER BY a.id"""
    ).fetchall()
    out = []
    for r in rows:
        try:
            text = (json.loads(r["body"]).get("text_en") or "").strip()
        except Exception:
            text = ""
        out.append((r["id"], text))
    return out


def tag_all(*, dry_run: bool = False, limit: int | None = None,
            cost_cap: float = DEFAULT_COST_CAP_USD,
            llm_caller: LLMCaller | None = None) -> TagSummary:
    caller = llm_caller or _default_llm_caller
    conn = get_connection()
    candidates = _untagged_doctrine(conn)
    summary = TagSummary(candidates=len(candidates))
    if limit is not None:
        candidates = candidates[:limit]
    if dry_run:
        return summary

    for start in range(0, len(candidates), BATCH_SIZE):
        if summary.cost_usd >= cost_cap:
            summary.errors.append(f"cost cap ${cost_cap} reached — stopped at {summary.tagged} tagged")
            break
        batch = candidates[start:start + BATCH_SIZE]
        passages = "\n\n".join(f"[{i}] {text[:900]}" for i, (_id, text) in enumerate(batch))
        prompt = _PROMPT_TMPL.format(min_tags=MIN_TAGS, max_tags=MAX_TAGS,
                                     vocab=", ".join(_SEED_VOCAB), passages=passages)
        rc, stdout, cost_str = caller(prompt)
        summary.batches += 1
        try:
            summary.cost_usd = round(summary.cost_usd + float(cost_str), 5)
        except (ValueError, TypeError):
            pass
        if rc != 0:
            summary.errors.append(f"batch @{start}: {cost_str}")
            continue
        try:
            results = _parse(stdout).get("results", [])
        except json.JSONDecodeError as exc:
            summary.errors.append(f"batch @{start}: JSON parse {exc}")
            continue
        by_i = {int(r["i"]): r.get("tags", []) for r in results if "i" in r}
        for i, (atom_id, _text) in enumerate(batch):
            tags = [_norm_tag(t) for t in by_i.get(i, []) if _norm_tag(t)]
            if not tags:
                continue
            for tag in tags[:MAX_TAGS]:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO atom_topic_tags (atom_id, tag) VALUES (?, ?)",
                    (atom_id, tag),
                )
                summary.tags_written += cur.rowcount
            summary.tagged += 1
        conn.commit()
    return summary


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="WC2 doctrine concept-tagger (D19)")
    p.add_argument("--dry-run", action="store_true", help="Count untagged doctrine atoms; no LLM, no write")
    p.add_argument("--limit", type=int, default=None, help="Tag at most N atoms (sample run)")
    p.add_argument("--cost-cap", type=float, default=DEFAULT_COST_CAP_USD, help="Abort when cumulative cost reaches this")
    args = p.parse_args()
    s = tag_all(dry_run=args.dry_run, limit=args.limit, cost_cap=args.cost_cap)
    flag = " (dry-run)" if args.dry_run else ""
    print(f"Doctrine concept-tagging{flag}:")
    print(f"  untagged candidates: {s.candidates}")
    if not args.dry_run:
        print(f"  tagged: {s.tagged}  tags written: {s.tags_written}  batches: {s.batches}  cost: ${s.cost_usd}")
        for e in s.errors:
            print(f"  ! {e}")
    else:
        print("  (dry-run: no LLM calls, no writes) — re-run without --dry-run to tag")
    return 1 if s.errors else 0


if __name__ == "__main__":
    sys.exit(main())
