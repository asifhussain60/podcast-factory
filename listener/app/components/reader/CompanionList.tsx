import { useEffect, useMemo, useRef, useState } from "react";
import { faQuoteLeft } from "@fortawesome/free-solid-svg-icons";

import { EmptyState } from "~/components/EmptyState";
import { Icon } from "~/components/Icon";
import type { CompanionCard } from "~/server/companion.server";

/**
 * The Scholar Companion's cards for one chapter, following the page.
 *
 * The same cards the Book Composer's Scholar panel shows, and deliberately NOT
 * the same component: that one (plan-dashboard's explanation-card.ts) exists to
 * make a card editable and drags a ProseMirror editor in with it. Nothing here
 * can be edited — writing a note is an act of authoring and belongs in the
 * Composer, next to the prose being explained.
 *
 * ONE card is expanded at a time, and scrolling into a tinted sentence is what
 * expands it. That is the whole point of the panel: it says where you are
 * standing rather than making you find the card that matches. A card opened by
 * hand stays open until the reader scrolls into a different passage, because a
 * panel that snapped shut under a finger would be unusable.
 *
 * `bodyHtml` was rendered at publish time by the admin site's own card renderer,
 * exactly as the chapter's prose was — see app/server/companion.server.ts.
 */
export function CompanionList({
  cards,
  unplaced,
  inViewIds,
  focus,
}: {
  cards: CompanionCard[];
  /** Cards whose sentence is not in the chapter as it now reads. */
  unplaced: ReadonlySet<string>;
  /** Cards whose sentence is on screen right now, in reading order. */
  inViewIds: string[];
  /** A tinted sentence was tapped. The nonce makes a repeat tap re-fire. */
  focus: { id: string; nonce: number } | null;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const body = useRef<HTMLDivElement>(null);

  const lit = useMemo(() => new Set(inViewIds), [inViewIds]);

  // Reaching a passage opens its card. Guarded on the FIRST id rather than the
  // whole set so that a second card drifting into view behind the one being read
  // does not pull the panel away from it.
  const leading = inViewIds[0] ?? null;
  useEffect(() => {
    if (leading !== null) setExpanded(leading);
  }, [leading]);

  useEffect(() => {
    if (focus === null) return;
    setExpanded(focus.id);
  }, [focus]);

  // Keep the open card in the drawer's view. `nearest`, so a card already fully
  // visible does not cause the panel to jump every time the reader scrolls the
  // page a little.
  useEffect(() => {
    if (expanded === null) return;
    body.current
      ?.querySelector(`[data-card-id="${CSS.escape(expanded)}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [expanded]);

  if (cards.length === 0) {
    return (
      <EmptyState>
        No explanations for this chapter yet. Write them in the Book Composer,
        beside the passage they explain, and they appear here the next time the
        book is published.
      </EmptyState>
    );
  }

  return (
    <div ref={body} className="pf-companion">
      {cards.map((card) => {
        const open = expanded === card.id;
        return (
          <article
            key={card.id}
            data-card-id={card.id}
            className={`pf-card pf-companion-card${lit.has(card.id) ? " pf-companion-card--lit" : ""}`}
          >
            <button
              type="button"
              aria-expanded={open}
              onClick={() => setExpanded(open ? null : card.id)}
              className="pf-companion-card__head"
            >
              <span className="pf-companion-card__title">
                {card.title ?? "Explanation"}
              </span>
              {open ? null : (
                <span className="pf-companion-card__gist">
                  {gistOf(card.bodyHtml)}
                </span>
              )}
            </button>

            {open ? (
              <div className="pf-companion-card__body">
                {card.quote === null ? null : (
                  <blockquote className="pf-companion-card__quote">
                    <Icon icon={faQuoteLeft} />
                    {card.quote}
                  </blockquote>
                )}

                {/* Rendered once, at publish time, by the same function the
                    Composer's cards go through. Nothing here parses markdown. */}
                <div
                  className="pf-companion-card__prose"
                  dangerouslySetInnerHTML={{ __html: card.bodyHtml }}
                />

                {card.etymology.length === 0 ? null : (
                  <ul className="pf-companion-card__etymology">
                    {card.etymology.map((row, at) => (
                      <li key={at}>{row}</li>
                    ))}
                  </ul>
                )}

                {/* Said plainly rather than hidden. The sentence this card was
                    written against is not in the chapter as it now reads — the
                    ordinary result of re-composing after the note was written —
                    and the card is shown anyway, unattached, because it is still
                    that chapter's note. Nothing is guessed onto a passage. */}
                {unplaced.has(card.id) ? (
                  <p className="pf-companion-card__lost">
                    This passage is not in the chapter as it now reads, so
                    nothing is marked in the text.
                  </p>
                ) : null}
              </div>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}

/** The one-line gist a collapsed card shows — its first prose, as plain text. */
function gistOf(html: string, limit = 120): string {
  const flat = html
    .replace(/<[^>]+>/g, " ")
    .replace(/&(amp|lt|gt|quot|#39);/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (flat.length <= limit) return flat;
  return `${flat.slice(0, limit).replace(/\s+\S*$/, "")}…`;
}
