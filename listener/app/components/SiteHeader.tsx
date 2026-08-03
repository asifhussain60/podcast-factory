import { Link } from "react-router";

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
 * `here` suppresses the link to wherever you already are, so the header never
 * offers a no-op.
 */
export function SiteHeader({
  here,
  isAdmin = false,
}: {
  here: "library" | "admin" | "book";
  isAdmin?: boolean;
}) {
  return (
    <header className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-4 px-6 py-6">
      {here === "library" ? (
        <Logo size={44} />
      ) : (
        <Link to="/" aria-label="Back to your library">
          <Logo size={44} />
        </Link>
      )}

      <div className="flex items-center gap-5">
        {here !== "library" ? (
          <Link
            to="/"
            className="font-ui text-sm text-pf-muted transition-colors hover:text-pf-ink"
          >
            Library
          </Link>
        ) : null}

        {isAdmin && here !== "admin" ? (
          <Link
            to="/admin"
            className="font-ui text-sm text-pf-muted transition-colors hover:text-pf-ink"
          >
            Access
          </Link>
        ) : null}

        <ThemePicker />
      </div>
    </header>
  );
}
