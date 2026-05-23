/**
 * Curated allowlist of standalone Arabic terms / names that don't follow
 * the `al-X` definite-article prefix or `Abu/Ibn X` compound patterns.
 *
 * The Arabic transliteration detector ([arabic-translit.ts]) auto-matches:
 *   - any italicised <em>...</em> with a diacritic or apostrophe
 *   - any plain-text `al-X` / `el-X` / `ad-X` / `ar-X` definite-article prefix
 *   - any plain-text `Abu X` / `Ibn X` / `Bint X` / `Umm X` name compound
 *   - words containing diacritics (ʿ ʾ ā ū ī ḥ ṣ ḍ ṭ ẓ)
 *
 * Add to ARABIC_TERMS any standalone proper noun or term that should be
 * recognised but doesn't match the above patterns. Case-sensitive match.
 *
 * Examples of what to add here: Arabic given names (Jalal), specific
 * concept terms that don't follow the al- pattern (Hayula, Tawhid, Sunnah).
 *
 * DO NOT add here: words already covered by Quran/Hadith categories, or
 * English transliterations that have entered standard English (e.g.
 * "Caliph", "Islam"). Those should stay unmarked.
 */

export const ARABIC_TERMS: readonly string[] = [
  // Concept terms
  'Allah',
  'Imam',
  'Imams',
  'Sharia',
  'Shariah',
  'Shariʿah',
  'Sharīʿa',
  'Sunna',
  'Sunnah',
  'Mahdi',
  'Khalifa',
  'Tawhid',
  'Tawḥīd',
  'Hayula',
  'Hāyūlā',
  'Mubdi',
  'Mubdiʿ',
  'Awwal',
  'Nafs',
  'Wali',
  'Walaya',
  'Hijra',
  'Daʿwa',
  'Daʿi',
  'Naqib',
  'Mizan',
  'Maʿarij',
  'Qamar',
  'Aʿraf',
  'Sufism',
  'Sufi',
  'Sufis',
  'Ismaili',
  'Ismailis',
  'Fatimid',
  'Fatimids',
  'Hanifi',
  'Hanafi',
  'Quranic',
  'Surat',
  'Surah',
  'Sura',
  'Tafsir',
  'Tafseer',
  'Hujjat',
  'Hujja',
  'Iraqayn',
  'Ajall',
  'Asas',
  'Riyad',
  // Proper names commonly appearing in kitab-al-riyad
  'Jalal',
  'Bishnaw',
  'Nadhid',
  'Yasin',
  'Taha',
  'Qutb',
  'Mathnawi',
  'Rumi',
  'Ali',
  'Hasan',
  'Husayn',
  'Husain',
  'Muhammad',
  'Ahmad',
  'Hamid',
  'Maʿadd',
  'Maʾad',
  'Shuʿayb',
  'Shu\'ayb',
  'Moses',           // appears repeatedly in scholarly translit context
  'Nuh',
  'Adam',
];

/**
 * Build a regex that matches any term in the allowlist as a whole word.
 * Sorted longest-first so multi-word entries match before their prefixes.
 */
export function buildAllowlistRegex(): RegExp {
  const sorted = [...ARABIC_TERMS].sort((a, b) => b.length - a.length);
  const escaped = sorted.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  return new RegExp(`\\b(?:${escaped.join('|')})\\b`, 'g');
}
