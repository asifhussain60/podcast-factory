/**
 * store.test.ts — the YAML line-patcher writes to LIVE book files, so every
 * guarantee it makes is pinned here: comments survive, unknown keys survive,
 * block scalars and lists survive, and nesting is written into the right block.
 *
 * The fixtures are the real shapes these files take (a commented series-config,
 * a meta.yml with a nested block, a list and a literal block scalar), because
 * the failure this guards against is exactly a file that looked simpler in a
 * test than it does on disk.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import yaml from "js-yaml";
import { patchYamlLines } from "./store";

/** Just enough of the fixtures' shape to assert on; `any` would hide a typo. */
interface MetaDoc {
  // Present in the fixture, so the assertions can read them without a guard.
  study_track: string;
  series: { enable_book_branch: boolean; enable_slide_decks?: boolean };
  pipeline: { current_phase: string };
  completed_episodes: string[];
  provenance: { note: string };
  // Added by a test rather than present to begin with.
  doctrinal_context?: { school?: string };
}
interface SeriesDoc {
  narrative_frame?: string;
  audience_profile?: string;
  title?: string;
  book_voice?: string;
  length_tier?: string;
  c?: number;
}
const meta = (t: string) => yaml.load(t) as MetaDoc;
const series = (t: string) => yaml.load(t) as SeriesDoc;

const META = `slug: kitab-al-riyad
title: Kitab al-Riyad
study_track: reality
short_name: kar

series:
  enable_book_branch: true

pipeline:
  current_phase: done

completed_episodes:
  - EP01-the-first
  - EP02-the-second

provenance:
  note: |
    A literal block scalar that must survive untouched,
    including this second line.
  ship_commits:
    - 8a5c76a  # a comment on a list item
`;

const SERIES = `slug: kitab-al-riyad
content_profile: islamic_scholarly

# Faithful reading edition — this comment must survive.
book_augmentation: none
book_voice: faithful

# Narrative frame — a property of the SOURCE, never inferred silently.
narrative_frame: first_person_author
enable_video: false
`;

test("updates a top-level key and changes nothing else", () => {
  const out = patchYamlLines(META, "study_track", "theology");
  const before = yaml.load(META) as Record<string, unknown>;
  const after = yaml.load(out) as Record<string, unknown>;
  assert.equal(after.study_track, "theology");
  assert.deepEqual(
    { ...after, study_track: null },
    { ...before, study_track: null },
  );
});

test("updates a nested key without disturbing its siblings or neighbours", () => {
  const out = patchYamlLines(META, "series.enable_book_branch", "false");
  const d = meta(out);
  assert.equal(d.series.enable_book_branch, false);
  assert.equal(d.pipeline.current_phase, "done");
  assert.equal(d.completed_episodes.length, 2);
  assert.match(d.provenance.note, /second line/);
});

test("adds a nested key inside an existing parent block", () => {
  const out = patchYamlLines(META, "series.enable_slide_decks", "false");
  const d = meta(out);
  assert.equal(d.series.enable_slide_decks, false);
  assert.equal(d.series.enable_book_branch, true, "sibling survives");
  assert.equal(d.pipeline.current_phase, "done", "next block untouched");
});

test("creates the parent block when it is absent", () => {
  const out = patchYamlLines(META, "doctrinal_context.school", "Ismaili");
  const d = meta(out);
  assert.equal(d.doctrinal_context?.school, "Ismaili");
});

test("keeps the comments around a key it rewrites", () => {
  const out = patchYamlLines(SERIES, "narrative_frame", "transmitted_report");
  assert.equal(series(out).narrative_frame, "transmitted_report");
  assert.match(out, /a property of the SOURCE/);
  assert.match(out, /Faithful reading edition/);
});

test("adds an absent top-level key and loses no existing one", () => {
  const before = Object.keys(yaml.load(SERIES) as object);
  const out = patchYamlLines(SERIES, "audience_profile", "academic");
  const d = yaml.load(out) as Record<string, unknown>;
  assert.equal(d.audience_profile, "academic");
  for (const k of before) assert.ok(k in d, `${k} survived`);
});

test("quotes a value YAML would otherwise mis-read", () => {
  const out = patchYamlLines(SERIES, "title", "Kitab: al-Riyad #2");
  assert.equal(series(out).title, "Kitab: al-Riyad #2");
});

test("sequential patches are independent", () => {
  const before = Object.keys(yaml.load(SERIES) as object);
  let out = SERIES;
  for (const [k, v] of [
    ["book_voice", "author_companion"],
    ["enable_video", "true"],
    ["length_tier", "longer"],
  ] as [string, string][]) {
    out = patchYamlLines(out, k, v);
  }
  const d = yaml.load(out) as Record<string, unknown>;
  for (const k of before) assert.ok(k in d, `${k} survived`);
  assert.equal(d.book_voice, "author_companion");
  assert.equal(d.length_tier, "longer");
});

test("a file that ended with a newline still ends with one", () => {
  for (const path of [
    "audience_profile", // appended top-level
    "book_voice", // rewritten in place
    "series.enable_slide_decks", // appended nested
    "doctrinal_context.school", // whole new block
  ]) {
    const out = patchYamlLines(META, path, "x");
    assert.ok(out.endsWith("\n"), `${path} kept the trailing newline`);
    assert.ok(!out.endsWith("\n\n\n"), `${path} did not pile up blank lines`);
  }
});

test("a file with no trailing newline does not gain one", () => {
  const out = patchYamlLines("a: 1\nb: 2", "c", "3");
  assert.ok(!out.endsWith("\n"));
  assert.equal(series(out).c, 3);
});
