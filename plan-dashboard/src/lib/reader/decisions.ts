/**
 * Load the KAHSKOLE R1 + R2 taxonomy decisions YAML files and expose
 * lookups for English titles at binder / chapter / topic granularity.
 *
 * Source of truth lives at tools/content_classifier/data/:
 *   wisdom-r1-decisions.yaml — binder + chapter retitles + dedup clusters
 *   wisdom-r2-decisions.yaml — topic retitles (currently partial: 9 of 19 binders)
 *
 * Each lookup returns the proposed English title or `undefined` if not
 * yet retitled (Round 2 is still partial for ~1,102 topics).
 */
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import yaml from 'js-yaml';
import { getRepoRoot } from '../content-paths';

interface BinderRetitle {
  binder_id: number;
  source: string;
  en_title: string;
}

interface ChapterRetitle {
  binder_id: number;
  chapter_id: number;
  source: string;
  en_title: string;
  confidence: 'high' | 'medium' | 'low';
}

interface TopicRetitle {
  binder_id: number;
  chapter_id: number;
  topic_id: number;
  source: string;
  en_title: string;
  confidence: 'high' | 'medium' | 'low';
}

interface DedupCluster {
  cluster_id: string;
  kind: string;
  primary?: { binder_id: number; chapter_id: number; topic_id?: number };
  cross_refs?: Array<{ binder_id: number; chapter_id: number; topic_id?: number; action: string }>;
  topic_id?: number;
  topic_name?: string;
  chapters?: Array<{ binder_id: number; chapter_id: number }>;
}

interface R1Decisions {
  version: number;
  approved_at: string;
  binder_retitles: BinderRetitle[];
  chapter_retitles: ChapterRetitle[];
  dedup_clusters: DedupCluster[];
}

interface R2Decisions {
  version: number;
  approved_at: string | null;
  batch: string;
  covered_binders: number[];
  deferred_binders: number[];
  topic_retitles: TopicRetitle[];
}

let _cache: {
  binderByName: Map<string, BinderRetitle>;
  binderById: Map<number, BinderRetitle>;
  chapterById: Map<string, ChapterRetitle>;       // key: `${bid}:${cid}`
  topicById: Map<string, TopicRetitle>;           // key: `${bid}:${cid}:${tid}`
  dedupClusters: DedupCluster[];
  coveredBinders: Set<number>;
  deferredBinders: Set<number>;
  r2BatchStatus: { batch: string; covered: number; deferred: number };
} | null = null;

export async function loadDecisions() {
  if (_cache) return _cache;
  const root = getRepoRoot();
  const r1Path = join(root, 'tools/content_classifier/data/wisdom-r1-decisions.yaml');
  const r2Path = join(root, 'tools/content_classifier/data/wisdom-r2-decisions.yaml');

  const [r1Text, r2Text] = await Promise.all([
    readFile(r1Path, 'utf-8').catch(() => null),
    readFile(r2Path, 'utf-8').catch(() => null),
  ]);

  const r1 = r1Text ? (yaml.load(r1Text) as R1Decisions) : null;
  const r2 = r2Text ? (yaml.load(r2Text) as R2Decisions) : null;

  const binderByName = new Map<string, BinderRetitle>();
  const binderById = new Map<number, BinderRetitle>();
  const chapterById = new Map<string, ChapterRetitle>();
  const topicById = new Map<string, TopicRetitle>();
  const dedupClusters: DedupCluster[] = [];

  if (r1) {
    for (const b of r1.binder_retitles ?? []) {
      binderByName.set(b.source, b);
      binderById.set(b.binder_id, b);
    }
    for (const c of r1.chapter_retitles ?? []) {
      chapterById.set(`${c.binder_id}:${c.chapter_id}`, c);
    }
    for (const cluster of r1.dedup_clusters ?? []) {
      dedupClusters.push(cluster);
    }
  }
  if (r2) {
    for (const t of r2.topic_retitles ?? []) {
      topicById.set(`${t.binder_id}:${t.chapter_id}:${t.topic_id}`, t);
    }
  }

  const r2BatchStatus = {
    batch: r2?.batch ?? 'not-loaded',
    covered: r2?.covered_binders?.length ?? 0,
    deferred: r2?.deferred_binders?.length ?? 0,
  };

  _cache = {
    binderByName,
    binderById,
    chapterById,
    topicById,
    dedupClusters,
    coveredBinders: new Set(r2?.covered_binders ?? []),
    deferredBinders: new Set(r2?.deferred_binders ?? []),
    r2BatchStatus,
  };
  return _cache;
}

export async function getBinderEnglish(sourceName: string): Promise<string | undefined> {
  const d = await loadDecisions();
  return d.binderByName.get(sourceName)?.en_title;
}

export async function getBinderEnglishById(binderId: number): Promise<string | undefined> {
  const d = await loadDecisions();
  return d.binderById.get(binderId)?.en_title;
}

export async function getChapterEnglish(
  binderId: number,
  chapterId: number,
): Promise<ChapterRetitle | undefined> {
  const d = await loadDecisions();
  return d.chapterById.get(`${binderId}:${chapterId}`);
}

export async function getTopicEnglish(
  binderId: number,
  chapterId: number,
  topicId: number,
): Promise<TopicRetitle | undefined> {
  const d = await loadDecisions();
  return d.topicById.get(`${binderId}:${chapterId}:${topicId}`);
}

export async function isBinderTopicRetitled(binderId: number): Promise<boolean> {
  const d = await loadDecisions();
  return d.coveredBinders.has(binderId);
}

export async function getDedupClustersForChapter(
  binderId: number,
  chapterId: number,
): Promise<DedupCluster[]> {
  const d = await loadDecisions();
  return d.dedupClusters.filter((c) => {
    if (c.primary?.binder_id === binderId && c.primary?.chapter_id === chapterId) return true;
    if (c.cross_refs?.some((r) => r.binder_id === binderId && r.chapter_id === chapterId)) return true;
    if (c.chapters?.some((ch) => ch.binder_id === binderId && ch.chapter_id === chapterId)) return true;
    return false;
  });
}

export async function getR2Status() {
  const d = await loadDecisions();
  return d.r2BatchStatus;
}
