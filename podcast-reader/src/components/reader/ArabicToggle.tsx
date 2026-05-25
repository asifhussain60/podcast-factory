/**
 * Client island: header toggle for the Arabic-script overlay.
 *
 * Writes to the unified `podcast-reader:settings` blob (schema v1) so it
 * stays in sync with the Phase-2 ReaderSettings panel. Reflects state
 * onto <body data-arabic="on|off"> which the CSS in global.css reads.
 *
 * Visual: prominent pill with an Amiri "ع" + label + ON/OFF badge. On
 * first page load the pill pulses once (1.8s) to draw attention.
 */

import { useEffect, useState } from 'react';
import { loadSettings, saveSettings } from '~/lib/reader-settings';

export default function ArabicToggle() {
  const [on, setOn] = useState(false);
  const [pulse, setPulse] = useState(false);

  useEffect(() => {
    const s = loadSettings();
    setOn(s.arabicOverlay);
    document.body.dataset.arabic = s.arabicOverlay ? 'on' : 'off';
    const seen = sessionStorage.getItem('podcast-reader:arabic-pulse-seen');
    if (!seen) {
      setPulse(true);
      sessionStorage.setItem('podcast-reader:arabic-pulse-seen', '1');
      setTimeout(() => setPulse(false), 2000);
    }
  }, []);

  useEffect(() => {
    document.body.dataset.arabic = on ? 'on' : 'off';
    saveSettings({ arabicOverlay: on });
  }, [on]);

  return (
    <button
      type="button"
      onClick={() => setOn((v) => !v)}
      className={
        'group inline-flex items-center gap-2 rounded-full border-2 px-3 py-1.5 text-[12px] font-medium transition-all duration-200 ' +
        (on
          ? 'border-amber-500 bg-amber-50 text-amber-900 shadow-sm hover:bg-amber-100 dark:bg-amber-900/30 dark:text-amber-100'
          : 'border-amber-400/70 bg-white text-stone-700 hover:border-amber-500 hover:bg-amber-50 hover:-translate-y-px hover:shadow-sm') +
        (pulse ? ' animate-arabic-pulse' : '')
      }
      aria-pressed={on}
      title={on ? 'Hide Arabic script' : 'Replace transliteration with Arabic script'}
    >
      <span aria-hidden style={{ fontFamily: 'Amiri, serif', fontSize: '18px', lineHeight: 1 }}>ع</span>
      <span className="hidden sm:inline">Arabic script</span>
      <span className={
        'rounded-full px-1.5 py-0 text-[9px] font-bold uppercase tracking-wider ' +
        (on ? 'bg-amber-600 text-white' : 'bg-stone-200 text-stone-600')
      }>{on ? 'On' : 'Off'}</span>
      <style>{`
        @keyframes arabicPulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(217, 119, 6, 0); }
          50%      { box-shadow: 0 0 0 6px rgba(217, 119, 6, 0.25); }
        }
        .animate-arabic-pulse { animation: arabicPulse 1.8s ease-in-out 2; }
      `}</style>
    </button>
  );
}
