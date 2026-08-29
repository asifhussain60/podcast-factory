import {
  faBars,
  faCircleDown,
  faCircleQuestion,
  faGaugeHigh,
  faHouse,
  faRightFromBracket,
  faUserShield,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";
import { useEffect, useState } from "react";
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
 *
 * Each link carries a small label under its icon now (Asif, 2026-08-14) — it
 * used to be icon-only, with the word carried only in `aria-label`/`title`,
 * which meant a sighted reader had to already know what "Access" or
 * "Dashboard" meant before hovering to confirm it. Below `sm` there is no
 * room left for six labelled items in a row without wrapping, so the nav
 * becomes a burger-triggered dropdown there instead of wrapping — wrapping
 * was tried first and is what used to happen; see the CSS for why it was
 * dropped.
 */
export function SiteHeader({
  here,
  isAdmin = false,
}: {
  here:
    "library" | "welcome" | "admin" | "book" | "about" | "search" | "downloads";
  isAdmin?: boolean;
}) {
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!menuOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setMenuOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  const close = () => setMenuOpen(false);

  return (
    <header className="pf-container pf-header">
      {/* The logo IS the way home, and home is the chooser at `/`. Unlinked
          only on the chooser itself — a link to where you already are is a
          control that appears to do nothing. It used to be unlinked on the
          shelf, back when the shelf was `/`. */}
      {here === "welcome" ? (
        <Logo size={56} />
      ) : (
        <Link to="/" aria-label="Home" className="pf-logo-link">
          <Logo size={56} />
        </Link>
      )}

      {/* Below `sm` only — see `.pf-header__burger` in the stylesheet. Toggles
          the same nav the wide layout always shows; it never renders its own
          copy of the links. */}
      <button
        type="button"
        className="pf-header__burger"
        aria-expanded={menuOpen}
        aria-controls="site-nav"
        aria-label={menuOpen ? "Close menu" : "Open menu"}
        onClick={() => setMenuOpen((open) => !open)}
      >
        <Icon
          icon={menuOpen ? faXmark : faBars}
          title={menuOpen ? "Close menu" : "Open menu"}
        />
      </button>

      {/* Click-away, below `sm` only, present only while open — the same
          scrim-to-close convention the reader's side panels use. */}
      {menuOpen ? (
        <button
          type="button"
          aria-hidden="true"
          tabIndex={-1}
          onClick={close}
          className="pf-header__nav-scrim"
        />
      ) : null}

      <div id="site-nav" className="pf-header__nav" data-open={menuOpen}>
        {here !== "welcome" ? (
          <Link
            to="/"
            className="pf-navlink pf-navlink--home"
            aria-label="Home"
            title="Home"
            onClick={close}
          >
            <Icon icon={faHouse} />
            <span className="pf-navlink__label">Home</span>
          </Link>
        ) : null}

        {isAdmin ? (
          <Link
            to="/admin"
            className="pf-navlink pf-navlink--access"
            aria-label="Access"
            title="Access"
            onClick={close}
          >
            <Icon icon={faUserShield} />
            <span className="pf-navlink__label">Access</span>
          </Link>
        ) : null}

        {isAdmin ? (
          <Link
            to="/admin/usage"
            className="pf-navlink pf-navlink--dashboard"
            aria-label="Dashboard"
            title="Dashboard"
            onClick={close}
          >
            <Icon icon={faGaugeHigh} />
            <span className="pf-navlink__label">Dashboard</span>
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
            onClick={close}
          >
            <Icon icon={faCircleDown} />
            <span className="pf-navlink__label">Downloads</span>
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
            onClick={close}
          >
            <Icon icon={faCircleQuestion} />
            <span className="pf-navlink__label">About</span>
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
            <span className="pf-navlink__label">Sign out</span>
          </button>
        </Form>
      </div>
    </header>
  );
}
