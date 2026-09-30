#!/usr/bin/env python3
"""Render the results table into the history entry, replacing <!-- RESULTS_TABLE -->."""
import json, collections, pathlib, subprocess, sys
RULES = ["plan-discipline", "documentation", "exploration", "general"]
ARMLABEL = {
    "a":    ("project", "old desc + `paths:`"),
    "b":    ("project", "**new** desc"),
    "cold": ("**plugin**", "old desc (v1.50.0)"),
    "c":    ("**plugin**", "**new** desc (v1.51.0)"),
    "d":    ("project", "*neutral* desc + `paths:`"),
}
ORDER = ["a", "b", "cold", "c", "d"]
# The committed scored output is the default input; pass a path to override.
HERE = pathlib.Path(__file__).resolve().parent
_agg = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "runs" / "aggregate-20260927.json"
agg = json.load(open(_agg))
scored = agg["scored"]
tally = collections.defaultdict(lambda: [0, 0])
for r in scored:
    m = r["model"] or r["requested_model"]
    k = (m, r["arm"], r["scen"])
    tally[k][0] += int(r["scen"] in r["task_turn_rule_calls"]); tally[k][1] += 1
models = sorted({k[0] for k in tally})
out = []
for m in models:
    arms = [a for a in ORDER if any(k[0] == m and k[1] == a for k in tally)]
    out.append(f"### `{m}`" + ("  — **the default Conductor model for the `claude` agent**"
                               if "opus-5" in m else "  — *not* the default model"))
    out.append("")
    out.append("| rule | " + " | ".join(f"{ARMLABEL[a][0]}<br>{ARMLABEL[a][1]}" for a in arms) + " |")
    out.append("|---|" + "---|" * len(arms))
    for scen in RULES:
        cells = []
        for a in arms:
            f, n = tally.get((m, a, scen), [0, 0])
            cells.append("—" if not n else (f"**{f}/{n}**" if f else f"{f}/{n}"))
        note = ""
        if scen in ("plan-discipline", "documentation"):
            note = " *(name matches the task — see finding 3)*"
        out.append(f"| `{scen}`{note} | " + " | ".join(cells) + " |")
    out.append("")
n_disc = len(agg["discarded"])
out.append(f"**{len(scored)} interpretable sessions. {n_disc} discarded at final count** "
           f"(19 limit-truncated sessions were discarded and re-run; see § instrument defects).")
p = pathlib.Path(sys.argv[1]); t = p.read_text()
assert "<!-- RESULTS_TABLE -->" in t
p.write_text(t.replace("<!-- RESULTS_TABLE -->", "\n".join(out), 1))
print("table rendered:", len(scored), "sessions,", len(models), "models")
