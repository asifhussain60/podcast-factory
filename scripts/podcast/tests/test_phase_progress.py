"""A long pass must say which chapter it is on, and how long is left.

isaf-al-talib, 2026-09-18: the polish and reconcile passes ran ~7.5 hours over 33 chapters with NO
per-chapter progress anywhere — the only way to find the chapter number was reading the cost ledger's step
names. The status card's ETA swung 7:00 PM -> 2:40 AM -> 3:50 AM because it extrapolated from phase
percentages. This records each finished chapter and estimates the rest from MEASURED per-chapter time.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _phase_progress as pp  # noqa: E402


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t

    def tick(self, s):
        self.t += s


def _book(tmp_path):
    (tmp_path / "_system").mkdir()
    return tmp_path


def test_nothing_recorded_means_no_line_rather_than_a_guess(tmp_path):
    assert pp.progress_line(_book(tmp_path)) is None


def test_the_line_names_the_pass_the_chapter_and_the_total(tmp_path):
    clock, b = Clock(), _book(tmp_path)
    pp.begin_pass(b, "polish", 33, now=clock)
    clock.tick(600)
    pp.item_done(b, "polish", 1, "The Pillar of Religion", now=clock)
    line = pp.progress_line(b, now=clock)
    assert "polish" in line and "1 of 33" in line and "The Pillar of Religion" in line


def test_the_eta_comes_from_measured_time_and_needs_two_measurements(tmp_path):
    clock, b = Clock(), _book(tmp_path)
    pp.begin_pass(b, "polish", 10, now=clock)
    clock.tick(600)
    pp.item_done(b, "polish", 1, "a", now=clock)
    assert pp.eta_seconds(pp.load(b)) is None, "one measurement is a guess, not an estimate"
    clock.tick(600)
    pp.item_done(b, "polish", 2, "b", now=clock)
    assert pp.eta_seconds(pp.load(b)) == 8 * 600  # 8 chapters left at a measured 10 minutes each


def test_the_estimate_follows_the_recent_pace_not_the_whole_history(tmp_path):
    clock, b = Clock(), _book(tmp_path)
    pp.begin_pass(b, "polish", 40, now=clock)
    for i in range(1, 11):  # ten slow chapters
        clock.tick(1200)
        pp.item_done(b, "polish", i, f"c{i}", now=clock)
    for i in range(11, 21):  # then ten fast ones
        clock.tick(300)
        pp.item_done(b, "polish", i, f"c{i}", now=clock)
    assert pp.eta_seconds(pp.load(b)) == 20 * 300


def test_a_stale_record_says_how_long_ago_instead_of_pretending_to_be_live(tmp_path):
    clock, b = Clock(), _book(tmp_path)
    pp.begin_pass(b, "polish", 5, now=clock)
    clock.tick(300)
    pp.item_done(b, "polish", 1, "a", now=clock)
    clock.tick(3 * 3600)
    assert "3h" in pp.progress_line(b, now=clock) and "ago" in pp.progress_line(b, now=clock)


def test_a_new_pass_replaces_the_old_one_and_clear_removes_it(tmp_path):
    clock, b = Clock(), _book(tmp_path)
    pp.begin_pass(b, "polish", 5, now=clock)
    pp.begin_pass(b, "reconcile", 7, now=clock)
    assert pp.load(b)["pass"] == "reconcile" and pp.load(b)["done"] == 0
    pp.clear(b)
    assert pp.load(b) is None


def test_recording_never_raises_on_a_bad_directory(tmp_path):
    assert pp.item_done(tmp_path / "does" / "not" / "exist", "polish", 1, "x") is False


def test_the_file_is_valid_json_and_written_atomically(tmp_path):
    b = _book(tmp_path)
    pp.begin_pass(b, "polish", 3)
    pp.item_done(b, "polish", 1, "x")
    assert json.loads((b / "_system" / "phase-progress.json").read_text())["done"] == 1
    assert not list((b / "_system").glob("*.tmp"))


def test_preflight_will_not_treat_the_progress_file_as_a_dirty_tree():
    text = (Path(__file__).resolve().parents[1] / "phases" / "preflight.py").read_text(encoding="utf-8")
    assert '"/_system/phase-progress.json"' in text
