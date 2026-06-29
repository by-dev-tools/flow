#!/usr/bin/env python3
"""
Shared "visual-significance" predicate for the flow ship pipeline.

ONE source of truth, reused by BOTH /flow:verify-build (which stamps the verdict
into the findings buffer metadata) and /flow:ship (Step 5c distill + Step 7
dual-deliverable gate). Downstream steps read the ONE authoritative value from
the buffer (`metadata.visual_significant` / `metadata.visual_signals`) rather than
re-deriving it (FB-0010 fan-out defense). Ship re-runs this helper only when there
is no buffer to read (verify-build skipped/short-circuited).

A change is **visually significant** when ALL of:
  1. `uiSurface != false`  (the project declares a UI surface), AND
  2. the diff (committed + uncommitted + untracked) touches a `uiFilePatterns`
     file OR adds/modifies an image / font / asset file, AND
  3. it is NOT a pure no-render-delta refactor (rename-only / comment-only /
     whitespace-only / punctuation-only change to those files).

Strong overrides that force `significant = true` regardless of the heuristics
above (but still subject to gate 1 — a project that declares NO UI surface is
never visually significant; an override under `uiSurface:false` is recorded as
suppressed, never silently honored):
  - the plan declares a `Visual-walk` block, OR
  - the agent explicitly flags it (`--flag-significant`, with `--flag-reason`).

Output (stdout, JSON):
  {
    "visual_significant": bool,
    "ui_surface": bool,
    "override": "visual-walk-block" | "agent-flag" | null,
    "visual_signals": ["<evidence line>", ...],   # the WHY, for the buffer + logs
    "reason": "<one-line summary>"
  }

Always exits 0 with a well-formed JSON verdict; a malformed config / unreadable
plan degrades to a documented default (uiSurface defaults TRUE — the
project-declares-UI assumption) with a `[WARN]` signal, never a crash and never a
silent skip.

Two input modes:
  - GIT mode (default): collects changed files + diff from git in CWD vs --base.
  - EXPLICIT mode (--files-from): reads a newline file list (each line
    "<status>\\t<path>", bare "path" ⇒ status M) and an optional --diff-from
    unified diff. Lets evals feed synthetic change-sets deterministically.

Stdlib only. Python 3.7+.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# extract_block (Visual-walk override) — reuse the shared walk parser so block
# detection cannot drift from the verify-build extractors (FB-0010).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from walk_extract import extract_block  # type: ignore
except Exception:  # pragma: no cover - defensive; walk_extract ships alongside
    extract_block = None

# Default UI-file pattern — MUST stay in sync with accessibility-review/SKILL.md's
# UI_PATTERN default (the shared uiFilePatterns contract value, FB-0010).
DEFAULT_UI_PATTERN = r"\.(tsx|jsx|vue|svelte|astro|mdx|css|scss|sass|less|html|njk|hbs|ejs)$"
# Image / font / asset files — a visual change can be a pure asset swap with no
# source edit. Generic, project-agnostic; overridable via --asset-patterns.
DEFAULT_ASSET_PATTERN = r"\.(png|jpe?g|gif|svg|webp|avif|ico|bmp|woff2?|ttf|otf|eot)$"

# Comment / structural-only line prefixes used by the pure-refactor exclusion. A
# changed line whose content (after stripping the +/- and whitespace) starts with
# one of these — or is pure punctuation — does not constitute a render delta.
_COMMENT_PREFIXES = ("//", "#", "/*", "*/", "*", "<!--", "-->", "--", ";")
_PUNCT_ONLY = set("{}()[];,.:")


def _git(args):
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, timeout=10)
        return out.stdout if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def resolve_base(explicit):
    if explicit:
        return explicit
    ref = _git(["symbolic-ref", "refs/remotes/origin/HEAD"]).strip()
    if ref.startswith("refs/remotes/origin/"):
        return ref[len("refs/remotes/origin/"):]
    return "main"


def load_config(path):
    """Return (cfg_dict, warnings)."""
    warnings = []
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError:
        return {}, [f"[WARN] no config at {path}; using built-in defaults (uiSurface defaults true)"]
    try:
        return json.loads(raw), warnings
    except ValueError as exc:
        return {}, [f"[WARN] config at {path} is malformed JSON ({exc}); using built-in defaults"]


def ui_surface(cfg):
    # FB-0058 boolean-slot idiom: ONLY an explicit `false` disables; absent ⇒ true.
    return cfg.get("uiSurface") is not False


def collect_changes_git(base):
    """Return a list of (status, path) tuples from the 3-way union."""
    changes = []
    # Committed vs base, with rename detection.
    for src in (["diff", f"{base}...HEAD", "--name-status", "-M"],
                ["diff", "HEAD", "--name-status", "-M"]):
        for line in _git(src).splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            status = parts[0][:1]  # R100 -> R, A -> A, M -> M
            path = parts[-1]       # rename: old\tnew -> take new (the live path)
            changes.append((status, path))
    # Untracked.
    for line in _git(["ls-files", "--others", "--exclude-standard"]).splitlines():
        if line.strip():
            changes.append(("U", line.strip()))
    return changes


def collect_changes_explicit(files_from):
    changes = []
    try:
        raw = Path(files_from).read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"[visual-significance] cannot read --files-from {files_from}: {exc}\n")
        return changes
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) == 1:
            changes.append(("M", parts[0].strip()))
        else:
            changes.append((parts[0].strip()[:1] or "M", parts[-1].strip()))
    return changes


def _diff_content_changed(diff_text, ui_re, asset_re):
    """True if any +/- line inside a UI/asset file's hunk is a real render delta
    (not comment / whitespace / pure-punctuation). Parses unified diff; tracks the
    current file via the `+++ b/<path>` header."""
    cur_relevant = False
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            p = line[4:].strip()
            if p.startswith("b/"):
                p = p[2:]
            cur_relevant = bool(ui_re.search(p) or asset_re.search(p)) and p != "/dev/null"
            continue
        if line.startswith("--- ") or line.startswith("diff ") or line.startswith("@@"):
            continue
        if not cur_relevant:
            continue
        if line[:1] in ("+", "-") and not line.startswith(("+++", "---")):
            body = line[1:].strip()
            if not body:
                continue  # whitespace-only
            if any(body.startswith(pfx) for pfx in _COMMENT_PREFIXES):
                continue  # comment-only
            if all(ch in _PUNCT_ONLY or ch.isspace() for ch in body):
                continue  # pure punctuation / brace move
            return True
    return False


def main(argv):
    ap = argparse.ArgumentParser(description="Compute the visual-significance verdict.")
    ap.add_argument("--config", default="flow.config.json")
    ap.add_argument("--plan", default=None, help="plan path for the Visual-walk override")
    ap.add_argument("--base", default=None, help="default-branch ref (git mode)")
    ap.add_argument("--files-from", default=None, help="explicit change-set file (eval mode)")
    ap.add_argument("--diff-from", default=None, help="explicit unified diff (eval mode)")
    ap.add_argument("--asset-patterns", default=None, help="override asset-file regex")
    ap.add_argument("--flag-significant", action="store_true", help="agent override → significant")
    ap.add_argument("--flag-reason", default=None, help="reason recorded for --flag-significant")
    args = ap.parse_args(argv[1:])

    cfg, signals = load_config(args.config)
    uis = ui_surface(cfg)

    ui_pat = cfg.get("uiFilePatterns") or DEFAULT_UI_PATTERN
    asset_pat = args.asset_patterns or DEFAULT_ASSET_PATTERN
    try:
        ui_re = re.compile(ui_pat)
    except re.error:
        signals.append(f"[WARN] uiFilePatterns invalid regex ({ui_pat!r}); using default")
        ui_re = re.compile(DEFAULT_UI_PATTERN)
    try:
        asset_re = re.compile(asset_pat)
    except re.error:
        signals.append(f"[WARN] asset pattern invalid regex; using default")
        asset_re = re.compile(DEFAULT_ASSET_PATTERN)

    # --- detect overrides (recorded even when suppressed by uiSurface:false) ---
    override = None
    override_signal = None
    if args.flag_significant:
        override = "agent-flag"
        reason = args.flag_reason or "(no reason given)"
        override_signal = f"agent explicitly flagged visually-significant — reason: {reason}"
    elif args.plan:
        try:
            plan_text = Path(args.plan).read_text(encoding="utf-8")
        except OSError:
            plan_text = ""
            signals.append(f"[WARN] could not read plan {args.plan} for Visual-walk override")
        if plan_text and extract_block is not None:
            blk = extract_block(plan_text, "Visual-walk")
            if blk.get("block_count", 0) >= 1:
                override = "visual-walk-block"
                override_signal = "plan declares a Visual-walk block"

    def emit(significant, reason):
        out = {
            "visual_significant": bool(significant),
            "ui_surface": bool(uis),
            "override": override if significant else (override if override else None),
            "visual_signals": signals,
            "reason": reason,
        }
        print(json.dumps(out, indent=2))
        return 0

    # Gate 1: no declared UI surface ⇒ never significant. An override here is
    # recorded as SUPPRESSED, never silently honored.
    if not uis:
        signals.append("uiSurface=false — project declares no UI surface")
        if override_signal:
            signals.append(f"override SUPPRESSED by uiSurface=false ({override_signal})")
        return emit(False, "uiSurface=false: not visually significant")

    signals.append("uiSurface=true")

    # --- collect the change-set + diff ---
    if args.files_from:
        changes = collect_changes_explicit(args.files_from)
        diff_text = ""
        if args.diff_from:
            try:
                diff_text = Path(args.diff_from).read_text(encoding="utf-8")
            except OSError as exc:
                signals.append(f"[WARN] could not read --diff-from {args.diff_from}: {exc}")
    else:
        base = resolve_base(args.base)
        changes = collect_changes_git(base)
        ui_asset_paths = [p for st, p in changes if ui_re.search(p) or asset_re.search(p)]
        diff_text = ""
        if ui_asset_paths:
            diff_text = _git(["diff", f"{base}...HEAD", "-M", "--", *ui_asset_paths]) \
                + _git(["diff", "HEAD", "-M", "--", *ui_asset_paths])

    # --- override path: force-true, but still attach heuristic evidence ---
    if override_signal:
        signals.append(f"{override_signal} → forces visually-significant")

    # --- heuristic evidence ---
    ui_hits = [p for st, p in changes if ui_re.search(p)]
    asset_hits = [p for st, p in changes if asset_re.search(p) and not ui_re.search(p)]
    matched = ui_hits + asset_hits
    if ui_hits:
        signals.append("diff touches uiFilePatterns: " + ", ".join(sorted(set(ui_hits))[:8]))
    if asset_hits:
        signals.append("diff adds/modifies asset files: " + ", ".join(sorted(set(asset_hits))[:8]))

    # Pure-refactor exclusion. A new (A) or untracked (U) UI/asset file is a real
    # render delta by construction (its content is all-added). For modified files
    # we inspect the diff: if NONE of the matched files carry a content delta, the
    # change is rename-only / comment-only / whitespace-only ⇒ not significant.
    new_files = [p for st, p in changes if st in ("A", "U") and (ui_re.search(p) or asset_re.search(p))]
    content_changed = bool(new_files) or _diff_content_changed(diff_text, ui_re, asset_re)
    # An asset whose path matched but which only appears under a rename (R) with no
    # content, and no diff body, is caught here: matched but content_changed False.

    if override_signal:
        return emit(True, f"override ({override}) forces visually-significant")

    if not matched:
        signals.append("diff touches no UI or asset files")
        return emit(False, "no UI/asset files in the diff: not visually significant")

    if not content_changed:
        signals.append("matched UI/asset files carry NO render delta (rename / comment / whitespace only)")
        return emit(False, "pure no-render-delta refactor of UI/asset files: not visually significant")

    signals.append("matched UI/asset files carry a real render delta")
    return emit(True, "diff makes a real change to a UI/asset surface: visually significant")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
