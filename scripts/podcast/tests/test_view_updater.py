#!/usr/bin/env python3
"""Tests for scripts/podcast/_view_updater.py (wave-completion HTML rendering)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _view_updater as vu  # noqa: E402


SAMPLE_YAML = """\
some_top_level: value

waves:

  - id: W1
    name: "Foundation & Guardrails"
    phases: [P1, P2]
    schedule_intent: "x"
    parallelism: "x"
    blast_radius: "x"
    kickoff_cmd: "x"
    done_signal: "x"
    gates_open_next: "x"
    on_completion:
      update_html_views: true
      target_files:
        - _workspace/plan/view/index.html
      html_summary: |
        Paragraph one about W1.
        Multi-line first paragraph continues here.

        Paragraph two about W1 ending with a period.

  - id: W2
    name: "Observability"
    phases: [P7, P8]
    on_completion:
      update_html_views: true
      target_files:
        - _workspace/plan/view/index.html
      html_summary: |
        Wave 2 summary, single paragraph.

  - id: W3
    name: "Corpus"
    phases: [P9]

  - id: W4
    name: "Control"
    phases: [P11]
    on_completion:
      update_html_views: false
      target_files:
        - _workspace/plan/view/index.html
      html_summary: |
        Should not render — opted out.
"""


class LoadCompletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        )
        self.tmp.write(SAMPLE_YAML)
        self.tmp.close()
        self.yaml_path = Path(self.tmp.name)
        self._saved = vu.PLAN_YAML
        vu.PLAN_YAML = self.yaml_path

    def tearDown(self):
        vu.PLAN_YAML = self._saved
        self.yaml_path.unlink(missing_ok=True)

    def test_loads_w1_with_two_paragraphs(self):
        wc = vu._load_wave_completion(1)
        self.assertIsNotNone(wc)
        self.assertEqual(wc.wave_id, "W1")
        self.assertIn("Foundation", wc.wave_name)
        self.assertIn("Paragraph one about W1", wc.html_summary)
        self.assertIn("Paragraph two about W1", wc.html_summary)

    def test_loads_w2_with_single_paragraph(self):
        wc = vu._load_wave_completion(2)
        self.assertIsNotNone(wc)
        self.assertIn("Wave 2 summary", wc.html_summary)

    def test_w3_missing_on_completion_returns_none(self):
        self.assertIsNone(vu._load_wave_completion(3))

    def test_w4_opted_out_returns_none(self):
        """`update_html_views: false` → no render."""
        self.assertIsNone(vu._load_wave_completion(4))

    def test_unknown_wave_returns_none(self):
        self.assertIsNone(vu._load_wave_completion(99))


class RenderBlockTests(unittest.TestCase):
    def test_block_has_markers(self):
        wc = vu.WaveCompletion(
            wave_id="W1", wave_name="Foundation",
            html_summary="One paragraph.\n",
            target_files=(),
        )
        block = vu._render_html_block(wc)
        self.assertIn("<!-- WAVE_SUMMARY_W1_START -->", block)
        self.assertIn("<!-- WAVE_SUMMARY_W1_END -->", block)
        self.assertIn("W1 · Foundation", block)
        self.assertIn("<p>One paragraph.</p>", block)

    def test_multi_paragraph_renders_separate_p_tags(self):
        wc = vu.WaveCompletion(
            wave_id="W2", wave_name="X",
            html_summary="Para one.\n\nPara two.\n",
            target_files=(),
        )
        block = vu._render_html_block(wc)
        self.assertEqual(block.count("<p>"), 2)

    def test_html_escapes_special_chars(self):
        wc = vu.WaveCompletion(
            wave_id="W1", wave_name="Foundation & Guardrails",
            html_summary="<script>alert</script>",
            target_files=(),
        )
        block = vu._render_html_block(wc)
        self.assertIn("&amp;", block)
        self.assertIn("&lt;script&gt;", block)
        self.assertNotIn("<script>alert</script>", block)


class EnsureSectionTests(unittest.TestCase):
    def test_inserts_before_main_close(self):
        html = "<body><main><h1>x</h1></main></body>"
        out = vu._ensure_completions_section(html)
        self.assertIn(vu.COMPLETION_SECTION_ANCHOR, out)
        self.assertLess(out.index(vu.COMPLETION_SECTION_ANCHOR), out.index("</main>"))

    def test_inserts_before_body_close_when_no_main(self):
        html = "<body><h1>x</h1></body>"
        out = vu._ensure_completions_section(html)
        self.assertIn(vu.COMPLETION_SECTION_ANCHOR, out)
        self.assertLess(out.index(vu.COMPLETION_SECTION_ANCHOR), out.index("</body>"))

    def test_idempotent_when_anchor_already_present(self):
        html = f"<body><main>{vu.COMPLETION_SECTION_ANCHOR}</main></body>"
        out = vu._ensure_completions_section(html)
        self.assertEqual(out, html)


class ReplaceMarkerBlockTests(unittest.TestCase):
    def test_replaces_existing_block(self):
        html = (
            "<body>"
            "<!-- WAVE_SUMMARY_W1_START -->OLD<!-- WAVE_SUMMARY_W1_END -->"
            "</body>"
        )
        new_block = "<!-- WAVE_SUMMARY_W1_START -->NEW<!-- WAVE_SUMMARY_W1_END -->"
        out, changed = vu._replace_marker_block(html, "W1", new_block)
        self.assertTrue(changed)
        self.assertIn("NEW", out)
        self.assertNotIn("OLD", out)

    def test_idempotent_when_block_matches(self):
        block = "<!-- WAVE_SUMMARY_W1_START -->X<!-- WAVE_SUMMARY_W1_END -->"
        html = f"<body>{block}</body>"
        out, changed = vu._replace_marker_block(html, "W1", block)
        self.assertFalse(changed)
        self.assertEqual(out, html)

    def test_inserts_when_marker_block_absent_but_anchor_present(self):
        html = f"<body>{vu.COMPLETION_SECTION_ANCHOR}</body>"
        new_block = "<!-- WAVE_SUMMARY_W3_START -->X<!-- WAVE_SUMMARY_W3_END -->"
        out, changed = vu._replace_marker_block(html, "W3", new_block)
        self.assertTrue(changed)
        self.assertIn("W3_START", out)


class UpdateViewForWaveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        # Build a minimal repo layout
        plan_dir = self.repo / "_workspace" / "plan"
        view_dir = plan_dir / "view"
        view_dir.mkdir(parents=True)
        self.yaml_path = plan_dir / "podcast-plan.yaml"
        self.yaml_path.write_text(SAMPLE_YAML)
        self.view_path = view_dir / "index.html"
        self.view_path.write_text(
            "<html><body><main><h1>Plan</h1></main></body></html>"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_first_update_adds_section_and_w1_block(self):
        result = vu.update_view_for_wave(1, repo_root=self.repo, plan_yaml=self.yaml_path)
        self.assertFalse(result["missing_summary"])
        self.assertEqual(len(result["updated"]), 1)
        html = self.view_path.read_text()
        self.assertIn(vu.COMPLETION_SECTION_ANCHOR, html)
        self.assertIn("W1 · Foundation", html)
        self.assertIn("Paragraph one about W1", html)
        self.assertIn("Paragraph two about W1", html)

    def test_second_update_idempotent(self):
        vu.update_view_for_wave(1, repo_root=self.repo, plan_yaml=self.yaml_path)
        first = self.view_path.read_text()
        result = vu.update_view_for_wave(1, repo_root=self.repo, plan_yaml=self.yaml_path)
        second = self.view_path.read_text()
        self.assertEqual(first, second)
        self.assertEqual(result["updated"], [])
        self.assertEqual(len(result["skipped"]), 1)

    def test_multi_wave_updates_compose(self):
        vu.update_view_for_wave(1, repo_root=self.repo, plan_yaml=self.yaml_path)
        vu.update_view_for_wave(2, repo_root=self.repo, plan_yaml=self.yaml_path)
        html = self.view_path.read_text()
        self.assertIn("W1 · Foundation", html)
        self.assertIn("W2 · Observability", html)

    def test_missing_summary_returns_flag_no_write(self):
        before_mtime = self.view_path.stat().st_mtime_ns
        result = vu.update_view_for_wave(3, repo_root=self.repo, plan_yaml=self.yaml_path)
        after_mtime = self.view_path.stat().st_mtime_ns
        self.assertTrue(result["missing_summary"])
        self.assertEqual(before_mtime, after_mtime)

    def test_opt_out_returns_missing_summary(self):
        """W4 has on_completion.update_html_views: false → treated as missing_summary."""
        result = vu.update_view_for_wave(4, repo_root=self.repo, plan_yaml=self.yaml_path)
        self.assertTrue(result["missing_summary"])

    def test_summary_edit_in_yaml_re_renders(self):
        vu.update_view_for_wave(1, repo_root=self.repo, plan_yaml=self.yaml_path)
        # Edit the YAML summary
        text = self.yaml_path.read_text().replace(
            "Paragraph one about W1.", "TOTALLY DIFFERENT W1 OPENING."
        )
        self.yaml_path.write_text(text)
        result = vu.update_view_for_wave(1, repo_root=self.repo, plan_yaml=self.yaml_path)
        self.assertEqual(len(result["updated"]), 1)
        self.assertIn("TOTALLY DIFFERENT W1 OPENING", self.view_path.read_text())


if __name__ == "__main__":
    unittest.main()
