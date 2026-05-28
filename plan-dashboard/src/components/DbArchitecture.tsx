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
    x: 20, y: 12,
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
    x: 20, y: 68,
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
    x: 20, y: 124,
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
    x: 20, y: 180,
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
      'Central intelligence library — one row per Quran verse, hadith, or doctrinal atom sourced from pipeline books or external corpora (Kashkole and future sources). Later books query this via the augmenter to enrich their own chapters. Supersedes the JSONL files in content/knowledge-base/ for queryable access. Doctrine atoms from Kashkole (75 PASS/WARN chapters) seed the library at Wave 1.',
    wave: 1,
    writtenBy: ['0h-knowledge-extract', 'kashkole-ingest'],
    readBy: ['0e-enrich', 'per-chapter', '0g-audit', 'augmenter'],
    x: 240, y: 12,
    fields: [
      { name: 'id',             type: 'TEXT',    pk: true,               description: "Canonical identifier: 'quran:2:255' | 'hadith:bukhari:1234' | 'doctrine:kashkole:24:650:0'." },
      { name: 'type',           type: 'TEXT',                             description: "'quran' | 'hadith' | 'doctrine' (Wave 1). 'quote' | 'definition' | 'etymology' arrive in Waves 2-3. Atom type determines the expected shape of body_json — the schema is documented in _atom_schemas.py." },
      { name: 'wave',           type: 'INTEGER',                          description: 'Intelligence wave that introduced this atom type: 1 (now), 2 (planned), or 3 (future).' },
      { name: 'first_seen_book',    type: 'TEXT', fk: 'books.slug', nullable: true, description: 'First pipeline book to surface this atom. Null for corpus-only atoms (sourced exclusively from Kashkole or other external corpora).' },
      { name: 'first_seen_chapter', type: 'TEXT', fk: 'chapters.id', nullable: true, description: 'First pipeline chapter to surface it. Null for corpus-only atoms.' },
      { name: 'first_seen_date',    type: 'TEXT',                         description: 'ISO-8601.' },
      { name: 'citation_count', type: 'INTEGER',                          description: 'Running count of unique sources (book+chapter pairs OR corpus chapters) that cite this atom. Incremented by the Librarian on every merge.' },
      { name: 'body_json',      type: 'TEXT',                             description: 'JSON blob with type-specific fields. Quran: surah/ayah/text_ar/text_en. Hadith: collection/number/grade/narrator. Doctrine: tradition/genre/binder_id/binder_slug/chapter_id/chunk_index/topic_tags/text_en/quran_refs.' },
      { name: 'variants_json',  type: 'TEXT',    nullable: true,          description: 'JSON array of captured wording variations found across different books or corpus passages.' },
      { name: 'needs_review',   type: 'INTEGER',                          description: 'Boolean (0 | 1). Set to 1 when the atom was sourced from a WARN-verdict corpus chapter or a pipeline chapter with unresolved P1/P2 findings. The augmenter can weight or filter these.' },
      { name: 'updated_at',     type: 'TEXT',                             description: 'ISO-8601 — last Librarian merge.' },
      { name: 'root_id',        type: 'INTEGER', fk: 'arabic_roots.root_id', nullable: true, description: 'When this atom contains a key term, links to its Arabic root entry for etymological depth. Null for atoms not yet enriched.' },
    ],
  },
  {
    id: 'atom_sources',
    label: 'atom_sources',
    category: 'knowledge',
    purpose:
      'Unified provenance table — one row per (atom, source) pair. Covers both pipeline books (source_type=pipeline, chapter_id set) and external corpora like Kashkole (source_type=corpus, corpus_chapter_id set). A CHECK constraint enforces exactly one of the two FK columns is non-null, preventing ghost rows. Single responsibility: all atom provenance, regardless of source.',
    wave: 1,
    writtenBy: ['0h-knowledge-extract', 'kashkole-ingest'],
    readBy: ['augmenter', '0g-audit', 'podcast-librarian'],
    x: 240, y: 68,
    fields: [
      { name: 'id',                type: 'INTEGER', pk: true,                            description: 'Auto-increment.' },
      { name: 'atom_id',           type: 'TEXT',    fk: 'knowledge_atoms.id',            description: 'The atom being sourced.' },
      { name: 'source_type',       type: 'TEXT',                                         description: "'pipeline' — atom extracted from an orchestrated book chapter | 'corpus' — atom extracted from an external corpus (Kashkole or future corpora). Discriminates which FK below is set." },
      { name: 'book_slug',         type: 'TEXT',    fk: 'books.slug', nullable: true,    description: 'Set when source_type = pipeline. Null for corpus sources.' },
      { name: 'chapter_id',        type: 'TEXT',    fk: 'chapters.id', nullable: true,   description: 'Set when source_type = pipeline. Null for corpus sources. CHECK: (chapter_id IS NULL) != (corpus_chapter_id IS NULL).' },
      { name: 'corpus_chapter_id', type: 'INTEGER', fk: 'corpus_chapters.id', nullable: true, description: 'Set when source_type = corpus. Null for pipeline sources. The CHECK constraint makes exactly one of this and chapter_id non-null.' },
      { name: 'locator',           type: 'TEXT',                                         description: 'Heading text or paragraph number — exact location within the source.' },
      { name: 'cited_at',          type: 'TEXT',                                         description: 'ISO-8601 — extraction timestamp.' },
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
    x: 240, y: 372,
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
    x: 20, y: 248,
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
    x: 20, y: 304,
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
    x: 20, y: 372,
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
    x: 20, y: 428,
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
    x: 20, y: 484,
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
  {
    id: 'atom_topic_tags',
    label: 'atom_topic_tags',
    category: 'knowledge',
    purpose:
      'Universal tag-to-atom join table — the DB-native replacement for a file-based tag index. One row per (atom, tag) pair. A covering index on tag enables O(1) augmenter scoring. Scope-agnostic: Wave 1 populates doctrine atoms; Waves 2-3 extend to quran and hadith without schema change.',
    wave: 1,
    writtenBy: ['0h-knowledge-extract', 'kashkole-ingest'],
    readBy: ['augmenter', '0g-audit', 'dashboard'],
    x: 240, y: 124,
    fields: [
      { name: 'id',            type: 'INTEGER', pk: true,                                  description: 'Auto-increment.' },
      { name: 'atom_id',       type: 'TEXT',    fk: 'knowledge_atoms.id',                  description: 'The tagged atom.' },
      { name: 'tag',           type: 'TEXT',                                               description: "Topic tag string, e.g. 'tawil', 'wilaya', 'jurisprudence'. A covering index on this column is mandatory at 150k+ eventual rows." },
      { name: 'topic_type_id', type: 'INTEGER', fk: 'topic_type_taxonomy.type_id', nullable: true, description: 'FK back to the taxonomy row that sourced this tag. Null for tags added outside the Kashkole taxonomy (e.g. manual pipeline tags).' },
      { name: 'created_at',    type: 'TEXT',                                               description: 'ISO-8601.' },
    ],
  },
  {
    id: 'external_corpora',
    label: 'external_corpora',
    category: 'knowledge',
    purpose:
      'Registry of external knowledge corpora — scholarly sources that feed the intelligence library without going through orchestrate_book.py. Kashkole is the first row (corpus_key = kashkole). Designed to accept future corpora (Rasail Ikhwan al-Safa, Nahjul Balagha) without schema changes. One row per corpus; corpus_chapters holds the per-chapter detail.',
    wave: 1,
    writtenBy: ['kashkole-ingest (seed, one-time per corpus)'],
    readBy: ['corpus_chapters', 'augmenter', 'dashboard'],
    x: 240, y: 248,
    fields: [
      { name: 'id',               type: 'INTEGER', pk: true,               description: 'Auto-increment.' },
      { name: 'corpus_key',       type: 'TEXT',                             description: "Short stable identifier, e.g. 'kashkole'. Used across scripts and logs." },
      { name: 'title_en',         type: 'TEXT',                             description: 'Full English title, e.g. Kashkole of Sheikh Bahai.' },
      { name: 'title_ar',         type: 'TEXT',    nullable: true,          description: 'Arabic script title if available.' },
      { name: 'source_language',  type: 'TEXT',                             description: "'ar' | 'fa' | 'ar+fa' — primary language of the source material." },
      { name: 'description',      type: 'TEXT',    nullable: true,          description: 'Brief plain-English description of the corpus scope and provenance.' },
      { name: 'binder_tags_json', type: 'TEXT',                             description: 'JSON object mapping binder IDs to fallback topic tags — used when a chapter has no specific topic_type assignment.' },
      { name: 'chapter_count',    type: 'INTEGER', nullable: true,          description: 'Total chapters in this corpus (populated after full ingestion scan).' },
      { name: 'ingested_at',      type: 'TEXT',    nullable: true,          description: 'ISO-8601 — when the first chapter was ingested into knowledge_atoms.' },
      { name: 'created_at',       type: 'TEXT',                             description: 'ISO-8601 — when this row was registered.' },
    ],
  },
  {
    id: 'topic_type_taxonomy',
    label: 'topic_type_taxonomy',
    category: 'knowledge',
    purpose:
      'The 18-row canonical topic-type reference table — seed data from Lookup_TopicTypes in the Kashkole DB. Replaces the hard-coded TOPIC_TYPE_TAGS dict in the ingestion driver with a DB join (DRY). Static by nature; the driver expands type_id → tags at ingestion time and writes rows to atom_topic_tags. Open for extension: adding a tradition category is one INSERT.',
    wave: 1,
    writtenBy: ['seed data (one-time, from topic-type-map.json)'],
    readBy: ['atom_topic_tags', 'kashkole-ingest', 'augmenter'],
    x: 240, y: 180,
    fields: [
      { name: 'type_id',             type: 'INTEGER', pk: true,             description: 'Matches the TopicTypeID from the Kashkole DB (15, 17, 18 … 34).' },
      { name: 'name_en',             type: 'TEXT',                          description: "English label, e.g. 'Kalam & Argumentation', 'Hadith & Sunnah'." },
      { name: 'name_ur',             type: 'TEXT',                          description: 'Urdu transliteration of the category name.' },
      { name: 'doctrinal_tags_json', type: 'TEXT',                          description: "JSON array of canonical topic tags for this type, e.g. ['kalam','argumentation','theology']. Written to atom_topic_tags at ingestion." },
      { name: 'ordering',            type: 'INTEGER',                       description: 'Sort order for dashboard display — scholarly importance, not numeric type_id order.' },
    ],
  },
  {
    id: 'corpus_chapters',
    label: 'corpus_chapters',
    category: 'knowledge',
    purpose:
      'One row per external corpus chapter — the ingestion gate, provenance anchor, and refinement state machine for corpus atoms. challenger_verdict is the quality filter: PASS and WARN are ingested (WARN sets needs_review=1 on produced atoms); FAIL chapters are skipped. ingestion_status tracks the five-state refinement cycle (pending → ingested → needs_correction → correction_draft → re_ingested), so chapters can be corrected one by one in any order without touching the rest of the library. Each re-ingest cycle deletes the chapter\'s old atoms and re-creates them from the corrected adapted-extract.en.md — idempotent, no duplicates. correction_count surfaces chronically problematic chapters.',
    wave: 1,
    writtenBy: ['kashkole-ingest'],
    readBy: ['atom_sources', 'atom_topic_tags', 'augmenter', 'dashboard'],
    x: 240, y: 304,
    fields: [
      { name: 'id',                  type: 'INTEGER', pk: true,                    description: 'Auto-increment.' },
      { name: 'corpus_id',           type: 'INTEGER', fk: 'external_corpora.id',   description: 'Parent corpus (e.g. Kashkole).' },
      { name: 'chapter_slug',        type: 'TEXT',                                 description: "Stable slug matching the directory under kashkole-ksessions/extracted/, e.g. '01-spiritual-wisdom/03-hadiths'." },
      { name: 'chapter_title',       type: 'TEXT',    nullable: true,              description: 'English chapter title from the adapted extract, if available.' },
      { name: 'binder_id',           type: 'INTEGER',                              description: 'Binder number within the corpus. Used to look up binder-level fallback tags in external_corpora.binder_tags_json.' },
      { name: 'chapter_id_external', type: 'INTEGER',                              description: 'Original ChapterID from the source DB. Preserved for re-ingestion reconciliation.' },
      { name: 'challenger_verdict',  type: 'TEXT',                                 description: "'PASS' | 'WARN' | 'FAIL' | 'UNCHALLENGED'. PASS+WARN are ingested; FAIL skipped; UNCHALLENGED queued." },
      { name: 'ingestion_status',    type: 'TEXT',                                 description: "'pending' | 'ingested' | 'needs_correction' | 'correction_draft' | 're_ingested'. Default 'pending'. Human sets needs_correction + writes correction_notes; driver sets ingested / re_ingested on successful ingest cycles." },
      { name: 'correction_notes',    type: 'TEXT',    nullable: true,              description: 'Human-written annotation describing what needs fixing in the adapted-extract.en.md. Set when marking needs_correction; cleared to null on successful re-ingest.' },
      { name: 'correction_count',    type: 'INTEGER',                              description: 'Number of completed re-ingest correction cycles. Increments each time ingest_chapter(re_ingest=True) completes. 0 = never corrected.' },
      { name: 'topic_ids_json',      type: 'TEXT',                                 description: 'JSON array of source DB TopicIDs for this chapter. Expanded to tags via topic_type_taxonomy at ingestion.' },
      { name: 'atom_count',          type: 'INTEGER',                              description: 'Number of knowledge_atoms rows produced from this chapter. 0 until ingested.' },
      { name: 'adapted_path',        type: 'TEXT',    nullable: true,              description: 'Relative path to adapted-extract.en.md under kashkole-ksessions/. Null if not yet extracted.' },
      { name: 'ingested_at',         type: 'TEXT',    nullable: true,              description: 'ISO-8601 — when this chapter was first ingested.' },
      { name: 'last_ingested_at',    type: 'TEXT',    nullable: true,              description: 'ISO-8601 — when most recently ingested (updated on every re-ingest cycle; same as ingested_at on first ingest).' },
      { name: 'created_at',          type: 'TEXT',                                 description: 'ISO-8601.' },
    ],
  },
];

// ─── Edge definitions ─────────────────────────────────────────────────────────

const EDGES: Edge[] = [
  { from: 'books', to: 'chapters',          type: '1:N', path: 'M90,48 V68' },
  { from: 'books', to: 'knowledge_atoms',   type: '1:N', path: 'M160,30 H240' },
  { from: 'books', to: 'pipeline_runs',     type: '1:N', path: 'M20,30 C6,30 6,266 20,266' },
  { from: 'chapters', to: 'episodes',       type: '1:1', path: 'M90,104 V124' },
  { from: 'pipeline_runs', to: 'cost_ledger', type: '1:N', path: 'M90,284 V304' },
  { from: 'knowledge_atoms', to: 'atom_sources',    type: '1:N', path: 'M310,48 V68' },
  { from: 'knowledge_atoms', to: 'atom_topic_tags', type: '1:N', path: 'M380,30 C394,30 394,142 380,142' },
  { from: 'books', to: 'challenger_findings', type: '1:N', dashed: true, path: 'M160,30 C216,30 216,390 240,390' },
  { from: 'books',        to: 'arabic_roots',     type: '1:N', path: 'M160,30 C176,30 176,390 160,390' },
  { from: 'arabic_roots', to: 'word_etymologies', type: '1:N', path: 'M90,408 V428' },
  { from: 'arabic_roots', to: 'letter_profiles',  type: 'N:M', path: 'M160,390 C174,390 174,502 160,502' },
  { from: 'topic_type_taxonomy', to: 'atom_topic_tags', type: '1:N', dashed: true, path: 'M310,198 C226,198 226,142 240,142' },
  { from: 'external_corpora',    to: 'corpus_chapters', type: '1:N', path: 'M310,284 V304' },
  { from: 'corpus_chapters',     to: 'atom_sources',    type: '1:N', path: 'M240,322 C226,322 226,86 240,86' },
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

  const relatedTables = selected
    ? EDGES
        .filter(e => e.from === selected || e.to === selected)
        .map(e => ({ id: e.from === selected ? e.to : e.from, type: e.type, dir: e.from === selected ? '→' : '←' }))
    : [];

  const categories: Category[] = ['core', 'knowledge', 'operations', 'quality'];
  const visibleTables = filter ? TABLES.filter(t => t.category === filter) : TABLES;

  const toggle = (id: string) => setSelected(prev => prev === id ? null : id);

  return (
    <div className="dba-root">

      {/* ── Filter bar ─────────────────────────────────────────── */}
      <div className="dba-filters">
        <span className="dba-filter-label">View by</span>
        <button
          className={`dba-pill${!filter ? ' dba-pill--active' : ''}`}
          onClick={() => { setFilter(null); setSelected(null); }}
        >
          All tables
        </button>
        {categories.map(cat => (
          <button
            key={cat}
            className={`dba-pill${filter === cat ? ' dba-pill--active' : ''}`}
            style={filter === cat ? { '--pill-color': CAT_COLOR[cat] } as React.CSSProperties : {}}
            onClick={() => { setFilter(filter === cat ? null : cat); setSelected(null); }}
          >
            <span className="dba-pill-dot" style={{ '--cat-color': CAT_COLOR[cat] } as React.CSSProperties} />
            {CAT_LABEL[cat]}
          </button>
        ))}
        {selected && (
          <button className="dba-pill dba-pill--clear" onClick={() => setSelected(null)}>
            ✕ Clear selection
          </button>
        )}
        <span className="dba-filter-count">
          {visibleTables.length} table{visibleTables.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* ── SQL table card grid ─────────────────────────────────── */}
      <div className="dba-grid">
        {visibleTables.map(table => {
          const isSel = selected === table.id;
          const isRelated = !isSel && selected !== null && connectedIds.has(table.id);
          const isDimmed = selected !== null && !isSel && !isRelated;
          const color = CAT_COLOR[table.category];

          return (
            <div
              key={table.id}
              className={[
                'dba-sql-card',
                isSel      ? 'is-selected' : '',
                isRelated  ? 'is-related'  : '',
                isDimmed   ? 'is-dimmed'   : '',
              ].filter(Boolean).join(' ')}
              style={{ '--cat-color': color } as React.CSSProperties}
              onClick={() => toggle(table.id)}
              role="button"
              tabIndex={0}
              onKeyDown={e => e.key === 'Enter' && toggle(table.id)}
              aria-pressed={isSel}
              aria-label={`Table ${table.label} — ${table.fields.length} columns`}
            >
              {/* ── Card header ── */}
              <div className="dba-sql-header">
                <div className="dba-sql-header-left">
                  <span className="dba-sql-table-icon">⬜</span>
                  <span className="dba-sql-table-name">{table.label}</span>
                </div>
                <div className="dba-sql-header-right">
                  {table.wave > 1 && (
                    <span className={`dba-wave-tag dba-wave-tag--${table.wave}`}>
                      W{table.wave}
                    </span>
                  )}
                  <span className="dba-sql-col-count">{table.fields.length}</span>
                </div>
              </div>

              {/* ── Column list ── */}
              <div className="dba-sql-body">
                <table className="dba-sql-table" aria-label={`Columns of ${table.label}`}>
                  <tbody>
                    {table.fields.map(field => (
                      <tr
                        key={field.name}
                        className={[
                          'dba-sql-row',
                          field.pk ? 'is-pk' : '',
                          field.fk ? 'is-fk' : '',
                        ].filter(Boolean).join(' ')}
                      >
                        <td className="dba-sql-icon-cell">
                          {field.pk
                            ? <span className="dba-icon-pk" title="Primary key">🔑</span>
                            : field.fk
                              ? <span className="dba-icon-fk" title={`FK → ${field.fk}`}>🔗</span>
                              : <span className="dba-icon-col" />}
                        </td>
                        <td className="dba-sql-col-name">{field.name}</td>
                        <td className="dba-sql-type-cell">
                          <span className="dba-sql-type">{field.type}</span>
                        </td>
                        <td className="dba-sql-constraints">
                          {field.pk && <span className="dba-con dba-con--pk">PK</span>}
                          {field.fk && <span className="dba-con dba-con--fk" title={field.fk}>FK</span>}
                          {field.nullable && <span className="dba-con dba-con--null">NULL</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* ── Card footer ── */}
              <div className="dba-sql-footer">
                <span className="dba-sql-cat-pill">{CAT_LABEL[table.category]}</span>
                {isSel
                  ? <span className="dba-sql-expand-hint">▲ collapse</span>
                  : <span className="dba-sql-expand-hint">▼ details</span>}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Expanded detail drawer ──────────────────────────────── */}
      {selectedTable && (
        <div
          className="dba-drawer"
          style={{ '--cat-color': CAT_COLOR[selectedTable.category] } as React.CSSProperties}
          aria-label={`Detail for ${selectedTable.label}`}
        >
          <div className="dba-drawer-header">
            <div className="dba-drawer-title">
              <span className="dba-drawer-table-name">{selectedTable.label}</span>
              <span className={`dba-badge dba-badge--wave${selectedTable.wave}`}>
                {WAVE_LABEL[selectedTable.wave]}
              </span>
              <span className="dba-badge" style={{ background: CAT_BG[selectedTable.category], color: CAT_COLOR[selectedTable.category] } as React.CSSProperties}>
                {CAT_LABEL[selectedTable.category]}
              </span>
            </div>
            <button className="dba-drawer-close" onClick={() => setSelected(null)} aria-label="Close detail">✕</button>
          </div>

          <p className="dba-drawer-purpose">{selectedTable.purpose}</p>

          <div className="dba-drawer-meta">
            <div>
              <div className="dba-drawer-meta-label">Written by</div>
              <div className="dba-drawer-chips">
                {selectedTable.writtenBy.map(p => (
                  <span key={p} className="dba-chip dba-chip--write">{p}</span>
                ))}
              </div>
            </div>
            <div>
              <div className="dba-drawer-meta-label">Read by</div>
              <div className="dba-drawer-chips">
                {selectedTable.readBy.map(p => (
                  <span key={p} className="dba-chip dba-chip--read">{p}</span>
                ))}
              </div>
            </div>
          </div>

          {relatedTables.length > 0 && (
            <div className="dba-drawer-relations">
              <div className="dba-drawer-meta-label">FK relationships</div>
              <div className="dba-drawer-chips">
                {relatedTables.map(r => {
                  const rt = TABLES.find(t => t.id === r.id)!;
                  return (
                    <button
                      key={r.id}
                      className="dba-chip dba-chip--related"
                      style={{ '--cat-color': CAT_COLOR[rt.category] } as React.CSSProperties}
                      onClick={() => setSelected(r.id)}
                    >
                      {r.dir} <strong>{r.id}</strong>
                      <span className="dba-chip-type">{r.type}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Full column detail table */}
          <div className="dba-drawer-fields-wrap">
            <div className="dba-drawer-meta-label">
              Columns ({selectedTable.fields.length})
            </div>
            <table className="dba-field-detail-table">
              <thead>
                <tr>
                  <th></th>
                  <th>Column</th>
                  <th>Type</th>
                  <th>Constraints</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {selectedTable.fields.map(field => (
                  <tr key={field.name} className={field.pk ? 'is-pk' : ''}>
                    <td className="dba-fd-icon">
                      {field.pk ? '🔑' : field.fk ? '🔗' : ''}
                    </td>
                    <td className="dba-fd-name">{field.name}</td>
                    <td className="dba-fd-type">{field.type}</td>
                    <td className="dba-fd-constraints">
                      {field.pk && <span className="dba-con dba-con--pk">PK</span>}
                      {field.fk && <span className="dba-con dba-con--fk" title={field.fk}>→ {field.fk}</span>}
                      {field.nullable && <span className="dba-con dba-con--null">NULL</span>}
                    </td>
                    <td className="dba-fd-desc">{field.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

