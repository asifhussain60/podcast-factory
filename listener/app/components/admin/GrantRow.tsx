import { Form } from "react-router";

import { ToggleButton } from "~/components/admin/ToggleButton";

/**
 * One row that gives one thing, or takes it back.
 *
 * Two screens render it from opposite ends of the same table: a person's page
 * lists the BOOKS they hold, a book's page lists the PEOPLE who hold it. Same
 * markup, same act, and the two copies had already drifted — one printed a
 * revoked marker in the hint line and the other did not, and one kept the
 * scroll position on submit while the other threw you back to the top. This is
 * the superset: both behaviours, once.
 *
 * What each screen names its grant differs and stays a prop: one posts a scope
 * type and id, the other posts a slug. What the button SAYS differs too — "Has
 * it" reads right beside a person's name and "Granted" beside a book's title.
 */
export function GrantRow({
  label,
  hint,
  on,
  onLabel,
  offLabel = "Give access",
  covered = false,
  fields,
}: {
  label: string;
  /** The small second line. Omitted when there is nothing worth adding. */
  hint?: string;
  /** Whether this is already given — which is also what a press will undo. */
  on: boolean;
  /** What the button reads once it is given. */
  onLabel: string;
  offLabel?: string;
  /** Held through something wider, so the hint says so instead of the caller. */
  covered?: boolean;
  /** What identifies this grant to the action — a scope, or a slug. */
  fields: Record<string, string>;
}) {
  return (
    // `preventScrollReset`, because a form post is a navigation and React Router
    // resets scroll on one unless told otherwise — so granting the eleventh book
    // threw the page back to the top and you scrolled down to it again.
    <Form method="post" preventScrollReset className="pf-grant">
      <input type="hidden" name="intent" value={on ? "revoke-grant" : "grant"} />
      {Object.entries(fields).map(([name, value]) => (
        <input key={name} type="hidden" name={name} value={value} />
      ))}

      <span className="pf-grant__what">
        <span className="pf-grant__label">{label}</span>
        {covered && !on ? (
          <span className="pf-grant__hint">Already covered by a wider grant</span>
        ) : hint ? (
          <span className="pf-grant__hint">{hint}</span>
        ) : null}
      </span>

      <ToggleButton on={on}>{on ? onLabel : offLabel}</ToggleButton>
    </Form>
  );
}
