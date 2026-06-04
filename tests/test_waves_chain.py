"""Tests for run_waves_chain.py — cross-wave autonomous execution chain driver.

H3 acceptance criteria:
  - authorize exits 0 and writes wave-chain-auth.json
  - status shows authorization and empty log
  - run invokes run_wave.py per wave in sequence
  - run exits 2 (EXIT_HALTED) when a wave halts
  - run exits 3 (EXIT_SPEND_CAP) when global spend cap is exceeded
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest

# ── Load module under test without requiring repo sys.path gymnastics ──────────
_CHAIN_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts" / "podcast" / "run_waves_chain.py"
)


def _load_chain_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "run_waves_chain", _CHAIN_PATH,
        submodule_search_locations=[],
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)

    # Stub _paths.REPO_ROOT so the module loads without the real repo root.
    _paths_stub = type(sys)("_paths")
    _paths_stub.REPO_ROOT = Path(__file__).resolve().parents[1]
    sys.modules["_paths"] = _paths_stub

    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_chain = _load_chain_module()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_auth_file(tmp_path, monkeypatch):
    """Redirect AUTH_FILE and CHAIN_LOG_FILE to tmp_path."""
    auth_file = tmp_path / "wave-chain-auth.json"
    log_file = tmp_path / "wave-chain-log.jsonl"
    monkeypatch.setattr(_chain, "AUTH_FILE", auth_file)
    monkeypatch.setattr(_chain, "CHAIN_LOG_FILE", log_file)
    return auth_file, log_file


# ── authorize ─────────────────────────────────────────────────────────────────

def test_authorize_writes_file(tmp_auth_file):
    auth_file, _ = tmp_auth_file
    args = _make_namespace(cmd="authorize", waves=[1, 2], spend_cap_total=30.0,
                            spend_cap_per_wave=10.0, note="test run")
    rc = _chain.cmd_authorize(args)
    assert rc == _chain.EXIT_DONE
    assert auth_file.exists()
    data = json.loads(auth_file.read_text())
    assert data["waves"] == [1, 2]
    assert data["spend_cap_total_usd"] == 30.0
    assert data["spend_cap_per_wave_usd"] == 10.0
    assert data["note"] == "test run"


def test_authorize_deduplicates_and_sorts_waves(tmp_auth_file):
    auth_file, _ = tmp_auth_file
    args = _make_namespace(cmd="authorize", waves=[3, 1, 3, 2], spend_cap_total=50.0,
                            spend_cap_per_wave=15.0, note="")
    _chain.cmd_authorize(args)
    data = json.loads(auth_file.read_text())
    assert data["waves"] == [1, 2, 3]


# ── revoke ────────────────────────────────────────────────────────────────────

def test_revoke_deletes_file(tmp_auth_file):
    auth_file, _ = tmp_auth_file
    auth_file.write_text(json.dumps({"waves": [1]}))
    rc = _chain.cmd_revoke(_make_namespace(cmd="revoke"))
    assert rc == _chain.EXIT_DONE
    assert not auth_file.exists()


def test_revoke_no_file_is_ok(tmp_auth_file):
    _, _ = tmp_auth_file  # ensures redirects are in place
    rc = _chain.cmd_revoke(_make_namespace(cmd="revoke"))
    assert rc == _chain.EXIT_DONE


# ── status ────────────────────────────────────────────────────────────────────

def test_status_no_auth(tmp_auth_file, capsys):
    _chain.cmd_status(_make_namespace(cmd="status"))
    out = capsys.readouterr().out
    assert "No valid authorization" in out


def test_status_with_auth(tmp_auth_file, capsys):
    auth_file, _ = tmp_auth_file
    data = {"waves": [1, 2], "spend_cap_total_usd": 50.0,
            "spend_cap_per_wave_usd": 15.0, "note": "ok",
            "authorized_at": "2026-01-01T00:00:00Z",
            "authorized_by": "operator"}
    auth_file.write_text(json.dumps(data))
    _chain.cmd_status(_make_namespace(cmd="status"))
    out = capsys.readouterr().out
    assert "[1, 2]" in out
    assert "$50.00" in out


# ── run — no auth ─────────────────────────────────────────────────────────────

def test_run_no_auth_returns_error(tmp_auth_file):
    rc = _chain.cmd_run(_make_namespace(cmd="run"))
    assert rc == _chain.EXIT_ERROR


# ── run — wave already DONE (exit 0 from run_wave) ───────────────────────────

def test_run_already_done_continues(tmp_auth_file, monkeypatch):
    auth_file, _ = tmp_auth_file
    _write_auth(auth_file, waves=[1, 2], cap_total=50.0, cap_per_wave=15.0)

    calls: list[int] = []

    def _fake_run(cmd, **_kwargs):
        calls.append(cmd[-1])  # wave number as string
        return _FakeProc(returncode=_chain._RW_ALREADY_DONE)

    monkeypatch.setattr(_chain.subprocess, "run", _fake_run)
    monkeypatch.setattr(_chain, "_total_spend_usd", lambda: 0.0)

    rc = _chain.cmd_run(_make_namespace(cmd="run"))
    assert rc == _chain.EXIT_DONE
    assert calls == ["1", "2"]


# ── run — wave completed (exit 2 from run_wave) ───────────────────────────────

def test_run_executed_done_continues(tmp_auth_file, monkeypatch):
    auth_file, _ = tmp_auth_file
    _write_auth(auth_file, waves=[1, 2], cap_total=50.0, cap_per_wave=15.0)

    monkeypatch.setattr(
        _chain.subprocess, "run",
        lambda *a, **kw: _FakeProc(returncode=_chain._RW_EXECUTED_DONE),
    )
    monkeypatch.setattr(_chain, "_total_spend_usd", lambda: 0.0)
    rc = _chain.cmd_run(_make_namespace(cmd="run"))
    assert rc == _chain.EXIT_DONE


# ── run — wave halts (exit 3 from run_wave) ───────────────────────────────────

def test_run_halted_returns_halted(tmp_auth_file, monkeypatch):
    auth_file, _ = tmp_auth_file
    _write_auth(auth_file, waves=[1, 2], cap_total=50.0, cap_per_wave=15.0)

    returncode_iter = iter([_chain._RW_HALTED])

    def _fake_run(*a, **kw):
        try:
            rc = next(returncode_iter)
        except StopIteration:
            rc = _chain._RW_EXECUTED_DONE
        return _FakeProc(returncode=rc)

    monkeypatch.setattr(_chain.subprocess, "run", _fake_run)
    monkeypatch.setattr(_chain, "_total_spend_usd", lambda: 0.0)
    rc = _chain.cmd_run(_make_namespace(cmd="run"))
    assert rc == _chain.EXIT_HALTED


# ── run — spend cap enforcement ───────────────────────────────────────────────

def test_run_global_spend_cap(tmp_auth_file, monkeypatch):
    """Chain halts when cumulative spend equals the global cap."""
    auth_file, _ = tmp_auth_file
    _write_auth(auth_file, waves=[1, 2, 3], cap_total=5.0, cap_per_wave=100.0)

    # First call: spend_before = 0; after W1: spend = 6.0 → cap hit before W2
    spend_values = iter([0.0, 0.0, 6.0, 6.0, 6.0])

    monkeypatch.setattr(_chain, "_total_spend_usd", lambda: next(spend_values))
    monkeypatch.setattr(
        _chain.subprocess, "run",
        lambda *a, **kw: _FakeProc(returncode=_chain._RW_EXECUTED_DONE),
    )

    rc = _chain.cmd_run(_make_namespace(cmd="run"))
    assert rc == _chain.EXIT_SPEND_CAP


# ── run — P-9 violation ───────────────────────────────────────────────────────

def test_run_p9_violated_returns_error(tmp_auth_file, monkeypatch):
    auth_file, _ = tmp_auth_file
    _write_auth(auth_file, waves=[1], cap_total=50.0, cap_per_wave=15.0)

    monkeypatch.setattr(
        _chain.subprocess, "run",
        lambda *a, **kw: _FakeProc(returncode=_chain._RW_P9_VIOLATED),
    )
    monkeypatch.setattr(_chain, "_total_spend_usd", lambda: 0.0)
    rc = _chain.cmd_run(_make_namespace(cmd="run"))
    assert rc == _chain.EXIT_ERROR


# ── run — unknown exit code from run_wave ────────────────────────────────────

def test_run_unknown_exit_code_returns_error(tmp_auth_file, monkeypatch):
    auth_file, _ = tmp_auth_file
    _write_auth(auth_file, waves=[1], cap_total=50.0, cap_per_wave=15.0)

    monkeypatch.setattr(
        _chain.subprocess, "run",
        lambda *a, **kw: _FakeProc(returncode=99),
    )
    monkeypatch.setattr(_chain, "_total_spend_usd", lambda: 0.0)
    rc = _chain.cmd_run(_make_namespace(cmd="run"))
    assert rc == _chain.EXIT_ERROR


# ── chain log ─────────────────────────────────────────────────────────────────

def test_chain_log_written_on_run(tmp_auth_file, monkeypatch):
    auth_file, log_file = tmp_auth_file
    _write_auth(auth_file, waves=[1], cap_total=50.0, cap_per_wave=15.0)
    monkeypatch.setattr(
        _chain.subprocess, "run",
        lambda *a, **kw: _FakeProc(returncode=_chain._RW_EXECUTED_DONE),
    )
    monkeypatch.setattr(_chain, "_total_spend_usd", lambda: 0.0)
    _chain.cmd_run(_make_namespace(cmd="run"))
    assert log_file.exists()
    events = [json.loads(l) for l in log_file.read_text().splitlines() if l.strip()]
    event_types = [e["event"] for e in events]
    assert "chain_start" in event_types
    assert "chain_done" in event_types


# ── line count (DR-005 ≤ 600 lines) ──────────────────────────────────────────

def test_dr005_line_limit():
    lines = _CHAIN_PATH.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 600, (
        f"run_waves_chain.py is {len(lines)} lines — exceeds DR-005 limit of 600."
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

class _FakeProc:
    def __init__(self, returncode: int):
        self.returncode = returncode


def _make_namespace(**kwargs):
    import argparse
    ns = argparse.Namespace()
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


def _write_auth(path: Path, *, waves: list[int], cap_total: float,
                cap_per_wave: float) -> None:
    data = {
        "authorized_at": "2026-01-01T00:00:00Z",
        "authorized_by": "operator",
        "waves": waves,
        "spend_cap_total_usd": cap_total,
        "spend_cap_per_wave_usd": cap_per_wave,
        "note": "test",
    }
    path.write_text(json.dumps(data))
