-- Episodes grouped into SESSIONS.
--
-- "Session" rather than "Season" deliberately: the author's own folder names say
-- Session, and the hosts are likely to say it inside the recordings. A page
-- headed "Season 3" over an episode that opens with "welcome to session three"
-- is the site arguing with its own audio.
--
-- The table is `book_session`, NOT `session` — Better Auth already owns a table
-- by that name for sign-in sessions (migration 0001), and the first attempt at
-- this failed on `table session already exists`. That collision is worth the
-- ugly prefix: two things called `session` in one database, one holding a
-- listener's identity and one holding a run of episodes, is a mistake waiting
-- for whoever writes the next query.
--
-- The grouping is not derived from anything. It comes from folder names a human
-- wrote — `m4a/Episodes/Session 2 — Spiritual Symbols: The Architecture of
-- Creation/` — which carry both the number and the title. Nothing infers a
-- session from episode count, runtime or chapter boundaries; a book whose
-- episodes were never grouped simply has none, and its episodes list flat.

CREATE TABLE book_session (
  slug   TEXT NOT NULL,
  number INTEGER NOT NULL,
  title  TEXT NOT NULL,
  PRIMARY KEY (slug, number)
);

-- Nullable, and it must stay nullable. An episode outside any session is a
-- normal episode, not a broken one — that is every book that has a podcast and
-- no grouping, which is most of them.
ALTER TABLE episode ADD COLUMN session_number INTEGER;

CREATE INDEX idx_episode_session ON episode (slug, session_number, number);
