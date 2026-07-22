"""cost_guard.py — per-book REAL-MONEY cost ceiling (Phase E, C4).

Enforces the $20 soft / $50 hard caps that were declared (dor_halts.py P6.3,
_convergence.py header) but never wired up. "Real money" = metered services only
(Azure OCR/translate, Gemini images) — the `engine="api"` rows in the cost
ledger. Claude Max (`claude -p`, `engine="max"`, cost_usd=0.0) is flat-rate and
deliberately EXCLUDED, so a 5-chapter authoring run (all Max) never trips this.

Reuses the canonical aggregation in cost_ledger_summary (load_ledger + summarize
-> real_spend_usd). Thresholds come from state["config"] (cost_cap_soft /
cost_cap_hard), defaulting to 20 / 50; a non-positive hard cap disables the gate.
"""

from __future__ import annotations

from pathlib import Path

from _progress import read_state
from cost_ledger_summary import load_ledger, summarize

DEFAULT_SOFT_USD = 20.0
DEFAULT_HARD_USD = 50.0


def _thresholds(book_dir: Path) -> tuple[float, float]:
    state = read_state(book_dir) or {}
    cfg = state.get("config") or {}
    try:
        soft = float(cfg.get("cost_cap_soft", DEFAULT_SOFT_USD))
    except (TypeError, ValueError):
        soft = DEFAULT_SOFT_USD
    try:
        hard = float(cfg.get("cost_cap_hard", DEFAULT_HARD_USD))
    except (TypeError, ValueError):
        hard = DEFAULT_HARD_USD
    return soft, hard


def real_spend_usd(book_dir: Path) -> float:
    """Total REAL (metered, engine='api') spend recorded for this book, in USD."""
    ledger = book_dir / "_system" / "cost-ledger.jsonl"
    if not ledger.is_file():
        return 0.0
    return float(summarize(load_ledger(ledger)).get("real_spend_usd", 0.0))


def cost_ceiling_check(book_dir: Path) -> dict:
    """Return {action, real_spend_usd, soft, hard}.

    action: "ok"   — under the soft cap (or gate disabled)
            "warn" — at/over soft, under hard (continue, but surface a warning)
            "halt" — at/over hard (caller must stop before more real-money spend)
    """
    soft, hard = _thresholds(book_dir)
    spend = real_spend_usd(book_dir)
    if hard <= 0:  # gate disabled
        return {"action": "ok", "real_spend_usd": spend, "soft": soft, "hard": hard}
    if spend >= hard:
        action = "halt"
    elif spend >= soft:
        action = "warn"
    else:
        action = "ok"
    return {"action": action, "real_spend_usd": spend, "soft": soft, "hard": hard}
