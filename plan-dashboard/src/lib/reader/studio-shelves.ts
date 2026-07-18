/**
 * studio-shelves.ts — view-model builder for the Studio landing (book picker).
 * Extracted from src/pages/studio.astro's 199-line frontmatter (R2 of the
 * clean-code hardening plan), following the studio-pipeline.ts pattern.
 * The page destructures buildStudioShelves()'s result under the template's
 * long-standing names — zero template change.
 */

import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { cardMetaFor } from "../book-card-meta";
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
};

export async function buildStudioShelves() {
  const allContent = await listContent();

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
      const bm = cardMetaFor(b.slug);
      const volM = VOL_RE.exec(b.slug);
      const volOrder = volM ? Number(volM[2]) : null;
      return {
        slug: b.slug,
        title: bm.displayTitle ?? slugToTitle(b.slug),
        bucket: b.bucket,
        steps,
        entry,
        statusBucket,
        nativeTitle: bm.nativeTitle,
        nativeLang: bm.nativeLang,
        author: bm.author,
        icon: bm.icon ?? "fa-book",
        blurb: bm.blurb,
        volume: bm.volume,
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
    title: string;
    nativeTitle?: string;
    nativeLang?: string;
    author?: string;
    icon: string;
    volumes: Card[];
  };
  type ShelfItem = { kind: "card"; card: Card } | { kind: "deck"; deck: Deck };

  function buildItems(shelfCards: Card[]): ShelfItem[] {
    const decks = new Map<string, Deck>();
    const items: ShelfItem[] = [];
    for (const c of shelfCards) {
      if (c.seriesSlug) {
        let d = decks.get(c.seriesSlug);
        if (!d) {
          const sm = cardMetaFor(c.seriesSlug);
          d = {
            seriesSlug: c.seriesSlug,
            title: sm.displayTitle ?? slugToTitle(c.seriesSlug),
            nativeTitle: sm.nativeTitle,
            nativeLang: sm.nativeLang,
            author: sm.author,
            icon: sm.icon ?? "fa-layer-group",
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
    for (const d of decks.values())
      d.volumes.sort((a, b) => (a.volumeOrder ?? 0) - (b.volumeOrder ?? 0));
    return items;
  }

  const shelves = BUCKETS.map((bucket) => {
    const shelfCards = cards
      .filter((c) => c.bucket === bucket)
      .sort((a, b) => a.title.localeCompare(b.title));
    return {
      bucket,
      meta: SHELF_META[bucket],
      items: buildItems(shelfCards),
      cards: shelfCards,
    };
  }).filter((s) => s.cards.length > 0);

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
