"""noise_router.py — Wave I (I2): Two-pass noise routing.

Pass 1 (zero cost): rule-based pre-pass strips structurally obvious noise —
isnads, biographical preambles, repetitive lecture openers, greetings.
Pass 2 (Sonnet only): ambiguous survivors go to Sonnet for context-sensitive
noise decisions.

Hard constraint: esoteric, quran, hadith, ta'wil, haqaiq, daqaiq, poetry,
reality, sharia paragraphs are excluded from the noise candidate pool entirely.

Output: _system/noise-stripped.jsonl with per-paragraph action + pass.

CLI usage:
    python3 scripts/podcast/phases/noise_router.py <book-dir> [--dry-run]
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent  # scripts/podcast
sys.path.insert(0, str(_HERE))

from _paths import REPO_ROOT  # noqa: E402
from _rules import R_NOISE_PROTECTED_CATEGORIES, R_NOISE_RULE_PATTERNS  # noqa: E402

_ARABIC_RE = re.compile(
    r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]"
)


@dataclass
class ParagraphDecision:
    para_idx: int
    text_preview: str      # first 80 chars
    action: str            # "keep" | "delete" | "improve"
    routing_pass: str      # "protected" | "rule" | "sonnet"
    reason: str
    confidence: float


def _is_protected(para: str) -> bool:
    """Return True if paragraph contains protected content (never noise-candidate)."""
    if _ARABIC_RE.search(para):
        return True
    lower = para.lower()
    for cat in R_NOISE_PROTECTED_CATEGORIES:
        if cat.replace("_", " ") in lower or cat in lower:
            return True
    return False


def _pass1_rule(para: str) -> ParagraphDecision | None:
    """Apply rule patterns. Returns a decision if matched, else None (send to Sonnet)."""
    for pattern, reason_label in R_NOISE_RULE_PATTERNS:
        if pattern.search(para):
            return ParagraphDecision(
                para_idx=0,
                text_preview=para[:80],
                action="delete",
                routing_pass="rule",
                reason=reason_label,
                confidence=0.92,
            )
    return None


def _pass2_sonnet(paragraphs: list[tuple[int, str]]) -> list[ParagraphDecision]:
    """Ask Sonnet to evaluate ambiguous paragraphs."""
    if not paragraphs:
        return []

    try:
        import anthropic  # type: ignore[import]
    except ImportError:
        # Graceful degradation: keep everything if Sonnet unavailable
        return [
            ParagraphDecision(
                para_idx=idx, text_preview=text[:80], action="keep",
                routing_pass="sonnet-skip", reason="anthropic not installed",
                confidence=0.5,
            )
            for idx, text in paragraphs
        ]

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return [
            ParagraphDecision(
                para_idx=idx, text_preview=text[:80], action="keep",
                routing_pass="sonnet-skip", reason="no API key",
                confidence=0.5,
            )
            for idx, text in paragraphs
        ]

    client = anthropic.Anthropic(api_key=api_key)
    para_text = "\n\n".join(f"[{idx}] {text[:400]}" for idx, text in paragraphs)

    system = (
        "You are a scholarly text noise detector. Classify each paragraph:\n"
        "- delete: pure padding, editorial filler, repetitive openers, biographical"
        " preambles that add no doctrinal value\n"
        "- improve: awkward phrasing but contains substantive content\n"
        "- keep: substantive content that teaches something\n\n"
        "IMPORTANT: Never mark for deletion any paragraph containing spiritual,"
        " doctrinal, scriptural, or philosophical content.\n\n"
        "Respond with JSON array: [{\"idx\": N, \"action\": \"keep|delete|improve\","
        " \"confidence\": 0.0-1.0, \"reason\": \"...\"}]"
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": f"Evaluate:\n\n{para_text}"}],
        )
        raw = response.content[0].text if response.content else "[]"
        start, end = raw.find("["), raw.rfind("]") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON array in response")
        items = json.loads(raw[start:end])
    except Exception:  # noqa: BLE001
        items = [{"idx": idx, "action": "keep", "confidence": 0.5,
                  "reason": "sonnet-error"} for idx, _ in paragraphs]

    idx_map = {idx: text for idx, text in paragraphs}
    results = []
    for item in items:
        idx = item.get("idx", -1)
        text = idx_map.get(idx, "")
        results.append(ParagraphDecision(
            para_idx=idx,
            text_preview=text[:80],
            action=item.get("action", "keep"),
            routing_pass="sonnet",
            reason=item.get("reason", ""),
            confidence=float(item.get("confidence", 0.5)),
        ))
    return results


def route_chapter(chapter_txt: Path, *, dry_run: bool = False) -> list[ParagraphDecision]:
    """Route all paragraphs of a chapter through the two-pass noise router."""
    text = chapter_txt.read_text(encoding="utf-8")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    decisions: list[ParagraphDecision] = []
    sonnet_queue: list[tuple[int, str]] = []

    for i, para in enumerate(paragraphs):
        if _is_protected(para):
            decisions.append(ParagraphDecision(
                para_idx=i, text_preview=para[:80], action="keep",
                routing_pass="protected", reason="protected-category", confidence=1.0,
            ))
            continue

        rule_decision = _pass1_rule(para)
        if rule_decision:
            rule_decision.para_idx = i
            decisions.append(rule_decision)
        else:
            sonnet_queue.append((i, para))

    # Pass 2: Sonnet for ambiguous survivors
    if not dry_run and sonnet_queue:
        sonnet_decisions = _pass2_sonnet(sonnet_queue)
        for d in sonnet_decisions:
            decisions.append(d)
    elif dry_run:
        for idx, para in sonnet_queue:
            decisions.append(ParagraphDecision(
                para_idx=idx, text_preview=para[:80], action="keep",
                routing_pass="sonnet-skip[dry-run]", reason="dry-run", confidence=0.5,
            ))

    decisions.sort(key=lambda d: d.para_idx)
    return decisions


def run_book_noise_routing(book_dir: Path, *, dry_run: bool = False) -> dict:
    """Route all chapters of a book and write noise-stripped.jsonl."""
    chapters_dir = book_dir / "chapters"
    system_dir = book_dir / "_system"
    system_dir.mkdir(parents=True, exist_ok=True)

    out_path = system_dir / "noise-stripped.jsonl"
    chapter_files = sorted(chapters_dir.glob("ch*.txt"))

    results = {
        "chapters_processed": 0,
        "total_paragraphs": 0,
        "deleted_rule": 0,
        "deleted_sonnet": 0,
        "kept": 0,
        "dry_run": dry_run,
    }

    records = []
    for cf in chapter_files:
        decisions = route_chapter(cf, dry_run=dry_run)
        for d in decisions:
            records.append({
                "chapter": cf.stem,
                "para_idx": d.para_idx,
                "action": d.action,
                "pass": d.routing_pass,
                "reason": d.reason,
                "confidence": d.confidence,
                "preview": d.text_preview,
            })
            if d.action == "delete" and d.routing_pass == "rule":
                results["deleted_rule"] += 1
            elif d.action == "delete" and d.routing_pass == "sonnet":
                results["deleted_sonnet"] += 1
            else:
                results["kept"] += 1
            results["total_paragraphs"] += 1
        results["chapters_processed"] += 1

    if not dry_run:
        with out_path.open("w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return results


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Two-pass noise router.")
    parser.add_argument("book_dir", type=Path, help="Book directory (CONTENT/drafts/books/<slug>)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run_book_noise_routing(args.book_dir, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
