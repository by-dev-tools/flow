# Rule-skill activation runs (FB-0124, v1.53.0)

The **raw per-session results** behind v1.53.0's numbers, committed unmodified so the measurement can be
checked rather than trusted — the same reason `tools/coverage-recall/runs/` exists.

Re-derive every number in the history entry, the changelog and the roadmap S0 block:

```sh
python3 tools/rule-activation/aggregate.py --offline    # durable: no network, no live sessions
```

That reproduces every figure in the prose, including `plugin-scope: 0 invocations in 25 sessions`.

**Use `--offline`, and know why it exists.** The default (no flag) re-scores by re-fetching each session's
transcript from Conductor — which needs those sessions to still be reachable, and the probe workspaces were
**archived 2026-09-30**. So `results-*.tsv` (session IDs + per-cell status) is the *index*, and
`aggregate-20260927.json` (the scored output: per session, its turn-1 `Skill` calls, sentinels and control
status) is the **evidence**. The live path is kept so it stays exercised while it still works; the offline
path is the one that survives.

`aggregate.py` discards any session that fails its own known-positive precondition, and prints the discard
count alongside the totals — a session whose control sentinel never came back is **not** a negative
observation. At final count: **59 interpretable, 0 discarded.**

## What the numbers are

**25 of the 59 sessions ran at plugin scope — the only scope a consumer has — and produced ZERO
invocations.** All four rules, the old descriptions and the rewritten ones, on sonnet and on the default
opus. The identical rewrite fires 3/3 at *project* scope. Scope is the decisive variable; the description is
not; and the skill *name* does most of the remaining work (arm d's deliberately vague description still
fired).

## Files

| file | arm | scope | descriptions | model |
|---|---|---|---|---|
| `results-a-sonnet.tsv`, `results-a-rerun.tsv` | a | project | pre-v1.53.0 (+ `paths:`) | sonnet-4-6 |
| `results-b-sonnet.tsv`, `results-b-rerun.tsv` | b | project | v1.53.0 | sonnet-4-6 |
| `results-b-xmodel.tsv` | b | project | v1.53.0 | **opus-5** (the default) |
| `results-cold-armcold.tsv` | cold | **plugin** | pre-v1.53.0, real v1.50.0 install | sonnet-4-6 |
| `results-c-armc.tsv` | c | **plugin** | v1.53.0, real install from this branch | sonnet-4-6 |
| `results-c-armc-opus.tsv` | c | **plugin** | v1.53.0, real install | **opus-5** (the default) |
| `results-d-sonnet.tsv` | d | project | *neutral* description + `paths:` | sonnet-4-6 |

A `-rerun` file supersedes same-cell rows in its `-sonnet` sibling: 19 of the first 28 sessions were
truncated by an account limit mid-run and were discarded and re-run, not counted. `aggregate.py` handles the
precedence — **and the ordering is load-bearing**, because plain `sorted(glob(...))` puts `-rerun` *before*
`-sonnet` and let the truncated original overwrite its own replacement (one of the three instrument defects
in the history entry).

## Supporting artifacts

| file | what it is |
|---|---|
| `aggregate-20260927.json` | the full scored output, per session: model, turn-1 `Skill` calls, sentinels, control status |
| `sentinel-nonces-20260927.json` | the per-rule nonces injected into the probe bodies — needed to interpret a transcript |
| `probe-workspaces-20260927.txt` | the Conductor workspace ids the probes ran in (archived 2026-09-30) |

## Re-running the design, not just the scoring

`../drive.sh` drives one arm; `../setup-arm-c.txt` and `../setup-arm-cold.txt` are the verbatim setup
messages that built the two plugin-scope arms, including the **validity check by content** (`paths:` absent,
`when_to_use` present) rather than by version string — the first arm-c build silently installed `main`'s
plugin instead of the branch's, and only a content assertion caught it.

The probe skill bodies themselves are **not** committed: they are the four real rule-skills plus an injected
nonce, reconstructible from any commit plus `sentinel-nonces-*.json`. The scrubbed neutral bases live on the
`probe/s0-arm-{a,b,d}` branches.

**This rig needs live authenticated sessions, so it cannot be CI-wired.** It is the instrument that would
measure a `SessionStart` hook if flow ever builds one (roadmap § "A plugin `SessionStart` hook"), which is
why it is committed rather than discarded with its workspaces.
