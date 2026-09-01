/**
 * studio-shelves.ts — view-model builder for the Studio landing (book picker).
 * Extracted from src/pages/studio.astro's 199-line frontmatter (R2 of the
 * clean-code hardening plan), following the studio-pipeline.ts pattern.
 * The page destructures buildStudioShelves()'s result under the template's
 * long-standing names — zero template change.
 */

import { existsSync, readdirSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { parse } from "yaml";

import {
  resolveBookCardIdentity,
  type BookCardIdentity,
  type StudyTrack,
} from "./book-card-identity";
import {
  BUCKETS,
  listContent,
  slugToTitle,
  type Bucket,
} from "../content-paths";
import {
  loadStatusBucket,
  loadStudioPipeline,
  type ArticulationStatus,
  type StatusBucket,
} from "./studio-pipeline";
import { readDeclaredWorkGroups, volumeIndex } from "./work-groups";

/**
 * Studio landing — the book picker for the content pipeline.
 *
 * Books are grouped by content bucket (Islamic / Fiction / Technical / Guides),
 * each rendered as a visual bookshelf section. Each card deep-links to that
 * book's current pipeline step. Cards show:
 *   • script panel: per-book icon + native-script title (Arabic/Chinese) when available
 *   • body: English translation, author (italic), pipeline status bar
 */

// Multi-volume series: a volume slug is `<work>-vol-NN`. The per-volume prophet
// label ("Adam", "Nuh", …) lives in each volume's meta.yml title after "Volume N:".
const VOL_RE = /^(.+)-vol-(\d+)$/;
async function readVolumeLabel(dir: string, order: number): Promise<string> {
  try {
    const meta = await readFile(join(dir, "meta.yml"), "utf-8");
    const m = meta.match(/^title:\s*["']?.*Volume\s*\d+:\s*(.+?)["']?\s*$/m);
    if (m) return m[1].trim();
  } catch {
    /* fall through */
  }
  return `Volume ${order}`;
}

// Generation-status pills — a book's real, on-disk artifacts, not pipeline
// phase state (which can drift from what actually exists on disk). Mirrors
// content-paths.ts's own isDirSync + existsSync(join(...)) pattern.
function listFilesSync(dir: string): string[] {
  try {
    return readdirSync(dir);
  } catch {
    return [];
  }
}

async function readGenerationStatus(dir: string) {
  const pdfGenerated = listFilesSync(join(dir, "book")).some((f) =>
    f.toLowerCase().endsWith(".pdf"),
  );
  const episodeFiles = listFilesSync(join(dir, "episodes")).filter((f) =>
    f.toLowerCase().endsWith(".txt"),
  );
  const podcastGenerated = listFilesSync(join(dir, "m4a")).some((f) =>
    f.toLowerCase().endsWith(".m4a"),
  );
  let augmented = false;
  const reportPath = join(dir, "_system", "book-augment-report.json");
  if (existsSync(reportPath)) {
    try {
      const report = JSON.parse(await readFile(reportPath, "utf-8"));
      augmented = typeof report.accepted === "number" && report.accepted > 0;
    } catch {
      /* malformed or unreadable report — treat as not augmented */
    }
  }
  let podcastPlanned = true;
  try {
    const meta = parse(await readFile(join(dir, "meta.yml"), "utf-8"));
    if (meta?.series?.podcast_enabled === false) podcastPlanned = false;
  } catch {
    /* Missing or malformed metadata keeps the established default. */
  }
  return {
    pdfGenerated,
    podcastGenerated,
    podcastPlanned,
    augmented,
    episodeCount: episodeFiles.length,
  };
}

/** `label` names the shelf; `chipLabel` names its filter chip — short, because
 *  three facets on two rows leaves no room for "Islamic Scholarship" on a chip
 *  and the shelf heading below already says it in full. */
const SHELF_META: Record<
  Bucket,
  { icon: string; label: string; chipLabel: string; desc: string }
> = {
  Islamic: {
    icon: "fa-mosque",
    label: "Islamic Scholarship",
    chipLabel: "Islamic",
    desc: "Scholarly texts, commentaries, and spiritual works",
  },
  Fiction: {
    icon: "fa-scroll",
    label: "Fiction & Narrative",
    chipLabel: "Fiction",
    desc: "Literature, storytelling, and imaginative works",
  },
  Technical: {
    icon: "fa-code",
    label: "Technical",
    chipLabel: "Technical",
    desc: "Engineering, architecture, and technical guides",
  },
  Guides: {
    icon: "fa-compass",
    label: "Guides & References",
    chipLabel: "Guides",
    desc: "Practical guides, explainers, and reference materials",
  },
  Supplications: {
    icon: "fa-hands-praying",
    label: "Supplications",
    chipLabel: "Supplications",
    desc: "Du'a, ziyarat, and munajat as facing-column reading editions",
  },
  Sessions: {
    icon: "fa-chalkboard-user",
    label: "Sessions",
    chipLabel: "Sessions",
    desc: "Lectures Asif delivered himself, read from the transcripts he marked up",
  },
  Audiobook: {
    icon: "fa-headphones",
    label: "Audiobooks",
    chipLabel: "Audiobooks",
    desc: "Published books read aloud, timed against the recording for read-along",
  },
};

// Hidden from the Studio picker specifically (Asif, 2026-08-12): with only
// one book each, Technical and Guides & References added two mostly-empty
// shelves to scroll past to reach the ones actually being worked. This is a
// DISPLAY choice, not a content one — the bucket, its books, and every other
// bucket-driven surface (Corpus, content-paths resolution, the Python
// pipeline) are untouched; a book already in one of these buckets is still
// reachable directly at /studio/<slug>. Un-hide by removing an entry here.
const STUDIO_HIDDEN_BUCKETS: readonly Bucket[] = ["Technical", "Guides"];

export async function buildStudioShelves() {
  const allContent = await listContent();

  /** Series slug -> the series' own directory (a volume's parent). Kept here
   *  rather than on each card so no absolute path enters the view model. */
  const seriesDirs = new Map<string, string>();
  for (const b of allContent) {
    const m = VOL_RE.exec(b.slug);
    if (m) seriesDirs.set(m[1], join(b.dir, ".."));
  }

  /** The OTHER shape a multi-volume work comes in: volumes that are flat,
   *  independently published, top-level folders whose slugs say nothing about
   *  belonging together, declared instead in
   *  `content/<Bucket>/_listener-groups/*.yml`. Read here so this shelf and the
   *  Podcast Factory Library — whose stacked cards read the same file — cannot
   *  disagree about what one work is. A declared group has no parent directory,
   *  so there is nothing to add to `seriesDirs`; its deck is described entirely
   *  by the declaration and by the volumes themselves. */
  const declared = volumeIndex(await readDeclaredWorkGroups());
  /** Deck slug -> the title its declaration gives it. The one thing about a
   *  declared deck that no volume knows and nothing can derive. */
  const declaredTitles = new Map<string, string>();
  for (const entry of declared.values()) {
    declaredTitles.set(entry.workSlug, entry.title);
  }

  const cards = await Promise.all(
    allContent.map(async (b) => {
      const { steps, articulation } = await loadStudioPipeline(b.slug);
      const statusBucket = await loadStatusBucket(b.slug, b.status);
      const blocked = steps.find((s) => s.state === "blocked");
      const active = steps.find((s) => s.state === "active");
      const entry =
        blocked ??
        active ??
        (steps.every((s) => s.state === "done") ? steps[3] : steps[0]);
      // The slug shape first, then the declaration. That order matters: a
      // nested volume already knows its own work from its slug, and a
      // declaration that also named it would be a second answer to a question
      // that already has one.
      const volM = VOL_RE.exec(b.slug);
      const declaredVol = volM ? undefined : declared.get(b.slug);
      const volOrder = volM ? Number(volM[2]) : (declaredVol?.order ?? null);
      const generation = await readGenerationStatus(b.dir);
      // Identity comes from the BOOK'S OWN FILES first (2026-08-02), with the
      // hand-typed BOOK_CARD_META as a fallback. It used to come only from that
      // map, so a book got a real card only if someone had typed one —
      // degrees-of-excellence read "Not yet catalogued" while its meta.yml
      // carried both an author and an English title.
      const identity = await resolveBookCardIdentity(
        b.slug,
        b.dir,
        slugToTitle(b.slug),
      );
      return {
        slug: b.slug,
        title: identity.title,
        bucket: b.bucket,
        steps,
        entry,
        articulation,
        statusBucket,
        identity,
        ...generation,
        // Multi-volume series fields (null for standalone books).
        seriesSlug: volM ? volM[1] : (declaredVol?.workSlug ?? null),
        volumeOrder: volOrder,
        // A declared volume is a book in its own right and its meta.yml says so
        // — there is no "Volume N: <name>" line to read, because it was never
        // published as part of a set. Its own catalogued title is the truest
        // label available, and the numbered fallback is the last resort for
        // both shapes alike.
        volumeLabel: declaredVol
          ? (identity.title ?? `Volume ${volOrder}`)
          : volOrder
            ? await readVolumeLabel(b.dir, volOrder)
            : "",
      };
    }),
  );

  // Fold multi-volume series into a single collapsible "deck"; standalone books
  // stay as cards. Reusable for any work with `<work>-vol-NN` volumes.
  type Card = (typeof cards)[number];
  type Deck = {
    seriesSlug: string;
    identity: BookCardIdentity;
    /** The series' own pipeline line, aggregated from its volumes — a deck has
     *  no orchestrator state of its own, and the alternative (no status line at
     *  all) is what made a deck look like a different design. */
    statusLabel: string;
    steps: { state: string }[];
    /** The series' own articulation stage — same laggard rule as `steps`
     *  below: a deck is only as far along as its least-advanced volume. */
    articulation: ArticulationStatus;
    volumes: Card[];
  };
  type ShelfItem = { kind: "card"; card: Card } | { kind: "deck"; deck: Deck };

  async function buildItems(shelfCards: Card[]): Promise<ShelfItem[]> {
    const decks = new Map<string, Deck>();
    const items: ShelfItem[] = [];
    for (const c of shelfCards) {
      if (c.seriesSlug) {
        let d = decks.get(c.seriesSlug);
        if (!d) {
          // The series directory is the volume's parent, so a series reads its
          // own work.yml/meta.yml exactly as a standalone book reads its own.
          // Looked up rather than carried on the card: `dir` is an absolute
          // filesystem path and the card view model is rendered into markup.
          //
          // A DECLARED deck has no such directory — its volumes are top-level
          // folders and the work exists only as a statement in a manifest — so
          // the resolver reads nothing and returns the slug-derived placeholder.
          // The declaration's own title replaces that; everything else it cannot
          // know is derived from the volumes below, where they agree.
          const declaredTitle = declaredTitles.get(c.seriesSlug);
          const identity = await resolveBookCardIdentity(
            c.seriesSlug,
            seriesDirs.get(c.seriesSlug) ?? "",
            declaredTitle ?? slugToTitle(c.seriesSlug),
          );
          d = {
            seriesSlug: c.seriesSlug,
            identity: {
              ...identity,
              title: declaredTitle ?? identity.title,
              icon: identity.icon,
              volume: undefined,
            },
            // Filled below from the volumes, once they are all collected.
            statusLabel: "",
            steps: [],
            articulation: { stage: "none", at: null },
            volumes: [],
          };
          decks.set(c.seriesSlug, d);
          items.push({ kind: "deck", deck: d });
        }
        d.volumes.push(c);
      } else {
        items.push({ kind: "card", card: c });
      }
    }
    for (const d of decks.values()) {
      d.volumes.sort((a, b) => (a.volumeOrder ?? 0) - (b.volumeOrder ?? 0));
      // A series' own track, DERIVED rather than recorded: the deck wears its
      // volumes' ribbon when they all agree, and none when they do not. A
      // mixed series has no single subject, and painting it with the first
      // volume's would state something no file says. Derived also means the
      // two can never drift — there is no container field to forget to update
      // when a volume's track changes. (asaas-al-taveel has no work.yml at
      // all; its six volumes each say `esoteric`, and that is where the deck's
      // ribbon comes from.)
      //
      // The same rule now covers the native-script title, the author and the
      // icon, for the same reason and by the same test. A DECLARED deck has no
      // directory to read any of them from, so without this its card would show
      // an English title over an empty script panel while both its volumes
      // display the identical Arabic — the set looking less catalogued than the
      // books inside it. Agreement is the whole condition: where the volumes
      // differ the deck says nothing, exactly as it does for a mixed track.
      // TWO rules, and the difference between them is deliberate.
      //
      // `agreed` is strict: a volume that says NOTHING counts as a
      // disagreement. That is the right test for the track, which is the
      // pre-existing rule above and answers "what is this work about" — a
      // question a silent volume genuinely leaves open.
      //
      // `agreedStated` ignores the silent volumes and asks only whether the
      // ones that DO speak say the same thing. That is the right test for a
      // work's author, its title in its own script, and its icon, which are
      // properties of the WORK: Mukhtasar's second volume records its author
      // and its first does not, and the two are unquestionably the same book by
      // the same hand. Under the strict rule the set would show no author while
      // a volume inside it showed one — the parent looking less catalogued than
      // its own children.
      const agreed = <T>(pick: (v: Card) => T | undefined): T | undefined => {
        const values = new Set(d.volumes.map(pick));
        return values.size === 1 ? [...values][0] : undefined;
      };
      const agreedStated = <T>(
        pick: (v: Card) => T | undefined,
      ): T | undefined => {
        const values = new Set(
          d.volumes.map(pick).filter((v) => v !== undefined),
        );
        return values.size === 1 ? [...values][0] : undefined;
      };
      if (!d.identity.studyTrack) {
        const only = agreed((v) => v.identity.studyTrack);
        if (only) d.identity = { ...d.identity, studyTrack: only };
      }
      if (!d.identity.nativeTitle) {
        const native = agreedStated((v) => v.identity.nativeTitle);
        if (native) {
          d.identity = {
            ...d.identity,
            nativeTitle: native,
            nativeLang: agreedStated((v) => v.identity.nativeLang),
          };
        }
      }
      if (!d.identity.author) {
        const author = agreedStated((v) => v.identity.author);
        if (author) d.identity = { ...d.identity, author };
      }
      // `resolveBookCardIdentity` never returns a bare icon — "fa-book" is its
      // last resort — so the default is what "says nothing" looks like here,
      // and a volume still sitting on it must not outvote one with a real icon.
      if (d.identity.icon === "fa-book") {
        const icon = agreedStated((v) =>
          v.identity.icon === "fa-book" ? undefined : v.identity.icon,
        );
        if (icon) d.identity = { ...d.identity, icon };
      }
      // A deck assembled from real, catalogued volumes is not uncatalogued,
      // whatever the empty directory behind it implied.
      if (
        d.identity.uncatalogued &&
        d.volumes.some((v) => !v.identity.uncatalogued)
      ) {
        d.identity = { ...d.identity, uncatalogued: false };
      }
      // The series is only as far along as its least-advanced volume; saying
      // otherwise would make a deck look finished while five volumes sit at
      // intake. The bar is that volume's own, so the two never disagree.
      const laggard = d.volumes.reduce((worst, v) =>
        v.steps.filter((s) => s.state === "done").length <
        worst.steps.filter((s) => s.state === "done").length
          ? v
          : worst,
      );
      const done = d.volumes.filter((v) =>
        v.steps.every((s) => s.state === "done"),
      ).length;
      d.statusLabel =
        done === d.volumes.length
          ? `All ${d.volumes.length} volumes complete`
          : `${done} of ${d.volumes.length} complete · ${laggard.entry.label}`;
      d.steps = laggard.steps;
      d.articulation = laggard.articulation;
    }
    return items;
  }

  const shelves = (
    await Promise.all(
      BUCKETS.filter((bucket) => !STUDIO_HIDDEN_BUCKETS.includes(bucket)).map(
        async (bucket) => {
          const shelfCards = cards
            .filter((c) => c.bucket === bucket)
            .sort((a, b) => a.title.localeCompare(b.title));
          return {
            bucket,
            meta: SHELF_META[bucket],
            items: await buildItems(shelfCards),
            cards: shelfCards,
          };
        },
      ),
    )
  ).filter((s) => s.cards.length > 0);

  /**
   * One entry per thing the shelf actually DRAWS — a standalone book, or a
   * series deck counted once rather than once per volume.
   *
   * Every filter count is measured over this, not over `cards`, because a chip's
   * number is a promise about what pressing it will show. Counted over `cards`
   * the promises were all wrong in the same direction: "Esoteric 7" for a shelf
   * that draws two esoteric things (one book and one six-volume deck), and "All
   * 25" for a shelf of thirteen. The volumes are real content and they are still
   * reachable — inside the deck, where the deck's own row filters them — but
   * they are not what the grid lays out.
   */
  type Unit = {
    bucket: Bucket;
    status: StatusBucket | "always";
    track: StudyTrack | undefined;
  };
  const units: Unit[] = shelves.flatMap((s) =>
    s.items.map((it): Unit =>
      it.kind === "deck"
        ? {
            bucket: s.bucket,
            // A deck has no single status of its own — its volumes each carry
            // theirs — so it is never hidden by the status facet, and the same
            // word the markup uses is the one counted here.
            status: "always",
            track: it.deck.identity.studyTrack,
          }
        : {
            bucket: s.bucket,
            status: it.card.statusBucket,
            track: it.card.identity.studyTrack,
          },
    ),
  );

  /**
   * The three filter facets — SINGLE-select each, "All" by default, and they
   * narrow together (a category AND a status AND a track).
   *
   * Single-select, matching the Podcast Factory Library's find row, replaces a
   * multi-select model that was backwards in practice: every chip started ON,
   * so clicking "Published" REMOVED the published books. That is the opposite
   * of what a filter chip promises, and the pressed styling made the chip you
   * had just switched off look like the selected one.
   *
   * `count` is measured against the WHOLE shelf, never the filtered view — a
   * chip that renumbered itself as you filtered would flicker, and the number
   * is there to tell you what choosing it would give you. An option with none
   * is rendered DISABLED rather than dropped: the taxonomy is the point, and a
   * list that changes length as books move through the pipeline teaches less
   * than one that keeps its shape.
   */
  const STATUS_FILTERS: {
    id: StatusBucket;
    icon: string;
    label: string;
    hint: string;
  }[] = [
    {
      id: "in-the-works",
      icon: "fa-gears",
      // Short labels (Asif, 2026-08-15): three facets on two rows leaves no
      // room for a sentence per chip, and the icon beside it already carries
      // half the meaning. The full sense lives in `hint`, which is the chip's
      // title attribute.
      label: "Pipeline",
      hint: "Books actively moving through the pipeline",
    },
    {
      id: "published",
      icon: "fa-circle-check",
      label: "Published",
      hint: "Live in the library",
    },
    {
      id: "up-next",
      icon: "fa-hourglass-start",
      label: "Up next",
      hint: "Scaffolded volumes where work has not begun",
    },
  ];

  /** The five subject tracks, in the Library's own display order —
   *  foundational to concrete, deliberately not alphabetical. */
  const TRACK_FILTERS: { id: StudyTrack; label: string; hint: string }[] = [
    { id: "history", label: "History", hint: "Historical works and accounts" },
    { id: "shariah", label: "Shariah", hint: "Law, practice, and observance" },
    {
      id: "theology",
      label: "Theology",
      hint: "Doctrine, belief, and the foundations",
    },
    {
      id: "esoteric",
      label: "Esoteric",
      hint: "Inner meaning and interpretation",
    },
    { id: "reality", label: "Reality", hint: "Metaphysics and the real" },
  ];

  // A deck is counted into EVERY status, because it is shown under every one —
  // the number and the outcome have to agree, and "Published 3" on a shelf that
  // draws five things when you press it is the same broken promise in the other
  // direction.
  const statusCount = (id: StatusBucket) =>
    units.filter((u) => u.status === id || u.status === "always").length;
  const trackCount = (id: StudyTrack) =>
    units.filter((u) => u.track === id).length;
  const bucketCount = (bucket: Bucket) =>
    units.filter((u) => u.bucket === bucket).length;

  return {
    cards,
    shelves,
    STATUS_FILTERS,
    TRACK_FILTERS,
    statusCount,
    trackCount,
    bucketCount,
    /** Everything the shelf draws, for the three "All" chips. */
    totalCount: units.length,
  };
}
