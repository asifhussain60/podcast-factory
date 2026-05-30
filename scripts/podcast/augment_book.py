#!/usr/bin/env python3
"""augment_book.py — WC8 holistic pipeline: enrich the unified book with wisdom corpus atoms.

Sits between reconcile_book.py and segment_book.py. Reads the unified-book.md produced
by reconcile_book.py and enriches each section with relevant atoms from the wisdom
corpus (knowledge.db), using Gemini to select and integrate them.

DESIGN PRINCIPLES
  - Augmentation happens ONCE on the full unified text, BEFORE episode segmentation.
  - The same atom is never used twice within the same book (tracked in augmentation-ledger.json).
  - Cross-book reuse is allowed but flagged (atom.first_seen_book != current book slug).
  - Tradition safety: atoms are triaged as "universal_islamic" vs "tradition_specific" so
    cross-tradition injection is principled (e.g. Fatimid atoms into a Ghazali/Sunni text).
  - When KASHKOLE/KQUR/KSESSIONS atoms are ingested via ingest_mcp_corpus.py (plan B5),
    they land in knowledge.db and are automatically picked up on the next --force run.

USAGE
    python3 scripts/podcast/augment_book.py --slug ayyuhal-walad
    python3 scripts/podcast/augment_book.py --slug ayyuhal-walad --force
    python3 scripts/podcast/augment_book.py --slug ayyuhal-walad --dry-run

OUTPUTS
    _system/unified-augmented.md       — enriched unified text
    _system/augmentation-ledger.json   — per-section atom usage log
    _system/cost-ledger.json           — appended

COST (~$0.07 Gemini)
    Triage call (1 × Gemini Flash):         ~$0.005
    Per-section injection (~20 sections):   ~$0.060
    Total:                                  ~$0.065
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from _paths import REPO_ROOT, resolve_content  # noqa: E402

PRICE_IN  = 0.000_000_1   # $/char Gemini Flash input
PRICE_OUT = 0.000_000_4   # $/char output

KB_PATH = REPO_ROOT / "content" / "knowledge-base" / "knowledge.db"

# Tags that are safe to inject across Islamic tradition boundaries (shared heritage)
SAFE_TAGS: frozenset[str] = frozenset({
    "Moral Advice and Ethics",
    "Hadith Commentary",
    "Rulings of Sharia",
    "Meaning of a Story",
    "Prophetic Hadith",
})

# Tags that are Ismaili-specific — do NOT inject into non-Ismaili texts
TRADITION_SPECIFIC_TAGS: frozenset[str] = frozenset({
    "Knowledge of the Esoteric (Batin)",
    "Knowledge of Ali",
    "Meaning of Sharia Command (Tawil)",
    "Meaning of Daaim al-Tahara",
})

# Ghazali / Sunni-Sufi thematic keywords for keyword-overlap scoring
GHAZALI_THEMES: list[str] = [
    "knowledge", "action", "sincerity", "ikhlas", "worship", "ibada",
    "nafs", "soul", "heart", "qalb", "dhikr", "remembrance",
    "dunya", "world", "akhira", "hereafter", "death", "tawbah", "repentance",
    "prayer", "salat", "tahajjud", "night prayer", "tawakkul", "trust",
    "zuhd", "asceticism", "scholar", "student", "teacher", "murshid",
    "patience", "sabr", "gratitude", "shukr", "servitude", "obedience",
    "ethics", "moral", "virtue", "guidance", "hikmah", "wisdom",
    "quran", "hadith", "sunnah", "prophet", "fiqh", "sharia",
]


# ---------------------------------------------------------------------------
# Gemini helpers
# ---------------------------------------------------------------------------

def _load_key() -> str:
    env = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env:
        return env.strip()
    r = subprocess.run(
        ["security", "find-generic-password", "-s", "gemini_api_key",
         "-a", os.environ.get("USER", ""), "-w"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise SystemExit("gemini_api_key not in keychain")
    return r.stdout.strip()


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
            "temperature": 0.15,
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


# ---------------------------------------------------------------------------
# Knowledge corpus helpers
# ---------------------------------------------------------------------------

def _load_atoms() -> list[dict]:
    """Load all atoms from knowledge.db with their tags and text_en."""
    conn = sqlite3.connect(str(KB_PATH))
    rows = conn.execute(
        "SELECT id, type, body, tradition, first_seen_book FROM atoms"
    ).fetchall()

    tag_map: dict[str, list[str]] = {}
    for atom_id, tag in conn.execute(
        "SELECT atom_id, tag FROM atom_topic_tags"
    ).fetchall():
        tag_map.setdefault(atom_id, []).append(tag)

    conn.close()

    atoms = []
    for atom_id, atype, body_json, tradition, first_seen_book in rows:
        try:
            body = json.loads(body_json)
        except (json.JSONDecodeError, TypeError):
            continue
        text_en = body.get("text_en", "")
        if not text_en or not text_en.strip():
            continue
        tags = tag_map.get(atom_id, [])
        atoms.append({
            "id": atom_id,
            "type": atype,
            "text_en": text_en.strip(),
            "tradition": tradition,
            "first_seen_book": first_seen_book or "unknown",
            "tags": tags,
        })
    return atoms


def _keyword_score(text: str) -> int:
    """Score text relevance to Ghazali themes by keyword overlap."""
    t = text.lower()
    return sum(1 for kw in GHAZALI_THEMES if kw in t)


def _is_safe_for_cross_tradition(atom: dict, allow_untagged: bool = False) -> bool:
    """Return True if this atom is safe to inject into a cross-tradition text."""
    tags = atom.get("tags", [])
    if not tags:
        # Untagged: allow if caller permits (will be triaged by Gemini)
        return allow_untagged
    if any(t in TRADITION_SPECIFIC_TAGS for t in tags):
        return False
    if any(t in SAFE_TAGS for t in tags):
        return True
    return False


def _triage_untagged_atoms(atoms: list[dict], slug: str) -> tuple[list[dict], float]:
    """
    Ask Gemini to classify untagged atoms as 'universal_islamic' or 'tradition_specific'.
    Returns (triaged_universal_atoms, cost).
    """
    untagged = [a for a in atoms if not a["tags"]]
    if not untagged:
        return [], 0.0

    # Send in batches of 50 to stay within context limits
    universal: list[dict] = []
    total_cost = 0.0

    for batch_start in range(0, len(untagged), 50):
        batch = untagged[batch_start:batch_start + 50]
        index = [
            {"id": a["id"], "preview": a["text_en"][:300]}
            for a in batch
        ]
        system = (
            "You are classifying Islamic teaching passages for cross-tradition compatibility.\n\n"
            "Context: These passages come from a Fatimid-Ismaili teaching tradition. We need to "
            "identify which ones are 'universal_islamic' (ethics, hadith, Quran commentary, "
            "spiritual guidance applicable to any Muslim context, like Ghazali's Ayyuhal Walad) "
            "vs 'tradition_specific' (Ismaili doctrines about Imam, ta'wil/esoteric interpretation "
            "of Quran, cosmological hierarchies, or texts from Daim al-Islam/Ismaili fiqh that "
            "differ from mainstream fiqh).\n\n"
            "Respond with a JSON object ONLY:\n"
            '{"classifications": [{"id": "...", "category": "universal_islamic|tradition_specific"}]}'
        )
        user = json.dumps({"atoms": index})
        resp, cost = _gemini(system, user, max_tokens=4096)
        total_cost += cost

        try:
            start = resp.find("{")
            end = resp.rfind("}") + 1
            data = json.loads(resp[start:end])
            id_to_cat = {
                c["id"]: c["category"]
                for c in data.get("classifications", [])
            }
        except (json.JSONDecodeError, ValueError):
            id_to_cat = {}

        for a in batch:
            if id_to_cat.get(a["id"]) == "universal_islamic":
                universal.append(a)

    return universal, total_cost


# ---------------------------------------------------------------------------
# Section parsing
# ---------------------------------------------------------------------------

def _parse_sections(unified_text: str) -> list[tuple[int, str, str]]:
    """
    Parse ## Section N — Title blocks.
    Returns list of (section_number, title, content).
    """
    pattern = re.compile(r"^## Section (\d+)(?:\s*—\s*(.+))?$", re.MULTILINE)
    matches = list(pattern.finditer(unified_text))
    sections = []
    for i, m in enumerate(matches):
        num = int(m.group(1))
        title = (m.group(2) or "").strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(unified_text)
        content = unified_text[start:end].strip()
        sections.append((num, title, content))
    return sections


# ---------------------------------------------------------------------------
# Per-section enrichment
# ---------------------------------------------------------------------------

_ENRICH_SYSTEM = """\
You are adding a wisdom enrichment addendum to a section of Ghazali's *Ayyuhal Walad*
(a Sunni-Sufi spiritual letter).

Your task:
1. Read the section carefully to understand its central counsel.
2. Review the candidate atoms. They come from various Islamic teaching traditions.
3. Select 0–2 atoms that GENUINELY deepen the section's teaching. Criteria:
   - The atom resonates with the section's central counsel or question.
   - The atom adds a dimension the section does not already cover.
   - Spiritually compatible with Ghazali's voice (ethics, sincerity, worship, soul).
   - Do NOT select atoms that introduce Ismaili-specific doctrine into Ghazali's text.
4. If you select atoms: write a 2–4 sentence enrichment addendum (NOT the full section —
   ONLY the addendum text). Introduce naturally, e.g.:
   "A parallel counsel from the tradition notes..." or "This teaching echoes..."
   Preserve Ghazali's contemplative register.
5. If no atom genuinely enriches this section, respond with only: USED_ATOMS: []

Response format — EXACTLY:
<addendum text here, or empty if none>
USED_ATOMS: ["atom_id_1", "atom_id_2"]
"""


def _enrich_section(section_text: str, candidates: list[dict]) -> tuple[str, list[str], float]:
    """
    Send a section + candidates to Gemini; get back an addendum to append.
    Returns (addendum_text_or_empty, used_atom_ids, cost).
    The caller appends addendum to the original section — original text is NEVER replaced.
    """
    atom_list = [
        f"[ATOM {a['id']}]\n{a['text_en'][:500]}"
        for a in candidates[:15]
    ]
    user = (
        "=== SECTION ===\n\n" + section_text + "\n\n"
        "=== CANDIDATE ATOMS ===\n\n" + "\n\n".join(atom_list)
    )
    resp, cost = _gemini(_ENRICH_SYSTEM, user, max_tokens=1024)

    used_ids: list[str] = []
    lines = resp.strip().splitlines()
    addendum_lines = []
    for line in lines:
        if line.startswith("USED_ATOMS:"):
            try:
                raw = line[len("USED_ATOMS:"):].strip()
                used_ids = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                used_ids = []
        else:
            addendum_lines.append(line)

    addendum = "\n".join(addendum_lines).strip()
    return addendum, used_ids, cost


# ---------------------------------------------------------------------------
# Cost ledger
# ---------------------------------------------------------------------------

def _log_cost(slug: str, entry: dict) -> None:
    p = resolve_content(slug) / "_system" / "cost-ledger.json"
    led = json.loads(p.read_text()) if p.exists() else {"slug": slug, "entries": [], "total_usd": 0.0}
    led["entries"].append(entry)
    led["total_usd"] = round(sum(e.get("cost_usd", 0.0) for e in led["entries"]), 4)
    p.write_text(json.dumps(led, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Main augmentation pass
# ---------------------------------------------------------------------------

def augment(slug: str, *, dry_run: bool = False, force: bool = False) -> Path:
    book_dir = resolve_content(slug)
    unified_path = book_dir / "_system" / "unified-book.md"
    out_path = book_dir / "_system" / "unified-augmented.md"
    ledger_path = book_dir / "_system" / "augmentation-ledger.json"

    if out_path.exists() and not force:
        print(f"  unified-augmented.md already exists — skip (--force to re-run)")
        return out_path

    if not unified_path.exists():
        raise FileNotFoundError(
            f"unified-book.md not found at {unified_path}. Run reconcile_book.py first."
        )

    unified_text = unified_path.read_text(encoding="utf-8")
    sections = _parse_sections(unified_text)
    print(f"  Loaded {len(sections)} sections from unified-book.md")

    # Load atoms
    print(f"  Loading wisdom corpus atoms from knowledge.db…", end="", flush=True)
    all_atoms = _load_atoms()
    print(f" {len(all_atoms)} atoms loaded")

    # Separate: safe-tagged vs untagged vs tradition-specific
    safe_tagged  = [a for a in all_atoms if _is_safe_for_cross_tradition(a, allow_untagged=False)]
    untagged_raw = [a for a in all_atoms if not a["tags"]]
    print(f"  Safe-tagged: {len(safe_tagged)}  |  Untagged (pending triage): {len(untagged_raw)}")

    total_cost = 0.0

    # Triage untagged atoms with Gemini
    if untagged_raw and not dry_run:
        print(f"  Triaging {len(untagged_raw)} untagged atoms for cross-tradition safety…", end="", flush=True)
        universal_untagged, triage_cost = _triage_untagged_atoms(untagged_raw, slug)
        total_cost += triage_cost
        print(f" {len(universal_untagged)} universal  ~${triage_cost:.4f}")
    else:
        universal_untagged = []

    candidate_pool = safe_tagged + universal_untagged
    # Score all candidates by keyword relevance to Ghazali themes
    for a in candidate_pool:
        a["_score"] = _keyword_score(a["text_en"])

    candidate_pool.sort(key=lambda a: a["_score"], reverse=True)
    print(f"  Candidate pool: {len(candidate_pool)} atoms (top keyword score: {candidate_pool[0]['_score'] if candidate_pool else 0})")

    used_atom_ids: set[str] = set()
    section_ledger: list[dict] = []
    enriched_sections: list[str] = []

    # Header (everything before first ## Section)
    first_section_match = re.search(r"^## Section \d+", unified_text, re.MULTILINE)
    preamble = unified_text[: first_section_match.start()].rstrip() if first_section_match else ""

    for sec_num, sec_title, sec_content in sections:
        if dry_run:
            enriched_sections.append(sec_content)
            continue

        # Find candidates not yet used in this book
        available = [a for a in candidate_pool if a["id"] not in used_atom_ids]
        if not available:
            enriched_sections.append(sec_content)
            section_ledger.append({"section": sec_num, "title": sec_title, "atoms_used": [], "note": "atom_pool_exhausted"})
            continue

        # Re-score candidates against this section's specific text
        sec_lower = sec_content.lower()
        for a in available:
            a["_section_score"] = sum(1 for kw in GHAZALI_THEMES if kw in sec_lower and kw in a["text_en"].lower())
        available.sort(key=lambda a: (a["_section_score"], a["_score"]), reverse=True)
        top_candidates = available[:15]

        print(f"  Section {sec_num} ({sec_title[:40]}…): enriching with {len(top_candidates)} candidates…",
              end="", flush=True)

        enriched, atom_ids_used, cost = _enrich_section(sec_content, top_candidates)
        total_cost += cost

        # Record usage
        used_atom_ids.update(atom_ids_used)

        # Build ledger entry
        atoms_used_detail = []
        for aid in atom_ids_used:
            atom = next((a for a in all_atoms if a["id"] == aid), None)
            if atom:
                cross_book = atom["first_seen_book"] != "wisdom" and atom["first_seen_book"] != slug
                atoms_used_detail.append({
                    "atom_id": aid,
                    "tradition": atom["tradition"],
                    "tags": atom["tags"],
                    "first_seen_book": atom["first_seen_book"],
                    "cross_book_reuse": cross_book,
                })

        section_ledger.append({
            "section": sec_num,
            "title": sec_title,
            "atoms_used": atoms_used_detail,
            "cost_usd": round(cost, 5),
        })

        # Append the addendum to original section — original is NEVER replaced.
        if enriched and atom_ids_used:
            final_section = sec_content + "\n\n> **Wisdom enrichment:** " + enriched
        else:
            final_section = sec_content
        enriched_sections.append(final_section)
        used_str = f"atoms={atom_ids_used}" if atom_ids_used else "no atoms selected"
        print(f" {used_str}  ~${cost:.4f}")

    # Assemble enriched unified text
    out_text = (preamble + "\n\n" if preamble else "") + "\n\n".join(enriched_sections) + "\n"
    word_count_in  = len(unified_text.split())
    word_count_out = len(out_text.split())

    if not dry_run:
        out_path.write_text(out_text, encoding="utf-8")

        ledger = {
            "slug": slug,
            "augmented_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "total_atoms_in_corpus": len(all_atoms),
            "candidate_pool_size": len(candidate_pool),
            "sections_enriched": sum(1 for s in section_ledger if s.get("atoms_used")),
            "total_atoms_used": len(used_atom_ids),
            "unique_atom_ids": sorted(used_atom_ids),
            "word_count_before": word_count_in,
            "word_count_after": word_count_out,
            "total_cost_usd": round(total_cost, 4),
            "sections": section_ledger,
        }
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")

        _log_cost(slug, {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "op": "augment_book",
            "service": "gemini/gemini-2.5-flash",
            "word_count_before": word_count_in,
            "word_count_after": word_count_out,
            "cost_usd": round(total_cost, 4),
        })

        delta = word_count_out - word_count_in
        print(f"\n  Words: {word_count_in:,} → {word_count_out:,} (+{delta:,})")
        print(f"  Atoms used: {len(used_atom_ids)} / {len(candidate_pool)} candidates")
        print(f"  Total augmentation cost: ~${total_cost:.4f}")

    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="WC8 wisdom-corpus augmentation of unified book text.")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--dry-run", action="store_true", help="Parse and plan without Gemini calls")
    ap.add_argument("--force", action="store_true", help="Re-run even if output exists")
    args = ap.parse_args()

    print(f"Augment book — {args.slug}")
    if not KB_PATH.exists():
        raise SystemExit(f"knowledge.db not found at {KB_PATH}")

    out = augment(args.slug, dry_run=args.dry_run, force=args.force)

    ledger = resolve_content(args.slug) / "_system" / "cost-ledger.json"
    if ledger.exists():
        total = json.loads(ledger.read_text()).get("total_usd", 0.0)
        print(f"Running total cost: ${total:.2f}")
    if not args.dry_run:
        print(f"Output: {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
