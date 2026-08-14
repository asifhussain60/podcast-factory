import {
  faCircleDown,
  faCircleQuestion,
  faGaugeHigh,
  faHouse,
  faRightFromBracket,
  faUserShield,
} from "@fortawesome/free-solid-svg-icons";
import { Form, Link } from "react-router";

import { Icon } from "~/components/Icon";
import { Logo } from "~/components/brand/Logo";
import { ThemePicker } from "~/components/ThemePicker";

/**
 * The one masthead, used by every signed-in surface.
 *
 * It exists because the admin pages shipped without one and became a dead end —
 * the tabs moved you between admin screens and nothing moved you out. Fixing
 * that by pasting the library's header into the admin layout would have left
 * three near-copies to drift apart, so there is exactly one.
 *
 * Admin shortcuts stay visible even inside the admin area: access work and
 * usage work are separate jobs, and switching between them must never depend on
 * remembering a URL.
 */
export function SiteHeader({
  here,
  isAdmin = false,
}: {
  here: "library" | "admin" | "book" | "about" | "search" | "downloads";
  isAdmin?: boolean;
}) {
  return (
    <header className="pf-container pf-header">
      {here === "library" ? (
        <Logo size={44} />
      ) : (
        <Link to="/" aria-label="Back to your library" className="pf-logo-link">
          <Logo size={44} />
        </Link>
      )}

      <div className="pf-header__nav">
        {here !== "library" ? (
          <Link
            to="/"
            className="pf-navlink pf-navlink--home"
            aria-label="Home"
            title="Home"
          >
            <Icon icon={faHouse} />
          </Link>
        ) : null}

        {isAdmin ? (
          <Link
            to="/admin"
            className="pf-navlink pf-navlink--access"
            aria-label="Access"
            title="Access"
          >
            <Icon icon={faUserShield} />
          </Link>
        ) : null}

        {isAdmin ? (
          <Link
            to="/admin/usage"
            className="pf-navlink pf-navlink--dashboard"
            aria-label="Dashboard"
            title="Dashboard"
          >
            <Icon icon={faGaugeHigh} />
          </Link>
        ) : null}

        {/* Offered on every page, because the moment somebody wants it is the
            moment they have no signal — and a link they have to remember the
            address of is not reachable then. The service worker redirects any
            failed navigation here, so this is also where the app lands when it
            opens on a plane. */}
        {here !== "downloads" ? (
          <Link
            to="/downloads"
            className="pf-navlink pf-navlink--downloads"
            aria-label="Downloads"
            title="Downloads"
          >
            <Icon icon={faCircleDown} />
          </Link>
        ) : null}

        <ThemePicker />

        {/* Right before Sign out, and offered to everyone. It answers the
            question a reader arrives with — what is this, and what can I do
            here — but sits beside the way out rather than up front, since it
            no longer needs to be the first thing offered. */}
        {here !== "about" ? (
          <Link
            to="/about"
            className="pf-navlink pf-navlink--about"
            aria-label="About"
            title="About"
          >
            <Icon icon={faCircleQuestion} />
          </Link>
        ) : null}

        {/* Last, after the theme picker, and that order is the point: the links
            before it go somewhere, the picker changes how this page looks, and
            this ends the session. Sitting between the two it read as a third way
            of navigating, and it was the one item here that cannot be undone by
            pressing something else.

            A POST, not a link — see routes/sign-out.tsx. Styled as a nav item so
            the header does not grow a second visual weight for what is just
            another way out. */}
        {/* Signing out drops the cached Downloads document. The page tells the
            worker rather than the worker watching for the POST: what a worker
            would see is the redirect, not whether the session actually ended.
            The episodes themselves are NOT dropped — they are this device's, and
            the lease is what withdraws them. */}
        <Form
          method="post"
          action="/sign-out"
          onSubmit={() =>
            navigator.serviceWorker?.controller?.postMessage("pf-signed-out")
          }
        >
          <button
            type="submit"
            className="pf-navlink pf-navlink--button pf-navlink--signout"
            aria-label="Sign out"
            title="Sign out"
          >
            <Icon icon={faRightFromBracket} />
          </button>
        </Form>
      </div>
    </header>
  );
}
