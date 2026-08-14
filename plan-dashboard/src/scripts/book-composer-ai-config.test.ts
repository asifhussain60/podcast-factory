/**
 * book-composer-ai-config.test.ts — regression guard for the 2026-08-14
 * Refine panel consolidation: four rewrite buttons became one group, the
 * duplicate "Explain" button was dropped in favor of the React term-curation
 * version, Diacritics stays the only Arabic-gated action.
 */
import { test, describe } from "node:test";
import assert from "node:assert/strict";

import {
  REWRITE_MODES,
  ETYMOLOGY_ACTION,
  DIACRITICS_ACTION,
} from "./book-composer-ai-config";

describe("REWRITE_MODES — the merged Rewrite/Expand/Condense/Simplify group", () => {
  test("still covers all four original modes, none dropped", () => {
    const modes = REWRITE_MODES.map((m) => m.mode).sort();
    assert.deepEqual(modes, ["clarify", "expand", "simplify", "tighten"]);
  });

  test("every entry has a unique kind and a unique mode", () => {
    const kinds = REWRITE_MODES.map((m) => m.kind);
    const modes = REWRITE_MODES.map((m) => m.mode);
    assert.equal(new Set(kinds).size, kinds.length, "duplicate kind");
    assert.equal(new Set(modes).size, modes.length, "duplicate mode");
  });

  test("every entry has a non-empty label short enough for a segmented row", () => {
    for (const m of REWRITE_MODES) {
      assert.ok(m.label.length > 0, `${m.kind} has no label`);
      assert.ok(
        m.label.length <= 12,
        `${m.kind}'s label "${m.label}" is too long for a segmented control`,
      );
    }
  });

  test("no entry carries an explain/etymology/diacritics flag — those are separate actions", () => {
    for (const m of REWRITE_MODES) {
      assert.ok(!("explain" in m), `${m.kind} should not have an explain flag`);
      assert.ok(
        !("etymology" in m),
        `${m.kind} should not have an etymology flag`,
      );
      assert.ok(
        !("diacritics" in m),
        `${m.kind} should not have a diacritics flag`,
      );
    }
  });
});

describe("the duplicate Explain button is gone", () => {
  test('no exported action declares kind "explain"', () => {
    const allKinds = [
      ...REWRITE_MODES.map((m) => m.kind),
      ETYMOLOGY_ACTION.kind,
      DIACRITICS_ACTION.kind,
    ];
    assert.ok(
      !allKinds.includes("explain"),
      'an "explain" action reappeared in the vanilla config — Explain now lives ' +
        "only in ComposeAiTools.tsx (useTermCuration's proposeExplain)",
    );
  });
});

describe("ETYMOLOGY_ACTION and DIACRITICS_ACTION stay separate, single-purpose actions", () => {
  test("Etymology is not Arabic-gated and is not the diacritics action", () => {
    assert.equal(ETYMOLOGY_ACTION.etymology, true);
    assert.ok(!ETYMOLOGY_ACTION.diacritics);
    assert.ok(!ETYMOLOGY_ACTION.arabicOnly);
  });

  test("Diacritics is the only arabicOnly-gated action across the whole config", () => {
    assert.equal(DIACRITICS_ACTION.diacritics, true);
    assert.equal(DIACRITICS_ACTION.arabicOnly, true);
    assert.ok(!DIACRITICS_ACTION.etymology);
    for (const m of REWRITE_MODES) {
      assert.ok(
        !("arabicOnly" in m),
        `${m.kind} should not be Arabic-gated — only Diacritics is`,
      );
    }
  });

  test("Etymology and Diacritics have distinct kinds", () => {
    assert.notEqual(ETYMOLOGY_ACTION.kind, DIACRITICS_ACTION.kind);
  });
});
