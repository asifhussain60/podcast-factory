// Type definitions mirroring scripts/podcast/_review_serializer.py dataclasses.
// Keep in sync — the wire format is JSON over the FastAPI backend.

export interface FlagRow {
  page: number
  quote: string
  note: string
  recurring_pattern: boolean
}

export interface GlossaryRow {
  term: string
  definition: string
}

export interface PronunciationRow {
  term: string
  correct: string
}

export interface ContentRange {
  body_starts_at_page: number | null
  body_ends_at_page: number | null
}

export interface AISuggestion {
  id: string
  page: number
  quote: string
  reason: string
  feature: string
  status: 'pending' | 'accepted' | 'dismissed'
}

export interface ReviewStruct {
  schema_version: number
  book_slug: string
  translation_issues: FlagRow[]
  missing_passages: FlagRow[]
  glossary: GlossaryRow[]
  pronunciation: PronunciationRow[]
  free_form_comments: string
  content_range: ContentRange
  approved: boolean
  ai_suggestions: AISuggestion[]
  mtime?: number
}

export interface BookSummary {
  slug: string
  phase_status: string
  current_phase: string
  page_count: number
  ocr_confidence: number | null
  has_review_file: boolean
  has_transcript: boolean
  review_mtime: number | null
  worktree_root: string
}

export interface BooksList {
  worktree_roots: string[]
  books: BookSummary[]
}

export interface TranscriptResponse {
  slug: string
  text: string
  source_signature: string
  page_index: { page: number; offset: number }[]
  char_count: number
}

export interface AIResult<T = unknown> {
  ok: boolean
  feature: string
  model: string
  cached: boolean
  cost_usd: number
  elapsed_sec: number
  payload: T
}

export interface AIBudget {
  spent_usd: number
  budget_usd: number
  remaining_usd: number
}

export type SectionId =
  | 'translation'
  | 'missing'
  | 'glossary'
  | 'pronunciation'
  | 'comments'
  | 'range'

export type ReaderTheme = 'dark' | 'sepia' | 'light'
export type ReaderFont = 'lato' | 'cormorant' | 'lora' | 'opendyslexic'
export type ReaderLine = 'tight' | 'normal' | 'loose'
export type ReaderWidth = 'narrow' | 'medium' | 'wide'

// AI feature identifiers — must match scripts/podcast/_review_ai.py MODEL_FOR_FEATURE keys
export type AIFeature =
  | 'summarize'
  | 'diff-explain'
  | 'arabic'
  | 'preflight'
  | 'voice-shift'
  | 'episode-plan'
  | 'suggest-flags'
  | 'autocomplete'
  | 'categorize'
  | 'content-range'

// AI feature payload shapes
export interface PageSummary {
  page: number
  summary: string
}

export interface ArabicTerm {
  term: string
  canonical_form?: string
  pages: number[]
  manifest_match: boolean
}

export interface PreflightFinding {
  page: number
  quote: string
  issue_type: string
  confidence: number
  suggestion: string
}

export interface VoiceShift {
  page: number
  before_quote: string
  after_quote: string
  shift_type: string
  confidence: number
  note: string
}

export interface EpisodePlan {
  episode_count: number
  rationale: string
  episodes: {
    n: number
    title: string
    page_range: [number, number]
    target_word_count: number
    recap_cue: string
    preview_cue: string
  }[]
}

export interface SuggestFlag {
  page: number
  quote: string
  reason: string
  confidence: number
}

export interface CategorizeResult {
  section_id: SectionId
  confidence: number
  reason: string
}

export interface ContentRangeRecommendation {
  body_starts_at_page: number
  body_ends_at_page: number
  rationale: string
}

export interface DiffExplanation {
  explanation: string
}

export interface AutocompleteResult {
  completions: string[]
}
