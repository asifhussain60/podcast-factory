/**
 * The one email comparator.
 *
 * Grants key on email rather than user id, because Asif has to be able to hand
 * someone a book before they have ever signed in — at which point there is no
 * user row to point at. That makes the email string a privilege bit, and a
 * privilege bit compared two different ways is a privilege bit that can be
 * bypassed. So: every comparison anywhere — the admin check, the invite lookup,
 * the grant lookup, the seed data — goes through `normalizeEmail`. Never a raw
 * `===` on an address, and never a second normalization rule somewhere else.
 *
 * The login side is not the risk. Google's OIDC `email` claim is always the
 * account's canonical primary address, so `a.b+tag@gmail.com` never arrives as
 * a claim and no aliasing trick gets anybody in. The risk is the WRITE side:
 * Asif types `Asif.Hussain60+book@Gmail.com` into the grant box, Google returns
 * `asifhussain60@gmail.com`, the grant silently never matches, and the failure
 * looks exactly like "not granted yet".
 */

/** Domains where the dots-and-plus-tags folding is actually correct. */
const GMAIL_DOMAINS = new Set(["gmail.com", "googlemail.com"]);

/** Printable ASCII only. Anything else is a homograph risk on the write side. */
const NON_ASCII = /[^\x20-\x7E]/;

export class InvalidEmailError extends Error {
  constructor(readonly input: string, reason: string) {
    super(`Not a usable email address (${reason})`);
    this.name = "InvalidEmailError";
  }
}

/**
 * Fold an address to its canonical comparison form, or throw.
 *
 * Deliberately NOT symmetric across domains: dots and `+tags` are stripped for
 * Gmail only, because that folding is a Gmail behaviour. Applying it everywhere
 * would merge `first.last@company.com` with `firstlast@company.com`, which on a
 * Workspace domain can be two different people — an over-normalization that
 * hands one person's library to another.
 */
export function normalizeEmail(raw: string): string {
  if (typeof raw !== "string") throw new InvalidEmailError(String(raw), "not a string");

  // NFKC first: it folds the compatibility characters (fullwidth Latin, and so
  // on) that would otherwise slip past the ASCII check as distinct code points
  // while looking identical to a reader.
  let value = raw.normalize("NFKC").trim();

  // Tolerate a pasted `Name <addr@host>` — the likeliest paste from a mail app.
  const angled = /^[^<]*<([^>]*)>$/.exec(value);
  if (angled) value = angled[1].trim();

  const at = value.indexOf("@");
  if (at === -1 || at !== value.lastIndexOf("@")) {
    throw new InvalidEmailError(raw, "needs exactly one @");
  }

  let local = value.slice(0, at);
  // One trailing dot is the fully-qualified DNS form and is equivalent.
  let domain = value.slice(at + 1).toLowerCase().replace(/\.$/, "");

  if (NON_ASCII.test(local) || NON_ASCII.test(domain)) {
    throw new InvalidEmailError(raw, "contains non-ASCII characters");
  }

  local = local.toLowerCase();

  if (GMAIL_DOMAINS.has(domain)) {
    domain = "gmail.com";
    const plus = local.indexOf("+");
    if (plus !== -1) local = local.slice(0, plus);
    local = local.replaceAll(".", "");
  }

  if (local === "") throw new InvalidEmailError(raw, "empty local part");
  if (!domain.includes(".") || domain.startsWith(".") || domain.endsWith(".")) {
    throw new InvalidEmailError(raw, "domain is not a hostname");
  }

  return `${local}@${domain}`;
}

/** Non-throwing form, for validating admin form input. */
export function tryNormalizeEmail(raw: string): string | null {
  try {
    return normalizeEmail(raw);
  } catch {
    return null;
  }
}

/**
 * True when an address carries a `+tag` on a domain where we do NOT strip it —
 * i.e. where the tag is part of the identity and almost certainly a mistake in
 * an invite box. Advisory: the admin form warns, it does not refuse, because on
 * some providers `a+b@x.com` really is a separate mailbox.
 */
export function hasUnfoldedPlusTag(raw: string): boolean {
  const normalized = tryNormalizeEmail(raw);
  return normalized !== null && normalized.includes("+");
}
