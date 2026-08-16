import { describe, expect, it } from "vitest";

import { inviteMessage } from "../app/lib/inviteMessage";

/**
 * The note that goes to a real person. It is the one thing this application
 * produces that leaves it entirely — pasted into a chat, read by somebody who
 * has never seen the site — so the parts that are load-bearing are asserted:
 * the address they must sign in with, the two links, and what they can open.
 *
 * The TONE is not asserted, and deliberately. "Informal" is a judgement, and a
 * test that pinned a phrase would fail the next time the phrasing improved while
 * proving nothing about whether it reads well.
 */

const base = {
  displayName: "Mariam Palejwala",
  email: "mariampalejwala07@gmail.com",
  siteUrl: "https://podcast-factory.safinaverse.com",
  books: ["Degrees of Excellence"],
  wholeLibrary: false,
};

describe("the invitation message", () => {
  it("greets by given name, not by full name", () => {
    // "Salaam Mariam Palejwala" reads like a form letter, which is what this
    // must not read like.
    expect(inviteMessage(base)).toContain("Salaam Mariam");
  });

  it("names the exact address they must sign in with", () => {
    // Access is keyed on the email. Somebody who signs in with a different
    // Google account lands on the no-access page and concludes the link is
    // broken — this line is what prevents that support question.
    expect(inviteMessage(base)).toContain("mariampalejwala07@gmail.com");
  });

  it("carries the link", () => {
    expect(inviteMessage(base)).toContain(
      "https://podcast-factory.safinaverse.com",
    );
  });

  it("points them at the About page, built from the same base address", () => {
    // Not a second hardcoded host. The About page is behind the sign-in, which
    // is why the sentence around it says "once you're in" — the gate carries the
    // destination through Google and returns them there.
    expect(inviteMessage(base)).toContain(
      "https://podcast-factory.safinaverse.com/about",
    );
  });

  it("does not produce a double slash when the site address has a trailing one", () => {
    const msg = inviteMessage({ ...base, siteUrl: "https://example.com/" });
    expect(msg).toContain("https://example.com/about");
    expect(msg).not.toContain("example.com//about");
  });

  it("takes the site address from its caller rather than hardcoding one", () => {
    const local = inviteMessage({ ...base, siteUrl: "http://localhost:5273" });
    expect(local).toContain("http://localhost:5273");
    expect(local).toContain("http://localhost:5273/about");
    expect(local).not.toContain("safinaverse");
  });

  it("mentions there's something to explore once they have any access", () => {
    expect(inviteMessage(base)).toContain(
      "There are several books and sessions available to explore once you're in.",
    );
  });

  it("says the same thing whether they hold one book or the whole library", () => {
    // The message no longer names specific titles — the line reads the same
    // for one book, several, or whole-library access, so nothing here needs
    // to change as somebody's grants change.
    const oneBook = inviteMessage(base);
    const wholeLibrary = inviteMessage({
      ...base,
      books: ["A", "B"],
      wholeLibrary: true,
    });
    expect(oneBook).toContain(
      "There are several books and sessions available to explore once you're in.",
    );
    expect(wholeLibrary).toContain(
      "There are several books and sessions available to explore once you're in.",
    );
  });

  it("omits the line entirely when they hold nothing yet", () => {
    // Rather than claiming there's something to explore when the truthful
    // state is that access comes next. This is the case that matters most
    // now: Generate message is offered for anybody selected, including
    // somebody invited a moment ago who holds nothing.
    const msg = inviteMessage({ ...base, books: [] });
    expect(msg).not.toContain("available to explore");
    // Everything else still has to be there — this is a message worth sending.
    expect(msg).toContain("mariampalejwala07@gmail.com");
    expect(msg).toContain("https://podcast-factory.safinaverse.com/about");
  });

  it("falls back to the address when no name was recorded", () => {
    // Inventing a name would be worse, and the administrator sees the message
    // before sending it.
    expect(inviteMessage({ ...base, displayName: base.email })).toContain(
      `Salaam ${base.email}`,
    );
  });

  it("is plain text — it survives being pasted anywhere", () => {
    // No markdown, no HTML. WhatsApp, Messages and a mail client each do
    // something different with markup, and this has to arrive intact in all of
    // them.
    const msg = inviteMessage(base);
    expect(msg).not.toMatch(/[<>]|\*\*|\[.+\]\(/);
  });

  it("is not hard-wrapped — the receiving app wraps it", () => {
    // Wrapping at a fixed column looked tidy in the desktop textarea and wrapped
    // a second time on a phone, leaving orphans like "work." alone on a line.
    // Paragraphs are single lines; blank lines are the only structure.
    const paragraphs = inviteMessage(base)
      .split("\n")
      .filter((l) => l.trim() !== "");
    expect(paragraphs.some((l) => l.length > 90)).toBe(true);
  });
});
