import { useState } from 'react';

// ─── Types ────────────────────────────────────────────────────────────────────

type Category = 'core' | 'knowledge' | 'operations' | 'quality';

interface Field {
  name: string;
  type: string;
  description: string;
  pk?: boolean;
  fk?: string;
  nullable?: boolean;
}

interface TableNode {
  id: string;
  label: string;
  category: Category;
  purpose: string;
  wave: number;
  writtenBy: string[];
  readBy: string[];
  fields: Field[];
  x: number;
  y: number;
}

interface Edge {
  from: string;
  to: string;
  type: '1:N' | 'N:M' | '1:1';
  path: string;
  dashed?: boolean;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const W = 140;
const H = 36;

const CAT_COLOR: Record<Category, string> = {
  core:       '#8b4513',
  knowledge:  '#b8860b',
  operations: '#0078d4',
  quality:    '#4a7c4a',
};

const CAT_BG: Record<Category, string> = {
  core:       'rgba(139,69,19,0.08)',
  knowledge:  'rgba(184,134,11,0.08)',
  operations: 'rgba(0,120,212,0.08)',
  quality:    'rgba(74,124,74,0.08)',
};

const CAT_LABEL: Record<Category, string> = {
  core: 'Core pipeline',
  knowledge: 'Knowledge store',
  operations: 'Operations',
  quality: 'Quality audit',
};

const WAVE_LABEL: Record<number, string> = {
  1: 'Wave 1 — current',
  2: 'Wave 2 — planned',
  3: 'Wave 3 — future',
};

// ─── Table definitions ────────────────────────────────────────────────────────

const TABLES: TableNode[] = [
  {
    id: 'books',
    label: 'books',
    category: 'core',
    purpose:
      'Central registry — one row per book the factory has ever touched. Every other table points back here. Replaces the per-book orchestrator-state.json files scattered across content/drafts/.',
    wave: 1,
    writtenBy: ['0a-ingest', 'finalize'],
    readBy: ['every phase', 'dashboard', 'publish'],
    x: 260, y: 12,
    fields: [
      { name: 'slug',            type: 'TEXT',    pk: true,                  description: 'Kebab-case book identifier — matches the git branch suffix and content/drafts/ folder name.' },
      { name: 'title_en',        type: 'TEXT',                               description: 'English title.' },
      { name: 'title_ar',        type: 'TEXT',    nullable: true,            description: 'Arabic title in Unicode script.' },
      { name: 'author',          type: 'TEXT',    nullable: true,            description: 'Author display name.' },
      { name: 'category',        type: 'TEXT',                               description: "Content category: 'book' | 'lecture' | 'article' | 'letter' | 'interview'." },
      { name: 'branch',          type: 'TEXT',                               description: "Full git branch name, e.g. 'book/kitab-al-riyad'." },
      { name: 'source_language', type: 'TEXT',                               description: "Source language: 'ar' | 'ur' | 'en'." },
      { name: 'pipeline_phase',  type: 'TEXT',                               description: 'Currently running (or last completed) orchestrator phase slug.' },
      { name: 'phase_status',    type: 'TEXT',                               description: "Execution state: 'running' | 'done' | 'halted' | 'failed'." },
      { name: 'episode_count',   type: 'INTEGER', nullable: true,            description: 'Total published episodes; null until finalization.' },
      { name: 'published_at',    type: 'TEXT',    nullable: true,            description: 'ISO-8601 timestamp when the book was shipped to the published catalog.' },
      { name: 'created_at',      type: 'TEXT',                               description: 'ISO-8601 intake timestamp.' },
    ],
  },
  {
    id: 'chapters',
    label: 'chapters',
    category: 'core',
    purpose:
      'One row per authored chapter — the atomic unit that Claude writes, the challenger criticises, and the auditor validates. Replaces the flat files under content/drafts/<slug>/chapters/.',
    wave: 1,
    writtenBy: ['per-chapter'],
    readBy: ['0g-audit', '0h-knowledge-extract', 'finalize'],
    x: 20, y: 112,
    fields: [
      { name: 'id',                type: 'TEXT',    pk: true,                  description: "Composite key: '<book_slug>:ch<n>'." },
      { name: 'book_slug',         type: 'TEXT',    fk: 'books.slug',          description: 'Parent book.' },
      { name: 'chapter_num',       type: 'INTEGER',                            description: 'Sequential number within the book.' },
      { name: 'slug',              type: 'TEXT',                               description: "Short name: 'ch01-prologue'." },
      { name: 'title',             type: 'TEXT',                               description: 'Chapter title as authored by Claude.' },
      { name: 'word_count',        type: 'INTEGER', nullable: true,            description: 'Approximate word count of final chapter text.' },
      { name: 'challenger_passes', type: 'INTEGER',                            description: 'How many critic-loop rounds this chapter went through before passing.' },
      { name: 'final_verdict',     type: 'TEXT',    nullable: true,            description: "'SHIP-READY' | 'SHIP-WITH-CAUTION' | 'BLOCKED'." },
      { name: 'created_at',        type: 'TEXT',                               description: 'ISO-8601 — first authored.' },
      { name: 'updated_at',        type: 'TEXT',                               description: 'ISO-8601 — last modification.' },
    ],
  },
  {
    id: 'episodes',
    label: 'episodes',
    category: 'core',
    purpose:
      'Published podcast episodes — the final artifact that listeners hear. Maps each chapter to its NotebookLM notebook and tracks the publish verdict.',
    wave: 1,
    writtenBy: ['finalize'],
    readBy: ['publish', 'dashboard'],
    x: 20, y: 216,
    fields: [
      { name: 'id',                  type: 'TEXT',    pk: true,               description: "Composite key: '<book_slug>:EP<n>'." },
      { name: 'book_slug',           type: 'TEXT',    fk: 'books.slug',       description: 'Parent book.' },
      { name: 'chapter_id',          type: 'TEXT',    fk: 'chapters.id',      description: 'Source chapter this episode is built from.' },
      { name: 'ep_num',              type: 'INTEGER',                          description: 'Episode number within the series.' },
      { name: 'title',               type: 'TEXT',                             description: 'Episode title.' },
      { name: 'notebooklm_url',      type: 'TEXT',    nullable: true,          description: 'NotebookLM notebook URL for this episode.' },
      { name: 'challenger_verdict',  type: 'TEXT',    nullable: true,          description: "'SHIP-READY' | 'SHIP-WITH-CAUTION' — quality gate result before shipping." },
      { name: 'published_at',        type: 'TEXT',    nullable: true,          description: 'ISO-8601 — when the episode went live.' },
    ],
  },
  {
    id: 'phonetics',
    label: 'phonetics',
    category: 'core',
    purpose:
      'Shared pronunciation registry for Arabic and Islamic terms. Global terms come from content/_shared/arabic/; per-book overrides live alongside them. Used when building episode text for NotebookLM.',
    wave: 1,
    writtenBy: ['0c-phonetic'],
    readBy: ['per-chapter', '0g-audit', 'build_episode_txt'],
    x: 20, y: 320,
    fields: [
      { name: 'id',               type: 'INTEGER', pk: true,               description: 'Auto-increment primary key.' },
      { name: 'term',             type: 'TEXT',                             description: "The term as it appears in English prose, e.g. 'Allah'." },
      { name: 'phonetic',         type: 'TEXT',                             description: "NotebookLM pronunciation guide, e.g. 'Ah-LAH'." },
      { name: 'transliteration',  type: 'TEXT',                             description: "Scholarly transliteration, e.g. 'Allāh'." },
      { name: 'arabic_script',    type: 'TEXT',    nullable: true,          description: "Unicode Arabic, e.g. 'الله'." },
      { name: 'scope',            type: 'TEXT',                             description: "'global' (shared manifest) | '<book_slug>' (per-book override)." },
      { name: 'book_slug',        type: 'TEXT',    nullable: true,  fk: 'books.slug', description: 'Set only for per-book overrides; null for global terms.' },
      { name: 'created_at',       type: 'TEXT',                             description: 'ISO-8601.' },
    ],
  },
  {
    id: 'knowledge_atoms',
    label: 'knowledge_atoms',
    category: 'knowledge',
    purpose:
      'Cross-book intelligence store — one row per Quran verse or hadith extracted across all processed books. Later books query this to enrich their own chapters. Supersedes the JSONL files in content/knowledge-base/ for queryable access.',
    wave: 1,
    writtenBy: ['0h-knowledge-extract'],
    readBy: ['0e-enrich', 'per-chapter', '0g-audit', 'augmenter'],
    x: 260, y: 127,
    fields: [
      { name: 'id',             type: 'TEXT',    pk: true,               description: "Canonical identifier: 'quran:2:255' | 'hadith:bukhari:1234'." },
      { name: 'type',           type: 'TEXT',                             description: "'quran' | 'hadith' | 'quote' | 'definition' | 'etymology' — Wave 1 ships quran + hadith only." },
      { name: 'wave',           type: 'INTEGER',                          description: 'Intelligence wave that introduced this atom type: 1 (now), 2 (planned), or 3 (future).' },
      { name: 'first_seen_book',    type: 'TEXT', fk: 'books.slug',      description: 'First book to surface this atom.' },
      { name: 'first_seen_chapter', type: 'TEXT', fk: 'chapters.id',    description: 'First chapter to surface it.' },
      { name: 'first_seen_date',    type: 'TEXT',                         description: 'ISO-8601.' },
      { name: 'citation_count', type: 'INTEGER',                          description: 'Running count of unique book+chapter pairs that cite this atom. Incremented by the Librarian on every merge.' },
      { name: 'body_json',      type: 'TEXT',                             description: 'JSON blob with type-specific fields: surah/ayah/text_ar/text_en for Quran; collection/number/grade/narrator for hadith.' },
      { name: 'variants_json',  type: 'TEXT',    nullable: true,          description: 'JSON array of captured wording variations found across different books.' },
      { name: 'updated_at',     type: 'TEXT',                             description: 'ISO-8601 — last Librarian merge.' },
      { name: 'root_id',        type: 'INTEGER', fk: 'arabic_roots.root_id', nullable: true, description: 'When this atom contains a key term, links to its Arabic root entry for etymological depth. Null for atoms not yet enriched.' },
    ],
  },
  {
    id: 'atom_citations',
    label: 'atom_citations',
    category: 'knowledge',
    purpose:
      'Provenance join table — records exactly which book and chapter cited each atom. The many-to-many bridge that makes the knowledge store\'s cross-book memory auditable.',
    wave: 1,
    writtenBy: ['0h-knowledge-extract'],
    readBy: ['augmenter', '0g-audit', 'podcast-librarian'],
    x: 260, y: 231,
    fields: [
      { name: 'id',         type: 'INTEGER', pk: true,                      description: 'Auto-increment.' },
      { name: 'atom_id',    type: 'TEXT',    fk: 'knowledge_atoms.id',      description: 'The referenced atom.' },
      { name: 'book_slug',  type: 'TEXT',    fk: 'books.slug',              description: 'Book that cites this atom.' },
      { name: 'chapter_id', type: 'TEXT',    fk: 'chapters.id',             description: 'Specific chapter where the citation appears.' },
      { name: 'locator',    type: 'TEXT',                                    description: 'Heading text or paragraph number — the exact spot in the chapter.' },
      { name: 'cited_at',   type: 'TEXT',                                    description: 'ISO-8601 — extraction timestamp.' },
    ],
  },
  {
    id: 'challenger_findings',
    label: 'challenger_findings',
    category: 'quality',
    purpose:
      'Permanent quality audit ledger — every P0/P1/P2 issue surfaced by the podcast-challenger, across all books and runs. Replaces the per-book _learning/findings.jsonl files.',
    wave: 1,
    writtenBy: ['0g-audit', 'podcast-challenger'],
    readBy: ['finalize', 'publish', 'dashboard'],
    x: 260, y: 333,
    fields: [
      { name: 'id',           type: 'INTEGER', pk: true,                    description: 'Auto-increment.' },
      { name: 'book_slug',    type: 'TEXT',    fk: 'books.slug',            description: 'Book where the finding appeared.' },
      { name: 'chapter_id',   type: 'TEXT',    fk: 'chapters.id',  nullable: true, description: 'Chapter-level findings carry this; book-level findings leave it null.' },
      { name: 'ep_num',       type: 'INTEGER', nullable: true,              description: 'Episode number, if applicable.' },
      { name: 'severity',     type: 'TEXT',                                  description: "'P0' (blocks ship) | 'P1' (warning) | 'P2' (advisory)." },
      { name: 'finding_code', type: 'TEXT',                                  description: "Rule code from the challenger spec, e.g. 'R-AUTH-CANON-01'." },
      { name: 'description',  type: 'TEXT',                                  description: 'Human-readable description of the issue.' },
      { name: 'resolved',     type: 'INTEGER',                               description: 'Boolean (0 | 1) — 1 when fixed or waived.' },
      { name: 'run_id',       type: 'INTEGER', fk: 'pipeline_runs.id', nullable: true, description: 'Pipeline run that produced this finding.' },
      { name: 'created_at',   type: 'TEXT',                                  description: 'ISO-8601.' },
    ],
  },
  {
    id: 'pipeline_runs',
    label: 'pipeline_runs',
    category: 'operations',
    purpose:
      'Orchestrator execution history — every phase of every book gets a row. The ops ledger that the dashboard reads to show what\'s running, how long things took, and what failed.',
    wave: 1,
    writtenBy: ['orchestrator'],
    readBy: ['dashboard', 'finalize', 'watchdog'],
    x: 500, y: 112,
    fields: [
      { name: 'id',          type: 'INTEGER', pk: true,               description: 'Auto-increment run ID.' },
      { name: 'book_slug',   type: 'TEXT',    fk: 'books.slug',       description: 'Book being processed.' },
      { name: 'phase',       type: 'TEXT',                             description: "Phase slug: '0a-ingest' | '0e-enrich' | 'per-chapter' | '0g-audit' | 'finalize'." },
      { name: 'status',      type: 'TEXT',                             description: "'running' | 'done' | 'halted' | 'failed'." },
      { name: 'started_at',  type: 'TEXT',                             description: 'ISO-8601.' },
      { name: 'finished_at', type: 'TEXT',    nullable: true,          description: 'ISO-8601 — null while the phase is still running.' },
      { name: 'duration_sec',type: 'INTEGER', nullable: true,          description: 'Wall-clock seconds. Null while running.' },
      { name: 'error_msg',   type: 'TEXT',    nullable: true,          description: 'Last error message captured if status = failed.' },
    ],
  },
  {
    id: 'cost_ledger',
    label: 'cost_ledger',
    category: 'operations',
    purpose:
      'Per-API-call spend tracker — every Claude, Gemini, and Azure call logged with token counts and USD cost. Replaces the per-book cost-ledger.jsonl files and enables cross-book cost analytics.',
    wave: 1,
    writtenBy: ['every LLM-calling phase'],
    readBy: ['dashboard', 'cost-cap checks', 'finalize'],
    x: 500, y: 216,
    fields: [
      { name: 'id',            type: 'INTEGER', pk: true,               description: 'Auto-increment.' },
      { name: 'book_slug',     type: 'TEXT',    fk: 'books.slug',       description: 'Book being processed when the call was made.' },
      { name: 'run_id',        type: 'INTEGER', fk: 'pipeline_runs.id', nullable: true, description: 'The pipeline run that triggered this call.' },
      { name: 'ts',            type: 'TEXT',                             description: 'ISO-8601 UTC timestamp.' },
      { name: 'phase',         type: 'TEXT',                             description: 'Phase slug.' },
      { name: 'step',          type: 'TEXT',                             description: "Step within the phase, e.g. 'ch01-write'." },
      { name: 'provider',      type: 'TEXT',                             description: "'anthropic' | 'google' | 'azure'." },
      { name: 'model',         type: 'TEXT',                             description: "Model name: 'claude-opus-4-7' | 'gemini-2.0-flash' | 'azure-doc-intelligence'." },
      { name: 'input_tokens',  type: 'INTEGER',                          description: 'Prompt tokens billed.' },
      { name: 'output_tokens', type: 'INTEGER',                          description: 'Completion tokens billed.' },
      { name: 'cache_read',    type: 'INTEGER',                          description: 'Cache-read tokens (reduced cost).' },
      { name: 'cache_create',  type: 'INTEGER',                          description: 'Cache-write tokens.' },
      { name: 'cost_usd',      type: 'REAL',                             description: 'USD cost of this single API call.' },
    ],
  },
  {
    id: 'arabic_roots',
    label: 'arabic_roots',
    category: 'knowledge',
    purpose:
      'Semitic root (جذر) registry — the spine of the etymology layer. Every Arabic word derives from a 3- or 4-letter root; this table holds each unique root with its abjad numerical value pre-computed, enabling cross-book semantic queries like "show all content touching roots in the semantic field of light." Scales to the full Arabic lexicon (28 k+ roots) without schema changes.',
    wave: 2,
    writtenBy: ['0h-knowledge-extract', 'seed import'],
    readBy: ['word_etymologies', 'letter_profiles', '0e-enrich', 'per-chapter'],
    x: 500, y: 320,
    fields: [
      { name: 'root_id',            type: 'INTEGER', pk: true,                    description: 'Auto-increment primary key.' },
      { name: 'root_ar',            type: 'TEXT',                                 description: 'Root consonants in Arabic script separated by dashes, e.g. ع-ل-م. Unique constraint.' },
      { name: 'root_latin',         type: 'TEXT',                                 description: 'ALA-LC transliteration, e.g. ʿ-l-m. Used for search and display in English UI.' },
      { name: 'root_type',          type: 'TEXT',                                 description: "'trilateral' | 'quadrilateral' — the vast majority of Arabic roots are three-letter (triconsonantal)." },
      { name: 'semantic_field',     type: 'TEXT',                                 description: "Primary semantic domain, e.g. 'knowledge' / 'light' / 'mercy'. Used for curriculum clustering across books." },
      { name: 'abjad_sum',          type: 'INTEGER',                              description: 'Sum of the abjad values of the root letters, pre-computed at insert time for fast lookup and cross-root grouping.' },
      { name: 'letter_values_json', type: 'TEXT',                                 description: 'JSON array of per-letter abjad values in root order, e.g. [70,30,40] for ع-ل-م = 140.' },
      { name: 'first_seen_book',    type: 'TEXT',    fk: 'books.slug', nullable: true, description: 'Book that first surfaced this root during extraction.' },
      { name: 'source_lexicon',     type: 'TEXT',    nullable: true,              description: "Reference lexicon: 'lane' (Lane's Lexicon) | 'lisan' (Lisān al-ʿArab) | 'mufradat' (al-Rāghib)." },
      { name: 'created_at',         type: 'TEXT',                                 description: 'ISO-8601.' },
    ],
  },
  {
    id: 'word_etymologies',
    label: 'word_etymologies',
    category: 'knowledge',
    purpose:
      'Morphological derivations from each root — the teaching layer that shows depth. Arabic derives dozens of word forms from a single root via fixed patterns (awzān/أوزان); each derived word carries its own abjad value, semantic nuances, and symbolic associations. A chapter about "knowledge" can surface علم → عالم → معلوم → علّم with each form\'s pattern, gloss, abjad value, and esoteric notes in a single query.',
    wave: 2,
    writtenBy: ['0e-enrich', '0h-knowledge-extract'],
    readBy: ['per-chapter', '0g-audit', 'dashboard'],
    x: 20, y: 430,
    fields: [
      { name: 'id',               type: 'INTEGER', pk: true,                          description: 'Auto-increment.' },
      { name: 'root_id',          type: 'INTEGER', fk: 'arabic_roots.root_id',        description: 'Parent root this word form is derived from.' },
      { name: 'word_ar',          type: 'TEXT',                                       description: 'The derived word in fully vowelled Arabic script (with diacritics/tashkeel).' },
      { name: 'word_latin',       type: 'TEXT',                                       description: 'ALA-LC transliteration of the word form.' },
      { name: 'pattern_ar',       type: 'TEXT',                                       description: 'Morphological pattern (wazn/وزن) — the abstract template, e.g. فَاعِل or مَفْعُول.' },
      { name: 'pattern_name',     type: 'TEXT',    nullable: true,                    description: "Pattern grammatical role: 'active participle' | 'verbal noun (masdar)' | 'elative' | 'place noun'." },
      { name: 'pos',              type: 'TEXT',                                       description: "Part of speech: 'noun' | 'verb' | 'adjective' | 'adverb' | 'particle'." },
      { name: 'meaning_en',       type: 'TEXT',                                       description: 'Primary English gloss — one concise phrase.' },
      { name: 'nuances_json',     type: 'TEXT',    nullable: true,                    description: 'JSON array of semantic nuances across classical contexts: Quranic usage, Fiqh usage, Tasawwuf usage, general prose.' },
      { name: 'abjad_value',      type: 'INTEGER',                                    description: 'Abjad numerical value of this specific word form, computed from its written letters.' },
      { name: 'abjad_method',     type: 'TEXT',                                       description: "Calculation tradition: 'kabeer' (standard eastern/Mashriqi) | 'sagheer' (reduced, single digit) | 'maghribi'." },
      { name: 'symbolic_notes',   type: 'TEXT',    nullable: true,                    description: 'Esoteric and teaching notes: words sharing the same abjad value, Sufi associations, colour or element correspondences.' },
      { name: 'quran_frequency',  type: 'INTEGER', nullable: true,                    description: 'Number of times this exact word form (not just root) appears in the Quran. Drives teaching emphasis.' },
      { name: 'created_at',       type: 'TEXT',                                       description: 'ISO-8601.' },
    ],
  },
  {
    id: 'letter_profiles',
    label: 'letter_profiles',
    category: 'knowledge',
    purpose:
      'Static reference table for all 28 Arabic letters — the atomic layer of the etymology system. Each row captures the full classical phonetic science (makhraj + sifāt) and esoteric profile (abjad value, eastern and Maghribi variants, Sufi associations, Quranic function) for one letter. 28 rows forever — but every word and root lookup can join here to unlock teaching depth at the letter level.',
    wave: 3,
    writtenBy: ['seed data (one-time)'],
    readBy: ['word_etymologies', 'arabic_roots', '0e-enrich', 'per-chapter'],
    x: 500, y: 430,
    fields: [
      { name: 'letter_ar',           type: 'TEXT',    pk: true,               description: "The Arabic letter in Unicode NFD form, e.g. 'ع'. Primary key — exactly 28 rows total." },
      { name: 'name_ar',             type: 'TEXT',                             description: "Letter name in Arabic script, e.g. 'عَيْن'." },
      { name: 'name_en',             type: 'TEXT',                             description: "Letter name in English transliteration, e.g. 'ayin'." },
      { name: 'abjad_value',         type: 'INTEGER',                          description: 'Eastern (Mashriqi) abjad value: ا=1, ب=2, ج=3, د=4, ه=5, و=6, ز=7, ح=8, ط=9, ي=10 … غ=1000.' },
      { name: 'abjad_maghribi',      type: 'INTEGER', nullable: true,          description: 'North African (Maghribi) variant value where it diverges from the eastern standard (primarily ث, خ, ذ, ض, ظ, غ).' },
      { name: 'makhraj',             type: 'TEXT',                             description: "Primary articulation zone per ʿilm al-tajwīd: 'halq' (throat) | 'lisān' (tongue) | 'shafa' (lips) | 'jawf' (open air) | 'khayshūm' (nasal)." },
      { name: 'makhraj_detail',      type: 'TEXT',                             description: "Precise articulation sub-location, e.g. 'deepest part of the throat' or 'front of tongue against teeth-ridge'." },
      { name: 'sifat_json',          type: 'TEXT',                             description: "JSON array of sifāt al-hurūf (letter characteristics), e.g. ['jahr','shidda','istila','itbaq']. Each has an Arabic name and classical opposite." },
      { name: 'is_solar',            type: 'INTEGER',                          description: '1 if shamsiyya (solar — assimilates the lam of al-); 0 if qamariyya (lunar — preserves the lam).' },
      { name: 'huruf_muqattaat',     type: 'INTEGER',                          description: '1 if this letter appears in the 14 mysterious Quranic opening letters (حروف المقطعات), e.g. ا in الم.' },
      { name: 'quranic_occurrences', type: 'INTEGER', nullable: true,          description: 'Approximate count of Quranic occurrences of this letter. Teaching emphasis — ا appears ~48 872 times.' },
      { name: 'esoteric_notes',      type: 'TEXT',    nullable: true,          description: 'Symbolic profile: colour correspondences (Ibn Arabi tradition), elemental association (fire/water/air/earth), spiritual station, and links to divine names (e.g. ا opens Allāh).' },
    ],
  },
];

// ─── Edge definitions ─────────────────────────────────────────────────────────

const EDGES: Edge[] = [
  { from: 'books', to: 'chapters',          type: '1:N', path: 'M330,48 C330,80 90,80 90,112' },
  { from: 'books', to: 'knowledge_atoms',   type: '1:N', path: 'M330,48 V127' },
  { from: 'books', to: 'pipeline_runs',     type: '1:N', path: 'M330,48 C330,80 570,80 570,112' },
  { from: 'chapters', to: 'episodes',       type: '1:1', path: 'M90,148 V216' },
  { from: 'pipeline_runs', to: 'cost_ledger', type: '1:N', path: 'M570,148 V216' },
  { from: 'knowledge_atoms', to: 'atom_citations', type: '1:N', path: 'M330,163 V231' },
  { from: 'books', to: 'challenger_findings', type: '1:N', dashed: true, path: 'M358,48 C408,48 408,333 358,333' },
  { from: 'books',        to: 'arabic_roots',     type: '1:N', path: 'M330,48 C330,200 570,200 570,320' },
  { from: 'arabic_roots', to: 'word_etymologies', type: '1:N', path: 'M570,356 C570,395 90,395 90,430' },
  { from: 'arabic_roots', to: 'letter_profiles',  type: 'N:M', path: 'M570,356 V430' },
];

// ─── Component ────────────────────────────────────────────────────────────────

export default function DbArchitecture() {
  const [selected, setSelected] = useState<string | null>(null);
  const [filter, setFilter] = useState<Category | null>(null);

  const selectedTable = TABLES.find(t => t.id === selected) ?? null;

  const connectedIds = selected
    ? new Set(
        EDGES
          .filter(e => e.from === selected || e.to === selected)
          .flatMap(e => [e.from, e.to])
          .filter(id => id !== selected)
      )
    : new Set<string>();

  const isActive = (id: string) => {
    if (selected) return id === selected || connectedIds.has(id);
    if (filter) return TABLES.find(t => t.id === id)?.category === filter;
    return true;
  };

  const isEdgeActive = (edge: Edge) => {
    if (selected) return edge.from === selected || edge.to === selected;
    if (filter) {
      const f = TABLES.find(t => t.id === edge.from);
      const t = TABLES.find(t => t.id === edge.to);
      return f?.category === filter || t?.category === filter;
    }
    return true;
  };

  const relatedTables = selected
    ? EDGES
        .filter(e => e.from === selected || e.to === selected)
        .map(e => ({ id: e.from === selected ? e.to : e.from, type: e.type, dir: e.from === selected ? '→' : '←' }))
    : [];

  const categories: Category[] = ['core', 'knowledge', 'operations', 'quality'];

  return (
    <div className="dba-root">

      {/* ── Filter bar ─────────────────────────────────────────── */}
      <div className="dba-filters">
        <span className="dba-filter-label">View by</span>
        <button
          className={`dba-pill ${!filter ? 'dba-pill--active' : ''}`}
          onClick={() => { setFilter(null); setSelected(null); }}
        >
          All tables
        </button>
        {categories.map(cat => (
          <button
            key={cat}
            className={`dba-pill ${filter === cat ? 'dba-pill--active' : ''}`}
            style={filter === cat ? { '--pill-color': CAT_COLOR[cat] } as React.CSSProperties : {}}
            onClick={() => { setFilter(filter === cat ? null : cat); setSelected(null); }}
          >
            <span className="dba-pill-dot" style={{ background: CAT_COLOR[cat] }} />
            {CAT_LABEL[cat]}
          </button>
        ))}
        {selected && (
          <button className="dba-pill dba-pill--clear" onClick={() => setSelected(null)}>
            ✕ Clear selection
          </button>
        )}
      </div>

      {/* ── Main layout ────────────────────────────────────────── */}
      <div className={`dba-layout ${selected ? 'dba-layout--split' : ''}`}>

        {/* SVG diagram */}
        <div className="dba-diagram-wrap">
          <svg
            className="dba-svg"
            viewBox="0 0 660 510"
            xmlns="http://www.w3.org/2000/svg"
            aria-label="Database architecture diagram — click any table to explore"
          >
            <defs>
              <marker id="ah-core" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                <path d="M0,1 L9,5 L0,9 Z" fill="#8b4513"/>
              </marker>
              <marker id="ah-knowledge" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                <path d="M0,1 L9,5 L0,9 Z" fill="#b8860b"/>
              </marker>
              <marker id="ah-operations" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                <path d="M0,1 L9,5 L0,9 Z" fill="#0078d4"/>
              </marker>
              <marker id="ah-quality" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                <path d="M0,1 L9,5 L0,9 Z" fill="#4a7c4a"/>
              </marker>
              <marker id="ah-dim" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">
                <path d="M0,1 L9,5 L0,9 Z" fill="#d9d3c4"/>
              </marker>
            </defs>

            {/* ── Edges (drawn before nodes) ── */}
            {EDGES.map((edge, i) => {
              const active = isEdgeActive(edge);
              const fromTable = TABLES.find(t => t.id === edge.from)!;
              const catColor = CAT_COLOR[fromTable.category];
              const markerId = active ? `ah-${fromTable.category}` : 'ah-dim';
              return (
                <g key={i}>
                  <path
                    d={edge.path}
                    fill="none"
                    stroke={active ? catColor : '#e8e2d8'}
                    strokeWidth={active ? 1.5 : 1}
                    strokeDasharray={edge.dashed ? '5 3' : undefined}
                    markerEnd={`url(#${markerId})`}
                    style={{ transition: 'stroke 0.2s, stroke-width 0.2s' }}
                  />
                  {/* Cardinality label at midpoint */}
                  {active && (() => {
                    // Compute approximate midpoint from path
                    const parts = edge.path.split(' ');
                    const lastCoord = parts[parts.length - 1];
                    const [ex, ey] = lastCoord.split(',').map(Number);
                    const firstCoord = edge.path.match(/M([0-9.]+),([0-9.]+)/);
                    const sx = firstCoord ? parseFloat(firstCoord[1]) : 0;
                    const sy = firstCoord ? parseFloat(firstCoord[2]) : 0;
                    const mx = (sx + ex) / 2;
                    const my = (sy + ey) / 2;
                    return (
                      <g>
                        <rect x={mx - 14} y={my - 9} width={28} height={14} rx="3" fill="white" stroke={catColor} strokeWidth="0.8" opacity="0.9"/>
                        <text x={mx} y={my + 4} textAnchor="middle" fontSize="9" fill={catColor} fontFamily="'Lato', sans-serif" fontWeight="700">
                          {edge.type}
                        </text>
                      </g>
                    );
                  })()}
                </g>
              );
            })}

            {/* ── Table nodes ── */}
            {TABLES.map(table => {
              const active = isActive(table.id);
              const isSel = selected === table.id;
              const color = CAT_COLOR[table.category];
              const bg = CAT_BG[table.category];

              return (
                <g
                  key={table.id}
                  onClick={() => setSelected(selected === table.id ? null : table.id)}
                  style={{ cursor: 'pointer' }}
                  role="button"
                  aria-label={`Table: ${table.label}`}
                  aria-pressed={isSel}
                >
                  {/* Selection ring */}
                  {isSel && (
                    <rect
                      x={table.x - 4} y={table.y - 4}
                      width={W + 8} height={H + 8}
                      rx="8" fill="none"
                      stroke={color} strokeWidth="2"
                      strokeDasharray="4 2"
                      opacity="0.5"
                    />
                  )}
                  {/* Main box */}
                  <rect
                    x={table.x} y={table.y}
                    width={W} height={H}
                    rx="5"
                    fill={active ? bg : '#f7f4ee'}
                    stroke={active ? color : '#e0dbd3'}
                    strokeWidth={isSel ? 2.5 : 1.5}
                    style={{ transition: 'all 0.18s' }}
                  />
                  {/* Category accent line */}
                  <rect
                    x={table.x} y={table.y}
                    width={6} height={H}
                    rx="5"
                    fill={active ? color : '#e0dbd3'}
                    style={{ transition: 'fill 0.18s' }}
                  />
                  {/* Table name */}
                  <text
                    x={table.x + 16} y={table.y + H / 2 + 5}
                    fontSize="11.5"
                    fontFamily="'Lato', sans-serif"
                    fontWeight="700"
                    fill={active ? (isSel ? color : '#1f1d18') : '#b0a898'}
                    style={{ transition: 'fill 0.18s' }}
                  >
                    {table.label}
                  </text>
                  {/* Field count badge */}
                  <text
                    x={table.x + W - 8} y={table.y + H / 2 + 5}
                    fontSize="9.5"
                    fontFamily="'Lato', sans-serif"
                    fill={active ? '#87827a' : '#c8c0b4'}
                    textAnchor="end"
                    style={{ transition: 'fill 0.18s' }}
                  >
                    {table.fields.length}f
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Diagram legend */}
          <div className="dba-diagram-legend">
            {categories.map(cat => (
              <span key={cat} className="dba-legend-item">
                <span className="dba-legend-dot" style={{ background: CAT_COLOR[cat] }} />
                {CAT_LABEL[cat]}
              </span>
            ))}
            <span className="dba-legend-item">
              <svg width="22" height="10" style={{ verticalAlign: 'middle' }}>
                <line x1="0" y1="5" x2="14" y2="5" stroke="#87827a" strokeWidth="1.5" strokeDasharray="4 2"/>
                <polygon points="12,2 20,5 12,8" fill="#87827a"/>
              </svg>
              secondary link
            </span>
            <span className="dba-legend-item dba-hint">
              Click any table ↑
            </span>
          </div>
        </div>

        {/* ── Detail panel ── */}
        {selectedTable ? (
          <div className="dba-panel" key={selectedTable.id}>
            <div className="dba-panel-header">
              <div className="dba-panel-name" style={{ borderLeftColor: CAT_COLOR[selectedTable.category] }}>
                {selectedTable.label}
              </div>
              <div className="dba-panel-badges">
                <span className="dba-badge" style={{ background: CAT_BG[selectedTable.category], color: CAT_COLOR[selectedTable.category] }}>
                  {CAT_LABEL[selectedTable.category]}
                </span>
                <span className={`dba-badge dba-badge--wave dba-badge--wave${selectedTable.wave}`}>
                  {WAVE_LABEL[selectedTable.wave]}
                </span>
              </div>
            </div>

            <p className="dba-panel-purpose">{selectedTable.purpose}</p>

            {/* Phase info */}
            <div className="dba-phase-grid">
              <div>
                <div className="dba-phase-label">Written by</div>
                <div className="dba-phase-chips">
                  {selectedTable.writtenBy.map(p => (
                    <span key={p} className="dba-chip dba-chip--write">{p}</span>
                  ))}
                </div>
              </div>
              <div>
                <div className="dba-phase-label">Read by</div>
                <div className="dba-phase-chips">
                  {selectedTable.readBy.map(p => (
                    <span key={p} className="dba-chip dba-chip--read">{p}</span>
                  ))}
                </div>
              </div>
            </div>

            {/* Related tables */}
            {relatedTables.length > 0 && (
              <div className="dba-related">
                <div className="dba-section-label">Connected tables</div>
                <div className="dba-related-chips">
                  {relatedTables.map(r => {
                    const rt = TABLES.find(t => t.id === r.id)!;
                    return (
                      <button
                        key={r.id}
                        className="dba-chip dba-chip--related"
                        style={{ borderColor: CAT_COLOR[rt.category], color: CAT_COLOR[rt.category] }}
                        onClick={() => setSelected(r.id)}
                      >
                        {r.dir} {r.id} <span className="dba-chip-type">{r.type}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Fields table */}
            <div className="dba-section-label" style={{ marginTop: '1rem' }}>
              Fields ({selectedTable.fields.length})
            </div>
            <div className="dba-fields">
              {selectedTable.fields.map(field => (
                <div key={field.name} className={`dba-field ${field.pk ? 'dba-field--pk' : ''}`}>
                  <div className="dba-field-top">
                    <span className="dba-field-name">{field.name}</span>
                    <div className="dba-field-tags">
                      <span className="dba-tag dba-tag--type">{field.type}</span>
                      {field.pk && <span className="dba-tag dba-tag--pk">PK</span>}
                      {field.fk && <span className="dba-tag dba-tag--fk" title={field.fk}>FK</span>}
                      {field.nullable && <span className="dba-tag dba-tag--null">nullable</span>}
                    </div>
                  </div>
                  <p className="dba-field-desc">{field.description}</p>
                  {field.fk && (
                    <p className="dba-field-fk-label">→ {field.fk}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="dba-panel dba-panel--empty">
            <div className="dba-empty-icon">⬡</div>
            <p>Select a table in the diagram to explore its fields, purpose, and connections.</p>
            <p className="dba-empty-hint">
              {filter
                ? `Showing ${CAT_LABEL[filter]} tables. ${TABLES.filter(t => t.category === filter).length} tables in this group.`
                : `${TABLES.length} tables total across ${categories.length} groups.`}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
