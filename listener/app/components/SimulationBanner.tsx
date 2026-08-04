import { faEye } from "@fortawesome/free-solid-svg-icons";
import { Form } from "react-router";

import { Icon } from "~/components/Icon";

/**
 * "You are in simulation mode" — on every page, until it is left.
 *
 * A PANEL rather than a strip, and it says the words SIMULATION MODE first. It
 * used to be one quiet line reading "Seeing the site as …", which describes the
 * situation accurately and is not what someone scans for: a simulation removes
 * books, removes the admin link and removes the Scholar Companion, and every one
 * of those looks exactly like a fault. The difference between a fault and a
 * simulation has to be the loudest thing on the page, not the softest.
 *
 * Sticky, not fixed: it stays in view down a chapter without permanently
 * covering a band that every other surface would then lay itself out around.
 *
 * Colour is the measured warn pair from `.pf-pill--warn` — a 12% fill with the
 * tone inked to 75% — rather than a solid warn band, which would need an
 * `--l-on-warn` token that does not exist and a contrast pair nobody has
 * measured. The weight comes from size, structure and a heavy edge instead.
 *
 * It says writes are discarded because they are: the marks endpoint refuses
 * while this is showing, so a highlight made here is gone on reload. Dropping
 * somebody's action silently is only acceptable when the page has said it will.
 */
export function SimulationBanner({ as }: { as: string }) {
  return (
    <aside className="pf-simulating" role="status" aria-label="Simulation mode">
      <Icon icon={faEye} className="pf-simulating__icon" />

      <div className="pf-simulating__what">
        <p className="pf-simulating__title">Simulation mode</p>
        <p className="pf-simulating__detail">
          You are seeing the site as <strong>{as}</strong>, with only what they can open.
          Nothing you change here is saved.
        </p>
      </div>

      {/* Posts to a PUBLIC route, which is the point: while this is showing, the
          admin screens answer 404 to you. */}
      <Form method="post" action="/stop-simulating" className="pf-simulating__out">
        <button type="submit" className="pf-button pf-button--sm">
          Exit simulation
        </button>
      </Form>
    </aside>
  );
}
