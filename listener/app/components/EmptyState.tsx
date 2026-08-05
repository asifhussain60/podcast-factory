/**
 * "There is nothing here yet", said the same way everywhere.
 *
 * Eleven places said it, in three different recipes of the same two classes:
 * `pf-empty` alone in four (which is spacing and no typography, so those four
 * set themselves in the browser's default face on a site that declares one),
 * `pf-note` alone in six (typography, and no room around it), and in exactly one
 * place both — which is the one that was right. Appearance was the shared
 * vocabulary rather than a component, so nobody could see the other ten were
 * wrong by looking at any one of them.
 *
 * No `className` escape hatch on purpose. The moment a caller can add to the
 * recipe there are eleven recipes again.
 */
export function EmptyState({ children }: { children: React.ReactNode }) {
  return <p className="pf-note pf-empty">{children}</p>;
}
