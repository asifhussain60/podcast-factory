"""tests/test_archetypes.py — Tests for scripts/podcast/_archetypes.py"""
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts" / "podcast"
sys.path.insert(0, str(SCRIPTS_DIR))

import _archetypes  # noqa: E402


# ---------------------------------------------------------------------------
# list_archetypes
# ---------------------------------------------------------------------------

def test_list_archetypes_returns_at_least_seven():
    slugs = _archetypes.list_archetypes()
    assert isinstance(slugs, list)
    assert len(slugs) >= 7, f"Expected ≥7 archetypes, found: {slugs}"


def test_list_archetypes_excludes_hidden_dirs():
    slugs = _archetypes.list_archetypes()
    for s in slugs:
        assert not s.startswith("_")
        assert not s.startswith(".")


def test_list_archetypes_is_sorted():
    slugs = _archetypes.list_archetypes()
    assert slugs == sorted(slugs)


# ---------------------------------------------------------------------------
# load_archetype
# ---------------------------------------------------------------------------

def test_load_play_novel():
    _archetypes._cache.clear()
    a = _archetypes.load_archetype("play-novel")
    assert a.slug == "play-novel"
    assert isinstance(a.display_name, str) and a.display_name


def test_load_lecture_series():
    _archetypes._cache.clear()
    a = _archetypes.load_archetype("lecture-series")
    assert a.slug == "lecture-series"


def test_load_scholarly_deep_dive():
    _archetypes._cache.clear()
    a = _archetypes.load_archetype("scholarly-deep-dive")
    assert a.slug == "scholarly-deep-dive"
    assert "A" in a.challenger_categories_active  # citations always required


def test_load_aphorism_collection():
    _archetypes._cache.clear()
    a = _archetypes.load_archetype("aphorism-collection")
    assert a.slug == "aphorism-collection"


def test_load_narrative_prose():
    _archetypes._cache.clear()
    a = _archetypes.load_archetype("narrative-prose")
    assert a.slug == "narrative-prose"


def test_load_socratic_dialogue():
    _archetypes._cache.clear()
    a = _archetypes.load_archetype("socratic-dialogue")
    assert a.slug == "socratic-dialogue"


def test_load_missing_archetype_raises():
    _archetypes._cache.clear()
    with pytest.raises(FileNotFoundError):
        _archetypes.load_archetype("does-not-exist-archetype-xyz")


def test_load_archetype_is_cached():
    _archetypes._cache.clear()
    a1 = _archetypes.load_archetype("play-novel")
    a2 = _archetypes.load_archetype("play-novel")
    assert a1 is a2


def test_archetype_has_non_empty_spec_text():
    _archetypes._cache.clear()
    a = _archetypes.load_archetype("scholarly-deep-dive")
    assert len(a.spec_yml_text) > 10
    assert len(a.exemplar_md_text) > 10
    assert len(a.anti_patterns_md_text) > 10


# ---------------------------------------------------------------------------
# resolve_archetype_for_book
# ---------------------------------------------------------------------------

def test_resolve_underscore_variant():
    _archetypes._cache.clear()
    result = _archetypes.resolve_archetype_for_book({"archetype_id": "scholarly_deep_dive"})
    assert result is not None
    assert result.slug == "scholarly-deep-dive"


def test_resolve_hyphen_variant():
    _archetypes._cache.clear()
    result = _archetypes.resolve_archetype_for_book({"archetype_id": "play-novel"})
    assert result is not None
    assert result.slug == "play-novel"


def test_resolve_fallback_key():
    _archetypes._cache.clear()
    result = _archetypes.resolve_archetype_for_book({"archetype": "lecture-series"})
    assert result is not None
    assert result.slug == "lecture-series"


def test_resolve_empty_meta_returns_none():
    result = _archetypes.resolve_archetype_for_book({})
    assert result is None


def test_resolve_unknown_archetype_returns_none_with_warning():
    import warnings
    _archetypes._cache.clear()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = _archetypes.resolve_archetype_for_book({"archetype_id": "unknown-archetype-xyz"})
    assert result is None
    assert len(w) == 1
    assert "not found on disk" in str(w[0].message)
