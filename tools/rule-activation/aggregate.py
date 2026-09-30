#!/usr/bin/env python3
"""Aggregate S0 probe results into counts. Discards any session failing its precondition."""
import json, sys, glob, collections
from pathlib import Path

# Resolve everything relative to THIS FILE, never a scratch dir: the committed runs/ are the
# evidence, and a hardcoded /tmp path made the README's "re-derive every number" command a
# claim nothing could check (the class this whole PR is about).
HERE = Path(__file__).resolve().parent
RUNS = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE / "runs"

RULES = ["plan-discipline", "documentation", "exploration", "general"]

def rows_from_tsv():
    seen = {}
    # ORDER IS LOAD-BEARING: a re-run must supersede the truncated original it replaces.
    # Plain sorted(glob) puts "results-a-rerun.tsv" BEFORE "results-a-sonnet.tsv", so the
    # original overwrote its own replacement and all 19 limit-truncated cells stayed
    # discarded. Originals first, replacements last.
    files = sorted(glob.glob(str(RUNS / "results-*.tsv")),
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

def tally_rows(scored):
    """(model, arm, rule) -> [fired, n]. The only place a count is computed."""
    t = collections.defaultdict(lambda: [0, 0])
    for r in scored:
        m = r["model"] or r.get("requested_model")
        # arm c runs the REAL plugin bodies, which carry no sentinel by design
        # (a sentinel would be a shipped artifact). Its signal is the Skill
        # tool_use, which IS the activation event: "full skill loads when invoked".
        fired = r["scen"] in r["task_turn_rule_calls"]
        key = (m, r["arm"], r["scen"])
        t[key][0] += int(fired)
        t[key][1] += 1
    return t


def offline(path):
    """Re-derive every number from the COMMITTED scored output — no network, no sessions.

    This is the durable path and the one the README promises. The `results-*.tsv` files hold
    session IDs, so re-scoring them needs the transcripts to still be fetchable; the probe
    workspaces were archived 2026-09-30, so that is not guaranteed. The scored JSON is the
    evidence. Kept as a separate entry point rather than the default so the live path stays
    exercised while it still works.
    """
    d = json.load(open(path))
    report(tally_rows(d["scored"]), len(d["scored"]), len(d["discarded"]),
           collections.Counter((r["model"] or r.get("requested_model")) for r in d["scored"]))


def report(tally, n_scored, n_disc, models):
    ORDER = {"a": 0, "b": 1, "cold": 2, "c": 3, "d": 4}
    RULES_ = ["plan-discipline", "documentation", "exploration", "general"]
    arms = sorted({k[1] for k in tally}, key=lambda a: ORDER.get(a, 9))
    for m in sorted({k[0] for k in tally}):
        print(f"\n=== model: {m} ===")
        print(f"{'rule':18} " + " ".join(f"arm {a:<8}" for a in arms))
        for scen in RULES_:
            cells = []
            for a in arms:
                f, n = tally.get((m, a, scen), [0, 0])
                cells.append((f"{f}/{n}" if n else "—").ljust(12))
            print(f"{scen:18} " + " ".join(cells))
    print(f"\ninterpretable sessions: {n_scored}   discarded (precondition unmet): {n_disc}")
    print("models observed:", dict(models))
    plug = [r for k, v in tally.items() if k[1] in ("c", "cold") for r in [v]]
    print(f"plugin-scope: {sum(v[0] for v in plug)} invocations in {sum(v[1] for v in plug)} sessions")


def main():
    # `--offline` re-derives from the committed scored JSON; the default re-fetches.
    if "--offline" in sys.argv:
        rest = [a for a in sys.argv[1:] if a != "--offline"]
        return offline(rest[0] if rest else HERE / "runs" / "aggregate-20260927.json")
    import importlib.util
    spec = importlib.util.spec_from_file_location("score", str(HERE / "score.py"))
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
    out = RUNS / "aggregate-latest.json"
    json.dump(dict(scored=scored, discarded=discarded), open(out, "w"), indent=2)

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
