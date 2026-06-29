#!/usr/bin/env python3
"""categorize_atoms.py — Wave L-3: assign content_level to doctrine atoms.

Classifies each uncategorized (content_level IS NULL) doctrine atom into one of
the six ladder levels (Wave M) so the augmentation gate can restrict a book to
its own level and below:

    general   — biographical / historical accounts
    advanced  — advanced scholarly; legal analysis; formal exoteric commentary
    taveel    — ta'wil: allegorical / esoteric interpretation (batin)
    mamsool   — parables / exemplars: teaching the esoteric through analogy
    mabda_maad — origin-and-return: cosmological doctrine, cosmic intellects
    haqaiq    — essential realities: eternal metaphysical truths (deepest)

ONLY doctrine atoms are categorized. Quran / Hadith / Term / Etymology / quote
atoms are universal resources and are left NULL (never level-gated).

Two-stage classification:
  1. Heuristic prior (zero-cost) from the atom's topic tags — strong, unambiguous
     tag signals map directly to a level with high confidence.
  2. Gemini 2.5 Flash for everything the heuristic can't place confidently, given
     the atom's tags + a text snippet + the 4-level rubric. Returns level +
     confidence + one-line reason.

Outputs (written to content/knowledge-base/):
  - categorize-report.json   — every atom: id, proposed_level, confidence, source, reason
  - categorize-review.json    — only atoms below --threshold (for human review)

`--apply` writes content_level to the DB for atoms at/above --threshold confidence.
Without `--apply` it is a dry run (report only, no DB writes).

USAGE
    python3 scripts/podcast/knowledge/categorize_atoms.py --dry-run
    python3 scripts/podcast/knowledge/categorize_atoms.py --apply --threshold 0.85

Authority: Wave L plan §L-3. Cost: ~$0.05 Gemini Flash for ~628 atoms.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS_PODCAST = _HERE.parent
sys.path.insert(0, str(_SCRIPTS_PODCAST))

import _db  # noqa: E402
from _rules import CONTENT_LEVEL_LADDER  # noqa: E402

REPO_ROOT = _SCRIPTS_PODCAST.parents[1]
KB_DIR = REPO_ROOT / "content" / "knowledge-base"

PRICE_IN = 0.000_000_1
PRICE_OUT = 0.000_000_4

# ── Heuristic tag → level priors (zero-cost fast-path) ──────────────────────
# Only STRONG, unambiguous tag signals. Anything not matched falls to Gemini.
# Most-metaphysical signal wins ties: Fatimid-Ismaili doctrine skews batin — an
# advanced-tagged atom that ALSO carries ta'wil is taveel, not advanced.
_HAQAIQ_TAGS = frozenset({
    "cosmology", "creation", "emanation", "first intellect", "universal soul",
    "hyle", "primordial matter", "primordial bodies", "metaphysics",
    "spiritual realities", "divine realities", "hidden realities", "reality",
    "realities", "eschatology", "qiyama", "qa'im", "qaim", "qāʾim",
    "cosmic cycles", "cycles", "celestial spheres", "celestial motion",
    "celestial bodies", "celestial influence", "contingency",
    "transmigration", "rebirth", "spiritual world", "abstraction",
})
_MABDA_MAAD_TAGS = frozenset({
    "mabda", "ma'ad", "mabda ma'ad", "origin and return", "origin", "return",
    "beginning and end", "emanation cycle", "cosmic hierarchy",
})
_TAVEEL_TAGS = frozenset({
    "ta'wil", "tawil", "esoteric interpretation", "esoteric meaning",
    "esoteric knowledge", "esoteric exegesis", "esoteric", "zahir batin",
    "batin", "inner meaning", "inner reality", "inner dimension",
    "hidden knowledge", "spiritual interpretation", "exoteric esoteric",
    "symbolism", "letter symbolism", "numerical symbolism", "numerology",
    "spiritual symbolism", "unveiling", "veils", "veil", "veiledness",
    "gnosis", "walayah", "walaya", "imamate", "spiritual hierarchy",
    "spiritual stations", "spiritual ascent", "interpretation",
    "inner self", "concealment", "taqiyya",
})
_ADVANCED_TAGS = frozenset({
    "sharia", "shari'a", "shariah", "ritual", "ritual law", "ritual purity",
    "prayer", "ablution", "ghusl", "wudu", "fasting", "ramadan", "hajj",
    "zakat", "charity", "alms", "worship", "obligatory prayer",
    "supererogatory prayer", "recommended prayer", "congregational prayer",
    "friday prayer", "daily prayer", "noon prayer", "afternoon prayer",
    "pillars of islam", "pillars", "hudud", "law", "divine law", "religious law",
    "purification", "ritual calendar", "lunar calendar", "ablutions",
    "adhan", "iqama", "qunut", "ruku", "prostration", "rak'ahs", "khushu",
    "fiqh", "obligation", "religious practice",
})
_GENERAL_TAGS = frozenset({
    "history", "pre-islamic arabia", "migration", "biography", "geography",
    "qadi nu'man", "salman", "pre-existence", "spiritual eras",
    "revelation cycle", "prophetic cycle", "spiritual lineage",
})


def _load_key() -> str:
    # Vault-deterministic: env -> keychain -> Azure Key Vault (llm-gemini-api-key).
    from _secrets import get_gemini_key
    return get_gemini_key()



def _gemini(system: str, user: str, *, model: str = "gemini-2.5-flash",
            max_tokens: int = 8192) -> tuple[str, float]:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={_load_key()}"
    )
    body = json.dumps({
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": max_tokens,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        d = json.loads(resp.read())
    parts = d["candidates"][0]["content"]["parts"]
    text_out = ""
    for part in parts:
        if not part.get("thought"):
            t = part.get("text", "")
            if t.strip():
                text_out = t
                break
    cost = (len(system) + len(user)) * PRICE_IN + len(text_out) * PRICE_OUT
    return text_out, round(cost, 6)


def _heuristic_level(tags: list[str]) -> tuple[str, float] | None:
    """Return (level, confidence) when a strong tag signal exists, else None.

    Precedence (Fatimid-Ismaili doctrine skews batin): haqaiq > mabda_maad >
    taveel > advanced > general. Most-metaphysical matched signal wins.
    """
    tset = {t.lower() for t in tags}
    if tset & _HAQAIQ_TAGS:
        return "haqaiq", 0.88
    if tset & _MABDA_MAAD_TAGS:
        return "mabda_maad", 0.88
    if tset & _TAVEEL_TAGS:
        return "taveel", 0.88
    if tset & _ADVANCED_TAGS:
        return "advanced", 0.86
    if tset & _GENERAL_TAGS:
        return "general", 0.86
    return None


_RUBRIC = (
    "You classify a passage of Islamic (Fatimid-Ismaili tradition) doctrine into "
    "ONE spiritual-content level. The levels form a ladder from most accessible "
    "to most metaphysical:\n"
    "  general    — biographical / historical accounts, lives of figures, eras.\n"
    "  advanced   — advanced scholarly; outward (zahir) law, ritual practice,\n"
    "               worship, hadith-based rulings, the five pillars, fiqh.\n"
    "  taveel     — inner (batin) allegorical interpretation, ta'wil, symbolism,\n"
    "               spiritual stations, the imamate's interpretive role.\n"
    "  mamsool    — teaching the esoteric through parables and exemplars;\n"
    "               'this is like…' illustrative stories with esoteric payoff.\n"
    "  mabda_maad — origin-and-return cosmology: cosmic intellects and souls,\n"
    "               emanation, eschatology of cycles, the celestial hierarchy.\n"
    "  haqaiq     — essential realities: eternal metaphysical truths that\n"
    "               transcend rational understanding; deepest esoteric level.\n\n"
    "Fatimid-Ismaili doctrine skews toward the inner levels. When a passage moves "
    "from an outward ritual to its hidden meaning, classify by the DEEPER level it "
    "ultimately teaches. Reply ONLY with strict JSON:\n"
    '{"level":"general|advanced|taveel|mamsool|mabda_maad|haqaiq","confidence":0.0-1.0,'
    '"reason":"one short sentence"}'
)


def _gemini_level(text_en: str, tags: list[str]) -> tuple[str, float, str, float]:
    """Return (level, confidence, reason, cost) from Gemini Flash."""
    snippet = text_en[:1200]
    user = json.dumps({"tags": tags[:12], "passage": snippet})
    raw, cost = _gemini(_RUBRIC, user, max_tokens=256)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{"):]
    try:
        obj = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        level = str(obj.get("level", "")).lower()
        conf = float(obj.get("confidence", 0.0))
        reason = str(obj.get("reason", ""))[:200]
        if level not in CONTENT_LEVEL_LADDER:
            return "esoteric", 0.0, f"unparseable level '{level}'", cost
        return level, conf, reason, cost
    except Exception as e:  # noqa: BLE001
        return "esoteric", 0.0, f"parse error: {e}", cost


def _load_uncategorized_doctrine() -> list[dict]:
    conn = _db.get_connection()
    rows = conn.execute(
        "SELECT id, body FROM atoms WHERE type='doctrine' AND content_level IS NULL"
    ).fetchall()
    tag_map: dict[str, list[str]] = {}
    for atom_id, tag in conn.execute("SELECT atom_id, tag FROM atom_topic_tags").fetchall():
        tag_map.setdefault(atom_id, []).append(tag)
    out = []
    for atom_id, body_json in rows:
        try:
            body = json.loads(body_json)
        except (json.JSONDecodeError, TypeError):
            continue
        out.append({
            "id": atom_id,
            "text_en": (body.get("text_en") or "").strip(),
            "tags": tag_map.get(atom_id, []),
        })
    return out


def categorize(*, apply: bool, threshold: float, use_gemini: bool) -> dict:
    atoms = _load_uncategorized_doctrine()
    report: list[dict] = []
    total_cost = 0.0
    heur_n = gem_n = 0

    for i, atom in enumerate(atoms):
        h = _heuristic_level(atom["tags"])
        if h is not None:
            level, conf = h
            report.append({"id": atom["id"], "level": level, "confidence": conf,
                           "source": "heuristic", "reason": "strong tag signal",
                           "tags": atom["tags"][:8]})
            heur_n += 1
            continue
        if not use_gemini:
            report.append({"id": atom["id"], "level": None, "confidence": 0.0,
                           "source": "unresolved", "reason": "no heuristic; gemini disabled",
                           "tags": atom["tags"][:8]})
            continue
        level, conf, reason, cost = _gemini_level(atom["text_en"], atom["tags"])
        total_cost += cost
        gem_n += 1
        report.append({"id": atom["id"], "level": level, "confidence": round(conf, 3),
                       "source": "gemini", "reason": reason, "tags": atom["tags"][:8]})
        if (i + 1) % 25 == 0:
            print(f"    …{i + 1}/{len(atoms)} classified (~${total_cost:.4f})", flush=True)

    applied = 0
    review = [r for r in report if (r["confidence"] or 0) < threshold or r["level"] is None]
    if apply:
        conn = _db.get_connection()
        for r in report:
            if r["level"] and (r["confidence"] or 0) >= threshold:
                conn.execute(
                    "UPDATE atoms SET content_level=?, "
                    "updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?",
                    (r["level"], r["id"]),
                )
                applied += 1
        conn.commit()

    KB_DIR.mkdir(parents=True, exist_ok=True)
    (KB_DIR / "categorize-report.json").write_text(
        json.dumps({"total": len(atoms), "heuristic": heur_n, "gemini": gem_n,
                    "applied": applied, "cost_usd": round(total_cost, 4),
                    "threshold": threshold, "atoms": report}, indent=2),
        encoding="utf-8",
    )
    (KB_DIR / "categorize-review.json").write_text(
        json.dumps({"count": len(review), "atoms": review}, indent=2), encoding="utf-8",
    )

    by_level: dict[str, int] = {}
    for r in report:
        if r["level"]:
            by_level[r["level"]] = by_level.get(r["level"], 0) + 1
    return {"total": len(atoms), "heuristic": heur_n, "gemini": gem_n,
            "applied": applied, "review": len(review), "cost_usd": round(total_cost, 4),
            "by_level": by_level}


def main() -> None:
    ap = argparse.ArgumentParser(description="Categorize doctrine atoms by content level (Wave L-3).")
    ap.add_argument("--apply", action="store_true", help="Write content_level to DB (default: dry run).")
    ap.add_argument("--threshold", type=float, default=0.85, help="Min confidence to apply (default 0.85).")
    ap.add_argument("--no-gemini", action="store_true", help="Heuristic only — skip Gemini calls.")
    args = ap.parse_args()

    _db.run_migrations()
    print(f"  Categorizing uncategorized doctrine atoms (apply={args.apply}, threshold={args.threshold})…")
    summary = categorize(apply=args.apply, threshold=args.threshold, use_gemini=not args.no_gemini)
    print(f"  Done. {summary}")
    print(f"  Report:  content/knowledge-base/categorize-report.json")
    print(f"  Review:  content/knowledge-base/categorize-review.json ({summary['review']} atoms below threshold)")


if __name__ == "__main__":
    main()
