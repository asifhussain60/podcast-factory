import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Link } from "react-router";

import { NotesList } from "~/components/reader/NotesList";
import { RichNoteEditor } from "~/components/notes/RichNoteEditor";
import { Transcript, parseVtt, type Cue } from "~/components/player/Transcript";
import { newId, refresh, type EpisodeNote } from "~/lib/marks";

/**
 * One <audio> element for the whole site.
 *
 * It lives in the authenticated LAYOUT, not in any page, which is the only way
 * playback survives navigation: React Router keeps a layout mounted across
 * client transitions, so moving from an episode to a chapter re-renders the
 * outlet and leaves this element — and the sound — untouched. An <audio> per
 * page would stop the moment the reader followed a link.
 *
 * No volume control anywhere in here. iOS silently ignores `volume` on
 * HTMLMediaElement, so a slider would be a control that visibly does nothing on
 * the platform most of this listening happens on. The device's own buttons are
 * the volume control.
 */

export interface NowPlaying {
  slug: string;
  bookTitle: string;
  number: number;
  title: string;
  src: string;
  durationS: number | null;
  /** The media URL of this episode's WebVTT, or null when none was made. */
  transcriptSrc: string | null;
}

/** Which side panel the player is showing, or none. */
export type PlayerPanel = "transcript" | "notes" | null;

interface PlayerState {
  current: NowPlaying | null;
  playing: boolean;
  /** Seconds. Driven by the element, not by us. */
  position: number;
  duration: number;
  rate: number;
  /**
   * What is said in the episode being played, loaded with the audio.
   *
   * Held HERE rather than fetched by the panel that shows it, which is what
   * makes the transcript follow the audio silently: the words are in memory from
   * the moment playback starts, so opening the panel mid-episode lands on the
   * line being spoken instead of showing a spinner. Nothing runs in between —
   * which line is current is derived from `position` at render time, and while
   * the panel is closed nobody asks.
   *
   * Null means either "no transcript for this episode" or "still loading"; the
   * panel says the same thing for both, because a listener can do nothing with
   * either distinction.
   */
  cues: Cue[] | null;
  panel: PlayerPanel;
  openPanel: (panel: PlayerPanel) => void;
  play: (episode: NowPlaying) => void;
  toggle: () => void;
  seek: (seconds: number) => void;
  nudge: (delta: number) => void;
  setRate: (rate: number) => void;
  close: () => void;
}

const PlayerContext = createContext<PlayerState | null>(null);

export const RATES = [0.9, 1, 1.2, 1.5, 1.8] as const;

/**
 * Where the listener had got to, keyed by the EPISODE rather than by its file.
 *
 * This used to key on `episode.src` — the media URL, which contains
 * `media_asset.key`. That key changes whenever an episode's audio is re-uploaded
 * under a new name, and when it does the old entry simply never matches again:
 * everyone silently lost their place, and nothing anywhere reported it, because
 * "no stored position" and "position stored under a name nothing asks for" look
 * identical. `slug` and `number` are the episode's own identity and survive a
 * re-publish exactly as `chapter.anchor_key` does.
 *
 * Local storage is now a CACHE, not the record. The record is
 * `listening_progress` in D1, so closing the iPad and opening the phone resumes
 * where the iPad stopped; the cache is what lets playback resume instantly
 * without waiting for a round trip, and what holds the position when the network
 * is gone.
 */
const POSITION_KEY = "pf-positions";

const positionKey = (slug: string, number: number) => `${slug}#${number}`;

function loadPositions(): Record<string, number> {
  try {
    return JSON.parse(localStorage.getItem(POSITION_KEY) || "{}");
  } catch {
    return {};
  }
}

function savePosition(episode: NowPlaying, seconds: number) {
  const whole = Math.floor(seconds);

  try {
    const all = loadPositions();
    all[positionKey(episode.slug, episode.number)] = whole;
    localStorage.setItem(POSITION_KEY, JSON.stringify(all));
  } catch {
    // Storage disabled. Playback still works; only the local memory is lost —
    // the server copy below is unaffected, which is the point of having both.
  }

  // Throttled to one write a minute, and deliberately not more. A position is
  // only useful to within a few seconds, this fires every five, and a listener
  // going through a two-hour episode would otherwise post 1,400 times.
  const now = Date.now();
  if (now - lastServerWrite < 60_000) return;
  lastServerWrite = now;

  void fetch(`/book/${encodeURIComponent(episode.slug)}/marks`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      intent: "listening",
      number: String(episode.number),
      seconds: String(whole),
    }),
    // The listener is mid-episode; a failed bookkeeping write must not surface
    // as an unhandled rejection in their console.
  }).catch(() => {});
}

let lastServerWrite = 0;

/**
 * Keep a moment of what is playing, with the line that was said at it.
 *
 * A DIRECT post, not a write through the marks store, and that is a correctness
 * requirement rather than a shortcut. `lib/marks.ts` holds one book open at a
 * time — whichever one is being READ — and posts its outbox to that book's
 * endpoint. A listener can have this book's episode playing while reading a
 * different book entirely, and routing this through the store would file the
 * note under the wrong work. `savePosition` above already writes this way, for
 * the same reason.
 *
 * The cost is that this one write has no offline outbox. That is the right trade:
 * a note is made in a moment the listener can see happen, and the alternative is
 * a queue that can attribute it to the wrong book.
 */
function markMoment(
  episode: NowPlaying,
  seconds: number,
  id: string,
  quote: string,
  // Optional and defaulted to "", so the transcript's one-tap "mark this
  // line" action — which has always sent no text — is unaffected by this
  // parameter existing. The same call now also serves the Notes panel's
  // "+ Add note" composer and its edit-in-place save, both of which pass
  // real content.
  note: string = "",
): Promise<boolean> {
  return fetch(`/book/${encodeURIComponent(episode.slug)}/marks`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      intent: "episode-note",
      id,
      number: String(episode.number),
      // Floor, not round: the stored value is where the line STARTS, and the
      // site plays back from a little before it anyway.
      seconds: String(Math.floor(seconds)),
      note,
      quote,
    }),
  })
    .then((response) => response.ok)
    .catch(() => false);
}

/**
 * The server's copy, if it is further along than the cache.
 *
 * "Further along" rather than "newer": there is no clock to trust between two
 * devices, and the failure that actually matters is resuming EARLIER than you
 * got to — re-listening to ten minutes you have already heard. Taking the
 * greater of the two can only ever skip ahead by however far the other device
 * went, which is the direction a listener can correct in one gesture.
 */
async function serverPosition(slug: string, number: number): Promise<number | null> {
  try {
    const response = await fetch(`/book/${encodeURIComponent(slug)}/marks`, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return null;
    const marks = (await response.json()) as { listening?: Record<string, number> };
    return marks.listening?.[String(number)] ?? null;
  } catch {
    return null;
  }
}

export function PlayerProvider({ children }: { children: ReactNode }) {
  const audio = useRef<HTMLAudioElement>(null);
  const [current, setCurrent] = useState<NowPlaying | null>(null);
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);
  const [rate, setRateState] = useState(1);
  const [cues, setCues] = useState<Cue[] | null>(null);
  const [panel, setPanel] = useState<PlayerPanel>(null);

  /**
   * Which episode the cues in state belong to.
   *
   * A ref, not state: it exists to make a late-arriving fetch discard itself
   * when the listener has already moved to another episode, and re-rendering
   * because it changed would be pointless. Without it, opening episode 3 while
   * episode 2's transcript is still in flight shows episode 2's words against
   * episode 3's audio — which is worse than showing none.
   */
  const cuesFor = useRef<string | null>(null);

  const play = useCallback((episode: NowPlaying) => {
    const element = audio.current;
    if (element === null) return;

    if (current?.src === episode.src) {
      void element.play();
      return;
    }

    setCurrent(episode);
    element.src = episode.src;

    // The words, loaded alongside the audio rather than when the panel opens.
    // Cleared FIRST so the panel never shows the previous episode's transcript
    // while this one arrives.
    setCues(null);
    cuesFor.current = episode.src;
    if (episode.transcriptSrc !== null) {
      const wanted = episode.src;
      void fetch(episode.transcriptSrc)
        .then((response) => (response.ok ? response.text() : Promise.reject(new Error("not ok"))))
        .then((text) => {
          if (cuesFor.current !== wanted) return; // they moved on; this is stale
          setCues(parseVtt(text));
        })
        .catch(() => {
          // No transcript to show. The panel says so; playback is unaffected,
          // and a failed side-fetch must not surface as an unhandled rejection
          // in the listener's console mid-episode.
        });
    }

    // Start from the cache immediately — playback must not wait on a request.
    const cached = loadPositions()[positionKey(episode.slug, episode.number)] ?? 0;
    element.currentTime = cached;
    void element.play();

    // Then ask the server, and jump forward only if another device got further.
    // Guarded on the listener not having moved in the meantime: seeking under
    // someone who has already scrubbed would be the player fighting them.
    void serverPosition(episode.slug, episode.number).then((remote) => {
      if (remote === null || remote <= cached + 5) return;
      if (audio.current === null || audio.current.src !== element.src) return;
      if (Math.abs(audio.current.currentTime - cached) > 5) return;
      audio.current.currentTime = remote;
    });
  }, [current]);

  const toggle = useCallback(() => {
    const element = audio.current;
    if (element === null || current === null) return;
    if (element.paused) void element.play();
    else element.pause();
  }, [current]);

  const seek = useCallback((seconds: number) => {
    const element = audio.current;
    if (element !== null) element.currentTime = seconds;
  }, []);

  const nudge = useCallback((delta: number) => {
    const element = audio.current;
    if (element === null) return;
    element.currentTime = Math.max(0, Math.min(element.duration || 0, element.currentTime + delta));
  }, []);

  const setRate = useCallback((next: number) => {
    const element = audio.current;
    if (element !== null) element.playbackRate = next;
    setRateState(next);
  }, []);

  const close = useCallback(() => {
    const element = audio.current;
    if (element !== null) {
      element.pause();
      element.removeAttribute("src");
      element.load();
    }
    setCurrent(null);
    setPlaying(false);
    // The panel belongs to what is playing. Left open over a closed player it
    // would be a transcript of nothing, with no control on screen to shut it.
    setPanel(null);
    setCues(null);
    cuesFor.current = null;
  }, []);

  /** Pressing the open panel's own button closes it, which is what a toggle is. */
  const openPanel = useCallback(
    (next: PlayerPanel) => setPanel((now) => (now === next ? null : next)),
    [],
  );

  const value = useMemo<PlayerState>(
    () => ({
      current,
      playing,
      position,
      duration,
      rate,
      cues,
      panel,
      openPanel,
      play,
      toggle,
      seek,
      nudge,
      setRate,
      close,
    }),
    [current, playing, position, duration, rate, cues, panel, openPanel, play, toggle, seek, nudge, setRate, close],
  );

  return (
    <PlayerContext.Provider value={value}>
      {children}

      <audio
        ref={audio}
        preload="none"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onDurationChange={(e) => setDuration(e.currentTarget.duration || 0)}
        onTimeUpdate={(e) => {
          setPosition(e.currentTarget.currentTime);
          if (current !== null && Math.floor(e.currentTarget.currentTime) % 5 === 0) {
            savePosition(current, e.currentTarget.currentTime);
          }
        }}
      />

      {current === null ? null : (
        <>
          <PlayerPanelDrawer />
          <PlayerBar />
        </>
      )}
    </PlayerContext.Provider>
  );
}

export function usePlayer(): PlayerState {
  const value = useContext(PlayerContext);
  if (value === null) throw new Error("usePlayer must be used inside PlayerProvider");
  return value;
}

/** mm:ss, or —:— when the duration is not known yet. */
export function clock(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds)) return "--:--";
  const total = Math.max(0, Math.floor(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
    : `${m}:${String(s).padStart(2, "0")}`;
}

function PlayerBar() {
  const { current, playing, position, duration, rate, panel, openPanel, toggle, seek, nudge, setRate, close } =
    usePlayer();
  if (current === null) return null;

  const total = duration || current.durationS || 0;

  return (
    <div
      role="region"
      aria-label="Now playing"
      className="pf-player"
    >
      <div className="pf-player__inner">
        <div className="pf-player__top">
          <button
            type="button"
            onClick={toggle}
            aria-label={playing ? "Pause" : "Play"}
            className="pf-player__play"
          >
            {playing ? <PauseIcon /> : <PlayIcon />}
          </button>

          <button
            type="button"
            onClick={() => nudge(-15)}
            aria-label="Back 15 seconds"
            className="pf-player__nudge"
          >
            &minus;15s
          </button>
          <button
            type="button"
            onClick={() => nudge(15)}
            aria-label="Forward 15 seconds"
            className="pf-player__nudge"
          >
            +15s
          </button>

          <div className="pf-player__what">
            <p className="pf-player__title">
              {current.number}. {current.title}
            </p>
            <Link
              to={`/book/${current.slug}`}
              className="pf-player__book"
            >
              {current.bookTitle}
            </Link>
          </div>

          <label className="pf-player__rate">
            <span className="sr-only">Playback speed</span>
            <select
              value={rate}
              onChange={(e) => setRate(Number(e.target.value))}
              className="pf-select pf-select--sm"
            >
              {RATES.map((r) => (
                <option key={r} value={r}>
                  {r}&times;
                </option>
              ))}
            </select>
          </label>

          {/* The two things a listener actually wants while listening, and the
              only controls here that are NOT hidden on a phone. The skip and
              speed controls go at that width; these are the point. */}
          {current.transcriptSrc === null ? null : (
            <button
              type="button"
              onClick={() => openPanel("transcript")}
              aria-expanded={panel === "transcript"}
              className="pf-player__panel-tab"
            >
              Transcript
            </button>
          )}

          <button
            type="button"
            onClick={() => openPanel("notes")}
            aria-expanded={panel === "notes"}
            className="pf-player__panel-tab"
          >
            Notes
          </button>

          <button
            type="button"
            onClick={close}
            aria-label="Close the player"
            className="pf-player__close"
          >
            &times;
          </button>
        </div>

        <div className="pf-player__scrub">
          <span>{clock(position)}</span>
          <input
            type="range"
            min={0}
            max={Math.max(1, total)}
            step={1}
            value={Math.min(position, total || 1)}
            onChange={(e) => seek(Number(e.target.value))}
            aria-label="Seek"
            className="pf-player__seek"
          />
          <span>{clock(total || null)}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * The player's own side panel: what is being said, or what you have marked.
 *
 * It belongs to the PLAYER rather than to any page, for the same reason the
 * <audio> element does — playback outlives navigation, so the transcript of what
 * is playing has to be reachable from wherever the listener happens to be. A
 * transcript that lives on one page is a transcript you have to go and find,
 * which is exactly the failure this replaces.
 *
 * It has no edge tab. The two buttons in the bar are its openers, so no page
 * grows a second tab beside its own, and it is closed until asked for.
 *
 * It is scoped to the PLAYING book, which is not always the book on screen — a
 * chapter of one work can be open while another work's episode plays. So the
 * notes here are fetched for `current.slug` rather than read from the marks
 * store, which holds whichever book is being READ. Same reason the position
 * write posts directly.
 */
function PlayerPanelDrawer() {
  const { current, panel, openPanel, cues, position, seek } = usePlayer();
  const [marks, setMarks] = useState<PlayingMarks | null>(null);
  // The "+ Add note" composer. `composeSeconds` is frozen at the moment the
  // button is pressed, not read again at save time — typing takes a while and
  // playback keeps advancing, so a live read would land the note on whatever
  // second the listener finished typing at, not the one they meant to mark.
  const [composing, setComposing] = useState(false);
  const [composeSeconds, setComposeSeconds] = useState(0);
  const [composeQuote, setComposeQuote] = useState("");
  const [composeDraft, setComposeDraft] = useState("");

  const slug = current?.slug ?? null;

  /* The playing book's own marks. Re-fetched when the panel opens rather than
     held all the time: it is a handful of rows behind a deliberate press, and
     keeping it live would mean polling for something nobody is looking at. */
  const reload = useCallback(() => {
    if (slug === null) return;
    void fetch(`/book/${encodeURIComponent(slug)}/marks`, { headers: { Accept: "application/json" } })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setMarks(data as PlayingMarks | null))
      .catch(() => setMarks(null));
  }, [slug]);

  useEffect(() => {
    if (panel === "notes") reload();
    else setComposing(false);
  }, [panel, reload]);

  if (current === null || panel === null) return null;

  /* THIS EPISODE's notes, not the whole book's.
     The panel belongs to what is playing, exactly as the transcript does — and
     it is also the only honest scope available here: the marks endpoint returns
     notes with an episode NUMBER, and rendering the ones from other episodes
     would need their titles, which nothing on this side has. Showing them as
     bare numbers, or silently dropping them, are both worse than a panel that
     says plainly what it covers. The whole book's notes are one press away on
     the book page, which has the titles. */
  const here = (marks?.episodeNotes ?? []).filter((n) => n.number === current.number);
  const label = panel === "transcript" ? "Transcript" : "Notes in this episode";

  return (
    <>
      {/* Below the player bar in the stack, so the transport stays usable with
          the panel open — pausing while reading along must not mean closing it
          first. */}
      <button
        type="button"
        aria-hidden="true"
        tabIndex={-1}
        onClick={() => openPanel(null)}
        className="pf-player-panel__scrim"
      />

      <aside aria-label={`${label} for ${current.title}`} className="pf-player-panel">
        <div className="pf-drawer__head">
          <h2 className="pf-drawer__title">{label}</h2>
          <button
            type="button"
            onClick={() => openPanel(null)}
            aria-label={`Close ${label.toLowerCase()}`}
            className="pf-tool"
          >
            &times;
          </button>
        </div>

        <div className="pf-drawer__body">
          {panel === "transcript" ? (
            <Transcript
              cues={cues}
              position={position}
              onSeek={seek}
              onNote={(cue) => {
                // Opens the same composer the "+ Add note" button does, on
                // the Notes panel — rather than saving a bare, textless mark
                // on tap. A transcript line's "+" is the one place this
                // composer arrives pre-filled with WHICH line, so the quote
                // travels with it; the timestamp and blank draft otherwise
                // work exactly as the generic composer's do.
                setComposeSeconds(Math.floor(cue.startS));
                setComposeQuote(cue.text);
                setComposeDraft("");
                setComposing(true);
                openPanel("notes");
              }}
            />
          ) : (
            <>
              {/* Not inside the Transcript panel, and not gated on one
                  existing — the Transcript tab button itself is hidden for an
                  episode with no transcript, so this is the only marking
                  control those episodes have at all. */}
              {composing ? (
                <div className="pf-mark pf-mark--moment">
                  <div className="pf-mark__body">
                    <span className="pf-mark__kind">{clock(composeSeconds)}</span>
                    {/* Only present when opened from a transcript line's "+" —
                        the generic "+ Add note" button has no line to quote. */}
                    {composeQuote ? <blockquote className="pf-mark__quote">{composeQuote}</blockquote> : null}
                    <RichNoteEditor
                      initialValue={composeDraft}
                      onChange={setComposeDraft}
                      placeholder="What are you thinking?"
                      autoFocus
                      ariaLabel="Your note at this moment"
                    />
                    <div className="pf-mark__edit-actions">
                      <button
                        type="button"
                        onClick={() => setComposing(false)}
                        className="pf-button pf-button--sm pf-button--ghost"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          void markMoment(current, composeSeconds, newId(), composeQuote, composeDraft).then(
                            (ok) => {
                              setComposing(false);
                              if (!ok) return;
                              void refresh(current.slug);
                              reload();
                            },
                          );
                        }}
                        className="pf-button pf-button--sm pf-button--primary"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    setComposeSeconds(Math.floor(position));
                    setComposeQuote("");
                    setComposeDraft("");
                    setComposing(true);
                  }}
                  className="pf-button pf-button--sm pf-button--primary pf-notes__add"
                >
                  + Add note at {clock(position)}
                </button>
              )}

              <NotesList
                annotations={[]}
                bookmarks={[]}
                chapters={[]}
                episodes={[{ number: current.number, title: current.title }]}
                episodeNotes={here}
                orphaned={NOTHING_ORPHANED}
                slug={current.slug}
                onPlay={(_number, seconds) => seek(seconds)}
                onRemoveAnnotation={NOTHING}
                onRemoveBookmark={NOTHING}
                onRemoveEpisodeNote={(id) => {
                  void fetch(`/book/${encodeURIComponent(current.slug)}/marks`, {
                    method: "POST",
                    headers: { "Content-Type": "application/x-www-form-urlencoded" },
                    body: new URLSearchParams({ intent: "un-episode-note", id }),
                  })
                    .then(() => {
                      void refresh(current.slug);
                      reload();
                    })
                    .catch(() => {});
                }}
                onEditEpisodeNote={(id, note) => {
                  const existing = here.find((n) => n.id === id);
                  if (existing === undefined) return;
                  void markMoment(current, existing.seconds, id, existing.quote ?? "", note).then((ok) => {
                    if (!ok) return;
                    void refresh(current.slug);
                    reload();
                  });
                }}
              />
            </>
          )}
        </div>
      </aside>
    </>
  );
}

/** What the marks endpoint gives back, as much of it as this panel uses. */
interface PlayingMarks {
  episodeNotes: EpisodeNote[];
}

const NOTHING_ORPHANED: ReadonlySet<string> = new Set<string>();
const NOTHING = () => {};

function PlayIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="currentColor">
      <path d="M8 5.5v13l11-6.5z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="currentColor">
      <path d="M7 5h3.5v14H7zm6.5 0H17v14h-3.5z" />
    </svg>
  );
}
