import {
  faBookOpen,
  faCircleQuestion,
  faHeadphones,
  faHighlighter,
  faImages,
  faKey,
  faLayerGroup,
  faMagnifyingGlass,
  type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";

/**
 * What this site does, in words a reader can find.
 *
 * DATA, not markup, and not markdown. Chapter prose is rendered to HTML once at
 * publish time precisely so the Worker carries no markdown implementation — a
 * second one here would be a second answer to what a paragraph looks like. Held
 * as a typed array instead, so the page renders it, `about.test.ts` checks its
 * shape, and neither has to parse anything.
 *
 * THE RULE FOR WHAT GOES IN: only what a READER can actually do. The temptation
 * on a page like this is to describe the whole system, and the whole system
 * includes things no reader will ever see — the Scholar Companion is readable by
 * one account, so an entry describing it would be a promise the site never keeps
 * for the people reading this page. Absence is the honest answer.
 *
 * Every claim below is a behaviour that exists in this app today. When one stops
 * being true its entry is wrong, and there is a check in the deploy that says so
 * — see the "What's new" step in scripts/podcast/deploy_listener.sh.
 */

/** One question and its answer, which is also the unit that search matches. */
export interface Entry {
  /** Phrased as the reader would ask it, because that is what they type. */
  q: string;
  /** Paragraphs. Plain strings — no markup, see the note above. */
  a: string[];
}

/** The six declared topic hues. See `--l-topic-*` in the stylesheet. */
export type Hue = "coral" | "cyan" | "violet" | "green" | "amber" | "blue";

export interface Section {
  /** The anchor, the filter value, and the `details` name group. */
  id: string;
  title: string;
  /**
   * The title again, short enough for a chip.
   *
   * A heading and a chip are read differently: the heading is arrived at and can
   * afford to be precise, the chip is scanned in a row of eight. Using the
   * heading for both put four rows of chips on a phone above a page whose entire
   * purpose is not to overwhelm anybody. Omitted when the title is already short.
   */
  short?: string;
  icon: IconDefinition;
  /**
   * Which of the six topic hues this section wears.
   *
   * A NAME, not a colour: the value indexes `--l-topic-*`, which every palette
   * declares and `test/theme.test.ts` holds to the body contrast floor in all
   * three. A hex here would be one colour for three themes, and the one that is
   * right on paper is the one that is unreadable on near-black.
   */
  hue: Hue;
  /** One line, always visible under the heading — the answer for a skimmer. */
  blurb: string;
  entries: Entry[];
}

/* -------------------------------------------------------------------------- */
/* What the site does                                                          */
/* -------------------------------------------------------------------------- */

export const SECTIONS: Section[] = [
  {
    id: "shelf",
    title: "The shelf",
    hue: "green",
    short: "The shelf",
    icon: faLayerGroup,
    blurb:
      "Three kinds of work, laid out so you can find one without wading through the others.",
    entries: [
      {
        q: "What are Books, Sessions and Audiobooks?",
        a: [
          "Books are classical works published twice over — a modern English reading edition, and a series of long-form conversational episodes drawn from the same source. Follow either, or both.",
          "Sessions are spoken teaching, gathered into series meant to be followed in order. The talk is the work; the reading edition behind it is that same evening written out.",
          "Audiobooks are published books read aloud by a narrator, with the text beside the voice — the words light up as they are spoken, so you can listen, read, or do both at once.",
          "If you have been given more than one kind, the site opens on a page that offers them as three tiles and says in a sentence what each one is. If you have only one kind, that page would be a choice with nothing to choose, so you go straight to the shelf.",
        ],
      },
      {
        q: "How do I narrow the shelf down?",
        a: [
          "The row above the shelf does three things: it searches, it switches between everything and one collection on its own, and it filters by subject — history, shariah, theology, esoteric, reality and philosophy.",
          "Showing everything, the shelf draws books and sessions as two titled groups rather than one alphabetical run, each on its own tinted panel. Narrowed to a single collection the headings go away, because the grid already is that collection.",
        ],
      },
      {
        q: "Can I make the shelf denser, or a plain list?",
        a: [
          "Yes — three view modes sit in the same row. Cards is the roomy default, compact fits many more on a screen at the size of a tile, and list is one row per book with its progress beside it.",
          "Your choice is remembered, and so are the collection and subject you last filtered by, so the shelf opens the way you left it.",
        ],
      },
      {
        q: "What is the coloured corner on a card?",
        a: [
          "The ribbon is the book's subject track, in the same colour as the matching filter above the shelf. In cards it carries the word; in the compact view it is the shape alone, so the corner still tells you what a book is without a label too small to read.",
          "The card itself is tinted by its collection, so a book and a session are told apart at a glance as well as by name.",
        ],
      },
      {
        q: "How does a work in several volumes appear?",
        a: [
          "As one card, not six. A multi-volume work is stacked into a single card carrying a numbered picker, so choosing a volume opens it in place rather than making you find it among its siblings. In the list view the same work is one row that opens to show its volumes.",
        ],
      },
    ],
  },

  {
    id: "reading",
    title: "Reading",
    hue: "blue",
    icon: faBookOpen,
    blurb:
      "Every book is a modern English edition you can set to your own eyes.",
    entries: [
      {
        q: "How do I make the text comfortable to read?",
        a: [
          "Open any chapter and the row of controls above the page sets six things: the typeface, the size, how far apart the lines sit, how wide the column runs, and the overall theme — light, sepia, or dark.",
          "There are seven text sizes and three column widths. Two of the six typefaces are designed for easier reading rather than for looks: Atkinson Hyperlegible, drawn for low vision, and OpenDyslexic. Nothing here is a preview — the page you are setting is the page you keep.",
          "Your settings follow you. They are remembered in the browser you set them in, so every book you open afterwards opens the way you left the last one.",
        ],
      },
      {
        q: "Does it remember where I stopped?",
        a: [
          "Yes. Your position is saved as you read and is kept against your account rather than against the device, so a chapter you started on a laptop carries on where you left it on a phone.",
          "The library shows how far through each book you are, and a book you have not opened says so plainly rather than showing an empty bar.",
        ],
      },
      {
        q: "How do I move around a book?",
        a: [
          "A single column of controls runs down the left of the reader: home, the chapter list, the reading assistant, a bookmark, the book's own page, and the source reference. The chapter list marks the chapter you are in, so you can jump without going back to the book.",
          "The row of controls above the page now only dresses it — theme, typeface, size, spacing and width. Everything that takes you somewhere lives in the column, in one place rather than two.",
          "Books vary in what they carry. Some have a reading edition and recordings, some only one of the two — the book's own page shows what is actually there and never offers a link to something that is not.",
        ],
      },
      {
        q: "Can I keep a book for reading without signal?",
        a: [
          "Yes. When a book is available for offline reading, its page offers a Read Offline button, paired with the PDF download and each explaining itself when you hover or focus it. Once it is saved, the downloads page shows what is on this device and opens a reader that does not need the network.",
          "Offline copies belong to the device you saved them on. They are useful for a flight or a weak connection; your account is still what decides which books can be saved in the first place.",
        ],
      },
      {
        q: "Can a chapter be read aloud to me?",
        a: [
          "Where a chapter has been recorded, a headphone control in the reader plays it, and the paragraph being spoken is lit as it goes — so you can follow the words with your eyes or simply listen.",
          "It is the same player the episodes use, so it keeps going while you move around the site, and pressing the control again pauses it. A chapter with no recording does not show the control at all.",
        ],
      },
      {
        q: "Is there anything to help me hold my place on the line?",
        a: [
          "Yes. The reading assistant dims the page and keeps the sentence you are on clear, so your eye has one line to hold rather than a full page of them. It is off until you turn it on, and it is the eye button in the column of controls.",
        ],
      },
      {
        q: "Where in the original book does a chapter come from?",
        a: [
          "For books whose original has been mapped, a control in the reader shows the pages and headings in the source that a chapter was drawn from. It is off by default and stays as you set it.",
          "It gives the page range and the headings, never the source's own words. A book that has not been mapped does not offer the control rather than offering one that answers nothing.",
        ],
      },
      {
        q: "Why are some passages set apart in coloured cards?",
        a: [
          "Quotations are set as cards rather than run into the paragraph, and the card says what kind of quotation it is — scripture, a reported saying, verse, or a quotation from another work. Where the original language is carried, it sits above the English with its reference beneath.",
        ],
      },
    ],
  },

  {
    id: "finding",
    title: "Finding things",
    hue: "coral",
    short: "Search",
    icon: faMagnifyingGlass,
    blurb: "Search your library, then narrow the answer inside a book.",
    entries: [
      {
        q: "Can I search across the library?",
        a: [
          "Yes. The search box on the library looks through the books you have been given and returns matching books, chapters and passages. It does not search books outside your own access.",
          "For a larger search, open the search page. It gives you room to scan the results, keep changing the words, and move straight into the chapter that contains what you found.",
        ],
      },
      {
        q: "Can I search inside one book?",
        a: [
          "Yes. A book's page can search that book's own chapters, so you can find a name or phrase without leaving the work you are already reading.",
          "Search ignores simple differences in accents and letter forms where it can, so a remembered word still has a good chance of finding the passage even when you do not type it exactly as the edition prints it.",
        ],
      },
    ],
  },

  {
    id: "marks",
    title: "Highlights, notes and bookmarks",
    hue: "amber",
    short: "Highlights",
    icon: faHighlighter,
    blurb: "Mark a passage, write on it, and find it again from any device.",
    entries: [
      {
        q: "How do I highlight something?",
        a: [
          "Select the words. A small bar appears over them offering four colours — gold, sage, sky and rose. Pick one and the passage is marked.",
          "Tap a highlight you already made and the same bar comes back, this time offering to change its colour, write a note on it, or take it off.",
        ],
      },
      {
        q: "How do notes work?",
        a: [
          "A note is attached to the passage it is about. Select the text, choose the note button, and write — the note keeps its place in the chapter, so opening it later takes you back to the sentence that prompted it.",
          "The panel on the right of the reader collects everything you have written in that chapter, so you can read your own notes as a list without hunting through the pages.",
        ],
      },
      {
        q: "What is a bookmark for, if my place is already saved?",
        a: [
          "Your reading position is one moving point — it follows you and there is only ever one of it. A bookmark is a place you chose to keep, and you can keep as many as you like.",
          "Bookmarks are listed in the same right-hand panel as your notes and highlights.",
        ],
      },
      {
        q: "Can anyone else see my highlights and notes?",
        a: [
          "No other reader can. Everything you mark is filed under your own account, and every request for it is answered for that account alone — a note you write in a book is not visible to anyone else reading the same book.",
        ],
      },
      {
        q: "What happens if I lose signal while I am reading?",
        a: [
          "Nothing is lost. A highlight or a note is applied on your screen immediately and queued, and the queue is sent as soon as the connection comes back — on the next page you open, the moment the device is online again, or when you return to the tab.",
          "Sending the same thing twice is harmless, so a patchy connection cannot leave you with duplicates.",
        ],
      },
    ],
  },

  {
    id: "listening",
    title: "Listening",
    hue: "violet",
    icon: faHeadphones,
    blurb:
      "Long-form episodes, with the transcript following along beside them.",
    entries: [
      {
        q: "What are the episodes?",
        a: [
          "Each book is published twice over: as a reading edition, and as a series of long-form conversational episodes drawn from the same source. They are two ways of taking the same material, not a summary of one another.",
          "Where a book has many episodes they are grouped into sessions, in the order the series runs.",
        ],
      },
      {
        q: "Does the audio stop when I move to another page?",
        a: [
          "No. The player keeps going while you move around the site — open another chapter, look something up in the library, and the episode carries on.",
        ],
      },
      {
        q: "Can I read what is being said?",
        a: [
          "Most episodes carry a transcript that follows the audio as it plays, and you can press any line to jump the recording to that moment.",
          "An episode without one simply does not show it. Transcripts are made from the recordings themselves, so an occasional name will be spelt as it sounded.",
        ],
      },
      {
        q: "Can I keep episodes on this device?",
        a: [
          "Yes, when downloads are offered for a book. Saved recordings play from the device instead of the network, so listening can continue when the connection drops.",
          "The downloads page tells you what is saved here and lets you remove it when you no longer need it.",
        ],
      },
      {
        q: "How is an audiobook different from an episode?",
        a: [
          "An episode is a conversation about the book. An audiobook is the book itself, read aloud by a narrator, with the text on screen beside the voice and the words lit as they are spoken.",
          "They sit in their own part of the shelf for that reason, and a work appears there only when it has actually been narrated.",
        ],
      },
      {
        q: "Can I change how fast it plays?",
        a: [
          "Yes, in half steps from normal speed up to three times. Three is the ceiling on purpose: past roughly that point the gaps between words disappear before the ear can separate them.",
          "The speed you choose is remembered, so the next episode starts where you left the dial rather than back at normal.",
        ],
      },
    ],
  },

  {
    id: "formats",
    title: "Slides and the print edition",
    hue: "cyan",
    short: "Slides & PDF",
    icon: faImages,
    blurb: "Some books also carry slides, and some a PDF you can keep.",
    entries: [
      {
        q: "What are the slides?",
        a: [
          "Where a book has them, its slides retell it visually, a deck per chapter. They are reached from the book's own page and read by paging through.",
        ],
      },
      {
        q: "Can I download a book?",
        a: [
          "When a book has a print edition, its page offers a Download PDF button with the size beside it. That is the same edition you read on screen, typeset for paper.",
          "A book whose PDF has not been uploaded yet says so rather than offering a link that fails.",
        ],
      },
    ],
  },

  {
    id: "access",
    title: "Signing in and access",
    hue: "green",
    short: "Access",
    icon: faKey,
    blurb:
      "The library is private. You are invited to it by address, book by book.",
    entries: [
      {
        q: "Why must I sign in with a particular email address?",
        a: [
          "Your invitation is tied to one address. Signing in with a different Google account is, as far as the site can tell, a different person — so it will not find your invitation and will not let you in.",
          "If you are not sure which address you were invited under, it is named in the message you were sent.",
        ],
      },
      {
        q: "I am signed in, but my library is empty.",
        a: [
          "Signing in and having books are two separate things. An invitation lets you through the door; each book is given separately.",
          "An empty library means the invitation worked and no book has been given to you yet. Ask Asif.",
        ],
      },
      {
        q: "How do I get access to more books?",
        a: [
          "Ask. Access is granted a book at a time, and a book you have not been given does not appear in your library at all.",
        ],
      },
      {
        q: "Is there an app to install?",
        a: [
          "No — this is a website, and it is built to work on a phone. On iPhone or Android you can add it to your home screen from the browser's share menu, and it will open like an app.",
        ],
      },
      {
        q: "Is any of this public?",
        a: [
          "No. Nothing in the library can be reached without signing in, and a book you have not been given is not merely hidden from your library — it cannot be opened at all, by any address.",
        ],
      },
    ],
  },
];

/* -------------------------------------------------------------------------- */
/* Frequently asked                                                            */
/* -------------------------------------------------------------------------- */

/**
 * The questions that are not about ONE feature.
 *
 * Kept as its own section rather than mixed into the five above, because the
 * question a reader arrives with — "why can I not see anything" — belongs
 * somewhere they can jump straight to. It is a `Section` like any other, so the
 * search box, the jump-links and the accordion all treat it identically.
 */
export const FAQ: Section = {
  id: "faq",
  title: "Frequently asked",
  hue: "coral",
  icon: faCircleQuestion,
  blurb: "The things people ask first.",
  entries: [
    {
      q: "Who is behind this?",
      a: [
        "Asif Hussain. The library is a personal project — classical works prepared as modern English editions and as long-form audio, shared with the people he invites to it.",
      ],
    },
    {
      q: "Do the books cost anything?",
      a: ["No. Nothing here is sold and nothing is advertised."],
    },
    {
      q: "Why do some books have no recordings, or no reading edition?",
      a: [
        "Because they are prepared one at a time and the two halves do not finish together. A book's page shows what it actually has today; a book gains its other half when that half is ready.",
      ],
    },
    {
      q: "Can I share a book with someone?",
      a: [
        "Not by sending a link — anyone opening it would be asked to sign in and would then be told they have no access. If somebody would like to read along, ask Asif to invite them.",
      ],
    },
    {
      q: "Something is broken, or a name is misspelt.",
      a: [
        "Tell Asif. Corrections to the text are made at the source and the whole edition is republished, so a fix reaches everyone reading it.",
      ],
    },
    {
      q: "Why do some books show a second title in another script?",
      a: [
        "Because that is the work's own name. Where a book has one, its original title is set beside the English on the book's page and on its card, in Arabic or Urdu as the work itself is written.",
      ],
    },
    {
      q: "How do I sign out?",
      a: [
        "Sign out is at the top right of every page, beside the theme control.",
      ],
    },
  ],
};

/** Everything the page renders and searches, in the order it appears. */
export const ALL_SECTIONS: Section[] = [...SECTIONS, FAQ];

/* -------------------------------------------------------------------------- */
/* What changed                                                                */
/* -------------------------------------------------------------------------- */

export interface Release {
  /** ISO `YYYY-MM-DD`. Rendered by the page; never parsed for logic. */
  date: string;
  items: string[];
}

/**
 * What has changed lately, written for readers.
 *
 * WRITTEN, not generated. The obvious automation is to build this from commit
 * messages at deploy time, and the commit messages in this repository read like
 * "test(listener): pin that the Access link is offered to the administrator" —
 * true, useful to its author, and noise to everybody this page is for. A release
 * note is a different document from a commit log and has to be composed as one.
 *
 * What IS automated is noticing when this list has fallen behind the app: the
 * deploy compares the last change to THIS FILE against the last change to
 * `listener/app`, and says so when the code is newer. It warns and continues —
 * it never blocks, because publishing a book runs the same deploy script and a
 * stale note here must not stop a finished book from reaching the site.
 *
 * Newest first.
 */
export const RELEASES: Release[] = [
  {
    date: "2026-09-01",
    items: [
      "Audiobooks. Published books read aloud by a narrator, with the text beside the voice and the words lit as they are spoken. They have their own place on the shelf, so a narrated book and a talk are no longer filed together.",
      "The site opens on a page that asks where you would like to begin, and explains in a sentence what Books, Sessions and Audiobooks are. It appears only if you have been given more than one kind.",
      "The reader has one column of controls instead of two rows and an edge tab: home, contents, the reading assistant, a bookmark, the book's page and the source reference. The row above the page now only dresses it — theme, typeface, size, spacing and width — and the page is wider for it.",
      "A reading assistant. It dims the page and keeps the sentence you are on clear, for anyone who loses their line on a full page of text.",
      "Listening speeds run in half steps up to three times normal, and the speed you pick is remembered.",
    ],
  },
  {
    date: "2026-08-29",
    items: [
      "Showing everything, the shelf now draws books and sessions as two titled groups on their own panels rather than one alphabetical run, and each card is tinted by the collection it belongs to.",
      "The subject ribbon on a compact card is large enough to read as a marker rather than a nick in the corner.",
    ],
  },
  {
    date: "2026-08-16",
    items: [
      "A work published in several volumes is one card carrying a numbered picker, instead of six cards sitting side by side. In the list view it is one row that opens to show its volumes.",
      "A quiet control in the reader shows which pages and headings of the original book a chapter was drawn from, for the books whose source has been mapped. It is off unless you turn it on.",
      "A book's page opens with one identity card — its category, its English title with the work's own name beside it, and the description — and the Read Offline and Download PDF buttons are paired beneath a clear chapter count, each explaining what it does.",
      "Every control in the reading toolbar now says what it is and what it does when you hover or focus it.",
    ],
  },
  {
    date: "2026-08-14",
    items: [
      "Chapters can be read aloud. Where a chapter has been recorded, a control in the reader plays it and lights the paragraph being spoken.",
      "The shelf can be shown three ways — roomy cards, a dense compact grid, or a plain list — and your choice is remembered along with the collection and subject you last filtered by.",
      "Books carry a subject track: history, shariah, theology, esoteric, reality and philosophy. It shows as the coloured corner on a card, and as a row of filters above the shelf.",
      "The whole of a library card is now a link, its actions sit in a fixed order, and Read opens the book's chapter list rather than dropping you into the middle of it.",
      "Arabic is set in one face at one size and one weight throughout the reader, and is never artificially bolded.",
    ],
  },
  {
    date: "2026-08-13",
    items: [
      "Search now reaches the words inside the books you hold. The library search finds books, chapters and passages, and a larger search page gives longer results room to breathe.",
      "Books and episodes can be kept on the device when downloads are available, with a downloads page that opens even when the network is gone.",
      "Library cards now behave like a row of actions: listen, read and notes are clear icon buttons in a fixed order, with note counts shown as a small badge instead of extra text.",
      "Arabic reading is steadier across the site: the Arabic font is bundled with the library, and the reader keeps source images and page ornaments aligned with the edition.",
    ],
  },
  {
    date: "2026-08-11",
    items: [
      "Sessions. The library now also holds the lecture series Asif delivered himself: the recording is his own voice from the evening it was given, and the reading edition is that same session written out. They carry a violet cover so you can tell them from the books at a glance, and a control above the library shows you either collection on its own.",
      "The Listen tab reads as a player rather than a list — each recording is a card you can start from anywhere on the row, and on a phone the player fills the screen while it plays.",
      "Bulleted and numbered lists in the reading edition show their bullets and numbers. Every list in every book had been rendering flat, so a passage the author set out as three points read as three paragraphs.",
    ],
  },
  {
    date: "2026-08-06",
    items: [
      "On a laptop, a tablet held sideways, or any wide screen, three buttons in the reading controls set how wide the page runs. The narrowest is what you have been reading; the other two use the space that was empty on either side. They do not appear on a phone or a tablet held upright, where the page already fills the screen.",
      "The speed you listen at is remembered. Choosing 1.5× used to last only until the page was reloaded, and every episode after that started at normal speed again.",
      "The player skips back and forward fifteen seconds on a phone. Those two buttons had been hidden on small screens, which is where most listening happens.",
      "The Notes button shows how many notes you have kept in the episode you are listening to.",
      "The episode list says the same thing for every episode at once: a small gold number on any episode you have kept something in. Press it to read those notes.",
      "A chapter is set as a leaf of paper rather than a panel — squared edges, the pages of the book showing behind it, and the margins a printed page is given.",
      "On a phone, every reading setting is now on screen at once. The typeface, size, spacing and line width had been sitting off the right-hand edge, reachable only by dragging a row that gave no sign it could be dragged.",
      "Your phone's own controls now know what is playing: the lock screen, your headphones and a car stereo show the episode and the book, and their skip buttons move by the same fifteen seconds.",
      "The player reads as a piece of equipment rather than the foot of the page, and the position bar shows how much of the episode is behind you.",
      'The transcript follows the audio as it plays, and a line\'s "+" opens a note already holding that line.',
    ],
  },
  {
    date: "2026-08-05",
    items: [
      "This page. Everything the site can do, with a search box and a FAQ.",
      "A book's page opens with both of its names — the English title and the work's own Arabic beneath it — set together in one panel.",
      "The notes panel in the reader stays as you leave it. It used to reopen itself every time you turned to a new chapter.",
      "Books whose recordings run long are now grouped into sessions, so a twenty-episode series reads as five sittings rather than one list.",
      "Slides are held per chapter, so a book with several decks keeps them apart instead of merging them into one.",
      "The library's cards were made uniform — every book now shows its progress in the same place, whether or not you have started it.",
    ],
  },
  {
    date: "2026-08-04",
    items: [
      "Notes are written thoughts rather than bare markers: a note keeps its place in the chapter and opens back to the sentence that prompted it.",
      "The transcript moved into the player, beside the episode it belongs to.",
    ],
  },
];
