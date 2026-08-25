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

import ast
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

    # `source_commit` and `generated_at` were asserted here until 2026-08-06, and
    # both generators had already stopped writing them: a tracked file cannot
    # contain its own not-yet-created commit hash, so stamping one guaranteed a
    # metadata-only diff on every subsequent commit, forever. Commit 6fff0b6
    # removed the fields — and strips them from an already-committed file — which
    # is what byte-identical output required. These two assertions were the
    # leftover, and they are the reason this suite reported two failures on
    # `develop` while both generators were behaving exactly as designed. The
    # remaining check is the one the class docstring actually claims.

    def test_each_snapshot_is_valid_json(self):
        data_dir = REPO / "plan-dashboard" / "src" / "data"
        names = [
            "architecture-snapshot.json",
            "dashboard-snapshot.json",
            "infrastructure-snapshot.json",
        ]
        for name in names:
            with self.subTest(snapshot=name):
                snap = json.loads((data_dir / name).read_text())
                self.assertIsInstance(snap, dict)

    def test_no_snapshot_reintroduces_a_self_referential_timestamp(self):
        """The fields are not merely unasserted — writing one is the bug."""
        data_dir = REPO / "plan-dashboard" / "src" / "data"
        for path in sorted(data_dir.glob("*-snapshot.json")):
            with self.subTest(snapshot=path.name):
                snap = json.loads(path.read_text())
                self.assertNotIn("generated_at", snap)
                self.assertNotIn("source_commit", snap)


class TestSnapshotsDescribeRealContent(unittest.TestCase):
    """The class of bug where a snapshot field is structurally empty.

    Found on 2026-07-30, four instances at once. Both generators read
    ``content/drafts`` — deleted by the 2026-06-04 restructure — so the directory
    walk threw ENOENT, the catch returned ``[]``, and the dashboard reported "0
    books in flight" for two months while six books sat mid-pipeline. Two more
    fields (``metrics``, ``books_shipped``) were never computed at all, so the
    Roadmap showed $0 spent and the Overview opened with "0 books published, 0
    episodes" over two finished books.

    Every one of them rendered as a confident zero. That is the failure mode these
    tests exist for: a dead path that degrades to an empty collection is worse than
    one that raises, because the empty collection looks like an answer. So rather
    than assert on source text, each test below asserts the snapshot AGREES WITH THE
    FILESYSTEM — the only check that would have caught the original.
    """

    def setUp(self):
        self.snap = json.loads((REPO / "plan-dashboard" / "src" / "data" / "dashboard-snapshot.json").read_text())
        self.content = REPO / "content"

    def _book_dirs(self):
        """Every book folder on disk, by the bucket layout the resolver defines.

        Bucket list is READ from regenerate-snapshots.py rather than duplicated
        here — a hardcoded copy is exactly what went stale when the Sessions
        bucket was added and this test kept scanning the four buckets that
        predate it, reporting every Sessions-lane in-flight book as a phantom
        snapshot entry.
        """
        buckets_line = next(line for line in PY.read_text().splitlines() if line.strip().startswith("BUCKETS"))
        buckets = ast.literal_eval(buckets_line.split("=", 1)[1].strip())
        out = []
        for bucket in buckets:
            root = self.content / bucket
            if not root.is_dir():
                continue
            out += [d for d in root.iterdir() if d.is_dir() and not d.name.startswith("_") and d.name == d.name.lower()]
        return out

    def test_neither_generator_still_points_at_the_retired_drafts_tree(self):
        """`content/drafts` may appear only as a legacy FALLBACK, never as the sole root."""
        for path in (PY, MJS):
            with self.subTest(generator=path.name):
                text = path.read_text()
                self.assertIn(
                    "Islamic",
                    text,
                    f"{path.name} does not know about the bucket layout — it can only "
                    "be reading a tree that no longer exists",
                )

    def test_books_in_flight_matches_the_books_actually_in_flight(self):
        on_disk = set()
        for d in self._book_dirs():
            state_path = d / "_system" / "orchestrator-state.json"
            if not state_path.is_file():
                continue
            try:
                state = json.loads(state_path.read_text())
            except Exception:
                continue
            if state.get("phase") == "done" or state.get("phase_status") in (
                "shipped",
                "merged",
            ):
                continue
            on_disk.add(d.name)
        in_snapshot = {b["slug"] for b in self.snap.get("books_in_flight", [])}
        self.assertEqual(
            in_snapshot,
            on_disk,
            "books_in_flight disagrees with the pipeline state on disk — run `cd plan-dashboard && npm run snapshot`",
        )

    def test_published_books_reach_the_snapshot_with_their_episode_counts(self):
        on_disk = {}
        for d in self._book_dirs():
            state_path = d / "_system" / "orchestrator-state.json"
            if not state_path.is_file():
                continue
            try:
                state = json.loads(state_path.read_text())
            except Exception:
                continue
            if state.get("status") != "published":
                continue
            eps = d / "episodes"
            on_disk[d.name] = (
                sum(1 for e in eps.iterdir() if e.is_file() and re.match(r"^EP\d+.*\.txt$", e.name))
                if eps.is_dir()
                else 0
            )
        in_snapshot = {b["slug"]: b["episodes"] for b in self.snap.get("books_shipped", [])}
        self.assertEqual(in_snapshot, on_disk)

    def test_roadmap_uses_one_closed_status_vocabulary(self):
        """plan.yaml says "finished" eight ways; exactly one may reach the site.

        The snapshot carried both `complete` and `completed`, and every consumer
        tests `=== "complete"` — so 61 finished steps read as unfinished and the
        Roadmap said 56 of 140 done when the real number was 117.
        """
        allowed = {"complete", "in_progress", "pending", "deferred"}
        seen = {s.get("status") for s in self.snap.get("roadmap", [])}
        self.assertTrue(
            seen <= allowed,
            f"un-normalized status(es) reached the snapshot: {sorted(seen - allowed)}. "
            "Map them in normalize_step_status / normalizeStepStatus, not in the pages.",
        )

    def test_spend_is_a_number_the_generator_actually_computed(self):
        """`metrics` was never written, so the Spend card summed an absent key."""
        metrics = self.snap.get("metrics")
        self.assertIsInstance(metrics, dict)
        self.assertIn(
            "burn_30d_usd",
            metrics,
            "the Roadmap's Spend / 30 Days card reads this key; an absent one renders $0",
        )
        self.assertIsInstance(metrics["burn_30d_usd"], (int, float))


class TestAgentEntriesAreReDerived(unittest.TestCase):
    """An agent's snapshot entry must be re-read from its spec on EVERY run.

    Both generators used to short-circuit on an id they had already recorded:

        if agent_id in existing_agents:      # .py
            agents.append(existing_agents[agent_id]); continue
        if (existingAgentById.has(id)) return existingAgentById.get(id);   // .mjs

    So frontmatter was read once, on an agent's first appearance, and frozen. Both
    legs shared the behaviour, which is why every parity test above stayed green:
    the pair AGREED and was wrong together — the same shape as the bucket-list gap
    below. The live site served a description of `repo-surgeon` retired three weeks
    earlier, and 7 of 23 agents were stale when this was found (2026-08-17).

    The fix re-derives name/role/plain/what_it_knows always, and merge-preserves
    only the curated fields — the ones hand-authored in the JSON that no
    frontmatter supplies. That list must be identical in both legs or a curated
    value survives on one machine and is reset on the other, which is precisely
    the forever-reverting diff this file exists to prevent.
    """

    def test_neither_generator_short_circuits_on_a_known_agent(self):
        py = PY.read_text()
        self.assertNotIn(
            "if agent_id in existing_agents:",
            py,
            "the .py leg is back to freezing an agent entry on first sight",
        )
        mjs = MJS.read_text()
        self.assertNotIn(
            "if (existingAgentById.has(id)) return existingAgentById.get(id);",
            mjs,
            "the .mjs leg is back to freezing an agent entry on first sight",
        )

    def test_both_legs_declare_the_same_curated_fields(self):
        def curated(path: Path) -> list[str]:
            match = re.search(r"AGENT_CURATED_FIELDS\s*=\s*[\(\[]([^\)\]]*)[\)\]]", path.read_text())
            self.assertIsNotNone(match, f"no AGENT_CURATED_FIELDS literal in {path.name}")
            return re.findall(r"[\"']([a-z_]+)[\"']", match.group(1))

        expected = curated(PY)
        self.assertIn("failure_mode", expected, "authority list looks truncated")
        self.assertEqual(
            curated(MJS),
            expected,
            "regenerate-snapshots.mjs and .py disagree about which agent fields are "
            "curated; a curated value would survive on one machine and reset on the "
            "other. Change both legs in one commit.",
        )

    def test_agent_files_are_read_in_a_stable_order(self):
        """readdir() order is not guaranteed; the .py leg sorts, so the .mjs must too."""
        mjs = MJS.read_text()
        self.assertRegex(
            mjs,
            r'f !== "_README\.md"\)\s*\.sort\(\)',
            "the .mjs leg reads infra/claude-agents in readdir order while the .py "
            "leg sorts — the agents array can differ by machine",
        )


class TestBucketListsTrackTheAuthority(unittest.TestCase):
    """Every restated copy of the bucket list must match `_content_types.BUCKETS`.

    The two generators were pinned to EACH OTHER and to nothing else, so when
    "Supplications" was appended to the authority on 2026-07-19 they stayed at four
    buckets and AGREED about it — byte-identical, both wrong. `site-health-smoke.mjs`
    carried a third copy with the same gap.

    Nothing was visibly broken because `content/Supplications/` does not exist yet.
    That is the point: the day the first supplication book lands it would have been
    absent from all three snapshot JSONs and its routes never visited by the smoke
    gate, with every test green. Pinning to the authority is what turns "wrong and
    latent" into "wrong and failing".

    The copies are restatements rather than imports because these scripts run under
    plain node with no TS resolver; this test is the price of that.
    """

    AUTHORITY = REPO / "scripts" / "podcast" / "_content_types.py"
    COPIES = (
        SCRIPTS / "regenerate-snapshots.mjs",
        SCRIPTS / "regenerate-snapshots.py",
        SCRIPTS / "site-health-smoke.mjs",
    )

    def _buckets(self, path: Path) -> list[str]:
        """The bucket names from the first BUCKETS/buckets sequence literal."""
        text = path.read_text()
        match = re.search(
            r"(?:BUCKETS|buckets)\s*(?::\s*tuple\[str, \.\.\.\]\s*)?=\s*[\(\[]([^\)\]]*)[\)\]]",
            text,
        )
        self.assertIsNotNone(match, f"no bucket list literal found in {path.name}")
        return re.findall(r"[\"']([A-Za-z]+)[\"']", match.group(1))

    def test_every_copy_matches_the_authority(self):
        expected = self._buckets(self.AUTHORITY)
        self.assertIn("Supplications", expected, "authority itself lost a bucket")
        for path in self.COPIES:
            with self.subTest(copy=path.name):
                self.assertEqual(
                    self._buckets(path),
                    expected,
                    f"{path.name} restates the bucket list and has drifted from "
                    f"scripts/podcast/_content_types.py::BUCKETS. Add the bucket "
                    f"there first, then update every copy named in this test.",
                )


if __name__ == "__main__":
    unittest.main()
