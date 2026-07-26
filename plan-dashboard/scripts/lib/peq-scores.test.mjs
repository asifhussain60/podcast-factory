/**
 * peq-scores.test.mjs — the JS half of the peq-scores <-> _quality mirror pair.
 *
 * The Python half is `tests/test_peq_mirror.py`, reading the SAME fixture file.
 *
 * This is a TRIPLE, not a pair: _rules.py owns the interest weight and patterns,
 * _quality.py imports them, and this file re-types them as literals with no link to
 * the authority. The Python harness asserts the constants against _rules.py; this one
 * asserts the same fixture values against what peq-scores.ts actually exports and
 * computes.
 *
 * Two real divergences were found and fixed at the root on 2026-07-26 — half-up vs
 * half-to-even rounding, and ASCII vs Unicode word boundaries. See the fixture's
 * `_comment` block for the honest scope of each.
 *
 * Run: cd plan-dashboard && npm test
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  THRESHOLD_PASS,
  THRESHOLD_WARN,
  roundHalfEven,
  __testHooks,
} from "../../src/lib/peq-scores.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIX = JSON.parse(
  readFileSync(join(HERE, "peq-scores.fixtures.json"), "utf8"),
);

test("thresholds match the shared fixtures", () => {
  assert.equal(THRESHOLD_PASS, FIX.constants.threshold_pass);
  assert.equal(THRESHOLD_WARN, FIX.constants.threshold_warn);
});

test("weights match the shared fixtures and sum to 1", () => {
  const w = FIX.constants.weights;
  const { weights } = __testHooks;
  assert.equal(weights.fidelity, w.fidelity);
  assert.equal(weights.voice, w.voice);
  assert.equal(weights.structure, w.structure);
  assert.equal(weights.enrichment, w.enrichment);
  assert.equal(weights.interest, w.interest);
  const sum =
    weights.fidelity +
    weights.voice +
    weights.structure +
    weights.enrichment +
    weights.interest;
  assert.ok(Math.abs(sum - 1) < 1e-9, `weights must sum to 1, got ${sum}`);
});

test("the voice-scorer flag matches the shared fixtures", () => {
  // Hand-mirrored boolean. If Python flips and this does not, the dashboard shows a
  // score the pipeline never awarded.
  assert.equal(__testHooks.voiceScorerReady, FIX.constants.voice_scorer_ready);
});

test("interest pattern counts match the shared fixtures", () => {
  // Catches a pattern added to _rules.py but never re-typed here.
  const expected = FIX.constants.interest_pattern_counts;
  for (const [group, count] of Object.entries(expected)) {
    assert.equal(
      __testHooks.patternGroups[group].length,
      count,
      `${group} pattern count`,
    );
  }
});

test("hook patterns stay unanchored", () => {
  // 0 of 8 hook patterns in _rules.py use a word boundary. Adding one here would
  // silently narrow the axis on the display side — which is exactly the slip that
  // happened while fixing the boundary divergence, so it is pinned.
  if (!FIX.constants.hook_patterns_are_unanchored) return;
  for (const re of __testHooks.patternGroups.hook) {
    assert.ok(
      !re.source.includes("(?<![\\p{L}"),
      `hook pattern gained a word boundary: ${re.source}`,
    );
  }
});

// ── rounding ──────────────────────────────────────────────────────────────────
test("roundHalfEven matches the shared fixtures", () => {
  for (const c of FIX.rounding_cases) {
    assert.equal(
      roundHalfEven(c.value, c.digits),
      c.out,
      `${c.why} — roundHalfEven(${c.value}, ${c.digits})`,
    );
  }
});

// ── word boundaries ───────────────────────────────────────────────────────────
test("boundary behaviour matches the shared fixtures", () => {
  for (const c of FIX.boundary_cases) {
    const patterns = __testHooks.patternGroups[c.pattern_group];
    const hit = patterns.some((p) => p.test(c.text));
    assert.equal(
      hit,
      c.expect_match,
      `${c.why} — ${JSON.stringify(c.text)} in ${c.pattern_group}`,
    );
  }
});

// ── interest axis ─────────────────────────────────────────────────────────────
test("the interest score matches the shared fixtures", () => {
  for (const c of FIX.interest_cases) {
    assert.equal(__testHooks.interestScore(c.text), c.expect_interest, c.why);
  }
});

// ── aggregation + verdict banding ─────────────────────────────────────────────
test("aggregation and verdict banding match the shared fixtures", () => {
  for (const c of FIX.aggregation_cases) {
    assert.equal(
      c.voice_available,
      false,
      "only the redistribution branch is fixtured today",
    );
    const { total, verdict } = __testHooks.aggregate(c.axes, c.voice_available);
    assert.equal(total, c.expect_total, `${c.why} — total`);
    assert.equal(verdict, c.expect_verdict, `${c.why} — verdict`);
  }
});
