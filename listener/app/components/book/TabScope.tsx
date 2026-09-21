import { Link, useSearchParams } from "react-router";

/**
 * "Showing one chapter" — and the way back to the whole book.
 *
 * A chapter's badge opens a tab already narrowed to that chapter, and a narrowed view that does
 * not say so reads as a book that has almost nothing in it. The narrowing lives in `?chapter=`
 * so it can be linked to and survives a reload; this banner is its visible half.
 */
export function useChapterScope(
  chapters: { anchorKey: string; title: string }[],
) {
  const [params] = useSearchParams();
  const key = params.get("chapter");
  return chapters.find((c) => c.anchorKey === key) ?? null;
}

export function TabScope({
  slug,
  tab,
  title,
}: {
  slug: string;
  tab: string;
  title: string;
}) {
  return (
    <p className="pf-scope" role="status">
      <span>
        Showing <strong>{title}</strong>
      </span>
      <Link
        to={`/book/${slug}?tab=${tab}`}
        className="pf-link pf-link--inline"
        replace
      >
        Show the whole book
      </Link>
    </p>
  );
}
