/**
 * VoicePicker — Screen-2 voice + audio-engine selector for new-content intake.
 *
 * Lets the operator choose the book's audio engine (ElevenLabs = autonomous,
 * the default for Islamic content; NotebookLM = manual upload ritual) and, when
 * ElevenLabs is chosen, ONE male (scholar / HOST_A) + ONE female (seeker /
 * HOST_B) from the approved pools (GET /api/intake/voices → voice-library.yaml).
 *
 * Each card shows a monogram avatar (accent-tinted, no external images / no
 * likeness concerns), the real profile name + accent, and a play button for a
 * short sample clip (/voice-samples/<name>.mp3). Selections are emitted as flat
 * settings keys (audio_engine, voice_cast_host_a, voice_cast_host_b) that
 * intake_launch stamps into series-config.yaml.
 *
 * Dependency-free, class-driven, external CSS only (Cortex DoD): zero inline
 * styles — the accent tint is carried by a data-accent attribute the CSS targets.
 */
import { useEffect, useRef, useState } from "react";

interface VoiceEntry {
  name: string;
  fullName: string;
  voiceId: string;
  accent: string;
  sample: string | null;
}
interface Pools {
  males: VoiceEntry[];
  females: VoiceEntry[];
}

interface Props {
  /** Per-profile default engine ('elevenlabs' for Islamic). */
  defaultEngine?: string;
  /** Default cast library names (e.g. Eric / Lily). */
  defaultHostA?: string;
  defaultHostB?: string;
  /** Emits flat settings keys whenever the selection changes. */
  onChange?: (patch: {
    audio_engine: string;
    voice_cast_host_a: string;
    voice_cast_host_b: string;
  }) => void;
}

function initialOf(name: string): string {
  return (name.trim()[0] ?? "?").toUpperCase();
}

function accentLabel(accent: string): string {
  if (accent === "arabic_bilingual") return "Arabic-bilingual";
  return accent ? accent.charAt(0).toUpperCase() + accent.slice(1) : "";
}

export default function VoicePicker({
  defaultEngine = "elevenlabs",
  defaultHostA = "Eric",
  defaultHostB = "Lily",
  onChange,
}: Props) {
  const [pools, setPools] = useState<Pools | null>(null);
  const [error, setError] = useState("");
  const [engine, setEngine] = useState(defaultEngine);
  const [hostA, setHostA] = useState(defaultHostA);
  const [hostB, setHostB] = useState(defaultHostB);
  const [playing, setPlaying] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Load the approved pools once; settle the default cast to real names.
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const r = await fetch("/api/intake/voices");
        const json = await r.json();
        if (!alive) return;
        if (!r.ok || !json.ok) {
          setError(json.error ?? "Could not load voices");
          return;
        }
        const p: Pools = json.data;
        setPools(p);
        const a =
          p.males.find((m) => m.name === defaultHostA)?.name ??
          p.males[0]?.name ??
          "";
        const b =
          p.females.find((f) => f.name === defaultHostB)?.name ??
          p.females[0]?.name ??
          "";
        setHostA(a);
        setHostB(b);
      } catch (e) {
        if (alive) setError(`Network error: ${String(e)}`);
      }
    })();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Propagate the resolved selection upward.
  useEffect(() => {
    onChange?.({
      audio_engine: engine,
      voice_cast_host_a: hostA,
      voice_cast_host_b: hostB,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [engine, hostA, hostB]);

  function playSample(entry: VoiceEntry) {
    if (!entry.sample) return;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (playing === entry.name) {
      setPlaying(null);
      return;
    }
    const audio = new Audio(`/voice-samples/${entry.sample}`);
    audio.onended = () => setPlaying(null);
    audio.onerror = () => setPlaying(null);
    audioRef.current = audio;
    setPlaying(entry.name);
    void audio.play().catch(() => setPlaying(null));
  }

  function renderColumn(
    role: "A" | "B",
    heading: string,
    sub: string,
    entries: VoiceEntry[],
  ) {
    const selected = role === "A" ? hostA : hostB;
    const setSel = role === "A" ? setHostA : setHostB;
    return (
      <div className="voice-col">
        <h3 className="voice-col-title">{heading}</h3>
        <p className="voice-col-sub">{sub}</p>
        <ul className="voice-list" aria-label={heading}>
          {entries.map((v) => {
            const isSel = v.name === selected;
            return (
              <li key={v.voiceId || v.name}>
                <div
                  className={`voice-card${isSel ? " voice-card--selected" : ""}`}
                >
                  <button
                    type="button"
                    className="voice-pick"
                    aria-pressed={isSel}
                    onClick={() => setSel(v.name)}
                  >
                    <span
                      className="voice-avatar"
                      data-accent={v.accent}
                      aria-hidden="true"
                    >
                      {initialOf(v.name)}
                    </span>
                    <span className="voice-meta">
                      <span className="voice-name">{v.name}</span>
                      <span className="voice-accent">
                        {accentLabel(v.accent)}
                      </span>
                    </span>
                  </button>
                  {v.sample && (
                    <button
                      type="button"
                      className={`voice-sample${playing === v.name ? " voice-sample--playing" : ""}`}
                      onClick={() => playSample(v)}
                      aria-label={`${playing === v.name ? "Stop" : "Play"} ${v.name} sample`}
                    >
                      {playing === v.name ? "◼ Stop" : "▶ Hear"}
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    );
  }

  return (
    <div className="intake-card">
      <h2 className="intake-card-title">Audio engine &amp; voices</h2>
      <p className="intake-hint">
        ElevenLabs renders the episodes automatically in the voices you pick
        here. NotebookLM is the manual upload path — you can still send
        individual episodes to NotebookLM later.
      </p>

      <div className="intake-field" role="group" aria-label="Audio engine">
        <span className="intake-label">Audio engine</span>
        <div className="voice-engine">
          {[
            {
              id: "elevenlabs",
              label: "ElevenLabs",
              sub: "Default · auto-rendered",
            },
            { id: "notebooklm", label: "NotebookLM", sub: "Manual upload" },
          ].map((opt) => (
            <button
              key={opt.id}
              type="button"
              aria-pressed={engine === opt.id}
              className={`voice-engine-opt${engine === opt.id ? " voice-engine-opt--selected" : ""}`}
              onClick={() => setEngine(opt.id)}
            >
              <span className="voice-engine-name">{opt.label}</span>
              <span className="voice-engine-sub">{opt.sub}</span>
            </button>
          ))}
        </div>
      </div>

      {error && (
        <p className="intake-error" role="alert">
          {error}
        </p>
      )}

      {engine === "elevenlabs" &&
        (pools ? (
          <div className="voice-grid">
            {renderColumn(
              "A",
              "Scholar voice",
              "Male · leads the teaching",
              pools.males,
            )}
            {renderColumn(
              "B",
              "Seeker voice",
              "Female · asks the questions",
              pools.females,
            )}
          </div>
        ) : (
          !error && (
            <p className="intake-hint" role="status">
              Loading voices…
            </p>
          )
        ))}
    </div>
  );
}
