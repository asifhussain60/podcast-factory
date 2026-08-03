import type { Route } from "./+types/no-access";
import { Logo } from "~/components/brand/Logo";
import { viewerOf } from "~/middleware/session";

export function loader({ context }: Route.LoaderArgs) {
  const viewer = viewerOf(context);
  return { email: viewer?.email ?? null };
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
    <div className="flex min-h-dvh flex-col bg-pf-bg">
      <header className="mx-auto flex w-full max-w-5xl items-center px-6 py-6">
        <Logo size={40} />
      </header>

      <main id="main" className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-6 pb-24">
        <h1 className="font-prose text-4xl leading-tight text-pf-ink">
          No access yet
        </h1>
        <p className="mt-4 font-prose text-pf-muted">
          {loaderData.email
            ? "This library is by invitation, and there is no invitation for the account you used."
            : "This library is by invitation."}
        </p>
        {loaderData.email ? (
          <p className="mt-4 font-ui text-sm text-pf-faint">
            You signed in as <span className="text-pf-muted">{loaderData.email}</span>. If
            you have more than one Google account, it may be the other one.
          </p>
        ) : null}
      </main>
    </div>
  );
}
