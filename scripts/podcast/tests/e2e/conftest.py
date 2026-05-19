"""Shared fixtures for the podcast end-to-end test suite.

The project tests with stdlib `unittest` today (no pytest dependency in the
system Python yet — pytest lands in P8.1). This `conftest.py` exists as a
placeholder so that:

  1. The P2.1 phase runner detects the file (acceptance row 1 of P2.1).
  2. If/when the project adds pytest to scripts/podcast/requirements.txt,
     pytest will pick this file up automatically and the existing fixture
     resolution paths below will Just Work.

Until then, the helpers below are imported directly by the unittest E2E
tests (`from scripts.podcast.tests.e2e.conftest import tiny_book_dir`).
"""
from __future__ import annotations

from pathlib import Path

E2E_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = E2E_DIR / "fixtures"
TINY_BOOK_DIR = FIXTURES_DIR / "tiny-book"


def tiny_book_dir() -> Path:
    """Return the canonical path to the tiny-book fixture directory."""
    return TINY_BOOK_DIR


def tiny_book_source() -> Path:
    """Path to the synthetic source.md (the canonical input)."""
    return TINY_BOOK_DIR / "source.md"


def tiny_book_raw_extract() -> Path:
    """Path to the raw-extract.md (post-OCR/translate stage)."""
    return TINY_BOOK_DIR / "raw-extract.md"
