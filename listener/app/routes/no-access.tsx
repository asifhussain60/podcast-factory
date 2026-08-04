import { Form } from "react-router";

import type { Route } from "./+types/no-access";
import { PublicShell } from "~/components/PublicShell";
import { SimulationBanner } from "~/components/SimulationBanner";
import { simulatingOf, viewerOf } from "~/middleware/session";

export function loader({ context }: Route.LoaderArgs) {
  const viewer = viewerOf(context);
  return { email: viewer?.email ?? null, simulating: simulatingOf(context) };
}

/**
 * Where a signed-in but uninvited (or revoked) person lands.
 *
 * Deliberately says nothing about what exists. It names the address they used,
 * because the single most common cause is signing in with the wrong Google
 * account, and without that they cannot tell.
 */
export default function NoAccess({ loaderData }: Route.ComponentProps) {
  return (
    <PublicShell themePicker={false}>
      {/* The one public page a simulation can land on: simulating a revoked or
          uninvited person bounces every gated route here. Without the banner
          this page is where the administrator would be stranded, since /admin
          answers 404 to them while it is running. */}
      {loaderData.simulating ? <SimulationBanner as={loaderData.simulating.as} /> : null}

      <p className="pf-eyebrow">Podcast Factory</p>
      <h1 className="pf-title">No access yet</h1>
      <p className="pf-lede">
        {loaderData.email
          ? "This library is by invitation, and there is no invitation for the account you used."
          : "This library is by invitation."}
      </p>
      {loaderData.email ? (
        <p className="pf-note pf-note--quiet pf-gate__action">
          You signed in as <strong className="pf-strong">{loaderData.email}</strong>. If you
          have more than one Google account, it may be the other one.
        </p>
      ) : null}

      {/* The whole reason sign-out is a public route. Telling someone they used
          the wrong account and then offering no way to change it is a dead end,
          and this page was one. */}
      <Form method="post" action="/sign-out" className="pf-gate__action">
        <button type="submit" className="pf-button">
          {loaderData.email ? "Sign in with a different account" : "Back to sign in"}
        </button>
      </Form>
    </PublicShell>
  );
}
