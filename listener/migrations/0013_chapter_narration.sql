CREATE TABLE IF NOT EXISTS chapter_narration (
  slug TEXT NOT NULL,
  anchor_key TEXT NOT NULL,
  audio_key TEXT NOT NULL,
  duration_s REAL,
  source_hash TEXT NOT NULL,
  voice TEXT NOT NULL,
  cues_json TEXT NOT NULL,
  PRIMARY KEY (slug, anchor_key)
);

CREATE INDEX IF NOT EXISTS idx_chapter_narration_audio
  ON chapter_narration(audio_key);
