"""Deterministic tests for Claude-primary / Codex-fallback authoring."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _codex_text  # noqa: E402
from _authoring import _core  # noqa: E402

CANNED_STDOUT = "Tokens: 10 in, 5 out, cache: 0 read, 0 create\n"


def _clear_engine_env(monkeypatch) -> None:
    monkeypatch.delenv(_core.AUTHORING_ENGINE_ENV, raising=False)
    monkeypatch.delenv(_core.CODEX_FALLBACK_ENV, raising=False)


def test_auto_mode_uses_claude_first_and_never_calls_codex_on_success(tmp_path: Path, monkeypatch) -> None:
    _clear_engine_env(monkeypatch)
    called: list[str] = []

    def fake_codex(*_args, **_kwargs):
        called.append("codex")
        return 0, "codex", ""

    monkeypatch.setattr(_codex_text, "call_codex_agent", fake_codex)
    with mock.patch("subprocess.run") as run_mock:
        run_mock.return_value = mock.MagicMock(returncode=0, stdout=CANNED_STDOUT, stderr="")
        rc, out, err = _core._run_claude_p(
            "test prompt",
            book_dir=tmp_path / "book",
            phase="0d",
            step="toc",
        )

    assert rc == 0
    assert called == []
    assert run_mock.call_args[0][0][0] == _core.CLAUDE_CMD


def test_auto_mode_falls_back_to_codex_for_claude_usage_limit(tmp_path: Path, monkeypatch) -> None:
    _clear_engine_env(monkeypatch)
    seen: dict = {}

    def fake_codex(prompt, **kwargs):
        seen["prompt"] = prompt
        seen["kwargs"] = kwargs
        return 0, "codex-authored output", ""

    monkeypatch.setattr(_codex_text, "call_codex_agent", fake_codex)
    claude_error = json.dumps(
        {
            "is_error": True,
            "api_error_status": 429,
            "result": "Claude usage limit reached. Please try later.",
        }
    )
    with mock.patch("subprocess.run") as run_mock:
        run_mock.return_value = mock.MagicMock(returncode=1, stdout=claude_error, stderr="")
        rc, out, err = _core._run_claude_p(
            "write the artifact",
            cwd=tmp_path,
            book_dir=tmp_path / "book",
            phase="0d",
            step="toc",
            system_prompt="Follow instructions.",
        )

    assert rc == 0
    assert out == "codex-authored output"
    assert seen["prompt"] == "write the artifact"
    assert seen["kwargs"]["cwd"] == tmp_path
    assert seen["kwargs"]["system_prompt"] == "Follow instructions."


def test_auto_mode_does_not_fallback_for_generic_content_failure(tmp_path: Path, monkeypatch) -> None:
    _clear_engine_env(monkeypatch)
    called: list[str] = []

    def fake_codex(*_args, **_kwargs):
        called.append("codex")
        return 0, "codex", ""

    monkeypatch.setattr(_codex_text, "call_codex_agent", fake_codex)
    with mock.patch("subprocess.run") as run_mock:
        run_mock.return_value = mock.MagicMock(returncode=1, stdout="bad output", stderr="validation failed")
        rc, out, err = _core._run_claude_p("test prompt", book_dir=tmp_path / "book", phase="0d", step="toc")

    assert rc == 1
    assert called == []
    assert err == "validation failed"


def test_claude_only_mode_disables_codex_fallback_on_usage_limit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(_core.AUTHORING_ENGINE_ENV, "claude")
    monkeypatch.setenv(_core.CODEX_FALLBACK_ENV, "1")
    called: list[str] = []

    def fake_codex(*_args, **_kwargs):
        called.append("codex")
        return 0, "codex", ""

    monkeypatch.setattr(_codex_text, "call_codex_agent", fake_codex)
    with mock.patch("subprocess.run") as run_mock:
        run_mock.return_value = mock.MagicMock(returncode=1, stdout="", stderr="usage limit reached")
        rc, out, err = _core._run_claude_p("test prompt", book_dir=tmp_path / "book", phase="0d", step="toc")

    assert rc == 1
    assert called == []


def test_codex_mode_skips_claude_and_runs_codex_directly(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(_core.AUTHORING_ENGINE_ENV, "codex")
    seen: dict = {}

    def fake_codex(prompt, **kwargs):
        seen["prompt"] = prompt
        seen["kwargs"] = kwargs
        return 0, "codex direct", ""

    monkeypatch.setattr(_codex_text, "call_codex_agent", fake_codex)
    with mock.patch("subprocess.run") as run_mock:
        rc, out, err = _core._run_claude_p("test prompt", cwd=tmp_path, phase="0d", step="toc")

    assert rc == 0
    assert out == "codex direct"
    assert seen["kwargs"]["cwd"] == tmp_path
    run_mock.assert_not_called()


def test_missing_claude_binary_uses_codex_fallback_in_auto_mode(tmp_path: Path, monkeypatch) -> None:
    _clear_engine_env(monkeypatch)
    called: list[str] = []

    def fake_codex(*_args, **_kwargs):
        called.append("codex")
        return 0, "codex fallback", ""

    monkeypatch.setattr(_codex_text, "call_codex_agent", fake_codex)
    with mock.patch("subprocess.run", side_effect=FileNotFoundError("no claude")):
        rc, out, err = _core._run_claude_p("test prompt", book_dir=tmp_path / "book", phase="0d", step="toc")

    assert rc == 0
    assert out == "codex fallback"
    assert called == ["codex"]


def test_codex_agent_records_subscription_usage(tmp_path: Path, monkeypatch) -> None:
    book_dir = tmp_path / "book"
    book_dir.mkdir()

    def fake_run(cmd, *, input, capture_output, text, timeout):
        out_path = Path(cmd[cmd.index("--output-last-message") + 1])
        out_path.write_text("done\n", encoding="utf-8")
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

    monkeypatch.setattr(_codex_text, "_codex_bin", lambda: "/fake/codex")
    monkeypatch.setattr(subprocess, "run", fake_run)

    rc, out, err = _codex_text.call_codex_agent(
        "Write something.",
        cwd=tmp_path,
        book_dir=book_dir,
        phase="0d",
        step="toc",
        model="gpt-test",
        timeout=10,
    )

    assert (rc, out, err) == (0, "done", "")
    row = json.loads((book_dir / "_system" / "cost-ledger.jsonl").read_text(encoding="utf-8"))
    assert row["model"] == "codex/gpt-test"
    assert row["engine"] == "max"
    assert row["cost_usd"] == 0.0
    assert row["input_tokens"] == 60
    assert row["cache_read"] == 30
