/**
 * CopyButton — copies a text payload to clipboard.
 *
 * Plan-dashboard editorial theme; no Tailwind utility classes — every
 * visual rule lives in chapter-viewer.css.
 */

import { useState } from 'react';
import { Copy, Check, AlertCircle } from 'lucide-react';

interface Props {
  text: string;
  label: string;
}

type Status = 'idle' | 'copied' | 'error';

export default function CopyButton({ text, label }: Props) {
  const [status, setStatus] = useState<Status>('idle');

  const handleCopy = async () => {
    try {
      if (!navigator.clipboard) {
        throw new Error('Clipboard API not available');
      }
      await navigator.clipboard.writeText(text);
      setStatus('copied');
      setTimeout(() => setStatus('idle'), 2000);
    } catch (err) {
      console.error('[CopyButton] copy failed:', err);
      setStatus('error');
      setTimeout(() => setStatus('idle'), 3000);
    }
  };

  const content = {
    idle: { Icon: Copy, label },
    copied: { Icon: Check, label: 'Copied!' },
    error: { Icon: AlertCircle, label: 'Copy failed' },
  }[status];

  const charCount = text.length;
  const lineCount = text.split('\n').length;

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={`copy-btn copy-btn--${status}`}
      title={
        status === 'idle'
          ? `Copy formatted markdown to clipboard (${charCount.toLocaleString()} chars · ${lineCount.toLocaleString()} lines)`
          : status === 'copied'
          ? 'Copied to clipboard'
          : 'Clipboard write failed — see console'
      }
      aria-label={status === 'idle' ? label : status === 'copied' ? 'Copied to clipboard' : 'Copy failed'}
    >
      <content.Icon className="copy-btn-icon" size={14} />
      <span>{content.label}</span>
    </button>
  );
}
