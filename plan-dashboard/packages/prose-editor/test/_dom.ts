/**
 * _dom.ts — DOM bootstrap for the package's tests.
 *
 * Mirrors the host repo's proven pattern: construct a happy-dom Window and put
 * its globals in place BEFORE importing anything that touches the DOM, because
 * TipTap parses HTML through the global DOMParser at module scope.
 *
 * Import this first, for its side effect, in every test that builds elements.
 */
import { Window } from "happy-dom";

const win = new Window();

Object.assign(globalThis, {
  window: win,
  document: win.document,
  DOMParser: win.DOMParser,
  HTMLElement: win.HTMLElement,
  Element: win.Element,
  Node: win.Node,
  Event: win.Event,
  CustomEvent: win.CustomEvent,
  getComputedStyle: win.getComputedStyle.bind(win),
  // happy-dom ships no rAF, and TipTap's focus() schedules through it. Run the
  // callback synchronously: the tests assert on state AFTER a command, so a
  // deferred frame would just make every assertion race.
  requestAnimationFrame: (cb: FrameRequestCallback) => {
    cb(0);
    return 0;
  },
  cancelAnimationFrame: () => {},
});

/** happy-dom's element types are structurally compatible but nominally distinct;
 *  cast once here rather than at every call site. */
export const doc = win.document as unknown as Document;
