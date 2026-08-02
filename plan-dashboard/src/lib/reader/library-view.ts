/**
 * library-view.ts — view-model builder for the Studio book index page
 * (src/pages/studio/[slug]/index.astro). Extracted from that page's 285-line
 * frontmatter (R2 of the clean-code hardening plan), following the
 * studio-pipeline.ts pattern: pure functions + typed shapes + one thin async
 * loader. The page destructures buildStudioIndexView()'s result under the
 * same names its template always used — zero template change.
 */

import { readFile, stat } from "node:fs/promises";
import { basename, resolve as resolvePath } from "node:path";

import type { Track } from "../../components/studio/AudioPlayer";
import type { FactProp } from "../../components/studio/EditableBookFacts";
import type {
  HaltArtifactLink,
  SavedDecision,
} from "../../components/studio/HaltReview";
import { formatBytes, formatModified, type DetailView } from "../library";
import {
  haltForPhase,
  resolveArtifacts,
  type HaltReviews,
} from "../studio/halts";
import { discoverSessions } from "./chapters";

type LibFile = DetailView["chapters"][number];

export interface SessionGroup {
  index: number;
  title: string;
  files: LibFile[];
}

export interface RenderGroup {
  label: string | null;
  count: number;
  files: LibFile[];
}

export interface MetaFileLink {
  kind: "file" | "dir" | "missing";
  name: string;
  icon: string;
  href: string | null;
}

// Editable "About this book" facts. Safe display fields are patchable; slug is
// structural identity (read-only here — rename is a separate guarded flow);
// source-path fields render as file links.
const EDITABLE_TEXT: Record<string, { max: number; required?: boolean }> = {
  title: { max: 200, required: true },
  short_name: { max: 60, required: true },
  author: { max: 120 },
  original_title: { max: 200 },
};
const CATEGORY_OPTIONS = [
  "books",
  "lectures",
  "articles",
  "documents",
  "interviews",
  "letters",
  "asbaaq",
];

// Source-path meta fields render as icon'd file links instead of raw relative
// paths. The href hits /api/library/source, which re-reads the path from
// meta.yml server-side (field-name only — no client paths).
const SOURCE_FIELDS = new Set(["source_pdf", "source_audio"]);

/** Humanize `01-Why_Knowledge_Is_Theft.m4a` / `final-review-report.md`. */
export function humanizeFile(name: string): string {
  const base = name.replace(/\.[a-z0-9]+$/i, "");
  const m = base.match(/^(\d+)[-_](.+)$/);
  const body = (m ? m[2] : base).replace(/[-_]+/g, " ").trim();
  const cased = body.charAt(0).toUpperCase() + body.slice(1);
  return m ? `${m[1]} — ${cased}` : cased;
}

function fileEpisodeNumber(name: string): number | null {
  const m = name.match(/^(?:EP|ch)(\d+)/i);
  return m ? Number(m[1]) : null;
}

export interface StudioIndexView {
  fileViewHref: (relPath: string) => string;
  episodeGroups: RenderGroup[];
  hasSessions: boolean;
  humanizeFile: typeof humanizeFile;
  metaFileLinks: Map<string, MetaFileLink>;
  bookFacts: FactProp[];
  audioTracks: Track[];
  pipelineTone: "fail" | "warn" | "pass" | null;
  activeHaltDef: ReturnType<typeof haltForPhase>;
  haltArtifacts: HaltArtifactLink[];
  haltSaved: SavedDecision | null;
  haltHalted: boolean;
  mediaCount: number;
  tabs: { id: string; label: string; count: number | null }[];
  firstChapterHref: string;
}

export async function buildStudioIndexView(
  detail: DetailView,
  slugStr: string,
): Promise<StudioIndexView> {
  const {
    summary,
    meta,
    chapters,
    episodes,
    slideDecks,
    audio,
    audits,
    sourceFiles,
    state,
  } = detail;

  // The "Review Arabic" entry point that used to be computed here (gated on the
  // book carrying an Arabic-script glossary) was removed on 2026-07-29 with the
  // Composer's Arabic drawer surface: it linked to /studio/<slug>/arabic-review,
  // a page retired in 2026-07 that redirects to the Composer, and the panel it
  // was pointing at no longer exists anywhere.

  function fileViewHref(relPath: string): string {
    // Text artifacts (episodes, source, audits) render in the in-site styled
    // reader; binary/audio still stream via the file API.
    const ext = relPath.split(".").pop()?.toLowerCase() ?? "";
    if (ext === "md" || ext === "txt") {
      return `/studio/${encodeURIComponent(slugStr)}/view?path=${encodeURIComponent(relPath)}`;
    }
    return `/api/library/file?slug=${encodeURIComponent(slugStr)}&path=${encodeURIComponent(relPath)}`;
  }

  // Session grouping (presence-gated): sessioned books render Binders and
  // Episodes inside collapsible Session groups; flat books render as before.
  const sessions = await discoverSessions(summary.ref.dir);
  const epToSessionIndex = new Map<number, number>();
  for (const s of sessions)
    for (const n of s.episodeNumbers) epToSessionIndex.set(n, s.index);

  function groupBySession(
    files: LibFile[],
  ): { groups: SessionGroup[]; ungrouped: LibFile[] } | null {
    if (sessions.length === 0) return null;
    const groups: SessionGroup[] = sessions.map((s) => ({
      index: s.index,
      title: s.title,
      files: [],
    }));
    const ungrouped: LibFile[] = [];
    for (const f of files) {
      const ep = fileEpisodeNumber(f.name);
      const idx = ep === null ? undefined : epToSessionIndex.get(ep);
      const g =
        idx === undefined ? undefined : groups.find((x) => x.index === idx);
      if (g) g.files.push(f);
      else ungrouped.push(f);
    }
    return { groups: groups.filter((g) => g.files.length > 0), ungrouped };
  }

  function renderGroups(files: LibFile[]): RenderGroup[] {
    const grouped = groupBySession(files);
    if (!grouped) return [{ label: null, count: files.length, files }];
    const out: RenderGroup[] = grouped.groups.map((g) => ({
      label: `Session ${g.index} — ${g.title}`,
      count: g.files.length,
      files: g.files,
    }));
    if (grouped.ungrouped.length > 0) {
      out.push({
        label: out.length > 0 ? "Ungrouped" : null,
        count: grouped.ungrouped.length,
        files: grouped.ungrouped,
      });
    }
    return out;
  }

  const episodeGroups = renderGroups(episodes);
  const hasSessions = sessions.length > 0;

  const metaFileLinks = new Map<string, MetaFileLink>();
  for (const [k, v] of Object.entries(meta)) {
    if (!SOURCE_FIELDS.has(k)) continue;
    const abs = resolvePath(summary.ref.dir, v);
    const name = basename(abs);
    let kind: MetaFileLink["kind"] = "missing";
    try {
      kind = (await stat(abs)).isDirectory() ? "dir" : "file";
    } catch {
      /* leave missing */
    }
    const ext = name.split(".").pop()?.toLowerCase() ?? "";
    const icon =
      kind === "dir"
        ? "fa-solid fa-folder"
        : ext === "pdf"
          ? "fa-solid fa-file-pdf"
          : ["mp3", "m4a", "wav"].includes(ext)
            ? "fa-solid fa-file-audio"
            : "fa-regular fa-file";
    metaFileLinks.set(k, {
      kind,
      name,
      icon,
      href:
        kind === "file"
          ? `/api/library/source?slug=${encodeURIComponent(slugStr)}&field=${encodeURIComponent(k)}`
          : null,
    });
  }

  const bookFacts: FactProp[] = Object.entries(meta)
    .slice(0, 16)
    .map(([k, v]) => {
      const link = metaFileLinks.get(k);
      const base: FactProp = {
        key: k,
        label: k.replace(/_/g, " "),
        value: v,
        editable: false,
      };
      if (link) return { ...base, link };
      if (k === "slug") return { ...base, structural: true };
      if (k === "category")
        return {
          ...base,
          editable: true,
          control: "select",
          options: CATEGORY_OPTIONS,
        };
      const t = EDITABLE_TEXT[k];
      if (t)
        return {
          ...base,
          editable: true,
          control: "text",
          maxLen: t.max,
          required: t.required,
        };
      return base;
    });

  const audioTracks: Track[] = audio.map((f) => ({
    label: humanizeFile(f.name),
    src: `/api/library/file?slug=${encodeURIComponent(slugStr)}&path=${encodeURIComponent(f.relPath)}`,
    meta: `${formatBytes(f.bytes)} · ${formatModified(f.modified)}`,
  }));

  const pipelineTone = !state.exists
    ? null
    : state.phaseStatus === "failed"
      ? "fail"
      : state.phaseStatus === "running" || state.phaseStatus === "halted"
        ? "warn"
        : "pass";

  // Per-halt review cockpit: if the book's current phase is a human-review halt
  // (halts.ts mirrors _progress.py), surface that halt's artifacts + a decision
  // control at the top of the Overview. Absent when the book isn't at a halt.
  const activeHaltDef = state.exists ? haltForPhase(state.phase) : null;
  let haltArtifacts: HaltArtifactLink[] = [];
  let haltSaved: SavedDecision | null = null;
  if (activeHaltDef) {
    haltArtifacts = resolveArtifacts(summary.ref.dir, activeHaltDef).map(
      (a) => ({
        label: a.label,
        href: fileViewHref(a.relPath),
        exists: a.exists,
      }),
    );
    try {
      const reviews = JSON.parse(
        await readFile(`${summary.ref.dir}/_system/halt-reviews.json`, "utf-8"),
      ) as HaltReviews;
      haltSaved = reviews[activeHaltDef.id] ?? null;
    } catch {
      /* no decisions recorded yet */
    }
  }
  const haltHalted =
    activeHaltDef !== null &&
    (state.phaseStatus === "halted" || state.phaseStatus === "pending");

  const mediaCount = audio.length + slideDecks.length;
  const tabs = [
    { id: "overview", label: "Overview", count: null },
    { id: "chapters", label: "Chapters", count: chapters.length },
    { id: "episodes", label: "Episodes", count: episodes.length },
    { id: "media", label: "Media", count: mediaCount },
    { id: "audits", label: "Audits", count: audits.length },
    { id: "source", label: "Source", count: sourceFiles.length },
  ];

  // The Chapters tab jumps straight into the editor on the first chapter
  // (the grid view was removed). chapters[] is filename-sorted, so [0] is ch01a.
  const firstChapterId = (chapters[0]?.name ?? "").replace(/\.(txt|md)$/i, "");
  const firstChapterHref = firstChapterId
    ? `/studio/${slugStr}/edit?ch=${firstChapterId}`
    : `/studio/${slugStr}/edit`;

  return {
    fileViewHref,
    episodeGroups,
    hasSessions,
    humanizeFile,
    metaFileLinks,
    bookFacts,
    audioTracks,
    pipelineTone,
    activeHaltDef,
    haltArtifacts,
    haltSaved,
    haltHalted,
    mediaCount,
    tabs,
    firstChapterHref,
  };
}
