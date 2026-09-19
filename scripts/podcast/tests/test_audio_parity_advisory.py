"""audio_parity after a publish is advisory: an unreadable production must not fail it."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import audio_parity  # noqa: E402


def test_unreadable_production_does_not_fail_a_publish(monkeypatch, capsys):
    monkeypatch.setattr(audio_parity, "book_dirs", lambda _slug: [Path("/x/demo")])

    def _boom(*_a, **_k):
        raise SystemExit("audio_parity: could not read remote D1\nAuthentication error")

    monkeypatch.setattr(audio_parity, "report", _boom)
    rc = audio_parity.check_after_publish(["demo"], [], dry_run=False, json_mode=False)
    assert rc == 0
    assert "skipped" in capsys.readouterr().out
