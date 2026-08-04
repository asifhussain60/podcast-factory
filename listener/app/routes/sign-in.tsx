import { redirect, useSearchParams } from "react-router";

import type { Route } from "./+types/sign-in";
import { PublicShell } from "~/components/PublicShell";
import { cloudflare } from "~/context";
import { safeNext } from "~/lib/nav";
import { viewerOf } from "~/middleware/session";
import { createAuth } from "~/server/auth.server";

export function loader({ request, context }: Route.LoaderArgs) {
  // Already signed in? Go where they were headed. The redirect target is
  // validated even here — it arrives in the query string like any other.
  if (viewerOf(context) !== null) {
    const next = safeNext(new URL(request.url).searchParams.get("next"));
    throw redirect(next);
  }
  // For the footer. The signed-in pages read it from the `_authed` layout, which
  // this page is deliberately outside of.
  return { siteName: context.get(cloudflare).env.PUBLIC_SITE_NAME };
}

/**
 * Starting sign-in is a POST, not a link.
 *
 * A GET that initiates an OAuth flow can be triggered by any page that embeds
 * an image or iframe pointing at it. A form POST cannot be triggered
 * cross-origin without the user acting.
 */
export async function action({ request, context }: Route.ActionArgs) {
  const { env } = context.get(cloudflare);
  const form = await request.formData();
  const next = safeNext(String(form.get("next") ?? "/"));

  const auth = createAuth(env);

  // `returnHeaders` is load-bearing, not a nicety.
  //
  // Starting an OAuth flow is not just "get a URL". Better Auth also mints a
  // one-time `state` and persists it in a cookie, then compares it against what
  // Google sends back — that comparison is the CSRF defence for the whole flow.
  // Taking only `url` and issuing our own redirect silently discards that
  // Set-Cookie, so the state has nowhere to live and every callback fails with
  // `state_mismatch`, which reads like a Google misconfiguration rather than a
  // dropped header.
  const { headers, response } = await auth.api.signInSocial({
    body: { provider: "google", callbackURL: next, errorCallbackURL: "/no-access" },
    returnHeaders: true,
  });

  if (!response.url) throw new Error("Google sign-in did not return an authorization URL");

  // Carry every header through, not just the cookie we happen to know about —
  // a future Better Auth version setting a second one must not need a change here.
  return redirect(response.url, { headers });
}

export default function SignIn({ loaderData }: Route.ComponentProps) {
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));

  return (
    <PublicShell hero siteName={loaderData.siteName}>
      {/* Two widths through srcset: a phone loading the 1600 would spend most
          of its bytes on pixels it cannot draw. `fetchPriority` because this is
          the largest paint on the page and there is nothing above it to wait
          for. The dimensions are on the element so the heading below it does
          not jump when the image arrives. */}
      <img
        className="pf-hero"
        src="/brand/home-1600.webp"
        srcSet="/brand/home-800.webp 800w, /brand/home-1600.webp 1600w"
        sizes="(max-width: 48rem) 100vw, 48rem"
        width={1672}
        height={941}
        fetchPriority="high"
        alt="Podcast Factory — an open book beside headphones, a microphone and a phone playing an episode"
      />

      {/* Title then byline, the order a title page uses — which is what makes
          the credit read as authorship rather than as a badge stuck on the
          page. Grouped with the heading so the column's gap falls around the
          pair; a byline floating midway between two blocks belongs to neither. */}
      <div className="pf-hero__titling">
        <h1 className="pf-hero__tagline">Classical books, made to be read and heard.</h1>
        {/* The space between the spans is deliberate. The gap that separates
            them on screen is flex, which leaves no character behind — so read
            aloud, or copied, the line came out as "Created byAsif Hussain". */}
        <p className="pf-byline">
          <span className="pf-byline__label">Created by</span>{" "}
          <span className="pf-byline__name">Asif Hussain</span>
        </p>
      </div>

      <p className="pf-hero__lede">
        Every work in this library is published twice: as a modern English
        reading edition, and as a series of long-form audio episodes drawn from
        the same source. Read it, listen to it, or follow both together.
      </p>

      <form method="post" className="pf-hero__action">
        <input type="hidden" name="next" value={next} />
        <button type="submit" className="pf-button pf-button--primary pf-button--lg">
          Continue with Google
        </button>
      </form>

      <p className="pf-note pf-note--quiet">
        {/* "the account you were invited with", not "the account your invitation
            was sent to" — nothing is sent. There is no mail transport in this
            application; an administrator adds an address and passes the link on
            by hand, so the second phrasing sends anyone who did not receive an
            email looking for one that never existed. */}
        This library is private — sign in with the Google account you were invited
        with. We ask Google only for your name, email address and profile picture.
      </p>
    </PublicShell>
  );
}
