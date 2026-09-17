#!/usr/bin/env python3
"""Eval harness for the `dispatchBackend` adapter (`plugins/flow/lib/dispatch_backend.py`).

Two bug classes, both of which have live precedent in this repo.

**Shell composition.** The orchestrator field manual's trap T6 records the
quoted-shell-string hazard firing four times in a single session among authors
who had each just finished reasoning about it — a refuted design, then silent
data loss, then unintended execution, then the report of the third mangled by
the third. FB-0108 concluded the fix belongs in the *interface*, not the call
sites. This module is that interface for dispatch, so the harness attacks it as
an interface: metacharacters, quotes, spaces, leading dashes, and an attempt to
route a message BODY through argv instead of a path.

**Silent no-op.** CLAUDE.md: skills reading `flow.config.json` "degrade to
documented defaults or print a loud warning — never silently no-op." For a
dispatch adapter the stakes are higher than usual, because a quiet failure
leaves the caller believing a worker was created when nothing ran. So every
absent/malformed path is asserted to produce a loud `⚠️` AND to name the manual
fallback.

  §1  slot resolution (absent / malformed / valid) and the loud-warning contract
  §2  verb validation — required placeholders, the CLOSED vocabulary, no {message}
  §3  safe rendering
  §4  refusal: shell metacharacters, quotes, spaces, leading `-`
  §5  the message body never reaches argv
  §6  the re-address broadcast renders N distinct messages, not one batched
  §7  no host literal in the suite, PAIRED with the positive slot-read assertion
  §8  malformed input degrades without crashing

**Deletion criterion (FB-0088):** delete with `dispatch_backend.py` — never
before it.

Stdlib only. No network. Run:
    python3 plugins/flow/evals/run_dispatch_backend_evals.py
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
LIB = PLUGIN / "lib" / "dispatch_backend.py"
SUITE = ("orchestrate", "spawn", "handoff", "gate")

_failures: list[str] = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")
        _failures.append(name)


spec = importlib.util.spec_from_file_location("dispatch_backend", LIB)
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)

TMP = Path(tempfile.mkdtemp(prefix="flow-dispatch-evals-"))


def cfg(obj) -> str:
    p = TMP / f"cfg-{abs(hash(json.dumps(obj, sort_keys=True)))}.json"
    p.write_text(json.dumps(obj), encoding="utf-8")
    return str(p)


# A deliberately invented, vendor-neutral CLI name. Using a real host's name here
# would put the very literal §7 forbids into the repo, in the file that forbids it.
GOOD = {
    "listWorkers": "xctl workspace list --json",
    "createWorker": "xctl workspace create --name {name} --message-file {messageFile}",
    "sendMessage": "xctl message create --session {session} --message-file {messageFile}",
    "workerStatus": "xctl session status {session} --json",
    "selfSession": "xctl session current --id",
}

print("\n§1  slot resolution + the loud-warning contract")
b, w = D.load_backend(cfg({}))
check("absent slot ⇒ empty backend + a loud warning", b == {} and len(w) == 1 and "⚠️" in w[0])
check("absent-slot warning names the five verbs so the fix is actionable",
      all(v in w[0] for v in ("listWorkers", "createWorker", "sendMessage", "workerStatus", "selfSession")))
b, w = D.load_backend(str(TMP / "does-not-exist.json"))
check("missing config file ⇒ loud warning, not a crash", b == {} and w and "⚠️" in w[0])
bad = TMP / "bad.json"; bad.write_text("{not json", encoding="utf-8")
b, w = D.load_backend(str(bad))
check("unparseable config ⇒ loud warning", b == {} and w and "⚠️" in w[0])
b, w = D.load_backend(cfg({"dispatchBackend": "xctl"}))
check("dispatchBackend as a STRING ⇒ treated as absent, loudly",
      b == {} and w and "not an object" in w[0])
check("malformed-slot warning distinguishes it from 'no adapter'",
      "is NOT the same as no adapter" in w[0])
b, w = D.load_backend(cfg({"dispatchBackend": GOOD}))
check("valid slot ⇒ no warnings", b == GOOD and w == [])

print("\n§2  verb validation — required placeholders and the closed vocabulary")
r = D.validate(GOOD)
check("a complete adapter validates", r["ok"] and r["configured"] == 5, json.dumps(r["verbs"], indent=1)[:400])
r = D.validate({k: v for k, v in GOOD.items() if k != "createWorker"})
check("a missing verb fails validation", not r["ok"] and r["verbs"]["createWorker"]["state"] == "absent")
check("a missing verb still prints its manual fallback",
      "create the workspace by hand" in r["verbs"]["createWorker"]["manual_fallback"])
r = D.validate({**GOOD, "sendMessage": "xctl message create --session {session}"})
check("sendMessage without {messageFile} is invalid",
      not r["ok"] and any("messageFile" in p for p in r["verbs"]["sendMessage"]["problems"]))
r = D.validate({**GOOD, "sendMessage": 'xctl message create --session {session} --message "{message}"'})
check("a {message} placeholder is REJECTED, not escaped",
      not r["ok"] and any("message" in p for p in r["verbs"]["sendMessage"]["problems"]))
check("the rejection explains the closed vocabulary",
      any("vocabulary is closed" in p for p in r["verbs"]["sendMessage"]["problems"]))
check("{message} is not in the known vocabulary at all", "message" not in D.KNOWN_PLACEHOLDERS)
# Every advertised placeholder must have a real supplier. One that validates and then
# refuses at render is the check-passes/dispatch-fails class the doctor check exists
# to prevent — `{branch}` was exactly that and was removed.
_suppliers = set()
for _req, _p, _m in D.VERBS.values():
    _suppliers |= _req
check("every advertised placeholder is required by at least one verb (none validates "
      "then refuses at render)", D.KNOWN_PLACEHOLDERS == _suppliers,
      f"advertised={sorted(D.KNOWN_PLACEHOLDERS)} supplied-by-a-verb={sorted(_suppliers)}")
check("the report emits the vocabulary, so consumers read it from one definition",
      D.validate(GOOD)["known_placeholders"] == sorted(D.KNOWN_PLACEHOLDERS))
for op in (";", "|", "&", "`", "$("):
    r = D.validate({**GOOD, "listWorkers": f"xctl workspace list {op} rm -rf /"})
    check(f"a template containing {op!r} is invalid", not r["ok"])

print("\n§3  safe rendering")
argv, err = D.render(GOOD, "sendMessage", {"session": "abc-123", "messageFile": ".flow/msg.md"})
check("sendMessage renders", err is None and argv is not None, str(err))
check("rendered argv substitutes both placeholders",
      argv == "xctl message create --session abc-123 --message-file .flow/msg.md".split(), str(argv))
argv, err = D.render(GOOD, "listWorkers", {})
check("a no-placeholder verb renders with no values", err is None and argv[0] == "xctl")
# A consumer may legitimately quote a placeholder in their own template. `str.split()`
# would leave the quotes inside the argument and the backend would report file-not-found
# on a path that exists; shlex is correct and the restricted charset cannot confuse it.
QUOTED = {**GOOD, "sendMessage": 'xctl message create --session {session} --message-file "{messageFile}"'}
argv, err = D.render(QUOTED, "sendMessage", {"session": "a1", "messageFile": ".flow/m.md"})
check("a QUOTED placeholder in the consumer's template parses to a clean argument",
      err is None and argv == ["xctl", "message", "create", "--session", "a1",
                               "--message-file", ".flow/m.md"], str(argv))

print("\n§4  refusal — metacharacters, quotes, spaces, leading dash")
ATTACKS = [
    "abc; rm -rf /", "abc`whoami`", "abc$(id)", "abc|tee /tmp/x", "abc&&id",
    'abc"quoted"', "abc'quoted'", "abc def", "abc\nnewline", "abc>out", "abc<in",
    "$HOME", "a*b", "a~b", "--flag",
]
for val in ATTACKS:
    argv, err = D.render(GOOD, "sendMessage", {"session": val, "messageFile": ".flow/m.md"})
    check(f"refuses session={val!r}", argv is None and err and "⚠️" in err, str(argv))
check("the refusal says REFUSED rather than sanitized",
      "Refused rather than escaped" in (D.render(GOOD, "sendMessage",
        {"session": "a;b", "messageFile": ".flow/m.md"})[1] or ""))
argv, err = D.render(GOOD, "createWorker", {"name": "track-a_1.2", "messageFile": ".flow/b-1.md"})
check("ordinary names/paths are NOT over-refused", err is None, str(err))

print("\n§5  the message body never reaches argv")
body = TMP / "brief.md"
body.write_text("Run `git status` && echo $(whoami)  # backticks and $( ) in real prose\n", encoding="utf-8")
argv, err = D.render(GOOD, "createWorker", {"name": "w1", "messageFile": str(body)})
check("createWorker renders with a real brief path", err is None, str(err))
flat = " ".join(argv or [])
check("argv carries the PATH", str(body) in flat)
check("argv does NOT carry the body's text", "whoami" not in flat and "backticks" not in flat)
check("no verb accepts a body-shaped placeholder",
      all("message}" not in t for t in GOOD.values()))
src = LIB.read_text(encoding="utf-8")
# Usage, not mention: the module docstring legitimately contains the word
# "subprocess" while promising not to use one. A check that cannot tell a
# promise from a call is not a check.
check("the lib never shells out (it renders, it does not run)",
      not any(tok in src for tok in ("subprocess.run", "subprocess.Popen", "os.system(", "os.popen(")))

print("\n§6  the re-address broadcast is N messages, not one batched")
workers = ["sess-a", "sess-b", "sess-c"]
rendered = []
for wsess in workers:
    a, e = D.render(GOOD, "sendMessage", {"session": wsess, "messageFile": ".flow/readdress.md"})
    check(f"re-address renders for {wsess}", e is None, str(e))
    rendered.append(" ".join(a or []))
check("one distinct command per worker (a batched message got the wrong instruction "
      "read by the wrong worker, undetectably from both ends)",
      len(set(rendered)) == 3 and all(w in r for w, r in zip(workers, rendered)))

print("\n§7  no host literal in the suite — PAIRED with the positive slot-read")
# NEGATIVE. Deliberately generic: any concrete host CLI leaking into a shipped
# artifact fails the §4.10 bar, not just one vendor's.
HOST_LITERALS = ("conductor ", "conductor workspace", "conductor session", "conductor message",
                 "codex ", "gpt-5", "opus-5", "sonnet-5", "sonnet-4-6", "haiku-4-5", "fable-5")
scanned = 0
for name in SUITE:
    for f in [PLUGIN / "skills" / name / "SKILL.md"] + sorted((PLUGIN / "skills" / name / "lib").glob("*.py")):
        if not f.is_file():
            continue
        scanned += 1
        txt = f.read_text(encoding="utf-8")
        for lit in HOST_LITERALS:
            check(f"{f.relative_to(PLUGIN)} carries no host/roster literal {lit!r}",
                  lit.lower() not in txt.lower())
for f in sorted((PLUGIN / "lib").glob("*.py")):
    scanned += 1
    txt = f.read_text(encoding="utf-8")
    for lit in HOST_LITERALS:
        check(f"{f.name} carries no host/roster literal {lit!r}", lit.lower() not in txt.lower())
# 4 SKILL.md + 3 skill libs + the shared predicate. Asserted as an exact count,
# not a floor: a floor goes green if a file is added, but also stays green if the
# skill it belongs to is deleted and another grows a second lib.
# 4 SKILL.md + 2 skill libs (gate, handoff) + 2 shared libs in plugins/flow/lib/.
# An exact count, not a floor: a floor goes green when a file is added, but also
# stays green when a skill is deleted and another grows a second lib.
check("the scan covered all 8 new shipped artifacts (an empty or partial sweep is a vacuous pass)",
      scanned == 8, str(scanned))
# POSITIVE — without this, deleting the adapter entirely would turn every line above green.
for name in SUITE:
    txt = (PLUGIN / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    check(f"POSITIVE: {name} still reaches the backend or the shared predicate",
          "dispatch_backend.py" in txt or "sensitive_paths.py" in txt)
check("POSITIVE: the adapter still defines all five verbs",
      set(D.VERBS) == {"listWorkers", "createWorker", "sendMessage", "workerStatus", "selfSession"})

print("\n§8  malformed input degrades without crashing")
for verb, vals in (("nope", {}), ("sendMessage", {}), ("sendMessage", {"session": "a"})):
    a, e = D.render(GOOD, verb, vals)
    check(f"render({verb}, {vals}) refuses cleanly", a is None and e and "⚠️" in e)
proc = subprocess.run([sys.executable, str(LIB), "check", "--config", str(TMP / "nope.json")],
                      capture_output=True, text=True)
check("CLI check on a missing config exits non-zero without a traceback",
      proc.returncode != 0 and "Traceback" not in proc.stderr, proc.stderr[:200])
proc = subprocess.run([sys.executable, str(LIB), "render", "sendMessage", "--set", "oops",
                       "--config", cfg({"dispatchBackend": GOOD})], capture_output=True, text=True)
check("CLI --set without '=' is rejected", proc.returncode == 2 and "KEY=VALUE" in proc.stderr)

print()
if _failures:
    print(f"FAILED: {len(_failures)} check(s)")
    for f in _failures:
        print(f"  - {f}")
    sys.exit(1)
print("All dispatch-backend eval checks passed.")
