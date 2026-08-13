/**
 * book-card-meta.ts — Static display metadata for Studio book cards.
 *
 * Provides native-script titles (Arabic / Chinese), English translations,
 * plain-English author names, and per-book FontAwesome icons. Keyed by slug.
 * Extend this map when new books are added.
 */

export interface BookCardMeta {
  /** Native-script title in the work's original language. */
  nativeTitle?: string;
  /** BCP-47 language tag for the native title (drives `lang` attr + font selection). */
  nativeLang?: "ar" | "ur" | "zh";
  /** English translation of the title shown on the card (overrides slug-derived title). */
  displayTitle?: string;
  /** Author name in plain English (no diacritics or special Unicode). */
  author?: string;
  /** FontAwesome icon name (without the `fa-solid` prefix), e.g. `'fa-key'`. */
  icon?: string;
  /** One-line description shown on the card above the pipeline status. */
  blurb?: string;
}

export const BOOK_CARD_META: Record<string, BookCardMeta> = {
  // ── Islamic Scholarship ────────────────────────────────────────────────────
  "al-anwaar-al-lateefah": {
    nativeTitle: "الأنوار اللطيفة",
    nativeLang: "ar",
    displayTitle: "The Subtle Lights",
    icon: "fa-lightbulb",
  },
  "asaas-al-taveel": {
    nativeTitle: "أساس التأويل",
    nativeLang: "ar",
    displayTitle: "Foundation of Esoteric Interpretation",
    author: "al-Qadi al-Nauman",
    icon: "fa-key",
  },
  "ayyuhal-walad": {
    nativeTitle: "أيُّها الولد",
    nativeLang: "ar",
    displayTitle: "O My Beloved Son",
    author: "Imam al-Ghazali",
    icon: "fa-feather-pointed",
  },
  "kitab-al-riyad": {
    nativeTitle: "كتاب الرياض",
    nativeLang: "ar",
    displayTitle: "The Book of Gardens",
    author: "al-Qadi al-Nauman",
    icon: "fa-seedling",
  },
  "kunooz-al-hikmah": {
    nativeTitle: "كنوز الحكمة",
    nativeLang: "ar",
    displayTitle: "Treasures of Wisdom",
    icon: "fa-gem",
  },
  "mukhtasar-ul-asar-2": {
    displayTitle: "Mukhtasar ul Asar 2",
    author: "Qadi al-Nu'man ibn Muhammad ibn Hayyun al-Tamimi",
    icon: "fa-book-open",
  },
  "the-master-and-the-disciple": {
    nativeTitle: "كتاب العالم والغلام",
    nativeLang: "ar",
    displayTitle: "The Scholar and the Disciple",
    author: "Jaffer bin Mansoor al-Yamen",
    icon: "fa-graduation-cap",
  },

  // ── Technical ──────────────────────────────────────────────────────────────
  "claude-code-training": {
    displayTitle: "Claude Code: From Copilot to Agentic AI",
    author: "Anthropic",
    icon: "fa-terminal",
    blurb:
      "A practical training series for developers switching from GitHub Copilot.",
  },

  // ── Guides ─────────────────────────────────────────────────────────────────
  healthequity: {
    displayTitle: "HealthEquity",
    author: "Health Equity Initiative",
    icon: "fa-scale-balanced",
    blurb: "A consumer guide to HSA, FSA, COBRA, and commuter benefits.",
  },
};

/** Resolved card meta — adds the volume number for `<parent>-vol-NN` slugs. */
export interface ResolvedCardMeta extends BookCardMeta {
  /** Volume number parsed from the slug; rendered as a badge, not in the title. */
  volume?: number;
}

/**
 * Resolve display metadata for a slug. Exact entries win; a volume slug
 * (`<parent>-vol-NN`) inherits its parent's template — native script, author,
 * icon, blurb — and carries its volume number separately so cards can render
 * it as a badge. This keeps every volume card identical to its series
 * template without per-volume entries.
 */
export function cardMetaFor(slug: string): ResolvedCardMeta {
  const exact = BOOK_CARD_META[slug];
  if (exact) return exact;
  const m = slug.match(/^(.+)-vol-0*(\d+)$/);
  if (m) {
    const parent = BOOK_CARD_META[m[1]];
    if (parent) return { ...parent, volume: Number(m[2]) };
  }
  return {};
}
