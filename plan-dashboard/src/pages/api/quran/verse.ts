/**
 * GET /api/quran/verse?key=2:43
 *
 * Wave J (J2): local-first verse lookup.
 * 1. Try source_library_server.py at localhost:4390 (300 ms timeout).
 *    Returns: arabic, pickthall, asad, urdu, phonetic from the KQUR mirror.
 * 2. Fall back to quran.com public v4 API if local server is unreachable.
 *
 * Response shape (superset of the pre-J2 shape; new fields: asad_translation,
 * urdu_translation, phonetic):
 *   {
 *     surah_number, surah_name_en, surah_name_ar, surah_name_meaning,
 *     verse_number, verse_key, verse_range,
 *     arabic, translation, translation_source,
 *     asad_translation?,   -- Asad translation (from local mirror)
 *     urdu_translation?,   -- Urdu translation (from local mirror)
 *     phonetic?,           -- Phonetic transliteration (from local mirror)
 *     audio_url?,
 *     source: 'local' | 'quran.com'
 *   }
 */

import type { APIRoute } from "astro";
import { fetchLocalVerse } from "../../../lib/localServerClient";

export const prerender = false;

interface ChapterMeta {
  name_simple: string;
  name_arabic: string;
  translated_name?: { name: string };
}

// In-process caches — one Quran is one Quran; cache forever.
const chapterCache = new Map<number, ChapterMeta>();
const verseCache = new Map<string, any>();

async function getChapterMeta(num: number): Promise<ChapterMeta | null> {
  if (chapterCache.has(num)) return chapterCache.get(num)!;
  try {
    const res = await fetch(
      `https://api.quran.com/api/v4/chapters/${num}?language=en`,
    );
    if (!res.ok) return null;
    const data = (await res.json()) as any;
    const meta = data?.chapter as ChapterMeta;
    if (meta) chapterCache.set(num, meta);
    return meta ?? null;
  } catch {
    return null;
  }
}

export const GET: APIRoute = async ({ url }) => {
  const key = url.searchParams.get("key");
  if (!key || !/^\d+:\d+(-\d+)?$/.test(key)) {
    return new Response(
      JSON.stringify({ error: 'bad key — expected "surah:ayah" like "2:43"' }),
      { status: 400 },
    );
  }

  const cacheKey = key;
  if (verseCache.has(cacheKey)) {
    return new Response(JSON.stringify(verseCache.get(cacheKey)), {
      status: 200,
      headers: {
        "content-type": "application/json",
        "cache-control": "public, max-age=86400",
      },
    });
  }

  const firstVerse = key.split("-")[0];
  const [surahStr, ayatStr] = firstVerse.split(":");
  const surah = Number(surahStr);
  const ayat = Number(ayatStr);

  // ── Try local server first ─────────────────────────────────────────────
  const local = await fetchLocalVerse(surah, ayat);
  if (local) {
    const meta = await getChapterMeta(surah).catch(() => null);
    const out = {
      surah_number: local.surah,
      surah_name_en: meta?.name_simple ?? `Surah ${surah}`,
      surah_name_ar: meta?.name_arabic ?? "",
      surah_name_meaning: meta?.translated_name?.name ?? "",
      verse_number: local.ayat,
      verse_key: firstVerse,
      verse_range: key,
      arabic: local.arabic,
      translation: local.pickthall,
      translation_source: "Pickthall",
      asad_translation: local.asad || undefined,
      urdu_translation: local.urdu || undefined,
      phonetic: local.phonetic || undefined,
      audio_url: null,
      source: "local" as const,
    };
    verseCache.set(cacheKey, out);
    return new Response(JSON.stringify(out), {
      status: 200,
      headers: {
        "content-type": "application/json",
        "cache-control": "public, max-age=86400",
      },
    });
  }

  // ── Fall back to quran.com ─────────────────────────────────────────────
  const translation = url.searchParams.get("translation") ?? "85";
  try {
    const [vRes, tRes, meta] = await Promise.all([
      fetch(
        `https://api.quran.com/api/v4/verses/by_key/${encodeURIComponent(firstVerse)}?fields=text_uthmani,audio`,
      ),
      fetch(
        `https://api.quran.com/api/v4/quran/translations/${encodeURIComponent(translation)}?verse_key=${encodeURIComponent(firstVerse)}`,
      ),
      getChapterMeta(surah),
    ]);
    if (!vRes.ok) {
      const txt = await vRes.text();
      return new Response(
        JSON.stringify({
          error: `quran.com ${vRes.status}`,
          detail: txt.slice(0, 200),
        }),
        { status: 502 },
      );
    }
    const vData = (await vRes.json()) as any;
    const v = vData?.verse ?? {};
    let translationText = "";
    let translationSource = "Translation";
    if (tRes.ok) {
      const tData = (await tRes.json()) as any;
      const tr = (tData?.translations ?? [])[0];
      if (tr) {
        translationText = stripHtml(tr.text ?? "");
        translationSource =
          tData?.meta?.translation_name ??
          tData?.meta?.author_name ??
          "Translation";
      }
    }
    const out = {
      surah_number: surah,
      surah_name_en: meta?.name_simple ?? `Surah ${surah}`,
      surah_name_ar: meta?.name_arabic ?? "",
      surah_name_meaning: meta?.translated_name?.name ?? "",
      verse_number: Number((v.verse_key ?? firstVerse).split(":")[1]),
      verse_key: v.verse_key ?? firstVerse,
      verse_range: key,
      arabic: v.text_uthmani ?? "",
      translation: translationText,
      translation_source: translationSource,
      audio_url: v.audio?.url
        ? `https://verses.quran.com/${v.audio.url}`
        : null,
      source: "quran.com" as const,
    };
    verseCache.set(cacheKey, out);
    return new Response(JSON.stringify(out), {
      status: 200,
      headers: {
        "content-type": "application/json",
        "cache-control": "public, max-age=86400",
      },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: (e as Error).message }), {
      status: 500,
    });
  }
};

function stripHtml(s: string): string {
  return s
    .replace(/<[^>]+>/g, "")
    .replace(/\s+/g, " ")
    .trim();
}
