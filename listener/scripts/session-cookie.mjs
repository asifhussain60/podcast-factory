/**
 * Mint a valid Better Auth session cookie for a local development session.
 *
 * Why this exists: the whole point of phase 2 is what happens when someone IS
 * signed in — default deny, work grants, admin gating, the `_routes` bypass. All
 * of that is unreachable through the real front door until a Google OAuth client
 * exists, and waiting for one would mean shipping the security model untested.
 *
 * This mints the same cookie Better Auth would, so every gate downstream runs
 * exactly as in production. It is a LOCAL tool: it reads BETTER_AUTH_SECRET from
 * .dev.vars and writes to the Miniflare D1 file. It cannot touch anything
 * deployed.
 *
 *   node scripts/session-cookie.mjs <email> [name]
 *
 * Prints the Cookie header value on stdout.
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

const [email, name = "Test Reader"] = process.argv.slice(2);
if (!email) {
  console.error("usage: node scripts/session-cookie.mjs <email> [name]");
  process.exit(2);
}

const secret = /^BETTER_AUTH_SECRET=(.*)$/m.exec(readFileSync(".dev.vars", "utf8"))?.[1];
if (!secret) {
  console.error("BETTER_AUTH_SECRET is not set in .dev.vars");
  process.exit(2);
}

const userId = `dev-${Buffer.from(email).toString("hex").slice(0, 16)}`;
const token = `devtok-${userId}`;
const now = new Date().toISOString();
const expires = new Date(Date.now() + 86_400_000).toISOString();

// Upsert the user and a live session. `emailVerified = 1` because the session
// middleware requires it, mirroring Google's own email_verified claim.
const sql = `
  INSERT INTO user (id, name, email, emailVerified, createdAt, updatedAt)
  VALUES ('${userId}', '${name}', '${email}', 1, '${now}', '${now}')
  ON CONFLICT(id) DO UPDATE SET email = excluded.email, emailVerified = 1;

  -- Delete ONLY this script's own deterministic row, never "all sessions for
  -- this user". The user id is derived from the email, so it collides with the
  -- row a real sign-in uses: Better Auth links a Google account to an existing
  -- row by verified email rather than creating a second one. A blanket delete
  -- therefore signed the real person out — observed, not theorised. A forged
  -- session sitting ALONGSIDE a real one is harmless; destroying the real one
  -- is not.
  DELETE FROM session WHERE id = 'sess-${userId}';

  INSERT INTO session (id, expiresAt, token, createdAt, updatedAt, userId)
  VALUES ('sess-${userId}', '${expires}', '${token}', '${now}', '${now}', '${userId}');
`;

execFileSync(
  "npx",
  ["wrangler", "d1", "execute", "podcast-listener", "--local", "--command", sql],
  { stdio: "pipe" },
);

// Exactly what better-call's signCookieValue does:
//   encodeURIComponent(`${value}.${base64(HMAC-SHA256(value, secret))}`)
const key = await crypto.subtle.importKey(
  "raw",
  new TextEncoder().encode(secret),
  { name: "HMAC", hash: "SHA-256" },
  false,
  ["sign"],
);
const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(token));
const value = encodeURIComponent(
  `${token}.${Buffer.from(new Uint8Array(signature)).toString("base64")}`,
);

process.stdout.write(`better-auth.session_token=${value}`);
