import { Logo } from "~/components/brand/Logo";
import { SiteFooter } from "~/components/SiteFooter";
import { ThemePicker } from "~/components/ThemePicker";

/**
 * The pages you can reach without being signed in — sign-in, no-access, and the
 * error boundary, which is also what a denied book answers with.
 *
 * They used to hand-roll a header each — the same logo and the same padding
 * written twice, next to a third copy in SiteHeader. Three near-identical
 * headers is how they start to drift, and one of them had already lost the
 * theme picker.
 *
 * `SiteHeader` cannot be reused here: its nav links point at gated routes, so
 * on a sign-in page every one of them is an invitation to be bounced back.
 * What is shared is the shell, not the navigation. `AppShell` is this same
 * structure for the pages that ARE signed in, and it is a separate component for
 * exactly that reason rather than for want of trying.
 */
export function PublicShell({
  themePicker = true,
  hero = false,
  error = false,
  siteName,
  children,
}: {
  /** The no-access page is a dead end; a theme control there is furniture. */
  themePicker?: boolean;
  /**
   * A wide, centred column instead of the narrow left-aligned one, and no logo
   * in the header — the hero image carries the wordmark at full size a few
   * pixels below it, and the same name twice in one eyeful reads as a mistake.
   */
  hero?: boolean;
  /**
   * The error page, which is also the denied 404 — so it is a third public page
   * and belongs here, and it had no shell at all until now.
   *
   * Not a gate: a gate is a short column held in the middle of the window, and
   * this one can carry a stack trace in development that grows past the fold.
   * It keeps its own top-aligned runway.
   */
  error?: boolean;
  /**
   * `PUBLIC_SITE_NAME`, where the page has a loader to read it from. The error
   * boundary has none — see root.tsx — so it takes the footer's own default.
   */
  siteName?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="pf-shell">
      <header
        className={`pf-container pf-header${hero ? " pf-header--bare" : ""}`}
      >
        {hero ? null : <Logo size={40} />}
        {themePicker ? <ThemePicker /> : null}
      </header>

      <main
        id="main"
        className={`pf-container ${hero ? "pf-gate pf-gate--hero" : error ? "pf-container--narrow pf-error" : "pf-gate pf-container--narrow"}`}
      >
        {children}
      </main>

      <SiteFooter siteName={siteName} />
    </div>
  );
}
