# `tools/rule-activation` — does a rule-skill actually load in a session?

Dev tooling for FB-0122 / roadmap S0. Measures whether Claude **invokes** one of flow's four
`user-invocable: false` rule-skills while doing a realistic task — the one thing `/flow:doctor` Check 3.2
structurally cannot see, and the thing twenty releases of `[PASS]` were silently not checking.

Needs live authenticated sessions, so it **cannot be CI-wired** and no shipped `/flow:*` skill invokes it.

## Why it is shaped this way

**The signal is body-level, not registry-level.** "The name appears in `claude plugin details`" is
registration. Activation is a `Skill` tool_use in a transcript, or recall of a nonce that exists only
inside the skill body. Conflating those two is the defect this tool exists to measure.

**It must be turn-segmented.** Turn 1 is the task and mentions no skills. Turn 2 *asks* which rules were
consulted. A model can satisfy turn 2 by invoking a rule right then — so scoring the whole session measures
"can a model invoke a skill when asked about it" (trivially yes). `score.py` scores **only turn 1**, which
is the sole window attributable to the description. The first run of this rig, scored un-segmented, showed
every arm firing including the control arm expected to return zero. That was the tell.

**Every session carries its own known-positive.** A `[]` result is worthless unless that session proves it
could have produced a hit: at project scope a user-invocable `probe-control` skill carries its own
sentinel; at plugin scope `flow:workflow-help` must be invocable. **A session failing its known-positive is
discarded, not counted as a negative** — `.claude/rules/general.md` § Consistency item 4.

**The base must be neutral and asserted per run.** Flow's own checkout carries `CLAUDE.md` and
`.claude/rules/general.md`, which already instruct plan-before-code and doc discipline — a probe there can
do everything `plan-discipline` says without ever loading it. Probes run on scrubbed branches with no
`CLAUDE.md`, no `AGENTS.md`, no `.claude/` beyond the probe skills.

## Arms

| arm | scope | what varies | control |
|---|---|---|---|
| a | project | today's (pre-v1.51.0) descriptions + `paths:` | `probe-control` sentinel |
| b | project | the v1.51.0 descriptions, no `paths:` | `probe-control` sentinel |
| c | plugin | the real installed plugin | `flow:workflow-help` invocable |
| d | project | a **neutral** description + `paths:` — isolates the field from the description | `probe-control` sentinel |

Arm **c** is the only arm at plugin scope, which is the only scope consumers have. Do not generalise a
project-scope result to consumers: the v1.51.0 measurement found them **divergent**, not equivalent.

## Running it

```sh
# one scrubbed workspace per arm, then:
FOLLOWUP=prompts/followup.txt ./drive.sh b <workspaceId> sonnet run1 plan-discipline:1 documentation:1
python3 aggregate.py     # counts per (arm, model, rule); discards precondition failures
```

Arm c uses `prompts/followup-c.txt` (plugin namespace + a plugin-scope control).

**Record the model per probe.** `aggregate.py` keys on the model reported by the session, not the one
requested, because skill effectiveness depends on the underlying model — the docs say to test every model
you ship to, and the v1.51.0 run found sonnet and opus disagreeing on the same rule.

## Reading a result honestly

- A rule whose **name** matches the task (`plan-discipline` ← "write a plan") fires on name alone: arm d,
  with a deliberately vague description, still fired. Such a cell measures naming, not description quality.
  The discriminating cells are the ones where the name does not match the task surface.
- n=3 per cell. A 1/3 vs 0/3 difference is noise. Report counts and say so.

## Known inefficiencies (measured, not fixed)

`/simplify`'s efficiency lens flagged these. They are recorded rather than fixed because the rig has already
produced its numbers and is re-run rarely; fix them if you are about to run a large sweep.

- **No transcript cache.** `score()` welds `fetch()` to scoring, so every re-score re-downloads every
  session — and this rig was re-run three times while its own defects were being fixed. Completed
  transcripts are immutable; caching to `raw/<sid>.json` would make re-scoring free.
- **Serial fetches.** ~50 independent CLI round-trips run one at a time. A stdlib `ThreadPoolExecutor` over
  the sid list would cut wall-clock to roughly the slowest batch.
- **`drive.sh` spawns a Python interpreter per 5-second poll** to read one status field, up to ~270 times per
  cell. `jq` (already a repo prerequisite) or `grep -o` would do.
- **`score.py` serializes turn-1 messages twice** (`b1` is a prefix of `ball`) and scans the blob ~9 times,
  once for a value the code itself labels "Diagnostic only -- NOT the measurement".
