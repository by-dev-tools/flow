### SV2-spike — Does bundled `/verify` return screenshots structurally, or only narrate them? (Deliverable-quality track V2 prerequisite)
**Date:** 2026-06-08
**Branch:** `claude/recursing-mendeleev-41df4c`
**Commit:** (this spike PR; squash SHA at merge) — base `8eb867f`
**Mode:** spike (disposable; deliverable = this entry). No `plugins/flow/*` change, no schema change, no version bump.

**The question (from `verify-build/lib/rubric.md:68` + `SKILL.md:56-64`):** does bundled `/verify` return screenshots **structurally** (frames a downstream consumer — verify-build's per-dimension judge and the future HTML renderer — can use as pixels or as path-referenced files), or does it only **narrate** what it sees in freeform prose? The whole shape of V2 (rendered capture + baseline) forks on the answer.

**Answer: narration-only *to the judge*. V2 must add an explicit capture-and-persist step (branch B).**

**What was done:**
Drove bundled `Skill("verify")` **live** against a throwaway zero-dep web app (under gitignored `.context/scratch/`, since the committed fixture `evals/fixtures/verify-toy-web-app/app` isn't runnable — `server.mjs` has no static serving and `vite` is absent) using the connected Chrome browser MCP. Characterized exactly how a captured frame travels, and where it stops.

Three empirical observations, each load-bearing:

1. **Screenshots return as an image *content block* bound to the invoking agent's conversation — the text channel carries only a narration string.** A Chrome-MCP `computer screenshot` returns `<output_image>` (pixels) to the agent that called it, while the *textual* tool result is just `"Successfully captured screenshot (1408x840, jpeg) - ID: ss_2419a0xsc"`. That ID-and-dimensions string is the only thing a text-reading consumer sees. That string **is** "narration."

2. **`save_to_disk: true` surfaced no usable file path, and no file was discoverable on disk.** The tool contract says `save_to_disk` "Returns the saved path in the tool result," but the returned text was still only `"…jpeg - ID: ss_3441gckti"` — no path — and a filesystem sweep of the tmp/claude dirs (last 5 min) found nothing addressable. So in this (Chrome-MCP) configuration there is no path to hand to another agent even if you ask for one.

3. **verify-build's judges are fresh-context `Agent` subagents that receive only their prompt text** (SKILL.md Step 6). An image block in the orchestrator's context does not propagate to a separately-spawned judge. Combined with (1)+(2): a visual claim reaches the judge as the narration string only → and the rubric's two-citation discipline (no hedged PASS; `rubric.md:35`) correctly turns narration-of-a-screenshot into **Unknown**. That is precisely today's "visual = Unknown → blocks" behavior, now explained mechanically rather than suspected.

I did **not** spawn a separate `Agent` to "confirm" the judge is blind to the orchestrator's image block — that probe is tautological once (1)+(2) hold (there is no path or data to even pass it), and the subagent-receives-only-its-prompt boundary is an architectural guarantee. Recording the omission as a deliberate spike-economy call, not a gap.

**Bonus finding — observation sources are not equally trustworthy (informs the rubric, not just V2):**
While verifying the toy's two criteria, the Chrome-MCP `read_network_requests` panel reported the `POST /api/submit` as **`statusCode: 503`** — reproducibly — while the DOM/a11y tree showed the success toast (which only renders on `res.ok`) and `curl -X POST` returned **`201`** three times running. The app received a 2xx; the network panel's status code was simply wrong. A judge citing the network observation alone would have **wrongly FAILed** criterion 1; the judge citing the DOM observation would have correctly PASSed it. This empirically vindicates `rubric.md:66` ("read text from the DOM/a11y tree if available") and adds a sharper rule for V2: **structured text (labels, toast, error copy, and — now — even network status) should come from the a11y tree / an explicit assertion, not be trusted from a single observation channel.** The a11y tree was the reliable source throughout (`status "Submitted successfully" [ref_2]`, exact button labels).

**Why (what this unblocks):**
V1 (v1.5.1) let a plan *declare* visual criteria, but verify-build still resolves every visual claim to Unknown → blocks, so the agent can't honestly say "the visuals are good" without a human babysitting (FB-0041 north star). V2 is the link that turns that Unknown into a real PASS the Step 8 readiness predicate can trust. This spike was the cheap precondition: it fixes V2's shape before any feature code is written.

**V2 shape (the recommendation this spike hands to the V2 feature plan):**
- **Branch (B): add an explicit capture-and-persist step.** The verify-orchestrating layer drives the browser-MCP screenshot, then **persists each frame to a flow-controlled path** (an assets dir alongside `verifyReportPath`) and writes **path references into the findings buffer's `observations[].content`** — which the schema already types as "relative path or base64 data URI" (`findings-schema.json:98`). No schema migration is needed for *capture*; the buffer was built a superset for exactly this. Judges then receive path-referenced frames (or base64 inlined into the judge prompt) **plus a baseline**, enabling the pairwise VLM comparison the rubric already prefers over absolute scoring.
- **Keep the rubric's VLM/pairwise section — rewrite it, don't remove it.** `rubric.md:68`'s "may be removed if narration-only" disposition is **overtaken**: the section is needed, but should be re-grounded on path-referenced frames + a baseline (the spike confirms frames are capturable; they just don't auto-flow to judges). Absolute scoring stays discouraged.
- **Read text from the a11y tree, not screenshot pixels** (the bonus finding): V2 should capture an `a11y_snapshot` observation per state for label/copy/status assertions, reserving the `screenshot` observation for genuinely visual claims (layout, spacing, color, motion end-state).
- **Coupling (FB-0003):** the V2 feature PR lands capture (producer) + the ephemeral renderer / a judge consumer (consumer) in the **same PR**; it must not duplicate #36's durable `visual-history.html` record (V3b).

**Tradeoffs discussed:**
- **Live run vs documentary characterization.** Chose live (Chrome MCP was confirmed connected) so the answer rests on observed behavior, not inference from docs. Cost was standing up a ~50-line throwaway server; worth it — the `503`-vs-`201` finding and the no-path-from-`save_to_disk` finding would both have been missed by documentary reasoning.
- **Throwaway scratch app vs fixing the committed fixture.** Used `.context/scratch/` (gitignored, uncommitted) rather than making `evals/fixtures/verify-toy-web-app/app` runnable, to keep the spike disposable and avoid editing a committed artifact for a research run. (Surfaced as a side-finding: the committed fixture is documentation-only and not runnable — noted for whoever wires the eventual smoke harness; not fixed here.)
- **Editing `rubric.md:68` / `SKILL.md:64` now vs deferring to V2.** Deferred (user-approved scope): the spike records the answer here; the marker rewrites are V2 implementation work touching shipped safety-critical artifacts, and doing them now would force a version bump + SAFETY ceremony for a research-only spike.

**Lessons learned / limitations (FB-0016 — a spike result is as general as its sample):**
- **The "narration-only-to-the-judge" conclusion generalizes** (it rests on the architectural subagent-boundary, platform-independent). **The specific capture mechanics do not** — they were observed on **one platform (web) via one MCP (Chrome)**. iOS (XcodeBuildMCP) / Android (mobile-mcp) may surface screenshot file paths differently (some return a path natively), which could make their capture step cheaper. **Re-test trigger:** when V2 extends capture beyond web, re-characterize the per-platform screenshot-return contract before assuming the persist-it-yourself step is needed there too.
- `save_to_disk`'s documented "returns the saved path" did not hold in this Chrome-MCP build — a reminder that MCP tool contracts are observed, not assumed (pairs with FB-0015's "check the bundled surface" discipline).
