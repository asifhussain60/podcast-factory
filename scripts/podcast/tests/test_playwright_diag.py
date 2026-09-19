"""'Chromium is not installed' when it IS installed is a worse message than none.

isaf-al-talib, 2026-09-18: 0book-render reported "Playwright chromium binary is not installed" while
Chromium WAS installed. Playwright 1.60 wanted build 1223 and only 1243 was in the shared cache (another
project's newer Playwright had evicted 1223). Playwright words "missing" and "wrong build" identically, so
the message told a person to install what they already had, and they worked around it with symlinks. This
reads the wanted build out of the error and compares it with what is actually cached.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _playwright_diag as pd  # noqa: E402

WANT_1223 = (
    "book-pdf: chromium unavailable — browserType.launch: Executable doesn't exist at "
    "/Users/x/Library/Caches/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-mac-arm64/chrome-headless-shell"
)


def _cache(tmp_path, *names):
    for n in names:
        (tmp_path / n).mkdir(parents=True)
    return tmp_path


def test_a_different_build_being_installed_is_called_a_revision_mismatch_not_missing(tmp_path):
    text = pd.diagnose_launch_failure(
        WANT_1223, cache_dir=_cache(tmp_path, "chromium-1243", "chromium_headless_shell-1243")
    )
    assert "1223" in text and "1243" in text
    assert "mismatch" in text.lower() or "different build" in text.lower()
    assert "not installed" not in text.lower()


def test_the_remedy_is_the_matching_install_and_warns_against_symlinks(tmp_path):
    text = pd.diagnose_launch_failure(WANT_1223, cache_dir=_cache(tmp_path, "chromium-1243"))
    assert "npx playwright install chromium" in text and "plan-dashboard" in text
    assert "symlink" in text.lower()  # the workaround that hides the real problem
    assert "keeps 1243" in text.replace("keep 1243", "keeps 1243") or "1243" in text


def test_an_empty_cache_is_genuinely_not_installed(tmp_path):
    text = pd.diagnose_launch_failure(WANT_1223, cache_dir=tmp_path)
    assert "not installed" in text.lower() and "npx playwright install chromium" in text


def test_the_wanted_build_being_present_means_something_else_is_wrong(tmp_path):
    text = pd.diagnose_launch_failure(WANT_1223, cache_dir=_cache(tmp_path, "chromium_headless_shell-1223"))
    assert "not installed" not in text.lower() and "mismatch" not in text.lower()
    assert "1223" in text


def test_an_error_that_names_no_build_is_reported_as_it_is(tmp_path):
    text = pd.diagnose_launch_failure("book-pdf: chromium unavailable — spawn ENOMEM", cache_dir=tmp_path)
    assert "ENOMEM" in text


def test_the_render_step_uses_the_diagnosis():
    src = (Path(__file__).resolve().parents[1] / "build_book_pdf.py").read_text(encoding="utf-8")
    assert "diagnose_launch_failure(" in src
