#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import upload_listener_media as ulm  # noqa: E402


def test_reader_narration_filter_uploads_only_narration_audio() -> None:
    with mock.patch.object(ulm, "d1", return_value=[]) as d1:
        ulm.pending(["sample-book"], remote=False, force=False, narration_only=True)

    sql = d1.call_args.args[0]
    assert "uploaded_at IS NULL" in sql
    assert "slug IN ('sample-book')" in sql
    assert "kind = 'audio'" in sql
    assert "key LIKE '%/narration/%'" in sql


def test_no_audio_still_uploads_reader_narration() -> None:
    with mock.patch.object(ulm, "d1", return_value=[]) as d1:
        ulm.pending(["sample-book"], remote=False, force=False, no_audio=True)

    sql = d1.call_args.args[0]
    assert "kind != 'audio'" in sql
    assert "key LIKE '%/narration/%'" in sql


def test_drop_local_audio_does_not_drop_reader_narration() -> None:
    with mock.patch.object(ulm, "d1", return_value=[]) as d1:
        ulm.local_audio_objects(["sample-book"])

    sql = d1.call_args.args[0]
    assert "kind = 'audio'" in sql
    assert "uploaded_at IS NOT NULL" in sql
    assert "key NOT LIKE '%/narration/%'" in sql


def test_verify_clears_stamp_when_uploaded_object_is_missing() -> None:
    rows = [
        {
            "key": "sample-book/narration/chapter-one.mp3",
            "slug": "sample-book",
            "kind": "audio",
            "bytes": 123,
        }
    ]
    with (
        mock.patch.object(ulm, "uploaded", return_value=rows),
        mock.patch.object(ulm, "object_exists", return_value=False),
        mock.patch.object(ulm, "unstamp") as unstamp,
    ):
        rc = ulm.verify_uploaded(["sample-book"], remote=True, narration_only=True)

    assert rc == 1
    unstamp.assert_called_once_with("sample-book/narration/chapter-one.mp3", remote=True)


def test_upload_stamps_only_after_r2_fetchback() -> None:
    row = {
        "key": "sample-book/narration/chapter-one.mp3",
        "slug": "sample-book",
        "kind": "audio",
        "content_type": "audio/mpeg",
        "bytes": 123,
        "source_path": "content/Islamic/sample-book/book/narration/chapter-one.mp3",
    }
    with (
        mock.patch.object(ulm, "pending", return_value=[row]),
        mock.patch.object(ulm, "bucket_exists", return_value=True),
        mock.patch.object(ulm, "upload"),
        mock.patch.object(ulm, "object_exists", return_value=False),
        mock.patch.object(ulm, "stamp") as stamp,
        mock.patch.object(ulm, "cloudflare_env", return_value={}),
        mock.patch.object(ulm, "account_ok", return_value=(True, "ok")),
        mock.patch.object(ulm.subprocess, "run") as run,
    ):
        run.return_value.stdout = "2026-08-13T21:40:00Z\n"
        rc = ulm.main(["sample-book", "--remote", "--reader-narration-only"])

    assert rc == 1
    stamp.assert_not_called()
