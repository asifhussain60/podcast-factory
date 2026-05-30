/**
 * EditorialDefaults — Step 2 of the /intake page (WC8 Slice 6b).
 *
 * Reuses the existing <EditorialCards> component at book scope.
 * Shows a placeholder until a slug has been scaffolded by NewContentForm;
 * once the slug is known it renders the full editorial cockpit for that book.
 *
 * No new card logic here — this is purely a composition wrapper so the
 * intake page can display book-scope editorial decisions alongside the form.
 */
import EditorialCards from '../reader/poc/EditorialCards';
import type { CardDef } from '../../lib/reader/editorial';

interface Props {
  /** Slug of the newly-scaffolded content, or null before scaffolding. */
  slug: string | null;
  /** Passed from the server-side .astro file to avoid bundling node:fs in the client. */
  cardDefs: CardDef[];
}

export default function EditorialDefaults({ slug, cardDefs }: Props) {
  if (!slug) {
    return (
      <div className="intake-editorial-panel">
        <p className="intake-editorial-label">Editorial defaults</p>
        <div className="intake-editorial-placeholder">
          Create the workshop folder first — the editorial cockpit will appear here
          so you can set canonical decisions before asking Claude to run intake.
        </div>
      </div>
    );
  }

  return (
    <div className="intake-editorial-panel">
      <p className="intake-editorial-label">Editorial defaults — {slug}</p>
      <EditorialCards slug={slug} chapters={[]} cardDefs={cardDefs} />
    </div>
  );
}
