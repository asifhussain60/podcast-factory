import { redirect } from "react-router";

import type { Route } from "./+types/sign-out";
import { cloudflare } from "~/context";
import { createAuth } from "~/server/auth.server";

/**
 * Ending a session is a POST, not a link — the same rule as starting one.
 *
 * A GET that signs you out can be fired by any page that embeds an image
 * pointing at it, which makes logging people out a thing any other site can do
 * to them. Nothing here is destructive, so it is a nuisance rather than a
 * vulnerability, but the fix is one attribute and the sign-in route already
 * argues the case.
 *
 * PUBLIC on purpose, and the reason is the one case where signing out matters
 * most: someone who signed in with the wrong Google account lands on
 * /no-access, which is outside the invited gate. Hanging this route inside that
 * gate would mean the page that tells you "you used the wrong account" is the
 * one page that cannot offer you a way to change it.
 *
 * It only ever ends the CALLER's own session; there is no id in the request to
 * name anyone else's.
 */
export function loader() {
  // Nothing to render. Someone typing the URL gets sent home rather than an
  // error page, and a GET still cannot end a session.
  throw redirect("/");
}

export async function action({ request, context }: Route.ActionArgs) {
  const { env } = context.get(cloudflare);

  try {
    const auth = createAuth(env);

    // `returnHeaders` is the whole point of the call: the Set-Cookie that
    // CLEARS the session token rides on those headers. Dropping them would
    // leave the cookie in place and the sign-out silently wouldn't.
    const { headers } = await auth.api.signOut({
      headers: request.headers,
      returnHeaders: true,
    });

    return redirect("/sign-in", { headers });
  } catch {
    // Already signed out, or a session that could not be resolved. Either way
    // the intent is satisfied and the destination is the same — an error page
    // here would be a dead end for someone trying to reach the front door.
    return redirect("/sign-in");
  }
}
