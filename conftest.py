"""Repo-wide pytest hooks (the repo-surgeon suite's own hooks live in tests/conftest.py).

Skip budget: a skipped test reads as a pass. Ten-plus tests skip with "this book is not present in this checkout", so on
a checkout without the content a whole class of checks silently disappears from CI. When PF_SKIP_BUDGET is set (CI sets
it), a run that skips MORE tests than the budget fails, and `-rs` prints why each one skipped. Unset locally: no gate.
The budget is a tripwire against mass-skipping, deliberately generous, not a target.
"""

import os


def pytest_sessionfinish(session, exitstatus):
    raw = os.environ.get("PF_SKIP_BUDGET")
    if not raw:
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    skipped = len(reporter.stats.get("skipped", [])) if reporter else 0
    if skipped > int(raw):
        if reporter:
            reporter.write_line(
                f"\nSKIP BUDGET EXCEEDED: {skipped} tests skipped, budget is {raw}. Skipped tests read as passes; "
                "see the -rs reasons above and either restore what they need or raise the budget on purpose.",
                red=True,
            )
        session.exitstatus = 1
