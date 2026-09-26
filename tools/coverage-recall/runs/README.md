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

Each run is an independent `flow:auditor` spawn — fresh context, no shared state — handed the
rendered skill body for its condition. `agents/auditor.md` is byte-identical between the installed
1.29.0 and this tree and is **not touched by this PR**, so the system prompt in every run is the one
that ships.

**One run is deliberately absent.** A sixth `spike.after` attempt returned only *"I need to read the
rest of the file."* — it truncated its Read of the 77 KB prompt and produced no verdict. It is
excluded because it is not an audit result, and it is recorded here rather than dropped silently:
1 of 13 attempts on a prompt that size produced nothing, which is a real operational property of
running a reviewer over a large evidence block.
