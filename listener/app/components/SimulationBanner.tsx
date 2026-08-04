import { faEye } from "@fortawesome/free-solid-svg-icons";
import { Form } from "react-router";

import { Icon } from "~/components/Icon";

/**
 * "You are seeing this as somebody else" — on every page, until it is stopped.
 *
 * Unmissable on purpose. A simulation changes what the whole site shows: books
 * disappear, the admin link goes, the Scholar Companion is not there. Every one
 * of those looks exactly like a fault, and the difference between a fault and a
 * simulation is this strip.
 *
 * Sticky rather than fixed: it stays in view while reading a chapter, without
 * permanently covering a band of the page the way the reader's own controls
 * would have to work around.
 *
 * It says writes are discarded because they are — the marks endpoint refuses
 * while simulating, so a highlight made here disappears on reload. Silently
 * dropping someone's action is only acceptable when the page has said it will.
 */
export function SimulationBanner({ as }: { as: string }) {
  return (
    <div className="pf-simulating" role="status">
      <p className="pf-simulating__what">
        <Icon icon={faEye} />
        <span>
          Seeing the site as <strong>{as}</strong>. Nothing you change here is saved.
        </span>
      </p>

      {/* Posts to a PUBLIC route, which is the point: while this is showing, the
          admin screens answer 404 to you. */}
      <Form method="post" action="/stop-simulating">
        <button type="submit" className="pf-button pf-button--sm">
          Stop
        </button>
      </Form>
    </div>
  );
}
