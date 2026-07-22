"""tests/test_snapshot_regenerator_parity.py

The Podcast Factory Astro Site reads three snapshot JSONs that TWO generators
write: `plan-dashboard/scripts/regenerate-snapshots.mjs` (primary) and
`regenerate-snapshots.py` (the fallback used when node/npm is unavailable —
`npm run snapshot` chains them with `||`).

Because either may run on any given machine, the two MUST emit byte-identical
files. When they drift, every commit from a node machine reverts the previous
commit from a python machine and back again, forever. These tests lock the
specific ways they drifted:

  1. non-ASCII encoding  — JSON.stringify emits raw UTF-8; json.dumps defaults
                           to ensure_ascii=True and escaped every em dash.
  2. generated_at        — .mjs used wall-clock, .py used the HEAD commit time,
                           so the snapshots were dirty after every run.
  3. generator field     — each stamped its own filename.
  4. wave ordering       — .py sorted plan.yaml's `waves_*` keys; .mjs read them
                           in document order, reordering the whole roadmap.
  5. last_touched typing — an unquoted all-digit SHA in plan.yaml is a string to
                           PyYAML and a number to js-yaml (which also silently
                           drops the leading zero, recording the wrong commit).
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "plan-dashboard" / "scripts"
MJS = SCRIPTS / "regenerate-snapshots.mjs"
PY = SCRIPTS / "regenerate-snapshots.py"
PLAN_YAML = REPO / "_workspace" / "plan" / "refactor" / "plan.yaml"


class TestRegeneratorParity(unittest.TestCase):
    """Source-level invariants that keep the two generators byte-compatible."""

    def test_python_writes_raw_utf8(self):
        """json.dumps must pass ensure_ascii=False to match JSON.stringify."""
        self.assertIn("ensure_ascii=False", PY.read_text())

    def test_neither_generator_stamps_its_own_filename(self):
        """A generator name that differs by runner is a guaranteed diff."""
        for path in (PY, MJS):
            with self.subTest(generator=path.name):
                self.assertNotIn(f'"generator": "{path.name}"', path.read_text())
                self.assertNotIn(f'generator: "{path.name}"', path.read_text())

    def test_generated_at_is_commit_time_not_wall_clock(self):
        """Both derive generated_at from HEAD's commit time, so re-running at the
        same commit is a no-op rather than a fresh diff."""
        mjs = MJS.read_text()
        self.assertIn("log -1 --format=%cI", mjs)
        # Every snapshot-writing site goes through the helper, never Date directly.
        self.assertNotIn("generated_at: new Date().toISOString()", mjs)
        self.assertNotIn("generated_at = new Date().toISOString()", mjs)

        py = PY.read_text()
        self.assertIn("--format=%cI", py)

    def test_python_reads_wave_keys_in_document_order(self):
        """sorted() over plan.yaml's keys put waves_bpv2 ahead of waves_ghj and
        reordered the roadmap away from the .mjs output."""
        py = PY.read_text()
        self.assertNotIn("for key in sorted(plan.keys())", py)


class TestPlanYamlShaTyping(unittest.TestCase):
    """plan.yaml values that both YAML parsers must agree on."""

    def test_last_touched_values_are_strings(self):
        """An unquoted all-digit SHA becomes an int under js-yaml, losing any
        leading zero. Quoting keeps both parsers on the same value."""
        plan = yaml.safe_load(PLAN_YAML.read_text())
        offenders = []
        for key, value in plan.items():
            if key != "waves" and not key.startswith("waves_"):
                continue
            for wave in value or []:
                for step in wave.get("steps") or []:
                    touched = step.get("last_touched")
                    if touched is not None and not isinstance(touched, str):
                        offenders.append((step.get("id"), touched))
        self.assertEqual(
            offenders,
            [],
            f"quote these last_touched values in plan.yaml so js-yaml keeps them as strings: {offenders}",
        )


class TestCommittedSnapshotsAreParseable(unittest.TestCase):
    """The site imports these at build time — a malformed one breaks the build."""

    def test_each_snapshot_is_valid_json_with_a_source_commit(self):
        data_dir = REPO / "plan-dashboard" / "src" / "data"
        names = [
            "architecture-snapshot.json",
            "dashboard-snapshot.json",
            "infrastructure-snapshot.json",
        ]
        for name in names:
            with self.subTest(snapshot=name):
                snap = json.loads((data_dir / name).read_text())
                self.assertIsInstance(snap.get("source_commit"), str)
                self.assertRegex(snap["source_commit"], r"^[0-9a-f]{7,40}$|^unknown$")

    def test_generated_at_is_iso8601(self):
        data_dir = REPO / "plan-dashboard" / "src" / "data"
        pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        for path in sorted(data_dir.glob("*-snapshot.json")):
            with self.subTest(snapshot=path.name):
                snap = json.loads(path.read_text())
                self.assertRegex(snap.get("generated_at", ""), pattern)


if __name__ == "__main__":
    unittest.main()
