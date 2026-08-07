/**
 * Accepting a note has to be visible on the card that was already built.
 *
 * The panel REUSES a card across renders on purpose — rebuilding it destroys the
 * editor a keystroke after the author opened it. The cost, live until
 * 2026-08-06, was that a card built from a "proposed" note kept its Unreviewed
 * badge and its tick after the note was accepted: the PATCH returned 200, the
 * file on disk said "kept", and pressing the tick looked from the outside like
 * it did nothing at all. Nothing failed, so nothing was reported.
 *
 * These tests hold the two halves of the fix: the card can be TOLD, and being
 * told is what removes both affordances.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { Window } from "happy-dom";

const win = new Window({ url: "http://localhost/" });
for (const k of [
  "window",
  "document",
  "DOMParser",
  "Node",
  "HTMLElement",
  "getComputedStyle",
  "requestAnimationFrame",
  "cancelAnimationFrame",
  "ResizeObserver",
] as const) {
  try {
    (globalThis as Record<string, unknown>)[k] = (
      win as unknown as Record<string, unknown>
    )[k];
  } catch {
    /* already provided by the host */
  }
}

import { renderExplanationCard } from "./explanation-card";
import type { CompanionNote } from "./types";

function aNote(over: Partial<CompanionNote> = {}): CompanionNote {
  return {
    id: "student:abc123",
    kind: "explanation",
    body: "The five conditions are named in the following chapter.",
    anchor: "the five conditions",
    quote: "the five conditions",
    review: "proposed",
    source: { provider: "scholar", label: "Ismaili Scholar" },
    ...over,
  } as CompanionNote;
}

/** The card as the Composer mounts it — with the handlers a review pass has. */
function composerCard(note: CompanionNote) {
  return renderExplanationCard(note, {
    onSave: () => {},
    onRemove: () => {},
    onAccept: () => {},
  });
}

test("an unreviewed note shows both the badge and the tick", () => {
  const card = composerCard(aNote());
  assert.equal(card.el.querySelectorAll(".xpl-proposed").length, 1);
  assert.equal(card.el.querySelectorAll(".xpl-keep").length, 1);
});

test("being told it was kept removes both", () => {
  // THE regression. Before the fix there was no way to say this at all, so a
  // reused card contradicted the file it came from.
  const card = composerCard(aNote());
  card.markKept();
  assert.equal(card.el.querySelectorAll(".xpl-proposed").length, 0);
  assert.equal(card.el.querySelectorAll(".xpl-keep").length, 0);
});

test("telling it twice is not an error", () => {
  // The panel calls this on every render of every accepted note, not once on
  // the transition — it has no idea which render is the first.
  const card = composerCard(aNote());
  card.markKept();
  card.markKept();
  assert.equal(card.el.querySelectorAll(".xpl-keep").length, 0);
});

test("a note already kept never had a badge or a tick to remove", () => {
  const card = composerCard(aNote({ review: "kept" }));
  assert.equal(card.el.querySelectorAll(".xpl-proposed").length, 0);
  assert.equal(card.el.querySelectorAll(".xpl-keep").length, 0);
  card.markKept();
  assert.equal(card.el.querySelectorAll(".xpl-proposed").length, 0);
});

test("a note with no review field is unmarked — absent means kept", () => {
  // Every note written before the field existed, and every note Asif typed
  // himself. Marking those unreviewed would put a badge on his own writing.
  const note = aNote();
  delete (note as Partial<CompanionNote>).review;
  const card = composerCard(note);
  assert.equal(card.el.querySelectorAll(".xpl-proposed").length, 0);
  assert.equal(card.el.querySelectorAll(".xpl-keep").length, 0);
});

test("a reading pass gets no tick even on an unreviewed note", () => {
  // No accept handler means no review is happening here, and a button that
  // called nothing would be a control that silently does nothing — the exact
  // complaint this whole file is about.
  const card = renderExplanationCard(aNote(), {});
  assert.equal(card.el.querySelectorAll(".xpl-keep").length, 0);
  assert.equal(
    card.el.querySelectorAll(".xpl-proposed").length,
    1,
    "the badge is still true",
  );
});

test("accepting does not disturb the delete button", () => {
  // Keeping is reversible precisely because delete survives it.
  const card = composerCard(aNote());
  assert.equal(
    card.el.querySelectorAll(".xpl-del").length,
    1,
    "there was one to disturb",
  );
  card.markKept();
  assert.equal(card.el.querySelectorAll(".xpl-del").length, 1);
});
