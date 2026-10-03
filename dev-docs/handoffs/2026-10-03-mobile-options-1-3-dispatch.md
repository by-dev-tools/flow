# Mobile options 1–3 — the orchestrator's dispatch, verbatim

**Status: ACTIVE.** This is the authority the plan block for
`conductor/mobile-options-1-3-hand-off-pr-images-preview-url` cites for its scope bound
(PR A vs PR B), its write scope (why `/flow:ship-spike` is excluded), its number-claiming
protocol, and PR B's blocking dependency on Ben's measured iOS answers.

Written to disk for the same reason `2026-10-01-cv1-followup-dispatch.md` was: a plan that cites
"the dispatch" as its scope authority, with no artifact on disk, cannot be checked by a reviewer —
or by the fresh session that will execute it — on either side of a stated disagreement. That
matters more than usual here, because the plan was written in a session running flow **1.29.0**
and execution moves to a different session (see the plan's hand-off section).

Quoted verbatim, not paraphrased.

---

## mobile-options-1-3 — Let a human review flow's visual artifacts from a phone

### Outcome
A human at either Conductor client (Mac app or iOS app) can reach what a gate asks them to look at.
The hand-off never presents a path that cannot be opened as if it could be. Before/after frames render in
the PR itself. When Conductor is available, the gate-1 prototype and the verify-build walkthrough are
served at a sign-in-gated preview URL, falling back to today's path when it isn't.

### Done means
- [ ] PR A (options 3 + 2): every hand-off naming a local/`file://` artifact says plainly where it can and cannot be opened; committed `visual-history-assets/` frames render as PR-body images (`raw.githubusercontent.com` URLs, pinned to the commit SHA)
- [ ] PR B (option 1): prototype §8 + verify-build/ship hand-offs serve the HTML via `conductor preview set` when the CLI is reachable and authenticated, and fall back loudly to today's path when not — paired evals for both branches
- [ ] PR B builds against Ben's measured mobile results (pending; I will forward them), not assumptions

### Routing
model · effort · why: top-tier (opus-5-1m) · high · touches ship/ + verify-build/ (sensitivePaths floor — silent gate failures)

### You own
write: plugins/flow/skills/{ship,verify-build,prototype}/**, their evals, dev-docs/{history,feedback,roadmap,plan}.md entries
ship slot: shared; serialize — the plugin-currency/Visual-walk worker holds v1.57.0/v1.58.0 and ships first; rebase when it lands

### Context you can't get from the repo
- Spec: `dev-docs/research/2026-10-mobile-workflow.md` §§2–3, §8 options 1–3 (merged as #175). Read it first.
- Ben, 2026-10-03: "I'd like all 5 of those ranked options." Options 4 and 5 go to other workers.
- `conductor preview set` is gated by Conductor sign-in + workspace read access (not public); URL lives until the workspace sleeps. Flow must stay project-agnostic: preview is an optional branch, never required.
- Watch the `**Visual-walk:** N/A` false positive (fix in flight, v1.58.0): if your ship trips it, waive with "orchestrator applying Ben's #173 ruling".

### Contract
- Mode: feature. Run the loop for that mode.
- STOP at the plan gate for EACH PR: write the plan, push the branch, report, end your turn.
- Surface every decision with a recommendation, a confidence (high/medium/low), and the justification. Never make me ask for the confidence or the why.
- Claim any contested number (version, feedback id) MECHANICALLY by pushing the file, not in prose. Re-sweep the default branch AND open branches at every rebase; if either is at or above your claim, take the next free value and re-sweep immediately, without asking.
- Ping me at 77d5e766-53a2-4b9d-8577-f5e4c264c668 on completion, on a blocking question, and on a stall. Compose the message into a file and send it with `conductor message create --session <id> --message-file <file>` — never as a quoted shell argument. Open every message to me with a one-line label: `[w:mobile-opts] <STATUS>` where STATUS is GATE / DONE / BLOCKED / FYI.
- FIRST, before anything else: confirm `/flow:ship` and `/flow:prototype` actually resolve in YOUR environment (`claude plugin list` shows the installed flow version; main is 1.56.0). If the install is 1.29.0, run `claude plugin marketplace update flow && claude plugin update flow@flow` and note that it applies only after a restart. If a skill does not resolve, ping me "SKILL-ABSENT <name>"; do NOT improvise a substitute. Then: start the loop on PR A.
- Never create workspaces or sessions. Never merge.

---

## Follow-up instruction from the orchestrator, mid-plan (2026-10-03), verbatim

> Orchestrator. Heads-up, no action needed until your plan gate: the other new worker found its
> workspace on flow 1.29.0, where /flow:prototype and /flow:spawn don't exist and /flow:ship is 27
> releases stale. Updating fixes the disk but not the running session (FB-0107). So: write your PR A
> plan, **push everything to the branch**, and report at the gate as planned. I'll then start a
> **fresh session in your workspace** for execution and ship, so it runs on 1.56.0, with your pushed
> plan as the hand-off. Write the plan so a fresh session can pick it up cold. Good catch on
> raw.githubusercontent (public 200 / private 404 unauthenticated): that's the kind of measured
> constraint option 2's design needs.
