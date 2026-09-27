#!/usr/bin/env python3
"""Deterministic scorer for the S0 activation probes — TURN-SEGMENTED.

Why segmentation is load-bearing: the session's turn 2 ASKS about the rule-skills. A
model can satisfy that by invoking one right then, producing a `Skill` call and a
sentinel that say nothing about whether the rule governed the TASK. Scoring the whole
session measures "can a model invoke a skill when asked about it" (trivially yes) rather
than "did the description earn the trigger". First run of this rig showed arm A, arm B and
arm D all firing -- the tell that the instrument, not the treatment, was doing the work.

Turn 1 = everything strictly before the SECOND userMessage. That is the only window in
which an invocation is attributable to the description.
"""
import json, re, subprocess, sys

RULES = ["general", "plan-discipline", "documentation", "exploration"]
SENT = lambda r: re.compile(rf"RULESENTINEL-{re.escape(r)}-[0-9a-f]{{8}}")

def fetch(sid):
    msgs, after = [], None
    while True:
        cmd = ["conductor", "--json", "session", "message", sid, "--limit", "200"]
        if after: cmd += ["--after", after]
        out = subprocess.run(cmd, capture_output=True, text=True).stdout
        try: batch = json.loads(out).get("data", [])
        except json.JSONDecodeError: break
        if not batch: break
        msgs += batch; after = batch[-1]["id"]
        if len(batch) < 200: break
    return msgs

def split_turns(msgs):
    """(turn1, rest). Turn 1 ends at the second userMessage."""
    seen = 0
    for i, m in enumerate(msgs):
        if m.get("type") == "userMessage":
            seen += 1
            if seen == 2:
                return msgs[:i], msgs[i:]
    return msgs, []

def skill_calls(blob):
    names = set()
    for pat in (r'"name"\s*:\s*"Skill"\s*,\s*"input"\s*:\s*\{(.*?)\}',
                r'"input"\s*:\s*\{(.*?)\}\s*,\s*"name"\s*:\s*"Skill"'):
        for m in re.finditer(pat, blob, re.DOTALL):
            t = re.search(r'"(?:skill|command|name)"\s*:\s*"([^"]+)"', m.group(1))
            if t: names.add(t.group(1).split(":")[-1])
    return names

def score(sid, label):
    msgs = fetch(sid)
    t1, t2 = split_turns(msgs)
    b1, ball = json.dumps(t1), json.dumps(msgs)
    model = None
    for m in msgs:
        rp = (m.get("content") or {}).get("rawPayload") or {}
        cand = ((rp.get("message") or {}).get("model")) or rp.get("model")
        # `<synthetic>` appears on locally-generated messages (e.g. a limit notice) and is
        # not a model id -- taking it would mislabel the row.
        if cand and not cand.startswith("<"):
            model = cand
    c1 = skill_calls(b1)
    return dict(
        label=label, sid=sid, model=model, msgs=len(msgs), turn1_msgs=len(t1),
        segmented=bool(t2),
        # THE measurement: invoked during the task turn, attributable to the description.
        task_turn_rule_calls=sorted(c1 & set(RULES)),
        task_turn_sentinels=sorted(r for r in RULES if SENT(r).search(b1)),
        # Diagnostic only -- NOT the measurement.
        anywhere_rule_calls=sorted(skill_calls(ball) & set(RULES)),
        # Known-positive for the instrument itself, per scope.
        #   project scope (arms a/b/d): the control skill's own sentinel came back
        #   plugin  scope (arm c): a plugin skill (`flow:workflow-help`) was invocable
        # Without one of these in THIS session, an empty result is indistinguishable
        # from "the harness never loaded here" and the session is not interpretable.
        control_ok=bool(re.search(r"RULESENTINEL-control-[0-9a-f]{8}", ball))
                   or "workflow-help" in skill_calls(ball),
    )

if __name__ == "__main__":
    rows = [score(a.split("=",1)[1], a.split("=",1)[0]) for a in sys.argv[1:]]
    print(json.dumps(rows, indent=2))
