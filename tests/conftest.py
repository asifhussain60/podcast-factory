"""Hooks for the repo-surgeon suite. The importable harness is tests/_harness.py.

Only the coverage ratchet lives here, because it is the one thing that must be a
hook: it needs the whole session, and a test that needed to sort last would be a
constraint the next person breaks without knowing why.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

# ---------- the coverage ratchet ----------
#
# A check that emits an id no test ever provokes is a check whose rainy path is
# unproven — exactly the condition this suite exists to make impossible. Every
# probe in the suite is built by `_harness.make_probe`, so that is where they are
# registered; at session end every finding any test produced is compared against
# the ids `repo_surgeon_probe.CHECKS` declares.
#
# It enforces ONLY on a run that collected all three repo-surgeon modules. Running
# one file must not report the other two files' ids as uncovered: a gate that fails
# on a legitimate partial run is one people learn to ignore.

_MODULES_SEEN: set[str] = set()

_SUITE = {
    "test_repo_surgeon_probe",
    "test_repo_surgeon_checks",
    "test_repo_surgeon_specs",
}


def pytest_collection_modifyitems(items):
    for item in items:
        _MODULES_SEEN.add(Path(str(item.fspath)).stem)


def pytest_sessionfinish(session, exitstatus):
    if not _SUITE.issubset(_MODULES_SEEN) or exitstatus != 0:
        # A failing suite has a more interesting story to tell first.
        return

    import _harness
    import repo_surgeon_probe as probe_mod

    declared = {i for c in probe_mod.CHECKS for i in c.emits}
    emitted = {f.id for p in _harness.PROBES for f in p.findings}
    missing = sorted(declared - emitted)
    if missing:
        session.exitstatus = 1
        print(
            "\n\nCOVERAGE RATCHET FAILED — these finding ids are declared in "
            "repo_surgeon_probe.CHECKS but no test in the suite provoked them:\n  "
            + "\n  ".join(missing)
            + "\n\nEvery declared id needs a defect case. Add one, or drop the id from "
            "the check's `emits` if it can no longer be reached.\n"
        )
