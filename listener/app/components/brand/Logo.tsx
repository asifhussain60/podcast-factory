import { Colophon, Qalam, Strapwork } from "./marks";

/**
 * Which mark the site wears. Asif has seen all three rendered but has not
 * picked, so this stays a one-line change until he does. Everything else in
 * the app imports <Logo /> and never a specific mark.
 */
export const DEFAULT_MARK: MarkName = "strapwork";

export type MarkName = "strapwork" | "colophon" | "qalam";

export function Mark({
  name = DEFAULT_MARK,
  size = 40,
  compact = false,
  className,
  playing = false,
}: {
  name?: MarkName;
  size?: number;
  compact?: boolean;
  className?: string;
  playing?: boolean;
}) {
  if (name === "colophon") {
    return <Colophon size={size} compact={compact} className={className} playing={playing} />;
  }
  if (name === "qalam") {
    return <Qalam size={size} compact={compact} className={className} />;
  }
  return <Strapwork size={size} compact={compact} className={className} />;
}

/**
 * Each mark has its own wordmark treatment — they are lockups, not a shared
 * label bolted onto three different pictures.
 */
export function Wordmark({ name = DEFAULT_MARK }: { name?: MarkName }) {
  if (name === "colophon") {
    return (
      <span className="font-ui text-[1.35rem] font-medium tracking-tight">
        <span className="text-pf-ink">Podcast</span>
        <span className="text-pf-accent"> Factory</span>
      </span>
    );
  }

  if (name === "qalam") {
    return (
      <span className="flex flex-col gap-1">
        <span className="font-ui text-[1.05rem] uppercase tracking-[0.16em] text-pf-ink">
          Podcast Factory
        </span>
        <span aria-hidden="true" className="h-px w-full bg-pf-accent" />
      </span>
    );
  }

  return (
    <span className="flex flex-col leading-none">
      <span className="font-prose text-[1.6rem] font-normal text-pf-ink">Podcast</span>
      <span className="font-ui text-[0.7rem] uppercase tracking-[0.22em] text-pf-muted">
        Factory
      </span>
    </span>
  );
}

/** Mark plus wordmark. The site's identity in one component. */
export function Logo({
  name = DEFAULT_MARK,
  size = 40,
  playing = false,
}: {
  name?: MarkName;
  size?: number;
  playing?: boolean;
}) {
  return (
    <span className="inline-flex items-center gap-3 text-pf-ink">
      <Mark name={name} size={size} playing={playing} />
      <Wordmark name={name} />
      <span className="sr-only">Podcast Factory</span>
    </span>
  );
}
