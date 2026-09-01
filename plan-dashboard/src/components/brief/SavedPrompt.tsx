/**
 * SavedPrompt — the hand-off prompt for a book whose settings were just saved.
 *
 * The EDIT path had no equivalent of PromptPanel: commissioning something new
 * ended with a prompt you could paste into Claude Code, but correcting an
 * existing book ended with a list of what was written and nothing to hand on.
 * Having just set forty fields, the one thing you want next is to tell someone
 * about them.
 *
 * Its own component rather than a mode on PromptPanel: that one is about a
 * generated brief — it names the brief folder, lists the files copied into it,
 * says whether it replaced a previous one, and offers to send the whole thing
 * to the launcher. None of that exists here, and threading four dead props
 * through it to render one textarea would make both harder to read.
 *
 * The textarea is the copy fallback as well as the display, for the reason
 * PromptPanel gives: navigator.clipboard is available on localhost, but a
 * denied permission would otherwise leave no way to get the text out.
 */
import { useRef, useState } from "react";

interface Props {
  prompt: string;
  slug: string;
}

export default function SavedPrompt({ prompt, slug }: Props) {
  const [copied, setCopied] = useState(false);
  const ref = useRef<HTMLTextAreaElement | null>(null);

  async function copy() {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    } catch {
      ref.current?.select();
    }
  }

  return (
    <div className="bf-saved-prompt">
      <div className="bf-saved-prompt-head">
        <h3 className="bf-saved-prompt-title">Hand this on</h3>
        <button type="button" className="bf-btn" onClick={copy}>
          {copied ? "Copied" : "Copy the prompt"}
        </button>
      </div>
      <p className="intake-hint">
        Paste this into Claude Code or Cowork to pick {slug} up with these
        settings.
      </p>
      <textarea
        ref={ref}
        className="bf-saved-prompt-text"
        readOnly
        rows={10}
        value={prompt}
        aria-label={`Hand-off prompt for ${slug}`}
      />
    </div>
  );
}
