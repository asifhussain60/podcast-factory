/**
 * A date an administrator can read.
 *
 * Rendered from the ISO string with an explicit locale rather than
 * `toLocaleDateString()` bare: the server and the browser can disagree about the
 * default locale, and a date that changes shape on hydration is a mismatch React
 * will report.
 *
 * Shared between the people table (a "Signed in" column) and one person's panel
 * (Invited / First signed in / Last signed in) — both format the same kind of
 * ISO timestamp the same way, so the rule lives once rather than being copied
 * when the panel was split out.
 */
export function when(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];
