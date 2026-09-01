import {
  faBookOpen,
  faHeadphones,
  faLayerGroup,
  faList,
  faMicrophoneLines,
  faSliders,
  faTableCells,
  faTableCellsLarge,
  type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import { Icon } from "~/components/Icon";
import { SearchBox } from "~/components/SearchBox";
import {
  COLLECTIONS,
  COLLECTION_LABELS,
  type Collection,
} from "~/lib/collection";
import type { ViewMode } from "~/lib/shelf";
import {
  ALL_STUDY_TRACKS,
  studyTrackLabel,
  type StudyTrack,
  type TrackChoice,
} from "~/lib/study-track";

/**
 * Every way of narrowing the library, in one column beside the grid.
 *
 * These controls were a row above the cards: search, the collection chooser,
 * Advanced search, the view icons, and a bordered panel of track chips beneath
 * them. Five separate blocks stacked on top of the thing they filter, costing
 * enough height to push the first card under the fold. Asif asked for the shape
 * the reader already uses — one floating panel down the side — and chose it
 * against the alternatives with the trade below on the table.
 *
 * THE TRADE, STATED ONCE, BECAUSE IT IS REAL. The panel occupies a fixed
 * gutter, so `.pf-container` gives up 23rem to guarantee it (see
 * `library-rail.css`). Above about 1216px that costs nothing — the container is
 * already narrower than the room available. Between 1024 and 1216 it genuinely
 * squeezes the three-column grid, and that was shown, measured, and accepted
 * rather than discovered later.
 *
 * NOTHING HERE IS NEW BEHAVIOUR. Every control keeps the state, the handler and
 * the ARIA it had in the row — the same `aria-pressed` buttons, the same
 * `role="group"`, the same disabled empty tracks, the same `<Link>` to the
 * advanced page so it still middle-clicks. This is a relocation, and it was
 * written as one so that a regression here can only be a layout regression.
 */

/** Collections carry an icon, tracks carry their own colour. Two vocabularies
 *  on purpose: a collection is a KIND of thing, a track is a subject, and
 *  giving both the same treatment made the column read as ten equal buttons. */
const COLLECTION_ICON: Record<Collection, IconDefinition> = {
  all: faLayerGroup,
  books: faBookOpen,
  sessions: faMicrophoneLines,
  audiobooks: faHeadphones,
};

const VIEWS: { mode: ViewMode; icon: IconDefinition; label: string }[] = [
  { mode: "cards", icon: faTableCellsLarge, label: "Card view" },
  { mode: "compact", icon: faTableCells, label: "Compact tile view" },
  { mode: "list", icon: faList, label: "List view" },
];

export function LibraryRail({
  query,
  onQuery,
  mixed,
  collection,
  onCollection,
  track,
  onTrack,
  trackCounts,
  total,
  viewMode,
  onViewMode,
}: {
  query: string;
  onQuery: (value: string) => void;
  /** The chooser appears only where there is more than one kind to choose. */
  mixed: boolean;
  collection: Collection;
  onCollection: (value: Collection) => void;
  track: TrackChoice;
  onTrack: (value: TrackChoice) => void;
  trackCounts: Map<StudyTrack, number>;
  total: number;
  viewMode: ViewMode;
  onViewMode: (value: ViewMode) => void;
}) {
  return (
    /* A `nav` would claim this is a set of links, and all but one of them are
       buttons that filter the page in place. `aria-label` names the region so
       it is reachable and announced without lying about what it holds. */
    <aside className="pf-library-rail" aria-label="Narrow the library">
      <div className="pf-library-rail__panel">
        <SearchBox
          id="library-search"
          label="Search the library"
          placeholder="Search"
          size="sm"
          action={{ kind: "filter", value: query, onChange: onQuery }}
        />

        {mixed ? (
          <>
            <p className="pf-rail-label" id="rail-collection-label">
              Show
            </p>
            <div
              className="pf-rail-group"
              role="group"
              aria-labelledby="rail-collection-label"
            >
              {COLLECTIONS.map((choice) => (
                <button
                  key={choice}
                  type="button"
                  className="pf-rail-item"
                  data-collection={choice}
                  aria-pressed={collection === choice}
                  onClick={() => onCollection(choice)}
                >
                  <span className="pf-rail-item__icon" aria-hidden="true">
                    <Icon icon={COLLECTION_ICON[choice]} />
                  </span>
                  <span className="pf-rail-item__label">
                    {COLLECTION_LABELS[choice]}
                  </span>
                </button>
              ))}
            </div>
          </>
        ) : null}

        <p className="pf-rail-label" id="rail-track-label">
          Track
        </p>
        {/* `pf-track-chip` is kept, not replaced: its `data-track` attribute is
            what paints each dot from the SAME `--l-ribbon-*` pair the card's
            corner ribbon uses, so choosing Esoteric here and seeing it on a card
            stay one decision rather than two that agree today. */}
        <div
          className="pf-rail-group pf-rail-group--tracks"
          role="group"
          aria-labelledby="rail-track-label"
        >
          <button
            type="button"
            className="pf-track-chip pf-rail-item"
            aria-pressed={track === "all"}
            onClick={() => onTrack("all")}
          >
            <span className="pf-rail-item__label">All tracks</span>
            <span className="pf-track-chip__count">{total}</span>
          </button>
          {ALL_STUDY_TRACKS.map((choice) => {
            const n = trackCounts.get(choice) ?? 0;
            return (
              <button
                key={choice}
                type="button"
                className="pf-track-chip pf-rail-item"
                data-track={choice}
                aria-pressed={track === choice}
                // Disabled rather than hidden, exactly as in the row it came
                // from: the empty track still teaches the reader the taxonomy
                // has five members before anything is filed under it.
                disabled={n === 0}
                onClick={() => onTrack(choice)}
              >
                <span className="pf-rail-item__label">
                  {studyTrackLabel(choice)}
                </span>
                <span className="pf-track-chip__count">{n}</span>
              </button>
            );
          })}
        </div>

        <p className="pf-rail-label">More</p>
        {/* Still a LINK: it goes to a page, so it must open in a new tab on a
            middle-click and be copyable like any other address. */}
        <Link to="/search" className="pf-rail-item">
          <span className="pf-rail-item__icon" aria-hidden="true">
            <Icon icon={faSliders} />
          </span>
          <span className="pf-rail-item__label">Advanced</span>
        </Link>

        {/* Its own group at the foot, because it changes how the same result is
            DRAWN rather than what the result is. */}
        <div
          className="pf-rail-views"
          role="group"
          aria-label="Book display"
        >
          {VIEWS.map(({ mode, icon, label }) => (
            <button
              key={mode}
              type="button"
              className="pf-rail-view"
              aria-pressed={viewMode === mode}
              aria-label={label}
              title={label}
              onClick={() => onViewMode(mode)}
            >
              <Icon icon={icon} title={label} />
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
}
