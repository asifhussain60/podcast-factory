/**
 * PhoneticsGenerator — interactive "generate from Arabic" widget.
 *
 * Takes a word in Arabic script or transliteration, calls /api/phonetic-generate
 * (Gemini Flash), and shows the house-style respelling inline.
 *
 * No inline styles — class-driven via pronunciation.css (.phgen-*).
 */

import { useState } from 'react';

export default function PhoneticsGenerator() {
  const [word, setWord] = useState('');
  const [result, setResult] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function generate() {
    const w = word.trim();
    if (!w) return;
    setLoading(true);
    setResult('');
    setError('');
    try {
      const res = await fetch('/api/phonetic-generate', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ word: w }),
      });
      const json = await res.json();
      if (!json.ok) throw new Error(json.error ?? 'request failed');
      setResult(json.data.phonetic);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  function onKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') generate();
  }

  return (
    <div className="phgen">
      <div className="phgen-row">
        <input
          className="phgen-input"
          type="text"
          value={word}
          onChange={(e) => { setWord(e.target.value); setResult(''); setError(''); }}
          onKeyDown={onKey}
          placeholder="Arabic word or transliteration…"
          aria-label="Word to generate a house-style respelling for"
          disabled={loading}
        />
        <button
          className="phgen-btn"
          onClick={generate}
          disabled={loading || !word.trim()}
          aria-label="Generate respelling"
        >
          {loading ? 'Generating…' : 'Generate'}
        </button>
      </div>
      {result && (
        <p className="phgen-result" role="status">
          <code className="phgen-phonetic">{result}</code>
        </p>
      )}
      {error && (
        <p className="phgen-error" role="alert">{error}</p>
      )}
    </div>
  );
}
