#!/usr/bin/env python3
"""Phase 6 Screen-1 regression — intake_staging lifecycle.

Staging is resolver-based (rename-safe), enforces the allow-list + role rules
(Q7: exactly one primary; audio-as-primary warned), and commits atomically into
the canonical _source/ only on confirm. Abandoned sessions are swept.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _paths  # noqa: E402
import intake_staging as st  # noqa: E402


@pytest.fixture
def temp_root(tmp_path, monkeypatch):
    root = tmp_path / "content"
    (root / "_system").mkdir(parents=True)
    monkeypatch.setattr(_paths, "CONTENT_ROOT", root)
    monkeypatch.setattr(_paths, "SYSTEM_ROOT", root / "_system")
    return root


def _stage_bytes(token: str, filename: str, data: bytes, role: str | None = None) -> dict:
    rec = st.register_file(token, filename, role=role)
    st.stored_path(token, rec["id"]).write_bytes(data)
    return rec


class TestRenameSafety:
    def test_staging_root_follows_resolver(self, temp_root):
        # rename-safe: uses SYSTEM_ROOT, not a hardcoded content/library literal
        assert st.staging_root() == temp_root / "_system" / "staging"

    def test_token_traversal_guarded(self, temp_root):
        for bad in ("../evil", "a/b", ".hidden", ""):
            with pytest.raises(ValueError):
                st.staging_dir(bad)


class TestLifecycle:
    def test_new_session_creates_manifest(self, temp_root):
        token = st.new_session()
        assert st.staging_dir(token).is_dir()
        assert st.list_files(token) == []

    def test_register_allowed_and_default_role(self, temp_root):
        token = st.new_session()
        pdf = _stage_bytes(token, "book.pdf", b"%PDF-1.4")
        txt = _stage_bytes(token, "notes.txt", b"hello")
        assert pdf["role"] == "primary_source"      # PDF auto-primary
        assert txt["role"] == "supplementary_text"  # default
        assert {f["filename"] for f in st.list_files(token)} == {"book.pdf", "notes.txt"}

    def test_disallowed_extension_rejected(self, temp_root):
        token = st.new_session()
        with pytest.raises(ValueError):
            st.register_file(token, "malware.exe")

    def test_set_role_and_remove(self, temp_root):
        token = st.new_session()
        rec = _stage_bytes(token, "audio.mp3", b"ID3")
        st.set_role(token, rec["id"], "source_recording")
        assert st.list_files(token)[0]["role"] == "source_recording"
        st.remove_file(token, rec["id"])
        assert st.list_files(token) == []
        # stored file gone
        assert list(st.staging_dir(token).glob("*.mp3")) == []


class TestRoleValidation:
    def test_exactly_one_primary_required(self, temp_root):
        token = st.new_session()
        _stage_bytes(token, "a.txt", b"x", role="supplementary_text")
        v = st.validate_roles(token)
        assert not v["ok"] and any("no primary_source" in e for e in v["errors"])

    def test_two_primaries_rejected(self, temp_root):
        token = st.new_session()
        _stage_bytes(token, "a.pdf", b"x")           # primary
        _stage_bytes(token, "b.pdf", b"y")           # primary
        v = st.validate_roles(token)
        assert not v["ok"] and any("exactly one" in e for e in v["errors"])

    def test_audio_as_primary_warns(self, temp_root):
        token = st.new_session()
        _stage_bytes(token, "talk.mp3", b"ID3", role="primary_source")
        v = st.validate_roles(token)
        assert v["ok"]  # valid (one primary) but...
        assert any("transcription" in w for w in v["warnings"])


class TestCommit:
    def test_commit_moves_files_and_returns_sources(self, temp_root):
        token = st.new_session()
        _stage_bytes(token, "book.pdf", b"%PDF")          # primary
        _stage_bytes(token, "gloss.md", b"# terms", role="pronunciation_reference")
        target = temp_root / "Islamic" / "asaas" / "vol-01" / "_source"
        sources = st.commit(token, target)
        assert (target / "book.pdf").is_file()
        assert (target / "gloss.md").is_file()
        roles = {s["path"]: s["role"] for s in sources}
        assert roles == {"book.pdf": "primary_source", "gloss.md": "pronunciation_reference"}
        # staging cleaned
        assert not st.staging_dir(token).exists()

    def test_commit_refuses_invalid_roles(self, temp_root):
        token = st.new_session()
        _stage_bytes(token, "a.txt", b"x", role="supplementary_text")  # no primary
        with pytest.raises(ValueError):
            st.commit(token, temp_root / "Islamic" / "x" / "_source")


class TestSweep:
    def test_sweeps_stale_sessions_only(self, temp_root):
        fresh = st.new_session()
        stale = st.new_session()
        now = time.time()
        # backdate the stale session's manifest
        m = st._read_manifest(stale)
        m["created"] = now - 48 * 3600
        st._write_manifest(stale, m)
        swept = st.sweep_stale(ttl_hours=24.0, now=now)
        assert stale in swept and fresh not in swept
        assert st.staging_dir(fresh).is_dir()
        assert not st.staging_dir(stale).exists()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
