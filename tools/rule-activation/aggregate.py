#!/usr/bin/env python3
"""Aggregate S0 probe results into counts. Discards any session failing its precondition."""
import json, subprocess, sys, glob, collections, re
sys.path.insert(0, "/tmp/rig")

RULES = ["plan-discipline", "documentation", "exploration", "general"]

def rows_from_tsv():
    seen = {}
    # ORDER IS LOAD-BEARING: a re-run must supersede the truncated original it replaces.
    # Plain sorted(glob) puts "results-a-rerun.tsv" BEFORE "results-a-sonnet.tsv", so the
    # original overwrote its own replacement and all 19 limit-truncated cells stayed
    # discarded. Originals first, replacements last.
    files = sorted(glob.glob("/tmp/rig/results-*.tsv"),
                   key=lambda f: (0 if f.endswith(("-sonnet.tsv",)) else 1, f))
    for f in files:
        for line in open(f):
            p = line.rstrip("\n").split("\t")
            if len(p) < 6 or p[4] != "OK":
                continue
            arm, scen, run, model, _, sid = p[:6]
            # a re-run supersedes the original cell
            seen[(arm, scen, run, model)] = sid
    return seen

def main():
    import importlib.util
    spec = importlib.util.spec_from_file_location("score", "/tmp/rig/score.py")
    score = importlib.util.module_from_spec(spec); spec.loader.exec_module(score)
    cells = rows_from_tsv()
    scored, discarded = [], []
    for (arm, scen, run, model), sid in sorted(cells.items()):
        r = score.score(sid, f"{arm}/{scen}/r{run}")
        r.update(arm=arm, scen=scen, run=run, requested_model=model)
        # PRECONDITION: the control sentinel must have come back in this very session.
        # Without it, [] is indistinguishable from "the harness never loaded here".
        if not (r["segmented"] and r["control_ok"]):
            discarded.append(r); continue
        scored.append(r)
    json.dump(dict(scored=scored, discarded=discarded), open("/tmp/rig/agg.json", "w"), indent=2)

    tally = collections.defaultdict(lambda: [0, 0])   # (arm,model,scen) -> [fired, n]
    models = collections.Counter()
    for r in scored:
        # arm c runs the REAL plugin bodies, which carry no sentinel by design
        # (a sentinel would be a shipped artifact). Its signal is the Skill
        # tool_use, which IS the activation event: "full skill loads when invoked".
        fired = r["scen"] in r["task_turn_rule_calls"]
        key = (r["arm"], r["model"] or r["requested_model"], r["scen"])
        tally[key][0] += int(fired); tally[key][1] += 1
        models[r["model"] or r["requested_model"]] += 1

    arms = sorted({k[0] for k in tally}); mdls = sorted({k[1] for k in tally})
    for m in mdls:
        print(f"\n=== model: {m} ===")
        print(f"{'rule':18} " + " ".join(f"arm {a:<8}" for a in arms))
        for scen in RULES:
            cells_out = []
            for a in arms:
                f, n = tally.get((a, m, scen), [0, 0])
                cells_out.append(f"{f}/{n}".ljust(12) if n else "—".ljust(12))
            print(f"{scen:18} " + " ".join(cells_out))
    print(f"\ninterpretable sessions: {len(scored)}   discarded (precondition unmet): {len(discarded)}")
    print("models observed:", dict(models))
    if discarded:
        print("discarded:", ", ".join(sorted(d["label"] for d in discarded)))

if __name__ == "__main__":
    main()
