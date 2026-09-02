import {
  faList,
  faTableCells,
  faTableCellsLarge,
  type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";

import { Icon } from "~/components/Icon";
import type { ViewMode } from "~/lib/shelf";

/**
 * How the same shelf is DRAWN — cards, compact tiles, or a list.
 *
 * Its own component since 2026-09-01, when Asif moved it out of the filter rail
 * and onto the shelf's heading row. That is a real distinction rather than a
 * rearrangement: everything left in the rail changes WHICH books are shown, and
 * this one changes how the same result looks. Sitting beside "The Shelf" it
 * reads as a property of the view; sitting under Advanced search it read as one
 * more filter.
 *
 * The markup lives here rather than in either caller so the two cannot drift
 * into different button orders or labels.
 */
const VIEWS: { mode: ViewMode; icon: IconDefinition; label: string }[] = [
  { mode: "cards", icon: faTableCellsLarge, label: "Card view" },
  { mode: "compact", icon: faTableCells, label: "Compact tile view" },
  { mode: "list", icon: faList, label: "List view" },
];

export function ViewSwitcher({
  viewMode,
  onViewMode,
}: {
  viewMode: ViewMode;
  onViewMode: (value: ViewMode) => void;
}) {
  return (
    <div className="pf-views" role="group" aria-label="Book display">
      {VIEWS.map(({ mode, icon, label }) => (
        <button
          key={mode}
          type="button"
          className="pf-view"
          aria-pressed={viewMode === mode}
          aria-label={label}
          title={label}
          onClick={() => onViewMode(mode)}
        >
          <Icon icon={icon} title={label} />
        </button>
      ))}
    </div>
  );
}
