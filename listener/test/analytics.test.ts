import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import {
  countryCodeFromRequest,
  recordUsageActivity,
  usageDashboard,
} from "~/server/analytics.server";
import { createTestDb } from "./d1";

const SLUG = "ayyuhal-walad";
const CHAPTER = "introduction-to-the-book";
const READER = "reader@example.com";
const NOW = "2026-08-13T18:00:00.000Z";
const LATER = "2026-08-13T18:05:00.000Z";

function seed() {
  const t = createTestDb();
  t.exec(`
    INSERT INTO invite (email, email_raw, invited_by, invited_at, first_name, last_name)
      VALUES ('${READER}', '${READER}', 'admin@example.com', '${NOW}', 'Reader', 'One');
    INSERT INTO content_unit (slug, bucket, title, kind, sort_order, status)
      VALUES ('${SLUG}', 'Islamic', 'Ayyuha al-Walad', 'book', 1, 'published');
    INSERT INTO chapter (slug, anchor_key, idx, title, html, word_count)
      VALUES ('${SLUG}', '${CHAPTER}', 1, 'Introduction', '<p>x</p>', 200);
    INSERT INTO episode (slug, number, title, blurb, style, audio_key, duration_s)
      VALUES ('${SLUG}', 2, 'Counsel and Companionship', '', 'Deep dive', 'audio.m4a', 600);
  `);
  return t;
}

describe("usage analytics", () => {
  it("summarizes reading and listening activity by person, content, and country", async () => {
    const t = seed();
    try {
      await recordUsageActivity(t.db, {
        email: READER,
        slug: SLUG,
        kind: "read",
        targetKey: CHAPTER,
        countryCode: "us",
        now: NOW,
      });
      await recordUsageActivity(t.db, {
        email: READER,
        slug: SLUG,
        kind: "read",
        targetKey: CHAPTER,
        countryCode: "US",
        now: LATER,
      });
      await recordUsageActivity(t.db, {
        email: READER,
        slug: SLUG,
        kind: "listen",
        targetKey: "2",
        countryCode: "GB",
        now: LATER,
      });

      const dashboard = await usageDashboard(t.db);

      expect(dashboard.overview).toMatchObject({
        activePeople: 1,
        activeTitles: 1,
        readingSignals: 2,
        listeningSignals: 1,
        countries: 2,
        lastSeenAt: LATER,
      });
      expect(dashboard.recent.find((event) => event.kind === "listen")).toMatchObject({
        name: "Reader One",
        title: "Ayyuha al-Walad",
        countryName: "United Kingdom",
        targetTitle: "Counsel and Companionship",
      });
      expect(dashboard.people[0]).toMatchObject({
        email: READER,
        titles: 1,
        readingSignals: 2,
        listeningSignals: 1,
      });
    } finally {
      t.close();
    }
  });

  it("derives only a country code from request metadata", () => {
    const cf = Object.assign(new Request("https://example.test/"), { cf: { country: "ca" } });
    expect(countryCodeFromRequest(cf)).toBe("CA");
    expect(
      countryCodeFromRequest(new Request("https://example.test/", { headers: { "CF-IPCountry": "GB" } })),
    ).toBe("GB");
    expect(
      countryCodeFromRequest(new Request("https://example.test/", { headers: { "CF-IPCountry": "unknown" } })),
    ).toBe("XX");
  });

  it("does not add raw IP or user-agent storage", () => {
    const migration = readFileSync(
      new URL("../migrations/0015_usage_activity.sql", import.meta.url),
      "utf8",
    );
    const server = readFileSync(new URL("../app/server/analytics.server.ts", import.meta.url), "utf8");

    const schema = migration.replace(/--.*$/gm, "");
    expect(schema).not.toMatch(/\bip\b|user_agent|user-agent/i);
    expect(server).not.toMatch(/x-forwarded-for|cf-connecting-ip|user-agent/i);
  });
});
