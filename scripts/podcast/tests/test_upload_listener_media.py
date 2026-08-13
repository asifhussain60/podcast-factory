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
