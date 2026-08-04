-- A book may have MORE THAN ONE slide deck, and each one belongs to a chapter.
--
-- The Listener was built around the exception. The Master and the Disciple has a
-- single book-wide deck, so `_listener_book.collect_media` looked in exactly one
-- hardcoded folder — `slide-decks/_pages/book/` — and `media_asset.key` was flat:
-- `<slug>/deck/page-NN.jpg`. But the pipeline that MAKES decks has been
-- per-chapter by DEFAULT the whole time (`_content_profile.slide_deck_mode`
-- defaults to "per-chapter"; "book" is the override), and it already rasterises
-- into `slide-decks/_pages/<ch>/`. Ayyuha al-Walad has four chapter decks, which
-- is the ordinary case, not a special one.
--
-- Two decks could not simply be pointed at the old shape: `key` is the PRIMARY
-- KEY, so ch01's `page-01.jpg` and ch02's `page-01.jpg` produced the SAME key and
-- one silently overwrote the other. The key now carries the deck
-- (`<slug>/deck/<ch>/page-NN.jpg`), which is what makes four decks storable at
-- all; these columns are what makes them readable as four rather than as one
-- pile of pages sorted by filename.
--
-- WHY A PLAIN ADD COLUMN IS ENOUGH. `kind` stays 'deck-page', so the CHECK
-- constraint on `media_asset` is untouched and none of the twelve-step table
-- rebuild that 0008 performs is needed here. SQLite adds a nullable column
-- without rewriting the table.
--
-- BOTH COLUMNS ARE NULLABLE, and that is the migration strategy: every row
-- written before this point keeps NULL, and `deckPagesOf` reads NULL as "the one
-- unnamed deck this book has". So the site renders correctly the moment the
-- migration lands and before anything is re-published — the old rows are not
-- wrong, they are simply from a world with one deck in it.
--
-- WHY A TITLE IS STORED RATHER THAN JOINED. The first draft of this migration
-- carried an `anchor_key` instead, on the reasoning that a deck's name is just
-- its chapter's title and `chapter.anchor_key` already reaches that. Checking the
-- data killed it: `_pages/ch01/` is numbered against the PODCAST chapter
-- segmentation (`chapters/ch01-*.txt`, four files for Ayyuha al-Walad) while
-- `chapter.anchor_key` keys the READING edition (ten chapters for the same book).
-- They are different segmentations of the same work — the third-segmentation
-- problem `read_bridge` documents — so deck-to-chapter is not derivable, and
-- deriving it anyway would have filed decks against the wrong chapters with
-- complete confidence.
--
-- So the title travels. It is not invented here either: it is read from the deck
-- SOURCE's own H1, the line the author wrote above the deck they exported.
--
-- Carries no privilege bit, like every migration since 0004: nothing here decides
-- whether anything is readable. Deck pages are gated by the SLUG, through
-- `requireUnitAccess` on the media route, and that is unchanged.

-- Which deck a page belongs to: the folder name under `slide-decks/_pages/`,
-- i.e. 'ch01'…'chNN', or the literal 'book' for a book-wide deck.
ALTER TABLE media_asset ADD COLUMN deck_id TEXT;

-- What to call this deck on screen: the H1 of its deck source, which is the name
-- the author gave it. NULL for a book-wide deck, which needs no name because it
-- is the only one — the chooser is not drawn at all for a single deck.
ALTER TABLE media_asset ADD COLUMN deck_title TEXT;

-- Decks are read one book at a time, grouped and then ordered within a group.
CREATE INDEX idx_media_asset_deck ON media_asset (slug, kind, deck_id);
