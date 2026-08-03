import { Link } from "react-router";
import type { Route } from "./+types/home";
import { cloudflare } from "~/context";
import { Logo } from "~/components/brand/Logo";
import { ThemePicker } from "~/components/ThemePicker";

export function loader({ context }: Route.LoaderArgs) {
  // Proves the Worker env reaches the loader — the wiring every later phase
  // depends on for D1 and R2 bindings.
  const { env } = context.get(cloudflare);
  return { siteName: env.PUBLIC_SITE_NAME ?? "Podcast Factory" };
}

export default function Home({ loaderData }: Route.ComponentProps) {
  return (
    <div className="min-h-dvh bg-pf-bg">
      <header className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-6 py-6">
        <Logo size={44} />
        <ThemePicker />
      </header>

      <main id="main" className="mx-auto max-w-5xl px-6 pb-24">
        <section className="border-t border-pf-rule pt-14">
          <p className="font-ui text-xs uppercase tracking-[0.18em] text-pf-muted">
            {loaderData.siteName}
          </p>
          <h1 className="mt-4 max-w-3xl text-balance font-prose text-5xl leading-[1.08] text-pf-ink sm:text-6xl">
            Scholarly books, read and heard.
          </h1>
          <p className="mt-6 max-w-xl font-prose text-lg leading-relaxed text-pf-muted">
            A private library of translated editions and the conversations built
            from them. Access is by invitation.
          </p>

          <div className="mt-10 flex flex-wrap items-center gap-4">
            <span
              aria-disabled="true"
              className="rounded-md bg-pf-accent px-5 py-2.5 font-ui text-sm text-pf-on-accent opacity-60"
            >
              Sign in with Google
            </span>
            <span className="font-ui text-sm text-pf-faint">Available in the next phase</span>
          </div>
        </section>

        <section className="mt-20 grid gap-6 sm:grid-cols-3">
          {[
            { t: "Listen", d: "Episodes that keep playing while you move around the site." },
            { t: "Read", d: "The full edition, reflowable, in your own type and theme." },
            { t: "Annotate", d: "Highlights and notes that survive the book being revised." },
          ].map((c) => (
            <article
              key={c.t}
              className="rounded-xl border border-pf-rule bg-pf-surface p-6"
              style={{ boxShadow: "var(--l-shadow)" }}
            >
              <h2 className="font-prose text-xl text-pf-ink">{c.t}</h2>
              <p className="mt-2 font-ui text-sm leading-relaxed text-pf-muted">{c.d}</p>
            </article>
          ))}
        </section>

        <section className="mt-16 rounded-xl border border-pf-rule-soft bg-pf-sunken p-6">
          <h2 className="font-prose text-lg text-pf-ink">Arabic sets correctly</h2>
          <p
            lang="ar"
            dir="rtl"
            className="mt-3 text-2xl text-pf-ink"
          >
            بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ
          </p>
          <p className="mt-3 font-ui text-sm text-pf-muted">
            Fully vowelled, in Scheherazade New, with the line spacing the marks
            need. <Link className="underline" to="/brand">Compare the three logo marks</Link>.
          </p>
        </section>
      </main>
    </div>
  );
}
