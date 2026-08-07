# Design brief — Podcast Factory Library

**Hand this whole file over as the prompt.** It is self-contained: the designer
needs no access to the codebase. Everything below is real — real book titles,
real chapter titles, real prose, real constraints. Nothing is placeholder.

## How to run it in Claude Design

- **Attach no design system.** Set it to none. This brief *is* the design system,
  and a pre-made one will quietly override the Verdigris palette and the type
  stack — which are the two things most worth reviewing.
- **Template: none.** Same reason.
- **Paste this line into the prompt box** alongside the attached file, so the
  brief is read as an instruction rather than as reference material:

  > Follow the attached brief exactly — its palette, typefaces and content are
  > fixed, not suggestions. Do not substitute colours or fonts, and do not add
  > screens listed as out of scope. Start with the book detail screen and the
  > reading screen at 1440px and 390px, in all three themes. Show me those two
  > before going further.

- **Do it in passes.** The brief covers 14 screens across three themes and two
  breakpoints; asked for in one go, the later screens get thin. Two screens
  first, correct the direction, then continue.

---

## The prompt

I need high-fidelity UI mockups for a web app called **Podcast Factory
Podcast Factory Library**. I will build the real thing from your mockups, so I need to see what
it will actually look like before I commit to it.

### What the product is

A small, private library site. One person translates classical Arabic and
Islamic scholarly books into English reading editions, and generates podcast
episodes discussing each book. This site is where a hand-picked audience —
maybe a few dozen people — comes to **listen** to those episodes, **read** the
translated editions, **download** the print PDFs, and **take private notes** on
what they read.

It is invite-only. Nothing is public and nothing is indexed by search engines.
There is no signup, no pricing, no marketing page. A visitor either has an
invitation or sees a polite "ask for access" screen.

The register is **serious scholarship, not a media product**. Think a
university press's digital reading room. Calm, typographic, unhurried. It should
feel like something you'd sit with for an hour, not something that wants your
attention.

### Non-negotiable design system

Use these exact values. Do not substitute, do not "improve" the palette, do not
add a second accent colour.

**Palette — "Verdigris"** (warm-neutral stone, aged-copper accent). Three real
themes, all of which must be designed; sepia is a first-class reading theme, not
a filter over light.

| Token | Light | Dark | Sepia |
|---|---|---|---|
| Page background | `#F4F4F1` | `#0B0F0E` | `#EFE7D8` |
| Card / surface | `#FCFCFA` | `#131A18` | `#F5EFE3` |
| Raised surface | `#FFFFFF` | `#1A2422` | `#FBF6EC` |
| Sunken / inset | `#E9E9E4` | `#070A09` | `#E4DAC7` |
| Body text | `#1A1C1A` | `#E6ECEA` | `#33291C` |
| Secondary text | `#5C625C` | `#90A09C` | `#6B5F4C` |
| Tertiary text | `#666D66` | `#74837F` | `#6F624C` |
| Hairline rule | `#D6D7D0` | `#26312E` | `#D8CDB8` |
| Accent | `#0F6E62` | `#3FBFAE` | `#14655A` |
| Text on accent | `#FFFFFF` | `#05201C` | `#FBF6EC` |
| Highlight (note) | `#EFCF87` | `#7C6224` | `#E0BC6E` |

**Type** — three families, all open-licence and self-hosted:

- **Literata** — all prose, all headings. It has an optical-size axis, so it
  stays correctly proportioned from 14px to 60px.
- **IBM Plex Sans** — all UI: nav, buttons, labels, metadata, form controls.
- **Scheherazade New** — all Arabic script. Critically: **this corpus is fully
  vowelled**, meaning diacritical marks stack above *and* below the baseline.
  Arabic runs need roughly `line-height: 2.1` where the surrounding English uses
  `1.7`. Get this wrong and the marks collide.
- **OpenDyslexic** must be offered as a font choice in the reader.

**Accessibility floor:** every text/background pair must clear **4.5:1**. I have
already had to fix three tokens that failed this. Do not hand me a mockup with
grey-on-grey secondary text that fails.

**Motion:** minimal. Never animate reading text — people get motion-sick. Honour
`prefers-reduced-motion`.

### The two structural problems I need you to solve

These are the real reasons I need a designer, not a template.

**1. Chapters and episodes are not the same thing, and do not map 1:1.**

Take the book *Degrees of Excellence: A Treatise on Affirming the Imamate*. As a
reading edition it has **9 chapters**:

1. The Pole and Foundation of Religion
2. By Nature and by Reason
3. Degrees of Excellence
4. The Ladder of Creation
5. The Physician of Souls
6. Governance and the First Principle
7. The Imam in the Pillars of Faith
8. From Adam to Ali
9. God's Vicegerent in His Time

But as a podcast it has **6 episodes**, drawn along different lines:

1. The Imamate: Pole and Foundation of Religion
2. Degrees of Excellence: The Peak of Every Kind
3. The Imam and the Authority over Sacred Law
4. Worship, Alms and War: Void without the Imam
5. Prophets as Symbols and the First Caliphs
6. The Virtues of Ali: The Imam who Mirrors God

A reader who finishes episode 3 and wants to "read that bit" needs to land
somewhere sensible. Show me how the book page presents these two different
groupings of the same work without making the user feel they've found two
different products. This is the single most important thing in the brief.

**2. Arabic runs inline, mid-sentence, inside English prose.**

This is a genuine paragraph from the reading edition — design against it, not
against lorem ipsum:

> In the Name of God, this book undertakes a single task, and its original title
> names that task exactly. *Kitab ithbat al-imama* means the demonstration of the
> imamate (الْإِمَامَة) — *ithbat* being the establishing of a claim by proof, and
> the imamate the necessity of a divinely appointed guide standing at the center
> of religion in every age.
>
> The work is ascribed to Ahmad b. Ibrahim al-Naysaburi (اَلنَّيْسَابُورِي), a scholar
> of the Ismaili tradition as it flourished under the Fatimids…

So: right-to-left script inside a left-to-right sentence, in parentheses, next to
italic transliteration, at a larger effective size and looser line-height than
the Latin around it — without making the paragraph's leading look ragged. Show
me a full page of this set properly, in all three themes.

### The real library (use these, not invented titles)

| Title | Arabic | Has audio? | Has PDF? | Has slides? |
|---|---|---|---|---|
| Ayyuha al-Walad | أيُّها الولد | no | no | no |
| The Master and the Disciple | كتاب العالم والغلام | no | yes | **yes — 15 pages** |
| Degrees of Excellence: A Treatise on Affirming the Imamate | كتاب إثبات الإمامة | 4 of 6 episodes | yes | no |
| Kitāb al-Riyāḍ | كتاب الرياض | no | no | no |
| Kunooz al Hikmah | كنوز الحكمة | no | no | no |
| Mukhtasar ul Asar | مختصر الآثار | no | yes | no |

**Design for this raggedness — it is the normal state, not an edge case.** Most
books are missing most things. A book with no audio must not look broken; a book
with no slide deck simply has no Slides tab. Only one book in the whole library
has a real slide deck, and it is a whole-book deck, not per-episode. One book has
audio for only 4 of its 6 episodes.

### Screens to mock

For each: **desktop 1440px** and **mobile 390px**. Tablet 834px only where the
layout genuinely differs.

1. **Sign in** — one button, "Continue with Google". Nothing else. This is the
   first impression; make it beautiful and confident rather than empty.
2. **No access** — a signed-in Google user who is not on the invite list. Warm,
   not accusatory. Tells them how to ask.
3. **Home** — "continue listening" and "continue reading" rails for work in
   progress, then the library. If nothing is in progress, this must not look
   like an error.
4. **Library** — all books. Show cover, title, Arabic title, and honest badges
   for what each contains. Consider how a 6-item library looks now versus 40 later.
5. **Book detail** — the hard one. Cover, blurb, and the chapters-vs-episodes
   problem above. Plus PDF download (label it with the file size), and the Slides
   tab where one exists.
6. **Listening** — an episode playing. Plus the **persistent player** in two
   states: a mini-bar that survives navigation across the whole site, and an
   expanded view. Controls: play/pause, skip back 15s, skip forward 15s, a
   scrubber, playback speed, and the episode's chapter markers on the scrub bar.
   **No volume slider** — iOS silently ignores it, so it must not exist.
7. **Reading** — a chapter of the edition. Continuous scroll, not pagination.
   Include: a thin progress bar, "about 14 minutes left in this chapter", the
   running chapter title.
8. **Reader settings** — a bottom sheet on mobile, a popover on desktop. Theme
   (three swatches), font family (with live previews, including OpenDyslexic),
   font size (an A/A stepper — **not** a slider, sliders are unusable one-handed),
   line height and line width (three presets each). Everything applies live
   behind the sheet; there is no Apply button.
9. **Table of contents drawer** — current chapter highlighted, note count per
   chapter as a small badge.
10. **Selecting text** → a floating toolbar (Highlight in four colours · Note ·
    Copy). On touch it must sit **above** the selection, not under the thumb.
    Then the note-writing popover.
11. **My notes** — all highlights and notes across all books, grouped by book.
    Include the **"notes without a home"** tray described below.
12. **Slides** — a page-image viewer for the one book that has a deck: swipe or
    arrow through 15 pages, thumbnail rail, full-screen.
13. **Account / settings** — sign out, reading preferences, and nothing else.
14. **Admin: invitations** — only I see this. A list of invited email addresses,
    add one, revoke one. Deliberately plain.

### The "notes without a home" state — please design this carefully

The books get revised. When a chapter is rewritten, a note anchored to a
sentence that no longer exists is **never deleted** — it is kept, with the
original quoted text, and surfaced for the reader to re-attach with one tap.

Show me three visual states for an annotation:
- **Fine** — normal highlight.
- **Text has changed** — re-attached, but the surrounding wording shifted.
  Something quieter than an error; a dotted underline, perhaps.
- **Homeless** — the passage is gone. Shown in a tray with its original quote and
  a "find this passage" action.

Losing someone's note on a religious text they've studied is unacceptable, and
the design should communicate that it hasn't happened.

### Also show me these states

Designers skip these and then I discover them in production: **empty** (no notes
yet, nothing in progress, a book with no audio), **loading** (skeletons for the
library and a chapter), **error** (an episode that won't play), and **focus** —
every interactive element needs a visible keyboard focus ring in all three themes.

### The logo

Three candidate marks exist and I have not chosen. All are pure geometry — no
crescent-and-star, no mosque silhouette, nothing figurative or animate.

- **Strapwork** *(current default)* — an eight-fold interlaced knot drawn as one
  continuous ribbon: an octagon and a square woven through each other, strands
  alternately breaking to pass under, with a solid accent-coloured dot at the
  centre. Wordmark: "Podcast" in Literata with "FACTORY" letterspaced small
  beneath it.
- **Colophon** — five rounded vertical bars (a level meter) whose rhythm
  continues to the right as three horizontal rules of decreasing length (a
  paragraph). Wordmark: "Podcast" in ink, "Factory" in accent, side by side.
- **Qalam** — a reed pen nib abstracted to an oblique parallelogram split by its
  slit, at the head of three horizontal rules. Wordmark: "PODCAST FACTORY"
  letterspaced, with a hairline rule beneath.

Use **Strapwork** in the mockups, but show all three in a header lockup at 44px
and as a 16px favicon so I can judge them in place.

### Explicitly out of scope — do not design these

Offline downloads, any "download for offline" affordance, PWA install prompts,
favourites or likes, a command palette, social sharing, comments, ratings,
recommendations, or a public marketing page. If you think one is essential, say
so in a note — do not add it to the mockups.

### What I want back

1. **Self-contained HTML mockups** I can open in a browser — inline CSS is fine,
   no build step. One file per screen, or one long page with anchors. Use the
   exact hex values and font names above. Real content throughout: the titles,
   chapters and paragraph I gave you.

   **Load the three typefaces from Google Fonts** — Literata, IBM Plex Sans and
   Scheherazade New are all available there. Do not substitute a system fallback.
   The entire point of these mockups is to judge the typography, and Scheherazade
   New is the only face here engineered for fully-vowelled Arabic; rendered in a
   fallback the diacritics will collide and I will be reviewing a lie. (The
   production site self-hosts all three — a CDN link is fine for a mockup.)
2. **A working theme switcher** in the mockups so I can flip light / sepia / dark
   and see all three for real.
3. **A short component inventory** — the reusable pieces you ended up with
   (book card, episode row, player bar, settings sheet, annotation popover,
   empty state…), with the states each one needs.
4. **A one-paragraph rationale for the chapters-vs-episodes solution**, since
   that is the decision I most need to understand before building.

Start with the **book detail** screen and the **reading** screen. Those two carry
the product; if they are right, the rest follows.
