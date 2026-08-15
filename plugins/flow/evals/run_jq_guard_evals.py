#!/usr/bin/env python3
"""Eval harness for missing-`jq` handling across flow skills.

The bug it pins (research: dev-docs/research/jq-absence-handling-2026-06.md): on a
freshly-provisioned box with no `jq` on PATH, flow skills that read flow.config.json
via `jq ... // default` chains silently substitute HARDCODED defaults — wrong diff
base, wrong file patterns, wrong docs — and report green. `/flow:doctor` is worse:
its `jq -e ...; then PASS; else FAIL` conditionals take the FAIL branch on exit 127
(command-not-found), so a correct install reports "[FAIL] marketplace not registered".
Silent wrong-config beats a loud failure nowhere — every config-reading skill must
fail loud on missing jq instead of degrading.

Policy pinned here (three shapes):
  * BLOCKING skills — read flow.config.json and take ACTION (ship/PR/review/audit).
    Must carry the /flow:ship Step 1.5 guard: `command -v jq` → exit 1 + install hint.
  * doctor — CANNOT exit (its job is to diagnose a broken env). Must detect jq-absence
    and emit an honest `[SKIP]` for each jq-dependent check, NEVER a false `[FAIL]`.
  * workflow-help — read-ONLY display carve-out. Warns (exit 0), does not block.

Rather than restate each guard here — which would let the eval pass while the shipped
shell drifted (FB-0074 lesson) — this harness EXTRACTS the guard/check blocks from the
live SKILL.md files and RUNS them under a jq-stripped PATH, so the fixture and the
artifact cannot disagree.

Stdlib only, POSIX sh. Run:
    python3 plugins/flow/evals/run_jq_guard_evals.py
"""

from __future__ import annotations

import atexit
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SKILLS = HERE.parent / "skills"

# Carve-outs — skills that read config via jq but must NOT carry the blocking guard,
# each with the reason (silence is what let the divergence hide; an exemption is explicit).
CARVE_OUTS = {
    "doctor": "diagnoses a broken env — must [SKIP] on jq-absence, never exit or false-FAIL",
    "workflow-help": "read-only display of the loop + slot values — warns, takes no action",
}

# Reads flow.config.json via jq to scope/gate/write something, so a wrong default is a
# latent wrong-result. DERIVED below, not hand-listed, so a skill added later with an
# unguarded config read cannot pass CI in silence. A skill qualifies if it invokes jq
# AND references flow.config.json — this catches all three read forms in the codebase:
# direct (`jq -r '.x' flow.config.json`), piped (`cat flow.config.json | jq -r`), and
# via-var (`CFG=flow.config.json; jq -r ".$1" "$CFG"`).
_JQ_RE = re.compile(r"\bjq\s+-[re]\b")
_CONFIG_RE = re.compile(r"flow\.config\.json")

_failures: list[str] = []


def check(name, ok, detail=""):
    if ok:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}\n        {detail}")
        _failures.append(name)


def jq_using_skills() -> list:
    """Every skill whose body reads flow.config.json via jq — derived from disk."""
    found = []
    for skill_md in sorted(SKILLS.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        if _JQ_RE.search(text) and _CONFIG_RE.search(text):
            found.append((skill_md.parent.name, skill_md))
    return found


def is_fork(path: Path) -> bool:
    """True when the skill's frontmatter declares `context: fork`.

    Fork skills read config in LOAD-TIME `!`-context spans, not agent-run `sh` blocks, so
    a body `exit 1` cannot abort them — they fail loud by emitting a ROUTED warning payload
    (the ROOT-UNRESOLVED / root_error pattern), not by exiting. They are tested accordingly.
    """
    head = path.read_text(encoding="utf-8", errors="replace").split("\n---", 1)[0]
    return any(ln.strip() == "context: fork" for ln in head.splitlines())


# A `!`-context span: from the `!\`` opener to the next backtick. Matches both the inline
# form (`!`cmd`` on one line) and the multi-line form (fork skills) — span content never
# contains an inner backtick (documented FB-0010 constraint). These pre-execute at skill
# load; their stdout is injected as context.
_BANG_SPAN_RE = re.compile(r"!`(.*?)`", re.DOTALL)


def bang_spans_reading_config(text: str) -> list:
    return [s for s in _BANG_SPAN_RE.findall(text)
            if _JQ_RE.search(s) and _CONFIG_RE.search(s)]


def has_verdict_fail(out: str) -> bool:
    """A real [FAIL] verdict token at line start — not the word inside explanatory prose."""
    return any(ln.lstrip().startswith("[FAIL]") for ln in out.splitlines())


def git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, capture_output=True)
    (path / "flow.config.json").write_text('{"planPath":"x/plan.md"}\n', encoding="utf-8")
    (path / "app.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=path, capture_output=True,
    )
    return path


def fenced_after(text: str, heading_substr: str) -> str | None:
    """The first ```sh fenced block appearing after `heading_substr`."""
    idx = text.find(heading_substr)
    if idx == -1:
        return None
    m = re.search(r"```(?:sh|bash)\n(.*?)\n```", text[idx:], re.DOTALL)
    return m.group(1) if m else None


# The blocking guard: `MISSING=""` … through the `fi` that closes the missing-tool branch.
_GUARD_RE = re.compile(r"^(MISSING=\"\".*?^fi)$", re.MULTILINE | re.DOTALL)


def extract_guard(text: str) -> str | None:
    m = _GUARD_RE.search(text)
    return m.group(1) if m else None


_SHADOW_BIN_CACHE: dict[tuple[bool, bool], str] = {}


@atexit.register
def _cleanup_shadow_bins() -> None:
    for d in _SHADOW_BIN_CACHE.values():
        shutil.rmtree(d, ignore_errors=True)


def _shadow_bin(include_jq: bool, include_gh: bool) -> str:
    """A PATH dir with the tools the blocks need, jq/gh present per the flags.

    Only jq/gh presence is under test; everything else the shell needs (sed, git…) is
    symlinked from the real PATH. jq/gh are excluded to simulate the fresh-sandbox case.
    Built once per (jq, gh) combination (≤4 dirs for the whole run) and reused across
    every block; the dirs are removed at interpreter exit rather than leaking into $TMPDIR.
    """
    key = (include_jq, include_gh)
    cached = _SHADOW_BIN_CACHE.get(key)
    if cached is not None:
        return cached
    d = tempfile.mkdtemp(prefix="jqguard-bin-")
    tools = ["sh", "sed", "cat", "grep", "git", "tr", "head", "tail", "printf", "echo", "env"]
    if include_jq:
        tools.append("jq")
    if include_gh:
        tools.append("gh")
    for t in tools:
        real = shutil.which(t)
        if real:
            try:
                os.symlink(real, os.path.join(d, t))
            except FileExistsError:
                pass
    _SHADOW_BIN_CACHE[key] = d
    return d


def run_block(block: str, *, include_jq: bool, include_gh: bool,
              home: str | None = None, cwd: str | None = None) -> tuple[int, str]:
    bindir = _shadow_bin(include_jq, include_gh)
    env = {"PATH": bindir}
    if home is not None:
        env["HOME"] = home
    sh = shutil.which("sh") or "/bin/sh"
    proc = subprocess.run(
        [sh, "-c", block], env=env, cwd=cwd,
        capture_output=True, text=True, timeout=20,
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def main() -> int:
    print("jq-guard evals (jq-absence-handling-2026-06)")

    targets = jq_using_skills()
    names = {n for n, _ in targets}

    # Every declared carve-out must actually be a jq-using skill — a stale carve-out
    # (skill renamed/removed) would silently exempt nothing and rot.
    for c in CARVE_OUTS:
        check(f"carve-out '{c}' is a real jq-using skill",
              c in names, f"{c} not found among jq-using skills {sorted(names)}")

    blocking = [(n, p) for n, p in targets if n not in CARVE_OUTS and not is_fork(p)]
    forks = [(n, p) for n, p in targets if n not in CARVE_OUTS and is_fork(p)]
    check("found the expected jq-using-skill population (>= 10)",
          len(targets) >= 10, f"only {len(targets)} found: {sorted(names)}")

    # ---- Part A: INLINE blocking skills exit non-zero + install hint when jq is absent ----
    for name, path in blocking:
        text = path.read_text(encoding="utf-8")
        guard = extract_guard(text)
        if guard is None:
            check(f"{name}: has a `command -v jq` blocking guard", False,
                  "no `MISSING=\"\" … command -v jq … exit` guard found — add the "
                  "/flow:ship Step 1.5 shape (research §4)")
            continue
        check(f"{name}: guard actually probes jq", "command -v jq" in guard,
              "guard exists but never tests jq")
        # gh PRESENT, jq ABSENT ⇒ only jq is missing ⇒ must exit non-zero with a jq hint.
        rc, out = run_block(guard, include_jq=False, include_gh=True)
        check(f"{name}: jq-absent ⇒ exit non-zero (blocks)", rc != 0,
              f"exited 0 — degrades instead of blocking. output: {out!r}")
        check(f"{name}: jq-absent ⇒ prints an install hint mentioning jq",
              "jq" in out and ("install" in out.lower() or "jqlang" in out),
              f"no actionable jq install hint. output: {out!r}")

    # ---- Part A2: FORK skills route a jq-missing WARNING from their `!`-context spans ----
    # A body exit can't abort a load-time span, so these emit a routed signal the prose
    # treats as not-clean (like ROOT-UNRESOLVED). Run each config-reading span under stubbed
    # jq inside a real git repo (so ROOT resolves) and require a jq-missing token, NOT a
    # silent default payload.
    _JQ_MISSING_TOKENS = ("JQ-MISSING", "jq_error", "jq is not on PATH")
    with tempfile.TemporaryDirectory() as td:
        repo = git_repo(Path(td) / "repo")
        for name, path in forks:
            spans = bang_spans_reading_config(path.read_text(encoding="utf-8"))
            check(f"{name}: has config-reading `!` span(s) to guard", bool(spans),
                  "no jq+config `!` span found — extraction may have drifted")
            for si, span in enumerate(spans):
                rc, out = run_block(span, include_jq=False, include_gh=True, cwd=str(repo))
                check(f"{name}[span {si + 1}]: jq-absent ⇒ emits a routed jq-missing signal",
                      any(t in out for t in _JQ_MISSING_TOKENS),
                      f"span degraded silently instead of routing a warning. output: {out!r}")

    # ---- Part B: doctor NEVER false-FAILs when jq is absent (the observed bug) ----
    # Covers every jq-conditional whose false-branch is a verdict [FAIL]: Checks 1.1, 1.2
    # (settings.json), 2.2 (config parses), 2.5 (schema slot-count). Each must degrade to an
    # honest [SKIP], never a [FAIL], on a KNOWN-GOOD install with jq merely absent.
    doctor = (SKILLS / "doctor" / "SKILL.md").read_text(encoding="utf-8")
    c11 = fenced_after(doctor, "Check 1.1 —")
    c12 = fenced_after(doctor, "Check 1.2 —")
    c22 = fenced_after(doctor, "Check 2.2 —")
    c25 = fenced_after(doctor, "Check 2.5 —")
    check("doctor: Checks 1.1/1.2/2.2/2.5 blocks are extractable",
          all([c11, c12, c22, c25]), "could not locate one of the jq conditionals")
    if all([c11, c12, c22, c25]):
        with tempfile.TemporaryDirectory() as td:
            # A KNOWN-GOOD install: marketplace registered + flow@flow enabled + valid config.
            home = Path(td) / "home"
            (home / ".claude").mkdir(parents=True)
            (home / ".claude" / "settings.json").write_text(
                '{"extraKnownMarketplaces":{"flow":{"source":"by-dev-tools/flow"}},'
                '"enabledPlugins":{"flow@flow":true}}\n', encoding="utf-8")
            cwd = Path(td) / "proj"
            cwd.mkdir()
            (cwd / "flow.config.json").write_text('{"defaultBranch":"main"}\n', encoding="utf-8")
            # 1.1+1.2+2.2 run in the fake project (settings.json + valid flow.config.json).
            combined = c11 + "\n" + c12 + "\n" + c22
            rc, out = run_block(combined, include_jq=False, include_gh=True,
                                home=str(home), cwd=str(cwd))
            # 2.5 needs the real schema reachable, so run it at the repo root — the block's
            # `elif [ -f plugins/flow/schema/... ]` branch then resolves SCHEMA. Otherwise
            # SCHEMA is empty and the check SKIPs before the jq read, masking the pre-fix
            # false-FAIL this case exists to pin.
            repo_root = Path(__file__).resolve().parents[3]
            rc25, out25 = run_block(c25, include_jq=False, include_gh=True,
                                    cwd=str(repo_root))
            out_all = out + "\n" + out25
            check("doctor: jq-absent on a GOOD install ⇒ no false [FAIL] (Checks 1.1/1.2/2.2/2.5)",
                  not has_verdict_fail(out_all),
                  f"emitted a false FAIL on a correct install. output: {out_all!r}")
            check("doctor: jq-absent ⇒ emits an honest [SKIP] instead",
                  "[SKIP]" in out and "[SKIP]" in out25,
                  f"did not degrade to [SKIP]. output: {out_all!r}")

    # ---- Part C: workflow-help WARNS from a `!` span, does not block (read-only carve-out) ----
    wh = (SKILLS / "workflow-help" / "SKILL.md").read_text(encoding="utf-8")
    warn_spans = [s for s in _BANG_SPAN_RE.findall(wh) if "command -v jq" in s]
    check("workflow-help: has a jq-presence warn `!` span (read-only carve-out)",
          bool(warn_spans),
          "read-only display must still WARN when slot values are defaults, not silent")
    for si, span in enumerate(warn_spans):
        rc, out = run_block(span, include_jq=False, include_gh=True)
        check(f"workflow-help[span {si + 1}]: jq-absent ⇒ warns, does NOT block (exit 0)",
              rc == 0 and ("jq" in out.lower() and ("default" in out.lower() or "install" in out.lower())),
              f"a read-only help command must warn without blocking. rc={rc} output: {out!r}")

    # ---- Part D: staff-review's SPLIT — gh warn-only, jq blocking ----
    # Needs a REAL jq to isolate the gh half; without one the scenario can't be built,
    # so say so rather than run a jq-absent block that would falsely look like a pass.
    sr = (SKILLS / "staff-review" / "SKILL.md").read_text(encoding="utf-8")
    guard = extract_guard(sr)
    if guard is not None and shutil.which("jq"):
        # gh ABSENT but jq PRESENT ⇒ gh half is graceful ⇒ must NOT block.
        rc, out = run_block(guard, include_jq=True, include_gh=False)
        check("staff-review: gh-absent + jq-present ⇒ exit 0 (gh stays warn-only)",
              rc == 0, f"blocked on missing gh — gh must stay graceful. output: {out!r}")
    elif guard is not None:
        print("  SKIP  staff-review gh-split check — no real jq on PATH to build the scenario")

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} eval(s): {', '.join(_failures)}")
        return 1
    print("All jq-guard evals passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
