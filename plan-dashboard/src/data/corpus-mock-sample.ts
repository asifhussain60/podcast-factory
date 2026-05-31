/**
 * corpus-mock-sample.ts — HARDCODED sample of the consolidated knowledge.db corpus.
 *
 * MOCK ONLY. These are real example rows pulled from content/knowledge-base/mirror.db
 * + the live wisdom doctrine atoms, shaped exactly as the WC1 mirror-primary importers
 * write them (see scripts/podcast/intelligence/ingest_{kqur,kashkole,ksessions_dump}.py).
 * The full counts below are the verified result of a temp-copy apply (atoms 696 -> 7036).
 *
 * Purpose: let Asif eyeball the data model + search/augment UX BEFORE we apply to the
 * live tracked knowledge.db. Fix deviations here, cheaply, first.
 */

export type AtomType = 'quran' | 'hadith' | 'term' | 'doctrine' | 'etymology' | 'poetry';
export type Tradition = 'universal' | 'fatimid-ismaili' | 'ismaili';
export type CorpusId = 'quran' | 'hadith' | 'ksessions' | 'wisdom';

export interface MockAtom {
  id: string;
  type: AtomType;
  corpus: CorpusId;
  tradition: Tradition;
  title: string;          // display label (Q 1:1, ALIM, hadith theme, doctrine heading)
  text_en: string;        // the searchable English rendering
  arabic?: string;
  topic_tags: string[];
  source: string;         // KQUR | KASHKOLE | KSESSIONS | wisdom-binder
  locator?: string;       // surah:ayat, hadith_num, chapter chunk, etc.
}

/** Verified consolidated totals (temp-copy apply of the WC1 importers). */
export const CORPUS_TOTALS = {
  atoms: 7036,
  byType: { quran: 6236, doctrine: 628, term: 58, hadith: 77, etymology: 35, poetry: 2 } as Record<AtomType, number>,
  byTradition: { universal: 6317, 'fatimid-ismaili': 628, ismaili: 91 } as Record<Tradition, number>,
  externalCorpora: 4,
  corpusChapters: 371,
  sampleShown: 0, // set below
};

/** External-corpora registry rows, as written by the importers. */
export const CORPORA = [
  { id: 'quran',     display_name: 'Quran (KQUR)',          corpus_type: 'quran',     atom_count: 6236, source: 'KQUR' },
  { id: 'wisdom',    display_name: 'Kashkole Corpus',        corpus_type: 'scholarly', atom_count: 628,  source: 'KASHKOLE (binder pipeline)' },
  { id: 'hadith',    display_name: 'Hadith (KASHKOLE)',      corpus_type: 'hadith',    atom_count: 77,   source: 'KASHKOLE' },
  { id: 'ksessions', display_name: 'KSESSIONS Transcripts',  corpus_type: 'scholarly', atom_count: 0,    source: 'KSESSIONS (182 chapters; atoms deferred to WC3)' },
] as const;

/** The 16-table model, grouped — what the consolidated knowledge.db looks like. */
export const SCHEMA_GROUPS = [
  {
    group: 'Knowledge', accent: 'knowledge',
    tables: [
      { name: 'atoms', purpose: 'The canonical referenceable unit. One row per teaching/verse/term, tradition-stamped.', cols: 'id · type · body(JSON) · tradition · first_seen_book · confidence', rows: 7036 },
      { name: 'atoms_sources', purpose: 'Provenance — which book/chapter surfaced this atom (many per atom).', cols: 'atom_id · book_slug · chapter_id · locator', rows: '—' },
      { name: 'atoms_variants', purpose: 'Alternate English renderings of the same atom (dedup HIGH tier lands here, non-destructive).', cols: 'atom_id · book_slug · text_en · translator', rows: 0 },
      { name: 'atom_topic_tags', purpose: 'Topic tags for blocking + faceted retrieval.', cols: 'atom_id · tag', rows: '—' },
      { name: 'external_corpora', purpose: 'Source registry — one row per corpus, with live atom_count + last_synced.', cols: 'id · display_name · corpus_type · atom_count', rows: 4 },
      { name: 'corpus_chapters', purpose: 'Structural reference — surahs, hadith books, session transcripts.', cols: 'id · corpus_id · number · title_en · verse_count', rows: 371 },
    ],
  },
  {
    group: 'Quality / Review', accent: 'quality',
    tables: [
      { name: 'manual_review_queue', purpose: 'Dedup BORDERLINE candidates + conflicts await human curation (WC4 view).', cols: 'id · reason · payload(JSON) · resolved_at', rows: 0 },
      { name: 'knowledge_base_conflicts', purpose: 'Same canonical id, different text_ar/grade — surfaced, never auto-merged.', cols: 'atom_id · existing_body · incoming_body · resolution', rows: 0 },
    ],
  },
] as const;

/** Tradition firewall legend (D5). */
export const TRADITIONS: { id: Tradition; label: string; note: string }[] = [
  { id: 'universal',       label: 'universal',       note: 'Raw scripture — Quran + hadith. Tradition-neutral, injectable into any book.' },
  { id: 'fatimid-ismaili', label: 'fatimid-ismaili', note: 'Wisdom teachings (doctrine). Only injected into same-tradition books.' },
  { id: 'ismaili',         label: 'ismaili',          note: 'Glossary terms + legacy hadith/poetry carried from the binder pipeline.' },
];

// --- Sample atoms: real rows, shaped as the importers write them ---------------
export const SAMPLE_ATOMS: MockAtom[] = [
  // Quran (universal)
  { id: 'quran:1:1', type: 'quran', corpus: 'quran', tradition: 'universal', title: 'Q 1:1', locator: '1:1',
    arabic: 'بِسْمِ ٱللَّهِ ٱلرَّحْمَنِ ٱلرَّحِيمِ', source: 'KQUR', topic_tags: ['basmala'],
    text_en: 'In the Name of Allah, the Most Beneficent, the Most Merciful. (Asad: In the name of God, The Most Gracious, The Dispenser of Grace.)' },
  { id: 'quran:1:2', type: 'quran', corpus: 'quran', tradition: 'universal', title: 'Q 1:2', locator: '1:2',
    arabic: 'ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَلَمِينَ', source: 'KQUR', topic_tags: ['praise', 'tawhid'],
    text_en: 'All praise is due to Allah, Lord of the worlds — the Sustainer of all the worlds.' },
  { id: 'quran:2:255', type: 'quran', corpus: 'quran', tradition: 'universal', title: 'Q 2:255 (Ayat al-Kursi)', locator: '2:255',
    arabic: 'ٱللَّهُ لَآ إِلَهَ إِلَّا هُوَ ٱلْحَىُّ ٱلْقَيُّومُ', source: 'KQUR', topic_tags: ['tawhid', 'divine-attributes'],
    text_en: 'Allah! None has the right to be worshipped but He, the Ever-Living, the Sustainer of all that exists. Neither slumber nor sleep overtakes Him.' },
  { id: 'quran:96:1', type: 'quran', corpus: 'quran', tradition: 'universal', title: 'Q 96:1', locator: '96:1',
    arabic: 'ٱقْرَأْ بِٱسْمِ رَبِّكَ ٱلَّذِى خَلَقَ', source: 'KQUR', topic_tags: ['knowledge', 'revelation'],
    text_en: 'Read in the name of your Lord who created — the first revelation, the command to seek knowledge.' },

  // Terms (ismaili)
  { id: 'term:kqur:alim', type: 'term', corpus: 'quran', tradition: 'ismaili', title: 'ALIM', locator: 'root: ilm',
    arabic: 'عالم', source: 'KQUR', topic_tags: ['knowledge', 'etymology'],
    text_en: 'ALIM (root ʿilm) — one having knowledge, a scholar. noun, adj.' },
  { id: 'term:kqur:alam', type: 'term', corpus: 'quran', tradition: 'ismaili', title: 'ALAM', locator: 'root: ilm',
    arabic: 'عالَم', source: 'KQUR', topic_tags: ['cosmology', 'etymology'],
    text_en: 'ALAM (root ʿilm) — what is known, the world. noun.' },
  { id: 'term:kqur:aleem', type: 'term', corpus: 'quran', tradition: 'ismaili', title: 'ALEEM', locator: 'root: ilm',
    arabic: 'عليم', source: 'KQUR', topic_tags: ['divine-attributes', 'knowledge'],
    text_en: 'ALEEM (root ʿilm) — the All-Knowing; a divine attribute.' },
  { id: 'term:kashkole:tawhid', type: 'term', corpus: 'hadith', tradition: 'ismaili', title: 'TAWHID', locator: 'root: w-h-d',
    arabic: 'توحيد', source: 'KASHKOLE', topic_tags: ['tawhid', 'theology'],
    text_en: 'TAWHID — the affirmation of divine oneness; the doctrine that God is absolutely one.' },

  // Hadith (universal — raw)
  { id: 'hadith:kashkole:14', type: 'hadith', corpus: 'hadith', tradition: 'universal', title: 'On self-knowledge', locator: 'theme: soul',
    arabic: 'مَن عَرَفَ نَفسَہُ فَقَدْ عَرَفَ رَبَّہُ', source: 'KASHKOLE', topic_tags: ['self-knowledge', 'soul'],
    text_en: 'The one who knows himself comes to know his Lord.' },
  { id: 'hadith:kashkole:9', type: 'hadith', corpus: 'hadith', tradition: 'ismaili', title: 'On seeking knowledge', locator: 'theme: knowledge',
    arabic: 'اطلبوا العلم', source: 'wisdom-binder', topic_tags: ['knowledge'],
    text_en: 'Seek knowledge from the cradle to the grave. (Pre-existing atom — preserved as ismaili by INSERT OR IGNORE.)' },
  { id: 'hadith:kashkole:500', type: 'hadith', corpus: 'hadith', tradition: 'universal', title: 'On intention', locator: 'theme: deeds',
    arabic: 'إنما الأعمال بالنيات', source: 'KASHKOLE', topic_tags: ['deeds', 'ethics'],
    text_en: 'Actions are but by intentions, and every person will have only what they intended.' },

  // Doctrine (fatimid-ismaili) — real wisdom atoms
  { id: 'doctrine:wisdom:28:119:1', type: 'doctrine', corpus: 'wisdom', tradition: 'fatimid-ismaili', title: 'The Distinction Between Islam and Faith', locator: 'musawwadat · mabda-wa-maad',
    source: 'wisdom-binder', topic_tags: ['islam', 'faith', 'eschatology'],
    text_en: 'The word "Islam" derives from salama (to obey), signifying submission to the words of the Messenger and obedience to his commandments, whereas faith (iman) is the inner assent of the heart.' },
  { id: 'doctrine:wisdom:28:119:0', type: 'doctrine', corpus: 'wisdom', tradition: 'fatimid-ismaili', title: 'Origin and Return', locator: 'musawwadat · mabda-wa-maad',
    source: 'wisdom-binder', topic_tags: ['cosmology', 'origin-and-return'],
    text_en: 'Origin and Return — the phases of the heavens and the embryo: the soul descends from its origin and ascends back through knowledge and purification.' },
  { id: 'doctrine:wisdom:12:143:0', type: 'doctrine', corpus: 'wisdom', tradition: 'fatimid-ismaili', title: 'The Ladder of the Intellect', locator: 'binder 12 · ch 143',
    source: 'wisdom-binder', topic_tags: ['intellect', 'soul', 'ascent'],
    text_en: 'The intellect is the ladder by which the soul ascends; each rung is an act of knowing that purifies the seeker and draws them nearer to the First Originator.' },

  // Etymology (universal)
  { id: 'etymology:ahd', type: 'etymology', corpus: 'wisdom', tradition: 'universal', title: 'ʿAHD (covenant)', locator: 'root: ʿ-h-d',
    arabic: 'عهد', source: 'wisdom-binder', topic_tags: ['covenant', 'etymology'],
    text_en: 'ʿAHD — covenant, pledge, era. The root carries the sense of a binding promise renewed across time.' },
  { id: 'etymology:ilm', type: 'etymology', corpus: 'wisdom', tradition: 'universal', title: 'ʿILM (knowledge)', locator: 'root: ʿ-l-m',
    arabic: 'علم', source: 'wisdom-binder', topic_tags: ['knowledge', 'etymology'],
    text_en: 'ʿILM — knowledge, science. The root underlies ALIM (knower), ALAM (world), and ALEEM (All-Knowing).' },

  // Poetry (ismaili)
  { id: 'poetry:kashkole:1355', type: 'poetry', corpus: 'wisdom', tradition: 'ismaili', title: 'Quatrain on the Seeker', locator: 'kashkole 1355',
    arabic: '—', source: 'KASHKOLE', topic_tags: ['seeker', 'longing'],
    text_en: 'O seeker, the road you walk is the road that walks you; / each step toward the Friend is a step the Friend takes toward you.' },
];

CORPUS_TOTALS.sampleShown = SAMPLE_ATOMS.length;

/** A sample chapter paragraph for the augmentation demo (Ayyuhal Walad register). */
export const SAMPLE_PROSE = {
  book: 'Ayyuhal Walad',
  chapter: 'ch01 · Frame and First Counsel',
  paragraph:
    'Know, dear child, that knowledge without action is a tree that bears no fruit, and action without knowledge is a road walked blind. The seeker who would know his Lord must first turn inward and come to know himself, for the soul that is examined is the soul that ascends.',
};
