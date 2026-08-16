/**
 * A submit button that is either set or not.
 *
 * Three forms wrote the same string by hand — `pf-button pf-button--sm`, plus
 * `pf-button--primary` when it is on — and `aria-pressed` beside it, which is
 * the half a fourth copy would have left off. Open a book to everyone, give a
 * person a book, give a book to a person: the same act, so the same control.
 */
export function ToggleButton({
  on,
  children,
}: {
  on: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="submit"
      aria-pressed={on}
      className={`pf-button pf-button--sm${on ? " pf-button--primary" : ""}`}
    >
      {children}
    </button>
  );
}
