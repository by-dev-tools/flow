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
  2. the diff (committed + uncommitted + untracked) touches a file matching this
     consumer's pattern — `visualFilePatterns` → `uiFilePatterns` → the built-in
     default (FB-0079; see lib/file_patterns.py) — OR adds/modifies an image /
     font / asset file, AND
  3. it is NOT a pure no-render-delta refactor (rename-only / comment-only /
     whitespace-only / punctuation-only / DEBUG-only-conditional change to
     those files — a hunk entirely inside a `#if DEBUG` / `#ifdef DEBUG`
     region is Release-byte-identical and does not count).

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

Exits 0 with a well-formed JSON verdict; a malformed config / unreadable plan
degrades to a documented default (uiSurface defaults TRUE — the
project-declares-UI assumption) with a `[WARN]` signal, never a crash and never a
silent skip. The one non-zero exit is an incomplete plugin install (lib/
file_patterns.py unimportable): stdout is still valid JSON, and the verdict fails
CLOSED (`visual_significant: true`) so a broken install demands the visual
deliverables rather than silently skipping the gate.

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

# Pattern resolution lives in file_patterns (FB-0079) — ONE definition of the
# visualFilePatterns → uiFilePatterns → default chain, shared with
# audit-skips/lib/skip-audit-checks.py so the two cannot drift. Guarded like
# walk_extract above: a partial plugin dir must not raise an ImportError
# traceback, because this script's only caller (skip-audit-checks.py) treats a
# crash as `visual_significant: false` — a FAIL-OPEN skip of the very gate this
# file exists to enforce. Missing sibling ⇒ main() emits a loud, fail-CLOSED
# verdict instead (see `_PATTERNS_IMPORT_ERROR` handling).
_PATTERNS_IMPORT_ERROR = None
try:
    from file_patterns import VISUAL, compile_for  # type: ignore
except Exception as _exc:  # pragma: no cover - defensive; file_patterns ships alongside
    # No sentinel rebinds: main() returns on _PATTERNS_IMPORT_ERROR before touching
    # either name, so a NameError is unreachable — and a `VISUAL = "visual"` fallback
    # would re-hardcode the very literal file_patterns.py says never to write bare.
    _PATTERNS_IMPORT_ERROR = _exc

# Image / font / asset files — a visual change can be a pure asset swap with no
# source edit. Generic, project-agnostic; overridable via --asset-patterns.
DEFAULT_ASSET_PATTERN = r"\.(png|jpe?g|gif|svg|webp|avif|ico|bmp|woff2?|ttf|otf|eot)$"

# Comment / structural-only line prefixes used by the pure-refactor exclusion. A
# changed line whose content (after stripping the +/- and whitespace) starts with
# one of these — or is pure punctuation — does not constitute a render delta.
_COMMENT_PREFIXES = ("//", "#", "/*", "*/", "*", "<!--", "-->", "--", ";")
_PUNCT_ONLY = set("{}()[];,.:")

# `#if DEBUG` / `#endif` tracking (Swift + C/Obj-C forms). A changed line inside
# a DEBUG-only conditional-compilation region is Release-byte-identical — it
# cannot be a visual delta for the build that ships. Detectable only from what
# the diff's own context shows (a DEBUG region opened outside the visible hunk
# is a known limitation of diff-based analysis, not something this can see).
_PP_IF_RE = re.compile(r"^#\s*(if|ifdef|ifndef)\b(.*)$")
_PP_ELSE_RE = re.compile(r"^#\s*else\b")
_PP_ENDIF_RE = re.compile(r"^#\s*endif\b")
_DEBUG_COND_RE = re.compile(r"^(?:defined\(\s*DEBUG\s*\)|DEBUG)$")
_NOT_DEBUG_COND_RE = re.compile(r"^!\s*(?:defined\(\s*DEBUG\s*\)|DEBUG)$")

# A modified/added/deleted binary file has NO `+++ b/<path>` header — git emits
# only `Binary files a/<pathA> and b/<pathB> differ`. Both sides are captured so
# add (`/dev/null and b/<path>`), delete (`a/<path> and /dev/null`), and modify
# (same path on both sides) are all covered by matching either side.
_BINARY_DIFF_RE = re.compile(r"^Binary files (.+) and (.+) differ$")


def _pp_own_kind(directive, cond):
    """Classify a `#if`/`#ifdef`/`#ifndef` condition as debug / not-debug / other."""
    cond = cond.strip()
    if directive == "ifdef":
        return "debug" if cond == "DEBUG" else "other"
    if directive == "ifndef":
        return "not-debug" if cond == "DEBUG" else "other"
    if _DEBUG_COND_RE.match(cond):
        return "debug"
    if _NOT_DEBUG_COND_RE.match(cond):
        return "not-debug"
    return "other"


def _git(args):
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, timeout=10)
        return out.stdout if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def resolve_base(explicit):
    """Return the ref to diff against. Prefer the remote-tracking `origin/<branch>`:
    a local `<branch>` can be stale or absent in a worktree / CI checkout, and
    diffing against it would silently pick the wrong base and FAIL OPEN
    (visual_significant=false on exactly the change the gate exists to catch —
    the FB-0010 silent-skip class this PR closes). Fall back to local `<branch>`
    only if the remote ref doesn't resolve."""
    branch = explicit
    if not branch:
        ref = _git(["symbolic-ref", "refs/remotes/origin/HEAD"]).strip()
        branch = ref[len("refs/remotes/origin/"):] if ref.startswith("refs/remotes/origin/") else "main"
    if branch.startswith("origin/"):
        return branch
    for cand in (f"origin/{branch}", branch):
        if _git(["rev-parse", "--verify", "--quiet", cand]).strip():
            return cand
    return f"origin/{branch}"


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


def _diff_content_changed(diff_text, visual_re, asset_re):
    """Returns (changed, debug_only_skipped):
      - changed: True if any +/- line inside a UI/asset file's hunk is a real
        render delta (not comment / whitespace / pure-punctuation / DEBUG-only).
      - debug_only_skipped: True iff at least one candidate content line was
        excluded specifically for being inside a DEBUG-only region (evidence
        for the caller's signals, even when `changed` ends up True from some
        other line).
    Parses unified diff; tracks the current file via the `+++ b/<path>` header.
    A binary file emits NO `+++` header (only `Binary files a/… and b/… differ`),
    so those are handled separately: a matched path on either side of that line is
    a real render delta, covering binary add / modify / delete uniformly (a font or
    icon re-export is an in-place modify at the same path — the always-broken case
    this fix closes). Also tracks `#if DEBUG` / `#endif` nesting (from context +
    changed lines alike) so a change entirely inside a DEBUG-only conditional-
    compilation region — Release byte-identical — does not count as a visual delta."""
    cur_relevant = False
    pp_stack = []  # [{"effective": bool, "kind": "debug"|"not-debug"|"other"}, ...]
    debug_only_skipped = False

    def debug_only():
        return bool(pp_stack) and pp_stack[-1]["effective"]

    for line in diff_text.splitlines():
        if line.startswith("Binary files "):
            # No `+++ b/<path>` header exists for a binary file — parse this line
            # instead. Check BOTH sides (add carries the path on b/, delete on a/,
            # modify on both) directly against the patterns; a matched path on
            # either side (ignoring /dev/null) is a render delta. Self-contained:
            # does not read/write cur_relevant or the preprocessor stack, so text-
            # hunk DEBUG tracking is unaffected. A binary delete counts as a render
            # delta by the same fail-safe logic as a modify (see the module + the
            # history entry: removing a rendered asset changes what draws).
            mb = _BINARY_DIFF_RE.match(line)
            if mb:
                for side in (mb.group(1), mb.group(2)):
                    p = side.strip()
                    if p.startswith("a/") or p.startswith("b/"):
                        p = p[2:]
                    if p != "/dev/null" and (visual_re.search(p) or asset_re.search(p)):
                        return True, debug_only_skipped
            continue
        if line.startswith("+++ "):
            p = line[4:].strip()
            if p.startswith("b/"):
                p = p[2:]
            cur_relevant = bool(visual_re.search(p) or asset_re.search(p)) and p != "/dev/null"
            pp_stack = []  # preprocessor nesting does not carry across files
            continue
        if line.startswith("--- ") or line.startswith("diff ") or line.startswith("@@"):
            continue
        if not cur_relevant:
            continue

        prefix = line[:1]
        raw = line[1:] if prefix in ("+", "-", " ") else line
        stripped = raw.strip()

        m = _PP_IF_RE.match(stripped)
        if m:
            kind = _pp_own_kind(m.group(1), m.group(2))
            parent_effective = pp_stack[-1]["effective"] if pp_stack else False
            effective = {"debug": True, "not-debug": False}.get(kind, parent_effective)
            pp_stack.append({"effective": effective, "kind": kind})
        elif _PP_ELSE_RE.match(stripped) and pp_stack:
            top = pp_stack[-1]
            if top["kind"] == "debug":
                top["effective"], top["kind"] = False, "not-debug"
            elif top["kind"] == "not-debug":
                top["effective"], top["kind"] = True, "debug"
            # "other"-kind #if: #else stays at the parent's effective value.
        elif _PP_ENDIF_RE.match(stripped) and pp_stack:
            pp_stack.pop()

        if prefix not in ("+", "-"):
            continue
        body = stripped
        if not body:
            continue  # whitespace-only
        if any(body.startswith(pfx) for pfx in _COMMENT_PREFIXES):
            continue  # comment-only (also catches the #if/#else/#endif lines themselves)
        if all(ch in _PUNCT_ONLY or ch.isspace() for ch in body):
            continue  # pure punctuation / brace move
        if debug_only():
            debug_only_skipped = True
            continue  # DEBUG-only region — Release build is byte-identical
        return True, debug_only_skipped
    return False, debug_only_skipped


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

    # A missing file_patterns sibling means we cannot resolve WHICH files count as
    # visual. Emit a well-formed, FAIL-CLOSED verdict (significant=true demands the
    # visual deliverables; a `false` here would silently skip the gate) and exit
    # non-zero. stdout stays valid JSON so skip-audit-checks.py — which parses
    # stdout regardless of exit status — reads the loud verdict, not a crash.
    if _PATTERNS_IMPORT_ERROR is not None:
        # Read the config FIRST. uiSurface:false is documented everywhere as
        # unconditional — "a project that declares NO UI surface is never visually
        # significant". Failing closed PAST that gate hands a headless project an
        # unsatisfiable visual-deliverable blocker (ship Step 7a branches on this
        # value with no uiSurface guard of its own) whose real cause is a broken
        # install. load_config has no dependency on file_patterns.
        _cfg, _cfg_warnings = load_config(args.config)
        _uis = ui_surface(_cfg)
        print(json.dumps({
            "visual_significant": _uis,
            "ui_surface": _uis,
            "override": None,
            "visual_signals": _cfg_warnings + [
                f"[WARN] cannot import lib/file_patterns.py ({_PATTERNS_IMPORT_ERROR}) — "
                f"the flow plugin install is incomplete. Reinstall the plugin. Until then "
                f"this change is treated as needing visual review rather than skipping the "
                f"check" + ("" if _uis else ", except that this project declares no UI "
                            "surface (uiSurface:false), which still wins") + ".",
            ],
            "reason": "could not load the UI-file patterns, so this is a safe default, not a measurement",
        }, indent=2))
        return 2

    cfg, signals = load_config(args.config)
    uis = ui_surface(cfg)

    # visualFilePatterns → uiFilePatterns → default (FB-0079). `source` names the
    # slot that actually supplied the pattern so the signals show an operator which
    # knob produced this scoping.
    visual_re, visual_src, pat_warnings = compile_for(cfg, VISUAL)
    signals.extend(pat_warnings)
    asset_pat = args.asset_patterns or DEFAULT_ASSET_PATTERN
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
            # anchor_label scopes the match to the ACTIVE PR's section — a
            # retained PR's Visual-walk block must not force significance on a
            # diff whose own plan block declares none (block_count alone can't
            # tell the two apart).
            blk = extract_block(plan_text, "Visual-walk", anchor_label="Spec-walk")
            if blk.get("co_located") is False:
                signals.append(
                    "[WARN] a Visual-walk block exists but belongs to a retained "
                    "PR section, not the active one — NOT treating it as an "
                    "override"
                )
                # Carry the parser's warnings through: they hold the line numbers
                # and the move-it-here remedy. Dropping them would leave the
                # operator with a refusal and no way to act on it.
                signals.extend(f"[WARN] {w}" for w in blk.get("warnings", []))
            elif blk.get("all_demoted"):
                # Every Visual-walk block is qualified (merged/shipped/demoted), so
                # the active plan section declares none. block_count >= 1 here, but
                # the just-demoted pair floats to the top and would read as active —
                # exactly the state a correct demote-at-merge produces. Requiring an
                # ACTIVE (bare) block closes the false override: a docs-only post-merge
                # PR must NOT be forced visually significant off a retained block.
                signals.append(
                    "[WARN] every Visual-walk block is demoted (qualified "
                    "merged/shipped) — the active plan section declares none; "
                    "NOT treating it as an override (expected after demote-at-merge; "
                    "no action needed)"
                )
                signals.extend(f"[WARN] {w}" for w in blk.get("warnings", []))
            elif blk.get("block_count", 0) >= 1:
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
        visual_asset_paths = [p for st, p in changes if visual_re.search(p) or asset_re.search(p)]
        diff_text = ""
        if visual_asset_paths:
            diff_text = _git(["diff", f"{base}...HEAD", "-M", "--", *visual_asset_paths]) \
                + _git(["diff", "HEAD", "-M", "--", *visual_asset_paths])

    # --- override path: force-true, but still attach heuristic evidence ---
    if override_signal:
        signals.append(f"{override_signal} → forces visually-significant")

    # --- heuristic evidence ---
    visual_hits = [p for st, p in changes if visual_re.search(p)]
    asset_hits = [p for st, p in changes if asset_re.search(p) and not visual_re.search(p)]
    matched = visual_hits + asset_hits
    if visual_hits:
        signals.append(f"diff touches UI files (pattern from {visual_src}): "
                       + ", ".join(sorted(set(visual_hits))[:8]))
    if asset_hits:
        signals.append("diff adds/modifies asset files: " + ", ".join(sorted(set(asset_hits))[:8]))

    # Pure-refactor exclusion. A new (A) or untracked (U) UI/asset file is a real
    # render delta by construction (its content is all-added). For modified files
    # we inspect the diff: if NONE of the matched files carry a content delta, the
    # change is rename-only / comment-only / whitespace-only ⇒ not significant.
    new_files = [p for st, p in changes if st in ("A", "U") and (visual_re.search(p) or asset_re.search(p))]
    diff_changed, debug_only_skipped = _diff_content_changed(diff_text, visual_re, asset_re)
    content_changed = bool(new_files) or diff_changed
    # An asset whose path matched but which only appears under a rename (R) with no
    # content, and no diff body, is caught here: matched but content_changed False.
    if debug_only_skipped:
        signals.append(
            "some matched-file hunks were inside a `#if DEBUG` region and were "
            "NOT counted as a render delta (Release build is byte-identical there)"
        )

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
