#!/usr/bin/env python3
"""Eval harness for the succession-brief check and the shared sensitivePaths predicate.

Two subjects, one harness, because they share a failure mode: **a rule that was
written down and then broken by the person who wrote it.**

`brief-check.py` (`skills/handoff/lib/`). Canonical §4.9 says every reference in
a succession brief must point somewhere the *successor* can reach — git hosting,
the backend API, or already-delivered-to-the-human — "never a path in the
outgoing sandbox," and records the dogfood where the first real succession did
exactly that anyway. Both halves are pinned here, because the negative alone is
satisfiable by writing nothing (`.claude/rules/general.md` § Consistency rule 3):

  §1  rejects an outgoing-sandbox path
  §2  requires a durable pointer AND the re-address instruction — so an empty or
      purely narrative brief FAILS rather than passing the prohibition trivially
  §3  malformed / empty / unreadable input

`sensitive_paths.py` (`plugins/flow/lib/`). One predicate, two readers, and they
do not naturally ask it the same question: the gate holds a changed-FILE list,
spawn holds owned-path GLOBS. FB-0079 is precisely about a shared slot with two
askers — "If the questions differ, the slot has two correct answers and the
consumer is forced to pick which consumer to answer wrongly." The resolution
here is to normalise spawn's input rather than overload the predicate, so:

  §4  the path entry point (gate's question)
  §5  the glob entry point (spawn's question), including globs matching nothing
  §6  the routing floor — a sensitive item cannot be routed down, whatever tier
      the agent picked — and the negative case, so the floor is not just "always
      true"
  §7  fail-safe direction: every degraded path classifies SENSITIVE
  §8  project-agnosticism of the defaults

**Deletion criterion (FB-0088):** delete with the two libs it pins — never
before them.

Stdlib only. No network. Run:
    python3 plugins/flow/evals/run_handoff_brief_evals.py
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
PLUGIN = HERE.parent
BRIEF_LIB = PLUGIN / "skills" / "handoff" / "lib" / "brief-check.py"
SP_LIB = PLUGIN / "lib" / "sensitive_paths.py"

_failures: list[str] = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")
        _failures.append(name)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


B = _load(BRIEF_LIB, "brief_check")
SP = _load(SP_LIB, "sensitive_paths")
TMP = Path(tempfile.mkdtemp(prefix="flow-handoff-evals-"))

GOOD_BRIEF = """# Succession brief — orchestrator

## Read first
The canonical plan and CLAUDE.md in the repo; see https://example.invalid/org/repo for open PRs.

## Live workers
Re-derive them: run the backend's listWorkers verb. Do not trust any list written here.

## In flight
- #12 waiting at its plan gate.

## Your first action
Re-address the ping channel: broadcast your own session id to every live worker, one message each.
The vendor report was already delivered to the human.
"""

print("\n§1  rejects references the successor cannot reach")
for bad, label in (
    ("/home/agent/workspace/report.md", "a /home path"),
    ("/Users/someone/notes.md", "a /Users path"),
    ("~/scratch/output.txt", "a ~-relative path"),
    ("/tmp/generated-report.html", "a /tmp path"),
):
    text = GOOD_BRIEF + f"\nThe report is at {bad}\n"
    r = B.check(text)
    check(f"rejects {label}", not r["ok"]
          and any(f["id"] == "sandbox-local-reference" for f in r["findings"]), json.dumps(r["findings"])[:200])
r = B.check(GOOD_BRIEF)
check("a fully-reachable brief passes", r["ok"], json.dumps(r["findings"])[:300])
check("and it reports WHICH durable pointers it found", len(r["durable_references"]) >= 2)
# Not over-eager: a repo-relative path is fine, it resolves in the successor's checkout.
r = B.check(GOOD_BRIEF + "\nSee dev-docs/plan.md and plugins/flow/skills/gate/SKILL.md.\n")
check("repo-relative paths are NOT rejected (they resolve in any checkout)", r["ok"],
      json.dumps(r["findings"])[:200])

print("\n§2  the positive half — a prohibition alone is satisfiable by writing nothing")
r = B.check("# Succession brief\n\nGood luck.\n")
check("a brief with no sandbox paths but no durable pointer FAILS", not r["ok"])
check("  ... naming the missing durable reference",
      any(f["id"] == "no-durable-reference" for f in r["findings"]))
check("  ... and the missing re-address instruction",
      any(f["id"] == "missing-readdress-instruction" for f in r["findings"]))
no_readdress = GOOD_BRIEF.replace(
    "Re-address the ping channel: broadcast your own session id to every live worker, one message each.",
    "Get started on the queue.")
r = B.check(no_readdress)
check("a brief missing ONLY the re-address instruction still fails",
      not r["ok"] and [f["id"] for f in r["findings"]] == ["missing-readdress-instruction"],
      json.dumps([f["id"] for f in r["findings"]]))
check("  ... and explains why silence is the symptom",
      "silence" in next(f["detail"] for f in r["findings"] if f["id"] == "missing-readdress-instruction"))

print("\n§3  malformed / empty / unreadable")
r = B.check("")
check("empty brief fails", not r["ok"] and any(f["id"] == "empty-brief" for f in r["findings"]))
r = B.check("   \n\n\t\n")
check("whitespace-only brief fails", not r["ok"])
proc = subprocess.run([sys.executable, str(BRIEF_LIB), "--brief-file", str(TMP / "nope.md")],
                      capture_output=True, text=True)
check("unreadable brief ⇒ exit 1, treated as REJECT, no traceback",
      proc.returncode == 1 and "Traceback" not in proc.stderr, proc.stderr[:200])
good = TMP / "good.md"; good.write_text(GOOD_BRIEF, encoding="utf-8")
proc = subprocess.run([sys.executable, str(BRIEF_LIB), "--brief-file", str(good)],
                      capture_output=True, text=True)
check("CLI exit 0 on a good brief", proc.returncode == 0, proc.stderr[:200])

print("\n§4  sensitivePaths — the path entry point (gate's question)")
DEF = SP.DEFAULT_SENSITIVE_PATHS
for path, should in (
    ("src/auth/login.ts", True),
    ("auth/login.ts", True),                       # repo-root, the zero-segment `**/` case
    ("db/migrations/0001_init.sql", True),
    (".github/workflows/ci.yml", True),
    ("plugins/flow/schema/flow.config.schema.json", True),
    (".env", True),
    ("config/.env.production", True),
    ("README.md", False),
    ("src/components/Button.tsx", False),
    ("docs/authoring-guide.md", False),            # 'auth' as a substring must NOT match
    ("src/author.ts", False),
):
    r = SP.classify([path], DEF)
    check(f"{path} ⇒ sensitive={should}", r["sensitive"] is should, json.dumps(r["matches"]))

print("\n§5  the glob entry point (spawn's question)")
tracked = ["README.md", "src/auth/login.ts", "src/ui/Button.tsx",
           "db/migrations/0001.sql", "docs/guide.md"]
expanded, empty = SP.expand_globs(["src/**"], tracked)
check("a glob expands to the tracked files it covers", set(expanded) == {"src/auth/login.ts", "src/ui/Button.tsx"},
      str(expanded))
check("a glob matching everything under it reports no empties", empty == [])
expanded, empty = SP.expand_globs(["does/not/exist/**"], tracked)
check("a glob matching nothing is REPORTED, not silently dropped", expanded == [] and empty == ["does/not/exist/**"])
expanded, _ = SP.expand_globs(["docs/**", "src/ui/**"], tracked)
check("a non-sensitive owned-glob set stays non-sensitive",
      SP.classify(expanded, DEF)["sensitive"] is False, str(expanded))

print("\n§6  the routing floor — and its negative, so it is not merely always-true")
expanded, _ = SP.expand_globs(["src/auth/**"], tracked)
check("FLOOR FIRES: an owned-glob set covering auth is sensitive ⇒ top tier, no exceptions",
      SP.classify(expanded, DEF)["sensitive"] is True)
expanded, _ = SP.expand_globs(["db/**"], tracked)
check("FLOOR FIRES: a migrations-owning worker is sensitive", SP.classify(expanded, DEF)["sensitive"] is True)
expanded, _ = SP.expand_globs(["docs/**"], tracked)
check("FLOOR DOES NOT FIRE for docs — a floor that always fires is not a floor, "
      "it is a ban on routing down at all",
      SP.classify(expanded, DEF)["sensitive"] is False)
# Both readers must reach the SAME verdict for the same underlying files — that is
# the whole one-definition-two-readers claim, asserted rather than asserted-in-prose.
files_verdict = SP.classify(["src/auth/login.ts"], DEF)["sensitive"]
globs_verdict = SP.classify(SP.expand_globs(["src/auth/**"], tracked)[0], DEF)["sensitive"]
check("the two entry points agree on the same underlying file", files_verdict == globs_verdict is True)
spawn_skill = (PLUGIN / "skills" / "spawn" / "SKILL.md").read_text(encoding="utf-8")
check("spawn uses the GLOB entry point, not the file one", "--globs-file" in spawn_skill)
gate_src = (PLUGIN / "skills" / "gate" / "lib" / "gate-classify.py").read_text(encoding="utf-8")
check("gate imports the shared predicate rather than copying the globs",
      "import sensitive_paths" in gate_src and "**/auth/**" not in gate_src)

print("\n§6a  the greenfield case — an owned glob matching nothing is NOT 'nothing sensitive'")
# The likeliest way this predicate is asked about one-way-door work: a worker
# dispatched to CREATE migrations or auth owns a glob with no matches yet. Answering
# `false` there was the module's one fail-OPEN, and /flow:spawn's floor reads the
# machine-readable field, not the stderr line.
import subprocess as _sp, tempfile as _tf, os as _os
_repo = Path(_tf.mkdtemp(prefix="flow-greenfield-"))
_sp.run(["git", "init", "-q", str(_repo)], check=False)
(_repo / "README.md").write_text("hi\n", encoding="utf-8")
_sp.run(["git", "-C", str(_repo), "add", "-A"], check=False)
_sp.run(["git", "-C", str(_repo), "-c", "user.email=e@x", "-c", "user.name=n",
         "commit", "-qm", "init"], check=False)
(_repo / "globs.txt").write_text("db/migrations/**\nsrc/auth/**\n", encoding="utf-8")
_r = _sp.run([sys.executable, str(SP_LIB), "--globs-file", "globs.txt"],
             cwd=str(_repo), capture_output=True, text=True)
_out = json.loads(_r.stdout)
check("a worker owning db/migrations/** + src/auth/** in a repo with NEITHER yet ⇒ SENSITIVE",
      _out["sensitive"] is True, json.dumps(_out))
check("  ... and says why, naming the unmatched globs",
      "match no tracked file yet" in _out.get("reason", "")
      and "db/migrations/**" in _out.get("reason", ""), _out.get("reason", ""))
check("  ... and still reports which globs matched nothing",
      sorted(_out["globs_matching_nothing"]) == ["db/migrations/**", "src/auth/**"])
check("  ... and names which of those are sensitive-SHAPED (not merely absent)",
      sorted(_out["globs_matching_nothing_but_sensitive_shaped"]) == ["db/migrations/**", "src/auth/**"])

# The other half, and the one the coverage audit demanded: greenfield is NOT a blanket
# escalation. Flooring every not-yet-existing glob would be the over-spending failure
# the routing policy names as explicitly as under-dispatching.
(_repo / "globs.txt").write_text("docs/guides/**\nsrc/ui/**\n", encoding="utf-8")
_r = _sp.run([sys.executable, str(SP_LIB), "--globs-file", "globs.txt"],
             cwd=str(_repo), capture_output=True, text=True)
_o = json.loads(_r.stdout)
check("greenfield globs that name NO sensitive area do NOT escalate "
      "(a floor that fires on all new work is a ban, not a floor)",
      _o["sensitive"] is False, _r.stdout[:200])
check("  ... and they are still reported as matching nothing, so the caller can see why",
      sorted(_o["globs_matching_nothing"]) == ["docs/guides/**", "src/ui/**"]
      and _o["globs_matching_nothing_but_sensitive_shaped"] == [])

# The predicate itself, both directions, so the rule is pinned independently of the CLI.
# BARE-DIRECTORY forms are in this table deliberately. Every case here previously ended
# in `/**` or a file wildcard, which is why a fail-open on the bare form survived a
# coverage pass: the fixtures pinned one spelling of the input, and the bug lived in the
# other. `src/auth` and `src/auth/**` name the same scope, and the bare form is the one a
# human writes by hand.
for _g, _want in (("db/migrations/**", True), ("src/auth/**", True), (".github/workflows/**", True),
                  ("api/schema/**", True), ("config/*.sql", True),
                  ("src/auth", True), ("db/migrations", True), ("secrets", True),
                  (".github/workflows", True), ("src/auth/", True),
                  ("**", True), ("*", True), ("", True),
                  ("docs/**", False), ("src/ui/**", False), ("notes/*.md", False),
                  ("docs", False), ("src/ui", False)):
    check(f"glob_names_sensitive_area({_g!r}) == {_want}",
          SP.glob_names_sensitive_area(_g, DEF) is _want)
# The stated residual, pinned so it is a decision on the record rather than a surprise:
# a broad glob answers False, and the plan gate's stakes axis is what catches it later.
# The extensional side had the same blindness: a bare directory is not itself a tracked
# path, so matching it literally found nothing and reported the glob as empty.
_tracked = ["src/auth/login.ts", "src/ui/Button.tsx", "docs/guide.md"]
_exp, _empty = SP.expand_globs(["src/auth"], _tracked)
check("a bare-directory glob expands to the files under it (not to nothing)",
      _exp == ["src/auth/login.ts"] and _empty == [], f"{_exp} {_empty}")

check("a broad `src/**` answers False — the documented residual, caught downstream by "
      "the gate's stakes axis over the ACTUAL changed files",
      SP.glob_names_sensitive_area("src/**", DEF) is False)
check("  ... and that same worker's actual auth file IS caught by the path entry point",
      SP.classify(["src/auth/login.ts"], DEF)["sensitive"] is True)
(_repo / "globs.txt").write_text("*.md\n", encoding="utf-8")
_r = _sp.run([sys.executable, str(SP_LIB), "--globs-file", "globs.txt"],
             cwd=str(_repo), capture_output=True, text=True)
check("a glob that DOES match, over non-sensitive files, is still not sensitive "
      "(the escalation is targeted, not blanket)",
      json.loads(_r.stdout)["sensitive"] is False, _r.stdout)

print("\n§6b  EMPTY input is 'asked about nothing', not 'nothing is sensitive'")
# Reachable in production: /flow:spawn's template writes the glob file with a printf
# whose substitution may not have happened, yielding an empty file. A `false` there
# routes a worker with UNDECLARED scope down a tier.
_empty = TMP / "empty.txt"; _empty.write_text("\n  \n", encoding="utf-8")
for _flag in ("--globs-file", "--files-file"):
    _r = _sp.run([sys.executable, str(SP_LIB), _flag, str(_empty)], capture_output=True, text=True)
    _o = json.loads(_r.stdout)
    check(f"an empty {_flag} ⇒ SENSITIVE, not a clean pass", _o["sensitive"] is True, _r.stdout[:200])
    check(f"  ... and says it was asked about nothing ({_flag})",
          "asked about nothing" in _o.get("reason", "") and "⚠️" in _r.stderr)

print("\n§6c  the durable-pointer POSITIVE is not satisfied by the template's own boilerplate")
# The shipped brief template hardcodes "Re-derive: run the backend's listWorkers verb",
# so while `re-derive`/`listWorkers`/`dispatchBackend` counted as durable pointers, an
# unfilled skeleton passed clean — the positive half had the same two-worlds defect the
# negative half is paired to fix.
SKELETON = """# Succession brief — orchestrator

## Read first

## Live workers
Re-derive: run the backend's listWorkers verb. Do NOT trust any list written here.

## In flight

## Your first action
Re-address the ping channel: broadcast your own session id to every live worker.
"""
_r = B.check(SKELETON)
check("the shipped skeleton with every slot UNFILLED fails", not _r["ok"],
      json.dumps(_r["findings"])[:200])
check("  ... specifically for having no durable pointer",
      any(f["id"] == "no-durable-reference" for f in _r["findings"]))
check("a runnable instruction is not counted as a pointer",
      B.check("re-derive with listWorkers and dispatchBackend")["durable_references"] == [])
# PAIRED: the same skeleton plus ONE real pointer passes. Without this half, the check
# could be satisfied by rejecting every brief.
_r2 = B.check(SKELETON.replace("## In flight\n", "## In flight\n- #12 at its plan gate: https://example.invalid/org/repo/pull/12\n"))
check("  ... and the SAME skeleton plus one real pointer is accepted", _r2["ok"], json.dumps(_r2["findings"])[:200])

print("\n§7  fail-safe direction — every degraded path classifies SENSITIVE")
# Pattern translation escapes everything that is not a wildcard, so odd pattern
# text is matched LITERALLY rather than crashing or silently matching nothing.
# Pinned as the real property, in place of an unreachable "failed to compile"
# fallback that would have read like protection while never firing (FB-0104: a
# checker's own fixtures must exercise every branch — a branch no fixture can
# reach is a branch that should not exist).
for pat in ("[unclosed", "a(b", "+++", "a{2,}", "\\", "(?i)secret"):
    try:
        r = SP.classify(["README.md"], [pat])
        check(f"pattern {pat!r} is handled literally, not crashed on", r["sensitive"] is False)
    except Exception as exc:  # noqa: BLE001
        check(f"pattern {pat!r} is handled literally, not crashed on", False, repr(exc))
check("a literal-matching pattern still matches its literal",
      SP.classify(["a(b"], ["a(b"])["sensitive"] is True)
print("\n§7a  the defaults are a FLOOR — a consumer list MERGES, it never replaces")
# The one silent-narrowing path in a module whose thesis is that every uncertain path
# escalates. A consumer adding one project entry must not lose .env/auth/migrations/CI.
_narrow = TMP / "narrow.json"
_narrow.write_text(json.dumps({"sensitivePaths": ["my/own/gate/**"]}), encoding="utf-8")
_pats, _src, _w = SP.load_patterns(str(_narrow))
check("a one-entry consumer list still carries every default",
      all(d in _pats for d in DEF), f"missing: {[d for d in DEF if d not in _pats]}")
check("  ... and the consumer's own entry too", "my/own/gate/**" in _pats)
check("  ... and the source says so, so the caller can tell", _src == "config+defaults")
check("a narrow consumer list does NOT drop auth coverage (the silent-narrowing bug)",
      SP.classify(["src/auth/login.ts"], _pats)["sensitive"] is True)
check("  ... nor migrations, nor .env, nor CI",
      all(SP.classify([f], _pats)["sensitive"] is True
          for f in ("db/migrations/1.sql", ".env", ".github/workflows/ci.yml")))
check("the consumer's own entry is matched", SP.classify(["my/own/gate/x.py"], _pats)["sensitive"] is True)
_dup = TMP / "dup.json"
_dup.write_text(json.dumps({"sensitivePaths": ["**/auth/**", "extra/**"]}), encoding="utf-8")
_pats2, _, _ = SP.load_patterns(str(_dup))
check("a consumer restating a default does not duplicate it",
      _pats2.count("**/auth/**") == 1 and "extra/**" in _pats2)

cfgp = TMP / "empty-slot.json"; cfgp.write_text(json.dumps({"sensitivePaths": []}), encoding="utf-8")
pats, src_, warns = SP.load_patterns(str(cfgp))
check("an EMPTY sensitivePaths list falls back to defaults with a warning, rather than "
      "classifying every diff low-stakes",
      pats == DEF and src_ == "default-after-error" and warns and "⚠️" in warns[0])
cfgp = TMP / "bad-slot.json"; cfgp.write_text(json.dumps({"sensitivePaths": "auth"}), encoding="utf-8")
pats, src_, warns = SP.load_patterns(str(cfgp))
check("a non-list sensitivePaths falls back loudly", pats == DEF and warns and "⚠️" in warns[0])
pats, src_, warns = SP.load_patterns(str(TMP / "absent.json"))
check("an ABSENT config is a silent, documented default (not a warning)",
      pats == DEF and src_ == "default" and warns == [])
check("  ... and 'default' is distinguishable from 'config+defaults', so the audit line "
      "can say which policy a verdict was reached under",
      SP.load_patterns(str(_narrow))[1] != src_)
proc = subprocess.run([sys.executable, str(SP_LIB), "--files-file", str(TMP / "nope.txt")],
                      capture_output=True, text=True)
check("an unreadable file list ⇒ sensitive:true, with a warning",
      json.loads(proc.stdout)["sensitive"] is True and "⚠️" in proc.stderr)

print("\n§7b  the policy protects its own surface, and refuses pathological patterns")
# Without these two defaults the diff that WEAKENS the gate is itself low-stakes and
# therefore auto-approvable: one green plan gate could edit the list deciding which
# plan gates are green.
for _f in ("flow.config.json", "sub/project/flow.config.json", ".flow/usage.tsv"):
    check(f"{_f} is sensitive by default (the policy's own surface)",
          SP.classify([_f], DEF)["sensitive"] is True)
# ReDoS: repo-controlled globs reach the matcher. Measured non-terminating before the
# bound; a gate that hangs never returns a verdict, which is worse than either answer.
import time as _time
for _bad, _label in (("*a*a*a*a*a*a*a*a*a*a*a*a*b", "nested-quantifier"),
                     ("**/" * 10 + "x", "repeated **/")):
    _t0 = _time.time()
    _r = SP.classify(["a/" * 30 + "z.txt"], [_bad])
    _el = _time.time() - _t0
    check(f"a {_label} pattern is refused in bounded time (<1s)", _el < 1.0, f"{_el:.2f}s")
    check(f"  ... and refusing classifies SENSITIVE, naming the pattern ({_label})",
          _r["sensitive"] is True and _r.get("unsafe_patterns"), json.dumps(_r)[:160])
# Pin the BUDGET, not the constant. `_MAX_WILDCARDS` was 12 and measured 54.9s on a
# 40-char path — the bound admitted the exact shape it exists to refuse, because it was
# set by eyeballing rather than by measuring. A wall-clock assertion cannot drift.
_worst = "*a" * SP._MAX_WILDCARDS + "*b"
_t0 = _time.time(); SP.classify(["a" * 60], [_worst]); _el = _time.time() - _t0
check(f"the WORST pattern the bounds admit ({SP._MAX_WILDCARDS} wildcards) matches in "
      f"under 0.5s — the budget, not the constant", _el < 0.5, f"{_el:.2f}s")
check("every shipped default is comfortably inside the wildcard bound",
      max(p.count("*") + p.count("?") for p in DEF) <= SP._MAX_WILDCARDS - 2)

check("an ordinary pattern is NOT refused as pathological",
      "unsafe_patterns" not in SP.classify(["src/auth/x.ts"], DEF))
check("collapsing repeated `**/` preserves meaning",
      SP.classify(["a/b/c/x.sql"], ["**/**/**/*.sql"])["sensitive"] is True)

print("\n§8  the defaults are project-agnostic")
blob = json.dumps(DEF)
# `.flow/` and `flow.config.json` ARE named, deliberately: they exist in every flow
# consumer, so they are generic to the plugin rather than specific to THIS project.
# What must not appear is a path only flow-the-repo has.
for tok in ("plugins/flow", "manifest-triage", "skip-audit", "verify-build", "pr-coherence", "dev-docs"):
    check(f"defaults name no flow-specific path {tok!r} (that belongs in a project's own config)",
          tok not in blob)
check("defaults still cover the universal one-way-door classes",
      all(any(k in p for p in DEF) for k in ("secrets", "auth", "migrations", "schema", "workflows")))
check("defaults are non-empty", len(DEF) >= 10)

print()
if _failures:
    print(f"FAILED: {len(_failures)} check(s)")
    for f in _failures:
        print(f"  - {f}")
    sys.exit(1)
print("All handoff-brief + sensitivePaths eval checks passed.")
