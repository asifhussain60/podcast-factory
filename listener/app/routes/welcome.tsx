import {
  faCircleArrowRight,
  faBookOpen,
  faMicrophoneLines,
} from "@fortawesome/free-solid-svg-icons";
import { Link, redirect } from "react-router";

import type { Route } from "./+types/welcome";
import { AppShell } from "~/components/AppShell";
import { Icon } from "~/components/Icon";
import { collectionOf } from "~/lib/collection";
import { count } from "~/lib/plural";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
import { visibleUnits } from "~/server/access.server";

/**
 * The chooser, between signing in and the shelf.
 *
 * The library holds two genuinely different things — classical works published
 * as reading editions with long-form audio, and lectures Asif recorded himself —
 * and until this page existed the only thing that told them apart was a small
 * segmented control near the top of one grid, which appears at all only for a
 * reader entitled to both. Nothing ever explained the difference. This does,
 * once, in the two sentences under the two tiles, and then gets out of the way.
 *
 * This IS the home page — `/` — so the masthead logo, the Home button and a
 * bare visit to the site all arrive here. The shelf lives at `/library`.
 */

/**
 * Sora, preloaded HERE rather than in `root.tsx`.
 *
 * The two faces root preloads are the ones every page draws. This one is drawn
 * on this page and nowhere else, so preloading it globally would cost eight
 * other pages a download none of them uses — and the tiles are the largest
 * thing on this screen, so a swap flash is exactly where it would be seen.
 */
export const links: Route.LinksFunction = () => [
  {
    rel: "preload",
    href: "/fonts/sora-latin-wght-normal.woff2",
    as: "font",
    type: "font/woff2",
    crossOrigin: "anonymous",
  },
];

/**
 * Both counts, from the ONE place the entitlement rule is written.
 *
 * No filtering happens here — `visibleUnits` decides what this reader may see
 * and this loader only sorts the result into two piles, by the same
 * `collectionOf` the cards, the book page and the player all read.
 *
 * The redirect is the guard that matters. The shelf draws its collection
 * toggle only when a library actually mixes both kinds, so a reader entitled to
 * books alone, sent to `/?collection=sessions`, would land on an empty grid with
 * no visible control to escape it. A chooser with one real option is not a
 * choice, so they go straight to the shelf and never see this page.
 */
export async function loader({ context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const viewer = context.get(session).viewer!;

  const units = await visibleUnits(env.DB, viewer.email);

  let sessions = 0;
  for (const unit of units) {
    if (collectionOf(unit.bucket) === "sessions") sessions += 1;
  }
  const books = units.length - sessions;

  if (books === 0 || sessions === 0) throw redirect("/library");

  return { books, sessions, isAdmin: viewer.isAdmin };
}

export default function Welcome({ loaderData }: Route.ComponentProps) {
  const { books, sessions, isAdmin } = loaderData;

  return (
    <AppShell here="welcome" isAdmin={isAdmin} flush>
      <section className="pf-welcome">
        <div className="pf-welcome__wrap">
          <p className="pf-welcome__eyebrow">Where would you like to begin</p>
          <h1 className="pf-welcome__title">Two ways to read this library</h1>
          <p className="pf-welcome__lede">
            The shelf holds both, side by side. Pick one to open it on its own —
            you can switch, or see everything at once, from the shelf itself.
          </p>

          {/* A list, because it is two of one kind of thing and a screen reader
              should say so before reading them. The links carry the whole tile:
              a card with a button inside it gives a keyboard one target and a
              mouse two, and the two disagree about how big the thing is. */}
          <ul className="pf-welcome__tiles">
            <li>
              <Link to="/library?collection=books" className="pf-tile">
                <span className="pf-tile__head">
                  <span className="pf-tile__glyph">
                    <Icon icon={faBookOpen} />
                  </span>
                  <span className="pf-tile__name">Books</span>
                </span>
                <span className="pf-tile__blurb">
                  Classical works, published twice over — a modern English
                  reading edition you can read on screen or take offline, and a
                  series of long-form podcast episodes drawn from the same
                  source. Follow either, or both together.
                </span>
                <span className="pf-tile__meta">{count(books, "title")}</span>
              </Link>
            </li>

            {/* `data-collection` is what §3b paints the violet session accent
                from — the same attribute the session cards, the session book
                pages and the player already carry, so this tile is the colour
                of what it opens rather than a colour chosen for a tile. */}
            <li>
              <Link
                to="/library?collection=sessions"
                className="pf-tile"
                data-collection="sessions"
              >
                <span className="pf-tile__head">
                  <span className="pf-tile__glyph">
                    <Icon icon={faMicrophoneLines} />
                  </span>
                  <span className="pf-tile__name">Sessions</span>
                </span>
                <span className="pf-tile__blurb">
                  Spoken teaching, gathered into series meant to be followed in
                  order — talks Asif gave and recorded himself, alongside
                  lectures by teachers such as Hamza Yusuf, transcribed from
                  their recordings. The talk is the work; there is no printed
                  edition behind it.
                </span>
                {/* "series" is its own plural — the default `+ "s"` would read
                    "2 seriess". */}
                <span className="pf-tile__meta">
                  {count(sessions, "series", "series")}
                </span>
              </Link>
            </li>
          </ul>

          {/* The third way out, and it has to hold its own beside two very
              large tiles without becoming a third thing to choose. So: bigger,
              inked, underlined, with an arrow — a LINK made prominent, not a
              button and not a card, per Asif's markup. */}
          <p className="pf-welcome__skip">
            <Link to="/library" className="pf-welcome__more">
              Or go straight to everything on the shelf
              <Icon
                icon={faCircleArrowRight}
                className="pf-welcome__more-arrow"
              />
            </Link>
          </p>
        </div>
      </section>
    </AppShell>
  );
}
