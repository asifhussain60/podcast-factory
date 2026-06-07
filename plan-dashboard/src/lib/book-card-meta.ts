/**
 * book-card-meta.ts — Static display metadata for Studio book cards.
 *
 * Provides native-script titles (Arabic / Chinese), English translations,
 * plain-English author names, and per-book FontAwesome icons. Keyed by slug.
 * Extend this map when new books are added.
 */

export interface BookCardMeta {
  /** Native script title — Arabic for Islamic books, Chinese for Chinese-origin fiction. */
  nativeTitle?: string;
  /** BCP-47 language tag for the native title (drives `lang` attr + font selection). */
  nativeLang?: 'ar' | 'zh';
  /** English translation of the title shown on the card (overrides slug-derived title). */
  displayTitle?: string;
  /** Author name in plain English (no diacritics or special Unicode). */
  author?: string;
  /** FontAwesome icon name (without the `fa-solid` prefix), e.g. `'fa-key'`. */
  icon?: string;
}

export const BOOK_CARD_META: Record<string, BookCardMeta> = {
  // ── Islamic Scholarship ────────────────────────────────────────────────────
  'asaas-al-taveel': {
    nativeTitle: 'أساس التأويل',
    nativeLang: 'ar',
    displayTitle: 'Foundation of Esoteric Interpretation',
    author: 'al-Qadi al-Nauman',
    icon: 'fa-key',
  },
  'ayyuhal-walad': {
    nativeTitle: 'أيُّها الولد',
    nativeLang: 'ar',
    displayTitle: 'O My Beloved Son',
    author: 'Imam al-Ghazali',
    icon: 'fa-feather-pointed',
  },
  'kitab-al-riyad': {
    nativeTitle: 'كتاب الرياض',
    nativeLang: 'ar',
    displayTitle: 'The Book of Gardens',
    author: 'al-Qadi al-Nauman',
    icon: 'fa-seedling',
  },
  'kunooz-al-hikmah': {
    nativeTitle: 'كنوز الحكمة',
    nativeLang: 'ar',
    displayTitle: 'Treasures of Wisdom',
    icon: 'fa-gem',
  },
  'the-master-and-the-disciple': {
    nativeTitle: 'كتاب العالم والغلام',
    nativeLang: 'ar',
    displayTitle: 'The Scholar and the Disciple',
    author: 'Anon. (Ismaili tradition)',
    icon: 'fa-graduation-cap',
  },

  // ── Fiction ────────────────────────────────────────────────────────────────
  'journey-to-the-west': {
    nativeTitle: '西遊記',
    nativeLang: 'zh',
    displayTitle: 'Journey to the West',
    author: 'Wu Cheng-en',
    icon: 'fa-dragon',
  },
  'journey-to-the-west-vol-1': {
    nativeTitle: '西遊記',
    nativeLang: 'zh',
    displayTitle: 'Journey to the West, Volume I',
    author: 'Wu Cheng-en',
    icon: 'fa-dragon',
  },

  // ── Technical ──────────────────────────────────────────────────────────────
  'claude-code-training': {
    author: 'Anthropic',
    icon: 'fa-terminal',
  },

  // ── Guides ─────────────────────────────────────────────────────────────────
  'healthequity': {
    displayTitle: 'HealthEquity',
    author: 'Health Equity Initiative',
    icon: 'fa-scale-balanced',
  },
};
