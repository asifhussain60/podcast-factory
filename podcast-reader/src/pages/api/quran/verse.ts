/**
 * GET /api/quran/verse?key=2:43&translation=131
 *
 * Server proxy to quran.com's public v4 API. Returns a compact JSON
 * shape tailored to the popover:
 *
 *   {
 *     surah_number: number,
 *     surah_name_en: string,
 *     surah_name_ar: string,
 *     surah_name_meaning: string,
 *     verse_number: number,
 *     arabic: string,                 // uthmani script
 *     translation: string,
 *     translation_source: string,
 *     audio_url?: string,
 *   }
 *
 * Default translation is 85 (M.A.S. Abdel Haleem — modern, literary).
 * Override via ?translation=20 (Saheeh International) etc.
 * In-process cache means repeat lookups within a server lifetime are
 * instant. Browser-side cache (localStorage) further suppresses calls
 * across page loads.
 */

import type { APIRoute } from 'astro';

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
    const res = await fetch(`https://api.quran.com/api/v4/chapters/${num}?language=en`);
    if (!res.ok) return null;
    const data = await res.json() as any;
    const meta = data?.chapter as ChapterMeta;
    if (meta) chapterCache.set(num, meta);
    return meta ?? null;
  } catch { return null; }
}

export const GET: APIRoute = async ({ url }) => {
  const key = url.searchParams.get('key');
  const translation = url.searchParams.get('translation') ?? '85';
  if (!key || !/^\d+:\d+(-\d+)?$/.test(key)) {
    return new Response(JSON.stringify({ error: 'bad key — expected "surah:ayah" like "2:43"' }), { status: 400 });
  }

  const cacheKey = `${key}/${translation}`;
  if (verseCache.has(cacheKey)) {
    return new Response(JSON.stringify(verseCache.get(cacheKey)), {
      status: 200,
      headers: { 'content-type': 'application/json', 'cache-control': 'public, max-age=86400' },
    });
  }

  // Handle ranges by fetching the first verse — popover shows the start of the range.
  const firstVerse = key.split('-')[0];
  const [surahStr] = firstVerse.split(':');
  const surah = Number(surahStr);

  try {
    const [vRes, tRes, meta] = await Promise.all([
      fetch(`https://api.quran.com/api/v4/verses/by_key/${encodeURIComponent(firstVerse)}?fields=text_uthmani,audio`),
      fetch(`https://api.quran.com/api/v4/quran/translations/${encodeURIComponent(translation)}?verse_key=${encodeURIComponent(firstVerse)}`),
      getChapterMeta(surah),
    ]);
    if (!vRes.ok) {
      const txt = await vRes.text();
      return new Response(JSON.stringify({ error: `quran.com ${vRes.status}`, detail: txt.slice(0, 200) }), { status: 502 });
    }
    const vData = await vRes.json() as any;
    const v = vData?.verse ?? {};
    let translationText = '';
    let translationSource = 'Translation';
    if (tRes.ok) {
      const tData = await tRes.json() as any;
      const tr = (tData?.translations ?? [])[0];
      if (tr) {
        translationText = stripHtml(tr.text ?? '');
        translationSource = tData?.meta?.translation_name ?? tData?.meta?.author_name ?? 'Translation';
      }
    }
    const out = {
      surah_number: surah,
      surah_name_en: meta?.name_simple ?? `Surah ${surah}`,
      surah_name_ar: meta?.name_arabic ?? '',
      surah_name_meaning: meta?.translated_name?.name ?? '',
      verse_number: Number((v.verse_key ?? firstVerse).split(':')[1]),
      verse_key: v.verse_key ?? firstVerse,
      verse_range: key,
      arabic: v.text_uthmani ?? '',
      translation: translationText,
      translation_source: translationSource,
      audio_url: v.audio?.url ? `https://verses.quran.com/${v.audio.url}` : null,
    };
    verseCache.set(cacheKey, out);
    return new Response(JSON.stringify(out), {
      status: 200,
      headers: { 'content-type': 'application/json', 'cache-control': 'public, max-age=86400' },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: (e as Error).message }), { status: 500 });
  }
};

function stripHtml(s: string): string {
  // Translation text often has footnote markers like <sup>...</sup>.
  // Strip tags but preserve content. Also collapse footnote refs like [1].
  return s.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
}
