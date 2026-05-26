/**
 * AskChapter — chapter-grounded chat in the right rail.
 *
 * Streams replies via /api/ai/ask-chapter (SSE).
 * No Tailwind utility classes — see chapter-viewer.css.
 */

import { useEffect, useRef, useState } from 'react';

interface Props {
  book: string;
  chapterTitle: string;
  chapterText: string;
}

interface Msg { role: 'user' | 'model'; text: string; }

export default function AskChapter({ book, chapterTitle, chapterText }: Props) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const send = async () => {
    const q = input.trim();
    if (!q || busy) return;
    setInput('');
    const history = messages.slice();
    setMessages([...history, { role: 'user', text: q }, { role: 'model', text: '' }]);
    setBusy(true);
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    try {
      const res = await fetch('/api/ai/ask-chapter', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          chapterText, chapterTitle, bookContext: book,
          history: history.map((m) => ({ role: m.role, text: m.text })),
          question: q,
        }),
        signal: abortRef.current.signal,
      });
      if (!res.ok || !res.body) throw new Error(`AI ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      let acc = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const events = buf.split('\n\n');
        buf = events.pop() ?? '';
        for (const ev of events) {
          const dataLine = ev.split('\n').find((l) => l.startsWith('data:'));
          if (!dataLine) continue;
          try {
            const payload = JSON.parse(dataLine.slice(5).trim());
            if (payload.text) {
              acc += payload.text;
              setMessages((m) => {
                const copy = m.slice();
                copy[copy.length - 1] = { role: 'model', text: acc };
                return copy;
              });
            }
          } catch { /* skip */ }
        }
      }
    } catch (e) {
      setMessages((m) => {
        const copy = m.slice();
        copy[copy.length - 1] = { role: 'model', text: `_Error: ${(e as Error).message}_` };
        return copy;
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rail-panel">
      <button
        onClick={() => setOpen((v) => !v)}
        className="rail-panel-toggle"
        aria-expanded={open}
      >
        <span>Ask this chapter</span>
        <span className="rail-panel-toggle-icon">{open ? '−' : '+'}</span>
      </button>
      {open && (
        <div className="ask-chapter-body">
          <div
            ref={scrollRef}
            className={`ask-chapter-log ${messages.length === 0 ? 'is-empty' : ''}`}
          >
            {messages.length === 0 && (
              <div className="ask-chapter-placeholder">
                Ask a question grounded in this chapter. The model only sees what's on this page.
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`ask-chapter-msg ask-chapter-msg--${m.role}`}>
                <span className="ask-chapter-msg-role">
                  {m.role === 'user' ? 'You' : 'Gemini'}
                </span>
                <span className="ask-chapter-msg-text">
                  {m.text || (busy && i === messages.length - 1 ? '…' : '')}
                </span>
              </div>
            ))}
          </div>
          <div className="ask-chapter-input-row">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder="What does 'Hujjah' mean here?"
              className="ask-chapter-input"
              disabled={busy}
            />
            <button
              onClick={send}
              disabled={busy || !input.trim()}
              className="rail-btn rail-btn-primary"
            >
              {busy ? '…' : 'Ask'}
            </button>
          </div>
          {messages.length > 0 && (
            <button onClick={() => setMessages([])} className="ask-chapter-clear">
              clear conversation
            </button>
          )}
        </div>
      )}
    </div>
  );
}
