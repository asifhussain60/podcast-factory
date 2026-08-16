import {
  faBookOpen,
  faGlobe,
  faTriangleExclamation,
  faUserClock,
  faUsers,
  type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import { Icon } from "~/components/Icon";
import type { PeopleFilter } from "~/server/access.server";

/**
 * The five numbers that describe Access, in one row.
 *
 * Chosen by whether the number makes somebody DO something, which is why there
 * are five and not the seven the Overview tab carried. "Revoked" and "Not yet
 * published" were dropped: both are almost always zero or derivable from a tile
 * that stayed, and both remain one click away — the first as a filter chip, the
 * second on the content screen.
 *
 * Every tile is a LINK to the view that shows the people or books it counted.
 * A number an administrator cannot act on is decoration; "3 people would see an
 * empty library" is only useful if pressing it produces those three.
 *
 * Colour carries meaning here and is not applied evenly. The two tiles that can
 * describe somebody quietly stuck — invited and never arrived, arrived and given
 * nothing — take a warning tone ONLY while their count is above zero. A screen
 * where every tile is tinted says nothing; a screen where one is says where to
 * look.
 */
export function MetricStrip({
  tallies,
  content,
}: {
  tallies: Record<PeopleFilter, number>;
  content: { published: number; openToAll: number; known: number };
}) {
  const invited = tallies.all - tallies.revoked;

  return (
    <ul className="pf-metrics" aria-label="Access at a glance">
      <Metric
        icon={faUsers}
        label="Invited"
        value={invited}
        hint="may sign in"
        to="/admin"
      />
      <Metric
        icon={faUserClock}
        label="Never signed in"
        value={tallies.never}
        hint="may not have the link"
        to="/admin?filter=never"
        attention={tallies.never > 0}
      />
      <Metric
        icon={faTriangleExclamation}
        label="No access yet"
        value={tallies.waiting}
        hint="would see an empty library"
        to="/admin?filter=waiting"
        attention={tallies.waiting > 0}
      />
      <Metric
        icon={faBookOpen}
        label="Readable now"
        value={content.published}
        hint={`of ${content.known} known`}
        to="/admin/content"
      />
      <Metric
        icon={faGlobe}
        label="Open to everyone"
        value={content.openToAll}
        hint="no grant needed"
        to="/admin/content"
      />
    </ul>
  );
}

function Metric({
  icon,
  label,
  value,
  hint,
  to,
  attention = false,
}: {
  icon: IconDefinition;
  label: string;
  value: number;
  hint: string;
  to: string;
  /** Whether this number is currently asking for something to be done. */
  attention?: boolean;
}) {
  return (
    <li>
      <Link
        to={to}
        className={attention ? "pf-metric pf-metric--attention" : "pf-metric"}
      >
        <span className="pf-metric__label">
          <Icon icon={icon} className="pf-metric__icon" />
          {label}
        </span>
        <span className="pf-metric__value">{value}</span>
        <span className="pf-metric__hint">{hint}</span>
      </Link>
    </li>
  );
}
