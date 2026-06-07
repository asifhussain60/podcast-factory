/**
 * book-card-meta.ts — Static display metadata for Studio book cards.
 *
 * Provides native-script titles (Arabic / Chinese) and author names
 * that are not yet present in on-disk YAML files. Keyed by book slug.
 * Extend this map when new books are added.
 */

export interface BookCardMeta {
  /** Native script title — Arabic for Islamic books, Chinese for Chinese-origin fiction. */
  nativeTitle?: string;
  /** BCP-47 language tag for the native title (drives `lang` attr + font selection). */
  nativeLang?: 'ar' | 'zh';
  /** Author name as it should appear on the card. */
  author?: string;
}

export const BOOK_CARD_META: Record<string, BookCardMeta> = {
  // ── Islamic Scholarship ────────────────────────────────────────────────────
  'asaas-al-taveel': {
    nativeTitle: 'أساس التأويل',
    nativeLang: 'ar',
    author: 'al-Qāḍī al-Nuʿmān',
  },
  'ayyuhal-walad': {
    nativeTitle: 'أيُّها الولد',
    nativeLang: 'ar',
    author: 'Imam al-Ghazālī',
  },
  'kitab-al-riyad': {
    nativeTitle: 'كتاب الرياض',
    nativeLang: 'ar',
    author: 'al-Qāḍī al-Nuʿmān',
  },
  'kunooz-al-hikmah': {
    nativeTitle: 'كنوز الحكمة',
    nativeLang: 'ar',
  },
  'the-master-and-the-disciple': {
    nativeTitle: 'كتاب العالم والغلام',
    nativeLang: 'ar',
    author: 'Anon. (Ismaili tradition)',
  },

  // ── Fiction ────────────────────────────────────────────────────────────────
  'journey-to-the-west': {
    nativeTitle: '西遊記',
    nativeLang: 'zh',
    author: "Wu Cheng'en",
  },
  'journey-to-the-west-vol-1': {
    nativeTitle: '西遊記',
    nativeLang: 'zh',
    author: "Wu Cheng'en",
  },

  // ── Technical ──────────────────────────────────────────────────────────────
  'claude-code-training': {
    author: 'Anthropic',
  },

  // ── Guides ─────────────────────────────────────────────────────────────────
  'healthequity': {
    author: 'Health Equity Initiative',
  },
};
