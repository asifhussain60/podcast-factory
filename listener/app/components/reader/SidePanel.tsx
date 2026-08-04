import { faXmark, type IconDefinition } from "@fortawesome/free-solid-svg-icons";

import { Icon } from "~/components/Icon";

/**
 * A panel against one edge of the reader, collapsed to a tab.
 *
 * ONE component for both sides, and one set of rules — the contents on the left
 * and your marks on the right are the same object mirrored, so they are the
 * same code mirrored. Written as two components they were the same shape twice,
 * and the two would have drifted the first time either was touched: a tab a few
 * pixels taller on one side than the other is the kind of difference nobody can
 * name but everybody sees.
 *
 * Collapsed, the panel is a tab against its edge, carrying its own affordance —
 * which is why nothing in the toolbar opens either of them. Both tabs are fixed
 * and centred, so they line up across the page whatever is scrolled.
 *
 * Fixed rather than in the flow, so opening one never moves the paragraph being
 * read. On a phone it covers the page and the scrim dims what it covers; on a
 * wide screen it takes a column of its own beside the text.
 */
export function SidePanel({
  side,
  as: Landmark,
  open,
  onOpen,
  onClose,
  label,
  icon,
  count,
  docked = false,
  children,
}: {
  /** `start` is the left edge in a left-to-right reading, `end` the right. */
  side: "start" | "end";
  /** `nav` for a list of places, `aside` for anything else. */
  as: "nav" | "aside";
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
  /** The tab's word, and the drawer's heading. One string, so they agree. */
  label: string;
  icon: IconDefinition;
  /** Shown on the tab when there is something in it. Never shown as zero. */
  count?: number;
  /**
   * Stand BESIDE the text rather than over it, on a screen wide enough.
   *
   * A panel that is open the whole time cannot be one that dims the page: the
   * reader would be reading through a scrim. Docked, the page lays out in the
   * width the panel leaves it and the scrim is gone — which is what the note at
   * the top of this file has always claimed a wide screen does, and never did.
   *
   * The word is honoured in CSS, not here, because it is a question about the
   * VIEWPORT: below the breakpoint a docked panel is an ordinary drawer again,
   * scrim and all, and nothing in React has to know which side of that line the
   * window is on.
   */
  docked?: boolean;
  children: React.ReactNode;
}) {
  if (!open) {
    return (
      <button
        type="button"
        onClick={onOpen}
        aria-expanded={false}
        aria-label={`Open ${label.toLowerCase()}`}
        title={label}
        className={`pf-edge-tab pf-edge-tab--${side}`}
      >
        <Icon icon={icon} />
        {/* Written out, not left to the icon. An unlabelled glyph alone in the
            margin is easy to miss entirely, and these two tabs are the only way
            to reach what they hold. Hidden on the phone layout, where the tab is
            too slim to carry it — the accessible name carries it there. */}
        <span className="pf-edge-tab__label">{label}</span>
        {count === undefined || count === 0 ? null : (
          <span className="pf-edge-tab__count">{count}</span>
        )}
      </button>
    );
  }

  return (
    <>
      {/* Click-away. Not focusable and hidden from assistive tech — Escape and
          the close button are the keyboard routes out, and a scrim in the tab
          order is a stop that announces nothing. */}
      <button
        type="button"
        aria-hidden="true"
        tabIndex={-1}
        onClick={onClose}
        className="pf-drawer__scrim"
      />

      <Landmark
        aria-label={label}
        className={`pf-drawer pf-drawer--${side}${docked ? " pf-drawer--docked" : ""}`}
      >
        <div className="pf-drawer__head">
          <h2 className="pf-drawer__title">{label}</h2>
          {/* No `aria-expanded` here. The tab is the disclosure control; this
              is a plain close button — and `.pf-tool` styles anything expanded
              as pressed, so it rendered lit, which on an X reads as a state
              rather than as a way out. */}
          <button
            type="button"
            onClick={onClose}
            aria-label={`Close ${label.toLowerCase()}`}
            className="pf-tool"
          >
            <Icon icon={faXmark} title={`Close ${label.toLowerCase()}`} />
          </button>
        </div>

        <div className="pf-drawer__body">{children}</div>
      </Landmark>
    </>
  );
}
