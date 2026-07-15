/**
 * live-index.ts — book picker source for the LIVE Session view.
 *
 * Lists every book that has a reading edition (book/book.md) grouped by content
 * bucket, with multi-volume works nested under their container. Sourced from the
 * canonical `listContent()` bucket scan (content-paths.ts) — never a hardcoded book
 * list — so a new book or a new volume appears automatically (studio-composer
 * REQ-SC-012/013). Server-only (uses node:fs via listContent).
 */
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { listContent, slugToTitle } from '../content-paths';
import type { Bucket } from '../content-paths';
import { loadBookMeta } from './books';

/** Composite volume slug produced by listContent for a nested work: `<work>-vol-NN`. */
const COMPOSITE_SLUG_RE = /^(.+)-(vol-\d+)$/;

export interface LiveVolume {
  slug: string;   // the composite slug that routes to /studio/<slug>/live
  label: string;  // "Volume 2" for a work volume, "" for a standalone book
}

export interface LiveEntry {
  bucket: Bucket;
  title: string;          // work title (multi-volume) or book title (standalone)
  multiVolume: boolean;
  volumes: LiveVolume[];  // one entry for a standalone book, N for a work
}

export interface LiveBucketGroup {
  bucket: Bucket;
  entries: LiveEntry[];
}

function volumeLabel(volDir: string): string {
  const n = volDir.replace(/^vol-0*/, '');
  return `Volume ${n}`;
}

/** All books with a reading edition, grouped by bucket, works nested. */
export async function loadLiveIndex(): Promise<LiveBucketGroup[]> {
  const refs = await listContent();
  const withBook = refs.filter((r) => existsSync(join(r.dir, 'book', 'book.md')));

  // bucket -> workKey -> LiveEntry. workKey is the container slug for a volume,
  // else the book's own slug (so standalone books never collide).
  const byBucket = new Map<Bucket, Map<string, LiveEntry>>();

  for (const ref of withBook) {
    const m = COMPOSITE_SLUG_RE.exec(ref.slug);
    const bucketMap = byBucket.get(ref.bucket) ?? new Map<string, LiveEntry>();
    byBucket.set(ref.bucket, bucketMap);

    if (m) {
      const [, workSlug, volDir] = m;
      const entry =
        bucketMap.get(workSlug) ??
        {
          bucket: ref.bucket,
          title: loadBookMeta(workSlug).titleEn || slugToTitle(workSlug),
          multiVolume: true,
          volumes: [],
        };
      entry.multiVolume = true;
      entry.volumes.push({ slug: ref.slug, label: volumeLabel(volDir) });
      bucketMap.set(workSlug, entry);
    } else {
      bucketMap.set(ref.slug, {
        bucket: ref.bucket,
        title: loadBookMeta(ref.slug).titleEn || slugToTitle(ref.slug),
        multiVolume: false,
        volumes: [{ slug: ref.slug, label: '' }],
      });
    }
  }

  // Stable, human order: bucket order fixed, entries + volumes alphabetized.
  const BUCKET_ORDER: Bucket[] = ['Islamic', 'Technical', 'Fiction', 'Guides'];
  const groups: LiveBucketGroup[] = [];
  for (const bucket of BUCKET_ORDER) {
    const bucketMap = byBucket.get(bucket);
    if (!bucketMap || bucketMap.size === 0) continue;
    const entries = [...bucketMap.values()].sort((a, b) => a.title.localeCompare(b.title));
    for (const e of entries) e.volumes.sort((a, b) => a.slug.localeCompare(b.slug));
    groups.push({ bucket, entries });
  }
  return groups;
}
