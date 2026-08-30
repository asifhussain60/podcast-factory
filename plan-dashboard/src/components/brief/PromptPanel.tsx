/**
 * PromptPanel — the generated hand-off prompt, ready to paste into Claude Code
 * or Cowork.
 *
 * The textarea is the copy fallback as well as the display: navigator.clipboard
 * is available on localhost (a secure context) but a denied permission or a
 * non-secure host would otherwise leave no way to get the text out, so the
 * button falls back to selecting it.
 */
import { useRef, useState } from "react";

interface Props {
  prompt: string;
  briefDir: string;
  files: string[];
  replaced: boolean;
  onSendToLauncher: () => void;
}

export default function PromptPanel({
  prompt,
  briefDir,
  files,
  replaced,
  onSendToLauncher,
}: Props) {
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
    <div className="bf-prompt">
      <p className="bf-prompt-lede">
        Paste this into Claude Code or Cowork on any machine. It carries the
        whole commission, source paths included.
      </p>
      <textarea
        ref={ref}
        className="bf-prompt-text"
        readOnly
        rows={16}
        value={prompt}
        aria-label="Hand-off prompt"
      />
      <div className="bf-prompt-actions">
        <button type="button" className="bf-btn bf-btn-primary" onClick={copy}>
          {copied ? "Copied" : "Copy the prompt"}
        </button>
        <button type="button" className="bf-btn" onClick={onSendToLauncher}>
          Send to the launcher
        </button>
      </div>
      <dl className="bf-prompt-meta">
        <dt>Brief written to</dt>
        <dd>
          <code>{briefDir}</code>
          {replaced && (
            <span className="bf-replaced"> — replaced an earlier one</span>
          )}
        </dd>
        {files.length > 0 && (
          <>
            <dt>Source kept at</dt>
            <dd>
              {files.map((f) => (
                <code key={f} className="bf-prompt-file">
                  {f}
                </code>
              ))}
            </dd>
          </>
        )}
      </dl>
      <p className="intake-hint bf-note">
        Nothing has been created yet — no folder, no branch, no pipeline run.
        That still starts at the launcher, after we have been through the brief.
      </p>
    </div>
  );
}
