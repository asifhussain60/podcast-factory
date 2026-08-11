import { faArrowLeft } from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import type { Route } from "./+types/search";
import { AppShell } from "~/components/AppShell";
import { Icon } from "~/components/Icon";
import { session } from "~/middleware/session";

/**
 * Advanced search — the page, ahead of the search.
 *
 * Deliberately a stub. It exists now so the library's own button has somewhere
 * real to go: a control that leads to a 404 is worse than no control, and the
 * alternative — holding the button back until the page is designed — means the
 * two land in one change with nothing to look at in between.
 *
 * What it must NOT do before then is query anything. Every result this page ever
 * shows has to come from `visibleUnits`, the one place the entitlement rule is
 * written, and a loader that reached for the catalogue now would be the start of
 * that rule living somewhere else too. So the loader reads exactly what the
 * shell needs and nothing more.
 */

export function meta(): Route.MetaDescriptors {
  return [
    { title: "Advanced search — Podcast Factory" },
    { name: "description", content: "Search the library by more than its title." },
  ];
}

export function loader({ context }: Route.LoaderArgs) {
  // Only whether the masthead offers the Access link. Nothing on this page
  // varies by who is reading it — yet.
  return { isAdmin: context.get(session).viewer?.isAdmin === true };
}

export default function Search({ loaderData }: Route.ComponentProps) {
  return (
    <AppShell here="search" isAdmin={loaderData.isAdmin}>
      <section className="pf-masthead pf-masthead--tight">
        <h1 className="pf-title">Advanced search</h1>
        <p className="pf-lede">
          Being designed. The library's own box searches titles; this page is where
          searching by everything else will live.
        </p>

        <p className="pf-masthead__action">
          <Link to="/" className="pf-button pf-button--soft">
            <Icon icon={faArrowLeft} />
            Back to the library
          </Link>
        </p>
      </section>
    </AppShell>
  );
}
