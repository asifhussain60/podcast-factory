import { normalizeEmail } from "./email.server";

export type UsageKind = "read" | "listen";

export interface UsageOverview {
  activePeople: number;
  activeTitles: number;
  readingSignals: number;
  listeningSignals: number;
  countries: number;
  lastSeenAt: string | null;
}

export interface UsageCountry {
  code: string;
  name: string;
  people: number;
  signals: number;
  lastSeenAt: string;
}

export interface UsageContent {
  slug: string;
  title: string;
  bucket: string;
  people: number;
  readingSignals: number;
  listeningSignals: number;
  signals: number;
  lastSeenAt: string;
}

export interface UsagePerson {
  email: string;
  name: string;
  countries: string[];
  titles: number;
  readingSignals: number;
  listeningSignals: number;
  signals: number;
  lastSeenAt: string;
}

export interface UsageRecent {
  email: string;
  name: string;
  slug: string;
  title: string;
  bucket: string;
  kind: UsageKind;
  targetKey: string;
  targetTitle: string | null;
  countryCode: string;
  countryName: string;
  lastSeenAt: string;
  signalCount: number;
}

export interface UsageRhythm {
  hour: number;
  label: string;
  signals: number;
}

export interface UsageDashboard {
  overview: UsageOverview;
  countries: UsageCountry[];
  content: UsageContent[];
  people: UsagePerson[];
  recent: UsageRecent[];
  rhythm: UsageRhythm[];
}

type RequestWithCloudflare = Request & { cf?: { country?: string } };

const UNKNOWN_COUNTRY = "XX";

export function countryCodeFromRequest(request: Request): string {
  const cfCountry = (request as RequestWithCloudflare).cf?.country;
  const headerCountry = request.headers.get("CF-IPCountry");
  const value =
    typeof cfCountry === "string" && cfCountry !== ""
      ? cfCountry
      : headerCountry;
  if (typeof value !== "string") return UNKNOWN_COUNTRY;

  const code = value.trim().toUpperCase();
  return /^[A-Z]{2}$/.test(code) ? code : UNKNOWN_COUNTRY;
}

export function countryName(code: string): string {
  if (code === UNKNOWN_COUNTRY) return "Unknown";
  try {
    return new Intl.DisplayNames(["en"], { type: "region" }).of(code) ?? code;
  } catch {
    return code;
  }
}

export async function recordUsageActivity(
  db: D1Database,
  input: {
    email: string;
    slug: string;
    kind: UsageKind;
    targetKey: string;
    countryCode: string;
    now: string;
  },
): Promise<void> {
  await db
    .prepare(
      `INSERT INTO usage_activity
              (user_email, slug, kind, target_key, country_code,
               first_seen_at, last_seen_at, signal_count)
       VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?6, 1)
       ON CONFLICT(user_email, slug, kind, target_key, country_code) DO UPDATE SET
         last_seen_at = ?6,
         signal_count = signal_count + 1`,
    )
    .bind(
      normalizeEmail(input.email),
      input.slug,
      input.kind,
      input.targetKey,
      normalizeCountryCode(input.countryCode),
      input.now,
    )
    .run();
}

export async function usageDashboard(db: D1Database): Promise<UsageDashboard> {
  const [overview, countries, content, people, recent, rhythm] =
    await Promise.all([
      usageOverview(db),
      usageCountries(db),
      usageContent(db),
      usagePeople(db),
      usageRecent(db),
      usageRhythm(db),
    ]);

  return { overview, countries, content, people, recent, rhythm };
}

async function usageOverview(db: D1Database): Promise<UsageOverview> {
  const row = await db
    .prepare(
      `SELECT count(DISTINCT user_email) AS active_people,
              count(DISTINCT slug) AS active_titles,
              coalesce(sum(CASE WHEN kind = 'read' THEN signal_count ELSE 0 END), 0)
                AS reading_signals,
              coalesce(sum(CASE WHEN kind = 'listen' THEN signal_count ELSE 0 END), 0)
                AS listening_signals,
              count(DISTINCT CASE WHEN country_code <> 'XX' THEN country_code END) AS countries,
              max(last_seen_at) AS last_seen_at
         FROM usage_activity`,
    )
    .first<{
      active_people: number;
      active_titles: number;
      reading_signals: number;
      listening_signals: number;
      countries: number;
      last_seen_at: string | null;
    }>();

  return {
    activePeople: row?.active_people ?? 0,
    activeTitles: row?.active_titles ?? 0,
    readingSignals: row?.reading_signals ?? 0,
    listeningSignals: row?.listening_signals ?? 0,
    countries: row?.countries ?? 0,
    lastSeenAt: row?.last_seen_at ?? null,
  };
}

async function usageCountries(db: D1Database): Promise<UsageCountry[]> {
  const rows = await db
    .prepare(
      `SELECT country_code, count(DISTINCT user_email) AS people,
              sum(signal_count) AS signals, max(last_seen_at) AS last_seen_at
         FROM usage_activity
        GROUP BY country_code
        ORDER BY signals DESC, people DESC, country_code
        LIMIT 12`,
    )
    .all<{
      country_code: string;
      people: number;
      signals: number;
      last_seen_at: string;
    }>();

  return rows.results.map((r) => ({
    code: r.country_code,
    name: countryName(r.country_code),
    people: r.people,
    signals: r.signals,
    lastSeenAt: r.last_seen_at,
  }));
}

async function usageContent(db: D1Database): Promise<UsageContent[]> {
  const rows = await db
    .prepare(
      `SELECT a.slug, coalesce(u.title, a.slug) AS title,
              coalesce(u.bucket, 'Library') AS bucket,
              count(DISTINCT a.user_email) AS people,
              coalesce(sum(CASE WHEN a.kind = 'read' THEN a.signal_count ELSE 0 END), 0)
                AS reading_signals,
              coalesce(sum(CASE WHEN a.kind = 'listen' THEN a.signal_count ELSE 0 END), 0)
                AS listening_signals,
              sum(a.signal_count) AS signals,
              max(a.last_seen_at) AS last_seen_at
         FROM usage_activity a
         LEFT JOIN content_unit u ON u.slug = a.slug
        GROUP BY a.slug
        ORDER BY signals DESC, people DESC, last_seen_at DESC
        LIMIT 10`,
    )
    .all<{
      slug: string;
      title: string;
      bucket: string;
      people: number;
      reading_signals: number;
      listening_signals: number;
      signals: number;
      last_seen_at: string;
    }>();

  return rows.results.map((r) => ({
    slug: r.slug,
    title: r.title,
    bucket: r.bucket,
    people: r.people,
    readingSignals: r.reading_signals,
    listeningSignals: r.listening_signals,
    signals: r.signals,
    lastSeenAt: r.last_seen_at,
  }));
}

async function usagePeople(db: D1Database): Promise<UsagePerson[]> {
  const rows = await db
    .prepare(
      `SELECT a.user_email,
              trim(coalesce(i.first_name, '') || ' ' || coalesce(i.last_name, '')) AS name,
              group_concat(DISTINCT a.country_code) AS countries,
              count(DISTINCT a.slug) AS titles,
              coalesce(sum(CASE WHEN a.kind = 'read' THEN a.signal_count ELSE 0 END), 0)
                AS reading_signals,
              coalesce(sum(CASE WHEN a.kind = 'listen' THEN a.signal_count ELSE 0 END), 0)
                AS listening_signals,
              sum(a.signal_count) AS signals,
              max(a.last_seen_at) AS last_seen_at
         FROM usage_activity a
         LEFT JOIN invite i ON i.email = a.user_email
        GROUP BY a.user_email
        ORDER BY last_seen_at DESC, signals DESC
        LIMIT 12`,
    )
    .all<{
      user_email: string;
      name: string | null;
      countries: string | null;
      titles: number;
      reading_signals: number;
      listening_signals: number;
      signals: number;
      last_seen_at: string;
    }>();

  return rows.results.map((r) => ({
    email: r.user_email,
    name: displayName(r.name, r.user_email),
    countries: (r.countries ?? "").split(",").filter(Boolean).map(countryName),
    titles: r.titles,
    readingSignals: r.reading_signals,
    listeningSignals: r.listening_signals,
    signals: r.signals,
    lastSeenAt: r.last_seen_at,
  }));
}

async function usageRecent(db: D1Database): Promise<UsageRecent[]> {
  const rows = await db
    .prepare(
      `SELECT a.user_email,
              trim(coalesce(i.first_name, '') || ' ' || coalesce(i.last_name, '')) AS name,
              a.slug, coalesce(u.title, a.slug) AS title, coalesce(u.bucket, 'Library') AS bucket,
              a.kind, a.target_key, a.country_code, a.last_seen_at, a.signal_count,
              CASE
                WHEN a.kind = 'read' THEN c.title
                WHEN a.kind = 'listen' THEN e.title
                ELSE NULL
              END AS target_title
         FROM usage_activity a
         LEFT JOIN invite i ON i.email = a.user_email
         LEFT JOIN content_unit u ON u.slug = a.slug
         LEFT JOIN chapter c
           ON c.slug = a.slug AND c.anchor_key = a.target_key AND a.kind = 'read'
         LEFT JOIN episode e
           ON e.slug = a.slug AND e.number = CAST(a.target_key AS INTEGER) AND a.kind = 'listen'
        ORDER BY a.last_seen_at DESC
        LIMIT 30`,
    )
    .all<{
      user_email: string;
      name: string | null;
      slug: string;
      title: string;
      bucket: string;
      kind: UsageKind;
      target_key: string;
      country_code: string;
      last_seen_at: string;
      signal_count: number;
      target_title: string | null;
    }>();

  return rows.results.map((r) => ({
    email: r.user_email,
    name: displayName(r.name, r.user_email),
    slug: r.slug,
    title: r.title,
    bucket: r.bucket,
    kind: r.kind,
    targetKey: r.target_key,
    targetTitle: r.target_title,
    countryCode: r.country_code,
    countryName: countryName(r.country_code),
    lastSeenAt: r.last_seen_at,
    signalCount: r.signal_count,
  }));
}

async function usageRhythm(db: D1Database): Promise<UsageRhythm[]> {
  const rows = await db
    .prepare(
      `SELECT CAST(substr(last_seen_at, 12, 2) AS INTEGER) AS hour,
              sum(signal_count) AS signals
         FROM usage_activity
        GROUP BY hour`,
    )
    .all<{ hour: number; signals: number }>();

  const byHour = new Map(rows.results.map((r) => [r.hour, r.signals]));
  return Array.from({ length: 24 }, (_, hour) => ({
    hour,
    label: hourLabel(hour),
    signals: byHour.get(hour) ?? 0,
  }));
}

function displayName(name: string | null, email: string): string {
  const trimmed = name?.trim() ?? "";
  return trimmed === "" ? email : trimmed;
}

function normalizeCountryCode(code: string): string {
  const upper = code.trim().toUpperCase();
  return /^[A-Z]{2}$/.test(upper) ? upper : UNKNOWN_COUNTRY;
}

function hourLabel(hour: number): string {
  if (hour === 0) return "12 AM";
  if (hour < 12) return `${hour} AM`;
  if (hour === 12) return "12 PM";
  return `${hour - 12} PM`;
}
