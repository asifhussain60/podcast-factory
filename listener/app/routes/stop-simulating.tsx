import { redirect } from "react-router";

import type { Route } from "./+types/stop-simulating";
import { cloudflare } from "~/context";
import { simulatingOf } from "~/middleware/session";
import { recordEvent } from "~/server/access.server";
import { simulatedEmail, stopSimulating } from "~/server/simulate.server";

/**
 * Stop seeing the site as somebody else.
 *
 * PUBLIC, for the same reason `/sign-out` is, and it matters more here. While a
 * simulation is running the viewer is not an administrator, so `/admin` answers
 * 404 — and if the person being simulated is revoked or uninvited, every gated
 * page redirects to `/no-access`. A stop control living behind either of those
 * would be a stop control the simulation itself can lock you out of.
 *
 * It is safe to leave open because it takes no argument and grants nothing: it
 * clears one cookie in the CALLER's own browser. Anyone else who posts here
 * simply clears a cookie they did not have.
 *
 * A POST, not a link. A GET that changes state can be fired by any page that
 * embeds an image pointing at it — the same rule sign-out already argues.
 */
export function loader() {
  throw redirect("/");
}

export async function action({ request, context }: Route.ActionArgs) {
  const { env } = context.get(cloudflare);
  const url = new URL(request.url);

  // Read before clearing, for two reasons: the audit row names who was being
  // simulated, and the administrator is returned to that person's own page
  // rather than to the top of a list of a hundred.
  const was = simulatedEmail(request);
  const headers = { "Set-Cookie": stopSimulating(url) };

  if (was === null) return redirect("/", { headers });

  // Best-effort. Failing to write the audit row must not leave someone stuck in
  // a simulation they have asked to leave.
  try {
    // The ACTOR is the administrator, not the person being simulated — the
    // viewer at this point is the simulated one, and an audit row saying they
    // acted on themselves would be exactly backwards.
    const by = simulatingOf(context)?.by ?? "unknown";
    await recordEvent(
      env.DB,
      "simulate-stop",
      was,
      new Date().toISOString(),
      by,
    );
  } catch {
    // Nothing to do about it here, and the cookie still clears.
  }

  return redirect(`/admin?email=${encodeURIComponent(was)}`, { headers });
}
