/**
 * Bottom-right floating action stack — Copy chapter, Scroll-to-top,
 * Open settings (settings trigger forwards to ReaderSettings panel via
 * the `reader-settings:open` window event).
 *
 * Auto-hides on scroll-down, shows on scroll-up. Always visible near the
 * page bottom so end-of-chapter actions are one click away.
 */

import { useEffect, useState } from 'react';

interface Props {
  copyText: string;
}

export default function FloatingActions({ copyText }: Props) {
  const [visible, setVisible] = useState(true);
  const [copied, setCopied] = useState(false);
  const [scrollTopVisible, setScrollTopVisible] = useState(false);

  useEffect(() => {
    let lastY = window.scrollY;
    const onScroll = () => {
      const y = window.scrollY;
      setScrollTopVisible(y > 600);
      const goingDown = y > lastY + 6;
      const goingUp = y < lastY - 6;
      if (goingDown) setVisible(false);
      else if (goingUp) setVisible(true);
      // Always visible near bottom
      if (y + window.innerHeight > document.documentElement.scrollHeight - 200) setVisible(true);
      lastY = y;
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(copyText);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch { /* clipboard blocked */ }
  };

  const scrollTop = () => window.scrollTo({ top: 0, behavior: 'smooth' });
  const openSettings = () => window.dispatchEvent(new CustomEvent('reader-settings:open'));

  return (
    <div
      className={
        'fixed bottom-6 right-6 z-40 flex flex-col gap-2 transition-all duration-300 ' +
        (visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none')
      }
    >
      {scrollTopVisible && (
        <button
          onClick={scrollTop}
          title="Back to top (g g)"
          className="h-10 w-10 rounded-full border border-stone-200 bg-white text-stone-600 shadow-md transition hover:-translate-y-0.5 hover:text-amber-700 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-300"
          aria-label="Scroll to top"
        >
          <span aria-hidden>↑</span>
        </button>
      )}
      <button
        onClick={copy}
        title="Copy chapter text"
        className="h-10 w-10 rounded-full border border-stone-200 bg-white text-stone-600 shadow-md transition hover:-translate-y-0.5 hover:text-amber-700 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-300"
        aria-label="Copy chapter"
      >
        {copied ? <span aria-hidden>✓</span> : <span aria-hidden style={{ fontFamily: 'system-ui' }}>⧉</span>}
      </button>
      <button
        onClick={openSettings}
        title="Reader settings (Aa)"
        className="h-10 w-10 rounded-full border border-stone-200 bg-white font-serif text-stone-700 shadow-md transition hover:-translate-y-0.5 hover:text-amber-700 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-300"
        aria-label="Open reader settings"
      >
        Aa
      </button>
    </div>
  );
}
