#!/usr/bin/env python3
"""Regression — converge_artifact (shift-left upstream validation for 0b/0e).

Mirrors test_convergence_safety_rails.py in spirit: drives the bounded loop with
fake precheck/discriminator/fixer callbacks so NO LLM is invoked, and pins the
flag-and-proceed + disabled-by-default + cost-ceiling + bounded-rounds contract.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

from _authoring import _artifact_convergence as ac  # noqa: E402


@pytest.fixture
def book(tmp_path):
    bd = tmp_path / "book"
    (bd / "_system").mkdir(parents=True)
    return bd


def _finding(check_id="X-FAKE", severity="P1"):
    return ac.ArtifactFinding(check_id=check_id, severity=severity,
                              signature=check_id, message="fake")


# ─── Pure deterministic pre-checks ───────────────────────────────────────────


class TestPrechecks0b:
    def test_clean_passes(self):
        raw = "a b c d\n\ne f g h\n\ni j k l\n\nm n o p\n\nq r s t"
        assert ac.precheck_refined_english(raw, raw) == []

    def test_empty_is_p0_and_short_circuits(self):
        raw = "a b c d\n\ne f g h\n\ni j k l\n\nm n o p"
        out = ac.precheck_refined_english(raw, "")
        assert [f.check_id for f in out] == ["U0B-EMPTY"]
        assert out[0].severity == "P0"

    def test_length_drift_flagged(self):
        raw = "word " * 1000
        out = ac.precheck_refined_english(raw, "tiny output here")
        assert "U0B-LENGTH-DRIFT" in {f.check_id for f in out}

    def test_structure_collapse_flagged(self):
        raw = "a\n\nb\n\nc\n\nd\n\ne\n\nf"
        # one paragraph, same-ish length → only collapse, not drift
        out = ac.precheck_refined_english(raw, "a b c d e f")
        assert "U0B-STRUCTURE-COLLAPSE" in {f.check_id for f in out}


class TestPrechecks0e:
    def test_clean_passes(self):
        assert ac.precheck_enriched_chapter("a b c", "a b c d") == []

    def test_shrank_flagged(self):
        out = ac.precheck_enriched_chapter("a b c d e f", "a b")
        assert [f.check_id for f in out] == ["U0E-SHRANK"]

    def test_balloon_flagged(self):
        out = ac.precheck_enriched_chapter("a b", "a b c d e f g h i j")
        assert [f.check_id for f in out] == ["U0E-BALLOON"]

    def test_empty_before_is_noop(self):
        assert ac.precheck_enriched_chapter("", "anything here") == []


# ─── Bounded loop: disabled-by-default (Phase A path) ────────────────────────


class TestDisabledByDefault:
    def test_clean_precheck_converges_no_llm(self, book):
        calls = {"disc": 0}

        def _disc():
            calls["disc"] += 1
            return [_finding()]

        out = ac.converge_artifact(
            label="t", book_dir=book,
            precheck_fn=lambda: [],
            discriminator_fn=_disc,   # supplied but cap=0 → must NOT fire
            cost_cap_usd=0.0,
        )
        assert out.converged is True
        assert out.proceeded is True
        assert out.discriminator_calls == 0
        assert calls["disc"] == 0          # LLM never called when cap unset
        assert out.rounds == 1

    def test_findings_without_fixer_flag_and_proceed(self, book):
        # Deterministic finding, no enabled fixer → surface once and proceed.
        out = ac.converge_artifact(
            label="t", book_dir=book,
            precheck_fn=lambda: [_finding()],
            cost_cap_usd=0.0,
        )
        assert out.converged is False
        assert out.proceeded is True
        assert out.fixer_calls == 0
        assert out.rounds == 1             # no fixer → does not loop
        assert any("no enabled fixer" in n for n in out.notes)


# ─── Bounded loop: enabled LLM path (still no real LLM — fakes) ───────────────


class TestEnabledPath:
    def test_discriminator_fires_when_cap_set(self, book):
        calls = {"disc": 0, "fix": 0}

        def _disc():
            calls["disc"] += 1
            return [_finding()] if calls["disc"] == 1 else []

        def _fix(findings):
            calls["fix"] += 1

        out = ac.converge_artifact(
            label="t", book_dir=book,
            precheck_fn=lambda: [],
            discriminator_fn=_disc,
            fixer_fn=_fix,
            cost_cap_usd=5.0,
            cost_fn=lambda: 0.0,
        )
        # round 1: disc finds 1 → fix → round 2: disc clean → converge
        assert out.converged is True
        assert calls["disc"] == 2
        assert calls["fix"] == 1
        assert out.rounds == 2

    def test_bounded_rounds_when_always_dirty(self, book):
        def _disc():
            return [_finding()]

        out = ac.converge_artifact(
            label="t", book_dir=book,
            precheck_fn=lambda: [],
            discriminator_fn=_disc,
            fixer_fn=lambda f: None,
            cost_cap_usd=5.0,
            cost_fn=lambda: 0.0,
        )
        assert out.converged is False
        assert out.proceeded is True
        assert out.rounds == ac.MAX_ARTIFACT_ROUNDS   # exactly the cap, then proceed
        assert any("round cap" in n for n in out.notes)


class TestCostCeiling:
    def test_breach_disables_llm_and_proceeds(self, book):
        calls = {"disc": 0}

        def _disc():
            calls["disc"] += 1
            return [_finding()]

        out = ac.converge_artifact(
            label="t", book_dir=book,
            precheck_fn=lambda: [],
            discriminator_fn=_disc,
            fixer_fn=lambda f: None,
            cost_cap_usd=10.0,
            cost_fn=lambda: 99.0,        # already over ceiling
        )
        assert out.cost_ceiling_tripped and "COST-CEILING" in out.cost_ceiling_tripped
        assert out.proceeded is True     # NEVER raises / blocks
        assert calls["disc"] == 0        # LLM never ran after breach
        assert out.converged is True     # precheck clean → converged on det. only


class TestHeartbeat:
    def test_heartbeat_each_round(self, book):
        beats = []
        ac.converge_artifact(
            label="t", book_dir=book,
            precheck_fn=lambda: [_finding()],
            discriminator_fn=lambda: [],
            fixer_fn=lambda f: None,
            cost_cap_usd=5.0, cost_fn=lambda: 0.0,
            heartbeat=lambda rnd, note: beats.append(rnd),
        )
        assert beats == [1, 2]           # ≤ MAX_ARTIFACT_ROUNDS

    def test_heartbeat_failure_never_breaks(self, book):
        def _boom(rnd, note):
            raise RuntimeError("beat exploded")
        out = ac.converge_artifact(
            label="t", book_dir=book,
            precheck_fn=lambda: [],
            heartbeat=_boom,
        )
        assert out.converged is True


class TestNeverRaises:
    def test_discriminator_exception_degrades_to_deterministic(self, book):
        def _disc():
            raise RuntimeError("disc down")

        out = ac.converge_artifact(
            label="t", book_dir=book,
            precheck_fn=lambda: [],
            discriminator_fn=_disc,
            fixer_fn=lambda f: None,
            cost_cap_usd=5.0, cost_fn=lambda: 0.0,
        )
        assert out.proceeded is True
        assert out.converged is True     # precheck clean, disc failure swallowed
        assert any("discriminator failed" in n for n in out.notes)


class TestWrappersNeverRaise:
    # Always stub the repo-level ledger writer so the real
    # _learning/findings.jsonl is never polluted by a test run.
    @pytest.fixture(autouse=True)
    def _no_real_ledger(self, monkeypatch):
        monkeypatch.setattr(ac, "_emit_findings", lambda *a, **k: None)

    def test_run_0b_precheck_missing_files_skips_cleanly(self, book):
        # No refined artifact → advisory wrapper SKIPS (no spurious U0B-EMPTY),
        # never raises. 0b's own non-empty assertion is the authority on absence.
        out = ac.run_0b_precheck(book, log=lambda *a: None)
        assert out.proceeded is True
        assert out.findings == []

    def test_run_0b_precheck_flags_real_drift(self, book):
        text_dir = book / "_system" / "source" / "text"
        text_dir.mkdir(parents=True)
        (text_dir / "raw-extract.md").write_text("word " * 1000, encoding="utf-8")
        (text_dir / "refined-english.md").write_text("tiny output", encoding="utf-8")
        out = ac.run_0b_precheck(book, log=lambda *a: None)
        assert "U0B-LENGTH-DRIFT" in {f.check_id for f in out.findings}

    def test_run_0e_chapter_precheck_emits_and_returns(self, book):
        out = ac.run_0e_chapter_precheck(
            book, "ch01", "a b c d e f", "a b", file="x", log=lambda *a: None)
        assert out.proceeded is True
        assert "U0E-SHRANK" in {f.check_id for f in out.findings}
        brief = book / "_system" / "upstream-precheck-report.md"
        assert brief.exists()


# ─── Phase B: discriminator helpers (pure / no LLM) ──────────────────────────


class TestSampleText:
    def test_short_returns_unchanged(self):
        text = "word " * 100
        assert ac._sample_text(text, 200) == text

    def test_long_returns_truncated(self):
        text = "word " * 2000
        sampled = ac._sample_text(text, 100)
        assert "…" in sampled or "[…]" in sampled
        assert len(sampled.split()) < 2000


class TestParseDiscriminatorFindings:
    def test_clean_verdict_returns_empty(self):
        assert ac._parse_discriminator_findings("VERDICT: CLEAN") == []

    def test_finding_parsed(self):
        out = 'FINDING: U0B-MEANING-DRIFT | changed a claim | raw: "x" → refined: "y"'
        findings = ac._parse_discriminator_findings(out)
        assert len(findings) == 1
        assert findings[0].check_id == "U0B-MEANING-DRIFT"
        assert findings[0].severity == "P1"

    def test_hallucinated_addition_is_p0(self):
        out = 'FINDING: U0B-HALLUCINATED-ADDITION | invented | raw: "" → refined: "xyz"'
        findings = ac._parse_discriminator_findings(out)
        assert findings[0].severity == "P0"

    def test_unknown_check_id_maps_to_p1(self):
        out = "FINDING: U0B-UNKNOWN-THING | some issue | raw: a → refined: b"
        findings = ac._parse_discriminator_findings(out)
        assert findings[0].severity == "P1"

    def test_malformed_line_ignored(self):
        out = "FINDING: no-pipe-here just text"
        assert ac._parse_discriminator_findings(out) == []

    def test_noisy_output_only_extracts_finding_lines(self):
        out = (
            "Here is my analysis:\n"
            "The text looks mostly good.\n"
            'FINDING: U0B-DROPPED-TEACHING | dropped ayah | raw: "verse" → refined: ""\n'
            "Overall, acceptable work.\n"
        )
        findings = ac._parse_discriminator_findings(out)
        assert len(findings) == 1
        assert findings[0].check_id == "U0B-DROPPED-TEACHING"


class TestBuild0bDiscriminatorPrompt:
    def test_prompt_contains_check_ids(self):
        p = ac.build_0b_discriminator_prompt("test-book", "raw sample", "refined sample")
        for cid in ["U0B-MEANING-DRIFT", "U0B-DROPPED-TEACHING",
                    "U0B-HALLUCINATED-ADDITION", "U0B-REGISTER-SHIFT"]:
            assert cid in p

    def test_prompt_contains_samples(self):
        p = ac.build_0b_discriminator_prompt("test-book", "MY_RAW_SAMPLE", "MY_REFINED_SAMPLE")
        assert "MY_RAW_SAMPLE" in p
        assert "MY_REFINED_SAMPLE" in p

    def test_prompt_includes_slug(self):
        p = ac.build_0b_discriminator_prompt("slug-xyz", "r", "f")
        assert "slug-xyz" in p


# ─── Phase C: 0e faithfulness discriminator helpers ──────────────────────────


class TestParseDiscriminatorFindingsWith0eSeverityMap:
    def test_hallucinated_citation_is_p0(self):
        out = 'FINDING: U0E-HALLUCINATED-CITATION | invented hadith | original: "" → enriched: "xyz"'
        findings = ac._parse_discriminator_findings(
            out, severity_map=ac._DISCRIMINATOR_0E_SEVERITY)
        assert findings[0].severity == "P0"

    def test_source_altered_is_p1(self):
        out = 'FINDING: U0E-SOURCE-ALTERED | meaning changed | original: "x" → enriched: "y"'
        findings = ac._parse_discriminator_findings(
            out, severity_map=ac._DISCRIMINATOR_0E_SEVERITY)
        assert findings[0].severity == "P1"

    def test_clean_verdict_still_returns_empty(self):
        assert ac._parse_discriminator_findings(
            "VERDICT: CLEAN", severity_map=ac._DISCRIMINATOR_0E_SEVERITY) == []


class TestBuild0eDiscriminatorPrompt:
    def test_prompt_contains_0e_check_ids(self):
        p = ac.build_0e_discriminator_prompt("test", "ch01", "before text", "after text")
        for cid in ["U0E-HALLUCINATED-CITATION", "U0E-SOURCE-ALTERED", "U0E-DOCTRINE-DRIFT"]:
            assert cid in p

    def test_prompt_contains_samples(self):
        p = ac.build_0e_discriminator_prompt("slug", "ch01", "BEFORE_TEXT", "AFTER_TEXT")
        assert "BEFORE_TEXT" in p and "AFTER_TEXT" in p


class TestRun0eChapterPrecheckWithDiscriminator:
    @pytest.fixture(autouse=True)
    def _no_real_ledger(self, monkeypatch):
        monkeypatch.setattr(ac, "_emit_findings", lambda *a, **k: None)

    def test_discriminator_fires_when_cap_set(self, book, monkeypatch):
        import types
        sp_mock = types.SimpleNamespace(
            _series_numeric=lambda bd, name, default=0.0: 1.5,
            _book_cost_so_far=lambda bd: 0.0,
        )
        monkeypatch.setitem(sys.modules, "phases.series_plan", sp_mock)

        disc_calls = {"n": 0}
        monkeypatch.setattr(ac, "discriminate_0e_faithfulness",
                            lambda bd, stem, before, after, log=print: (
                                disc_calls.__setitem__("n", disc_calls["n"] + 1) or []
                            ))

        out = ac.run_0e_chapter_precheck(
            book, "ch01", "a b c d", "a b c d e f", log=lambda *a: None)
        assert out.proceeded is True
        assert disc_calls["n"] == 1

    def test_discriminator_off_when_cap_zero(self, book, monkeypatch):
        import types
        sp_mock = types.SimpleNamespace(
            _series_numeric=lambda bd, name, default=0.0: 0.0,
            _book_cost_so_far=lambda bd: 0.0,
        )
        monkeypatch.setitem(sys.modules, "phases.series_plan", sp_mock)

        disc_calls = {"n": 0}
        monkeypatch.setattr(ac, "discriminate_0e_faithfulness",
                            lambda bd, stem, before, after, log=print: (
                                disc_calls.__setitem__("n", disc_calls["n"] + 1) or []
                            ))

        out = ac.run_0e_chapter_precheck(
            book, "ch01", "a b c d", "a b c d e f", log=lambda *a: None)
        assert out.proceeded is True
        assert disc_calls["n"] == 0


class TestRun0bPrecheckWithDiscriminator:
    """run_0b_precheck when phase_0b_discriminator_cap_usd > 0."""

    @pytest.fixture(autouse=True)
    def _no_real_ledger(self, monkeypatch):
        monkeypatch.setattr(ac, "_emit_findings", lambda *a, **k: None)

    def test_discriminator_fires_when_cap_set(self, book, monkeypatch):
        # Stub series-plan cap and cost function via monkeypatching the
        # import inside run_0b_precheck.
        import types
        sp_mock = types.SimpleNamespace(
            _series_numeric=lambda bd, name, default=0.0: 2.0,
            _book_cost_so_far=lambda bd: 0.0,
        )
        monkeypatch.setitem(sys.modules, "phases.series_plan", sp_mock)

        disc_calls = {"n": 0}
        # Stub discriminate_0b_fidelity so no real LLM call happens.
        monkeypatch.setattr(ac, "discriminate_0b_fidelity",
                            lambda bd, raw, refined, log=print: (
                                disc_calls.__setitem__("n", disc_calls["n"] + 1) or []
                            ))

        # Create the required files.
        text_dir = book / "_system" / "source" / "text"
        text_dir.mkdir(parents=True)
        (text_dir / "raw-extract.md").write_text("word " * 100, encoding="utf-8")
        (text_dir / "refined-english.md").write_text("word " * 90, encoding="utf-8")

        out = ac.run_0b_precheck(book, log=lambda *a: None)
        assert out.proceeded is True
        assert disc_calls["n"] == 1

    def test_discriminator_off_when_cap_zero(self, book, monkeypatch):
        import types
        sp_mock = types.SimpleNamespace(
            _series_numeric=lambda bd, name, default=0.0: 0.0,
            _book_cost_so_far=lambda bd: 0.0,
        )
        monkeypatch.setitem(sys.modules, "phases.series_plan", sp_mock)

        disc_calls = {"n": 0}
        monkeypatch.setattr(ac, "discriminate_0b_fidelity",
                            lambda bd, raw, refined, log=print: (
                                disc_calls.__setitem__("n", disc_calls["n"] + 1) or []
                            ))

        text_dir = book / "_system" / "source" / "text"
        text_dir.mkdir(parents=True)
        (text_dir / "raw-extract.md").write_text("word " * 100, encoding="utf-8")
        (text_dir / "refined-english.md").write_text("word " * 90, encoding="utf-8")

        out = ac.run_0b_precheck(book, log=lambda *a: None)
        assert out.proceeded is True
        assert disc_calls["n"] == 0  # discriminator must NOT fire when cap=0


# ─── Phase D: query_upstream_findings ────────────────────────────────────────


class TestQueryUpstreamFindings:
    def test_empty_ledger_returns_empty(self, tmp_path):
        result = ac.query_upstream_findings(repo_root=tmp_path, min_occurrences=1)
        assert result == {}

    def test_missing_ledger_returns_empty(self, tmp_path):
        # No _learning/ directory at all.
        result = ac.query_upstream_findings(repo_root=tmp_path / "nowhere")
        assert result == {}

    def test_groups_by_check_id_above_threshold(self, tmp_path):
        import json
        learning = tmp_path / "_learning"
        learning.mkdir()
        ledger = learning / "findings.jsonl"
        for i in range(4):
            rec = {"source": "precheck-0b", "check_id": "U0B-LENGTH-DRIFT",
                   "severity": "P1", "signature": "U0B-LENGTH-DRIFT",
                   "book": f"book-{i}", "ts": "2026-01-01T00:00:00Z"}
            ledger.write_text(
                ledger.read_text() if ledger.exists() else "" +
                json.dumps(rec) + "\n", encoding="utf-8"
            )
        # Simpler: write all at once
        ledger.write_text(
            "\n".join(json.dumps(
                {"source": "precheck-0b", "check_id": "U0B-LENGTH-DRIFT",
                 "severity": "P1", "signature": "U0B-LENGTH-DRIFT",
                 "book": f"book-{i}", "ts": "2026-01-01T00:00:00Z"}
            ) for i in range(4)) + "\n",
            encoding="utf-8"
        )
        result = ac.query_upstream_findings(repo_root=tmp_path, min_occurrences=3)
        assert "U0B-LENGTH-DRIFT" in result
        assert len(result["U0B-LENGTH-DRIFT"]) == 4

    def test_below_threshold_excluded(self, tmp_path):
        import json
        learning = tmp_path / "_learning"
        learning.mkdir()
        ledger = learning / "findings.jsonl"
        ledger.write_text(
            json.dumps({"source": "precheck-0b", "check_id": "U0B-EMPTY",
                        "severity": "P0", "book": "x", "ts": "2026-01-01T00:00:00Z"})
            + "\n",
            encoding="utf-8",
        )
        result = ac.query_upstream_findings(repo_root=tmp_path, min_occurrences=3)
        assert result == {}  # only 1 occurrence — below threshold of 3

    def test_non_upstream_sources_excluded(self, tmp_path):
        import json
        learning = tmp_path / "_learning"
        learning.mkdir()
        ledger = learning / "findings.jsonl"
        ledger.write_text(
            "\n".join(json.dumps(
                {"source": "podcast-challenger", "check_id": "A1",
                 "book": f"b{i}", "ts": "2026-01-01T00:00:00Z"}
            ) for i in range(10)) + "\n",
            encoding="utf-8",
        )
        result = ac.query_upstream_findings(repo_root=tmp_path, min_occurrences=1)
        assert result == {}  # podcast-challenger is not an upstream source


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
