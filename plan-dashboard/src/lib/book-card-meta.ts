/**
 * book-card-meta.ts — Static display metadata for Studio book cards.
 *
 * Provides native-script titles (Arabic / Chinese), plain-English author names,
 * and per-book FontAwesome icons. Keyed by book slug.
 * Extend this map when new books are added.
 */

export interface BookCardMeta {
  /** Native script title — Arabic for Islamic books, Chinese for Chinese-origin fiction. */
  nativeTitle?: string;
  /** BCP-47 language tag for the native title (drives `lang` attr + font selection). */
  nativeLang?: 'ar' | 'zh';
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
    author: 'al-Qadi al-Nauman',
    icon: 'fa-key',
  },
  'ayyuhal-walad': {
    nativeTitle: 'أيُّها الولد',
    nativeLang: 'ar',
    author: 'Imam al-Ghazali',
    icon: 'fa-feather-pointed',
  },
  'kitab-al-riyad': {
    nativeTitle: 'كتاب الرياض',
    nativeLang: 'ar',
    author: 'al-Qadi al-Nauman',
    icon: 'fa-seedling',
  },
  'kunooz-al-hikmah': {
    nativeTitle: 'كنوز الحكمة',
    nativeLang: 'ar',
    icon: 'fa-gem',
  },
  'the-master-and-the-disciple': {
    nativeTitle: 'كتاب العالم والغلام',
    nativeLang: 'ar',
    author: 'Anon. (Ismaili tradition)',
    icon: 'fa-graduation-cap',
  },

  // ── Fiction ────────────────────────────────────────────────────────────────
  'journey-to-the-west': {
    nativeTitle: '西遊記',
    nativeLang: 'zh',
    author: 'Wu Cheng-en',
    icon: 'fa-dragon',
  },
  'journey-to-the-west-vol-1': {
    nativeTitle: '西遊記',
    nativeLang: 'zh',
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
    author: 'Health Equity Initiative',
    icon: 'fa-scale-balanced',
  },
};
