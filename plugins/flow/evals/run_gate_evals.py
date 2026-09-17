#!/usr/bin/env python3
"""Eval harness for the §4.8 gate-delegation policy (`skills/gate/lib/gate-classify.py`).

The bug class it pins: **a gate that fails silently.** Every other reviewer in
this repo fails loudly — a wrong verdict shows up as a red check or a manifest
entry. This one does not. An axis mis-read as green auto-approves a plan that
should have escalated, and the only symptom is that a human who expected to be
asked never was. There is no downstream artifact to notice.

So the combination rule gets a truth table rather than a smoke test:

  §1  the four-axis plan gate — all-green, every single-red, and every
      *undeclared* axis (an unknown must never default to approve)
  §2  the prototype carve-out, which overrides four green axes
  §3  the merge gate's three branches AND the crawl-rung pin, asserted
      positively (the classification is still produced) as well as negatively
      (the verdict is always `human`)
  §4  the never-merge invariant, PAIRED with the positive assertion of the
      escalation path it protects — `.claude/rules/general.md` § Consistency
      rule 3: a prohibition alone passes in two opposite worlds, the contract
      honored or the contract deleted
  §5  ships-or-paperwork (rule 7 / FB-0106), including the unknown⇒ships
      asymmetry
  §6  escalation format — the FB-0090 triple, the FB-0092 rule-5 return
      address, and refusal when either is missing
  §7  malformed / empty input degrades without crashing
  §8  the suite's frontmatter contract: four skills, all agent-invocable
  §9  the fourteen deletion criteria (FB-0088 corollary (b)), enumerated
  §10 registration + CI-wiring self-guards

Stdlib only. No network. Run:
    python3 plugins/flow/evals/run_gate_evals.py
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
REPO = PLUGIN.parent.parent
GATE_LIB = PLUGIN / "skills" / "gate" / "lib" / "gate-classify.py"
SUITE = ("orchestrate", "spawn", "handoff", "gate")

_failures: list[str] = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")
        _failures.append(name)


def _mod():
    spec = importlib.util.spec_from_file_location("gate_classify", GATE_LIB)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


G = _mod()

# A config with NO sensitivePaths slot, so §1 exercises the documented defaults
# rather than whatever the host repo happens to configure. An eval that reads the
# live config would change meaning when the config does.
_TMP = tempfile.mkdtemp(prefix="flow-gate-evals-")
PLAIN_CFG = Path(_TMP) / "flow.config.json"
PLAIN_CFG.write_text("{}", encoding="utf-8")

GREEN = dict(
    reversible="yes", confidence="high", critique_verdict="approved", taste="low",
    config_path=str(PLAIN_CFG),
)
SAFE_FILES = ["README.md", "docs/guide.md"]


print("\n§1  four-axis plan gate — all-green, each single-red, each undeclared")
r = G.classify_plan(SAFE_FILES, **GREEN)
check("all four axes green ⇒ approve", r["verdict"] == "approve", json.dumps(r["red_axes"]))
check("all-green audit line says so", "all four axes green" in r["audit_line"], r["audit_line"])

r = G.classify_plan(["src/auth/session.ts"], **GREEN)
check("red stakes ⇒ escalate", r["verdict"] == "escalate" and r["red_axes"] == ["stakes"])
check("red stakes names the matched pattern", "**/auth/**" in r["axes"]["stakes"]["why"])

for axis, kw in (
    ("reversible", dict(reversible="no")),
    ("confidence", dict(confidence="medium")),
    ("confidence", dict(critique_verdict="redirect")),
    ("taste", dict(taste="high")),
):
    args = dict(GREEN); args.update(kw)
    r = G.classify_plan(SAFE_FILES, **args)
    check(f"red {axis} via {list(kw)[0]}={list(kw.values())[0]} ⇒ escalate",
          r["verdict"] == "escalate" and axis in r["red_axes"], json.dumps(r["red_axes"]))

# The load-bearing one: an axis nobody declared must NEVER read as green.
for axis, kw in (
    ("reversible", dict(reversible=None)),
    ("confidence", dict(confidence=None)),
    ("confidence", dict(critique_verdict=None)),
    ("taste", dict(taste=None)),
    ("reversible", dict(reversible="")),
    ("taste", dict(taste="probably fine")),
):
    args = dict(GREEN); args.update(kw)
    r = G.classify_plan(SAFE_FILES, **args)
    check(f"UNDECLARED {axis} ({list(kw)[0]}={list(kw.values())[0]!r}) ⇒ escalate, not approve",
          r["verdict"] == "escalate" and r["axes"][axis]["state"] == "unknown",
          json.dumps(r["axes"][axis]))

r = G.classify_plan([], **GREEN)
check("empty changed-file list ⇒ stakes unknown ⇒ escalate (absence is not proof of safety)",
      r["verdict"] == "escalate" and r["axes"]["stakes"]["state"] == "unknown")

print("\n§2  the prototype carve-out overrides four green axes")
r = G.classify_plan(SAFE_FILES, prototype_attached=True, **GREEN)
check("prototype attached ⇒ escalate despite all-green", r["verdict"] == "escalate")
check("carve-out is named in the result", bool(r["carve_out"]) and "prototype" in r["carve_out"])
check("carve-out reaches the audit line", "prototype" in r["audit_line"])

print("\n§3  merge gate — three branches classified, verdict pinned to human")
cases = [
    (dict(diff_class="docs-only"), "docs-only", True),
    (dict(diff_class="code", verify_verdict="pass", confidence="extremely-high",
          plan_axes_green="yes"), "verified-code", True),
    (dict(diff_class="code", verify_verdict="unknown", confidence="extremely-high",
          plan_axes_green="yes"), "anything-else", False),
    (dict(diff_class="code", verify_verdict="skipped", confidence="high",
          plan_axes_green="yes"), "anything-else", False),
    (dict(diff_class="code", verify_verdict="pass", confidence="medium",
          plan_axes_green="yes"), "anything-else", False),
    (dict(diff_class="code", verify_verdict="pass", confidence="extremely-high",
          plan_axes_green="no"), "anything-else", False),
    (dict(), "anything-else", False),
]
for kw, branch, delegable in cases:
    r = G.classify_merge(config_path=str(PLAIN_CFG), **kw)
    # NEGATIVE half — never anything but human.
    check(f"merge {branch} ({kw or 'no inputs'}) ⇒ verdict human", r["verdict"] == "human", json.dumps(r))
    # POSITIVE half — the classification is still produced. Without this, a stub
    # returning {"verdict": "human"} and nothing else would pass every check above.
    check(f"merge {branch} still classifies + reports delegability",
          r["classification"] == branch and r["would_delegate_at_walk_rung"] is delegable
          and bool(r["why"]) and bool(r["audit_line"]),
          json.dumps({k: r.get(k) for k in ("classification", "would_delegate_at_walk_rung", "why")}))

check("rollout rung is crawl", G.ROLLOUT_RUNG == "crawl")
src = GATE_LIB.read_text(encoding="utf-8")
check("no input can flip the merge verdict (single literal assignment)",
      src.count('"verdict": "human"') == 1)

print("\n§4  never-merge — negative AND the positive it protects (general.md rule 3)")
gate_skill = (PLUGIN / "skills" / "gate" / "SKILL.md").read_text(encoding="utf-8")
for tok in ("gh pr merge", "gh api", "--squash", "--rebase-merge", "pulls/", "/merge\n"):
    check(f"lib contains no merge call token {tok!r}", tok not in src)
    check(f"skill contains no merge call token {tok!r}", tok not in gate_skill)
# The pairing. Deleting the escalation machinery would satisfy every line above.
check("POSITIVE: the escalation formatter exists and is reachable",
      hasattr(G, "format_escalation") and "format" in src and "--decision-file" in src)
check("POSITIVE: the plan classifier exists and can return both verdicts",
      hasattr(G, "classify_plan")
      and G.classify_plan(SAFE_FILES, **GREEN)["verdict"] == "approve"
      and G.classify_plan(["db/migrations/001.sql"], **GREEN)["verdict"] == "escalate")
check("POSITIVE: the skill still documents the merge gate it refuses to act on",
      "merge gate" in gate_skill.lower() and "human" in gate_skill)

print("\n§5  ships-or-paperwork (rule 7 / FB-0106)")
r = G.ships_or_paperwork("no", "no", "no")
check("no behavior/surface/gate change ⇒ paperwork ⇒ resolve yourself",
      r["classification"] == "paperwork" and "RESOLVE IT YOURSELF" in r["action"])
for kw in (("yes", "no", "no"), ("no", "yes", "no"), ("no", "no", "yes")):
    check(f"any yes {kw} ⇒ ships", G.ships_or_paperwork(*kw)["classification"] == "ships")
check("UNKNOWN ⇒ ships (FB-0106 asymmetry: a wrong 'ships' costs a round trip, "
      "a wrong 'paperwork' is only catchable later)",
      G.ships_or_paperwork(None, "no", "no")["classification"] == "ships")

print("\n§6  escalation format — FB-0090 triple + FB-0092 return address")
base = dict(title="Pick A or B", recommendation="A", confidence="high",
            justification="B needs a migration", originating_session="sess-1")
out = G.format_escalation(base)
for label in ("**Recommendation:**", "**Confidence:**", "**Why:**"):
    check(f"rendered escalation carries {label}", label in out)
check("rendered escalation names the return address", "sess-1" in out)
check("rendered escalation promises the relay, not a workspace visit",
      "never need to open its workspace" in out)
for missing in ("recommendation", "confidence", "justification"):
    d = dict(base); d[missing] = ""
    check(f"missing {missing} ⇒ BLOCKER, not a best-effort render",
          "BLOCKER" in G.format_escalation(d) and missing in G.format_escalation(d))
d = dict(base); d["originating_session"] = ""
check("missing originating_session ⇒ BLOCKER (rule 5's return leg has nowhere to go)",
      "BLOCKER" in G.format_escalation(d) and "rule 5" in G.format_escalation(d))
d = dict(base); d["confidence"] = "pretty sure"
check("unparseable confidence ⇒ BLOCKER", "BLOCKER" in G.format_escalation(d))
d = dict(base); d["other_threads"] = ["#1 at gate", "#2 shipping"]
out = G.format_escalation(d)
check("other threads render as ONE line, not a second ask (rule 4)",
      "Also live (2)" in out and out.count("**Recommendation:**") == 1)

print("\n§7  malformed input degrades without crashing")
for bad in ({}, {"recommendation": None}, {"confidence": 3}):
    try:
        check(f"format({bad}) returns a string rather than raising",
              isinstance(G.format_escalation(bad), str))
    except Exception as exc:  # noqa: BLE001
        check(f"format({bad}) returns a string rather than raising", False, repr(exc))
try:
    r = G.classify_plan(["x"], reversible=object(), confidence=[], taste={},
                        critique_verdict=7, config_path=str(PLAIN_CFG))
    check("classify_plan survives nonsense axis types ⇒ escalate", r["verdict"] == "escalate")
except Exception as exc:  # noqa: BLE001
    check("classify_plan survives nonsense axis types ⇒ escalate", False, repr(exc))
missing_cfg = Path(_TMP) / "nope.json"
r = G.classify_plan(SAFE_FILES, **{**GREEN, "config_path": str(missing_cfg)})
check("absent config ⇒ documented defaults, still classifies", r["pattern_source"] == "default")
proc = subprocess.run([sys.executable, str(GATE_LIB), "format", "--decision-file", str(missing_cfg)],
                      capture_output=True, text=True)
check("CLI format with an unreadable decision-file exits non-zero, does not traceback",
      proc.returncode != 0 and "Traceback" not in proc.stderr, proc.stderr[:200])

print("\n§8  the suite's frontmatter contract")
for name in SUITE:
    sk = PLUGIN / "skills" / name / "SKILL.md"
    check(f"{name}/SKILL.md exists", sk.is_file())
    if not sk.is_file():
        continue
    txt = sk.read_text(encoding="utf-8")
    fm = txt.split("---")[1] if txt.startswith("---") else ""
    check(f"{name} is AGENT-INVOCABLE (disable-model-invocation: false)",
          "disable-model-invocation: false" in fm,
          "§4.10 requires it — a spawned worker runs these with no human in the loop")
    check(f"{name} declares allowed-tools", "allowed-tools:" in fm)
    # Every skill body runs python3 through Bash; a missing Bash tool is the
    # inert-gate shape (a skill whose steps cannot execute).
    if "```sh" in txt:
        check(f"{name} declares Bash (its body has shell blocks)", "Bash" in fm)

print("\n§9  fourteen deletion criteria, enumerated (FB-0088 corollary (b))")
ARTIFACTS = [
    PLUGIN / "skills" / "orchestrate" / "SKILL.md",
    PLUGIN / "skills" / "spawn" / "SKILL.md",
    PLUGIN / "skills" / "handoff" / "SKILL.md",
    PLUGIN / "skills" / "gate" / "SKILL.md",
    PLUGIN / "lib" / "sensitive_paths.py",
    PLUGIN / "skills" / "gate" / "lib" / "gate-classify.py",
    PLUGIN / "skills" / "spawn" / "lib" / "dispatch-backend.py",
    PLUGIN / "skills" / "handoff" / "lib" / "brief-check.py",
    HERE / "run_gate_evals.py",
    HERE / "run_dispatch_backend_evals.py",
    HERE / "run_handoff_brief_evals.py",
]
for f in ARTIFACTS:
    check(f"{f.name} states a deletion criterion",
          f.is_file() and "eletion criterion" in f.read_text(encoding="utf-8"))
schema = json.loads((PLUGIN / "schema" / "flow.config.schema.json").read_text(encoding="utf-8"))
for slot in ("dispatchBackend", "sensitivePaths"):
    check(f"schema slot {slot} states a deletion criterion",
          "eletion criterion" in schema["properties"][slot]["description"])
doctor = (PLUGIN / "skills" / "doctor" / "SKILL.md").read_text(encoding="utf-8")
check("doctor's adapter check states a deletion criterion",
      "dispatchBackend" in doctor and "eletion criterion" in doctor)
check("the enumerated list is 14 long, matching the plan's table",
      len(ARTIFACTS) + 2 + 1 == 14, f"got {len(ARTIFACTS) + 3}")

print("\n§10  registration + CI-wiring self-guards")
ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
for h in ("run_gate_evals.py", "run_dispatch_backend_evals.py", "run_handoff_brief_evals.py"):
    check(f"{h} is wired into ci.yml (FB-0056: an un-wired eval is zero protection)", h in ci)
check("schema carries 36 slots", len(schema["properties"]) == 36, str(len(schema["properties"])))
sp_spec = importlib.util.spec_from_file_location("sensitive_paths", PLUGIN / "lib" / "sensitive_paths.py")
sp = importlib.util.module_from_spec(sp_spec); sp_spec.loader.exec_module(sp)
check("schema's sensitivePaths default is byte-identical to the lib's",
      schema["properties"]["sensitivePaths"]["default"] == sp.DEFAULT_SENSITIVE_PATHS)

print()
if _failures:
    print(f"FAILED: {len(_failures)} check(s)")
    for f in _failures:
        print(f"  - {f}")
    sys.exit(1)
print("All gate eval checks passed.")
