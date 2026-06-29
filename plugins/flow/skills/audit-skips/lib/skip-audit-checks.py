#!/usr/bin/env python3
"""
Deterministic ground-truth engine for /flow:audit-skips (Feature 2).

The skill is a skeptical, fresh-context, read-only reviewer (modeled on
/flow:audit-coverage). This helper owns the MECHANICAL half: for each stage's
reported status + skip reason + expected output artifact, it cross-checks the
claim against ground truth (config slots, the diff, the canonical artifact's
existence + freshness) and emits a per-stage `mechanical` verdict the fork agent
trusts:

  LEGITIMATE      — the skip reason is verified against ground truth.
  SHOULD-RE-RUN   — the skip reason is contradicted by the diff/config, OR the
                    stage claims it RAN but its canonical OUTPUT ARTIFACT is
                    absent / stale for HEAD (verdict-without-artifact == skip).
  NEEDS-JUDGMENT  — not mechanically decidable (e.g. a spike/tiny mode skip); the
                    fork agent adjudicates.

The load-bearing rule: a stage's claimed verdict is trusted only if its canonical
artifact EXISTS and matches HEAD. A PASS with no fresh buffer is the "agent
confirmed manually + self-certified" failure — the missing buffer is the tell.

Input: a "stages report" JSON (--report PATH or stdin):
  {"stages": [
     {"name":"verify-build","status":"ran","verdict":"PASS","skip_reason":null},
     {"name":"security","status":"skipped","skip_reason":"doc-only"},
     {"name":"accessibility","status":"skipped","skip_reason":"uiSurface:false"},
     {"name":"audit-coverage","status":"skipped","skip_reason":"no Spec-walk"},
     {"name":"simplify","status":"ran"},
     {"name":"staff-review","status":"ran"},
     {"name":"visual-verification","status":"skipped"}
  ]}

Ground-truth sources (all overridable for eval determinism):
  --config        flow.config.json (platform, uiSurface, verifyEnabled, *Path slots)
  --head-sha      current short HEAD (default: git rev-parse --short HEAD)
  --branch        current branch (default: git branch --show-current)
  --files-from    explicit change-set (status\\tpath lines) — else 3-way git union
  --diff-from     explicit unified diff (for the visual-significance refactor test)
  --plan          plan path (Spec-walk / Visual-walk detection)
  --base          default-branch ref (git mode)

Always exits 0 with a well-formed JSON report (a clean read is the common case;
a missing artifact is a finding, not an error). Stdlib only. Python 3.7+.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
# Reuse the verify-build lib (one source of truth — FB-0010).
VS_HELPER = os.path.normpath(os.path.join(HERE, "..", "..", "verify-build", "lib", "visual-significance.py"))
WALK_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "verify-build", "lib"))
RIGOR_HELPER = os.path.normpath(os.path.join(HERE, "..", "..", "ship", "lib", "rigor-marker.py"))
sys.path.insert(0, WALK_DIR)
try:
    from walk_extract import extract_block  # type: ignore
except Exception:
    extract_block = None

DEFAULT_SOURCE_PATTERN = (
    r"\.(ts|tsx|js|jsx|mjs|cjs|py|rs|swift|go|rb|java|kt|sh|bash|tf|tfvars|sql|proto|graphql|gql)$"
    r"|\.(json|ya?ml|toml)$|(^|/)(Dockerfile|Makefile)(\.|$)"
)
DEFAULT_UI_PATTERN = r"\.(tsx|jsx|vue|svelte|astro|mdx|css|scss|sass|less|html|njk|hbs|ejs)$"

# Stages whose SHOULD-RE-RUN is cheaply re-runnable by ship (re-invoke the Skill);
# everything else routes to the draft manifest as decision-required.
_AUTO_RERUN = {"verify-build", "security", "accessibility", "audit-coverage", "simplify", "staff-review"}


def _git(args):
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, timeout=10)
        return out.stdout if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def resolve_base(explicit):
    """Prefer the remote-tracking `origin/<branch>` ref — a local `<branch>` can be
    stale/absent in a worktree or CI checkout, which would diff against the wrong
    base and FAIL OPEN (FB-0010 silent-skip). Fall back to local `<branch>`."""
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


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def collect_files(files_from, base):
    paths = []
    if files_from:
        try:
            raw = Path(files_from).read_text(encoding="utf-8")
        except OSError:
            raw = ""
        for line in raw.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            paths.append(parts[-1].strip())
    else:
        for src in ([f"{base}...HEAD"], ["HEAD"]):
            for line in _git(["diff", *src, "--name-only"]).splitlines():
                if line.strip():
                    paths.append(line.strip())
        for line in _git(["ls-files", "--others", "--exclude-standard"]).splitlines():
            if line.strip():
                paths.append(line.strip())
    return paths


def compute_visual_significance(args, cfg_path):
    """Call the shared helper so visual_significant has ONE definition (FB-0010)."""
    argv = [sys.executable, VS_HELPER, "--config", cfg_path]
    if args.files_from:
        argv += ["--files-from", args.files_from]
    if args.diff_from:
        argv += ["--diff-from", args.diff_from]
    if args.plan:
        argv += ["--plan", args.plan]
    if args.base:
        argv += ["--base", args.base]
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=20)
        return json.loads(out.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return {"visual_significant": False, "visual_signals": ["[WARN] visual-significance helper unavailable"]}


def read_buffer(path, branch, head_sha):
    """Return dict of buffer facts for the verify-build findings artifact."""
    facts = {"path": path, "exists": False, "fresh": False, "branch": None,
             "head_sha_short": None, "overall_verdict": None, "screenshot_frames": 0,
             "visual_significant": None}
    if not path:
        return facts
    data = load_json(path, None)
    if not isinstance(data, dict):
        return facts
    facts["exists"] = True
    meta = data.get("metadata") or {}
    facts["branch"] = meta.get("branch")
    facts["head_sha_short"] = meta.get("head_sha_short")
    facts["overall_verdict"] = data.get("overall_verdict")
    facts["visual_significant"] = meta.get("visual_significant")
    frames = 0
    # Coupling note: a captured frame is an observation with type=="screenshot"
    # (verify-build §5a stamps exactly that type). If that discriminator ever
    # changes, this count would silently zero → every visually-significant PASS
    # would route to SHOULD-RE-RUN. Keep in sync with the schema's observation enum.
    for crit in (data.get("criteria") or []):
        for obs in (crit.get("observations") or []):
            if isinstance(obs, dict) and obs.get("type") == "screenshot":
                frames += 1
    facts["screenshot_frames"] = frames
    b_ok = (not facts["branch"]) or (branch and facts["branch"] == branch)
    s_ok = (not facts["head_sha_short"]) or (head_sha and facts["head_sha_short"] == head_sha)
    facts["fresh"] = bool(facts["exists"] and b_ok and s_ok and (facts["branch"] or facts["head_sha_short"]))
    return facts


def vh_references_branch(path, branch):
    """Best-effort: does the durable visual-history doc mention this branch?
    The Step 7 gate is authoritative; this is the audit's corroborating read."""
    if not path or not branch:
        return None
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return False
    return branch in text


def rigor_fresh(branch, source_pattern):
    """Mechanical staff-review evidence: is there a fresh rigor marker for this
    source on this branch? Mirrors ship Step 1.0a."""
    if not os.path.exists(RIGOR_HELPER) or not branch:
        return None
    try:
        sha = subprocess.run([sys.executable, RIGOR_HELPER, "source-sha",
                              "--source-pattern", source_pattern],
                             capture_output=True, text=True, timeout=15).stdout.strip()
        res = subprocess.run([sys.executable, RIGOR_HELPER, "check", "--branch", branch,
                              "--source-sha", sha],
                             capture_output=True, text=True, timeout=15)
        return res.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return None


def _reason_has(skip_reason, *needles):
    s = (skip_reason or "").lower()
    return any(n in s for n in needles)


def _doc_only_verdict(diff_is_clean, label, auto):
    """Shared resolution for a 'doc-only / no <label>' skip claim: LEGITIMATE when
    the diff really touches no files of that class, else SHOULD-RE-RUN."""
    if diff_is_clean:
        return "LEGITIMATE", f"diff touches no {label}", auto
    return "SHOULD-RE-RUN", f"skip claims doc-only but the diff touches {label}", auto


def classify(stage, ctx):
    """Return (mechanical, reason, auto_resolvable) for one stage."""
    name = stage.get("name", "?")
    status = (stage.get("status") or "").lower()
    verdict = stage.get("verdict")
    skip = stage.get("skip_reason")
    cfg = ctx["config"]
    diff = ctx["diff"]
    buf = ctx["buffer"]
    auto = name in _AUTO_RERUN

    # ---- verify-build ----
    if name == "verify-build":
        if status == "skipped":
            if _reason_has(skip, "platform library", "platform none", "library", "none"):
                if str(cfg.get("platform")) in ("library", "none"):
                    return "LEGITIMATE", "platform resolves to library/none — no runnable target", auto
                return "SHOULD-RE-RUN", f"skip claims platform library/none but platform={cfg.get('platform')!r}", auto
            if _reason_has(skip, "verifyenabled"):
                if cfg.get("verifyEnabled") is False:
                    return "LEGITIMATE", "verifyEnabled=false — project opted out", auto
                return "SHOULD-RE-RUN", "skip claims verifyEnabled=false but it is not set false", auto
            if _reason_has(skip, "doc-only", "no behavior", "docs-only", "no source"):
                if not diff["touches_source"] and not diff["touches_ui"]:
                    return "LEGITIMATE", "diff touches no source/UI files", auto
                return "SHOULD-RE-RUN", "skip claims doc-only but the diff touches source/UI files", auto
            return "NEEDS-JUDGMENT", f"unrecognized verify-build skip reason: {skip!r}", auto
        # status ran
        if not buf["exists"]:
            return "SHOULD-RE-RUN", f"claims it ran (verdict {verdict}) but NO findings buffer at {buf['path']} — verdict without an artifact is a skip", auto
        if str(verdict) == "PASS" and not buf["fresh"]:
            return ("SHOULD-RE-RUN",
                    f"claims PASS but the buffer is stale (verified {buf['branch']}@{buf['head_sha_short']}, HEAD is {ctx['branch']}@{ctx['head_sha']}) — self-certified PASS with no fresh artifact", auto)
        if str(verdict) == "PASS" and ctx["visual_significant"] and buf["screenshot_frames"] == 0:
            return ("SHOULD-RE-RUN",
                    "visually-significant PASS with ZERO captured frames — must be Unknown until frames are captured or a not_tested rationale is recorded", auto)
        return "LEGITIMATE", f"ran; fresh buffer present (verdict {verdict})", auto

    # ---- security ----
    if name == "security":
        if status == "skipped":
            if _reason_has(skip, "doc-only", "docs-only", "trivially safe", "no source"):
                return _doc_only_verdict(not diff["touches_source"], "source/config files", auto)
            return "NEEDS-JUDGMENT", f"unrecognized security skip reason: {skip!r}", auto
        return "LEGITIMATE", "ran (no machine artifact to cross-check)", auto

    # ---- accessibility ----
    if name in ("accessibility", "a11y"):
        if status == "skipped":
            if _reason_has(skip, "uisurface"):
                if cfg.get("uiSurface") is False:
                    return "LEGITIMATE", "uiSurface=false — project declares no UI surface", auto
                return "SHOULD-RE-RUN", "skip claims uiSurface:false but it is not set false", auto
            if _reason_has(skip, "no ui", "non-ui", "no ui in diff"):
                if not diff["touches_ui"]:
                    return "LEGITIMATE", "diff touches no UI files", auto
                return "SHOULD-RE-RUN", "skip claims no UI in diff but the diff touches UI files", auto
            return "NEEDS-JUDGMENT", f"unrecognized a11y skip reason: {skip!r}", auto
        return "LEGITIMATE", "ran", auto

    # ---- audit-coverage ----
    if name == "audit-coverage":
        if status == "skipped":
            if _reason_has(skip, "no spec-walk", "no spec walk", "no plan"):
                if ctx["spec_walk_blocks"] == 0:
                    return "LEGITIMATE", "plan has no **Spec-walk:** block", auto
                return "SHOULD-RE-RUN", f"skip claims no Spec-walk but the plan has {ctx['spec_walk_blocks']} block(s)", auto
            if _reason_has(skip, "no behavior", "doc", "test", "refactor"):
                if not diff["touches_source"]:
                    return "LEGITIMATE", "diff has no behavior-bearing source files", auto
                return "SHOULD-RE-RUN", "skip claims no behavior but the diff touches source files", auto
            return "NEEDS-JUDGMENT", f"unrecognized audit-coverage skip reason: {skip!r}", auto
        return "LEGITIMATE", "ran", auto

    # ---- simplify / staff-review ----
    if name in ("simplify", "staff-review"):
        if status == "skipped":
            if _reason_has(skip, "doc-only", "docs-only", "no source"):
                return _doc_only_verdict(not diff["touches_source"], "source files", auto)
            # spike / tiny mode is a plan declaration — not mechanically decidable.
            return "NEEDS-JUDGMENT", f"skip reason {skip!r} is mode-declared (spike/tiny) — confirm against the plan", auto
        # ran: staff-review writes the rigor marker; a missing/stale marker on a
        # source-touching diff means no mechanical evidence it ran on THIS source.
        if name == "staff-review" and diff["touches_source"]:
            if ctx["rigor_fresh"] is False:
                return "SHOULD-RE-RUN", "claims it ran but no fresh staff-review rigor marker for this source (ship Step 1.0a) — verdict without an artifact is a skip", auto
            if ctx["rigor_fresh"] is True:
                return "LEGITIMATE", "ran; fresh rigor marker matches the current source", auto
        return "NEEDS-JUDGMENT", "ran (no mechanically-verifiable artifact for this stage)", auto

    # ---- visual-verification / Present visual sign-off ----
    if name in ("visual-verification", "present", "visual"):
        if not ctx["visual_significant"]:
            return "LEGITIMATE", "change is not visually significant — no visual verification required", auto
        # visually significant: the dual deliverable is required.
        missing = []
        if not (buf["fresh"] and buf["screenshot_frames"] >= 1):
            missing.append("the rendered walkthrough (a fresh findings buffer with ≥1 captured frame)")
        if ctx["vh_references_branch"] is False:
            missing.append("a new visual-history entry referencing this branch")
        if status == "skipped":
            return ("SHOULD-RE-RUN",
                    "visual verification skipped while the change is visually significant", False)
        if missing:
            return ("SHOULD-RE-RUN",
                    "visually significant but missing " + " AND ".join(missing), False)
        return "LEGITIMATE", "visually significant; both deliverables present", auto

    return "NEEDS-JUDGMENT", f"unknown stage {name!r}", auto


def main(argv):
    ap = argparse.ArgumentParser(description="Mechanical ground-truth checks for /flow:audit-skips.")
    ap.add_argument("--report", default=None, help="stages-report JSON (default: stdin)")
    ap.add_argument("--config", default="flow.config.json")
    ap.add_argument("--head-sha", default=None)
    ap.add_argument("--branch", default=None)
    ap.add_argument("--files-from", default=None)
    ap.add_argument("--diff-from", default=None)
    ap.add_argument("--plan", default=None)
    ap.add_argument("--base", default=None)
    args = ap.parse_args(argv[1:])

    # Load the stages report.
    try:
        raw = Path(args.report).read_text(encoding="utf-8") if args.report else sys.stdin.read()
        report = json.loads(raw)
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": f"cannot read stages report: {exc}", "stages": []}))
        return 0
    stages = report.get("stages") or []

    cfg = load_json(args.config, {})
    branch = args.branch if args.branch is not None else _git(["branch", "--show-current"]).strip()
    head_sha = args.head_sha if args.head_sha is not None else _git(["rev-parse", "--short", "HEAD"]).strip()

    source_pat = cfg.get("sourceFilePatterns") or DEFAULT_SOURCE_PATTERN
    ui_pat = cfg.get("uiFilePatterns") or DEFAULT_UI_PATTERN
    try:
        src_re = re.compile(source_pat)
    except re.error:
        src_re = re.compile(DEFAULT_SOURCE_PATTERN)
    try:
        ui_re = re.compile(ui_pat)
    except re.error:
        ui_re = re.compile(DEFAULT_UI_PATTERN)

    base = resolve_base(args.base)
    files = collect_files(args.files_from, base)
    touches_source = any(src_re.search(p) for p in files)
    touches_ui = any(ui_re.search(p) for p in files)

    vs = compute_visual_significance(args, args.config)
    visual_significant = bool(vs.get("visual_significant"))

    # Resolve artifact paths from config slots (with documented defaults).
    findings_path = cfg.get("verifyFindingsPath") or "/tmp/flow-verify-findings.json"
    vh_path = cfg.get("visualHistoryPath") or "core-docs/visual-history.html"
    buf = read_buffer(findings_path, branch, head_sha)

    spec_blocks = 0
    if args.plan and extract_block is not None:
        try:
            spec_blocks = extract_block(Path(args.plan).read_text(encoding="utf-8"), "Spec-walk").get("block_count", 0)
        except OSError:
            spec_blocks = 0

    ctx = {
        "branch": branch, "head_sha": head_sha,
        "config": cfg,
        "diff": {"touches_source": touches_source, "touches_ui": touches_ui},
        "buffer": buf,
        "visual_significant": visual_significant,
        "spec_walk_blocks": spec_blocks,
        "rigor_fresh": rigor_fresh(branch, source_pat),
        "vh_references_branch": vh_references_branch(vh_path, branch),
    }

    out_stages = []
    n_rerun = n_legit = n_judg = 0
    for st in stages:
        mech, reason, auto = classify(st, ctx)
        if mech == "SHOULD-RE-RUN":
            n_rerun += 1
        elif mech == "LEGITIMATE":
            n_legit += 1
        else:
            n_judg += 1
        out_stages.append({
            "name": st.get("name"),
            "reported": {"status": st.get("status"), "verdict": st.get("verdict"),
                         "skip_reason": st.get("skip_reason")},
            "mechanical": mech,
            "reason": reason,
            "auto_resolvable": auto if mech == "SHOULD-RE-RUN" else None,
        })

    result = {
        "context": {
            "branch": branch, "head_sha_short": head_sha,
            "visual_significant": visual_significant,
            "visual_signals": vs.get("visual_signals", []),
            "diff": {"touches_source": touches_source, "touches_ui": touches_ui},
        },
        "config": {"platform": cfg.get("platform"), "uiSurface": cfg.get("uiSurface"),
                   "verifyEnabled": cfg.get("verifyEnabled"),
                   "verifyFindingsPath": findings_path, "visualHistoryPath": vh_path},
        "buffer": buf,
        "stages": out_stages,
        "summary": {"should_re_run": n_rerun, "legitimate": n_legit, "needs_judgment": n_judg},
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
