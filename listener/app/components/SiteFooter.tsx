/**
 * The end of the page.
 *
 * The site had none: every view simply stopped at its last row, which on a short
 * library reads as a page that failed to finish loading. This says nothing
 * important on purpose — its job is to be a floor.
 *
 * No links. A footer full of navigation on an invite-only site with five pages
 * would be furniture for its own sake, and the masthead already goes everywhere
 * this site goes.
 */
export function SiteFooter({
  siteName = "Podcast Factory",
}: {
  siteName?: string;
}) {
  return (
    <footer className="pf-container pf-footer">
      <span>{siteName}</span>
      <span>Scholarly books, read and heard.</span>
    </footer>
  );
}
