/**
 * compose-narration.test.ts — the Book Composer's read-aloud control.
 *
 * Exercises the three states createComposeNarration must get right without
 * ever touching the network: (1) a chapter that already has narration shows
 * the player and never the button; (2) clicking "Generate narration" POSTs,
 * then polls, then — on success — asks the audio route directly (HEAD) rather
 * than trusting the render summary's ambiguous rendered/skipped lists (see the
 * module header); (3) a book-level `skipped` reason retires the button for
 * good instead of offering a retry that can only fail the same way again.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { Window } from "happy-dom";

const win = new Window({ url: "http://localhost/" });
for (const key of [
  "window",
  "document",
  "HTMLElement",
  "Element",
  "Node",
  "Event",
] as const) {
  try {
    (globalThis as Record<string, unknown>)[key] = (
      win as unknown as Record<string, unknown>
    )[key];
  } catch {
    /* already defined by the host and equivalent */
  }
}

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
): HTMLElementTagNameMap[K] {
  return win.document.createElement(tag) as unknown as HTMLElementTagNameMap[K];
}

const { createComposeNarration } = await import("./compose-narration.ts");

interface Harness {
  container: HTMLElement;
  generateBtn: HTMLButtonElement;
  audio: HTMLAudioElement;
  status: HTMLElement;
}

function harness(): Harness {
  return {
    container: el("div"),
    generateBtn: el("button"),
    audio: el("audio"),
    status: el("span"),
  };
}

/** A scripted fetch: each call consumes the next queued response. */
function scriptedFetch(
  responses: Array<
    | { ok: true; json?: unknown }
    | { ok: false; status: number }
  >,
): { fetchImpl: typeof fetch; calls: string[] } {
  const calls: string[] = [];
  let i = 0;
  const fetchImpl = (async (
    input: RequestInfo | URL,
    init?: RequestInit,
  ) => {
    calls.push(`${init?.method ?? "GET"} ${String(input)}`);
    const next = responses[Math.min(i, responses.length - 1)];
    i += 1;
    return {
      ok: next.ok,
      status: next.ok ? 200 : next.status,
      statusText: "",
      json: async () => ("json" in next ? next.json : {}),
    } as Response;
  }) as typeof fetch;
  return { fetchImpl, calls };
}

test("a chapter with narrationAvailable shows the player, never the button", () => {
  const h = harness();
  createComposeNarration({
    slug: "sample-book",
    chapters: [{ key: "intro", available: true, durationS: 95 }],
    container: h.container,
    generateBtn: h.generateBtn,
    audio: h.audio,
    status: h.status,
    fetchImpl: scriptedFetch([]).fetchImpl,
  }).setEligible(true);

  assert.equal(h.container.hidden, false);
  assert.equal(h.generateBtn.hidden, true);
  assert.equal(h.audio.hidden, false);
  assert.match(h.audio.getAttribute("src") ?? "", /chapter=intro/);
  assert.match(h.audio.getAttribute("src") ?? "", /slug=sample-book/);
  assert.equal(h.status.textContent, "1:35");
});

test("a chapter with no narration shows the enabled generate button, not the player", () => {
  const h = harness();
  createComposeNarration({
    slug: "sample-book",
    chapters: [{ key: "intro", available: false, durationS: null }],
    container: h.container,
    generateBtn: h.generateBtn,
    audio: h.audio,
    status: h.status,
    fetchImpl: scriptedFetch([]).fetchImpl,
  }).setEligible(true);

  assert.equal(h.generateBtn.hidden, false);
  assert.equal(h.generateBtn.disabled, false);
  assert.equal(h.audio.hidden, true);
});

test("the control stays hidden until setEligible(true), regardless of chapter data", () => {
  const h = harness();
  createComposeNarration({
    slug: "sample-book",
    chapters: [{ key: "intro", available: true, durationS: 95 }],
    container: h.container,
    generateBtn: h.generateBtn,
    audio: h.audio,
    status: h.status,
    fetchImpl: scriptedFetch([]).fetchImpl,
  });

  assert.equal(h.container.hidden, true);
});

test("generate: click -> POST -> poll running -> poll done -> probes THIS chapter's audio via HEAD", async () => {
  const h = harness();
  const { fetchImpl, calls } = scriptedFetch([
    { ok: true, json: { ok: true, data: { slug: "sample-book", pid: 123 } } }, // POST
    { ok: true, json: { ok: true, data: { state: "running" } } }, // first poll
    {
      ok: true,
      json: {
        ok: true,
        data: { state: "done", rendered: ["intro"], skipped: [] },
      },
    }, // second poll
    { ok: true }, // HEAD probe — file exists
  ]);
  const ctl = createComposeNarration({
    slug: "sample-book",
    chapters: [{ key: "intro", available: false, durationS: null }],
    container: h.container,
    generateBtn: h.generateBtn,
    audio: h.audio,
    status: h.status,
    fetchImpl,
    pollIntervalMs: 1,
  });
  ctl.setEligible(true);

  h.generateBtn.dispatchEvent(new Event("click"));
  // "Generating…" shows immediately, before the POST resolves.
  assert.match(h.status.textContent ?? "", /Generating narration/);
  assert.equal(h.generateBtn.hidden, true);

  // Let the POST, both polls (1ms apart) and the HEAD probe settle.
  await new Promise((r) => setTimeout(r, 40));

  assert.equal(calls[0], "POST /api/studio/narration");
  assert.ok(calls.some((c) => c.startsWith("GET /api/studio/narration?")));
  assert.ok(calls.some((c) => c.startsWith("HEAD /api/studio/narration-audio?")));
  assert.equal(h.audio.hidden, false);
  assert.equal(h.generateBtn.hidden, true);
});

test("a book-level skip reason retires the button instead of offering a retry", async () => {
  const h = harness();
  const { fetchImpl } = scriptedFetch([
    { ok: true, json: { ok: true, data: { pid: 1 } } }, // POST
    {
      ok: true,
      json: {
        ok: true,
        data: { state: "skipped", reason: "not an Islamic source book" },
      },
    }, // poll
  ]);
  const ctl = createComposeNarration({
    slug: "sample-book",
    chapters: [{ key: "intro", available: false, durationS: null }],
    container: h.container,
    generateBtn: h.generateBtn,
    audio: h.audio,
    status: h.status,
    fetchImpl,
    pollIntervalMs: 1,
  });
  ctl.setEligible(true);
  h.generateBtn.dispatchEvent(new Event("click"));
  await new Promise((r) => setTimeout(r, 20));

  assert.equal(h.generateBtn.hidden, true);
  assert.match(h.status.textContent ?? "", /not an Islamic source book/);

  // A second click must not re-fire the request — the button is retired.
  h.generateBtn.dispatchEvent(new Event("click"));
  await new Promise((r) => setTimeout(r, 5));
  assert.match(h.status.textContent ?? "", /not an Islamic source book/);
});

test("a per-chapter probe miss reports 'no narration for this chapter', not a generic error", async () => {
  const h = harness();
  const { fetchImpl } = scriptedFetch([
    { ok: true, json: { ok: true, data: { pid: 1 } } }, // POST
    {
      ok: true,
      json: { ok: true, data: { state: "done", rendered: [], skipped: ["intro"] } },
    }, // poll
    { ok: false, status: 404 }, // HEAD probe — no file for THIS chapter
  ]);
  const ctl = createComposeNarration({
    slug: "sample-book",
    chapters: [{ key: "intro", available: false, durationS: null }],
    container: h.container,
    generateBtn: h.generateBtn,
    audio: h.audio,
    status: h.status,
    fetchImpl,
    pollIntervalMs: 1,
  });
  ctl.setEligible(true);
  h.generateBtn.dispatchEvent(new Event("click"));
  await new Promise((r) => setTimeout(r, 20));

  assert.equal(h.audio.hidden, true);
  assert.equal(h.generateBtn.hidden, false); // free to retry — a re-render might help
  assert.match(h.status.textContent ?? "", /No narration was produced/);
});
