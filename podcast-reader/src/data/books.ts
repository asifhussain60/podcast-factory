/**
 * Per-book metadata for cover pages and the home-page book index.
 *
 * Each book registered here gets a proper cover (English + Arabic title,
 * author with honorifics, description, editor, publisher). Books without
 * an entry render a slug-derived placeholder.
 *
 * To add a new book: append a key + BookMeta entry. The slug must match
 * the directory name under `content/drafts/`.
 *
 * `isPilot: true` marks the v1 in-scope book that has full reader routes
 * wired up. Others render in the home-page list but are visibly deferred.
 */

export interface BookAuthor {
  name: string;
  titles?: string[];
  era?: string;
}

export interface BookMeta {
  slug: string;
  titleEn: string;
  titleAr?: string;
  subtitle?: string;
  author: BookAuthor;
  editor?: string;
  publisher?: string;
  series?: string;
  description: string;        // 60-80 words
  tradition?: string;
  isPilot?: boolean;
}

export const BOOKS: Record<string, BookMeta> = {
  'kitab-al-riyad': {
    slug: 'kitab-al-riyad',
    titleEn: 'Kitab al-Riyad',
    titleAr: 'كتاب الرياض',
    subtitle: 'A judgment between the two reformers — al-Islah and al-Nusra',
    author: {
      name: 'Hamid al-Din Ahmad ibn Abdallah al-Kirmani',
      titles: ['the Ismaili Daʿi al-Ajall', 'Hujjat al-Iraqayn'],
      era: 'd. circa 411 AH / 1020 CE',
    },
    editor: 'Arif Tamir (investigation and verification)',
    publisher: 'Dar al-Thaqafa · Beirut, Lebanon',
    series: 'Arabic Manuscripts Series · No. 1',
    tradition: 'Ismaili philosophical theology',
    isPilot: true,
    description:
      "A philosophical adjudication between the Two Reformers — the authors of al-Islah (\"The Correction\") and al-Nusra (\"The Defense\") — over the foundational disputes of Ismaili cosmology: the universal Soul, the First Intellect, the speaking souls, the human as the fruit of all the worlds, the architecture of motion, stillness, prime matter, and form, the sections of the world, qada and qadar, the Shariʿah of Adam, the prophets as teachers, and tawhid. Across fifteen chapters, al-Kirmani walks the prior disputes joint-by-joint, refuses to collapse them, and lands his own settled formulas.",
  },
  'asaas-al-taveel': {
    slug: 'asaas-al-taveel',
    titleEn: 'Asas al-Taʾwil',
    titleAr: 'أساس التأويل',
    subtitle: 'The foundation of inner interpretation',
    author: {
      name: 'al-Qadi al-Nuʿman ibn Muhammad',
      titles: ['Chief judge of the Fatimid caliphate', 'compiler of Ismaili law'],
      era: 'd. 363 AH / 974 CE',
    },
    publisher: 'Classical Fatimid corpus',
    tradition: 'Ismaili daʿwa · taʾwil',
    description:
      "The canonical foundation-text of Ismaili taʾwil — the inner interpretation of revelation. Al-Qadi al-Nuʿman lays out the hermeneutic by which the outer law (ẓāhir) and the inner meaning (bāṭin) are held together: how the speakers, foundations, and limits of the daʿwa stand in correspondence with the verses they unfold. Read alongside Kitab al-Riyad, it supplies the interpretive grammar that al-Kirmani assumes his reader already carries.",
  },
  'ayyuhal-walad': {
    slug: 'ayyuhal-walad',
    titleEn: 'Ayyuha\'l-Walad',
    titleAr: 'أيها الولد',
    subtitle: 'O my dear son — a letter on the discipline of the seeker',
    author: {
      name: 'Abu Hamid Muhammad al-Ghazali',
      titles: ['Hujjat al-Islam', 'the Proof of Islam'],
      era: 'd. 505 AH / 1111 CE',
    },
    tradition: 'Sufism · spiritual pedagogy',
    description:
      "A short letter al-Ghazali wrote to a former student who asked for the distilled essence of decades of study. The reply: knowledge without action is a debt; the saved are those whose hearts are sound; companions, sincerity, and conduct outrank cleverness. A pocket-sized work that distils al-Ghazali's pedagogical project — Iḥyāʾ ʿUlūm al-Dīn compressed into a handful of pages addressed to one young man.",
  },
  'islr-mas-i': {
    slug: 'islr-mas-i',
    titleEn: 'An Introduction to Statistical Learning',
    subtitle: 'Master Series I — applications in R / Python',
    author: {
      name: 'James · Witten · Hastie · Tibshirani',
      titles: ['Statisticians, Stanford University & Cambridge'],
      era: '2nd ed. 2021',
    },
    publisher: 'Springer',
    series: 'Springer Texts in Statistics',
    tradition: 'Statistical learning',
    description:
      "The standard contemporary introduction to statistical learning — linear regression, classification, resampling, tree-based methods, support vector machines, unsupervised learning. Written by four of the field's foundational authors as the accessible companion to The Elements of Statistical Learning. The Master Series I adaptation walks the first seven chapters in detail, with code examples and conceptual scaffolding.",
  },
  'the-master-and-the-disciple': {
    slug: 'the-master-and-the-disciple',
    titleEn: 'The Master and the Disciple',
    titleAr: 'كتاب العالم والمتعلم',
    subtitle: 'An early Ismaili dialogue on initiation into the daʿwa',
    author: {
      name: 'Jaʿfar ibn Mansur al-Yaman',
      titles: ['Fatimid daʿi', 'early Ismaili teacher'],
      era: 'd. circa 346 AH / 957 CE',
    },
    tradition: 'Ismaili daʿwa pedagogy',
    description:
      "One of the earliest surviving Ismaili dialogue-texts. A young seeker meets a teacher and is led, by questions and graded answers, into the architecture of the call: the speakers and their foundations, the relation between outer law and inner meaning, the obligations of the muʾmin. The dialogue form preserves the actual pedagogy by which initiation into the daʿwa was conducted in the third and fourth centuries AH.",
  },
};

export function loadBookMeta(slug: string): BookMeta {
  if (slug in BOOKS) {
    return BOOKS[slug];
  }
  const titleEn = slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  return {
    slug,
    titleEn,
    author: { name: 'Unknown author' },
    description:
      'No book metadata registered yet. Add an entry in src/data/books.ts to populate this book with title, author, description, and publisher.',
  };
}
