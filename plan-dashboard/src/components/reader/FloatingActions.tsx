/**
 * Bottom-right floating action stack — Copy chapter, Scroll-to-top,
 * Open settings (forwards to ReaderSettings panel via the
 * `reader-settings:open` window event).
 *
 * Auto-hides on scroll-down, shows on scroll-up.
 * No Tailwind utility classes — see chapter-viewer.css.
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
    <div className={`floating-actions ${visible ? 'is-visible' : 'is-hidden'}`}>
      {scrollTopVisible && (
        <button
          onClick={scrollTop}
          title="Back to top (g g)"
          className="floating-action-btn"
          aria-label="Scroll to top"
        >
          <span aria-hidden>↑</span>
        </button>
      )}
      <button
        onClick={copy}
        title="Copy chapter text"
        className={`floating-action-btn ${copied ? 'is-flash' : ''}`}
        aria-label="Copy chapter"
      >
        {copied ? <span aria-hidden>✓</span> : <span aria-hidden>⧉</span>}
      </button>
      <button
        onClick={openSettings}
        title="Reader settings (Aa)"
        className="floating-action-btn is-serif"
        aria-label="Open reader settings"
      >
        Aa
      </button>
    </div>
  );
}
