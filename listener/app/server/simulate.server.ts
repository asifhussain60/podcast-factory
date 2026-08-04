/**
 * Seeing the site as someone else — the cookie, and the rules around it.
 *
 * This deliberately makes the application lie to itself about who is reading, in
 * an app whose entire access model is "the viewer is whoever the session says".
 * Four things keep that safe, and all four are load-bearing:
 *
 *   1. THE COOKIE GRANTS NOTHING BY ITSELF. `withSession` only consults it when
 *      the REAL session is the administrator's. Forged in anyone else's browser
 *      it is inert — their real session is not admin, so it is never read. That,
 *      not the cookie's contents, is the gate.
 *
 *   2. IT ONLY EVER DOWNGRADES. The simulated viewer is built with
 *      `isAdmin: false` unconditionally, including when simulating the admin's
 *      own address. There is no value of this cookie that adds a capability.
 *
 *   3. IT CANNOT WRITE. Every mark in this application is keyed on
 *      `viewer.email`, so browsing as somebody would otherwise rewrite their
 *      bookmarks and their reading position. The marks action refuses while it
 *      is set; see book.$slug.marks.ts.
 *
 *   4. IT EXPIRES. Two hours, and it is a session cookie besides. A forgotten
 *      simulation resolves itself rather than quietly persisting as a browser
 *      that shows the wrong library.
 *
 * `HttpOnly` because no script has any business reading or setting it, and
 * `SameSite=Lax` because nothing should be able to start a simulation from
 * another site. It is NOT signed: signing defends against forgery, and forgery
 * buys nothing here — rule 1 is what a signature would otherwise be for.
 */

import { tryNormalizeEmail } from "./email.server";

export const SIMULATE_COOKIE = "pf-simulate";

/** Two hours. Long enough to look around, short enough to forget safely. */
const MAX_AGE = 2 * 60 * 60;

/**
 * The address being simulated, normalized, or null.
 *
 * Normalized HERE rather than trusted from the cookie, because every entitlement
 * decision downstream compares normalized addresses — a raw value would look up
 * grants that can never match and present as "this person has nothing".
 */
export function simulatedEmail(request: Request): string | null {
  const header = request.headers.get("Cookie");
  if (header === null) return null;

  for (const part of header.split(";")) {
    const at = part.indexOf("=");
    if (at === -1) continue;
    if (part.slice(0, at).trim() !== SIMULATE_COOKIE) continue;

    try {
      return tryNormalizeEmail(decodeURIComponent(part.slice(at + 1).trim()));
    } catch {
      // A cookie that is not even decodable is not an address.
      return null;
    }
  }

  return null;
}

/** `Secure` everywhere it can be — never on plain-http localhost, or dev breaks. */
const secure = (url: URL) => (url.protocol === "https:" ? "; Secure" : "");

export function startSimulating(email: string, url: URL): string {
  return `${SIMULATE_COOKIE}=${encodeURIComponent(email)}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${MAX_AGE}${secure(url)}`;
}

export function stopSimulating(url: URL): string {
  return `${SIMULATE_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${secure(url)}`;
}
