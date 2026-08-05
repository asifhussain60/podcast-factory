import { faCopy, faXmark } from "@fortawesome/free-solid-svg-icons";
import { useEffect, useRef, useState } from "react";

import { Icon } from "~/components/Icon";
import { inviteMessage, type InviteMessageInput } from "~/lib/inviteMessage";

/**
 * The note to send somebody, ready to copy.
 *
 * A native `<dialog>`, not a hand-built overlay. Focus trapping, Escape, inert
 * background and the top layer are all things the platform already does
 * correctly and that a div-with-a-z-index gets wrong in ways nobody notices
 * until a keyboard user is stuck behind it.
 *
 * The message is in a `<textarea>` rather than a `<pre>` so it can be read,
 * corrected before sending, and selected by hand if the clipboard is refused —
 * which it is on any page not served over https, and this admin screen is used
 * on localhost. The Copy button is the fast path, never the only one.
 */
export function InviteMessage({
  open,
  onClose,
  ...message
}: { open: boolean; onClose: () => void } & InviteMessageInput) {
  const ref = useRef<HTMLDialogElement>(null);
  const [text, setText] = useState("");

  // Rebuilt whenever the dialog opens, not on every render: it is editable, and
  // regenerating under the administrator mid-correction would discard what they
  // had typed.
  useEffect(() => {
    if (!open) return;
    setText(inviteMessage(message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, message.email, message.books.join("|"), message.wholeLibrary]);

  // `showModal()` rather than the `open` attribute — only the method puts the
  // dialog in the top layer and makes the rest of the page inert.
  useEffect(() => {
    const el = ref.current;
    if (el === null) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  /**
   * Copy, and get out of the way.
   *
   * Closing is the confirmation: the administrator's next act is to paste it
   * somewhere else, and a dialog still sitting over the screen is one more press
   * before they can.
   *
   * ONLY on success, which is the whole reason this is not one line. The
   * clipboard is refused outright on any page not served over https, and this
   * screen is used on localhost — so an unconditional close would shut the dialog
   * having copied nothing, and the administrator would paste whatever was in the
   * clipboard before. On the failure path the dialog STAYS, with its text
   * selected, so the keyboard shortcut is one press away.
   *
   * There is no "Copied" state any more, because closing IS the acknowledgement
   * and nothing could observe the label change in the frame before the dialog
   * went away.
   */
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      onClose();
    } catch {
      const field = ref.current?.querySelector("textarea");
      field?.select();
    }
  }

  return (
    <dialog ref={ref} onClose={onClose} onCancel={onClose} className="pf-dialog">
      <div className="pf-dialog__head">
        <h2 className="pf-dialog__title">Send them this</h2>
        <button type="button" onClick={onClose} className="pf-button pf-button--soft pf-button--sm">
          <Icon icon={faXmark} />
          Close
        </button>
      </div>

      <p className="pf-note pf-note--quiet">
        Paste it into a message or an email. You can edit it here first — nothing is
        sent from this page.
      </p>

      {/* The link is the site's declared base address, which on this machine is
          localhost. Said plainly, because a message that looks finished and
          carries a link only the sender can open is worse than one that warns. */}
      {/^https?:\/\/(localhost|127\.0\.0\.1)/.test(message.siteUrl) ? (
        <p className="pf-message pf-message--danger">
          This link points at your own machine, so nobody else can open it. Generate
          the message on the live site before sending it.
        </p>
      ) : null}

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={20}
        aria-label="The message to send"
        className="pf-dialog__text"
      />

      <div className="pf-dialog__foot">
        <button type="button" onClick={copy} className="pf-button pf-button--primary">
          <Icon icon={faCopy} />
          Copy to clipboard
        </button>
      </div>
    </dialog>
  );
}
