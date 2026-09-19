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


# ─── layering: a localhost-only publish never touches or depends on production ────────────────────
def _stub_one_file(monkeypatch, tmp_path, *, disk_hash, local_hash):
    f = tmp_path / "ch1.m4a"
    f.write_bytes(b"x")
    rel = str(f.relative_to(tmp_path))
    monkeypatch.setattr(audio_parity, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(audio_parity, "book_dirs", lambda _s: [tmp_path / "demo"])
    monkeypatch.setattr(audio_parity, "shippable_audio", lambda _d: [f])
    monkeypatch.setattr(audio_parity, "sha256", lambda _p: disk_hash)
    monkeypatch.setattr(
        audio_parity,
        "local_rows",
        lambda: {rel: {"sha256": local_hash, "slug": "demo", "key": "k", "source_path": rel}},
    )

    def production_is_off_limits():
        raise AssertionError("a localhost-only publish read PRODUCTION")

    monkeypatch.setattr(audio_parity, "remote_rows", production_is_off_limits)


def test_a_local_only_publish_never_reads_production(monkeypatch, tmp_path, capsys):
    _stub_one_file(monkeypatch, tmp_path, disk_hash="a", local_hash="a")
    rc = audio_parity.check_after_publish(["demo"], [], dry_run=False, json_mode=False, remote=False)
    out = capsys.readouterr().out
    assert rc == 0 and "skipped" not in out
    assert "disk and local agree" in out and "production" not in out


def test_a_local_only_publish_still_catches_disk_versus_local_drift(monkeypatch, tmp_path, capsys):
    _stub_one_file(monkeypatch, tmp_path, disk_hash="a", local_hash="b")
    rc = audio_parity.check_after_publish(["demo"], [], dry_run=False, json_mode=False, remote=False)
    out = capsys.readouterr().out
    assert rc == 1 and "STALE" in out


def test_publish_to_listener_tells_the_check_which_database_it_wrote_to():
    src = (Path(__file__).resolve().parents[1] / "publish_to_listener.py").read_text(encoding="utf-8")
    import re

    assert re.search(r"check_after_publish\([^)]*remote=args\.remote", src)
