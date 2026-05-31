/**
 * corpus-mock-sample.ts — HARDCODED sample of the consolidated knowledge.db corpus,
 * organised CONCEPT-FIRST (the "Concept Lens" design).
 *
 * MOCK ONLY. Atom shapes mirror what the WC1 mirror-primary importers write
 * (scripts/podcast/intelligence/ingest_*.py). The novelty here is the CONCEPTS layer:
 * an English-meaningful concept (mercy / knowledge / worship …) keyed to an Arabic
 * root, aggregating evidence across every source. Concepts are derived in production
 * from atom_topic_tags + the etymology/term roots — here they are authored by hand so
 * Asif can review the UX before we build the real index.
 *
 * Full counts are the verified temp-apply result (atoms 696 -> 7036).
 */

export type AtomType = 'quran' | 'hadith' | 'term' | 'doctrine' | 'etymology' | 'poetry';
export type Tradition = 'universal' | 'fatimid-ismaili' | 'ismaili';
export type CorpusId = 'quran' | 'hadith' | 'ksessions' | 'wisdom';

export interface MockAtom {
  id: string;
  type: AtomType;
  corpus: CorpusId;
  tradition: Tradition;
  gloss: string;          // English-MEANINGFUL headline (what you read first)
  source_ref: string;     // the coordinate, shown as a small chip (Q 2:255, Bukhari, root ر-ح-م)
  arabic?: string;
  text_en: string;        // fuller searchable text
  root?: string;          // Arabic root — the cross-source spine
  concepts: string[];     // concept ids this atom belongs to
}

export interface Concept {
  id: string;
  label: string;          // English concept name
  arabic: string;
  translit: string;       // raḥma, ʿilm …
  root: string;           // ر-ح-م
  definition: string;     // one-line gloss (from the term/etymology)
  synonyms: string[];     // search aliases (English + translit variants)
  family: string[];       // related derived terms (root family)
}

export const CORPUS_TOTALS = {
  atoms: 7036,
  byType: { quran: 6236, doctrine: 628, term: 58, hadith: 77, etymology: 35, poetry: 2 } as Record<AtomType, number>,
  byTradition: { universal: 6317, 'fatimid-ismaili': 628, ismaili: 91 } as Record<Tradition, number>,
  externalCorpora: 4,
  corpusChapters: 371,
  conceptsInProduction: '~1,400 (topic tags + Arabic roots)',
  sampleConcepts: 0,
  sampleAtoms: 0,
};

export const CORPORA = [
  { id: 'quran',     display_name: 'Quran (KQUR)',          corpus_type: 'quran',     atom_count: 6236, source: 'KQUR' },
  { id: 'wisdom',    display_name: 'Kashkole Corpus',        corpus_type: 'scholarly', atom_count: 628,  source: 'KASHKOLE (binder pipeline)' },
  { id: 'hadith',    display_name: 'Hadith (KASHKOLE)',      corpus_type: 'hadith',    atom_count: 77,   source: 'KASHKOLE' },
  { id: 'ksessions', display_name: 'KSESSIONS Transcripts',  corpus_type: 'scholarly', atom_count: 0,    source: 'KSESSIONS (182 chapters; atoms deferred to WC3)' },
] as const;

export const SCHEMA_GROUPS = [
  {
    group: 'Knowledge', accent: 'knowledge',
    tables: [
      { name: 'atoms', purpose: 'The canonical referenceable unit. One row per teaching/verse/term, tradition-stamped.', cols: 'id · type · body(JSON) · tradition · first_seen_book', rows: 7036 },
      { name: 'atom_topic_tags', purpose: 'Topic tags — the raw material the Concept Lens groups by.', cols: 'atom_id · tag', rows: '—' },
      { name: 'atoms_variants', purpose: 'Alternate English renderings (dedup HIGH tier lands here, non-destructive).', cols: 'atom_id · book_slug · text_en · translator', rows: 0 },
      { name: 'external_corpora', purpose: 'Source registry — one row per corpus, live atom_count + last_synced.', cols: 'id · display_name · corpus_type · atom_count', rows: 4 },
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

export const TRADITIONS: { id: Tradition; label: string; note: string }[] = [
  { id: 'universal',       label: 'universal',       note: 'Raw scripture — Quran + hadith. Tradition-neutral, injectable into any book.' },
  { id: 'fatimid-ismaili', label: 'fatimid-ismaili', note: 'Wisdom teachings (doctrine). Only injected into same-tradition books.' },
  { id: 'ismaili',         label: 'ismaili',          note: 'Glossary terms + legacy hadith/poetry carried from the binder pipeline.' },
];

// ---- Concepts (the search/select unit) ----------------------------------------
export const CONCEPTS: Concept[] = [
  { id: 'mercy', label: 'Mercy', arabic: 'رحمة', translit: 'raḥma', root: 'ر-ح-م',
    definition: 'Mercy, compassion — the all-encompassing divine attribute that precedes wrath.',
    synonyms: ['mercy', 'compassion', 'rahma', 'rehma', 'rahman', 'rahim', 'grace', 'womb'],
    family: ['Raḥmān (Universally Merciful)', 'Raḥīm (Especially Merciful)', 'raḥim (womb)', 'marḥama'] },
  { id: 'knowledge', label: 'Knowledge', arabic: 'علم', translit: 'ʿilm', root: 'ع-ل-م',
    definition: 'Knowledge, science — to know; the first command of revelation.',
    synonyms: ['knowledge', 'ilm', 'learning', 'scholar', 'alim', 'aleem', 'known', 'wisdom'],
    family: ['ʿĀlim (knower/scholar)', 'ʿĀlam (the known/world)', 'ʿAlīm (All-Knowing)'] },
  { id: 'worship', label: 'Worship & Servitude', arabic: 'عبادة', translit: 'ʿibāda', root: 'ع-ب-د',
    definition: 'Worship, servitude — to serve; true ʿubūdiyya is freedom from all but God.',
    synonyms: ['worship', 'servitude', 'slavery', 'slave', 'servant', 'ibadah', 'ibada', 'abd', 'devotion'],
    family: ['ʿAbd (servant/slave)', 'ʿIbāda (worship)', 'ʿUbūdiyya (servitude)', 'Maʿbūd (the Worshipped)'] },
  { id: 'oneness', label: 'Divine Oneness', arabic: 'توحيد', translit: 'tawḥīd', root: 'و-ح-د',
    definition: 'The affirmation of God’s absolute oneness — the foundation of faith.',
    synonyms: ['oneness', 'tawhid', 'unity', 'monotheism', 'one', 'wahid', 'ahad'],
    family: ['Wāḥid (One)', 'Aḥad (Unique)', 'Tawḥīd (declaring oneness)'] },
  { id: 'soul', label: 'Soul & Self', arabic: 'نفس', translit: 'nafs', root: 'ن-ف-س',
    definition: 'The soul/self — that which knows itself comes to know its Lord.',
    synonyms: ['soul', 'self', 'nafs', 'self-knowledge', 'ego', 'spirit', 'breath'],
    family: ['Nafs (soul/self)', 'Nafas (breath)', 'Tanaffus (respiration)'] },
  { id: 'love', label: 'Love & Longing', arabic: 'حب', translit: 'ḥubb', root: 'ح-ب-ب',
    definition: 'Love, longing — the soul’s yearning for its origin.',
    synonyms: ['love', 'longing', 'hubb', 'mahabba', 'beloved', 'desire'],
    family: ['Ḥubb (love)', 'Maḥabba (affection)', 'Ḥabīb (beloved)'] },
];

// ---- Atoms (English-meaning-first), tagged to concepts ------------------------
export const SAMPLE_ATOMS: MockAtom[] = [
  // ── Mercy ──────────────────────────────────────────────────────────────────
  { id: 'quran:1:3', type: 'quran', corpus: 'quran', tradition: 'universal', root: 'ر-ح-م', concepts: ['mercy'],
    gloss: 'God is the Most Gracious, the Dispenser of Grace.', source_ref: 'Q 1:3', arabic: 'ٱلرَّحْمَنِ ٱلرَّحِيمِ',
    text_en: 'The Most Beneficent, the Most Merciful — Ar-Rahman, Ar-Rahim, the all-encompassing mercy and grace of God.' },
  { id: 'quran:21:107', type: 'quran', corpus: 'quran', tradition: 'universal', root: 'ر-ح-م', concepts: ['mercy'],
    gloss: 'We sent you only as a mercy to all the worlds.', source_ref: 'Q 21:107', arabic: 'وَمَآ أَرْسَلْنَكَ إِلَّا رَحْمَةًۭ لِّلْعَلَمِينَ',
    text_en: 'And We have not sent you, [O Muhammad], except as a mercy to the worlds — rahmatan lil-alamin.' },
  { id: 'hadith:mercy:1', type: 'hadith', corpus: 'hadith', tradition: 'universal', root: 'ر-ح-م', concepts: ['mercy'],
    gloss: 'My mercy prevails over my wrath.', source_ref: 'Hadith Qudsi', arabic: 'إِنَّ رَحْمَتِي تَغْلِبُ غَضَبِي',
    text_en: 'God says: My mercy prevails over my wrath — a hadith qudsi on the precedence of divine compassion.' },
  { id: 'term:kqur:rahman', type: 'term', corpus: 'quran', tradition: 'ismaili', root: 'ر-ح-م', concepts: ['mercy'],
    gloss: 'RAHMAN — the Universally Merciful.', source_ref: 'term · root ر-ح-م', arabic: 'رحمٰن',
    text_en: 'RAHMAN (root r-h-m) — the One whose mercy embraces all creation without exception; an intensive form.' },
  { id: 'etymology:rhm', type: 'etymology', corpus: 'wisdom', tradition: 'universal', root: 'ر-ح-م', concepts: ['mercy'],
    gloss: 'Root ر-ح-م — the womb that nurtures; mercy, compassion.', source_ref: 'root ر-ح-م', arabic: 'ر-ح-م',
    text_en: 'The root r-h-m yields raḥim (womb) and raḥma (mercy): the nurturing, life-giving compassion of the womb extended to the divine.' },
  { id: 'doctrine:mercy', type: 'doctrine', corpus: 'wisdom', tradition: 'fatimid-ismaili', root: 'ر-ح-م', concepts: ['mercy'],
    gloss: 'Divine mercy is the encompassing attribute that precedes and outweighs wrath.', source_ref: 'wisdom · divine attributes',
    text_en: 'In the teaching, mercy (raḥma) is not one attribute among many but the encompassing reality within which justice and wrath operate; the cosmos is held in being by it.' },

  // ── Knowledge ────────────────────────────────────────────────────────────────
  { id: 'quran:96:1', type: 'quran', corpus: 'quran', tradition: 'universal', root: 'ع-ل-م', concepts: ['knowledge'],
    gloss: 'Read in the name of your Lord who created — the command to seek knowledge.', source_ref: 'Q 96:1', arabic: 'ٱقْرَأْ بِٱسْمِ رَبِّكَ ٱلَّذِى خَلَقَ',
    text_en: 'Recite in the name of your Lord who created — the first revelation, opening with the imperative to know.' },
  { id: 'hadith:knowledge:1', type: 'hadith', corpus: 'hadith', tradition: 'universal', root: 'ع-ل-م', concepts: ['knowledge'],
    gloss: 'Seek knowledge from the cradle to the grave.', source_ref: 'Hadith', arabic: 'اطلبوا العلم من المهد إلى اللحد',
    text_en: 'Seek knowledge from the cradle to the grave — the lifelong obligation of learning.' },
  { id: 'term:kqur:alim', type: 'term', corpus: 'quran', tradition: 'ismaili', root: 'ع-ل-م', concepts: ['knowledge'],
    gloss: 'ALIM — one who has knowledge; a scholar.', source_ref: 'term · root ع-ل-م', arabic: 'عالم',
    text_en: 'ALIM (root ʿilm) — one having knowledge, a knower, a scholar. noun, adj.' },
  { id: 'term:kqur:aleem', type: 'term', corpus: 'quran', tradition: 'ismaili', root: 'ع-ل-م', concepts: ['knowledge'],
    gloss: 'ALEEM — the All-Knowing (a divine name).', source_ref: 'term · root ع-ل-م', arabic: 'عليم',
    text_en: 'ALEEM (root ʿilm) — the All-Knowing; a divine attribute denoting complete, unbounded knowledge.' },
  { id: 'etymology:ilm', type: 'etymology', corpus: 'wisdom', tradition: 'universal', root: 'ع-ل-م', concepts: ['knowledge'],
    gloss: 'Root ع-ل-م — to know; the spine of ALIM, ALAM, ALEEM.', source_ref: 'root ع-ل-م', arabic: 'ع-ل-م',
    text_en: 'The root ʿ-l-m (to know) generates ʿālim (knower), ʿālam (the known/world), and ʿalīm (All-Knowing).' },
  { id: 'doctrine:intellect', type: 'doctrine', corpus: 'wisdom', tradition: 'fatimid-ismaili', root: 'ع-ل-م', concepts: ['knowledge', 'soul'],
    gloss: 'The intellect is the ladder by which the soul ascends through knowing.', source_ref: 'wisdom · ladder of the intellect',
    text_en: 'Each act of knowing is a rung; knowledge purifies the seeker and draws the soul nearer to the First Originator.' },

  // ── Worship & Servitude ──────────────────────────────────────────────────────
  { id: 'quran:1:5', type: 'quran', corpus: 'quran', tradition: 'universal', root: 'ع-ب-د', concepts: ['worship'],
    gloss: 'You alone we worship, and You alone we ask for help.', source_ref: 'Q 1:5', arabic: 'إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ',
    text_en: 'It is You we worship and You we ask for help — the axis of servitude and reliance.' },
  { id: 'term:kqur:abd', type: 'term', corpus: 'quran', tradition: 'ismaili', root: 'ع-ب-د', concepts: ['worship'],
    gloss: 'ABD — servant, slave (of God); the root of worship.', source_ref: 'term · root ع-ب-د', arabic: 'عبد',
    text_en: 'ABD (root ʿabada) — a servant or slave; in devotion, the willing slave of God, from which ʿibāda (worship) derives.' },
  { id: 'etymology:abd', type: 'etymology', corpus: 'wisdom', tradition: 'universal', root: 'ع-ب-د', concepts: ['worship'],
    gloss: 'Root ع-ب-د — to serve, to worship; servitude as devotion.', source_ref: 'root ع-ب-د', arabic: 'ع-ب-د',
    text_en: 'The root ʿ-b-d spans ʿabd (servant), ʿibāda (worship), and ʿubūdiyya (servitude): service freely given becomes worship.' },
  { id: 'doctrine:worship', type: 'doctrine', corpus: 'wisdom', tradition: 'fatimid-ismaili', root: 'ع-ب-د', concepts: ['worship'],
    gloss: 'True servitude (ʿubūdiyya) is freedom from bondage to all but God.', source_ref: 'wisdom · servitude',
    text_en: 'The teaching inverts slavery: to be wholly the servant of God is to be freed from every lesser master — the highest liberty.' },

  // ── Divine Oneness ─────────────────────────────────────────────────────────────
  { id: 'quran:2:255', type: 'quran', corpus: 'quran', tradition: 'universal', root: 'و-ح-د', concepts: ['oneness'],
    gloss: 'None has the right to be worshipped but He, the Ever-Living, the Sustainer.', source_ref: 'Q 2:255 · Ayat al-Kursi', arabic: 'ٱللَّهُ لَآ إِلَهَ إِلَّا هُوَ ٱلْحَىُّ ٱلْقَيُّومُ',
    text_en: 'Allah — there is no deity except Him, the Ever-Living, the Sustainer of existence; neither slumber nor sleep overtakes Him.' },
  { id: 'quran:112:1', type: 'quran', corpus: 'quran', tradition: 'universal', root: 'و-ح-د', concepts: ['oneness'],
    gloss: 'Say: He is God, the One.', source_ref: 'Q 112:1', arabic: 'قُلْ هُوَ ٱللَّهُ أَحَدٌ',
    text_en: 'Say: He is Allah, [who is] One — the pure declaration of divine uniqueness.' },
  { id: 'term:kashkole:tawhid', type: 'term', corpus: 'hadith', tradition: 'ismaili', root: 'و-ح-د', concepts: ['oneness'],
    gloss: 'TAWHID — the affirmation of divine oneness.', source_ref: 'term · root و-ح-د', arabic: 'توحيد',
    text_en: 'TAWHID — to declare God one; the doctrine that God is absolutely one, without partner or division.' },
  { id: 'doctrine:islam-faith', type: 'doctrine', corpus: 'wisdom', tradition: 'fatimid-ismaili', root: 'و-ح-د', concepts: ['oneness'],
    gloss: 'The distinction between Islam (outward submission) and faith (inner assent).', source_ref: 'wisdom · mabda-wa-maad',
    text_en: '"Islam" derives from salama (to obey) — outward submission to the Messenger; faith (iman) is the heart’s inner assent to oneness.' },

  // ── Soul & Self ────────────────────────────────────────────────────────────────
  { id: 'hadith:nafs:1', type: 'hadith', corpus: 'hadith', tradition: 'universal', root: 'ن-ف-س', concepts: ['soul'],
    gloss: 'Whoever knows himself comes to know his Lord.', source_ref: 'Hadith', arabic: 'مَن عَرَفَ نَفسَهُ فَقَدْ عَرَفَ رَبَّهُ',
    text_en: 'The one who knows himself comes to know his Lord — self-knowledge as the door to knowledge of God.' },
  { id: 'doctrine:origin-return', type: 'doctrine', corpus: 'wisdom', tradition: 'fatimid-ismaili', root: 'ن-ف-س', concepts: ['soul'],
    gloss: 'Origin and Return: the soul descends from its source and ascends back through purification.', source_ref: 'wisdom · mabda-wa-maad',
    text_en: 'The soul originates in the higher world, descends into the body, and through knowledge and purification ascends to its origin (mabda wa maad).' },
  { id: 'etymology:nafs', type: 'etymology', corpus: 'wisdom', tradition: 'universal', root: 'ن-ف-س', concepts: ['soul'],
    gloss: 'Root ن-ف-س — breath, soul, self.', source_ref: 'root ن-ف-س', arabic: 'ن-ف-س',
    text_en: 'The root n-f-s links nafs (soul/self) and nafas (breath): the self as the living breath within.' },

  // ── Love & Longing ───────────────────────────────────────────────────────────
  { id: 'poetry:seeker', type: 'poetry', corpus: 'wisdom', tradition: 'ismaili', root: 'ح-ب-ب', concepts: ['love'],
    gloss: 'O seeker — each step toward the Friend is a step the Friend takes toward you.', source_ref: 'Kashkole · quatrain', arabic: '—',
    text_en: 'O seeker, the road you walk is the road that walks you; each step toward the Friend is a step the Friend takes toward you.' },
  { id: 'doctrine:love', type: 'doctrine', corpus: 'wisdom', tradition: 'fatimid-ismaili', root: 'ح-ب-ب', concepts: ['love'],
    gloss: 'Love is the soul’s longing for its origin.', source_ref: 'wisdom · longing',
    text_en: 'Love (ḥubb) is read as the gravitational pull of the soul back toward the source from which it came.' },
];

CORPUS_TOTALS.sampleConcepts = CONCEPTS.length;
CORPUS_TOTALS.sampleAtoms = SAMPLE_ATOMS.length;

/** Sample chapter paragraph for the augmentation demo (Ayyuhal Walad register). */
export const SAMPLE_PROSE = {
  book: 'Ayyuhal Walad',
  chapter: 'ch01 · Frame and First Counsel',
  paragraph:
    'Know, dear child, that knowledge without action is a tree that bears no fruit, and action without knowledge is a road walked blind. The seeker who would know his Lord must first turn inward and come to know himself, for the soul that is examined is the soul that ascends.',
};

/** Helper: atoms for a concept. */
export function atomsForConcept(conceptId: string): MockAtom[] {
  return SAMPLE_ATOMS.filter((a) => a.concepts.includes(conceptId));
}
