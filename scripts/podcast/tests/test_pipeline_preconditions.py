"""The two mechanical gates, and the books they must NOT break.

Each was written from a failure that a prose rule had already been written for
and had not prevented. What matters as much as catching those failures is that
neither gate halts a book that was fine yesterday: twenty-seven books are on
disk, six of them with no series-config.yaml at all, and a gate that stopped
them would be a worse regression than the bug it closes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _paths  # noqa: E402
from _pipeline_preconditions import bucket_mismatch, stale_done_markers  # noqa: E402


def _book(tmp_path: Path, bucket: str, slug: str, cfg: dict | None = None) -> Path:
    """A book under a fake content root, so the gate's own resolver is exercised."""
    d = tmp_path / "content" / bucket / slug
    (d / "_system").mkdir(parents=True)
    if cfg is not None:
        (d / "_system" / "series-config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return d


def _at(monkeypatch, tmp_path):
    monkeypatch.setattr(_paths, "CONTENT_ROOT", tmp_path / "content")


# ── A. folder vs declared profile ────────────────────────────────────────────
def test_a_consistent_book_passes(tmp_path, monkeypatch):
    _at(monkeypatch, tmp_path)
    d = _book(tmp_path, "Sessions", "s", {"content_profile": "islamic_session"})
    assert bucket_mismatch(d) is None


def test_the_failure_that_cost_two_chapters_is_caught(tmp_path, monkeypatch):
    """A recorded session in Sessions/ that declares no profile: every phase
    reads it as islamic_scholarly, which is how enrichment reached a sermon."""
    _at(monkeypatch, tmp_path)
    d = _book(tmp_path, "Sessions", "s", {"source_language": "en"})
    msg = bucket_mismatch(d)
    assert msg and "declares no content_profile" in msg
    assert "content/Islamic/" in msg


def test_a_wrongly_declared_profile_is_caught_and_named(tmp_path, monkeypatch):
    _at(monkeypatch, tmp_path)
    d = _book(tmp_path, "Sessions", "s", {"content_profile": "islamic_scholarly"})
    msg = bucket_mismatch(d)
    assert msg and "islamic_scholarly" in msg and "content/Islamic/" in msg


# The regression half: none of these may halt.
def test_a_book_with_no_config_at_all_is_left_alone(tmp_path, monkeypatch):
    """Six books on disk have none. Inventing a profile for them is the guess
    that caused the damage, and halting them would strand every one."""
    _at(monkeypatch, tmp_path)
    assert bucket_mismatch(_book(tmp_path, "Guides", "stub", None)) is None


def test_an_unparseable_config_makes_no_claim(tmp_path, monkeypatch):
    _at(monkeypatch, tmp_path)
    d = _book(tmp_path, "Sessions", "s", {"x": 1})
    (d / "_system" / "series-config.yaml").write_text("{{ not yaml", encoding="utf-8")
    assert bucket_mismatch(d) is None


def test_a_directory_outside_content_makes_no_claim(tmp_path, monkeypatch):
    _at(monkeypatch, tmp_path)
    assert bucket_mismatch(tmp_path / "somewhere" / "else") is None


def test_every_book_currently_on_disk_passes(tmp_path):
    """The gate is about to run on every launch. If it halts a real book today,
    it is a regression, not a gate."""
    halted = []
    for _status, _bucket, d in _paths.iter_content():
        msg = bucket_mismatch(Path(d))
        if msg:
            halted.append((_paths.slug_of(Path(d)), msg))
    assert halted == [], f"gate would halt real books: {halted}"


# ── B. checkpoints vs the plan on disk ───────────────────────────────────────
def _plan(*titles):
    return [{"sc_index": i, "source_title": t} for i, t in enumerate(titles, start=1)]


def _marker(d: Path, idx: int, title: str | None) -> None:
    d.mkdir(parents=True, exist_ok=True)
    body = f"sc_index={idx}\n" + (f"source_title={title}\n" if title else "")
    (d / f"sc-{idx:03d}.done").write_text(body, encoding="utf-8")


def test_markers_matching_the_plan_pass(tmp_path):
    _marker(tmp_path, 1, "Love of the World")
    assert stale_done_markers(tmp_path, _plan("Love of the World", "Envy")) == []


def test_the_resegmentation_hazard_is_caught(tmp_path):
    """`sc-001` meant the merged chapter and now means the book's first. Left in
    place, seventeen of twenty-four would be skipped and the run would report
    success."""
    _marker(tmp_path, 1, "The World and the Envious Heart")
    out = stale_done_markers(tmp_path, _plan("Love of the World", "Envy"))
    assert len(out) == 1
    assert "The World and the Envious Heart" in out[0] and "Love of the World" in out[0]


def test_a_marker_past_the_end_of_the_plan_is_caught(tmp_path):
    _marker(tmp_path, 9, "Something Old")
    out = stale_done_markers(tmp_path, _plan("A", "B"))
    assert out and "only 2 chapters" in out[0]


def test_a_marker_with_no_recorded_title_makes_no_claim(tmp_path):
    """Markers written before titles were recorded must stay resumable."""
    _marker(tmp_path, 1, None)
    assert stale_done_markers(tmp_path, _plan("Anything")) == []


def test_a_missing_chunks_dir_makes_no_claim(tmp_path):
    assert stale_done_markers(tmp_path / "nope", _plan("A")) == []


def test_an_unreadable_marker_is_skipped_not_fatal(tmp_path):
    (tmp_path / "sc-001.done").write_text("garbage with no equals sign", encoding="utf-8")
    assert stale_done_markers(tmp_path, _plan("A")) == []


def test_the_gate_is_wired_into_the_resume_preflight(tmp_path):
    """A check nothing calls is a check that does not exist. It lives in
    `preflight_resume`'s failure list rather than the CLI because
    `orchestrate_book.py` sits exactly ON its 600-line DR-005 limit, and because
    a preflight failure list is what this repo already uses to refuse a launch."""
    import inspect

    from phases import preflight

    src = inspect.getsource(preflight.preflight_resume)
    assert "bucket_mismatch" in src


def test_no_book_on_disk_fails_the_resume_preflight_on_this_check(tmp_path):
    from phases.preflight import preflight_resume

    for _status, _bucket, d in _paths.iter_content():
        slug = _paths.slug_of(Path(d))
        _bd, fails = preflight_resume(slug)
        assert not [f for f in fails if "content_profile" in f], f"{slug}: {fails}"


def test_the_live_run_s_own_markers_would_pass(tmp_path):
    """The shape the in-flight run is in: markers written FROM the current plan.
    A gate that halted it would have cost the whole re-segmentation."""
    for i, t in enumerate(["Love of the World", "Envy", "Blameworthy Modesty"], start=1):
        _marker(tmp_path, i, t)
    plan = _plan("Love of the World", "Envy", "Blameworthy Modesty", "Fantasizing")
    assert stale_done_markers(tmp_path, plan) == []
