/**
 * view-state.test.ts — the guarantees the module exists to make.
 *
 * The interesting cases are the hostile ones: storage that throws, a stored
 * value that no longer names anything real, and two books whose selections
 * must never be able to reach each other.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  defineViewState,
  oneOf,
  existing,
  __resetViewStateRegistry,
  type ViewStateStorage,
} from "./view-state.ts";

function memoryStore(): ViewStateStorage & { map: Map<string, string> } {
  const map = new Map<string, string>();
  return {
    map,
    get: (k) => map.get(k) ?? null,
    set: (k, v) => void map.set(k, v),
    remove: (k) => void map.delete(k),
  };
}

const throwingStore: ViewStateStorage = {
  get() {
    throw new Error("private mode");
  },
  set() {
    throw new Error("private mode");
  },
  remove() {
    throw new Error("private mode");
  },
};

test("a value round-trips", () => {
  __resetViewStateRegistry();
  const store = memoryStore();
  const lane = defineViewState(
    { surface: "compose", field: "lane", validate: oneOf(["book", "podcast"]) },
    store,
  );
  lane.write("podcast");
  assert.equal(lane.read(), "podcast");
});

test("scopes keep two books apart", () => {
  __resetViewStateRegistry();
  const store = memoryStore();
  const chapter = defineViewState(
    { surface: "compose", field: "chapter", validate: (r) => r },
    store,
  );
  chapter.write("chapter-one", "book-a");
  chapter.write("chapter-nine", "book-b");
  assert.equal(chapter.read("book-a"), "chapter-one");
  assert.equal(chapter.read("book-b"), "chapter-nine");
  assert.equal(chapter.read("book-c"), null, "an unvisited book has no state");
});

test("an unscoped key is not the same key as a scoped one", () => {
  __resetViewStateRegistry();
  const store = memoryStore();
  const v = defineViewState(
    { surface: "s", field: "f", validate: (r) => r },
    store,
  );
  v.write("global");
  v.write("scoped", "slug");
  assert.equal(v.read(), "global");
  assert.equal(v.read("slug"), "scoped");
});

test("a stored value outside the allow-list is discarded", () => {
  __resetViewStateRegistry();
  const store = memoryStore();
  const tab = defineViewState(
    { surface: "pre-upload", field: "tab", validate: oneOf(["a", "b"]) },
    store,
  );
  store.map.set(tab.keyFor(), "a-tab-that-was-removed");
  assert.equal(tab.read(), null, "the page must fall back to its default");
});

test("a remembered item that no longer exists is discarded", () => {
  __resetViewStateRegistry();
  const store = memoryStore();
  const live = new Set(["ch-1", "ch-2"]);
  const chapter = defineViewState(
    {
      surface: "compose",
      field: "chapter",
      validate: existing((r) => live.has(r)),
    },
    store,
  );
  chapter.write("ch-2", "slug");
  assert.equal(chapter.read("slug"), "ch-2");

  live.delete("ch-2"); // the chapter was renamed by a re-compose
  assert.equal(
    chapter.read("slug"),
    null,
    "a deleted chapter must not be restored",
  );
});

test("a validator that throws is a rejection, not a crash", () => {
  __resetViewStateRegistry();
  const store = memoryStore();
  const v = defineViewState(
    {
      surface: "s",
      field: "f",
      validate: () => {
        throw new Error("malformed");
      },
    },
    store,
  );
  store.map.set(v.keyFor(), "junk");
  assert.equal(v.read(), null);
});

test("storage that throws degrades to no memory at all", () => {
  __resetViewStateRegistry();
  const v = defineViewState(
    { surface: "s", field: "f", validate: (r) => r },
    throwingStore,
  );
  // The point is that none of these escape.
  assert.doesNotThrow(() => v.write("x"));
  assert.doesNotThrow(() => v.clear());
  assert.equal(v.read(), null);
});

test("the real guarded storage swallows a throwing localStorage", () => {
  __resetViewStateRegistry();
  const g = globalThis as unknown as { localStorage?: unknown };
  const original = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    get() {
      throw new Error("blocked by the browser");
    },
  });
  try {
    const v = defineViewState({
      surface: "s",
      field: "guarded",
      validate: (r) => r,
    });
    assert.doesNotThrow(() => v.write("x"));
    assert.equal(v.read(), null);
  } finally {
    if (original) Object.defineProperty(globalThis, "localStorage", original);
    else delete g.localStorage;
  }
});

test("clear removes only its own scope", () => {
  __resetViewStateRegistry();
  const store = memoryStore();
  const v = defineViewState(
    { surface: "s", field: "f", validate: (r) => r },
    store,
  );
  v.write("a", "one");
  v.write("b", "two");
  v.clear("one");
  assert.equal(v.read("one"), null);
  assert.equal(v.read("two"), "b");
});

test("defining the same surface+field twice throws", () => {
  __resetViewStateRegistry();
  const store = memoryStore();
  defineViewState({ surface: "dup", field: "f", validate: (r) => r }, store);
  assert.throws(
    () =>
      defineViewState(
        { surface: "dup", field: "f", validate: (r) => r },
        store,
      ),
    /already defined/,
    "a silent key collision is exactly what the registry exists to prevent",
  );
});

test("a custom serializer round-trips a non-string", () => {
  __resetViewStateRegistry();
  const store = memoryStore();
  const scroll = defineViewState<number>(
    {
      surface: "live",
      field: "scroll",
      serialize: (n) => String(n),
      validate: (r) => {
        const n = Number(r);
        return Number.isFinite(n) && n >= 0 ? n : null;
      },
    },
    store,
  );
  scroll.write(1420, "slug");
  assert.equal(scroll.read("slug"), 1420);

  store.map.set(scroll.keyFor("slug"), "not-a-number");
  assert.equal(scroll.read("slug"), null);
});
