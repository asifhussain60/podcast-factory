/**
 * ReadAloud — browser Speech Synthesis API as the default TTS engine.
 *
 * Why native: zero round-trip, instant start, free, voice list on macOS
 * is genuinely good (Samantha, Karen, Daniel, etc.). Sentence-level
 * highlighting moves with the cursor so the reader can follow along
 * visually while listening.
 *
 * Glossary terms get pronounced with their audio_phonetic when speech
 * passes through them (we substitute the audio_phonetic for the written
 * form before speaking — gives correct prosody on "JAH-far ibn man-SOOR
 * al-YAH-man").
 *
 * Phase 4 hook: a future Azure Neural endpoint can register here as a
 * higher-quality engine option without rewriting the UI.
 */

import { useEffect, useRef, useState } from 'react';

type Status = 'idle' | 'playing' | 'paused';

interface Sentence { node: HTMLElement; text: string; }

function collectSentences(): Sentence[] {
  const article = document.querySelector('.prose-body');
  if (!article) return [];
  const blocks = Array.from(article.querySelectorAll('p, h2, h3, li, blockquote')) as HTMLElement[];
  const out: Sentence[] = [];
  blocks.forEach((b) => {
    // For each glossary span, substitute its data-audio for the visible text
    // so the speech synthesizer uses the phonetic pronunciation. We do this
    // by walking the DOM rather than reading textContent directly.
    const clone = b.cloneNode(true) as HTMLElement;
    clone.querySelectorAll('.ar-overlay').forEach((s) => {
      const audio = (s as HTMLElement).dataset.audio;
      const fallback = (s as HTMLElement).dataset.phonetic;
      const replacement = audio?.trim() ? audio.replace(/-/g, ' ') : (fallback || (s as HTMLElement).textContent || '');
      s.textContent = ' ' + replacement + ' ';
    });
    const text = (clone.textContent || '').replace(/\s+/g, ' ').trim();
    if (text) out.push({ node: b, text });
  });
  return out;
}

export default function ReadAloud() {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<Status>('idle');
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [voiceURI, setVoiceURI] = useState<string>('');
  const [rate, setRate] = useState(1.0);
  const sentencesRef = useRef<Sentence[]>([]);
  const idxRef = useRef(0);
  const utterRef = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    const refresh = () => {
      const list = speechSynthesis.getVoices().filter((v) => v.lang.startsWith('en'));
      setVoices(list);
      if (!voiceURI && list.length) {
        const preferred = list.find((v) => /samantha|karen|daniel|moira|tessa/i.test(v.name)) ?? list[0];
        setVoiceURI(preferred.voiceURI);
      }
    };
    refresh();
    speechSynthesis.addEventListener('voiceschanged', refresh);
    return () => speechSynthesis.removeEventListener('voiceschanged', refresh);
  }, [voiceURI]);

  const highlight = (i: number) => {
    sentencesRef.current.forEach((s, j) => {
      if (j === i) {
        s.node.classList.add('reading-active');
        s.node.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } else {
        s.node.classList.remove('reading-active');
      }
    });
  };

  const speakFrom = (start: number) => {
    speechSynthesis.cancel();
    const sentences = sentencesRef.current;
    if (start >= sentences.length) { setStatus('idle'); highlight(-1); return; }
    idxRef.current = start;
    highlight(start);
    const u = new SpeechSynthesisUtterance(sentences[start].text);
    const v = voices.find((x) => x.voiceURI === voiceURI);
    if (v) u.voice = v;
    u.rate = rate;
    u.onend = () => {
      if (utterRef.current === u && status !== 'paused') speakFrom(start + 1);
    };
    utterRef.current = u;
    speechSynthesis.speak(u);
  };

  const play = () => {
    if (status === 'paused') {
      speechSynthesis.resume();
      setStatus('playing');
      return;
    }
    sentencesRef.current = collectSentences();
    // Find sentence nearest the top of the viewport.
    const top = window.scrollY + 100;
    const idx = sentencesRef.current.findIndex((s) => s.node.getBoundingClientRect().top + window.scrollY >= top);
    speakFrom(Math.max(0, idx));
    setStatus('playing');
  };

  const pause = () => { speechSynthesis.pause(); setStatus('paused'); };
  const stop = () => { speechSynthesis.cancel(); highlight(-1); setStatus('idle'); };

  useEffect(() => () => { speechSynthesis.cancel(); }, []);

  // Apply highlight CSS once.
  useEffect(() => {
    if (document.getElementById('read-aloud-style')) return;
    const style = document.createElement('style');
    style.id = 'read-aloud-style';
    style.textContent = `.reading-active { background: color-mix(in oklab, #f59e0b 18%, transparent); border-radius: 3px; transition: background 200ms; }`;
    document.head.appendChild(style);
  }, []);

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 left-6 z-40 inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white px-3 py-2 text-[12px] font-medium text-stone-700 shadow-md transition hover:-translate-y-0.5 hover:border-amber-400 hover:text-amber-700 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-200"
        title="Read this chapter aloud"
      >
        <span aria-hidden>🔊</span>
        <span>Read aloud</span>
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 left-6 z-40 w-[320px] rounded-xl border border-stone-200 bg-white p-3 shadow-2xl dark:border-stone-700 dark:bg-stone-800">
      <div className="mb-2 flex items-center justify-between">
        <div className="font-ui text-[10px] font-semibold uppercase tracking-wider text-stone-500">Read aloud</div>
        <button onClick={() => { stop(); setOpen(false); }} className="text-stone-400 hover:text-stone-900 dark:hover:text-stone-100" aria-label="Close">✕</button>
      </div>
      <div className="flex items-center gap-2">
        {status !== 'playing' ? (
          <button onClick={play} className="rounded bg-amber-600 px-3 py-1.5 text-[12px] font-semibold text-white hover:bg-amber-700">
            {status === 'paused' ? '▶ Resume' : '▶ Play'}
          </button>
        ) : (
          <button onClick={pause} className="rounded bg-stone-700 px-3 py-1.5 text-[12px] font-semibold text-white hover:bg-stone-800">⏸ Pause</button>
        )}
        <button onClick={stop} className="rounded border border-stone-300 px-2 py-1.5 text-[12px] dark:border-stone-600">⏹</button>
      </div>
      <div className="mt-3">
        <label className="font-ui text-[10px] uppercase tracking-wider text-stone-500">Voice</label>
        <select
          value={voiceURI}
          onChange={(e) => setVoiceURI(e.target.value)}
          className="mt-1 w-full rounded border border-stone-300 bg-white px-2 py-1 text-[12px] dark:border-stone-600 dark:bg-stone-800"
        >
          {voices.map((v) => <option key={v.voiceURI} value={v.voiceURI}>{v.name} ({v.lang})</option>)}
        </select>
      </div>
      <div className="mt-2">
        <label className="font-ui text-[10px] uppercase tracking-wider text-stone-500">Speed: {rate.toFixed(2)}×</label>
        <input
          type="range" min={0.6} max={1.8} step={0.05}
          value={rate}
          onChange={(e) => {
            const r = Number(e.target.value);
            setRate(r);
            if (utterRef.current) {
              // applying mid-utterance restarts from current sentence cleanly
              speakFrom(idxRef.current);
            }
          }}
          className="mt-1 w-full"
        />
      </div>
      <div className="mt-2 font-ui text-[10px] text-stone-400">
        Glossary terms are pronounced from their audio_phonetic.
      </div>
    </div>
  );
}
