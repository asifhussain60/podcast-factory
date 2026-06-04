# Supabase — salty-lamps-notes

Full database record for the notes and brainstorm board backing the Salty Lamps proposal site.

**Last reconciled:** 2026-05-31

---

## TL;DR

The Salty Lamps proposal site (https://salty-lamps-proposal.pages.dev) has a slide-in notes panel. Every note and post-it is persisted here. To view saved notes: open the Table Editor at the dashboard URL below.

---

## Project details

| Field | Value |
|---|---|
| **Project name** | asifhussain60's Project |
| **Project ID** | `babguqugvxagijmnsgsj` |
| **Project URL** | `https://babguqugvxagijmnsgsj.supabase.co` |
| **REST API base** | `https://babguqugvxagijmnsgsj.supabase.co/rest/v1/` |
| **Region** | East US (North Virginia) — `us-east-1` |
| **Compute** | NANO (free tier) |
| **Plan** | Free — 500 MB DB, 50k monthly active users, 5 GB bandwidth |
| **Dashboard** | https://supabase.com/dashboard/project/babguqugvxagijmnsgsj |

---

## API credentials

| Key type | Value | Usage |
|---|---|---|
| **Publishable key** (anon) | `sb_publishable_8rpQsGmtH11e1UM2FEuWtg_7U6qXylD` | Browser-safe. Used in the deployed React app. |
| **Secret key** | `sb_secret_rxTeL…` (masked) | Server-side only. Never expose in client code. |

The publishable key is safe to store in `.env.local` and in client-side bundles because Row Level Security (RLS) is enabled on all tables — unauthenticated access is controlled by the policies defined below.

---

## Tables

### `text_notes`

Stores the freeform proposal notes from the Notes tab. Single row, keyed `'default'`.

```sql
create table text_notes (
  id text primary key default 'default',
  content text default '',
  updated_at timestamptz default now()
);
```

| Column | Type | Notes |
|---|---|---|
| `id` | text (PK) | Always `'default'` — one row per site session |
| `content` | text | Full freeform notes content |
| `updated_at` | timestamptz | Auto-set; not currently used by app but available for audit |

### `board_notes`

Stores each post-it on the brainstorm board. One row per note.

```sql
create table board_notes (
  id bigint primary key,
  x float default 0,
  y float default 0,
  width float default 200,
  height float default 160,
  color text default 'yellow',
  content text default '',
  z int default 1,
  updated_at timestamptz default now()
);
```

| Column | Type | Notes |
|---|---|---|
| `id` | bigint (PK) | `Date.now()` at creation — unique per note |
| `x`, `y` | float | Canvas position in pixels |
| `width`, `height` | float | Note dimensions in pixels |
| `color` | text | One of: `yellow`, `pink`, `blue`, `green`, `orange`, `purple` |
| `content` | text | Note text body |
| `z` | int | Z-index stacking order |
| `updated_at` | timestamptz | Auto-set on insert |

---

## Row Level Security (RLS)

RLS is enabled on both tables. The current policy is open read/write for the publishable (anon) key — appropriate for a single-user proposal tool with no auth requirement.

```sql
alter table text_notes enable row level security;
alter table board_notes enable row level security;

create policy "allow all" on text_notes for all using (true) with check (true);
create policy "allow all" on board_notes for all using (true) with check (true);
```

**If multi-user access is ever needed:** replace the `using (true)` policies with auth-scoped ones tied to Supabase Auth user IDs.

---

## How the app uses this database

The notes panel in the proposal site (`src/components/NotesPanel.jsx`) follows this pattern:

1. **On panel open (first time):** fetch both tables from Supabase; hydrate state; write to localStorage as cache.
2. **On every change:** update React state + localStorage immediately (instant UX). After a **1.5-second debounce**, upsert/replace in Supabase.
3. **Sync indicator:** header shows "Saving…" (orange dot) during the debounce window, "Saved" (green dot) on success, "Offline" (red dot) on error.
4. **Board save strategy:** delete all rows then re-insert on every board change (simple, avoids partial-update edge cases at this scale).

The Supabase client is initialised in `src/lib/supabase.js`:

```js
import { createClient } from '@supabase/supabase-js'
const url = import.meta.env.VITE_SUPABASE_URL
const key = import.meta.env.VITE_SUPABASE_ANON_KEY
export const supabase = url && key ? createClient(url, key) : null
```

Both env vars are baked into the JS bundle at Vite build time from `.env.local`.

---

## Bootstrap on a new machine

The `.env.local` file must exist at `salty-lamps-proposal/.env.local` before building:

```
VITE_SUPABASE_URL=https://babguqugvxagijmnsgsj.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_8rpQsGmtH11e1UM2FEuWtg_7U6qXylD
```

Then build and deploy normally:

```bash
cd "Salty Lamps/salty-lamps-proposal"
npm run build
npx wrangler pages deploy dist --project-name salty-lamps-proposal --branch master --commit-dirty=true
```

---

## Viewing saved notes

Open the Supabase Table Editor:

- **Text notes:** https://supabase.com/dashboard/project/babguqugvxagijmnsgsj/editor (select `text_notes`)
- **Board notes:** https://supabase.com/dashboard/project/babguqugvxagijmnsgsj/editor (select `board_notes`)

Or query directly via SQL Editor:

```sql
-- View all text notes
select * from text_notes;

-- View all board post-its, newest first
select id, color, content, x, y from board_notes order by id desc;

-- Count notes by colour
select color, count(*) from board_notes group by color order by count desc;
```

---

## Upcoming maintenance notice

Supabase shared pooler maintenance is scheduled for us-east-1 on **03 Jun 2026, 09:00**.  
No action required — the free tier uses direct connections, not the pooler.

---

## Quick-reference URLs

| Surface | URL |
|---|---|
| Project dashboard | https://supabase.com/dashboard/project/babguqugvxagijmnsgsj |
| Table Editor | https://supabase.com/dashboard/project/babguqugvxagijmnsgsj/editor |
| SQL Editor | https://supabase.com/dashboard/project/babguqugvxagijmnsgsj/sql |
| API Keys (Settings) | https://supabase.com/dashboard/project/babguqugvxagijmnsgsj/settings/api-keys |
| REST API docs | https://supabase.com/dashboard/project/babguqugvxagijmnsgsj/api |
| Supabase JS docs | https://supabase.com/docs/reference/javascript |

---

## See also

- [`cloudflare/salty-lamps-proposal.md`](../cloudflare/salty-lamps-proposal.md) — the site that writes to this database.
- [`supabase/README.md`](README.md) — index of all Supabase projects.
