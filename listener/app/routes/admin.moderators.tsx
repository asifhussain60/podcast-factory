import { Form } from "react-router";

import type { Route } from "./+types/admin.moderators";
import { EmptyState } from "~/components/EmptyState";
import { ToggleButton } from "~/components/admin/ToggleButton";
import { when } from "~/lib/adminDate";
import { cloudflare } from "~/context";
import { session } from "~/middleware/session";
import { tryNormalizeEmail } from "~/server/email.server";
import { listModerators, setModerator } from "~/server/moderation.server";

/**
 * Who may see books held for moderation.
 *
 * Its own screen rather than a control on the people table, for a practical reason: the
 * people route is at its size ceiling and is the wrong place for a second kind of
 * privilege — and a moderator is one, so it is worth seeing as a list of its own.
 *
 * Nested under the admin layout, so `requireAdmin` guards it and its action alike. A
 * moderator is strictly LOWER than admin and can never widen into it: admin remains
 * `ADMIN_EMAIL` alone, and there is still no role column.
 */
export async function loader({ context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  return { moderators: await listModerators(env.DB) };
}

export async function action({ request, context }: Route.ActionArgs) {
  const { env } = context.get(cloudflare);
  const actor = context.get(session).viewer!.email;
  const form = await request.formData();
  const email = tryNormalizeEmail(String(form.get("email") ?? ""));

  if (email === null) return { error: "That is not a usable email address." };

  await setModerator(
    env.DB,
    email,
    form.get("on") === "1",
    actor,
    new Date().toISOString(),
  );
  return { ok: true };
}

export default function AdminModerators({
  loaderData,
  actionData,
}: Route.ComponentProps) {
  const { moderators } = loaderData;

  return (
    <div className="pf-panel">
      <div className="pf-panel__head">
        <h2 className="pf-panel__title">Moderators</h2>
      </div>

      <div className="pf-panel__body pf-stack-sm">
        <p className="pf-note">
          A moderator can see books that are held for moderation, and nothing
          more: no other book, and none of this admin section. Admins are
          moderators automatically and do not need to be listed.
        </p>

        <Form method="post" className="pf-split" preventScrollReset>
          <input type="hidden" name="on" value="1" />
          <label htmlFor="moderator-email" className="sr-only">
            Email address to make a moderator
          </label>
          <input
            id="moderator-email"
            name="email"
            type="email"
            required
            autoComplete="off"
            placeholder="Email address"
            className="pf-input pf-input--sm pf-split__main"
          />
          <ToggleButton on={false}>Make a moderator</ToggleButton>
        </Form>

        {actionData && "error" in actionData ? (
          <p className="pf-message pf-message--warn">{actionData.error}</p>
        ) : null}

        {moderators.length === 0 ? (
          <EmptyState>
            Nobody is a moderator yet. Admins can already see held books.
          </EmptyState>
        ) : (
          moderators.map((m) => (
            <Form
              key={m.email}
              method="post"
              preventScrollReset
              className="pf-grant"
            >
              <input type="hidden" name="email" value={m.email} />
              <input type="hidden" name="on" value="0" />
              <div className="pf-split__main">
                <span className="pf-row__main">{m.displayName}</span>
                <p className="pf-note pf-note--quiet">
                  {m.invited
                    ? `Since ${when(m.grantedAt)}`
                    : "Not invited yet, so they cannot sign in — invite them on the People tab."}
                </p>
              </div>
              <ToggleButton on>Moderator · remove</ToggleButton>
            </Form>
          ))
        )}
      </div>
    </div>
  );
}
