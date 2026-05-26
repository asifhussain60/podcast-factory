/**
 * CopyButton — small React island that copies a given text payload to the
 * clipboard. Used by the episode and chapter reader pages to copy the full
 * rendered content as structured markdown.
 *
 * Server-renders the text into the `text` prop so the actual formatting
 * happens at build/SSR time. Client only handles the click + clipboard
 * write + transient feedback.
 */

import { useState } from 'react';
import { Copy, Check, AlertCircle } from 'lucide-react';

interface Props {
  text: string;
  label: string;        // e.g. "Copy episode" or "Copy chapter"
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
      // eslint-disable-next-line no-console
      console.error('[CopyButton] copy failed:', err);
      setStatus('error');
      setTimeout(() => setStatus('idle'), 3000);
    }
  };

  const classes = {
    idle: 'border-stone-300 bg-white text-stone-700 hover:border-stone-500 hover:bg-stone-50 hover:text-stone-900',
    copied: 'border-emerald-500 bg-emerald-50 text-emerald-800',
    error: 'border-red-400 bg-red-50 text-red-800',
  }[status];

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
      className={`font-ui inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-semibold shadow-sm transition ${classes}`}
      title={
        status === 'idle'
          ? `Copy formatted markdown to clipboard (${charCount.toLocaleString()} chars · ${lineCount.toLocaleString()} lines)`
          : status === 'copied'
          ? 'Copied to clipboard'
          : 'Clipboard write failed — see console'
      }
      aria-label={status === 'idle' ? label : status === 'copied' ? 'Copied to clipboard' : 'Copy failed'}
    >
      <content.Icon className="h-3.5 w-3.5" />
      <span>{content.label}</span>
    </button>
  );
}
