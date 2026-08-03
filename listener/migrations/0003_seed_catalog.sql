-- Seed the catalog with the content units that actually exist on disk today.
--
-- This is deliberately a seed rather than a sync endpoint. The alternative was a
-- script POSTing a manifest under a bearer token — but `open_to_all` and `status`
-- are privilege bits, and a token that can write the content_unit row is a token
-- that can grant everyone access to everything. That token would live in a
-- .dev.vars file and travel in a script. A seed needs no secret at all.
--
-- Phase 3's publish pipeline becomes the ongoing writer, and when it does it
-- names its columns explicitly — never open_to_all, never status.
--
-- Titles are plain ASCII romanization per the house rule (so "Kitab al-Riyad",
-- not the diacritic form meta.yml carries). Statuses mirror
-- _system/orchestrator-state.json as of 2026-08-03; two units have no state file
-- at all and are seeded 'draft', which is the safe direction — an unpublished
-- unit is unreadable regardless of who holds a grant.

-- Standalone books -----------------------------------------------------------
INSERT INTO content_unit (slug, bucket, title, kind, work_slug, sort_order, status) VALUES
  ('ayyuhal-walad',             'Islamic',   'Ayyuha al-Walad',                                'book', NULL, 10, 'published'),
  ('the-master-and-the-disciple','Islamic',  'The Master and the Disciple',                    'book', NULL, 20, 'published'),
  ('degrees-of-excellence',     'Islamic',   'Degrees of Excellence',                          'book', NULL, 30, 'draft'),
  ('kitab-al-riyad',            'Islamic',   'Kitab al-Riyad',                                 'book', NULL, 40, 'draft'),
  ('kunooz-al-hikmah',          'Islamic',   'Kunooz al-Hikmah',                               'book', NULL, 50, 'draft'),
  ('mukhtasar-ul-asar-1',       'Islamic',   'Mukhtasar ul-Asar 1',                            'book', NULL, 60, 'draft'),
  ('mukhtasar-ul-asar-2',       'Islamic',   'Mukhtasar ul-Asar 2',                            'book', NULL, 70, 'draft'),
  ('healthequity',              'Guides',    'HealthEquity: Health Benefits That Change Lives','book', NULL, 80, 'draft'),
  ('claude-code-training',      'Technical', 'Claude Code Training',                           'book', NULL, 90, 'draft');

-- Multi-volume works ---------------------------------------------------------
-- The parent row is what makes a work grantable as a whole: granting
-- 'asaas-al-taveel' covers every volume, including ones added later, without
-- revisiting anybody's permissions. A work parent is never itself readable —
-- it has no chapters — so its own status stays 'draft'.
INSERT INTO content_unit (slug, bucket, title, kind, work_slug, sort_order, status) VALUES
  ('asaas-al-taveel',        'Islamic', 'Asas al-Taweel',       'work', NULL, 100, 'draft'),
  ('al-anwaar-al-lateefah',  'Islamic', 'Al-Anwaar al-Lateefah','work', NULL, 200, 'draft');

INSERT INTO content_unit (slug, bucket, title, kind, work_slug, sort_order, status) VALUES
  ('asaas-al-taveel-vol-01', 'Islamic', 'Volume 1: Adam',                          'book', 'asaas-al-taveel', 101, 'draft'),
  ('asaas-al-taveel-vol-02', 'Islamic', 'Volume 2: Nuh',                           'book', 'asaas-al-taveel', 102, 'draft'),
  ('asaas-al-taveel-vol-03', 'Islamic', 'Volume 3: Ibrahim',                       'book', 'asaas-al-taveel', 103, 'draft'),
  ('asaas-al-taveel-vol-04', 'Islamic', 'Volume 4: Musa',                          'book', 'asaas-al-taveel', 104, 'draft'),
  ('asaas-al-taveel-vol-05', 'Islamic', 'Volume 5: Isa',                           'book', 'asaas-al-taveel', 105, 'draft'),
  ('asaas-al-taveel-vol-06', 'Islamic', 'Volume 6: Muhammad and the Awaited Qaim', 'book', 'asaas-al-taveel', 106, 'draft');

INSERT INTO content_unit (slug, bucket, title, kind, work_slug, sort_order, status) VALUES
  ('al-anwaar-al-lateefah-vol-01', 'Islamic', 'Volume 1: The Oneness (Tawheed)',                'book', 'al-anwaar-al-lateefah', 201, 'draft'),
  ('al-anwaar-al-lateefah-vol-02', 'Islamic', 'Volume 2: The Origin (Mabda)',                   'book', 'al-anwaar-al-lateefah', 202, 'draft'),
  ('al-anwaar-al-lateefah-vol-03', 'Islamic', 'Volume 3: The Hidden Hierarchy',                 'book', 'al-anwaar-al-lateefah', 203, 'draft'),
  ('al-anwaar-al-lateefah-vol-04', 'Islamic', 'Volume 4: The Sacred Line',                      'book', 'al-anwaar-al-lateefah', 204, 'draft'),
  ('al-anwaar-al-lateefah-vol-05', 'Islamic', 'Volume 5: The Two Paths and the Resurrection',   'book', 'al-anwaar-al-lateefah', 205, 'draft'),
  ('al-anwaar-al-lateefah-vol-06', 'Islamic', 'Volume 6: Retribution and the Dawn',             'book', 'al-anwaar-al-lateefah', 206, 'draft');

-- The admin's own invite -----------------------------------------------------
-- Without this the admin cannot get past the invite gate, which sits ABOVE the
-- admin gate, and there would be no way to invite anybody — the app would ship
-- locked with no key. Must match ADMIN_EMAIL in wrangler.jsonc, in the form
-- normalizeEmail() produces; a test asserts the pairing.
INSERT INTO invite (email, email_raw, invited_by, invited_at, note) VALUES
  ('asifhussain60@gmail.com', 'asifhussain60@gmail.com', 'seed', '2026-08-03T00:00:00Z',
   'The administrator. Seeded so the app is not shipped locked with no key.');

-- And a whole-library grant for the same person.
--
-- Note what this is NOT: there is no admin bypass inside the resolver. Admin
-- governs the /admin screens only; reading content follows exactly the same rule
-- for everyone, which means there is ONE path to audit instead of two. The
-- consequence is that without this row the owner signs in to an empty library
-- and the app looks broken. So the fix is an ordinary grant — visible in the
-- admin UI, revocable from it, and covering volumes added later.
INSERT INTO access_grant (user_email, scope_type, scope_id, granted_by, granted_at) VALUES
  ('asifhussain60@gmail.com', 'library', '*', 'seed', '2026-08-03T00:00:00Z');
