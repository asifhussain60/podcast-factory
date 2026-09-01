/**
 * playback-rate.ts — how fast the listener plays things, and how that is kept.
 *
 * SPLIT OUT OF `Player.tsx` (2026-09-01) when extending the scale to 3x pushed
 * that file past its `npm run ratchets` ceiling. A real seam rather than a cut
 * made to fit: the scale, the storage key, the validation and the application to
 * an element are one concern with one invariant between them — the list the UI
 * offers is the list a stored value is validated against — and Player.tsx is the
 * component that uses them, not the place they are decided.
 */

/**
 * The listening speeds the player offers, slowest first.
 *
 * Asif's scale (2026-09-01), replacing 0.9 / 1 / 1.2 / 1.5 / 1.8: half-step
 * increments and no slow speed at all. The fine gradations below 1.5x were
 * distinctions nobody was making, and dropping them means every remaining button
 * is a speed somebody would actually choose.
 *
 * 3x is the ceiling, and it is a judgement about listening rather than a limit of
 * the API — `playbackRate` accepts far more, and browsers mute audio entirely
 * above about 4x. Comprehension holds to roughly 2.5-3x on clear narration; past
 * that the gaps between words disappear before the ear can segment them, and a
 * scale that offers an unusable speed is worse than a shorter one.
 *
 * This is also the validation list for what comes back out of storage, so the
 * three speeds just removed are no longer restorable: a listener who had left the
 * player at 1.2x comes back at 1x rather than at a speed no button shows. That is
 * the intended outcome of the rule below, not a side effect of it.
 */
export const RATES = [1, 1.5, 2, 2.5, 3] as const;

/**
 * Set the speed, and keep the voice at its own pitch while doing it.
 *
 * `preservesPitch` is the single thing that makes the upper half of the scale
 * usable: without it 3x is a chipmunk and the words are gone long before the
 * speed is the problem. Every current browser defaults it to true, so this was
 * working by luck rather than by decision — and it has not always defaulted that
 * way. Written once, here, because the rate is applied from four places (the
 * restore effect, a new source, the setter, and the media-session mirror) and
 * three of them remembering is how one of them stops.
 */
export function applyRate(element: HTMLAudioElement, rate: number): void {
  element.preservesPitch = true;
  element.playbackRate = rate;
}

/**
 * How fast the listener plays things — remembered like every other setting.
 *
 * It was React state alone, so a listener who plays at 1.5× was returned to 1×
 * by every reload and every new visit, on every episode. That is not a position
 * (which belongs to one episode) but a PREFERENCE about listening, so it is one
 * value rather than a map, and it sits beside the positions rather than in
 * `pf-reading` — that key is the reading column's typography, and a listening
 * speed inside it would be a second meaning for one store.
 */
export const RATE_KEY = "pf-rate";

export function loadRate(): number {
  try {
    const stored = Number(localStorage.getItem(RATE_KEY));
    // Validated against the SCALE THE UI OFFERS, never merely against "is a
    // number". `playbackRate = 0` is a silent, unrecoverable pause, and a rate
    // between the buttons would light none of them — the control would read as
    // broken. Same rule as `storedReading`, and it must keep using the exported
    // RATES rather than a second list: a copy that drifted would reject every
    // real stored value and reset to 1, which is the bug this exists to fix.
    return (RATES as readonly number[]).includes(stored) ? stored : 1;
  } catch {
    return 1;
  }
}

/** Remember the chosen speed. Silent when storage is disabled — the rate still
 *  applies to this session, which is the graceful half of the same promise. */
export function saveRate(rate: number): void {
  try {
    localStorage.setItem(RATE_KEY, String(rate));
  } catch {
    // Storage disabled. The rate still applies to this session.
  }
}
