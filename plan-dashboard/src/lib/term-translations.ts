/**
 * term-translations.ts — known English/biblical equivalents for Arabic and
 * Islamic transliterated terms used in the pre-upload Replace workflow.
 *
 * Keys are normalised to lowercase with diacritics stripped. The lookup
 * function handles case and common prefix variants (al-, ibn-, etc.).
 *
 * Coverage: Quranic prophets, archangels, common Ismaili theological terms,
 * and Asas al-Taweel vol-01 specific terms.
 */

export interface Translation {
  english: string;
  note?: string;
}

const RAW: Record<string, Translation> = {
  // ── Quranic prophets (Islamic name → biblical English) ───────────────────
  'adam':       { english: 'Adam' },
  'hawa':       { english: 'Eve',       note: 'wife of Adam' },
  'hawwa':      { english: 'Eve' },
  'idris':      { english: 'Enoch',     note: 'antediluvian prophet' },
  'nuh':        { english: 'Noah' },
  'hud':        { english: 'Hud',       note: 'prophet to Aad — no biblical equivalent' },
  'salih':      { english: 'Saleh',     note: 'prophet to Thamud — no direct biblical name' },
  'ibrahim':    { english: 'Abraham' },
  'lut':        { english: 'Lot' },
  'ismail':     { english: 'Ishmael' },
  'ishaq':      { english: 'Isaac' },
  'yaqub':      { english: 'Jacob' },
  'yusuf':      { english: 'Joseph' },
  'shuayb':     { english: 'Jethro',    note: 'father-in-law of Moses in some traditions' },
  'musa':       { english: 'Moses' },
  'harun':      { english: 'Aaron' },
  'khidr':      { english: 'the Green One', note: 'mysterious guide-figure' },
  'dawud':      { english: 'David' },
  'sulaiman':   { english: 'Solomon' },
  'ilyas':      { english: 'Elijah' },
  'alyasa':     { english: 'Elisha' },
  'yunus':      { english: 'Jonah' },
  'zakariyya':  { english: 'Zechariah' },
  'yahya':      { english: 'John',      note: 'John the Baptist' },
  'isa':        { english: 'Jesus' },
  'maryam':     { english: 'Mary',      note: 'mother of Jesus' },
  'muhammad':   { english: 'Muhammad',  note: 'no English equivalent — keep as is' },

  // ── Archangels ────────────────────────────────────────────────────────────
  'jibrail':    { english: 'Gabriel' },
  'jibril':     { english: 'Gabriel' },
  'mikail':     { english: 'Michael' },
  'mikaeel':    { english: 'Michael' },
  'israfil':    { english: 'Raphael',   note: 'angel of the trumpet; identified with Raphael in some traditions' },
  'izrail':     { english: 'Azrael',    note: 'angel of death' },

  // ── Common theological terms ──────────────────────────────────────────────
  'sunna':      { english: 'prophetic tradition' },
  'sunnah':     { english: 'prophetic tradition' },
  'hadith':     { english: 'prophetic report' },
  'sharia':     { english: 'divine law' },
  'tawil':      { english: 'esoteric interpretation' },
  'tafsir':     { english: 'Quranic commentary' },
  'zahir':      { english: 'the exoteric' },
  'al-zahir':   { english: 'the exoteric' },
  'batin':      { english: 'the esoteric' },
  'al-batin':   { english: 'the esoteric' },
  'dhikr':      { english: 'remembrance' },
  'dua':        { english: 'supplication' },
  'zakat':      { english: 'almsgiving' },
  'hijab':      { english: 'veil' },
  'aqida':      { english: 'creed' },
  'ummah':      { english: 'community of believers' },
  'khalifa':    { english: 'caliph' },
  'khilafa':    { english: 'caliphate' },
  'jihad':      { english: 'struggle' },
  'taqiyya':    { english: 'precautionary dissimulation' },
  'quran':      { english: 'Quran' },
  'al-shaytan': { english: 'Satan' },
  'shaytan':    { english: 'Satan' },
  'iblis':      { english: 'Iblis',     note: 'proper name of the devil — keep as is or use "Satan"' },

  // ── Ismaili-specific terms ────────────────────────────────────────────────
  'natiq':      { english: 'Speaker-Prophet' },
  'asas':       { english: 'Foundation' },
  'wasi':       { english: 'Executor' },
  'hujja':      { english: 'Proof' },
  'hujjat':     { english: 'Proof' },
  'al-hujaj':   { english: 'the Proofs' },
  "da'i":       { english: 'Summoner' },
  'dai':        { english: 'Summoner' },
  "al-du'at":   { english: 'the Summoners' },
  'al-duat':    { english: 'the Summoners' },
  'imam':       { english: 'Imam',      note: 'context-dependent — often left untranslated' },
  'walaya':     { english: 'devotion to the Imam' },
  'wali':       { english: 'guardian' },
  'bab':        { english: 'Gate' },
  'mustajib':   { english: 'Respondent' },
  'mutim':      { english: 'Feeder' },
  'mazun':      { english: 'Licentiate' },
  'muassis':    { english: 'Founder' },

  // ── Asas al-Taweel vol-01 specific ───────────────────────────────────────
  'ismailiyya': { english: 'the Ismaili community' },
  "ka'ba":      { english: 'Kaaba' },
  'kaaba':      { english: 'Kaaba' },
  'al-husayn':  { english: 'al-Husayn',  note: 'grandson of the Prophet — name kept in Islamic contexts' },
  'al-wafayat': { english: 'Obituaries', note: 'short title of Ibn Khallikan\'s biographical dictionary' },
  'raf al-isr': { english: 'Lifting of the Burden' },
  "raf' al-isr":{ english: 'Lifting of the Burden' },
  'dhikr al-muqaddimat': { english: 'Introduction' },
};

/** Normalise a term string for lookup. */
function normalise(term: string): string {
  return term
    .toLowerCase()
    .replace(/[؀-ۿ]/g, '')   // strip Arabic script if present
    .replace(/[''ʿʾ]/g, "'")           // normalise apostrophes
    .replace(/[āáàâ]/g, 'a')
    .replace(/[īíì]/g, 'i')
    .replace(/[ūúù]/g, 'u')
    .replace(/ḥ/g, 'h').replace(/ṭ/g, 't').replace(/ṣ/g, 's')
    .replace(/ḍ/g, 'd').replace(/ẓ/g, 'z').replace(/ġ/g, 'gh')
    .trim();
}

/**
 * Look up the English equivalent for an Arabic/Islamic term.
 * Returns the translation if found, or null if the term is unknown.
 */
export function lookupTranslation(term: string): Translation | null {
  const key = normalise(term);
  if (RAW[key]) return RAW[key];

  // Try stripping the definite article al- prefix
  const stripped = key.replace(/^al-/, '');
  if (RAW[stripped]) return RAW[stripped];

  // Try with al- prefix added
  const withAl = 'al-' + key;
  if (RAW[withAl]) return RAW[withAl];

  return null;
}
