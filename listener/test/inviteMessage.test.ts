import { describe, expect, it } from "vitest";

import { inviteMessage } from "../app/lib/inviteMessage";

/**
 * The note that goes to a real person. It is the one thing this application
 * produces that leaves it entirely — pasted into a chat, read by somebody who
 * has never seen the site — so the parts that are load-bearing are asserted:
 * the address they must sign in with, the link, and what they can open.
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
    // "Hi Mariam Palejwala" reads like a form letter, which is what this must
    // not read like.
    expect(inviteMessage(base)).toContain("Hi Mariam,");
  });

  it("names the exact address they must sign in with", () => {
    // Access is keyed on the email. Somebody who signs in with a different
    // Google account lands on the no-access page and concludes the link is
    // broken — this line is what prevents that support question.
    expect(inviteMessage(base)).toContain("mariampalejwala07@gmail.com");
  });

  it("carries the link", () => {
    expect(inviteMessage(base)).toContain("https://podcast-factory.safinaverse.com");
  });

  it("takes the site address from its caller rather than hardcoding one", () => {
    const local = inviteMessage({ ...base, siteUrl: "http://localhost:5273" });
    expect(local).toContain("http://localhost:5273");
    expect(local).not.toContain("safinaverse");
  });

  it("says what one book is", () => {
    expect(inviteMessage(base)).toContain("You can open: Degrees of Excellence");
  });

  it("joins two books with 'and', and three with commas", () => {
    expect(inviteMessage({ ...base, books: ["A", "B"] })).toContain("You can open: A and B");
    expect(inviteMessage({ ...base, books: ["A", "B", "C"] })).toContain("You can open: A, B and C");
  });

  it("says 'everything' rather than listing twenty-one titles", () => {
    const msg = inviteMessage({ ...base, books: ["A", "B"], wholeLibrary: true });
    expect(msg).toContain("You can open: everything in the library");
    expect(msg).not.toContain("A and B");
  });

  it("omits the line entirely when they hold nothing yet", () => {
    // Rather than printing "You can open:" with nothing after it, which reads as
    // a fault where the truthful state is that the books come next.
    expect(inviteMessage({ ...base, books: [] })).not.toContain("You can open:");
  });

  it("falls back to the address when no name was recorded", () => {
    // Inventing a name would be worse, and the administrator sees the message
    // before sending it.
    expect(inviteMessage({ ...base, displayName: base.email })).toContain(`Hi ${base.email},`);
  });

  it("is plain text — it survives being pasted anywhere", () => {
    // No markdown, no HTML. WhatsApp, Messages and a mail client each do
    // something different with markup, and this has to arrive intact in all of
    // them.
    const msg = inviteMessage(base);
    expect(msg).not.toMatch(/[<>]|\*\*|\[.+\]\(/);
  });
});
