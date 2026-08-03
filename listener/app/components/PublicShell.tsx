import { Logo } from "~/components/brand/Logo";
import { SiteFooter } from "~/components/SiteFooter";
import { ThemePicker } from "~/components/ThemePicker";

/**
 * The two pages you can reach without being signed in.
 *
 * They used to hand-roll a header each — the same logo and the same padding
 * written twice, next to a third copy in SiteHeader. Three near-identical
 * headers is how they start to drift, and one of them had already lost the
 * theme picker.
 *
 * `SiteHeader` cannot be reused here: its nav links point at gated routes, so
 * on a sign-in page every one of them is an invitation to be bounced back.
 * What is shared is the shell, not the navigation.
 */
export function PublicShell({
  themePicker = true,
  hero = false,
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
  children: React.ReactNode;
}) {
  return (
    <div className="pf-shell">
      <header className={`pf-container pf-header${hero ? " pf-header--bare" : ""}`}>
        {hero ? null : <Logo size={40} />}
        {themePicker ? <ThemePicker /> : null}
      </header>

      <main
        id="main"
        className={`pf-container pf-gate ${hero ? "pf-gate--hero" : "pf-container--narrow"}`}
      >
        {children}
      </main>

      <SiteFooter />
    </div>
  );
}
