import { beforeEach, describe, expect, it, vi } from "vitest";

import { flushPositions, pendingCount, queuePosition } from "../app/lib/listening";

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
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new Error("offline"))));

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
    vi.stubGlobal("fetch", vi.fn(async () => new Response("", { status: 404 })));

    await flushPositions();
    expect(pendingCount()).toBe(0);
  });
});
