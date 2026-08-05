"""The generated Codex agent specs must be parseable TOML.

The first generated set was not. `render_toml` embedded each spec's body in a TOML
BASIC multi-line string, which interprets backslash escapes — and these specs are
full of regexes (`max-height|height:\\s*100vh`, `EP\\d\\d`, `Version: \\d`), so
three of eighteen files shipped unparseable and a future spec containing a
valid-looking `\\t` would have been silently mangled instead of failing loudly.

The `--check` mode could not catch it: it compares generated text to file text, and
both were equally broken. Validity needs its own test, which is this one.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sync_codex_agents  # noqa: E402
from sync_codex_agents import CODEX_DIR, main, render_toml  # noqa: E402

try:  # tomllib lands in 3.11; tomli is the backport this repo's 3.9 needs.
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - depends on interpreter
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

_SPECS = sorted(CODEX_DIR.glob("*.toml")) if CODEX_DIR.is_dir() else []

pytestmark = pytest.mark.skipif(tomllib is None, reason="no TOML parser available")


@pytest.mark.parametrize("spec", _SPECS, ids=lambda p: p.stem)
def test_generated_spec_is_valid_toml(spec: Path) -> None:
    data = tomllib.load(spec.open("rb"))
    assert set(data) == {"name", "description", "developer_instructions"}, spec.name
    assert data["developer_instructions"].strip(), f"{spec.name} has an empty body"


def test_a_body_full_of_regex_escapes_survives_the_round_trip() -> None:
    """The exact shape that broke three specs: backslashes in the prose."""
    canonical = (
        '---\nname: probe\ndescription: "A probe spec."\n---\n\n'
        "Match `max-height|height:\\s*100vh` and `EP\\d\\d` and `Version: \\d`.\n"
        "Also a Windows-looking path: C:\\Users\\nobody and a tab escape \\t.\n"
    )
    rendered = render_toml(canonical, "probe")
    data = tomllib.loads(rendered)
    assert "\\s*100vh" in data["developer_instructions"]
    assert "\\d\\d" in data["developer_instructions"]
    assert "C:\\Users\\nobody" in data["developer_instructions"]
    assert "\\t" in data["developer_instructions"]


def test_a_body_containing_the_delimiter_is_refused_not_mangled() -> None:
    canonical = "---\nname: probe\ndescription: \"x\"\n---\n\nA body with ''' inside it.\n"
    with pytest.raises(ValueError, match="triple quote"):
        render_toml(canonical, "probe")


def _isolated_dirs(tmp_path, monkeypatch):
    """Point the module at a scratch pair of directories for one test."""
    codex_dir = tmp_path / ".codex" / "agents"
    canonical_dir = tmp_path / "infra" / "claude-agents"
    codex_dir.mkdir(parents=True)
    canonical_dir.mkdir(parents=True)
    monkeypatch.setattr(sync_codex_agents, "CODEX_DIR", codex_dir)
    monkeypatch.setattr(sync_codex_agents, "CANONICAL_DIR", canonical_dir)
    monkeypatch.setattr(sync_codex_agents, "REPO_ROOT", tmp_path)
    return codex_dir, canonical_dir


def test_orphaned_toml_fails_check_and_is_untouched(tmp_path, monkeypatch) -> None:
    """A .toml whose canonical spec was retired is an orphan, not a curated
    absence — exactly the shape that let reconcile.toml survive two months
    after infra/claude-agents/reconcile.md was deleted. --check must fail
    loudly rather than print a NOTE and exit 0."""
    codex_dir, _ = _isolated_dirs(tmp_path, monkeypatch)
    orphan = codex_dir / "retired-agent.toml"
    orphan.write_text('name = "retired-agent"\n', encoding="utf-8")

    exit_code = main(["prog", "--check"])

    assert exit_code == 1
    assert orphan.exists(), "check mode must never delete"


def test_orphaned_toml_is_deleted_in_sync_mode(tmp_path, monkeypatch) -> None:
    codex_dir, _ = _isolated_dirs(tmp_path, monkeypatch)
    orphan = codex_dir / "retired-agent.toml"
    orphan.write_text('name = "retired-agent"\n', encoding="utf-8")

    exit_code = main(["prog"])

    assert exit_code == 0
    assert not orphan.exists()


def test_a_toml_with_a_live_canonical_spec_is_not_an_orphan(tmp_path, monkeypatch) -> None:
    """Control: a toml whose canonical spec still exists must survive --check
    (assuming it isn't drifted) — only a genuinely retired canonical trips
    the orphan path."""
    codex_dir, canonical_dir = _isolated_dirs(tmp_path, monkeypatch)
    canonical = canonical_dir / "live-agent.md"
    canonical.write_text('---\nname: live-agent\ndescription: "x"\n---\n\nBody.\n', encoding="utf-8")
    toml_path = codex_dir / "live-agent.toml"
    toml_path.write_text(render_toml(canonical.read_text(encoding="utf-8"), "live-agent"), encoding="utf-8")

    exit_code = main(["prog", "--check"])

    assert exit_code == 0
    assert toml_path.exists()
