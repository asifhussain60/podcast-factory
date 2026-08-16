/**
 * The note Asif sends somebody to tell them they can get in.
 *
 * A pure function returning plain text, deliberately. It is pasted into
 * WhatsApp, Messages, or an email body, and every one of those does something
 * different with rich markup — so the message is written to survive being
 * pasted anywhere, which means no formatting at all beyond line breaks.
 *
 * It reads like a person wrote it, because a person is sending it. The earlier
 * draft opened "I've given you access to my library of classical Islamic works",
 * which is accurate and reads like a service notification — and the whole point
 * of this text is that it arrives from someone the recipient knows.
 *
 * The ADDRESS is the part that earns its place. Access is keyed on the email,
 * so somebody signing in with a different Google account than the one they were
 * invited under lands on the no-access page and reasonably concludes the link is
 * broken. Naming the exact address turns the commonest support question into
 * something they can answer themselves.
 */

export interface InviteMessageInput {
  /** Their name if one was recorded, else their address — `Person.displayName`. */
  displayName: string;
  /** The address the invitation is keyed on, shown exactly as they must type it. */
  email: string;
  /** Where the site lives. Passed in, never hardcoded — it differs per environment. */
  siteUrl: string;
  /** Titles they can open, or empty. */
  books: string[];
  /** True when one of their grants is the whole library. */
  wholeLibrary: boolean;
}

/**
 * Just the given name, for the greeting.
 *
 * "Hi Mariam" rather than "Hi Mariam Palejwala", which reads like a form letter
 * — which is exactly what this must not read like. An address falls back to
 * itself: "Hi mariam@example.com" is odd, but inventing a name is worse, and the
 * administrator can see what they are about to send before they send it.
 */
function greetingName(displayName: string): string {
  const trimmed = displayName.trim();
  if (trimmed === "" || trimmed.includes("@")) return trimmed;
  return trimmed.split(/\s+/)[0];
}

/** Whether they have anything granted at all yet. */
function hasAnyAccess(books: string[], wholeLibrary: boolean): boolean {
  return wholeLibrary || books.length > 0;
}

/**
 * The About page.
 *
 * Behind the sign-in like everything else, which is fine and is why the line
 * around it says "once you're in": the gate carries the destination through
 * sign-in in `?next=`, so following this link cold lands them here after Google
 * rather than dumping them on the library with nothing explained.
 */
const aboutUrl = (siteUrl: string) => `${siteUrl.replace(/\/+$/, "")}/about`;

export function inviteMessage(input: InviteMessageInput): string {
  const name = greetingName(input.displayName);
  const has = hasAnyAccess(input.books, input.wholeLibrary);

  // NOT hard-wrapped. Each paragraph is one line and the receiving app wraps it
  // to its own width. Wrapping at a fixed column looked tidy in a desktop
  // textarea and broke everywhere else: pasted into WhatsApp on a phone it wraps
  // a second time, so every third line was a stray orphan — "edition," and
  // "work." alone on a line. Blank lines between paragraphs are the only
  // structure that survives being pasted anywhere.
  //
  // The site/sign-in block is fenced by plain ASCII dash rules rather than any
  // real box-drawing or markup — the fence is the closest thing to a "bordered
  // panel" that still survives being pasted into WhatsApp, iMessage, or a plain
  // Gmail compose box unchanged, which is the same constraint the rest of this
  // message is already written under.
  const rule = "-".repeat(50);

  const lines = [
    `Salaam ${name} — this site holds a library of classical Islamic works, each available in two ways: a proper English edition to read and a series of long-form audio sessions covering the same material. Read it, listen to it, or do both.`,
    "",
    rule,
    `Site: ${input.siteUrl}`,
    `Sign in with Google: ${input.email} — this is the account it's tied to, so another Google account won't work.`,
    rule,
    "",
  ];

  // Omitted entirely when they hold nothing yet, rather than printed empty —
  // same reasoning as before: telling them "there's more to explore" when
  // nothing has actually been granted yet would be false, not just vague.
  if (has) {
    lines.push("There are several books and sessions available to explore once you're in.", "");
  }

  lines.push(
    `Take a look at the about page too — it walks through everything the site can do, including highlighting, notes, and transcripts: ${aboutUrl(input.siteUrl)}`,
    "",
    "It's all private, nothing's public, and there's no cost. If you run into any trouble getting in, just let me know.",
    "",
    "— Asif",
  );

  return lines.join("\n");
}
