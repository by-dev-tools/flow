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

const HARD_CAP = 30;
const AUDIT_INTERVAL = 5; // ship runs between audits

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
