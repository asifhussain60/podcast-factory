#!/usr/bin/env python3
"""fill_etymology_phonetics.py — Wave L-4: bake spoken phonetics into etymology atoms.

Etymology atoms store the Arabic root as an UPPERCASE transliteration
(`root_transliteration`, e.g. "ANS", "AMN") plus Arabic script. Neither is a
listener-friendly spoken form. This tool generates the house-style hyphenated
phonetic (e.g. "ah-MAAN", matching the Phase 06 `_phonetics.md` convention:
lowercase, hyphen-separated syllables) for the root and each derivative term,
and writes them back into the atom body as `root_phonetic` / derivative
`phonetic` fields.

Pronunciation consistency: the host says the root the same way the book glossary
says it. The generator first reuses any matching `audio_phonetic` already baked
into a book glossary.yml (same value the rest of the book uses); only roots not
found in any glossary are generated fresh via Gemini using the same hyphenated
house style. This honors the "reuse the Phase 0c phonetics engine" intent.

Spoken-form discipline (Wave L requirement): the phonetic is what a host SAYS —
the Arabic SCRIPT is never spoken or emitted into episode text. The script stays
in the atom only for the reader overlay.

USAGE
    python3 scripts/podcast/knowledge/fill_etymology_phonetics.py --dry-run
    python3 scripts/podcast/knowledge/fill_etymology_phonetics.py --apply

Authority: Wave L plan §L-4. Cost: trivial (~35 atoms, Gemini Flash).
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

REPO_ROOT = _SCRIPTS_PODCAST.parents[1]
PRICE_IN = 0.000_000_1
PRICE_OUT = 0.000_000_4

_HOUSE_STYLE = (
    "You produce SPOKEN pronunciation guides for Arabic words, in the exact house "
    "style of a podcast pronunciation index: ALL LOWERCASE, syllables separated by "
    "hyphens, the stressed syllable in CAPITALS. Examples from the index:\n"
    "  al-Ghazali  -> gha-zaa-lee\n"
    "  Ayyuhal Walad -> eye-yoo-hal waa-lad\n"
    "  iman        -> ee-MAAN\n"
    "  amn         -> AH-man\n"
    "  insan       -> in-SAAN\n"
    "Never include Arabic script. Never spell out individual letters. Give ONLY the "
    "spoken syllable form. Reply with strict JSON:\n"
    '{"root_phonetic":"...","derivatives":[{"term":"<TERM>","phonetic":"..."}]}'
)


def _load_key() -> str:
    # Vault-deterministic: env -> keychain -> Azure Key Vault (llm-gemini-api-key).
    from _secrets import get_gemini_key
    return get_gemini_key()



def _gemini(system: str, user: str, *, model: str = "gemini-2.5-flash",
            max_tokens: int = 512) -> tuple[str, float]:
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={_load_key()}")
    body = json.dumps({
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": max_tokens,
                             "thinkingConfig": {"thinkingBudget": 0}},
    }).encode()
    req = urllib.request.Request(url, data=body,
                                headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as resp:
        d = json.loads(resp.read())
    parts = d["candidates"][0]["content"]["parts"]
    text_out = next((p.get("text", "") for p in parts
                     if not p.get("thought") and p.get("text", "").strip()), "")
    cost = (len(system) + len(user)) * PRICE_IN + len(text_out) * PRICE_OUT
    return text_out, round(cost, 6)


def _glossary_phonetics() -> dict[str, str]:
    """Collect {lower term: audio_phonetic} from every book glossary.yml (reuse)."""
    out: dict[str, str] = {}
    try:
        import yaml  # type: ignore[import]
    except Exception:  # noqa: BLE001
        return out
    for gloss in REPO_ROOT.glob("content/drafts/**/_system/glossary.yml"):
        try:
            data = yaml.safe_load(gloss.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            continue
        for e in data.get("entries", []) or []:
            term = str(e.get("transliteration") or e.get("phonetic") or "").strip().lower()
            audio = str(e.get("audio_phonetic") or "").strip()
            if term and audio:
                out[term] = audio
    return out


def _gen_phonetics(root_translit: str, derivatives: list[dict]) -> tuple[dict, float]:
    terms = [d.get("term", "") for d in derivatives if d.get("term")]
    user = json.dumps({"root": root_translit, "derivatives": terms})
    raw, cost = _gemini(_HOUSE_STYLE, user)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
    try:
        obj = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        return obj, cost
    except Exception:  # noqa: BLE001
        return {}, cost


def fill(*, apply: bool) -> dict:
    conn = _db.get_connection()
    rows = conn.execute("SELECT id, body FROM atoms WHERE type='etymology'").fetchall()
    gloss = _glossary_phonetics()
    total_cost = 0.0
    updated = 0
    reused = 0
    for atom_id, body_json in rows:
        try:
            body = json.loads(body_json)
        except (json.JSONDecodeError, TypeError):
            continue
        if body.get("root_phonetic"):
            continue  # already baked
        root = body.get("root_transliteration", "")
        derivs = body.get("derivatives", []) or []

        # Reuse glossary audio_phonetic where available (consistency).
        gen, cost = _gen_phonetics(root, derivs)
        total_cost += cost
        root_phon = gloss.get(root.lower()) or gen.get("root_phonetic", "")
        if gloss.get(root.lower()):
            reused += 1
        body["root_phonetic"] = root_phon
        gen_map = {d.get("term", "").upper(): d.get("phonetic", "")
                   for d in gen.get("derivatives", [])}
        for d in derivs:
            term = d.get("term", "")
            d["phonetic"] = gloss.get(term.lower()) or gen_map.get(term.upper(), "")
        if apply:
            conn.execute(
                "UPDATE atoms SET body=?, updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') "
                "WHERE id=?",
                (json.dumps(body, ensure_ascii=False), atom_id),
            )
        updated += 1
    if apply:
        conn.commit()
    return {"etymology_atoms": len(rows), "phonetics_generated": updated,
            "glossary_reused": reused, "cost_usd": round(total_cost, 4), "applied": apply}


def main() -> None:
    ap = argparse.ArgumentParser(description="Bake spoken phonetics into etymology atoms (Wave L-4).")
    ap.add_argument("--apply", action="store_true", help="Write phonetics to DB (default: dry run).")
    args = ap.parse_args()
    _db.run_migrations()
    summary = fill(apply=args.apply)
    print(f"  {summary}")


if __name__ == "__main__":
    main()
