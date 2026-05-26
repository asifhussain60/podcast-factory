/**
 * Header toggle for the Arabic-script overlay.
 *
 * Writes to the unified `pf-reader:settings` blob. Reflects state onto
 * <body data-arabic="on|off"> which chapter-viewer.css reads.
 * No Tailwind utility classes.
 */

import { useEffect, useState } from 'react';
import { loadSettings, saveSettings } from '../../lib/reader/reader-settings';

export default function ArabicToggle() {
  const [on, setOn] = useState(false);
  const [pulse, setPulse] = useState(false);

  useEffect(() => {
    const s = loadSettings();
    setOn(s.arabicOverlay);
    document.body.dataset.arabic = s.arabicOverlay ? 'on' : 'off';
    document.documentElement.dataset.arabic = s.arabicOverlay ? 'on' : 'off';
    const seen = sessionStorage.getItem('pf-reader:arabic-pulse-seen');
    if (!seen) {
      setPulse(true);
      sessionStorage.setItem('pf-reader:arabic-pulse-seen', '1');
      setTimeout(() => setPulse(false), 2000);
    }
  }, []);

  useEffect(() => {
    document.body.dataset.arabic = on ? 'on' : 'off';
    document.documentElement.dataset.arabic = on ? 'on' : 'off';
    saveSettings({ arabicOverlay: on });
  }, [on]);

  return (
    <button
      type="button"
      onClick={() => setOn((v) => !v)}
      className={`arabic-toggle ${on ? 'is-on' : 'is-off'} ${pulse ? 'is-pulsing' : ''}`}
      aria-pressed={on}
      title={on ? 'Hide Arabic script' : 'Replace transliteration with Arabic script'}
    >
      <span aria-hidden className="arabic-toggle-glyph">ع</span>
      <span className="arabic-toggle-label">Arabic script</span>
      <span className="arabic-toggle-badge">{on ? 'On' : 'Off'}</span>
    </button>
  );
}
