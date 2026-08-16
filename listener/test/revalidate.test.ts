import { describe, expect, it } from "vitest";

import { shouldRevalidate } from "../app/routes/book.$slug";

/**
 * When the book page must ask the server again.
 *
 * This function exists so that switching a tab does not re-run six queries, and
 * it shipped with a bug that looked nothing like a caching bug: deleting a
 * bookmark from the Notes tab stopped working. It had not stopped working — the
 * row was deleted every time — but a fetcher submission does not change the URL,
 * so "nothing about the URL changed, skip the refresh" also cancelled the reload
 * that would have shown it gone. A delete button that deletes and leaves the row
 * on screen is indistinguishable from one that is not wired up at all.
 *
 * The rule these pin: only a plain GET navigation whose ONLY difference is
 * `?tab` may be skipped. Everything else revalidates.
 */

const args = (over: Partial<Parameters<typeof shouldRevalidate>[0]> = {}) =>
  ({
    currentUrl: new URL("https://x.test/book/a?tab=read"),
    nextUrl: new URL("https://x.test/book/a?tab=notes"),
    currentParams: {},
    nextParams: {},
    defaultShouldRevalidate: true,
    ...over,
  }) as Parameters<typeof shouldRevalidate>[0];

describe("revalidating the book page", () => {
  it("skips the refresh when only the open tab changed", () => {
    expect(shouldRevalidate(args())).toBe(false);
  });

  it("refreshes after a submission, even though the URL is identical", () => {
    // The delete button. A fetcher posts to the marks endpoint and the page URL
    // never moves, so without this the list keeps showing what was just removed.
    const url = new URL("https://x.test/book/a?tab=notes");
    expect(
      shouldRevalidate(
        args({ currentUrl: url, nextUrl: url, formMethod: "POST" }),
      ),
    ).toBe(true);
  });

  it("refreshes after every other submission method too", () => {
    const url = new URL("https://x.test/book/a?tab=notes");
    for (const formMethod of ["POST", "PUT", "PATCH", "DELETE"] as const) {
      expect(
        shouldRevalidate(args({ currentUrl: url, nextUrl: url, formMethod })),
      ).toBe(true);
    }
  });

  it("refreshes when the book itself changed", () => {
    expect(
      shouldRevalidate(
        args({
          currentUrl: new URL("https://x.test/book/a?tab=read"),
          nextUrl: new URL("https://x.test/book/b?tab=read"),
        }),
      ),
    ).toBe(true);
  });

  it("refreshes when anything else in the query changed", () => {
    expect(
      shouldRevalidate(
        args({
          currentUrl: new URL("https://x.test/book/a?tab=read"),
          nextUrl: new URL("https://x.test/book/a?tab=read&page=2"),
        }),
      ),
    ).toBe(true);
  });

  it("never overrides a router that has already decided not to", () => {
    // When the default is false the answer is false: this function exists to
    // skip work, never to demand it.
    expect(
      shouldRevalidate(
        args({
          currentUrl: new URL("https://x.test/book/a"),
          nextUrl: new URL("https://x.test/book/b"),
          defaultShouldRevalidate: false,
        }),
      ),
    ).toBe(false);
  });
});
