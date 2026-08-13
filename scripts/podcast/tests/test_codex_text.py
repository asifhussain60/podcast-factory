#!/usr/bin/env python3
"""Tests for the ChatGPT-subscription Codex text helper.

These are offline: `codex exec` is mocked, because the contract worth pinning is
the subprocess shape, output capture, and subscription-usage ledger row.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _codex_text as codex_text  # noqa: E402


def test_usage_from_jsonl_splits_cached_input() -> None:
    stdout = "\n".join(
        [
            "noise",
            json.dumps({"type": "turn.started"}),
            json.dumps(
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 100,
                        "cached_input_tokens": 40,
                        "cache_write_input_tokens": 7,
                        "output_tokens": 9,
                    },
                }
            ),
        ]
    )

    assert codex_text._usage_from_jsonl(stdout) == {
        "input_tokens": 60,
        "output_tokens": 9,
        "cache_read": 40,
        "cache_create": 7,
    }


def test_call_codex_text_records_subscription_usage(tmp_path: Path, monkeypatch) -> None:
    book_dir = tmp_path / "book"
    book_dir.mkdir()

    def fake_run(cmd, *, input, capture_output, text, timeout):
        out_path = Path(cmd[cmd.index("--output-last-message") + 1])
        out_path.write_text("rewritten prose\n", encoding="utf-8")
        stdout = json.dumps(
            {
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 90,
                    "cached_input_tokens": 30,
                    "cache_write_input_tokens": 0,
                    "output_tokens": 12,
                },
            }
        )
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(codex_text, "_codex_bin", lambda: "/fake/codex")
    monkeypatch.setattr(subprocess, "run", fake_run)

    out = codex_text.call_codex_text(
        "Rewrite this.",
        book_dir=book_dir,
        phase="rearticulate",
        step="part-01",
        model="gpt-test",
        system_prompt="Return text only.",
        timeout=10,
    )

    assert out == "rewritten prose"
    rows = [(book_dir / "_system" / "cost-ledger.jsonl").read_text(encoding="utf-8")]
    row = json.loads(rows[0])
    assert row["model"] == "codex/gpt-test"
    assert row["engine"] == "max"
    assert row["cost_usd"] == 0.0
    assert row["input_tokens"] == 60
    assert row["cache_read"] == 30
