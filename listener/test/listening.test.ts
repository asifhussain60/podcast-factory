import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  flushMoments,
  flushPositions,
  pendingCount,
  pendingMoments,
  queueMoment,
  queuePosition,
  withPendingMoments,
} from "../app/lib/listening";

/**
 * Positions listened to with no network.
 *
 * The rule worth pinning is not that the queue works — it is what the flush does
 * with a request that DID NOT SUCCEED, because the wrong answer to that either
 * loses an hour of listening or hammers the server on every launch forever.
 */

/** A localStorage good enough for a module that only get/sets one key. */
function fakeStorage() {
  const map = new Map<string, string>();
  return {
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
    clear: () => map.clear(),
    key: () => null,
    length: 0,
  } as unknown as Storage;
}

beforeEach(() => {
  vi.stubGlobal("localStorage", fakeStorage());
  vi.unstubAllEnvs();
});

describe("the listening outbox", () => {
  it("keeps one entry per episode, with the latest position", () => {
    queuePosition("wisdom", 2, 100);
    queuePosition("wisdom", 2, 250);
    queuePosition("wisdom", 3, 10);

    expect(pendingCount()).toBe(2);
  });

  it("keeps the LAST position, not the furthest", async () => {
    // Where somebody stopped is where they stopped. Scrubbing back twenty
    // minutes and closing the app means they want to resume there, and keeping
    // the maximum would silently refuse that.
    queuePosition("wisdom", 2, 2000);
    queuePosition("wisdom", 2, 30);

    const sent: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: string, init: RequestInit) => {
        sent.push(String(init.body));
        return new Response("", { status: 200 });
      }),
    );

    await flushPositions();
    expect(sent[0]).toContain("seconds=30");
  });

  it("sends each queued position to ITS OWN book", async () => {
    // The whole reason this is not routed through lib/marks: a listener can have
    // one book playing while reading another, and a queue with a single current
    // book would file a position under the wrong work.
    queuePosition("wisdom", 1, 10);
    queuePosition("ayyuha-al-walad", 4, 20);

    const urls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        urls.push(url);
        return new Response("", { status: 200 });
      }),
    );

    await flushPositions();
    expect(urls).toContain("/book/wisdom/marks");
    expect(urls).toContain("/book/ayyuha-al-walad/marks");
    expect(pendingCount()).toBe(0);
  });

  it("keeps everything when the network is still gone", async () => {
    queuePosition("wisdom", 1, 10);
    queuePosition("wisdom", 2, 20);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Promise.reject(new Error("offline"))),
    );

    await flushPositions();
    expect(pendingCount()).toBe(2);
  });

  it("stops at the first failure instead of firing the rest", async () => {
    // One dead request means the link is down; sending the remainder anyway
    // turns a single failure into a queue-length burst every time the device
    // flickers.
    queuePosition("a", 1, 10);
    queuePosition("b", 2, 20);
    queuePosition("c", 3, 30);
    const fetcher = vi.fn(async () => Promise.reject(new Error("offline")));
    vi.stubGlobal("fetch", fetcher);

    await flushPositions();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("keeps a position when the gate bounced us to sign-in", async () => {
    // A redirect is not a refusal of this position — it is nobody being signed
    // in. Dropping it would lose the listening; retrying it later is right.
    queuePosition("wisdom", 1, 10);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        const response = new Response("", { status: 200 });
        Object.defineProperty(response, "redirected", { value: true });
        return response;
      }),
    );

    await flushPositions();
    expect(pendingCount()).toBe(1);
  });

  it("drops a position the server will never accept", async () => {
    // A 404 means the book is gone or no longer readable. Keeping it would
    // retry the same doomed request on every launch for as long as the app is
    // installed.
    queuePosition("withdrawn", 1, 10);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("", { status: 404 })),
    );

    await flushPositions();
    expect(pendingCount()).toBe(0);
  });
});

describe("the moment outbox", () => {
  const keep = (id: string, seconds: number, note = "") => ({
    slug: "wisdom",
    intent: "episode-note" as const,
    fields: { id, number: "2", seconds: String(seconds), note, quote: "" },
  });

  it("preserves ORDER, unlike the position queue", () => {
    // The whole reason moments are a list and positions are a map. Two writes
    // against the same note are two events, not one value.
    queueMoment(keep("a", 10));
    queueMoment({
      slug: "wisdom",
      intent: "un-episode-note",
      fields: { id: "a" },
    });

    expect(pendingMoments().map((m) => m.intent)).toEqual([
      "episode-note",
      "un-episode-note",
    ]);
  });

  it("shows a moment kept with no network, before it has been sent", () => {
    // Otherwise marking a moment on a plane is indistinguishable from a button
    // that does nothing.
    queueMoment(keep("a", 30, "a thought"));

    const shown = withPendingMoments("wisdom", 2, []);
    expect(shown).toHaveLength(1);
    expect(shown[0]).toMatchObject({ id: "a", seconds: 30, note: "a thought" });
  });

  it("replays an add-then-withdraw to nothing", () => {
    queueMoment(keep("a", 30));
    queueMoment({
      slug: "wisdom",
      intent: "un-episode-note",
      fields: { id: "a" },
    });

    expect(withPendingMoments("wisdom", 2, [])).toEqual([]);
  });

  it("replays an edit over what the server already has", () => {
    const server = [
      { id: "a", number: 2, seconds: 30, note: "old", quote: null },
    ];
    queueMoment(keep("a", 30, "new"));

    expect(withPendingMoments("wisdom", 2, server)).toEqual([
      { id: "a", number: 2, seconds: 30, note: "new", quote: null },
    ]);
  });

  it("shows nothing from another book", () => {
    // The objection that kept the player from having an outbox at all: a queue
    // with no per-entry book files a note under whatever is open.
    queueMoment(keep("a", 30));
    expect(withPendingMoments("ayyuha-al-walad", 2, [])).toEqual([]);
  });

  it("sends in order and never reaches past a failure", async () => {
    /* THE rule. Three writes: the first lands, the second cannot go out, and
       the third must NOT be attempted — sending it would put a later write
       against this note ahead of an earlier one, which for an add followed by a
       withdrawal means the note survives its own deletion. */
    queueMoment(keep("a", 10));
    queueMoment({
      slug: "wisdom",
      intent: "un-episode-note",
      fields: { id: "a" },
    });
    queueMoment(keep("c", 30));

    const attempted: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: string, init: RequestInit) => {
        const body = String(init.body);
        attempted.push(body);
        if (attempted.length === 1)
          return new Response(JSON.stringify({ ok: true }), { status: 200 });
        throw new Error("offline");
      }),
    );

    await flushMoments();

    // Two attempts: the one that landed, and the one that could not. Never the
    // third.
    expect(attempted).toHaveLength(2);
    expect(attempted[0]).toContain("intent=episode-note");
    expect(attempted[1]).toContain("intent=un-episode-note");

    // What is left is the failure and everything behind it, in order.
    expect(pendingMoments().map((m) => m.intent)).toEqual([
      "un-episode-note",
      "episode-note",
    ]);
  });

  it("drops a write the server will never accept", async () => {
    // A malformed note refused as permanent would otherwise block every write
    // behind it for as long as the app is installed.
    queueMoment(keep("a", 10));
    queueMoment(keep("b", 20));
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ error: "bad id", permanent: true }), {
            status: 200,
          }),
      ),
    );

    await flushMoments();
    expect(pendingMoments()).toEqual([]);
  });

  it("keeps everything when the gate bounced us to sign-in", async () => {
    queueMoment(keep("a", 10));
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        const response = new Response("", { status: 200 });
        Object.defineProperty(response, "redirected", { value: true });
        return response;
      }),
    );

    await flushMoments();
    expect(pendingMoments()).toHaveLength(1);
  });
});
