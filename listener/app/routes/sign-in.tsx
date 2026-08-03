import { redirect, useSearchParams } from "react-router";

import type { Route } from "./+types/sign-in";
import { Logo } from "~/components/brand/Logo";
import { ThemePicker } from "~/components/ThemePicker";
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
  return null;
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

export default function SignIn() {
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));

  return (
    <div className="flex min-h-dvh flex-col bg-pf-bg">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-6 py-6">
        <Logo size={40} />
        <ThemePicker />
      </header>

      <main id="main" className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-6 pb-24">
        <h1 className="font-prose text-4xl leading-tight text-pf-ink">Sign in</h1>
        <p className="mt-4 font-prose text-pf-muted">
          This library is private. Sign in with the Google account your
          invitation was sent to.
        </p>

        <form method="post" className="mt-8">
          <input type="hidden" name="next" value={next} />
          <button
            type="submit"
            className="w-full rounded-lg bg-pf-accent px-5 py-3 font-ui text-sm text-pf-on-accent transition-colors hover:bg-pf-accent-hover"
          >
            Continue with Google
          </button>
        </form>

        <p className="mt-6 font-ui text-xs leading-relaxed text-pf-faint">
          We ask Google only for your name, email address and profile picture.
        </p>
      </main>
    </div>
  );
}
