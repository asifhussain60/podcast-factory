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

/** What they can open, as the sentence fragment that follows "You've got:". */
function whatTheyHave(books: string[], wholeLibrary: boolean): string | null {
  if (wholeLibrary) return "everything in the library";
  if (books.length === 0) return null;
  if (books.length === 1) return books[0];
  if (books.length === 2) return `${books[0]} and ${books[1]}`;
  return `${books.slice(0, -1).join(", ")} and ${books[books.length - 1]}`;
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
  const has = whatTheyHave(input.books, input.wholeLibrary);

  // NOT hard-wrapped. Each paragraph is one line and the receiving app wraps it
  // to its own width. Wrapping at a fixed column looked tidy in a desktop
  // textarea and broke everywhere else: pasted into WhatsApp on a phone it wraps
  // a second time, so every third line was a stray orphan — "edition," and
  // "work." alone on a line. Blank lines between paragraphs are the only
  // structure that survives being pasted anywhere.
  const lines = [
    `Hi ${name},`,
    "",
    "I've been putting together a little library of classical Islamic works and I've set you up with access. Each book comes two ways — a proper English edition you can read, and a series of long-form audio episodes on the same material. Read it, listen to it, or do both.",
    "",
    input.siteUrl,
    "",
    `Sign in with Google using ${input.email} — that's the address I've set it up under, so another account won't find it.`,
    "",
  ];

  // Omitted entirely when they hold nothing yet, rather than printed empty. A
  // line reading "You've got:" with nothing after it tells them something has
  // gone wrong, when the truthful state is simply that the books come next.
  if (has !== null) {
    lines.push(`You've got: ${has}`, "");
  }

  lines.push(
    `Once you're in, have a look at this — it runs through everything the site does, including highlighting, notes and the transcripts: ${aboutUrl(input.siteUrl)}`,
    "",
    "It's all private, nothing's public, and there's nothing to pay. Any trouble getting in, just tell me.",
    "",
    "— Asif",
  );

  return lines.join("\n");
}
