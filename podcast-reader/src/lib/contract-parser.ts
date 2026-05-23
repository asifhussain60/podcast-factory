/**
 * Parse a chapter-contract YAML file into a structured render model.
 *
 * The model is intentionally tolerant — the YAML schema across kitab-al-riyad
 * contracts has minor variations (some fields null, some absent, some are
 * strings vs arrays). The parser normalises to one shape so the renderer
 * doesn't carry conditional logic for every field.
 */

import { readFile } from 'node:fs/promises';
import { load as yamlLoad } from 'js-yaml';

export interface AnchorPassage {
  text: string;
  // optional structured fields if we ever start emitting them in the YAML
  cite?: string;
}

export interface ShowNotes {
  blurb?: string;
  bullets?: string[];
  keywords?: string[];
  raw?: Record<string, unknown>;
}

export interface ChapterContract {
  // identity
  chapterRef: string;
  slug: string;
  bookSlug: string;
  episodeNumber: number | null;
  sourceChapterRef: string | null;
  sectionIndex: number | null;
  title: string;

  // editorial framing
  audience: string;
  angle: string | null;
  episodeFormat: string | null;
  hostDynamic: string | null;
  hostDynamicCustom: string | null;
  debate: string | null;
  lengthTarget: string | null;
  adaptationMode: string | null;

  // body
  keyTensions: string[];
  toneConstraints: string[];
  anchorPassages: AnchorPassage[];

  // ancillary
  phoneticOverrides: Record<string, string>;
  showNotes: ShowNotes;

  // catchall
  raw: Record<string, unknown>;
}

function asString(value: unknown, fallback = ''): string {
  if (typeof value === 'string') return value;
  if (typeof value === 'number') return String(value);
  return fallback;
}

function asNullableString(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === 'string') return value.length > 0 ? value : null;
  if (typeof value === 'number') return String(value);
  return null;
}

function asNullableNumber(value: unknown): number | null {
  if (typeof value === 'number') return value;
  if (typeof value === 'string' && /^\d+$/.test(value)) return Number(value);
  return null;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((v) => (typeof v === 'string' ? v : null))
    .filter((v): v is string => v !== null);
}

function asAnchorPassages(value: unknown): AnchorPassage[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((v): AnchorPassage | null => {
      if (typeof v === 'string') return { text: v };
      if (v && typeof v === 'object') {
        const obj = v as Record<string, unknown>;
        const text = asString(obj.text ?? obj.passage ?? obj.quote);
        if (!text) return null;
        const cite = asNullableString(obj.cite ?? obj.citation ?? obj.source) ?? undefined;
        return { text, cite };
      }
      return null;
    })
    .filter((v): v is AnchorPassage => v !== null);
}

function asShowNotes(value: unknown): ShowNotes {
  if (!value || typeof value !== 'object') return {};
  const obj = value as Record<string, unknown>;
  return {
    blurb: asNullableString(obj.blurb) ?? undefined,
    bullets: asStringArray(obj.bullets),
    keywords: asStringArray(obj.keywords),
    raw: obj,
  };
}

function asStringRecord(value: unknown): Record<string, string> {
  if (!value || typeof value !== 'object') return {};
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(value)) {
    if (typeof v === 'string') out[k] = v;
  }
  return out;
}

export async function loadChapterContract(filePath: string): Promise<ChapterContract> {
  const raw = await readFile(filePath, 'utf-8');
  return parseChapterContractFromString(raw);
}

export function parseChapterContractFromString(text: string): ChapterContract {
  const parsed = (yamlLoad(text) as Record<string, unknown> | null) ?? {};

  return {
    chapterRef: asString(parsed.chapter_ref),
    slug: asString(parsed.slug),
    bookSlug: asString(parsed.book_slug),
    episodeNumber: asNullableNumber(parsed.episode_number),
    sourceChapterRef: asNullableString(parsed.source_chapter_ref),
    sectionIndex: asNullableNumber(parsed.section_index),
    title: asString(parsed.title) || asString(parsed.slug),

    audience: asString(parsed.audience),
    angle: asNullableString(parsed.angle),
    episodeFormat: asNullableString(parsed.episode_format),
    hostDynamic: asNullableString(parsed.host_dynamic),
    hostDynamicCustom: asNullableString(parsed.host_dynamic_custom),
    debate: asNullableString(parsed.debate),
    lengthTarget: asNullableString(parsed.length_target),
    adaptationMode: asNullableString(parsed.adaptation_mode),

    keyTensions: asStringArray(parsed.key_tensions),
    toneConstraints: asStringArray(parsed.tone_constraints),
    anchorPassages: asAnchorPassages(parsed.anchor_passages),

    phoneticOverrides: asStringRecord(parsed.phonetic_overrides),
    showNotes: asShowNotes(parsed.show_notes),

    raw: parsed,
  };
}
