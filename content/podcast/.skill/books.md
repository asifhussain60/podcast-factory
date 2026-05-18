# Podcast Library Index

One row per book under `content/podcast/library/<category>/<book-slug>/`. Each
row points to the book's own registry. The per-book registry is the
authoritative list of episodes for that book; this file is just the index.

| Category | Book Slug | Title | Registry |
|---|---|---|---|
| books | ayyuhal-walad | Ayyuhal Walad (Imam al-Ghazali) | [registry](../library/books/ayyuhal-walad/_system/registry.md) |
| books | the-master-and-the-disciple | The Master and the Disciple | (registry pending — Phase 0 not yet run) |

## Schema (per-book registry)

Every `library/<category>/<book-slug>/_system/registry.md` is a markdown
table with these columns (extra columns tolerated):

- `EP#` — strictly increasing, unique positive integer
- `Title` — episode title; should match the chapter's concise title
- `Slug` — kebab-case, ≤40 chars, unique within the book
- `Source Type` — one of `book-chapter`, `article`, `document`, `lecture`, `interview`, `letter`
- `Status` — one of `draft`, `challenger-pending`, `ready`, `generated`, `archived`
- `Date Started`, `NotebookLM URL` — optional metadata
