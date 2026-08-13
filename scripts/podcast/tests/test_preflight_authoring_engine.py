"""Tests for setup-stage authoring engine selection."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import preflight_doctor as doctor  # noqa: E402
from _authoring import _core  # noqa: E402


def _result(name: str, status: str, detail: str) -> doctor.CheckResult:
    return doctor.CheckResult(name, status, detail)


def test_auto_preflight_accepts_codex_when_claude_is_unavailable(monkeypatch) -> None:
    monkeypatch.delenv(_core.AUTHORING_ENGINE_ENV, raising=False)
    monkeypatch.delenv(_core.CODEX_FALLBACK_ENV, raising=False)
    monkeypatch.setattr(
        doctor, "check_claude_auth", lambda do_ping=True: _result("claude-auth", doctor.FAIL, "limit reached")
    )
    monkeypatch.setattr(
        doctor, "check_codex_auth", lambda do_ping=True: _result("codex-auth", doctor.OK, "codex ready")
    )

    result = doctor.check_authoring_ai(do_ping=False)

    assert result.name == "authoring-ai"
    assert result.status == doctor.WARN
    assert "Codex fallback ready" in result.detail


def test_auto_preflight_fails_when_fallback_is_disabled(monkeypatch) -> None:
    monkeypatch.delenv(_core.AUTHORING_ENGINE_ENV, raising=False)
    monkeypatch.setenv(_core.CODEX_FALLBACK_ENV, "0")
    monkeypatch.setattr(
        doctor, "check_claude_auth", lambda do_ping=True: _result("claude-auth", doctor.FAIL, "limit reached")
    )

    result = doctor.check_authoring_ai(do_ping=False)

    assert result.status == doctor.FAIL
    assert result.detail == "limit reached"


def test_claude_preflight_is_strict_in_claude_mode(monkeypatch) -> None:
    monkeypatch.setenv(_core.AUTHORING_ENGINE_ENV, "claude")
    monkeypatch.setattr(
        doctor, "check_claude_auth", lambda do_ping=True: _result("claude-auth", doctor.FAIL, "login needed")
    )

    result = doctor.check_authoring_ai(do_ping=False)

    assert result.name == "authoring-ai"
    assert result.status == doctor.FAIL
    assert result.detail == "login needed"


def test_codex_preflight_uses_codex_in_codex_mode(monkeypatch) -> None:
    monkeypatch.setenv(_core.AUTHORING_ENGINE_ENV, "codex")
    monkeypatch.setattr(
        doctor, "check_codex_auth", lambda do_ping=True: _result("codex-auth", doctor.OK, "codex ready")
    )

    result = doctor.check_authoring_ai(do_ping=False)

    assert result.name == "authoring-ai"
    assert result.status == doctor.OK
    assert result.detail == "codex ready"
