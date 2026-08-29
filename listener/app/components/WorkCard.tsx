import { useState, useSyncExternalStore } from "react";

import { BookBand, BookCard } from "~/components/BookCard";
import { collectionOf } from "~/lib/collection";
import type { CardPlayableEpisode, LibraryCard } from "~/server/catalog.server";
import type { Progress } from "~/server/marks.server";

/**
 * Which volume of a work stands as the card's picked cover.
 *
 * A reader's own display preference, not data — the same reasoning
 * `home.tsx`'s `pf-library-view`/`pf-library-collection` keys use, and the
 * same `pf-marks:<slug>` colon-keying `lib/marks.ts` uses to keep one book's
 * cache from colliding with another's. Keying on `work_slug` is what keeps
 * picking a volume in one series from ever touching another series' card.
 * Deliberately separate from that reading-progress cache: this never talks
 * to the server, never touches `content_unit`/`access_grant`, and is purely
 * "which volume do I see", not "where did I get to".
 */
const frontVolumeKey = (workSlug: string) => `pf-work-front:${workSlug}`;

/**
 * Which volume was picked last time, and the store that hands it to the card.
 *
 * NOT read during render, which is what it was until now — and that mattered
 * more here than anywhere: this is the shelf's DEFAULT view, so any reader who
 * had ever picked a volume in a multi-volume work got a first client render the
 * server's HTML could not match. React rebuilt the document, and `data-theme` —
 * which THEME_INIT_SCRIPT stamps on `<html>` before first paint, and which no
 * React tree owns — went with it, silently reverting that reader's colour theme
 * and dropping session cards out of violet.
 *
 * So it is read through `useSyncExternalStore`, exactly as `~/lib/shelf` and
 * `~/lib/theme` are: the server and the hydrating client both render the picker,
 * and the remembered volume arrives in the commit straight after hydration. The
 * snapshot is cached per work because `getSnapshot` is compared by identity and
 * is called on every render — reading storage each time would return a fresh
 * value and re-render forever.
 */
const picked = new Map<string, string | null>();
const listeners = new Set<() => void>();

function frontVolumeSnapshot(workSlug: string): string | null {
  if (!picked.has(workSlug)) {
    try {
      picked.set(workSlug, localStorage.getItem(frontVolumeKey(workSlug)));
    } catch {
      picked.set(workSlug, null);
    }
  }
  return picked.get(workSlug) ?? null;
}

function subscribeFrontVolume(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function saveFrontVolume(workSlug: string, slug: string) {
  picked.set(workSlug, slug);
  try {
    localStorage.setItem(frontVolumeKey(workSlug), slug);
  } catch {
    // A reader whose storage is full or blocked still gets the pick for
    // this visit — it just doesn't survive to the next one. Same
    // best-effort shape as the setters in `~/lib/shelf`.
  }
  for (const listener of listeners) listener();
}

/** Chips are capped so the closed card stays a fixed, compact size — the
 * final slot becomes a "+N" summary once a work has more volumes than that.
 * Asas al-Taveel already runs 6 volumes; the cap is set to 12 so every
 * multi-part series in the library today fits without ever hitting the
 * overflow slot, while still bounding a single card's size against
 * whatever the next series turns out to need. */
const CHIP_CAP = 12;

/** One volume of a work, carrying exactly what `BookCard` needs to render it. */
export interface WorkVolume {
  slug: string;
  title: string;
  bucket: string;
  card: LibraryCard | null;
  progress?: Progress | null;
  listen?: {
    mode: "resume" | "start";
    episode: CardPlayableEpisode;
    seconds: number | null;
  } | null;
  marks?: { notes: number; bookmarks: number } | null;
}

/**
 * A multi-volume work, standing as one card until a reader has a volume in
 * mind — or has already picked one, this visit or a past one.
 *
 * Only rendered by the caller when 2+ VISIBLE volumes share a `work_slug` — a
 * lone volume (including a work reduced to one visible volume by access
 * grants) renders as a plain `BookCard`, unchanged, and this component never
 * sees it.
 *
 * Two states, never a separate page or overlay for either:
 *  - PICKER (no volume picked yet, or the reader asked to change it): the
 *    work's own band and title, with a small numbered-chip panel underneath —
 *    one chip per volume, tap one to pick it.
 *  - SELECTED (a volume is picked): a real, fully functional `BookCard` for
 *    that volume — its own cover, its own read/play/notes actions, its own
 *    progress — with a small "change volume" button layered on top to go
 *    back to the picker. This is the same card position and the same two
 *    decorative leaves behind it in both states, so the set never stops
 *    reading as a set.
 *
 * A picked volume is remembered per work (`localStorage`), so a returning
 * reader lands straight on SELECTED — the picker is a one-time cost, not a
 * repeated one. There is deliberately no fanned-out overlay here anymore:
 * the chip panel does that job in less space and without the viewport-edge
 * math an absolutely positioned overlay needed.
 */
export function WorkCard({
  workSlug,
  title,
  volumes,
}: {
  workSlug: string;
  title: string;
  volumes: WorkVolume[];
}) {
  // The picker on the server and on the first client render alike; the
  // remembered volume immediately after hydration. See `frontVolumeSnapshot`
  // above for why it may not be read any earlier than that.
  const frontSlug = useSyncExternalStore(
    subscribeFrontVolume,
    () => frontVolumeSnapshot(workSlug),
    () => null,
  );
  // Session-only "I want to see the picker again" — distinct from
  // `frontSlug` so opening it to look around, then leaving without tapping a
  // chip, never erases an already-remembered pick.
  const [pickerOpen, setPickerOpen] = useState(false);

  const count = volumes.length;
  const front =
    frontSlug === null
      ? null
      : (volumes.find((v) => v.slug === frontSlug) ?? null);
  const showPicker = pickerOpen || front === null;

  function pickFront(slug: string) {
    saveFrontVolume(workSlug, slug);
    setPickerOpen(false);
  }

  const chipVolumes =
    count <= CHIP_CAP ? volumes : volumes.slice(0, CHIP_CAP - 1);
  const overflowCount = count > CHIP_CAP ? count - (CHIP_CAP - 1) : 0;

  // The same bucket driving whichever band is currently showing (the picked
  // volume's, or `volumes[0]`'s while nothing is picked yet) — so the badge
  // and the change button pick up that book's own collection accent
  // (`collectionOf`, the one function the card, the book page and the
  // player all already call) instead of a colour invented for this card.
  // A Sessions work reads violet here for the same reason a Sessions
  // `BookCard` already does; an Islamic one reads its theme's default blue.
  const collection = collectionOf((front ?? volumes[0]!).bucket);

  return (
    <div
      className="pf-work"
      data-work-slug={workSlug}
      data-front-slug={front?.slug ?? ""}
      data-collection={collection}
    >
      <span className="pf-work-leaf pf-work-leaf--back" aria-hidden="true" />
      <span className="pf-work-leaf pf-work-leaf--mid" aria-hidden="true" />

      {showPicker ? (
        <>
          <div className="pf-work-picker">
            <BookBand
              title={title}
              bucket={volumes[0]!.bucket}
              card={volumes[0]!.card}
            />
            <div className="pf-work-picker__body">
              <h3 className="pf-work-picker__title">{title}</h3>
              {/* Was "{count}-volume set" — purely restated the tag's own
                  number back at the reader without telling them what to DO
                  here. Instruction earns this line's space better than a
                  fact the tag already carries. */}
              <p className="pf-work-picker__sub">Tap a volume to open it</p>
              <div className="pf-work-chip-wrap">
                <div
                  className="pf-work-chip-panel"
                  role="group"
                  aria-label={`Volumes of ${title}`}
                >
                  <div className="pf-work-chip-grid">
                    {chipVolumes.map((volume, i) => (
                      <button
                        key={volume.slug}
                        type="button"
                        className={
                          "pf-work-chip" +
                          (volume.progress != null
                            ? " pf-work-chip--done"
                            : "") +
                          (volume.slug === front?.slug
                            ? " pf-work-chip--current"
                            : "")
                        }
                        aria-label={`Show volume ${i + 1} of ${title}`}
                        onClick={() => pickFront(volume.slug)}
                      >
                        {i + 1}
                      </button>
                    ))}
                    {overflowCount > 0 ? (
                      <span
                        className="pf-work-chip pf-work-chip--more"
                        aria-label={`${overflowCount} more volumes not shown`}
                      >
                        +{overflowCount}
                      </span>
                    ) : null}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="pf-work-selected">
          <div className="pf-work-selected__front">
            <BookCard
              slug={front.slug}
              title={title}
              volumeLabel={`Volume ${volumes.findIndex((v) => v.slug === front.slug) + 1} of ${count}`}
              bucket={front.bucket}
              card={front.card}
              progress={front.progress ?? null}
              listen={front.listen ?? null}
              marks={front.marks ?? null}
            />
          </div>
          <button
            type="button"
            className="pf-work-change"
            aria-label={`Select a volume of ${title} — currently showing volume ${volumes.findIndex((v) => v.slug === front.slug) + 1} of ${count}`}
            title="Select volume"
            onClick={() => setPickerOpen(true)}
          >
            Select volume
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * Group a slug-keyed list into standalone units and multi-volume sets.
 *
 * A `work_slug` shared by only ONE visible unit does not make a set — that is
 * a volume whose siblings are invisible to this reader (unpublished, or
 * behind a grant they do not hold), and it must render exactly as a
 * standalone book always has. `workSlug` on `WorkVolume` is deliberately not
 * carried through: the set already knows its own key, and every volume
 * inside it is otherwise identical in shape to a standalone `BookCard`'s
 * props.
 */
export function groupIntoWorks<
  T extends { slug: string; workSlug: string | null } & WorkVolume,
>(
  units: T[],
): Array<
  { kind: "book"; unit: T } | { kind: "work"; workSlug: string; volumes: T[] }
> {
  const byWork = new Map<string, T[]>();
  for (const unit of units) {
    if (unit.workSlug === null) continue;
    byWork.set(unit.workSlug, [...(byWork.get(unit.workSlug) ?? []), unit]);
  }

  const grouped = new Set<string>();
  for (const [workSlug, members] of byWork) {
    if (members.length >= 2) grouped.add(workSlug);
  }

  const out: Array<
    { kind: "book"; unit: T } | { kind: "work"; workSlug: string; volumes: T[] }
  > = [];
  const emitted = new Set<string>();

  for (const unit of units) {
    if (unit.workSlug !== null && grouped.has(unit.workSlug)) {
      if (emitted.has(unit.workSlug)) continue;
      emitted.add(unit.workSlug);
      out.push({
        kind: "work",
        workSlug: unit.workSlug,
        volumes: byWork.get(unit.workSlug)!,
      });
    } else {
      out.push({ kind: "book", unit });
    }
  }

  return out;
}
