-- 010_atom_topic_tags.sql — Tag/topic index for knowledge atoms.
-- Enables faceted browsing and augmenter scoping by topic.
-- Depends on: 001_atoms.sql.

CREATE TABLE IF NOT EXISTS atom_topic_tags (
    atom_id   TEXT NOT NULL REFERENCES atoms (id) ON DELETE CASCADE,
    tag       TEXT NOT NULL,   -- e.g. "tawhid", "eschatology", "imama", "ethics"
    PRIMARY KEY (atom_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_atom_topic_tags_tag     ON atom_topic_tags (tag);
CREATE INDEX IF NOT EXISTS idx_atom_topic_tags_atom_id ON atom_topic_tags (atom_id);
