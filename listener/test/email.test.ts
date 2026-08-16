import { describe, expect, it } from "vitest";

import {
  hasUnfoldedPlusTag,
  normalizeEmail,
  tryNormalizeEmail,
} from "../app/server/email.server";

describe("normalizeEmail", () => {
  it("folds a Gmail alias to the address Google will actually send", () => {
    // The bug this exists to prevent: Asif types the left, Google returns the
    // right, the grant never matches, and it looks like "not granted yet".
    expect(normalizeEmail("Asif.Hussain60+listener@GoogleMail.COM")).toBe(
      "asifhussain60@gmail.com",
    );
    expect(normalizeEmail("asifhussain60@gmail.com")).toBe(
      "asifhussain60@gmail.com",
    );
  });

  it("does NOT strip dots outside Gmail", () => {
    // On a Workspace domain these can be two different people. Folding them
    // would hand one person's library to another.
    expect(normalizeEmail("first.last@company.com")).toBe(
      "first.last@company.com",
    );
    expect(normalizeEmail("firstlast@company.com")).toBe(
      "firstlast@company.com",
    );
    expect(normalizeEmail("first.last@company.com")).not.toBe(
      normalizeEmail("firstlast@company.com"),
    );
  });

  it("does NOT strip plus tags outside Gmail", () => {
    expect(normalizeEmail("a+b@example.org")).toBe("a+b@example.org");
  });

  it("rejects homographs rather than storing them", () => {
    // U+0430 CYRILLIC SMALL LETTER A, visually identical to ASCII "a".
    expect(() => normalizeEmail("аsifhussain60@gmail.com")).toThrow();
    expect(tryNormalizeEmail("аsifhussain60@gmail.com")).toBeNull();
  });

  it("folds compatibility characters before the ASCII check", () => {
    // Fullwidth Latin normalizes to ASCII under NFKC, so this is a real address
    // typed with a CJK IME rather than a spoof.
    expect(normalizeEmail("ａｂｃ@gmail.com")).toBe("abc@gmail.com");
  });

  it("lowercases and accepts the fully-qualified domain form", () => {
    expect(normalizeEmail("  Someone@Example.COM.  ")).toBe(
      "someone@example.com",
    );
  });

  it("unwraps a pasted display-name form", () => {
    expect(normalizeEmail("Asif Hussain <asifhussain60@gmail.com>")).toBe(
      "asifhussain60@gmail.com",
    );
  });

  it("rejects malformed input", () => {
    for (const bad of [
      "",
      "  ",
      "nope",
      "a@@b.com",
      "@example.com",
      "a@nodot",
      "a@.com",
    ]) {
      expect(() => normalizeEmail(bad), bad).toThrow();
    }
  });

  it("is idempotent", () => {
    const fixtures = [
      "Asif.Hussain60+listener@GoogleMail.COM",
      "first.last@company.com",
      "a+b@example.org",
      "Someone@Example.COM.",
      "asifhussain60@gmail.com",
    ];
    for (const input of fixtures) {
      const once = normalizeEmail(input);
      expect(normalizeEmail(once), input).toBe(once);
    }
  });
});

describe("hasUnfoldedPlusTag", () => {
  it("warns on a tag we keep, stays quiet on one we fold away", () => {
    expect(hasUnfoldedPlusTag("a+b@example.org")).toBe(true);
    expect(hasUnfoldedPlusTag("a+b@gmail.com")).toBe(false);
    expect(hasUnfoldedPlusTag("a@example.org")).toBe(false);
  });
});
