#!/usr/bin/env python3
"""estimate_cost.py — pre-run cost forecast + estimate-vs-actual reconciliation.

The pipeline already records ACTUAL spend per call (_cost_ledger.py) and sums it
(cost_ledger_summary.py). This module adds the two missing bookends:

  • PRE-RUN ESTIMATE  — forecast spend before the orchestrator runs, from the
    book's content_profile + scope (episode count, source size, video on/off).
    Written to <book_dir>/_system/cost-estimate.json. Surfaced at the 0f review
    halt so the forecast lands at the Tier-2 go/no-go gate.

  • RECONCILIATION    — diff the estimate against the actual ledger after the run
    (estimate vs actual, per service, notional-vs-real, % variance). Folded into
    cost-estimate.json under "reconciliation" and runnable at finalize.

DESIGN
  - Rate constants are NEVER re-hardcoded here. The metered-service prices
    (Gemini images/text, Azure) are IMPORTED from _cost_ledger.py — the single
    source of truth. Claude notional per-episode volumes are CALIBRATED from
    shipped books' real ledgers (defaults below come from Ayyuhal Walad).
  - "Notional" = flat-rate Claude Max via `claude -p` ($0 marginal, covered by
    the subscription). "Real" = metered money (Gemini + Azure). The estimate
    separates them, because conflating them overstates real cost ~50x.

USAGE
    python3 scripts/podcast/estimate_cost.py <slug-or-path>            # write estimate
    python3 scripts/podcast/estimate_cost.py <slug> --episodes 12      # override ep count
    python3 scripts/podcast/estimate_cost.py <slug> --json             # stdout JSON
    python3 scripts/podcast/estimate_cost.py <slug> --reconcile        # estimate vs actual

EXIT CODES
    0 — estimate (or reconciliation) written / printed
    1 — book not found / config unreadable
    2 — --reconcile requested but no estimate or no ledger exists
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import yaml

# Single source of truth for metered-service rates — never re-hardcode prices.
# AZURE_PRICING_USD is re-exported as part of this module's contract
# (identity-asserted by test_fiction_pipeline's single-source-of-truth check).
from _cost_ledger import (
    AZURE_PRICING_USD as AZURE_PRICING_USD,
)
from _cost_ledger import (
    GEMINI_PRICING_USD,
    PRICING_USD_PER_MILLION_TOKENS,
)
from _paths import find_content
from generate_video_layer import IMAGE_COST_ESTIMATE, IMAGES_PER_EP_SCENIC

# ─── Calibration (NOTIONAL Claude-on-Max, USD per episode) ────────────────────
#
# Derived from the shipped Ayyuhal Walad ledger (4 episodes, islamic_scholarly,
# opus-4-8): per-chapter authoring incl. challenger convergence ≈ $18.80/ep;
# 0d chapter design ≈ $5.0/ep; book compose+illustrate ≈ $2.9/ep. These are
# NOTIONAL (flat-rate Max) — they forecast token volume, not real money. Refresh
# from real ledgers as more books ship (reconciliation feeds this back).
CALIB_PER_EPISODE_NOTIONAL_USD = {
    "per_chapter_authoring": 18.80,  # framing + build + challenger convergence
    "phase_0d_design": 5.00,  # chapter/episode design
    "book_compose": 2.90,  # reading-edition compose + illustrate
}
# Phase 0b windowed refine — small, sonnet-tier; modeled per 1k source words.
CALIB_0B_NOTIONAL_USD_PER_1K_WORDS = 0.02
# Phase 0e enrichment per episode (islamic_scholarly only; fiction/technical skip).
CALIB_0E_NOTIONAL_USD_PER_EPISODE = 0.74

# Claude-translation model (fiction non-English source). Output tokens dominate.
# english_words ≈ source_chars * CHARS_TO_EN_WORDS; output_tokens ≈ words * 1.3;
# notional cost via opus output rate; a windowing-overhead multiplier covers
# per-window prompt re-send + occasional retries.
CHARS_TO_EN_WORDS = 0.70
WORDS_TO_OUTPUT_TOKENS = 1.30
TRANSLATION_OVERHEAD_FACTOR = 1.5
_OPUS_OUTPUT_USD_PER_M = PRICING_USD_PER_MILLION_TOKENS["claude-opus-4-8"][1]  # 75.0

# Default episode count when scope is unknown and source size is unavailable.
DEFAULT_EPISODE_COUNT = 12

# Words per consolidated fiction episode (rough) — used to back out an episode
# count from source size. Set to the upper-middle of the "extended" tier band
# (5,500–9,500) because fiction CONSOLIDATES adjacent chapters into fuller episodes.
WORDS_PER_EPISODE_FICTION = 7000


def _resolve_book_dir(arg: str) -> Path:
    p = Path(arg)
    if p.exists() and (p / "_system").is_dir():
        return p.resolve()
    found = find_content(arg)
    if found:
        return found[2]
    raise FileNotFoundError(f"book not found: {arg!r}")


def _read_config(book_dir: Path) -> dict:
    cfg_path = book_dir / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return {}
    try:
        return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _count_source_words(book_dir: Path) -> int:
    """Best-effort source word count: refined English if present, else raw source."""
    text_dir = book_dir / "_system" / "source" / "text"
    for name in ("refined-english.md", "raw-extract.md"):
        p = text_dir / name
        if p.exists():
            return len(p.read_text(encoding="utf-8", errors="ignore").split())
    # Fall back to any source file under _system/source/
    src = book_dir / "_system" / "source"
    if src.exists():
        total = 0
        for f in src.rglob("*"):
            if f.is_file() and f.suffix.lower() in (".md", ".txt", ".html"):
                total += len(f.read_text(encoding="utf-8", errors="ignore").split())
        return total
    return 0


def _count_source_chars(book_dir: Path) -> int:
    """Char count of the original source (for translation forecasting)."""
    src = book_dir / "_system" / "source"
    if not src.exists():
        return 0
    total = 0
    for f in src.rglob("*"):
        if f.is_file() and f.suffix.lower() in (".md", ".txt", ".html"):
            total += len(f.read_text(encoding="utf-8", errors="ignore"))
    return total


def estimate(book_dir: Path, *, episodes: int | None = None) -> dict:
    """Compute a cost forecast for a book. Returns the estimate dict."""
    cfg = _read_config(book_dir)
    profile = str(cfg.get("content_profile", "islamic_scholarly")).strip()
    video_enabled = bool(cfg.get("enable_video", False))
    source_language = str(cfg.get("source_language", "en")).strip().lower()
    is_fiction = profile == "fiction"
    is_islamic = profile == "islamic_scholarly"

    source_words = _count_source_words(book_dir)
    source_chars = _count_source_chars(book_dir)

    # English-word volume drives the episode count. For a non-English source the
    # raw source_words count is meaningless (Chinese has no whitespace word breaks),
    # so estimate the post-translation English words from char count instead.
    if source_language not in ("en", "english", ""):
        est_en_words = int(source_chars * CHARS_TO_EN_WORDS)
    else:
        est_en_words = source_words

    if episodes is None:
        explicit = int(cfg.get("estimated_episode_count") or 0)
        episodes = explicit or (
            max(1, round(est_en_words / WORDS_PER_EPISODE_FICTION)) if est_en_words else DEFAULT_EPISODE_COUNT
        )

    assumptions: list[str] = []

    # ── Notional Claude (flat-rate Max) ───────────────────────────────────────
    notional: dict[str, float] = {}
    notional["per_chapter_authoring"] = round(episodes * CALIB_PER_EPISODE_NOTIONAL_USD["per_chapter_authoring"], 2)
    notional["phase_0d_design"] = round(episodes * CALIB_PER_EPISODE_NOTIONAL_USD["phase_0d_design"], 2)
    notional["book_compose"] = round(episodes * CALIB_PER_EPISODE_NOTIONAL_USD["book_compose"], 2)
    notional["phase_0b_refine"] = round((source_words / 1000.0) * CALIB_0B_NOTIONAL_USD_PER_1K_WORDS, 2)

    if is_islamic:
        notional["phase_0e_enrich"] = round(episodes * CALIB_0E_NOTIONAL_USD_PER_EPISODE, 2)
    else:
        assumptions.append("0c phonetics + 0e enrichment SKIPPED (non-islamic_scholarly profile).")

    # Translation only for non-English source (Claude on Max).
    if source_language not in ("en", "english", ""):
        en_words = source_chars * CHARS_TO_EN_WORDS
        out_tokens = en_words * WORDS_TO_OUTPUT_TOKENS
        translate_usd = (out_tokens / 1_000_000.0) * _OPUS_OUTPUT_USD_PER_M * TRANSLATION_OVERHEAD_FACTOR
        notional["translation"] = round(translate_usd, 2)
        assumptions.append(
            f"Translation: {source_chars:,} source chars → ~{en_words:,.0f} EN words "
            f"→ ~{out_tokens:,.0f} output tokens at opus notional rate × "
            f"{TRANSLATION_OVERHEAD_FACTOR} overhead. NOTIONAL (Max, $0 marginal). "
            f"LARGEST single uncertainty — first non-English source, no baseline."
        )

    notional_total = round(sum(notional.values()), 2)

    # ── Real metered spend (Gemini + Azure) ───────────────────────────────────
    real: dict[str, float] = {}
    if video_enabled:
        real["gemini_scenic_images"] = round(episodes * IMAGES_PER_EP_SCENIC * IMAGE_COST_ESTIMATE, 2)
        # Gemini Flash prompt text per episode — small; ~chapter chars in, ~3k out.
        flash_in = GEMINI_PRICING_USD["gemini-2.5-flash"]["in_per_char"]
        flash_out = GEMINI_PRICING_USD["gemini-2.5-flash"]["out_per_char"]
        per_ep_text = (source_chars / max(episodes, 1)) * flash_in + 3000 * flash_out
        real["gemini_prompt_text"] = round(episodes * per_ep_text, 2)
    else:
        assumptions.append("Video DISABLED (enable_video: false) — no Gemini image spend.")

    # Azure: only when ingest uses Azure OCR/translation. Fiction here uses Claude
    # translation + an HTML source, so Azure ≈ $0. Flag explicitly.
    if is_fiction or source_language not in ("en", ""):
        assumptions.append("Azure ≈ $0: Claude does translation; non-PDF source → no Doc-Intelligence OCR.")
    real_total = round(sum(real.values()), 2)

    return {
        "schema_version": 1,
        "kind": "cost-estimate",
        "book_slug": book_dir.name,
        "content_profile": profile,
        "video_enabled": video_enabled,
        "source_language": source_language,
        "scope": {
            "episodes": episodes,
            "source_words": source_words,
            "source_chars": source_chars,
            "estimated_english_words": est_en_words,
            "words_per_episode_assumed": WORDS_PER_EPISODE_FICTION,
        },
        "notional_max_usd": notional,
        "notional_max_total_usd": notional_total,
        "real_metered_usd": real,
        "real_metered_total_usd": real_total,
        "headline": {
            "real_money_usd": real_total,
            "notional_max_usd": notional_total,
            "note": "Real money is metered (Gemini/Azure). Notional is flat-rate "
            "Claude Max — covered by the subscription, $0 marginal.",
        },
        "assumptions": assumptions,
        "confidence": "low" if (is_fiction or source_language not in ("en", "")) else "medium",
        "calibration_source": "ayyuhal-walad actuals (4 ep, islamic_scholarly, opus-4-8)",
    }


def reconcile(book_dir: Path) -> dict:
    """Diff a written estimate against the actual ledger. Returns the variance dict."""
    from cost_ledger_summary import load_ledger, summarize  # local import

    est_path = book_dir / "_system" / "cost-estimate.json"
    ledger = book_dir / "_system" / "cost-ledger.jsonl"
    if not est_path.exists():
        raise FileNotFoundError(f"no estimate at {est_path} — run estimate first")
    if not ledger.exists():
        raise FileNotFoundError(f"no actual ledger at {ledger}")

    est = json.loads(est_path.read_text(encoding="utf-8"))
    summary = summarize(load_ledger(ledger))

    est_real = float(est.get("real_metered_total_usd", 0.0))
    est_notional = float(est.get("notional_max_total_usd", 0.0))
    act_real = float(summary.get("real_spend_usd", 0.0))
    act_notional = float(summary.get("max_notional_usd", 0.0))

    def _pct(est_v: float, act_v: float) -> float | None:
        if est_v == 0:
            return None
        return round((act_v - est_v) / est_v * 100.0, 1)

    return {
        "real_metered": {
            "estimate_usd": round(est_real, 4),
            "actual_usd": round(act_real, 4),
            "variance_pct": _pct(est_real, act_real),
        },
        "notional_max": {
            "estimate_usd": round(est_notional, 4),
            "actual_usd": round(act_notional, 4),
            "variance_pct": _pct(est_notional, act_notional),
        },
        "actual_total_calls": summary["totals"]["calls"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="estimate_cost.py",
        description="Pre-run cost forecast + estimate-vs-actual reconciliation.",
    )
    ap.add_argument("book", help="Book slug or path to book dir.")
    ap.add_argument("--episodes", type=int, default=None, help="Override the forecast episode count.")
    ap.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    ap.add_argument("--no-write", action="store_true", help="Do not write cost-estimate.json.")
    ap.add_argument("--reconcile", action="store_true", help="Diff the written estimate against the actual ledger.")
    args = ap.parse_args(argv)

    try:
        book_dir = _resolve_book_dir(args.book)
    except FileNotFoundError as e:
        sys.stderr.write(f"error: {e}\n")
        return 1

    if args.reconcile:
        try:
            variance = reconcile(book_dir)
        except FileNotFoundError as e:
            sys.stderr.write(f"error: {e}\n")
            return 2
        est_path = book_dir / "_system" / "cost-estimate.json"
        est = json.loads(est_path.read_text(encoding="utf-8"))
        est["reconciliation"] = variance
        if not args.no_write:
            est_path.write_text(json.dumps(est, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(variance, indent=2) if args.json else _fmt_reconcile(variance, book_dir.name))
        return 0

    est = estimate(book_dir, episodes=args.episodes)
    if not args.no_write:
        out = book_dir / "_system" / "cost-estimate.json"
        out.write_text(json.dumps(est, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(est, indent=2) if args.json else _fmt_estimate(est))
    return 0


def _fmt_estimate(est: dict) -> str:
    s = est["scope"]
    lines = [
        f"Cost estimate — {est['book_slug']}  (profile={est['content_profile']}, confidence={est['confidence']})",
        f"  Scope: {s['episodes']} episodes, {s['source_words']:,} source words, {s['source_chars']:,} source chars",
        "",
        f"  REAL metered spend:   ${est['real_metered_total_usd']:>9.2f}",
    ]
    for k, v in est["real_metered_usd"].items():
        lines.append(f"      {k:<24} ${v:>8.2f}")
    lines += [
        f"  NOTIONAL (Max, $0 real): ${est['notional_max_total_usd']:>9.2f}  (covered by subscription)",
    ]
    for k, v in est["notional_max_usd"].items():
        lines.append(f"      {k:<24} ${v:>8.2f}")
    if est["assumptions"]:
        lines.append("")
        lines.append("  Assumptions:")
        for a in est["assumptions"]:
            lines.append(f"    - {a}")
    return "\n".join(lines)


def _fmt_reconcile(v: dict, slug: str) -> str:
    def _row(label, d):
        pct = d["variance_pct"]
        pct_s = "n/a" if pct is None else f"{pct:+.1f}%"
        return f"  {label:<16} est ${d['estimate_usd']:>9.2f}  actual ${d['actual_usd']:>9.2f}  variance {pct_s}"

    return "\n".join(
        [
            f"Cost reconciliation — {slug}",
            _row("Real metered", v["real_metered"]),
            _row("Notional Max", v["notional_max"]),
            f"  Actual total calls: {v['actual_total_calls']}",
        ]
    )


if __name__ == "__main__":
    sys.exit(main())
