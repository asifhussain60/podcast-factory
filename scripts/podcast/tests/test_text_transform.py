from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _text_transform as text_transform  # noqa: E402


def test_adapters_for_engine_keeps_claude_on_default_path() -> None:
    adapter, repair_adapter = text_transform.adapters_for_engine("claude")

    assert adapter is None
    assert repair_adapter is None


def test_adapters_for_engine_routes_codex_and_gemini() -> None:
    codex_adapter, codex_repair = text_transform.adapters_for_engine("codex")
    gemini_adapter, gemini_repair = text_transform.adapters_for_engine("gemini")

    assert codex_adapter.__name__ == "_codex_adapter"
    assert codex_repair.__name__ == "_codex_repair_adapter"
    assert gemini_adapter.__name__ == "_gemini_adapter"
    assert gemini_repair.__name__ == "_gemini_repair_adapter"


def test_auto_engine_keeps_claude_primary_inside_codex(monkeypatch) -> None:
    monkeypatch.setenv("CODEX_THREAD_ID", "thread")
    monkeypatch.delenv("PODCAST_FACTORY_AUTHORING_ENGINE", raising=False)

    assert text_transform.resolve_runtime_engine("auto") == "claude"


def test_auto_engine_uses_codex_when_authoring_engine_forces_codex(monkeypatch) -> None:
    monkeypatch.setenv("PODCAST_FACTORY_AUTHORING_ENGINE", "codex")

    assert text_transform.resolve_runtime_engine("auto") == "codex"


def test_auto_engine_uses_claude_without_codex_markers(monkeypatch) -> None:
    for name in ("CODEX_THREAD_ID", "CODEX_CI", "CODEX_SHELL"):
        monkeypatch.delenv(name, raising=False)

    assert text_transform.resolve_runtime_engine("auto") == "claude"


def test_preflight_codex_checks_the_codex_binary(monkeypatch) -> None:
    seen: list[bool] = []

    def fake_codex_bin() -> str:
        seen.append(True)
        return "/fake/codex"

    monkeypatch.setattr("_codex_text._codex_bin", fake_codex_bin)

    text_transform.preflight_engine("codex")

    assert seen == [True]


def test_preflight_gemini_checks_the_secret(monkeypatch) -> None:
    seen: list[bool] = []

    def fake_key() -> str:
        seen.append(True)
        return "key"

    monkeypatch.setattr("_secrets.get_gemini_key", fake_key)

    text_transform.preflight_engine("gemini")

    assert seen == [True]
