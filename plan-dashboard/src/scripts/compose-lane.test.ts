/**
 * compose-lane.test.ts — the Book Composer's lane switch, under the real editor.
 *
 * The danger being tested is narrow and specific: the podcast lane shows a
 * DIFFERENT English text of the same Arabic source (independently translated,
 * differently segmented, carrying narration framing and citations the book
 * deliberately omits). If a flip to that lane left an editable surface or a
 * live autosave controller behind the toggle, one debounced keystroke would
 * PUT podcast prose to /api/studio/book-md — which writes book.md AND
 * _system/composer-edits.json, after which the pipeline never regenerates that
 * chapter. That is RCA-001 with prose from the wrong lane.
 *
 * So these tests wire the REAL primitives the Composer uses — mountChapterEditor
 * (TipTap) and createAutosave — to a recording transport, and drive the REAL
 * createComposeLane. Only the network is stubbed. `leave()` here performs the
 * same two steps book-composer.ts's leaveEditMode performs (flush, then
 * destroy), and a source-level test below pins that the production call site
 * still passes that path rather than a no-op.
 */
import { test, type TestContext } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { Window } from "happy-dom";

// TipTap parses its seed HTML through the global DOMParser, and the lane
// controller touches sessionStorage; give node:test a DOM before either loads.
const win = new Window({ url: "http://localhost/" });
for (const key of [
  "window",
  "document",
  "DOMParser",
  "HTMLElement",
  "Element",
  "Node",
  "Event",
  "CustomEvent",
  "MutationObserver",
  "sessionStorage",
  "localStorage",
  "getComputedStyle",
] as const) {
  try {
    (globalThis as Record<string, unknown>)[key] = (
      win as unknown as Record<string, unknown>
    )[key];
  } catch {
    /* already defined by the host and equivalent */
  }
}

/**
 * happy-dom's element classes are structurally distinct from lib.dom's, so a
 * node created here is not assignable to a parameter typed `HTMLElement` even
 * though it behaves identically at runtime. One cast, in one place, rather than
 * one per call site — and the production types stay strict.
 */
function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
): HTMLElementTagNameMap[K] {
  const node = win.document.createElement(tag);
  win.document.body.append(node);
  return node as unknown as HTMLElementTagNameMap[K];
}

import { createAutosave, type AutosaveController } from "./autosave";
import { mountChapterEditor, type ChapterEditor } from "./book-md-editor";
import {
  assertReadOnly,
  createComposeLane,
  demoteHeadings,
  pendingLane,
  type PodcastChapterMeta,
} from "./compose-lane";
import { renderEditSeed, renderSourceMarkdown } from "../lib/reader/markdown";
import {
  composeLane as composeLaneState,
  composePodcastFile,
} from "./compose-view-state";

const SLUG = "test-book";

/** The book chapter as book.md carries it — the articulated reading edition.
 *  One line per paragraph, which is the shape the Composer's serializer writes;
 *  a soft-wrapped fixture would fold on the round trip and test nothing. */
const BOOK_CHAPTER_MD = [
  "As for the doctrines of the righteous: it has reached us that a certain man among the people of Persia was afflicted by the calamity of ignorance.",
  "",
  "**The boy** follows him, is refused, and is admitted only on conditions.",
].join("\n");

/** The SAME source passage as chapters/*.txt carries it — a different
 *  translation, with the narration framing and a cited reference the book
 *  deliberately does not carry. */
const PODCAST_CHAPTER_TXT = [
  "# Three Thanks and the Persian Awakening",
  "",
  "*Three Thanks and the Persian Awakening, the opening of a tenth-century dialogue.*",
  "",
  "## Where the dialogue opens",
  "",
  "It has reached us that a number of the truly faithful said to one of their scholars:",
  'the Quran sets the principle plainly: *"If you are grateful, I will surely increase',
  'you in favor"* (Quran 14:7, Sahih International rendering).',
].join("\n");

const CHAPTERS: PodcastChapterMeta[] = [
  {
    file: "ch01a-three-thanks.txt",
    title: "Three Thanks and the Persian Awakening",
    ordinal: "01a",
  },
  {
    file: "ch02b-the-test-of-speech.txt",
    title: "The Test of Speech",
    ordinal: "02b",
  },
];

interface Put {
  path: string;
  body: unknown;
}

/**
 * Force-destroy any editor a test left mounted, registered per test.
 *
 * Needed for the FALSIFICATION path, not the green one. A mutant that skips the
 * lane's `leave()` hook leaves live TipTap editors behind; their observers keep
 * the event loop alive, node:test's watchdog kills the whole FILE, and the
 * per-test results never print — the gate still fails, but as an opaque 45s
 * timeout instead of the named assertion that caught it. An opaque gate is one
 * nobody can act on, so each test cleans up after itself even when the code
 * under test failed to.
 */
function disposeAfter(t: TestContext, destroy: () => void): void {
  t.after(() => {
    try {
      destroy();
    } catch {
      /* already destroyed by the lane's own teardown — the normal case */
    }
  });
}

/**
 * A book-lane editing session built from the production modules: a real TipTap
 * editor seeded exactly as the Composer seeds it, and a real debounced autosave
 * whose save() records the PUT instead of issuing it.
 *
 * `leave()` is the same two-step book-composer.ts performs in leaveEditMode:
 * flush the pending save, then destroy the editor.
 */
function session(
  t: TestContext,
  puts: Put[],
  opts: { failSave?: boolean } = {},
) {
  const host = el("div");
  const mount = () => {
    const ed = mountChapterEditor(host, renderEditSeed(BOOK_CHAPTER_MD));
    disposeAfter(t, () => ed.destroy());
    return ed;
  };
  let editor: ChapterEditor | null = mount();
  const autosave: AutosaveController = createAutosave({
    debounceMs: 5_000, // long, so "flip inside the debounce window" is deliberate
    onStateChange: () => {},
    save: async () => {
      if (opts.failSave) return { ok: false, error: "network down" };
      puts.push({
        path: "/api/studio/book-md",
        body: {
          slug: SLUG,
          chapterKey: "the persian who was dead and revived",
          markdown: editor!.toMarkdown(),
        },
      });
      return { ok: true };
    },
  });
  editor.editor.on("update", () => autosave.markDirty());

  let entered = 0;
  return {
    host,
    get editor() {
      return editor;
    },
    autosave,
    enteredCount: () => entered,
    async leave(): Promise<boolean> {
      const saved = await autosave.flush();
      if (!saved) return false; // stands in for the "Keep editing" decline
      editor?.destroy();
      editor = null;
      host.replaceChildren();
      return true;
    },
    enter(): void {
      entered += 1;
      editor = mount();
      editor.editor.on("update", () => autosave.markDirty());
    },
  };
}

/** The lane DOM compose.astro server-renders, built the same way here. */
function laneDom() {
  const root = el("div");
  root.className = "composer";
  const pane = el("section");
  pane.hidden = true;
  const body = el("div");
  const statusEl = el("p");
  const select = el("select");
  for (const c of CHAPTERS) {
    const o = el("option");
    o.value = c.file;
    o.textContent = c.title;
    select.append(o);
  }
  const bookBtn = el("button");
  const podcastBtn = el("button");
  pane.append(select, statusEl, body);
  root.append(bookBtn, podcastBtn, pane);
  return { root, pane, body, statusEl, select, bookBtn, podcastBtn };
}

/** The lane and podcast-file memories are durable (localStorage) rather than
 *  one-shot, so a case that flipped lanes would otherwise hand its restore to
 *  every case after it. Cleared per lane construction; a case that WANTS a
 *  remembered value seeds it between construction and the flip. */
function forgetLaneState(): void {
  composeLaneState.clear(SLUG);
  composePodcastFile.clear(SLUG);
}

function lane(
  dom: ReturnType<typeof laneDom>,
  sess: ReturnType<typeof session>,
  fetched: string[] = [],
) {
  forgetLaneState();
  return createComposeLane({
    slug: SLUG,
    chapters: CHAPTERS,
    root: dom.root,
    pane: dom.pane,
    body: dom.body,
    select: dom.select,
    status: dom.statusEl,
    bookBtn: dom.bookBtn,
    podcastBtn: dom.podcastBtn,
    book: { leave: () => sess.leave(), enter: () => sess.enter() },
    fetchChapterText: async (_slug, file) => {
      fetched.push(file);
      return PODCAST_CHAPTER_TXT;
    },
    render: renderSourceMarkdown,
  });
}

// ── 1. the one that matters: no save can fire from the podcast lane ──────────

test("podcast lane: typing and flushing after the flip fires ZERO book.md PUTs", async (t) => {
  const puts: Put[] = [];
  const sess = session(t, puts);
  const dom = laneDom();
  const l = lane(dom, sess);

  assert.equal(await l.setLane("podcast"), "podcast");
  const putsAfterFlip = puts.length; // the flip's own flush is legitimate

  // Everything a keystroke could reach in this lane, tried in turn.
  sess.autosave.markDirty(); // a stray controller reference
  await sess.autosave.flush(); // the pagehide handler's best-effort save
  dom.body.dispatchEvent(new Event("input", { bubbles: true }));
  dom.body.dispatchEvent(new Event("keyup", { bubbles: true }));
  dom.body.textContent += " typed into the podcast pane";
  await sess.autosave.flush();

  assert.equal(
    puts.length,
    putsAfterFlip,
    `podcast lane produced ${puts.length - putsAfterFlip} book.md PUT(s)`,
  );
  assert.equal(puts.length, 0, "an unedited book chapter had nothing to save");
});

test("podcast lane: no editable surface and no live editor survives the flip", async (t) => {
  const sess = session(t, []);
  const dom = laneDom();
  const l = lane(dom, sess);
  await l.setLane("podcast");

  // Asserted as a boolean, never as the object: a failing
  // `assert.equal(sess.editor, null)` makes node inspect the whole TipTap
  // Editor (schema, view, state, plugins, DOM) to build its diff, which takes
  // ~40s and buries the result. The predicate says the same thing instantly.
  assert.ok(sess.editor === null, "the TipTap editor must be destroyed");
  assert.equal(
    dom.root.querySelector('[contenteditable="true"], .ProseMirror, .cx-prose'),
    null,
    "no editable surface may remain anywhere in the composer",
  );
  assert.equal(dom.body.getAttribute("contenteditable"), "false");
  assert.equal(dom.body.getAttribute("aria-readonly"), "true");
  assert.doesNotThrow(() => assertReadOnly(dom.body));
});

test("assertReadOnly is a real guard, not a comment", () => {
  const editable = el("div");
  editable.setAttribute("contenteditable", "true");
  assert.throws(() => assertReadOnly(editable), /editable/);

  const hostWithEditor = el("div");
  const inner = el("div");
  inner.className = "ProseMirror";
  hostWithEditor.append(inner);
  assert.throws(() => assertReadOnly(hostWithEditor), /editable surface/);
});

// ── 2. the flip flushes FIRST, and a declined leave abandons it ──────────────

test("a pending edit is flushed to book.md BEFORE the pane swaps", async (t) => {
  const puts: Put[] = [];
  const sess = session(t, puts);
  const dom = laneDom();
  const l = lane(dom, sess);

  // Type, then flip while the (5s) debounce is still pending.
  sess.editor!.editor.commands.insertContentAt(
    1,
    "A sentence typed a moment before the flip. ",
  );
  assert.equal(puts.length, 0, "the debounce has not fired yet");

  await l.setLane("podcast");

  assert.equal(puts.length, 1, "exactly one save, carried by the flip's flush");
  assert.equal(puts[0].path, "/api/studio/book-md");
  const md = (puts[0].body as { markdown: string }).markdown;
  assert.match(md, /A sentence typed a moment before the flip\./);
  // The edit reached the BOOK text, not the podcast text.
  assert.match(md, /people of Persia/);
  assert.doesNotMatch(md, /truly faithful/);
});

test("a failed save aborts the flip and leaves the book lane in place", async (t) => {
  const puts: Put[] = [];
  const sess = session(t, puts, { failSave: true });
  const dom = laneDom();
  const l = lane(dom, sess);

  sess.editor!.editor.commands.insertContentAt(1, "Unsaveable. ");
  assert.equal(
    await l.setLane("podcast"),
    "book",
    "the flip must be abandoned",
  );
  assert.equal(l.lane(), "book");
  assert.equal(dom.pane.hidden, true, "the podcast pane must stay hidden");
  assert.ok(sess.editor !== null, "the editor must survive a declined leave");
  assert.equal(puts.length, 0);
  assert.equal(
    sessionStorage.getItem(`cx-restore-lane:${SLUG}`),
    null,
    "an abandoned flip must not leave a lane request behind for the next load",
  );
});

// ── 3. the flip is lossless in both directions ──────────────────────────────

test("flip away and back leaves the book chapter byte-identical", async (t) => {
  const puts: Put[] = [];
  const sess = session(t, puts);
  const dom = laneDom();
  const l = lane(dom, sess);

  const before = sess.editor!.toMarkdown();
  await l.setLane("podcast");
  assert.equal(await l.setLane("book"), "book");

  assert.equal(sess.enteredCount(), 1, "the book lane must be re-entered");
  assert.equal(sess.editor!.toMarkdown(), before, "byte-identical round trip");
  assert.equal(before, BOOK_CHAPTER_MD.trim() + "\n");
  assert.equal(puts.length, 0, "a lossless round trip writes nothing");
});

test("flipping back drops the podcast prose from the DOM", async (t) => {
  const sess = session(t, []);
  const dom = laneDom();
  const l = lane(dom, sess);

  await l.setLane("podcast");
  assert.match(dom.body.innerHTML, /truly faithful/);
  await l.setLane("book");
  assert.equal(
    dom.body.innerHTML,
    "",
    "no podcast prose may linger in the DOM",
  );
  assert.equal(dom.pane.hidden, true);
});

// ── 4. the lanes stay visibly distinct, and the pane says which is which ────

test("the podcast lane renders the podcast text, framing and citations intact", async (t) => {
  const fetched: string[] = [];
  const sess = session(t, []);
  const dom = laneDom();
  const l = lane(dom, sess, fetched);

  await l.setLane("podcast");

  assert.deepEqual(fetched, ["ch01a-three-thanks.txt"], "lazy, first chapter");
  const html = dom.body.innerHTML;
  assert.match(
    html,
    /truly faithful/,
    "the podcast translation, not the book's",
  );
  assert.doesNotMatch(html, /people of Persia/, "not the book translation");
  assert.match(
    html,
    /tenth-century dialogue/,
    "the narration framing survives",
  );
  assert.match(html, /Quran 14:7/, "the cited reference survives");
  assert.match(dom.statusEl.textContent ?? "", /chapters\/ch01a/);
});

test("the podcast picker changes chapter without touching the book lane", async (t) => {
  const fetched: string[] = [];
  const puts: Put[] = [];
  const sess = session(t, puts);
  const dom = laneDom();
  const l = lane(dom, sess, fetched);

  await l.setLane("podcast");
  dom.select.value = "ch02b-the-test-of-speech.txt";
  await l.showChapter(dom.select.value);

  assert.deepEqual(fetched, [
    "ch01a-three-thanks.txt",
    "ch02b-the-test-of-speech.txt",
  ]);
  assert.equal(puts.length, 0, "browsing the podcast lane writes nothing");
});

test("showChapter is inert in the book lane and refuses unlisted files", async (t) => {
  const fetched: string[] = [];
  const sess = session(t, []);
  const dom = laneDom();
  const l = lane(dom, sess, fetched);

  await l.showChapter("ch01a-three-thanks.txt"); // book lane
  assert.deepEqual(fetched, []);

  await l.setLane("podcast");
  await l.showChapter("../../book/book.md"); // not a listed chapter
  assert.deepEqual(fetched, ["ch01a-three-thanks.txt"]);
});

test("a fetch failure reports itself and leaves the pane empty", async (t) => {
  const sess = session(t, []);
  const dom = laneDom();
  const l = createComposeLane({
    slug: SLUG,
    chapters: CHAPTERS,
    root: dom.root,
    pane: dom.pane,
    body: dom.body,
    select: dom.select,
    status: dom.statusEl,
    bookBtn: dom.bookBtn,
    podcastBtn: dom.podcastBtn,
    book: { leave: () => sess.leave(), enter: () => sess.enter() },
    fetchChapterText: async () => {
      throw new Error("404 Not Found");
    },
  });

  assert.equal(await l.setLane("podcast"), "podcast");
  assert.equal(dom.body.innerHTML, "");
  assert.match(dom.statusEl.textContent ?? "", /Couldn't read this chapter/);
  assert.equal(dom.statusEl.classList.contains("is-error"), true);
});

// ── 5. the production call site still uses the flush-and-teardown path ──────

test("book-composer wires the lane's leave hook to leaveEditMode", () => {
  const src = readFileSync(
    new URL("./book-composer.ts", import.meta.url),
    "utf-8",
  );
  const at = src.indexOf("createComposeLane(");
  assert.notEqual(at, -1, "the Composer must mount the lane controller");
  const call = src.slice(at);
  assert.match(
    call.slice(0, 2_000),
    /leave:\s*\(\)\s*=>\s*leaveEditMode\(\)/,
    "the podcast flip must go through leaveEditMode (flush + editor teardown)",
  );
  assert.match(
    call.slice(0, 2_000),
    /enter:\s*\(\)\s*=>/,
    "the book lane must have a re-entry hook",
  );
});

test("two rapid flips do not run the flush twice", async (t) => {
  // `lane` stays "book" for the whole await on leave(), so an unserialized
  // second click would sail past the same-lane guard and flush again — two PUTs
  // for one edit, and two teardowns of one editor.
  const puts: Put[] = [];
  const sess = session(t, puts);
  const dom = laneDom();
  const l = lane(dom, sess);
  let leaves = 0;
  const inner = sess.leave.bind(sess);

  const guarded = createComposeLane({
    slug: SLUG,
    chapters: CHAPTERS,
    root: dom.root,
    pane: dom.pane,
    body: dom.body,
    select: dom.select,
    status: dom.statusEl,
    bookBtn: dom.bookBtn,
    podcastBtn: dom.podcastBtn,
    book: {
      leave: async () => {
        leaves += 1;
        return inner();
      },
      enter: () => sess.enter(),
    },
    fetchChapterText: async () => PODCAST_CHAPTER_TXT,
  });
  void l; // the shared instance above is unused here — this test drives `guarded`

  sess.editor!.editor.commands.insertContentAt(1, "One edit, one save. ");
  const [a, b] = await Promise.all([
    guarded.setLane("podcast"),
    guarded.setLane("podcast"),
  ]);

  assert.equal(a, "podcast");
  assert.equal(b, "podcast");
  assert.equal(leaves, 1, "the book lane must be left exactly once");
  assert.equal(puts.length, 1, "one edit must produce exactly one save");
});

test("a flip back queued behind a flip out still lands on the book lane", async (t) => {
  const sess = session(t, []);
  const dom = laneDom();
  const l = lane(dom, sess);

  const [out, back] = await Promise.all([
    l.setLane("podcast"),
    l.setLane("book"),
  ]);

  assert.equal(out, "podcast");
  assert.equal(
    back,
    "book",
    "the queued flip back must run after the flip out",
  );
  assert.equal(l.lane(), "book");
  assert.equal(dom.pane.hidden, true);
});

test("the picker is told when the lane sets its value itself", async (t) => {
  // The visible chapter list is drawn, not the OS dropdown, so the <select> is
  // only the state holder — setting `.value` without syncing leaves the list
  // showing the wrong chapter title beside the right prose.
  const sess = session(t, []);
  const dom = laneDom();
  while (dom.select.options.length) dom.select.remove(0); // no value to inherit
  let syncs = 0;

  const l = createComposeLane({
    slug: SLUG,
    chapters: CHAPTERS,
    root: dom.root,
    pane: dom.pane,
    body: dom.body,
    select: dom.select,
    syncSelect: () => {
      syncs += 1;
    },
    status: dom.statusEl,
    bookBtn: dom.bookBtn,
    podcastBtn: dom.podcastBtn,
    book: { leave: () => sess.leave(), enter: () => sess.enter() },
    fetchChapterText: async () => PODCAST_CHAPTER_TXT,
  });

  await l.setLane("podcast");
  assert.equal(
    syncs,
    1,
    "the drawn picker must be re-read after a value change",
  );
  assert.match(dom.statusEl.textContent ?? "", /chapters\/ch01a/);
});

// ── 6. the page keeps ONE h1 — the podcast sources open with their own ──────

test("the lane demotes the source's own h1 so the page keeps a single h1", async (t) => {
  // A chapter source opens with `# Title`, and renderSourceMarkdown emits that
  // verbatim. The page's one <h1> is the book title, and the reading lane sets a
  // chapter title as <h2> — so an undemoted source heading both duplicates the
  // h1 and makes the two lanes disagree about what a chapter title is.
  const sess = session(t, []);
  const dom = laneDom();
  const l = lane(dom, sess);

  await l.setLane("podcast");

  assert.equal(
    dom.body.querySelectorAll("h1").length,
    0,
    "no h1 may survive in the podcast pane",
  );
  const first = dom.body.querySelector("h2, h3, h4, h5, h6");
  assert.equal(
    first?.tagName,
    "H2",
    "the source's h1 becomes the chapter's h2",
  );
  assert.match(first?.textContent ?? "", /Three Thanks/);
  // Its own `## Where the dialogue opens` section heading follows one level down.
  assert.equal(
    dom.body.querySelector("h3")?.textContent,
    "Where the dialogue opens",
  );
});

test("demoteHeadings shifts one level, keeps attributes, and never double-demotes", () => {
  const host = el("div");
  host.innerHTML =
    '<h1 id="t" class="k">Title</h1><h2>Sec <em>x</em></h2><h5>deep</h5>' +
    "<h6>floor</h6><p>body</p>";
  demoteHeadings(host);

  assert.equal(
    host.innerHTML,
    '<h2 id="t" class="k">Title</h2><h3>Sec <em>x</em></h3><h6>deep</h6>' +
      "<h6>floor</h6><p>body</p>",
  );
  // h6 has nowhere to go and must be left alone rather than dropped.
  assert.equal(host.querySelectorAll("h6").length, 2);
});

// ── 7. the reload-restore path: the stash must OUTLIVE leave() ──────────────

test("a successful flip leaves the lane stashed for a reload to restore", async (t) => {
  // `leave()` is leaveEditMode, which reloads the page when prose changed.
  // `location.reload()` queues a navigation instead of halting the task, so any
  // clear after leave() runs BEFORE the reload — which deleted the request in
  // exactly the case the mechanism exists for, landing the user back in the
  // editor after pressing Podcast. Asserted from inside the hook, which is the
  // only vantage point a stubbed leave can offer on the reload window.
  const sess = session(t, []);
  const dom = laneDom();
  let stashedDuringLeave: string | null = null;
  forgetLaneState();

  const l = createComposeLane({
    slug: SLUG,
    chapters: CHAPTERS,
    root: dom.root,
    pane: dom.pane,
    body: dom.body,
    select: dom.select,
    status: dom.statusEl,
    bookBtn: dom.bookBtn,
    podcastBtn: dom.podcastBtn,
    book: {
      leave: async () => {
        stashedDuringLeave = composeLaneState.read(SLUG);
        return sess.leave();
      },
      enter: () => sess.enter(),
    },
    fetchChapterText: async () => PODCAST_CHAPTER_TXT,
  });

  await l.setLane("podcast");
  assert.equal(stashedDuringLeave, "podcast", "stashed before leave() runs");
  assert.equal(
    composeLaneState.read(SLUG),
    "podcast",
    "and STILL stashed after — a reload queued inside leave() must find it",
  );
});

test("flipping back to the book clears the stash", async (t) => {
  const sess = session(t, []);
  const dom = laneDom();
  const l = lane(dom, sess);

  await l.setLane("podcast");
  assert.equal(composeLaneState.read(SLUG), "podcast");
  await l.setLane("book");
  assert.equal(
    composeLaneState.read(SLUG),
    null,
    "the book lane is the default — nothing to restore",
  );
});

test("pendingLane is durable, so it survives past the reload that read it", () => {
  // It used to be consumed on read, which made it a one-shot handoff: it kept
  // your lane across the editor's own autosave reload and lost it on a plain
  // F5 or a new tab. The same value now answers both questions, so reading it
  // must NOT erase it.
  forgetLaneState();
  composeLaneState.write("podcast", SLUG);
  assert.equal(pendingLane(SLUG), "podcast");
  assert.equal(pendingLane(SLUG), "podcast", "still there on a second read");
});

test("a remembered podcast file is restored on the flip, over the picker default", async (t) => {
  const sess = session(t, []);
  const dom = laneDom();
  const fetched: string[] = [];
  const l = lane(dom, sess, fetched); // clears state, then we seed it
  composePodcastFile.write(CHAPTERS[1].file, SLUG);

  await l.setLane("podcast");
  assert.deepEqual(
    fetched,
    [CHAPTERS[1].file],
    "after a reload the picker is back at option one; the memory is what restores",
  );
});

test("a remembered podcast file that no longer exists falls back to the first", async (t) => {
  const sess = session(t, []);
  const dom = laneDom();
  const fetched: string[] = [];
  const l = lane(dom, sess, fetched);
  composePodcastFile.write("ch99-a-chapter-that-was-removed.txt", SLUG);

  await l.setLane("podcast");
  assert.deepEqual(
    fetched,
    [CHAPTERS[0].file],
    "a stale memory must never be fetched into a 404",
  );
});
