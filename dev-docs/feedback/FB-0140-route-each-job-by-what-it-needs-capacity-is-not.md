### FB-0140 — Route each job by what IT needs; "the fleet needs the capacity" is not a routing reason

**Date:** 2026-10-05

**Source type:** review feedback (measured in `dev-docs/research/2026-10-efficiency-audit.md` §4,
a dispatch brief this program actually sent) + Ben's own stated priority.

**What was said:** A live dispatch brief downshifted a worker's model tier with the justification
*"It's reversible, and the program's one critical-path worker needs the account's capacity."* The
audit's §5 read on this: "the clearest evidence the orchestrate is already informally rationing the
shared rate-limit pool via model choice — a real practice, but one that exists only in prose inside
individual dispatch briefs, not as a written rule anywhere." Separately, and the reason this is not
simply a spend decision: Ben, 2026-10-05 — *"If I run out of usage I run out of usage, I just want
to make sure that we're not wasting the tokens we have. Lost time isn't a concern right now… If I do
get a higher tier in the future, flow should already be tuned to be as efficient as possible."*

**Synthesized rule:** Model/effort routing is decided per job, from what that job needs — never by
reference to a sibling job's workload. Downshifting job A to free capacity for job B is the
mirror-image failure of `/flow:spawn`'s already-documented "never decline a worker for budget
reasons" rule, and gets the same treatment: named explicitly as forbidden, not left to an
author's judgment call under pressure. If the account is genuinely short on room, that is this
skill's own step-1 admission-control decision (hold the queue), made explicitly as a queue
question — never a silent per-job effort cut dressed as routing judgment. Overage or a tier change
is Ben's call to raise, never flow's to propose as the fix for a capacity problem.

**Applies to:** `plugins/flow/skills/spawn/SKILL.md` step 2 (the routing table + escalation rule)
and `research/orchestrator-field-manual.md` § 3 (the presentation-rules section that carries Ben's
direct priorities verbatim). Related: [[FB-0091]] (routing must be evidence-driven and logged, not
by feel) — this entry closes the specific capacity-rationing gap FB-0091's own audit left open.
