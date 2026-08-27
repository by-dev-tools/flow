#!/usr/bin/env node
// Failure-pattern memory corpus health check.
// See ${CLAUDE_PLUGIN_ROOT}/docs/workflow.md § "Continuous improvement"
// for the model.
//
// Usage:
//   node ${CLAUDE_PLUGIN_ROOT}/tools/memory/check.mjs                — print summary
//   node ${CLAUDE_PLUGIN_ROOT}/tools/memory/check.mjs --count        — print entry count only
//   node ${CLAUDE_PLUGIN_ROOT}/tools/memory/check.mjs --list         — list entries by mtime (newest first)
//   node ${CLAUDE_PLUGIN_ROOT}/tools/memory/check.mjs --audit-due    — increment ship counter; exit 1 if audit due
//   node ${CLAUDE_PLUGIN_ROOT}/tools/memory/check.mjs --dead [--days=N]
//                                                                    — list entries with no
//                                                                      activity in N days
//                                                                      (default 60)
//
// Memory directory resolution (in priority order):
//   1. $MEMORY_DIR env var
//   2. Path read from `${CLAUDE_PLUGIN_ROOT}/tools/memory/.memory-dir`
//      (gitignored, per-checkout override; rarely needed since #3 handles
//      Conductor workspaces automatically)
//   3. Best-match directory under ~/.claude/projects/ that contains the
//      project name (handles Conductor workspaces and similar setups where
//      cwd != harness-canonical project path)
//   4. cwd-derived fallback: ~/.claude/projects/<slug-of-cwd>/memory
//
// Why the scan: the harness's auto-memory directory is keyed by the
// *original* project path (e.g. /Users/x/dev/my-project), not the
// worktree cwd (e.g. /Users/x/conductor/workspaces/my-project/branch).
// We want memory entries to land where the harness will auto-load them
// on the next session.
//
// Audit marker location: the .last-audit file lives next to this script
// (inside the plugin install dir). That means the audit counter is per
// flow-install, NOT per consumer project — if you have flow installed
// at user scope and use it across multiple projects, all of their ship
// runs contribute to the same audit counter. Acceptable for v1.1
// because the audit-pass reads memory entries (which ARE per-project)
// to surface stale/contradicting/over-fit candidates; the cadence
// across projects just means the audit runs more often. Revisit in
// v1.2 if a real audit-misalignment surfaces.

import { readdirSync, statSync, readFileSync, writeFileSync, existsSync } from 'fs';
import { join, dirname, basename, resolve } from 'path';
import { fileURLToPath } from 'url';

// Defaults; overridable per-project via flow.config.json at the cwd.
const DEFAULT_HARD_CAP = 30;
const AUDIT_INTERVAL = 5; // ship runs between audits
const DEAD_ENTRY_DAYS = 60; // no-activity threshold for --dead; matches ship/SKILL.md § 4b.vi prose

// Read flow.config.json.memoryHardCap if present + valid; else default.
// The config is consumer-owned (same trust level as package.json scripts).
function resolveHardCap() {
  const cfgPath = join(process.cwd(), 'flow.config.json');
  if (!existsSync(cfgPath)) return DEFAULT_HARD_CAP;
  try {
    const cfg = JSON.parse(readFileSync(cfgPath, 'utf-8'));
    const v = cfg.memoryHardCap;
    if (typeof v === 'number' && Number.isInteger(v) && v > 0) return v;
    return DEFAULT_HARD_CAP;
  } catch {
    return DEFAULT_HARD_CAP;
  }
}

const HARD_CAP = resolveHardCap();

// Defense-in-depth: even though this script only *reads* from memoryDir
// (writes go to a hardcoded auditMarker path), validate that any externally-
// supplied path resolves under ~/.claude/projects/. Prevents a misconfigured
// MEMORY_DIR or .memory-dir from making us list arbitrary directories.
function validateMemoryDir(p, source) {
  const home = process.env.HOME || '';
  const projectsRoot = resolve(join(home, '.claude', 'projects'));
  const resolved = resolve(p);
  if (!resolved.startsWith(projectsRoot + '/') && resolved !== projectsRoot) {
    throw new Error(
      `Memory dir from ${source} must resolve under ${projectsRoot}; got ${resolved}`,
    );
  }
  return resolved;
}

// Score a project-dir slug: prefer dev-style paths over conductor-workspace
// paths. The harness's canonical project dir is usually the original repo
// path (e.g. /Users/x/dev/repo), not the worktree path.
function scoreCandidate(slug) {
  let score = 0;
  if (slug.includes('-conductor-workspaces-')) score -= 10;
  if (slug.includes('-dev-')) score += 5;
  if (slug.includes('-Desktop-coding-')) score += 4;
  if (slug.includes('-claude-worktrees-')) score -= 5;
  return score;
}

function deriveMemoryDir() {
  if (process.env.MEMORY_DIR) {
    return validateMemoryDir(process.env.MEMORY_DIR, 'MEMORY_DIR env var');
  }

  const here = dirname(fileURLToPath(import.meta.url));
  const overrideFile = join(here, '.memory-dir');
  if (existsSync(overrideFile)) {
    const v = readFileSync(overrideFile, 'utf-8').trim();
    if (v) return validateMemoryDir(v, '.memory-dir file');
  }

  const home = process.env.HOME || '';
  const projectsRoot = join(home, '.claude', 'projects');

  // Find the canonical project dir by matching against the repo name. In a
  // Conductor workspace, cwd() looks like .../my-project/<branch> — so the
  // repo name is the parent dir. In a normal checkout, cwd() *is* the repo.
  // We try both and let the scorer pick.
  const candidatesNames = new Set();
  candidatesNames.add(basename(process.cwd()));
  candidatesNames.add(basename(dirname(process.cwd())));

  if (existsSync(projectsRoot)) {
    const matches = readdirSync(projectsRoot)
      .filter(d => [...candidatesNames].some(n => d.endsWith(`-${n}`) || d.includes(`-${n}-`)))
      .map(d => ({ slug: d, score: scoreCandidate(d), mtime: statSync(join(projectsRoot, d)).mtime }))
      .sort((a, b) => b.score - a.score || b.mtime - a.mtime);
    if (matches.length > 0) {
      return join(projectsRoot, matches[0].slug, 'memory');
    }
  }

  // Last-resort fallback: cwd-derived (creates a separate dir per worktree).
  const cwdSlug = process.cwd().replace(/\//g, '-');
  return join(projectsRoot, cwdSlug, 'memory');
}

const memoryDir = deriveMemoryDir();
// auditMarker lives next to this script (inside the plugin install dir)
// rather than in memoryDir because it counts ship-skill invocations from
// this flow install — not a memory entry, and we don't want to clutter
// the harness's auto-loaded memory directory with it. See top-of-file
// comment for the per-install vs per-project semantics.
const auditMarker = join(dirname(fileURLToPath(import.meta.url)), '.last-audit');

function listEntries() {
  if (!existsSync(memoryDir)) return [];
  return readdirSync(memoryDir)
    .filter(f => f.startsWith('feedback_') && f.endsWith('.md'))
    .map(f => ({ name: f, mtime: statSync(join(memoryDir, f)).mtime }));
}

// Pull every YYYY-MM-DD-shaped substring out of a single field's text. Entries write this
// field freehand (ship/SKILL.md § 4b.v appends a date per firing) so this is deliberately
// lenient rather than pinned to one exact separator style.
function extractDates(text) {
  const matches = text.match(/\d{4}-\d{2}-\d{2}/g) || [];
  return matches
    .map(d => new Date(d))
    .filter(d => !isNaN(d.getTime()));
}

// Grabs the content of every LINE THAT STARTS WITH a `- **Label**` bullet (not just the
// first one) — nothing pins whether a repeated firing is appended onto the existing bullet's
// line or written as its own new bullet line, so both shapes are unioned rather than assuming
// one. Anchored to the bullet marker (^\s*-\s*), not just "contains **Label**" anywhere in the
// line: an unanchored match would also fire on a DIFFERENT field's prose that happens to
// mention "**Fire log**" in passing (e.g. a Pattern field discussing the feature itself),
// silently reading unrelated dates as real activity and defeating --dead's whole purpose.
function fieldLines(content, label) {
  const re = new RegExp(`^\\s*-\\s*\\*\\*${label}\\*\\*.*$`, 'gm');
  return content.match(re) || [];
}

// Reads a feedback_*.md entry and resolves its last-activity date via a three-tier fallback,
// each tier reached only if the one before yields nothing parseable:
//   most recent Fire log date  →  First seen date  →  file mtime.
// Never throws — pre-this-feature entries with no Fire log (or no First seen) bullet at all
// still resolve to a usable date via mtime. `activitySource` names which tier resolved it, so
// callers can distinguish "known-quiet since a real date" from "no dates recorded at all" —
// collapsing that distinction into a bare day-count would make a legacy entry with no dates
// indistinguishable from one that's genuinely been fired recently and just happens to read old.
// NOTE: the mtime tier is a last resort, not a durable timestamp — a re-materialized directory
// (fresh checkout, backup restore, cross-machine sync) resets mtime to the copy time, so an
// entry with no Fire log/First seen dates can transiently under-flag as fresh regardless of its
// true age. Accepted tradeoff (parse-never-throws beats a hard failure on legacy entries); the
// periodic audit is agent-reviewed downstream, which bounds the impact.
function parseEntry(path) {
  const content = readFileSync(path, 'utf-8');
  const fireDates = extractDates(fieldLines(content, 'Fire log').join(' '));
  const firstSeenDates = extractDates(fieldLines(content, 'First seen').join(' '));
  const firstSeen = firstSeenDates.length ? firstSeenDates[0] : null;

  let lastActivity, activitySource;
  if (fireDates.length) {
    lastActivity = new Date(Math.max(...fireDates.map(d => d.getTime())));
    activitySource = 'fire';
  } else if (firstSeen) {
    lastActivity = firstSeen;
    activitySource = 'first-seen';
  } else {
    lastActivity = statSync(path).mtime;
    activitySource = 'mtime';
  }

  return { fireCount: fireDates.length, lastActivity, activitySource };
}

function daysSince(date) {
  return (Date.now() - date.getTime()) / (1000 * 60 * 60 * 24);
}

const args = new Set(process.argv.slice(2));
const entries = listEntries();
const count = entries.length;

if (args.has('--count')) {
  console.log(count);
  process.exit(0);
}

if (args.has('--list')) {
  for (const e of entries.sort((a, b) => b.mtime - a.mtime)) {
    console.log(`${e.mtime.toISOString().slice(0, 10)}  ${e.name}`);
  }
  process.exit(0);
}

if (args.has('--dead')) {
  let days = DEAD_ENTRY_DAYS;
  // Only the FIRST --days= occurrence is honored (valid or not) — a second occurrence is
  // silently ignored rather than potentially overwriting `days` again with a message that no
  // longer matches what's in effect (e.g. `--days=30 --days=bogus` warning about `bogus` while
  // `days` is actually still 30 from the first flag).
  const daysFlag = [...args].find(a => a.startsWith('--days='));
  if (daysFlag) {
    // Validate the RAW string, not parseInt's output — parseInt('60.9')=60 and
    // Number.isInteger(60)===true, so checking only the parsed value silently truncates
    // fractional/exponential input instead of rejecting it. `(.*)$` (not `(.+)$`) also
    // catches a bare `--days=` with nothing after the `=` (e.g. an unset shell variable
    // expansion) rather than letting it slip past the flag match entirely.
    const raw = daysFlag.slice('--days='.length);
    if (/^\d+$/.test(raw) && parseInt(raw, 10) > 0) {
      days = parseInt(raw, 10);
    } else {
      console.error(`⚠️ --days=${raw} is not a positive integer; using default ${DEAD_ENTRY_DAYS}`);
    }
  }

  const stale = entries
    .map(e => {
      const parsed = parseEntry(join(memoryDir, e.name));
      return { name: e.name, ...parsed, daysSinceActivity: daysSince(parsed.lastActivity) };
    })
    .filter(e => e.daysSinceActivity > days)
    .sort((a, b) => a.lastActivity - b.lastActivity); // oldest activity first

  if (stale.length === 0) {
    console.log(`No entries stale beyond ${days} days.`);
    process.exit(0);
  }

  const sourceLabel = { fire: 'fire', 'first-seen': 'first-seen', mtime: 'mtime — no Fire log/First seen found' };
  for (const e of stale) {
    const d = Math.floor(e.daysSinceActivity);
    const iso = e.lastActivity.toISOString().slice(0, 10);
    console.log(`${e.name}  (${iso}, ${d}d since last activity via ${sourceLabel[e.activitySource]}, ${e.fireCount} fire${e.fireCount === 1 ? '' : 's'})`);
  }
  console.log(`${stale.length} entr${stale.length === 1 ? 'y' : 'ies'} stale beyond ${days} days — archive candidates for the periodic audit.`);
  process.exit(0);
}

if (args.has('--audit-due')) {
  // Increments a counter; signals audit when interval reached or cap exceeded.
  let shipsSinceAudit = 0;
  if (existsSync(auditMarker)) {
    shipsSinceAudit = parseInt(readFileSync(auditMarker, 'utf-8').trim(), 10) || 0;
  }
  shipsSinceAudit += 1;
  const due = shipsSinceAudit >= AUDIT_INTERVAL || count >= HARD_CAP;
  if (due) {
    writeFileSync(auditMarker, '0');
    console.log(`audit due (ships since last: ${shipsSinceAudit}, entries: ${count}/${HARD_CAP})`);
    process.exit(1);
  }
  writeFileSync(auditMarker, String(shipsSinceAudit));
  console.log(`audit not due (${shipsSinceAudit}/${AUDIT_INTERVAL} ships, ${count}/${HARD_CAP} entries)`);
  process.exit(0);
}

// Default summary
console.log(`Memory: ${count}/${HARD_CAP} entries at ${memoryDir}`);
if (count >= HARD_CAP) {
  console.log(`AT/OVER CAP — curate (archive or merge) before adding more entries.`);
  process.exit(1);
}
if (count >= Math.floor(HARD_CAP * 0.8)) {
  console.log(`Approaching cap — start curating.`);
}
process.exit(0);
