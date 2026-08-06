#!/usr/bin/env python3
"""sync_codex_agents.py — regenerate .codex/agents/*.toml from the canonical specs.

`sync-agent-wrappers.sh` already keeps three of the four agent mirrors byte-identical:
`infra/claude-agents/<name>.md` (canonical) -> `.github/agents/<name>.agent.md` ->
`.claude/agents/<name>.md`. The FOURTH mirror, `.codex/agents/<name>.toml`, was
never wired to anything, and it rotted exactly as an unsynced copy always does.

The 2026-07-20 post-merge sweep found `book-challenger.toml` stuck a whole
generation behind: it had been hand-grafted with the new Pass 3 table but was
missing the sentence that makes Pass 3 a GATE, along with the entire
translation-edition route section and all three self-study passes. An agent driven
from the Codex spec therefore ran the narrative-frame checks and treated the
results as advisory. The docs-sweep rule in CLAUDE.md names all four mirrors, so
this was a rule with no mechanism behind it.

The transform is deterministic — frontmatter `name` and `description` become the
scalar keys, everything after the frontmatter becomes `developer_instructions` —
so the TOML never needs to be edited by hand again. Edit the canonical markdown.

Only regenerates TOMLs that ALREADY exist. The Codex set is a curated subset of
the agent roster (18 of 24), and silently promoting an agent into another tool's
registry is not this script's call to make; an agent with no `.toml` yet is left
alone rather than created.

The REVERSE case — a `.toml` whose canonical spec has been retired — is an
orphan, not a curated absence, and IS deleted in sync mode / failed in check
mode (added 2026-08-05, mirroring the reverse sweep `sync-agent-wrappers.sh`
already runs for the other three mirrors). Before this, an orphaned `.toml`
only printed a NOTE and exited 0 even under `--check`, which is exactly how
`reconcile.toml` survived for two months after its canonical spec was deleted.

Modes:
    sync_codex_agents.py            rewrite drifted TOMLs, delete orphaned ones
    sync_codex_agents.py --check    exit non-zero on drift OR an orphan, write nothing
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CANONICAL_DIR = REPO_ROOT / "infra" / "claude-agents"
CODEX_DIR = REPO_ROOT / ".codex" / "agents"

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def _split_frontmatter(text: str) -> tuple[str, str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return "", text
    return match.group(1), text[match.end() :]


def _scalar(frontmatter: str, key: str) -> str:
    """Read one top-level scalar out of the frontmatter.

    Deliberately not a YAML parse: the frontmatter also carries a nested
    `challenger_contract:` block, and a real parser would pull in a dependency to
    read two strings. Matches `key: value` at column zero only, so nested keys of
    the same name cannot shadow the one we want.
    """
    match = re.search(rf"(?m)^{re.escape(key)}:[ \t]*(.+?)[ \t]*$", frontmatter)
    if not match:
        return ""
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def _toml_basic_string(value: str) -> str:
    """Quote a TOML basic string. Only backslash and double quote need escaping here."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_toml(canonical_md: str, name: str) -> str:
    """Render one canonical spec as TOML.

    The body goes in a LITERAL multi-line string (`'''`), not a basic one
    (`\"\"\"`). A basic string interprets backslash escapes, and these specs are
    full of regexes — `max-height|height:\\s*100vh`, `EP\\d\\d`, `Version: \\d` —
    so the first generated set left three of eighteen files unparseable, and a
    future spec containing a valid-looking `\\t` would have been silently mangled
    instead. A literal string interprets nothing, which is exactly right for
    embedding prose verbatim.
    """
    frontmatter, body = _split_frontmatter(canonical_md)
    description = _scalar(frontmatter, "description")
    declared = _scalar(frontmatter, "name") or name
    body = body.strip("\n")
    if "'''" in body:
        raise ValueError(f"{name}: body contains a literal triple quote and cannot be embedded in TOML")
    return (
        f"name = {_toml_basic_string(declared)}\n"
        f"description = {_toml_basic_string(description)}\n"
        f"developer_instructions = '''\n{body}'''\n"
    )


def main(argv: list[str]) -> int:
    check = "--check" in argv or "check" in argv[1:2]
    if not CODEX_DIR.is_dir():
        print("no .codex/agents/ directory — nothing to sync")
        return 0

    drift = 0
    errors = 0
    orphans = 0
    for toml_path in sorted(CODEX_DIR.glob("*.toml")):
        name = toml_path.stem
        canonical = CANONICAL_DIR / f"{name}.md"
        if not canonical.is_file():
            # An orphan, not a curated absence: the canonical spec USED to exist
            # (this file was rendered from it) and was retired without anyone
            # deleting the .codex copy. `reconcile.toml` survived exactly this
            # way for two months — this branch used to only print a NOTE and
            # exit 0 even in --check mode, so nothing ever caught it. Deleted in
            # sync mode, failed in check mode, mirroring the reverse sweep
            # sync-agent-wrappers.sh already runs for the other three mirrors.
            orphans += 1
            rel = toml_path.relative_to(REPO_ROOT)
            if check:
                print(f"ORPHAN:  {rel} (no canonical infra/claude-agents/{name}.md)", file=sys.stderr)
            else:
                toml_path.unlink()
                print(f"removed  {rel} (orphan — canonical spec no longer exists)")
            continue
        try:
            rendered = render_toml(canonical.read_text(encoding="utf-8"), name)
        except ValueError as exc:
            # Counted separately from drift so it fails in SYNC mode too. Treating
            # it as drift meant an unrenderable spec printed to stderr and exited
            # clean, which is how three unparseable files shipped.
            print(f"ERROR: {exc}", file=sys.stderr)
            errors += 1
            continue
        if toml_path.read_text(encoding="utf-8") == rendered:
            continue
        drift += 1
        rel = toml_path.relative_to(REPO_ROOT)
        if check:
            print(f"DRIFT:   {rel}", file=sys.stderr)
        else:
            toml_path.write_text(rendered, encoding="utf-8")
            print(f"synced   {rel}")

    if errors:
        print(f"\n{errors} Codex spec(s) could not be rendered.", file=sys.stderr)
        return 1
    if check and (drift or orphans):
        if drift:
            print(f"\n{drift} Codex spec(s) drifted from canonical.", file=sys.stderr)
            print("Run: python3 scripts/podcast/sync_codex_agents.py", file=sys.stderr)
        if orphans:
            print(f"\n{orphans} Codex spec(s) orphaned (canonical spec retired).", file=sys.stderr)
            print("Run: python3 scripts/podcast/sync_codex_agents.py", file=sys.stderr)
        return 1
    if check:
        print("all Codex specs in sync")
    elif not drift and not orphans:
        print("all Codex specs already in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
