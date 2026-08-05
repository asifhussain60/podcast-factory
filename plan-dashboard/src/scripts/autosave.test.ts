/**
 * autosave.test.ts — the no-op guard (RCA-002 AI-1).
 *
 * The controller is wired to editor EVENTS, not to content change, so the
 * question these tests answer is the one the incident turned on: given a
 * markDirty() that fires, does anything reach `save()` when the content is
 * the same as it was loaded?
 *
 * Timers are real but the debounce is set to 0 and awaited via a macrotask
 * turn, so the tests stay deterministic without a fake-timer dependency.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { createAutosave, type AutosaveState } from "./autosave.ts";

// createAutosave reaches for window.clearTimeout/setTimeout.
const g = globalThis as unknown as {
  window?: { setTimeout: typeof setTimeout; clearTimeout: typeof clearTimeout };
};
g.window ??= { setTimeout, clearTimeout };

/** One macrotask turn past a 0ms debounce. */
const tick = (): Promise<void> => new Promise((r) => setTimeout(r, 5));

interface Harness {
  saves: string[];
  states: [AutosaveState, string][];
  content: { value: string };
}

function harness(opts: { fingerprint?: boolean } = {}) {
  const content = { value: "original" };
  const saves: string[] = [];
  const states: [AutosaveState, string][] = [];
  const ctrl = createAutosave({
    debounceMs: 0,
    save: async () => {
      saves.push(content.value);
      return { ok: true };
    },
    onStateChange: (s, m) => void states.push([s, m]),
    fingerprint: opts.fingerprint === false ? undefined : () => content.value,
  });
  return { ctrl, saves, states, content } as Harness & { ctrl: typeof ctrl };
}

test("a markDirty with no content change never calls save", async () => {
  const h = harness();
  h.ctrl.markDirty(); // stray keystroke / accidental drag that changed nothing
  await tick();
  assert.deepEqual(h.saves, [], "an unchanged document must not be written");
});

test("a real edit still saves", async () => {
  const h = harness();
  h.content.value = "edited";
  h.ctrl.markDirty();
  await tick();
  assert.deepEqual(h.saves, ["edited"]);
});

test("the baseline advances, so an edit saves once and then goes quiet", async () => {
  const h = harness();
  h.content.value = "edited";
  h.ctrl.markDirty();
  await tick();
  h.ctrl.markDirty(); // another event, same content
  await tick();
  assert.deepEqual(h.saves, ["edited"], "the second event must be a no-op");
});

test("an edit reverted back to the original stops saving again", async () => {
  const h = harness();
  h.content.value = "edited";
  h.ctrl.markDirty();
  await tick();
  h.content.value = "original"; // undo
  h.ctrl.markDirty();
  await tick();
  h.content.value = "original";
  h.ctrl.markDirty();
  await tick();
  assert.deepEqual(h.saves, ["edited", "original"]);
});

test("a skipped save does not wipe an earlier Saved message off the pill", async () => {
  const h = harness();
  h.content.value = "edited";
  h.ctrl.markDirty();
  await tick();
  const savedMsg = h.states.filter(([s]) => s === "saved").at(-1);
  assert.ok(savedMsg, "the real save should have reported saved");

  h.states.length = 0;
  h.ctrl.markDirty(); // no-op
  await tick();
  const last = h.states.at(-1);
  assert.deepEqual(
    last,
    savedMsg,
    "a no-op must settle back to the previous Saved state, not invent a new one",
  );
  assert.ok(
    !h.states.some(([s]) => s === "saving"),
    "a no-op must never enter the saving state",
  );
});

test("flush on an unchanged document writes nothing and still resolves true", async () => {
  const h = harness();
  h.ctrl.markDirty();
  assert.equal(await h.ctrl.flush(), true);
  assert.deepEqual(h.saves, []);
});

test("flush on a changed document writes", async () => {
  const h = harness();
  h.content.value = "edited";
  h.ctrl.markDirty();
  assert.equal(await h.ctrl.flush(), true);
  assert.deepEqual(h.saves, ["edited"]);
});

test("without a fingerprint the controller behaves exactly as before", async () => {
  const h = harness({ fingerprint: false });
  h.ctrl.markDirty(); // no content change, but no guard either
  await tick();
  assert.deepEqual(
    h.saves,
    ["original"],
    "the unguarded path must stay available for callers with no cheap fingerprint",
  );
});

test("a throwing fingerprint falls back to saving rather than blocking it", async () => {
  const saves: string[] = [];
  const ctrl = createAutosave({
    debounceMs: 0,
    save: async () => {
      saves.push("x");
      return { ok: true };
    },
    onStateChange: () => {},
    fingerprint: () => {
      throw new Error("editor torn down");
    },
  });
  ctrl.markDirty();
  await tick();
  assert.deepEqual(
    saves,
    ["x"],
    "a broken guard must not silently stop saving",
  );
});

test("a failed save leaves the baseline behind so the retry still writes", async () => {
  const content = { value: "original" };
  const saves: string[] = [];
  let fail = true;
  const ctrl = createAutosave({
    debounceMs: 0,
    save: async () => {
      if (fail) return { ok: false, error: "network" };
      saves.push(content.value);
      return { ok: true };
    },
    onStateChange: () => {},
    fingerprint: () => content.value,
  });
  content.value = "edited";
  ctrl.markDirty();
  await tick();
  assert.deepEqual(saves, [], "the failing save wrote nothing");

  fail = false;
  assert.equal(await ctrl.flush(), true);
  assert.deepEqual(
    saves,
    ["edited"],
    "the retry must not be swallowed by a baseline advanced on a failed save",
  );
});
