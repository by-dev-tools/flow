# Recall-measurement runs (FB-0115, v1.49.0)

The **raw reviewer outputs** behind v1.49.0's before/after numbers, committed unmodified so the
measurement can be checked rather than trusted — the same reason the D1 §9.3 spike committed its
`design-brief.md` and `auto-plan.md`.

Re-derive every number:

```sh
python3 tools/coverage-recall/recall.py report tools/coverage-recall/runs
```

`report` runs `selftest` first and refuses to print anything if the instrument cannot fail.

| file | condition |
|---|---|
| `spike.before.r1–r4.txt` | source mode, `origin/main`'s SKILL.md (single fused pass) |
| `spike.after.r1,r2,r3,r5,r6.txt` | source mode, this branch's SKILL.md (two-stage) |
| `pr158b.before.r1–r3.txt` | diff mode, `origin/main`'s SKILL.md |
| `pr158b.after.r1–r3.txt` | diff mode, this branch's SKILL.md |
| `pr158.before.r1–r3.txt` · `pr158.after.r1–r3.txt` | diff mode, **the DEGENERATE case** — see below |

Each run is an independent `flow:auditor` spawn — fresh context, no shared state — handed the
rendered skill body for its condition. `agents/auditor.md` is byte-identical between the installed
1.29.0 and this tree and is **not touched by this PR**, so the system prompt in every run is the one
that ships.

**One run is deliberately absent.** A sixth `spike.after` attempt returned only *"I need to read the
rest of the file."* — it truncated its Read of the 77 KB prompt and produced no verdict. It is
excluded because it is not an audit result, and it is recorded here rather than dropped silently:
1 of 13 attempts on a prompt that size produced nothing, which is a real operational property of
running a reviewer over a large evidence block.


## The degenerate `pr158` runs, and why they are here

Six of these outputs score **80% and 100%** — the highest numbers in the corpus — and they
measure nothing. At that commit the plan doc's first `**Spec-walk:**` block belonged to a
*different* PR, so every behaviour in the diff was trivially undeclared. `recall.py report`
labels the case rather than printing it in the recall column, because the best number in a
table being the meaningless one is exactly how a reader gets misled.

They are committed because **every other number in this PR re-derives from committed evidence
and this one did not.** `cases.py` asserted "5/5 in both conditions" from a sandbox that was
about to be archived — and committing the files immediately proved that claim stale: under the
tightened scoring key the before condition is **4/5**, not 5/5. Nobody could have caught that
while the evidence lived only in a container. A claim whose evidence dies with the container is
the shape this work spent itself arguing against.
