#!/usr/bin/env python3
"""F38 close-out grep gate (DR-015 token-pool isolation).

Unattended pipeline code MUST invoke the model via the Anthropic SDK
(make_sdk_invoke_fn / spawn_claude), never by shelling out to the interactive
`claude -p` binary (which would divert spend off the isolated metered pool and
cannot be cost-covered). This test fails if any executable `subprocess.* ["claude",
…]` invocation reappears in the unattended modules.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]

# Modules that run unattended (bulk phases / chunked authoring / tighten).
UNATTENDED = [
    "_chunking.py",
    "tighten_source.py",
    "_tighten_helpers.py",
]

# An executable shellout to the `claude` CLI, e.g. subprocess.run(["claude", "-p", …])
# or subprocess.Popen(("claude", …)). Comments / docstrings mentioning `claude -p`
# are fine — only actual invocations are forbidden.
CLAUDE_SHELLOUT = re.compile(
    r"subprocess\.(?:run|Popen|call|check_output)\(\s*[\[(]\s*[\"']claude[\"']",
)


@pytest.mark.parametrize("module", UNATTENDED)
def test_no_claude_cli_shellout(module):
    path = SCRIPTS_PODCAST / module
    assert path.is_file(), f"expected unattended module missing: {module}"
    src = path.read_text(encoding="utf-8")
    hits = CLAUDE_SHELLOUT.findall(src)
    assert not hits, (
        f"{module}: found a `claude` CLI shellout — unattended code must use the "
        f"Anthropic SDK path (F38/DR-015), not `claude -p`."
    )


def test_sdk_path_present():
    """Positive assertion: the SDK invocation helpers still exist."""
    chunking = (SCRIPTS_PODCAST / "_chunking.py").read_text(encoding="utf-8")
    tighten = (SCRIPTS_PODCAST / "_tighten_helpers.py").read_text(encoding="utf-8")
    assert "make_sdk_invoke_fn" in chunking
    assert "messages.create" in tighten


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
