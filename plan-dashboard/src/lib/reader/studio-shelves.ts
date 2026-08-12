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

import {
  resolveBookCardIdentity,
  type BookCardIdentity,
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
  type StatusBucket,
} from "./studio-pipeline";

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
  return {
    pdfGenerated,
    podcastGenerated,
    augmented,
    episodeCount: episodeFiles.length,
  };
}

const SHELF_META: Record<
  Bucket,
  { icon: string; label: string; desc: string }
> = {
  Islamic: {
    icon: "fa-mosque",
    label: "Islamic Scholarship",
    desc: "Scholarly texts, commentaries, and spiritual works",
  },
  Fiction: {
    icon: "fa-scroll",
    label: "Fiction & Narrative",
    desc: "Literature, storytelling, and imaginative works",
  },
  Technical: {
    icon: "fa-code",
    label: "Technical",
    desc: "Engineering, architecture, and technical guides",
  },
  Guides: {
    icon: "fa-compass",
    label: "Guides & References",
    desc: "Practical guides, explainers, and reference materials",
  },
  Supplications: {
    icon: "fa-hands-praying",
    label: "Supplications",
    desc: "Du'a, ziyarat, and munajat as facing-column reading editions",
  },
  Sessions: {
    icon: "fa-chalkboard-user",
    label: "Sessions",
    desc: "Lectures Asif delivered himself, read from the transcripts he marked up",
  },
};

export async function buildStudioShelves() {
  const allContent = await listContent();

  /** Series slug -> the series' own directory (a volume's parent). Kept here
   *  rather than on each card so no absolute path enters the view model. */
  const seriesDirs = new Map<string, string>();
  for (const b of allContent) {
    const m = VOL_RE.exec(b.slug);
    if (m) seriesDirs.set(m[1], join(b.dir, ".."));
  }

  const cards = await Promise.all(
    allContent.map(async (b) => {
      const steps = await loadStudioPipeline(b.slug);
      const statusBucket = await loadStatusBucket(b.slug, b.status);
      const blocked = steps.find((s) => s.state === "blocked");
      const active = steps.find((s) => s.state === "active");
      const entry =
        blocked ??
        active ??
        (steps.every((s) => s.state === "done") ? steps[3] : steps[0]);
      const volM = VOL_RE.exec(b.slug);
      const volOrder = volM ? Number(volM[2]) : null;
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
        statusBucket,
        identity,
        ...generation,
        // Multi-volume series fields (null for standalone books).
        seriesSlug: volM ? volM[1] : null,
        volumeOrder: volOrder,
        volumeLabel: volOrder ? await readVolumeLabel(b.dir, volOrder) : "",
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
          const identity = await resolveBookCardIdentity(
            c.seriesSlug,
            seriesDirs.get(c.seriesSlug) ?? "",
            slugToTitle(c.seriesSlug),
          );
          d = {
            seriesSlug: c.seriesSlug,
            identity: { ...identity, icon: identity.icon, volume: undefined },
            statusLabel: "",
            steps: [],
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
    }
    return items;
  }

  const shelves = (
    await Promise.all(
      BUCKETS.map(async (bucket) => {
        const shelfCards = cards
          .filter((c) => c.bucket === bucket)
          .sort((a, b) => a.title.localeCompare(b.title));
        return {
          bucket,
          meta: SHELF_META[bucket],
          items: await buildItems(shelfCards),
          cards: shelfCards,
        };
      }),
    )
  ).filter((s) => s.cards.length > 0);

  /** Status filter buttons — MULTI-select facets; ALL on by default so no book is
   *  ever hidden on arrival. Toggling a chip adds/removes that status from the view. */
  const STATUS_FILTERS: {
    id: StatusBucket;
    icon: string;
    label: string;
    hint: string;
    defaultOn: boolean;
  }[] = [
    {
      id: "in-the-works",
      icon: "fa-gears",
      label: "In Pipeline",
      hint: "Books actively moving through the pipeline",
      defaultOn: true,
    },
    {
      id: "published",
      icon: "fa-circle-check",
      label: "Published",
      hint: "Live in the library",
      defaultOn: true,
    },
    {
      id: "up-next",
      icon: "fa-hourglass-start",
      label: "Up Next",
      hint: "Scaffolded volumes where work has not begun",
      defaultOn: true,
    },
  ];

  const statusCount = (id: StatusBucket) =>
    cards.filter((c) => c.statusBucket === id).length;
  const defaultOn = new Set(
    STATUS_FILTERS.filter((f) => f.defaultOn).map((f) => f.id),
  );
  const visibleInShelf = (shelfCards: typeof cards) =>
    shelfCards.filter((c) => defaultOn.has(c.statusBucket)).length;
  return {
    cards,
    shelves,
    STATUS_FILTERS,
    statusCount,
    defaultOn,
    visibleInShelf,
  };
}
