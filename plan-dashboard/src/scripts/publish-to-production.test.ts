/**
 * The Publish button's two decisions that are not the server's.
 *
 * `choicesFor` is where the "pick intelligently" judgement lives — which options
 * are offered and which are pre-ticked — and judgement is worth pinning.
 * `events` is the NDJSON reader, and its failure mode is why it is here: a
 * dropped or mis-split line means the panel silently omits the one failed check
 * that explains the run.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { choicesFor, events } from "./publish-to-production";

function bodyOf(...chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
}

async function drain(
  stream: ReadableStream<Uint8Array>,
): Promise<Record<string, unknown>[]> {
  const out: Record<string, unknown>[] = [];
  for await (const ev of events(stream)) out.push(ev);
  return out;
}

const byId = (state: Parameters<typeof choicesFor>[0]) =>
  Object.fromEntries(choicesFor(state).map((c) => [c.id, c]));

// ─── which options are offered, and which start ticked ──────────────────────

test("no offer to accept cards when there are none to accept", () => {
  // A ticked box that would do nothing teaches the reader to stop reading the
  // boxes — and its label would read "Accept 0 unreviewed Companion cards".
  assert.equal(byId({ unreviewed: 0 }).accept, undefined);
});

test("the offer names the exact number it would accept, and is ticked", () => {
  const accept = byId({ unreviewed: 29 }).accept;
  assert.equal(accept.label, "Accept 29 unreviewed Companion cards");
  assert.equal(accept.checked, true);
});

test("one card is a card, not cards", () => {
  assert.equal(
    byId({ unreviewed: 1 }).accept.label,
    "Accept 1 unreviewed Companion card",
  );
});

test("the PDF re-render is pre-ticked when chapters changed", () => {
  // The print edition ships with the book, so an edited chapter over a stale PDF
  // sends readers a printed book that disagrees with the text on screen.
  const state = { reason: "chapters or cards changed since the last publish" };
  assert.equal(byId(state).rebuildPdf.checked, true);
});

test("the PDF re-render is NOT pre-ticked for a book never published", () => {
  // Nothing was edited — it has simply never gone out. Spending a minute on a
  // render nobody asked for is how a one-click button stops being one.
  assert.equal(
    byId({ reason: "never published to production" }).rebuildPdf.checked,
    false,
  );
});

test("the PDF hint never explains a tick that is not there", () => {
  // Caught in the browser, 2026-08-06: the hint read "Ticked because chapters
  // changed" beside an unticked box. A hint that contradicts what it sits next
  // to teaches the reader that the hints are decoration.
  const off = byId({ reason: "never published to production" }).rebuildPdf;
  assert.equal(off.checked, false);
  assert.ok(off.hint, "the option must explain itself either way");
  assert.doesNotMatch(off.hint, /ticked/i);

  const on = byId({
    reason: "chapters or cards changed since the last publish",
  }).rebuildPdf;
  assert.equal(on.checked, true);
  assert.ok(on.hint);
  assert.match(on.hint, /ticked/i);
});

test("the plain run is the complete run", () => {
  // Every option SUBTRACTS work, so the untouched dialog publishes everything.
  const all = byId({});
  assert.equal(all.transcripts.checked, true);
  assert.equal(all.media.checked, true);
});

test("every option explains itself", () => {
  for (const choice of choicesFor({ unreviewed: 3 })) {
    assert.ok(choice.hint, `${choice.id} has no hint`);
    assert.match(choice.icon, /^fa-/);
  }
});

// ─── reading the run as it arrives ──────────────────────────────────────────

test("one event per line", async () => {
  const out = await drain(
    bodyOf(
      '{"event":"step","name":"Content"}\n{"event":"done","verified":true}\n',
    ),
  );
  assert.deepEqual(out, [
    { event: "step", name: "Content" },
    { event: "done", verified: true },
  ]);
});

test("a line split across two chunks is held until it is whole", async () => {
  // A chunk boundary inside a JSON object is the normal case on a slow upload;
  // splitting there would drop the event entirely.
  const out = await drain(
    bodyOf('{"event":"check","name":"vis', 'ible","ok":true}\n'),
  );
  assert.deepEqual(out, [{ event: "check", name: "visible", ok: true }]);
});

test("a final line that never got its newline is still yielded", async () => {
  const out = await drain(bodyOf('{"event":"done","verified":false}'));
  assert.deepEqual(out, [{ event: "done", verified: false }]);
});

test("output that will not parse becomes a log line rather than nothing", async () => {
  // Almost always a warning printed by a tool the driver called. Swallowing it
  // would hide the one thing explaining a failed check.
  const out = await drain(bodyOf("npm warn something\n"));
  assert.deepEqual(out, [{ event: "log", text: "npm warn something" }]);
});

test("blank lines are ignored", async () => {
  assert.equal(
    (await drain(bodyOf('\n\n{"event":"log","text":"a"}\n\n'))).length,
    1,
  );
});
