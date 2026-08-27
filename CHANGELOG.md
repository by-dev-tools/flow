# Changelog

All notable changes to flow are recorded here. Reverse chronological (newest first).

This is the **consumer-facing changelog** — read this before upgrading. For per-PR design decisions + tradeoffs, see [`dev-docs/history.md`](dev-docs/history.md) (verbose, internal-tracking).

Format: each entry has a date, version, headline, 2-4 bullets, and an explicit "Breaking changes:" callout.

To upgrade: see [`docs/upgrade.md`](docs/upgrade.md).

---

## v1.36.0 — 2026-08-27

**`/flow:doctor` Check 2.5's slot-count guard is now the same wrap-tolerant predicate flow runs on itself.**

*(Versioned v1.36.0, not v1.33.0 — v1.33.0–v1.36.0 were all claimed by other concurrently open PRs (two of which, v1.33.0 and v1.34.0, shipped below before this one); re-checked at each rebase and took the next free minor above every live claim. See `dev-docs/history.md` 2026-08-27 for the account.)*

- **The consumer-facing check was weaker than flow's own internal one.** FB-0079 hardened flow's internal slot-count sweep after a wrapped `all 30\n  slots` slipped a line-oriented grep inside `doctor/SKILL.md`'s own YAML frontmatter. Check 2.5 — the guard every consumer project runs — still had every property that produced that miss: line-oriented, a single-literal-space pattern, and doc-ish-only scan targets.
- **Hoisted to one shared predicate.** New `skills/doctor/lib/slot_count_scan.py` (stdlib) matches `N slots` claims over each file's full text rather than line-by-line, so a wrapped claim is caught regardless of where the line breaks. Both flow's internal eval harness and Check 2.5's own shell block now call the identical module — no more two implementations that can silently drift apart.
- **Human-readable survivor output.** Stale claims are reported with a line number and plain words ("13 slots"), not a Python `repr()` that would leak a literal `\n` escape sequence to the terminal.
- **Also added `bootstrap.sh`** to Check 2.5's scan targets — a harmless, zero-cost addition, though narrower than first scoped (it doesn't close the specific gap it was drafted to close; see `dev-docs/history.md` for the honest accounting).

**Breaking changes:** none. The check's output shape and its historical-narrative tolerance (a `#`-prefixed `.sh` comment is still exempt) are unchanged; only its matching precision improved.

## v1.35.0 — 2026-08-27

**A design brief gets its own review pass — before any prototype gets built.**

- **New `lens-experience` agent (D3, FB-0046).** Two lenses in one prompt: an experience/product-designer lens (is this the right problem, is the ambition high enough, does the brief consider the journey/edge-states/friction/feel) and a push-further-on-quality lens (raise the craft bar of the brief's *declared* scope only — a loud guard against proposing new functionality). Reached only through `/flow:review-brief`, matching the rest of the `lens-*.md` family's "would anyone run this alone?" test.
- **New `/flow:review-brief` skill.** One extraction of a design brief, fanned to `auditor` + `plan-critic` + `lens-experience` in a single tool message, so all three demonstrably reviewed the same artifact. Returns one triaged verdict: a clean pass states "proceed to the prototype phase"; any `decision-required` finding renders as a numbered, answerable question — never a document to go read. Standalone-invocable today (`/flow:review-brief <path>`), the same way `/flow:critique-plan <path>` is.
- **A six-field design-brief template**, documented in `workflow.md`: Problem, Whose moment, Constraints, Intended scope, Deliberately excluded, Where this pushes past the literal request — targeting roughly a 20-second read (~80 words total).
- **This is D1 Phase 1** (`dev-docs/handoffs/d1-prototype-first-gate.md`) — the "review the brief before building anything" half of the prototype-first gate. No trigger, no prototype phase, and no loop re-ordering ship here; a brief is still something you write by hand today. Phase 0 (the `role` config slot, v1.31.0) and Phase 1 are both self-contained and don't change behavior for any project that isn't explicitly invoking `/flow:review-brief`.

**Breaking changes:** none. No existing skill, schema slot, or default changes; this PR only adds new, opt-in surface.

---

## v1.34.0 — 2026-08-27

**The periodic memory audit no longer eyeballs Fire-log dates across up to 30 entries by hand.**

- **New `tools/memory/check.mjs --dead [--days=N]`** (default 60). Lists failure-pattern memory entries with no recent activity — most recent `Fire log` date, falling back to `First seen`, falling back to file mtime — so `/flow:ship` § 4b.vi's periodic audit agent gets a deterministic candidate list instead of computing date arithmetic itself. `--list`, `--count`, and `--audit-due` are unchanged.
- **Reduced scope from the original roadmap item.** Fire-rate×recency ranking of `--list` and a deterministic fire-log writer were cut before implementation: flow doesn't control what the harness actually injects into a session's context, so ranking could only ever reorder a curation-facing `--list` output over a corpus capped at 30 files — not worth the added machinery. See `dev-docs/feedback.md` FB-0093.
- **Output includes the resolving date + fallback tier** (e.g. `2026-XX-XX, 90d since last activity via fire, 1 fire`), not just a bare day-count, so a human or the audit agent can tell "known-quiet since a real date" from "no dates recorded at all."

**Breaking changes:** none. `--dead` is a new, opt-in flag; every existing `check.mjs` invocation and output shape is unchanged.

---

## v1.33.0 — 2026-08-27

**The 4 advertised auto-loading rules have never fired for any consumer — until now.**

- **The 4 portable rules (`general`, `plan-discipline`, `documentation`, `exploration`) now ship as path-activated skills.** `plugins/flow/rules/` was never a Claude Code plugin component — no loader call site joins a plugin root to a `rules/` directory, confirmed by decompiling the installed CLI. Every consumer who installed flow got zero of these rules active, regardless of how carefully they followed the bootstrap docs. They now live at `plugins/flow/skills/{general,plan-discipline,documentation,exploration}/SKILL.md` (`paths:` frontmatter + `user-invocable: false`), the mechanism Claude Code's own docs point at for path-triggered guidance. No bootstrap.sh change needed — the plugin install already precedes the scaffold step, so a consumer gets all 4 for free on `/plugin install flow@flow`.
- **`/flow:doctor` now verifies the loader's own report, not disk presence.** The old Check 3.2 inferred a pass from the marketplace + enabled checks; it could never actually detect the rules-never-load bug it existed to catch. It now shells out to `claude plugin details flow@flow` and asserts each of the 4 rule-skills is named in the loader's own output — deleting one reds the check.
- **Hooks stay opt-in, deliberately.** `hooks/default-hooks.json`'s own header already says "NOT auto-applied — consumers opt-in," and the shipped sensitive-file-blocking hook does broad substring matching (`*token*`, `*key*`, `*secret*`) with real false-positive risk — auto-enabling it for every consumer was the riskier direction, not the safer one. The docs that blurred this (`workflow.md` listing "default hooks" alongside unconditionally-bundled components) are corrected instead.
- **Reconciled the drift that let this go unnoticed for so long.** This repo's own dogfooding never caught the bug because its project-scope `.claude/rules/{general,documentation}.md` — a separate, legitimately-forked copy for flow's own dev workflow — auto-loaded successfully and looked like proof the mechanism worked. Three genuinely-duplicated sections (Scope discipline, Decision tracking, Autonomous work guardrails) had drifted between the two copies; synced now, with an explicit cross-reference note in both files so future drift is a decision, not an accident.

**Under the hood.** Skill count 17 → 21 (`claude plugin details` confirms). No gate-machinery code touched — ship/manifest-triage/skip-audit/verify-build/pr-coherence are all untouched. Full eval suite green post-move (`run_plugin_desc_evals.py`'s glob-based skill discovery and the composition lint's dynamic count both picked up the 4 new files with no hardcoded-count breakage).

**Breaking changes:** none. Consumers who already deleted local `.claude/rules/{general,plan-discipline,documentation,exploration}.md` copies per `docs/migration.md`'s Stage 2 guidance now correctly receive the plugin's content for the first time — previously they'd have received none. Consumers who never had local copies see the 4 rules become active where they were silently inert before.

---

## v1.32.0 — 2026-08-26

**A session can no longer claim verification it had no way to perform — or be refused the honest admission that it couldn't.**

- **New `toolchain` manifest kind.** Flow could say *there is no runnable target* (`platform: library|none`, `verifyEnabled: false`); it could not say *there is one, and this machine cannot build it* — the normal condition of a Linux cloud workspace on an iOS project. Both prior exits were wrong: run `/flow:verify-build` and it fails to launch, judges `Unknown`, and gets filed as a regression nobody introduced; skip it and `/flow:audit-skips` refuses the skip, because `platform` is `ios`, not `library`.
- **`/flow:verify-build` now declares that skip itself** — a third self-skip case beside the two it already had, firing when *every* binary its declared platform's build needs is missing from the host. A partially-equipped machine (SDK present, one tool off `PATH`) is deliberately **not** treated as absent and still runs the gate: erring toward running costs a failed build, erring toward skipping silently drops the change's only behavioral gate.
- **The skip is validated, never trusted.** `/flow:audit-skips` calls it LEGITIMATE only on a **conjunction** — the reason must name a toolchain problem *and* a probe of this host must confirm it. Neither half alone: the reason is free text the claimant writes, and the host fact alone would excuse any skip at all on an under-equipped machine. Claimed on a machine that has the toolchain ⇒ `SHOULD-RE-RUN`, naming the binary it found.
- **An honest skip still drafts the PR.** A LEGITIMATE toolchain verdict carries a `toolchain` manifest entry, so `/flow:ship` opens a draft with plain-language copy instead of a green tick. "The skip was honest" and "the change was verified" are different claims, and only the first is established. The entry is `blocked` and un-waivable — no assertion clears it, only a passing check on a machine that has the toolchain.
- **Scope:** `platform: ios` only for now. Android's near-universal `./gradlew` wrapper never resolves through a `PATH` lookup, so a table entry there would make every fully-equipped Android machine self-skip — admitting a platform needs a wrapper-aware probe and a capable-host fixture, not a new dict key. Projects that leave `platform` undeclared are unaffected and keep today's behavior.

**Under the hood.** New shared `skills/verify-build/lib/toolchain.py` (one table, two consumers — the producer and the auditor import it rather than each keeping a copy). `skip-audit-checks.py` gains a `manifest_kind` field so the *engine*, not the calling agent, decides that a LEGITIMATE skip still owes the PR an entry; the field is rendered on `/flow:audit-skips`' summary line so it survives the fork boundary, with a bidirectional eval assertion on that join. New eval coverage across the two CI-wired harnesses — `run_skip_audit_evals.py` goes 35 → 79 checks — each case red-verified against the pre-change tree.

**Breaking changes:** none. Projects without a declared toolchain-gated `platform` see no behavior change; `platform: library|none` and `verifyEnabled: false` skips are untouched.

---

## v1.31.0 — 2026-08-26

**A new optional `role` config slot (`designer` | `engineer`) — Phase 0 of the D1 "prototype-first gate" track.**

- **Why it matters.** The Designer-signal track's D1 work will eventually move a designer's first review gate from the written plan to a prototype, while an engineer keeps today's classic plan gate. That trigger needs to know which role the human on a project holds. This release ships only the slot, so the feature lands in small, independently-shippable pieces.
- **What changed.** `flow.config.schema.json` gains an optional `role` enum (`"designer" | "engineer"`, no default — unset is a distinct, valid state, not silently coerced to either value). `/flow:doctor` gains Check 2.11, reporting the resolved value in all three states. `workflow.md` documents the slot and states plainly that no skill reads it yet.
- **Unaffected.** No runtime behavior changes for any existing project — this is additive schema + reporting only. The eventual trigger, the experience/ambition lens, the design-brief template, and the prototype phase are later, separate releases.
- **Known limitation.** `role` has no consumer yet; setting it today has zero effect beyond `/flow:doctor`'s report.
- **Breaking changes:** none. Schema grows to 33 slots; every existing config resolves exactly as before.

## v1.30.0 — 2026-08-17

**A plan whose walk blocks are all demoted (already merged/shipped) no longer reads as having an active block — so a docs-only post-merge PR is no longer wrongly flagged visually significant.**

- **Why it mattered.** The walk parsers model a block's *position*, not its *lifecycle*. Once the demote-at-merge convention qualified every `Spec-walk`/`Visual-walk` heading (e.g. `**Spec-walk (merged #99):**`), the just-demoted block floated to the top and read as active. `visual-significance.py` (Visual-walk override) and `skip-audit-checks.py` (audit-coverage "no Spec-walk" check) both keyed on `block_count`, so a docs-only post-merge PR computed `visual_significant: true` and had its legitimate skip flagged — routing a clean docs PR to the draft manifest.
- **What changed.** Both consumers now key on the `all_demoted` / `first_heading is None` predicate the shared `walk_extract` parser already emits. `/flow:verify-build` §5a frame-capture activation gains the same guard (the third consumer of the predicate). Red-green fixtures added to both eval harnesses.
- **Unaffected.** A plan with a genuine *active* (bare) walk block behaves exactly as before (regression controls pin this).
- **Known limitation.** The separate "active PR has no anchor / retained block authored above its Spec-walk" leak is still a tracked `walk_extract` limitation (needs a plan-format boundary marker); out of scope here.
- **Breaking changes:** none.

## v1.29.0 — 2026-08-15

**A binary asset change (font / icon / image) now correctly reads as visually significant, instead of silently skipping the `/flow:ship` visual-deliverable gate.**

- **Why it mattered.** `visual-significance.py` found a hunk's file via the `+++ b/<path>` header, but git emits **no** `+++` header for a binary file — only `Binary files a/… and b/… differ`. So an in-place font/icon re-export (`M …/Fraunces.ttf`) computed `visual_significant: false` and waved the change through the visual gate. Because a real font/icon PR *is* an in-place re-export at the same path, this was always the broken case (reported from a live consumer ship).
- **What changed.** A dedicated branch parses the `Binary files … differ` line, checking **both** the `a/` and `b/` sides against the UI/asset patterns. This covers binary **add / modify / delete** uniformly. A binary *delete* of a matched asset now counts as a render delta (removing a rendered asset changes what draws — the gate over-demands a screenshot rather than under-demanding).
- **Unaffected.** The `#if DEBUG` render-delta tracking, the FB-0079 per-consumer pattern split, and all text-diff handling are untouched (the new branch is self-contained).
- **Known limitation.** A *text*-file full deletion has a separate `+++ /dev/null` blind spot not addressed here; tracked as a follow-up.

**Breaking changes:** none. A project that was (incorrectly) skipping the visual gate on a binary asset change will now be asked for the visual deliverable it should always have provided.

## v1.28.0 — 2026-08-14

**Every config-reading flow skill now fails loud when `jq` is missing, instead of silently degrading to hardcoded defaults and reporting green.**

- **Why it mattered.** Skills read `flow.config.json` via `jq … // default` chains. On a box with no `jq` on PATH, each read silently substitutes a hardcoded default — wrong diff base, wrong file patterns, wrong doc paths — and the skill reports success while looking at the wrong thing. `/flow:doctor` was worse: its `jq -e …; then PASS; else FAIL` conditionals took the FAIL branch on exit 127, so a correct install reported `[FAIL]`.
- **What changed.** The action-taking skills (`security-review`, `accessibility-review`, `staff-review`, `contribute`) now `exit 1` with an install hint on missing `jq` (the `/flow:ship` Step 1.5 shape, FB-0009). Three principled carve-outs: `doctor` emits an honest `[SKIP]` (it must diagnose a broken env, never `exit`); `workflow-help` warns but keeps rendering (read-only); the fork skills (`audit-coverage`, `audit-skips`, `critique-plan`) route a `JQ-MISSING`/`jq_error` signal, because a load-time `!`-span cannot abort with `exit`.
- **Regression-pinned.** New `run_jq_guard_evals.py` (wired into CI) *derives* the guarded-skill set from disk and *executes* each live guard under a `jq`-stripped PATH — so a new config-reading skill added without a guard, or a guard that stops blocking, fails CI rather than drifting silently.

**Behavior change:** on a machine without `jq`, the four action-taking skills now stop with a clear install hint instead of running against wrong-scoped defaults. Install `jq` (`brew install jq` / `apt install jq`) and they proceed as before; machines that already have `jq` see no change.

## v1.27.0 — 2026-08-10

**Flow's ephemeral scratch moves out of `/tmp` into a repo-local `.flow/` directory — which restores the skip-legitimacy gate (inert since v1.13.0) and ends cross-project clobbering of reviewer inputs.**

- **`/flow:audit-skips` actually runs again.** A forked skill **cannot see** a `/tmp` file the parent shell wrote — confirmed by a same-file A/B: the handoff produced a full report from the parent and "no stage report to audit" from the fork. Because that message is also the legitimate standalone no-op, the gate had been silently passing on **every ship since v1.13.0**. The handoff now lives at `<repo-root>/.flow/skip-audit-stages.json`, which both sides can read.
- **Concurrent sessions on different projects no longer clobber each other.** `/tmp/flow-staff-diff.patch` and friends were one global filename shared by every project on the machine; in the wild, staff-review lenses were handed another project's diff. Repo-local paths are unique per **worktree** by construction, so the collision cannot happen rather than being unlikely. Reviewer diffs also carry a `# flow-review-context repo=… branch=… head=…` header, and lens agents are told to stop rather than review a workspace they weren't asked about.
- **Handoffs must now prove they belong to this workspace.** Every handoff carries a `flow_stamp` (repo + branch + head); a reader **refuses a mismatch loudly** instead of reading it and hoping someone notices, and an *absent* stamp is refused too. `absent` / `invalid` / `stale` / `ok` are four distinct states — collapsing them is how a foreign buffer read as "nothing to do".
- **A misconfigured `referenceGlob` no longer silently blinds the plan critic.** Zero resolved reference documents used to render *no* `## Reference documents` section, indistinguishable from "this project has no rules." It now emits a loud warning telling the reviewer it cannot raise a Spec violation at all. Flow's own `flow.config.json` was itself missing the slot, so its critic had been running document-blind.
- **Security (CWE-59):** flow refuses to write scratch through a symlink. Moving the scratch dir into the repo created a link-following write primitive `/tmp` did not have — an untrusted clone shipping `.flow` as a symlink could redirect flow's writes outside the repo, since `mkdir -p` follows an existing symlink-to-dir. Found by this release's own security review.
- New `run_scratch_isolation_evals.py` (56 checks, wired into CI) — the **first** harness here to extract and *execute* a SKILL.md `!`-block, which is precisely why the transport bug survived.

**Behavior change:** the skip-legitimacy gate runs for the first time since v1.13.0 — ships that used to pass Step 2a silently will now surface `[skip-audit]` findings, and some will open as drafts that previously did not. That is the fix working, but it is a real change in what you will see. Two config **defaults changed** too: `verifyFindingsPath` `/tmp/flow-verify-findings.json` → `.flow/verify-findings.json`, and `verifyReportPath` `/tmp/flow-verify-report.html` → `.flow/verify-report.html`. Projects that set these explicitly are unaffected. `.flow/` self-ignores (it writes its own `.gitignore`), so it never dirties `git status` and is never committed.

## v1.26.0 — 2026-08-03

**Two file-pattern questions, two slots — `uiFilePatterns` no longer forces one regex to answer both.**

- **What you get.** Two new optional slots: `visualFilePatterns` (does this change what the app *draws*?) and `a11yFilePatterns` (does this change something with an *accessibility surface*?). Each falls back to `uiFilePatterns`, so **if you set only `uiFilePatterns`, nothing about your project changes** — the new slots are opt-in.
- **Why it was broken.** One slot gated two reviewers that ask different questions of the same diff, so every scoping choice was a forced trade. On a real iOS project: the directory that builds the string VoiceOver reads had to be *included* for the a11y review, which then demanded screenshots for pure-persistence files that draw nothing; the mock-data file that decides a chart's shape had to be *excluded* for a11y, so its genuine visual changes went unflagged and needed a hand-written workaround. Neither question was expressible.
- **Also fixed:** `/flow:audit-skips` now confirms each reviewer's skip against the pattern *that reviewer used*. Previously one merged field backed both checks, so once the patterns could disagree it would have confirmed an accessibility skip using the visual pattern — and reported a confident verdict measured with the wrong ruler.
- Pinned by new assertions across two harnesses, each confirmed to fail against the old code — the two headline cases reproduce the exact symptoms reported. The two runtimes that implement the fallback chain (Python and the shell gate's jq) are now compared against each other automatically, so they can't drift apart again.

**Breaking changes:** none. Schema grows to 32 slots; every existing config resolves exactly as before.

---

## v1.25.0 — 2026-08-01

**`/flow:post-merge` now actually runs the doc-currency step instead of telling you to run it.**

- **What you get.** After you merge, `/flow:post-merge <PR#>` reconciles your forward docs itself and hands you the resulting `docs: land #N` PR to merge — one action instead of two. The close-out now leads with the answer to the only question you're asking: `✅ #84 closed out — nothing left.` or `🚫 #84 — 1 left: merge docs PR #91`.
- **Why it was broken.** That step is supposed to call `/flow:land`, but `/flow:land` was marked as never-callable-by-Claude, so the call was rejected every time and quietly degraded into "please run it yourself." The flag was guarding against `/flow:land` firing on its own — which it already can't do, because it refuses to touch anything until GitHub confirms the PR is merged, and Claude can't merge. Clearing the flag costs nothing and restores the step.
- **Also fixed:** `/flow:land` now refuses to run over uncommitted work instead of switching branches out from under it, and its merged-PR check no longer disagrees with the one `/flow:post-merge` uses (they could previously reach opposite conclusions about the same PR during a merge-queue lag).
- Pinned by five new assertions so the step can't be silently removed again — the old check passed whether the call worked *or* was deleted, which is how this survived four releases. All mutation-tested.

**Breaking changes:** none. `/flow:land <PR#>` still works exactly as before when you type it.

## v1.24.0 — 2026-07-29

**The `/flow:verify-build` annotation layer is redesigned: commenting is a mode you stay in, not a button you re-press.**

- **No more re-arming.** Click an element → write or dictate → `↵` → click the next one. Commenting is a persistent mode, on by default. `⌘`/`Ctrl`/`Alt`-click passes a click through to the page (so links and interactive prototypes still work), selecting text never creates a comment, and `Esc` hands the page back.
- **Chrome is one circular floating control** — the minimized comment container. Filled = commenting is live; it carries the comment count; clicking expands the panel. The panel holds a labelled **Commenting** switch, hover-outlining and hide-pins toggles, per-comment copy and delete, **Copy all**, and a two-tap **Delete all**. Only pins float over the design being reviewed.
- **Toasts removed.** Each control states its own condition — a switch, a swapped icon, or a transient label on the button just pressed — instead of a floating message that covered the controls it described. A visually-hidden `role="status"` region carries the same information to screen readers.
- **Accessibility + contrast fixes from a staff design + UX review.** A capture-phase `Enter`/arrow handler was cancelling the default action on *every* key press, so `Enter` could not activate any control, arrows could not scroll, and `Enter` inside a host page's own input was swallowed. White-on-accent failed WCAG on five filled surfaces in dark mode (now a themed `--an-on-accent`); the switch off-state was 1.28:1; list rows were focusable with no focus style; and the crosshair cursor captured the layer's own buttons.
- Anchors (content-derived, regeneration-stable), the located-descriptor export format, and the `file://` hardening are **unchanged**. Existing comments keyed to the old storage prefix are not migrated — the layer starts clean.

**Breaking changes:** none for consumers. Internal note: the layer's element ids changed (`annot-*` → `an-*`) and the storage key is now `flow-annotations-v2:`; anything that greps the partial (flow's own evals do) must be updated with it.

## v1.23.0 — 2026-07-29

**A blocked ship now hands you decisions you can answer, not a draft PR to decode.**

- **The problem.** When a ship gate did not pass, `/flow:ship` opened a draft PR and handed it back. Measured across five real draft PRs in two projects, the round-trip from draft to ready ran **47 minutes to 13 days** — because the blocker was written for an engineer (`needs: declare + verify the criterion, or human waive`) with no proposed fix attached, so the only available move was to ask the agent to go fix it.
- **What changes.** Every blocker is now triaged into one of three shapes. If a resolution exists and has not been tried, the agent tries it once — the visual-walkthrough gate used to draft without ever attempting the capture it was asking for. If it is a real decision, the agent **drafts the fix** and Step 8 hands you a **numbered question**: what it means in plain language, the proposed resolution, a recommendation with its reasoning, what was already tried, and "waive and ship as-is." You answer in a word; the agent applies it and re-runs the check, and the PR goes ready once it passes. If it needs something only you can do outside the session (rotate a leaked secret, vet a dependency), it stays a draft — which is what a draft is actually for.
- **What does not change.** No new approval gate: the pipeline still always reaches the PR, so an unattended run is never wedged (the draft just stands, now answerable). And a failing build still cannot become a merge-ready PR — waiving one is recorded, but the PR stays a draft. If you accept that risk, you mark it ready yourself; the agent will not.
- **Under the hood.** New `skills/ship/lib/manifest-triage.py` (deterministic table, not model judgment) + `evals/run_manifest_triage_evals.py` in CI. The eight places that write a blocker were normalized onto one parseable line shape — five of them did not carry a source tag at all, so four different blocker types were indistinguishable.

Breaking changes: none.

---

---

## v1.22.0 — 2026-07-29

**Three gates that could report success without doing their job — each a contract split across two files with nothing checking the join.**

- **Forked audit skills now know which repo they are auditing.** These skills run in a forked context and inherit the *session* cwd, which is not necessarily the repo under review. From a non-repo cwd every relative read silently returned empty — `flow.config.json` resolved to `{}`, every `git` call returned `""` — and every unverifiable skip then validated as `LEGITIMATE`. The gate printed `all stage skips LEGITIMATE — proceed` having never looked at the repo, and `"could not locate the repo"` was byte-identical to `"nothing to audit"`. `/flow:audit-coverage`, `/flow:audit-skips` and `/flow:critique-plan` now resolve an explicit root — **the cwd's git toplevel first, `CLAUDE_PROJECT_DIR` as the fallback** — before any relative read, and an unresolvable root emits a distinct `ROOT-UNRESOLVED` / `root_error` that `/flow:ship` Step 2a routes to the draft manifest as `[decision-required]`, never a clean pass. (Precedence matters: env-first would break git worktrees, where a session started in the parent repo makes the guard audit the parent tree on a different branch.) `/flow:critique-plan` has the same shape and gates *plan approval* — with no reference docs it structurally cannot quote a rule, so it returns APPROVED. Each also prints the repo root it resolved, so the residual case (cwd is a *different* real repo, where git succeeds) is visible rather than silent.
- **The PR `## Test plan` is now checked, not just specified.** It was *specified* as a non-forgeable projection of the verify-build buffer, but nothing checked that a published block came from the renderer — so a hand-written block with hand-ticked boxes read exactly like a machine verdict. `render-test-plan.py` now stamps **every** path it emits (including the honest no-buffer fallback) with a marker **and a content digest over the checkbox states**, and `/flow:ship` Step 7b asserts both against the **re-fetched** body. That catches two distinct forgeries: a hand-written block (no stamp), and a genuinely-rendered block whose boxes were flipped afterwards (digest mismatch). The digest covers checkbox state and count, deliberately not criterion prose — ship tells you to fill in the fallback's `<how to verify>` line, so hashing prose would make the documented happy path fail its own gate. **Honest limit:** the digest is unkeyed and its algorithm ships in this repo, so an agent determined to forge can recompute it — this defeats cheap forgery (hand-writing the block, flipping a box, editing the published body after ship), not a deliberate in-domain forger.
- **A skill can no longer "call" a skill that cannot be called.** `/flow:post-merge` §3 instructed `Skill("flow:land")`, but `/flow:land` sets `disable-model-invocation: true`, which blocks *programmatic* invocation — so that call was rejected on every run since v1.21.0 and the doc-currency step silently degraded to its fallback. `/flow:land`'s flag is deliberate (it opens PRs; it must not auto-fire), so the delegation is now an explicit hand-off to the human, carried into the archive-safety verdict as an outstanding item instead of being claimed as done. New `doctor/lib/skill-composition-lint.py` + doctor **Check 1.4** fail on any `Skill()` call naming a model-invocation-disabled skill, in the plugin's skills and in a project's own `.claude/skills/`.
- `/flow:contribute` no longer opens drafts (FB-0073): verified changes are applied and the PR opens ready for review; genuine decisions are surfaced explicitly instead of parked.
- Two new eval harnesses wired into CI (`run_skill_composition_evals.py`, `run_root_anchor_evals.py`), plus Test-plan-provenance cases in `run_pr_coherence_evals.py` and `run_render_evals.py`. Each was verified to **fail on the pre-fix tree** — a fixture that passes before and after is not regression protection.
- **CI now checks its own harness list.** It enumerates harnesses by hand (the list is segmented across two jobs, which a glob would flatten), but nothing verified the list was complete — a run with 19 of 20 harnesses looks identical to one with all 20. A new step asserts the on-disk set and the runner set match, in both directions. This is the same contract-split-across-two-files class as the three fixes above, found in this release's own `ci.yml` change.

**Known, not fixed:** cross-project `/tmp` handoff collisions (~16 fixed filenames; two sessions on different repos can hand one project's reviewers another project's diff). Previously dismissed twice as already-covered by a branch/sha freshness guard — that guard covers one of those paths, and `repo_root`, not branch+sha, is the right discriminator. Full evidence table and a split fix plan are in `dev-docs/roadmap.md` § Exploration.

**Breaking changes:** none. `/flow:post-merge` §3 now hands `/flow:land` to you rather than claiming to run it — which is what already happened, now stated honestly.

## v1.21.1 — 2026-07-29

**Two bug fixes: the skip-legitimacy gate can no longer silently pass on a broken handoff, and the Swift preflight discovers `.xcodeproj` bundles correctly.**

- **`/flow:audit-skips` fails loud instead of silent.** Its mechanical engine (`skip-audit-checks.py`) used to return a success exit code with an error-shaped `{"error": …, "stages": []}` when it couldn't read the per-stage handoff — indistinguishable from a genuine "no handoff" standalone run, so `/flow:ship`'s whole skip-legitimacy gate read "nothing to audit" and passed. It now exits non-zero with a diagnostic on stderr; the skill routes that as a distinct `engine_error` (loud, → draft manifest) versus the real absent-handoff no-op versus a valid empty audit.
- **Swift preflight `xcodebuild` discovery fixed.** `template/stacks/swift/tools/preflight/check.sh` used `ls *.xcodeproj`; since `.xcodeproj`/`.xcworkspace` are directory bundles, bare `ls` listed the bundle's *contents* and handed `xcodebuild` an invalid `-project project.pbxproj`. Now `ls -d` — the bundle name xcodebuild expects.
- New `run_skip_audit_evals.py` cases pin the exit-code contract. The related "a forked skill can't see the parent's `/tmp` handoff" transport question is captured in the roadmap, deliberately not patched per-caller here.

**Breaking changes:** none. Internal robustness fixes to shipped skills; no config or API change.

## v1.21.0 — 2026-07-24

**New `/flow:post-merge` skill — the "merged — anything left, or safe to archive?" close-out, run after you merge a PR.**

- **What it does.** One human-invoked command for the moment right after a merge: (1) confirms the PR actually merged, (2) reconciles the forward docs by **calling `/flow:land`**, (3) captures the feedback you gave at the merge gate (your review→iterate→merge comments), (4) deletes the merged branch, and (5) tells you whether the workspace is `✅ safe to archive` or `🚫 not safe` (with reasons). Never merges.
- **Merge-queue safe.** The merge check is three-state, not "merged-or-fail": `MERGED` → proceed; `CLOSED` without merging → fail loud; still `OPEN` → poll up to `postMergeWaitSeconds` (default 150; `0` = fail-fast), then a calm "still queued, re-run once it lands." So on a merge-queue / auto-merge repo — where there's a 1–2 min gap between clicking merge and the PR landing — running it immediately no longer false-fails.
- **Composes with `/flow:land`, doesn't replace it.** ⚠️ *Superseded — see v1.25.0.* `/flow:post-merge` delegates doc-currency to `/flow:land` rather than reimplementing it; `/flow:land` stays independently invocable (run it alone after a GitHub-web merge with no local workspace).
- **Feedback capture on the right side of the merge gate.** `/flow:ship` synthesizes feedback from the window that *closes when the PR opens* — so your richest design-taste comments at the merge gate leaked. `/flow:post-merge` synthesizes that delta window into user-scope agent memory + the `/flow:contribute` queue (content-match dedup; **no** repo-doc `feedbackPath` write in v1 — the transcript watermark + FB-inbox are deferred to v1b).
- New `postMergeWaitSeconds` config slot (schema now **30 slots**). Deterministic core (`skills/post-merge/lib/merge-status.py`: three-state classify + poll policy + archive-safety check) pinned by `run_merge_status_evals.py`, wired into CI.

**Breaking changes:** none. New skill + additive slot; existing behavior unchanged.

## v1.20.0 — 2026-07-15

**The verify-build walkthrough's annotation layer now pins a note to _any_ element on the page — not just a captured screenshot (FB-0071).**

- **Pin anything.** The click-to-pin overlay (v1.7.0) could only anchor to a screenshot, keyed to an `x%/y%` coordinate inside one `<img>`. Now you press **Pin**, hover to pick the exact element under the cursor (a DevTools-style outline snaps to it), and press **↑/↓** to widen to the parent or narrow back to a child — then click or **↵** to drop the pin and type a note. A paragraph, a table cell, a verdict card, or an "open question for you" are all annotatable.
- **Pins survive regeneration.** The report is regenerated every iteration, so pins are keyed to a **stable element identity** (an author `data-pin-id`, else nearest heading + tag + role + a short text sample) — never DOM position — and re-anchor on reload. A note whose element genuinely vanished isn't lost: it stays as a dashed "unanchored" pin and is still exported, flagged.
- **Located, legible export.** "Copy notes" now emits a **location descriptor** per note (`## <section>` → `at <element> "<text>"`) instead of raw coordinates, grouped by section in reading order — so the agent gets "the totals row's Protein cell" rather than "x=46% y=31%".
- **Reusable, not welded to one renderer.** The layer is one self-contained, dependency-free partial with a documented injection contract (paste before `</body>`; opt in to `data-pin-id`) — any flow skill/subagent emitting a reviewable HTML page can inject it. `render-report.py` now injects it on every rendered report, text-only ones included.
- **Kept everything that worked on `file://`.** No native `confirm/alert/prompt` (two-step inline Clear, flash toasts), no async Clipboard API (hidden-textarea + `execCommand`), localStorage persistence, numbered pins, inline editor, bulk "Copy notes". Existing image-region pins are migrated automatically.

**Breaking changes:** none.

## v1.19.0 — 2026-07-12

**`/flow:ship-spike` now harvests flow-generalizable lessons too — the Step 4c contribution router that `/flow:ship` has had since v1.11.0 finally reaches its sibling skill.**

- **The gap.** `/flow:ship-spike`'s Step 4 ran only the memory self-feedback sub-steps — it had **no** Step 4c, so a spike ship never routed lessons about *flow itself* (gate misfires, reviewer false-positives, taste calls you overruled) to the cross-project contribution queue. Spikes are the *highest-yield* source for those lessons, because the agent runs with less guardrail and surfaces more of them — so the omission dropped exactly the signal worth keeping.
- **The fix.** Added Step 4c to `/flow:ship-spike`, a faithful mirror of `/flow:ship` § 4c: the same pre-scan cost gate (`harvest_lesson.py prescan` — a clean spike stays ~free), the same noise/destination/source-type router, the same `enqueue` to `contributionsQueuePath`, the same watermark advance. `/flow:contribute` drains the queue into a draft PR later, unchanged.
- **Always-run, by design.** The harvest is not gated on spike-ness — the value is workflow-type-independent, and the pre-scan keeps it cheap when there's nothing to harvest.
- **No new surface.** No new config slots (reuses the three v1.11.0 harvest slots), no script changes, no schema change — a prompt-doc addition to one skill, kept contract-consistent (identical scripts, slots, and shell blocks) with its `/flow:ship` sibling per the FB-0010 fan-out discipline.

**Breaking changes:** none.

## v1.18.0 — 2026-07-12

**The plan reviewers can now review a plan _document_ on disk, and a deterministic lint flags Spec-walk checkboxes that name no verification (FB-0068).**

- **`/flow:critique-plan <path>` / `/flow:audit-plan <path>`.** Pass a path to review a queued plan document (e.g. a `plans/*.md` file) instead of the session's most recent plan. Without an argument, behavior is unchanged. Under the hood, `extract_session.py` gains `--plan-file`: plan-mode only, a cwd-scoped path guard (rejected outside cwd unless `--allow-external-paths`, mirroring reference docs), fatal on a missing/empty plan (the plan is the review subject, not optional context). Session context becomes best-effort — with no transcript, the render carries a loud standalone-review note and artifact read-status shows **UNKNOWN, never UNREAD**, so a merely-absent transcript can't produce false unverified-recall findings.
- **Pinning lint.** `/flow:critique-plan` now appends a deterministic report (`skills/critique-plan/lib/walk-pin-lint.py`, reusing the shared `walk_extract` parser) of Spec-walk checkboxes that name no test or verification artifact. It is **advisory** — the plan-critic assigns severity only where a reference doc requires a pinning test, and the two-citation rule still binds. Absent such a rule, the lint is informational.
- **Why.** Both gaps surfaced while dogfooding a large set of queued plan documents in a consumer project where the plugin was not installed; the reviewer prompts were applied by reference, not dispatched. The `--plan-file` gap is invocation-independent (the preprocessing had no plan-file input regardless of install state); the pinning gap was the single largest class of thin plans the review found.
- New `run_plan_file_evals.py` + `run_pin_lint_evals.py`, wired into CI.

Breaking changes: none.

---

## v1.17.0 — 2026-07-08

**A PR marked ready can no longer keep the `🚫 NOT READY TO MERGE` manifest at the top of its body. Every PR-body / draft-state write is now read-back-verified, and a body↔draft coherence invariant is enforced at ship and surfaced by doctor + land (FB-0067, SAFETY).**

- **The bug.** A ready PR (`isDraft:false`, mergeable, clean) whose body still opened with the draft manifest — the PR contradicting its own state. Root cause was three converging gaps, all in flow: the manifest scrub was coupled to a full `/flow:ship` re-run (so a blocker cleared *out-of-band* never triggered removal); no PR-body write was read back to confirm it landed (a masked `gh` write like `gh pr edit … | tail -1 && gh pr ready` reports the pipe's exit 0, not gh's failure); and nothing ever asserted the body↔draft contradiction anywhere.
- **Mandatory read-back after every write.** New `skills/ship/lib/verify-pr-body.sh` (→ deterministic `skills/ship/lib/pr-coherence.py`) re-fetches the live PR after any `gh pr edit` / `gh api PATCH` / `gh pr ready[/--undo]` and asserts the write took: intended substrings present, the manifest absent on a ready PR, draft state as intended. A `gh` write is its own checked statement — never piped into a filter that masks its exit code. Wired into `/flow:ship` Step 7 (both PR-CREATE and PR-OPEN paths), `/flow:ship-spike`, and `/flow:staff-review`.
- **Coherence invariant, enforced + surfaced.** `NOT isDraft ⇒ body carries no 🚫 NOT READY TO MERGE manifest`. `/flow:ship` Step 7b asserts it as the last thing it does (fix-in-place or halt loud); `/flow:doctor` Check 2.10 asserts it against any open PR for HEAD; `/flow:land` blocks if the PR it is reconciling merged while still carrying the manifest. Pinned by `evals/run_pr_coherence_evals.py` (manifest-on-ready ⇒ FAIL; manifest-absent-on-ready ⇒ PASS; manifest-on-draft ⇒ PASS), wired into CI.
- **Reconcile-only fast-path.** `/flow:ship` Step 7c re-renders the body + reconciles draft state from the current findings buffer — no reviewers, no doc synthesis — so when a blocker is cleared out-of-band there is a one-command, side-effect-free way to make the body honest.
- **Breaking changes:** none.

---

## v1.16.0 — 2026-07-08

**Frame-integrity gate: `/flow:verify-build` now audits every captured screenshot against a fixed, must-pass checklist — so an obvious visual defect no criterion named (a broken safe-area background, a seam, clipped text) FAILs the gate instead of slipping through.**

- **The gap (dogfood).** On a UI change, screenshots *were* captured, but the frames plainly showed the ambient background broken at the safe-area edges (white bands at the notch + home-indicator, a seam between pages) — and the change was still declared "verified." Two-layer root cause: (1) the frames were read by the *implementing* agent during Execute, not by `/flow:verify-build` §5a's fresh-context judge (the exact conflict of interest §5a exists to remove); (2) even the §6 judges are criterion-scoped, so a defect no `Visual-walk` assertion named had **no checker** — the closest dimension (`regression`) resolved `Unknown` with no baseline rather than `FAIL`.
- **New must-pass frame-integrity pass.** A fourth Step-6 judge (`lib/frame-integrity-checklist.md`) runs in fresh context against **every** persisted screenshot, **independent of the plan's declared criteria** — a closed checklist: edge-to-edge background (no white/black/wrong-gradient band at any safe-area edge), no seam, no clipped text, no collisions, palette fidelity, safe-area respect. It must emit a **literal per-edge / per-corner / background-continuity description before any verdict** (a bare "looks fine" is structurally impossible), and **any failing item ⇒ FAIL, never Unknown** — these are single-frame absolute properties, so absence of a baseline is no excuse.
- **Gate-blocking + visible.** Output is a new top-level `frame_integrity[]` findings-buffer field (additive — `schema_version` stays 1.0), rendered as a prominent "Frame integrity" section in the HTML report. A single `FAIL` forces `overall_verdict: FAIL` (Step 7), independent of the per-criterion verdicts.
- **Operator discipline.** `docs/workflow.md` (Step 8/9) now forbids self-certifying a UI change from screenshots the implementing agent took and read itself: ad-hoc Execute screenshots are for iterating, never sign-off — a visually-significant change routes through `/flow:verify-build` §5a (a11y-gated capture → fresh-context judge → frame-integrity checklist) for any visual verdict. Extends the MANDATORY-capture gate's spirit: implementer-eyeballed frames ⇒ not a verdict.
- Pinned by `run_frame_integrity_evals.py` (wired into CI): a known-bad frame renders a visible `FAIL` with its failing checklist items + described edge evidence; a clean frame renders `PASS`.

**Breaking changes:** none. `frame_integrity[]` is additive; a buffer without it renders exactly as before.

---

## v1.15.0 — 2026-07-08

**The `/flow:ship` + `/flow:ship-spike` PR body now opens with a plain-language summary + a Scope label, so the first thing a reviewer reads at the merge gate is what kind of change this is and what it does — without opening the diff.**

- **`## Summary` leads top-down: scope → what → why.** A `**Scope:**` label (`docs-only | new feature | bugfix | refactor | test | chore | mixed`; `spike` for `/flow:ship-spike`) followed by a one-or-two-sentence, non-technical description of what changed, above the existing why-bullets.
- **Additive, never subtractive.** The plain-language opener is a new top layer — it does not replace or trim the why-bullets or any reviewer-facing detail. The authoring instruction explicitly forbids dropping detail to make room for the summary.
- **Plain language means plain.** The what-changed line bars internal codenames (FB-XXXX, PR letters) and jargon, so a teammate skimming the PR list understands it at a glance.
- **Docs/prompt-only.** The mechanical `## Test plan` renderer and the `## Flow run` table are untouched. Template fan-out kept in sync across `skills/ship`, `skills/ship-spike`, `docs/workflow.md`, and the `resolution-confidence-routing` eval fixture. Breaking changes: none.

---

## v1.14.0 — 2026-07-01

**Orientation-doc-staleness gap closed: `/flow:ship` now discovers UNDECLARED status surfaces (the CLAUDE.md a fresh agent reads first) that drifted after a merge, and routes them to the draft manifest.**

- **The gap.** The doc-currency machinery (`/flow:ship` Step 5a/5b, doctor Check 2.7) only reconciles surfaces a project explicitly declared in `statusDocs`. An UNDECLARED orientation doc is invisible to the whole pipeline: Step 5a touches nothing, Step 5b prints "none declared", doctor 2.7 has nothing to check. So it silently rots after a merge — the dogfood: a merged sub-PR "3c₁" left `CLAUDE.md`'s status paragraphs reading "3c is next (not started)", describing just-shipped work as upcoming; a separate hand PR was needed to fix it.
- **New `statusSurfaceCandidates` slot (schema, default ships).** An array of repo-root paths of well-known auto-loading orientation docs. Defaults to `CLAUDE.md, AGENTS.md, README.md, GEMINI.md, .cursorrules, .github/copilot-instructions.md` so **zero-config projects are covered**; override to extend/narrow, or `[]` to opt out of discovery. The drift judgment — not the file list — is what holds false positives down.
- **New ship Step 5a.5 (discovery + best-effort drift detection).** ONLY when this ship moved forward-looking status (the existing `STATUS_MOVED` signal), the stdlib `skills/ship/lib/status-surface-scan.py` helper emits each candidate that exists and is **not** already declared, plus a bounded status-bearing slice. The agent best-effort-judges each (same tier as `/flow:audit-coverage`) for a stale "next/upcoming/not-started" claim about work the just-reconciled plan/roadmap now marks shipped. **False-positive discipline:** flag ONLY with a **verbatim** drift quote — mere keyword presence ("Phase 3c") is not drift; no quote ⇒ no flag. A flagged surface → a `[decision-required]` draft-manifest entry (reconcile now, OR declare + fence it for Tier 2 auto-reconcile, OR human-waive). **Never a hard halt; never a silent rewrite of an un-fenced human doc** — the draft item IS the propose-before-editing proposal. Clean, undeclared-but-not-drifted → an explicit skip line.
- **Two clean tiers.** Declared + fenced = Tier 2 (auto-reconciled by 5a, never a draft item). Undeclared but drifted = Tier 1 (discovered by 5a.5 → draft). The scan excludes declared paths, so it never double-counts.
- **doctor Check 2.9 (setup-time opt-in nudge).** Warn-only: an undeclared candidate that carries status content gets a one-time nudge to fence it + declare it (Tier 2), so a project opts in before the next ship's 5a.5 keeps nagging.
- **Bootstrap.** The scaffolded `CLAUDE.md` now ships with a `<!-- flow:status -->` fenced status region + a seeded `statusDocs` entry, so **new consumers get Tier 2 auto-reconcile by default**.
- New `run_status_surface_evals.py` (positive dogfood / negative declared-fenced / false-positive fixtures + helper unit coverage) wired into CI. Schema now 29 slots. Breaking changes: none.

---

## v1.13.0 — 2026-06-28

**Two failure-open gaps in the ship pipeline closed: visually-significant changes now REQUIRE both visual deliverables, and every stage skip is audited for legitimacy. SAFETY (gate behavior).**

- **Visual-deliverable gate (Feature 1).** A new shared predicate (`skills/verify-build/lib/visual-significance.py`, reused by verify-build + ship — one source of truth) decides whether a change is visually significant: `uiSurface != false`, the diff touches UI/asset files (or a plan `Visual-walk` block / agent flag forces it), and it isn't a pure no-render-delta refactor. The verdict is stamped into the findings buffer (`metadata.visual_significant` / `visual_signals`) so downstream steps read ONE value. When true: `/flow:verify-build` makes frame capture **mandatory** — zero captured frames aggregates to `Unknown`, never `PASS` (a `not_tested[]` line carries the rationale); ship Step 5c's visual-history distill **no longer fails open** on a short-circuited or grounding-less buffer (a hand-authored entry becomes the required path); and ship Step 7a asserts **both** deliverables exist (a fresh walkthrough with ≥1 frame + a new `visual-history.html` entry referencing the branch) before marking the PR ready — either missing routes it to a **draft** naming the gap, with the ephemeral walkthrough's local path in the body handoff.
- **Skip-legitimacy audit (Feature 2).** New `/flow:audit-skips` skill (ship Step 2a, after the four reviewers) audits every stage's skip + every "ran" claim against ground truth, backed by the deterministic `skills/audit-skips/lib/skip-audit-checks.py`. The load-bearing rule: **a stage's verdict is trusted only if its canonical artifact EXISTS and matches HEAD** — a verify-build PASS with no fresh findings buffer is the "confirmed manually + self-certified" short-circuit, and the missing buffer is the tell. SHOULD-RE-RUN with a cheap re-run → re-run + re-audit once; otherwise a `[decision-required]` draft entry. Docs-only / backend-only PRs rule clean (no false positives).
- New `run_visual_significance_evals.py` + `run_skip_audit_evals.py` (the five acceptance cases) wired into CI. No new config slots. The two human gates (plan approval, merge) are unchanged; both new gates route to the draft manifest the human already sees at the merge gate, never a hard halt. Breaking changes: none.

---

## v1.12.0 — 2026-06-28

**New skill `/flow:land <PR#>` — post-merge doc-currency. Closes the "at PR → merged never reconciles" gap.**

- **What it does.** `/flow:ship` reconciles your forward docs at *PR-open* time, but it runs before the merge — so once *you* merge, nothing flips the item from "at PR (#N)" to "merged (#N)", and `main`'s roadmap/plan sit stale until someone hand-patches them. `/flow:land <PR#>` is the one command that does that reconciliation: it verifies the PR is actually merged (fails loudly otherwise, edits nothing), flips the item to "merged (#N)" across roadmap/plan/history, moves it to "Recently shipped", and opens a small `docs: land #N` PR. **Never merges.**
- **Human-only.** `disable-model-invocation: true` — Claude can't merge, so this can't live inside `/flow:ship` and never auto-fires; you run it after merging.
- **Also handles** the late visual-history distill (re-runs `/flow:ship` §5c if a visual pass was blocked at ship and has since completed — one shared implementation, not a fork), a CHANGELOG-currency check, and clearing any feedback-ID reservations the PR claimed. Idempotent: a re-run after a partial land reuses the land branch and treats already-done steps as no-ops.
- Backed by the stdlib `skills/land/lib/land-helpers.py` (changelog-check + clear-reservation) and `evals/run_land_evals.py`, wired into CI (FB-0061).
- Breaking changes: none.

## v1.11.1 — 2026-06-27

**`/flow:ship-spike` re-ship now gets the same `gh` Projects-classic resilience as `/flow:ship` + `/flow:staff-review`. SAFETY (PR-body write fallback).**

- **Fan-out fix.** v1.10.1 added a canonical `gh`-resilience fallback (REST body PATCH + draft-toggle mutations) for the Projects-classic `projectCards` GraphQL deprecation and wired it into `/flow:ship` Step 7 + `/flow:staff-review` Step 7 — but **`/flow:ship-spike`'s PR-OPEN re-ship path was missed** (the third PR-write site). On affected repos a spike re-ship's body update would still fail silently. `/flow:ship-spike` Step 7 now references the canonical fallback, and the stale `/flow:staff-review` §1.5 note is de-staled (FB-0010 fan-out completion, FB-0060).
- Docs-only; no renderer or gate behavior changes. Breaking changes: none.

## v1.11.0 — 2026-06-25

**Flow now learns from its own use and contributes the lessons back. `/flow:ship` Step 4c harvests *flow-generalizable* lessons (a reviewer false-positive, a gate misfire, a taste call you overruled) behind a ~free pre-scan; the new `/flow:contribute` skill drains them into a DRAFT PR back to the flow plugin. Runs itself; you only gate the merge. SAFETY (new ship step + session-parsing helpers + install-surface manifests).**

- **Harvest (automatic, in `/flow:ship` Step 4c).** A deterministic pre-scan makes clean PRs cost zero tokens. When the transcript carries a correction / symptom / overrule / endorsed-reviewer signal, the analyzer routes each finding PROJECT-LOCAL (existing 4a/4b surfaces) vs FLOW-GENERALIZABLE vs BOTH, drops noise/low-confidence, and enqueues the generalizable ones to a user-scope cross-project queue. Routing/noise are best-effort LLM judgment; only the confidence score + pre-scan are mechanical.
- **`/flow:contribute` (the drain).** Run from your flow checkout (`flowRepoPath`), it drains the queue **and** the previously-manual `/flow:log-disagreement` store, sanitizes out personal-project tokens (fail-closed — a residual leak is held for you, never shipped), scores, and opens a single rolling **draft** PR with the high-confidence clean lessons (everything else held + listed). Never merges; calibrates from each PR's merge/close/edit outcome.
- **Self-triggering.** A flow-repo `SessionStart` hook fires the drain whenever you open the flow checkout with a non-empty queue (primary); an optional local OS job covers the rest. No cloud routine (the queue + checkout are local).
- **4 new slots → 28 total:** `flowRepoPath`, `contributionsQueuePath`, `lastHarvestedPath`, `contributionThreshold`. New scripts (`contribution_store.py`, `harvest_lesson.py`, `sanitize_tokens.py`) + `run_contribution_evals.py` wired into CI. Auto-merge of high-confidence contributions is designed-for but **deferred** (v1 always gates the merge on you). FB-0059.
- Breaking changes: none.

## v1.10.2 — 2026-06-26

**Fixes a jq boolean-slot footgun that silently inverted `verifyEnabled: false` / `uiSurface: false` opt-outs. SAFETY (skip-gate / fallback behavior).**

- `jq -r '.X // true'` treats boolean `false` (not just `null`) as "empty", so `false // true` → `true` — an explicit opt-out resolved to *enabled*. The load-bearing case: a project with `verifyEnabled: false` had `/flow:verify-build`'s Step 1.2 skip-gate fail to fire, running the behavioral gate despite the opt-out.
- Fixed all **four** affected sites with `jq -r 'if .X == false then "false" else "true" end'` (absent/null → default-on; explicit `false` honored): `doctor` Check 5.3, `verify-build` Step 1.2 skip-gate + the preprocessed display line, and `ship` §5c's `uiSurface` visual-history gate (the 4th instance, which regressed in v1.8.0 — caught while bringing the fix current).
- **FB-0058** names the durable discipline: never read a boolean slot with `// <default>`; grep skills for `.<slot> //` when adding a boolean slot or a new read. (Originally drafted as FB-0047 on PR #44; renumbered on merge to avoid colliding with main's shipped FB-0047.)
- Surfaced by a consumer dogfood (valletta iOS flow-migration, `verifyEnabled: false`).
- Breaking changes: none.

## v1.10.1 — 2026-06-24

**Docs-only follow-up to v1.10.0: `gh` Projects-classic PR-write resilience. SAFETY (PR-write fallback behavior in the ship pipeline).**

- `/flow:ship` Step 7 + `/flow:staff-review` Step 7 now document a fallback for the `gh` Projects-classic GraphQL deprecation: on classic-projects repos with affected `gh` versions, `gh pr edit` / `gh pr ready` / `gh pr view --json` fail with `GraphQL: Projects (classic) … projectCards`. The fallback sets the PR body via REST (`gh api -X PATCH .../pulls/N -F body=@file`) and toggles draft state via the `markPullRequestReadyForReview` / `convertPullRequestToDraft` GraphQL mutations (which don't query `projectCards`).
- The secondary item from the same FB-0056 dogfood report that produced v1.10.0; no behavior change to renderers or gates.
- Breaking changes: none.

## v1.10.0 — 2026-06-23

**Two dogfood-discovered integrity gaps in `/flow:verify-build` + `/flow:ship` are closed (#57). SAFETY (verify/ship verdict + gating behavior).**

- **Provenance / anti-forgery.** A per-criterion `metadata`/criterion `provenance` field (`adversarial-judged` | `spike-rubric` | `hand-authored`; **absent ⇒ hand-authored**) lets the renderers tell a judged buffer from a self-reported one. A hand-authored buffer renders a distinct `[~]` self-report state + banner in the PR Test plan and HTML report, never a forgeable machine `[x]`.
- **Spike ≠ no-plan.** Spike's reduced rigor now requires an explicit `/flow:ship-spike`; a no-plan source-touching diff runs the full judged path over diff-derived criteria + draft-routes (`no_plan_fallback`); docs-only → smoke.
- **Rigor gate.** A new commit-invariant `lib/rigor-marker.py`: `/flow:staff-review` writes it, `/flow:ship` Step 1.0a reads it for source-touching diffs → draft if missing/stale.
- New report-render + rigor-marker eval harnesses + a hand-authored fixture, wired into CI (with the previously-orphaned visual-history harness). FB-0056.
- Breaking changes: none.

## v1.9.1 — 2026-06-21

**`/flow:verify-build`'s rendered visual summary is no longer silently dropped when a plan's `**Spec-walk:**` heading is non-canonical. The visual-capture step (§5a) now gates on its own condition, independent of behavioral-criteria extraction, and a new parser makes the capture state-set deterministic. Deliverable-quality track V2.1. SAFETY (verify-build routing/fallback behavior).**

- **Silent-skip fix.** §5a (visual capture → the HTML walkthrough) was gated behind successful `**Spec-walk:**` extraction, so a non-canonical heading → 0 criteria → spike fallback → §5a skipped with no warning, dropping the visual summary even when a `Visual-walk` block was declared. §5a now activates on `uiSurface:true` + a `Visual-walk` block present (via the new parser), decoupled from Spec-walk and spike mode.
- **New `extract-visual-states.py`** — deterministic 1:1 parse of the `Visual-walk` block (one capture-target per declared assertion + optional `[category:]`), so two runs no longer enumerate the capture state-set differently.
- **Robust heading match + active-block scoping (both parsers).** Recognizes canonical `**Spec-walk:**`, qualified `**Spec-walk (…):**`, markdown `### Spec-walk`, and the `**Visual-walk** *(…)*:` form; extracts only the first (active) block with a loud multi-block warning. Convention: author the active PR's plan at the top — retained blocks are ignored and need no heading qualification (retires the prior author-memory convention). Shared logic in `lib/walk_extract.py`; `extract-criteria.py` stays backward-compatible (additive `block_count`). Pinned by `evals/run_walk_extract_evals.py` (FB-0055).
- Breaking changes: none.

## v1.9.0 — 2026-06-19

**Doc-currency reconciliation now covers project-declared status surfaces, not just the built-in plan/roadmap pair. A new `statusDocs` slot lets a project name forward-looking status docs (e.g. a `CLAUDE.md` / `README` status line a cold agent reads) that `/flow:ship` reconciles every ship — and the mechanical gate fires with NO version manifest, closing the dogfood hole where a sub-PR left a phase status stale. SAFETY (new ship-time BLOCKER path).**

- **New `statusDocs` slot (24 slots total)** — an array (default `[]`) of `{ "path": "CLAUDE.md", "marker": "flow:status" }` entries. Flow reconciles **only** the region between the HTML-comment fences `<!-- {marker} -->` … `<!-- /{marker} -->` — a narrow, mechanical update, never a restructure (so projects that gate broad `CLAUDE.md` edits behind a human stay safe). `marker` defaults to `flow:status`. Empty/absent ⇒ identical behavior to today.
- **`/flow:ship` Step 5a** reconciles each declared region to the just-shipped reality (after the built-in plan "Current Focus" + roadmap "Now"). A declared-but-unfenced surface is a loud `⚠️` warning, never a silent skip.
- **`/flow:ship` Step 5b** gains a **version-manifest-INDEPENDENT** marker-coverage gate: if the ship moved forward-looking status (plan "## Current Focus" or roadmap "## Now" changed vs the base) but a declared region was left untouched — or a declared marker is missing — the ship **BLOCKS**. The existing version-token assertion is preserved for versioned projects; this adds real enforcement for projects with no `plugin.json`/`package.json`.
- **`/flow:doctor` Check 2.7** verifies every declared `statusDocs` path exists and is fenced, so misconfiguration surfaces at setup instead of at the next ship's BLOCKER.
- **`lib/status-docs.py` (stdlib) + `evals/run_status_docs_evals.py`.** A shared pure-text helper (parse entries, extract region/section, check fences) consumed by Step 5b + doctor — one implementation, not three copies of awk (FB-0010). Wired into CI.
- **Backward compatible (FB-0054):** projects that don't declare `statusDocs` see no behavior change on any step; flow's own repo declares none, so this PR's own ship exercises the empty-skip path.
- Breaking changes: none.

## v1.8.1 — 2026-06-16

**Fixes a dogfound image-load bug in V3b's `/flow:ship` Step 5c distill, caught by the first real cold-run on a UI surface. SAFETY (asset-persistence path correctness).**

- **Asset-path doubling fix.** §5c set `ASSETS_SRC="$(dirname REPORT)/assets"` and copied `"$ASSETS_SRC/<content>"`, but each frame's `observations[].content` already begins `assets/…` (the §5a convention) → the source path doubled to `.../assets/assets/<frame>`, so the copy missed and the durable record's `<img>` refs pointed at missing files. §5c now resolves frame sources against the **report dir** (`$REPORT_DIR/<content>`) and copies by **basename**, aligning §5a's and §5c's "relative to what" wording. A new `run_visual_history_evals.py` guard pins it (no `ASSETS_SRC`, uses `$REPORT_DIR` + `basename`, keeps the explicit `assets/assets` trap note).
- **Resolved-this-iteration open-question routing clarified.** §5c now distinguishes a `this-iteration` question the human *answered with a decision* (a distill source) from a genuinely-forward `future-planning` question (route to roadmap), and warns against relabeling a still-open blocker as `future-planning` just to clear the Step 8 gate. The proper schema `resolved` flag is roadmapped (§ Next).
- **Validated:** the FB-0016 health-tracker (iOS) cold-run confirmed §5c fires, the curated entry is editorially sound, and screenshots load — and surfaced this bug + two roadmap follow-ups (Spec-walk-block aggregation; the `resolved` open-question flag).
- Breaking changes: none.

## v1.8.0 — 2026-06-16

**The durable visual record (`visual-history.html`) + the distill bridge — Deliverable-quality track V3b. The ephemeral per-run verify-build report now *feeds* a committed, curated record of the visual decisions that changed how the product looks; nothing is read back from `/tmp` and lost. SAFETY (new committed-asset persistence path + create-on-first-write fallback).**

- **New `visualHistoryPath` slot (23 slots total)** — the path to a single, curated, reverse-chronological `visual-history.html`, the *picture* companion to the history doc. Default `core-docs/visual-history.html`; `uiSurface`-gated.
- **`/flow:ship` Step 5c — the distill bridge.** On UI projects, after a verify-build run, the load-bearing visual decisions in that run's findings buffer (the `grounding` entries that changed the user's read + any resolved this-iteration `open_questions`) are distilled into **one** curated entry; the ephemeral report stays ephemeral (distill-then-discard). Heavily gated — self-skips with an explicit reason on `uiSurface:false`, a skipped verify-build, or a run with no load-bearing visual decision (the record is curated, **not** a per-PR dump).
- **`lib/insert-visual-history.py` (stdlib) + `lib/visual-history-skeleton.html`.** The agent curates *which* decision is load-bearing and authors its content; the helper enforces *structure* — seeds the file from the bundled skeleton on first write (no `bootstrap.sh` scaffold, so non-UI projects never get an empty doc), prepends the entry (reverse-chronological), regenerates the anchor-link TOC, and strips heading emphasis (no italic headings). Lean committed asset refs in `visual-history-assets/`; an inline CSS/SVG reconstruction is the honest, labelled fallback when capture isn't available. Malformed target / invalid entry → loud fail, no partial write.
- **`/flow:ship` Step 4a** now also derives a candidate `FB-XXXX` from a this-iteration `open_question` the human answered with a correction (the canonical user-correction FB source).
- **Mechanism note (FB-0053, reverses FB-0042(e)):** created-on-first-write, not a bootstrap scaffold — `bootstrap.sh` runs before `flow.config.json` exists, so it can't gate on `uiSurface`; create-on-first-write keeps the doc out of non-UI repos. Pinned by `evals/run_visual_history_evals.py`.
- **Validation:** the entry shape is **provisional** pending a UI-surface cold-run (flow's own repo is `uiSurface:false`, so its ship always self-skips this step). The first real curated entry comes from the tracked health-tracker (iOS) follow-up.
- Breaking changes: none.

## v1.7.1 — 2026-06-15

**Plain-language copy pass on the `/flow:verify-build` HTML report so a human reading it to make the merge decision understands it at a glance (from FB-0052). Copy-only — no behavior, schema, or logic change.**

- Plainer lede; the legend header `How a verdict / a choice earns its place` → **"Legend"** + a one-line gloss explaining the grounding tags.
- Dropped the redundant jargon `verify exit code: N` pill (the `Overall` pill already encodes pass/fail); `N verify calls` → `N verification steps`.
- Observation labels humanized: `a11y_snapshot` → "Accessibility tree"; `timestamp_offset_ms` shown as **"1.2s in"** instead of `+1200ms`.
- Did **not** rename the grounding vocabulary (need / design-language / craft-commitment / open-question — the established FB-0040 tags); glossed it. Renderer's graceful-degradation + security guards untouched.
- Breaking changes: none.

## v1.7.0 — 2026-06-15

**The `/flow:verify-build` ephemeral HTML report is now a TWO-WAY review surface — the human leaves *located* feedback at the merge gate instead of prose the agent must guess at. Completes V3a (the renderer shipped read-only in v1.6.0). SAFETY (changes the rendered report's output + injection behavior).**

- **Click-to-pin annotation overlay (`verify-build/lib/annotation-layer.html`):** a self-contained, dependency-free vanilla-JS layer that `render-report.py` injects before `</body>` **when the buffer carries at least one captured frame**. The reviewer clicks a screenshot to drop a numbered pin, types a note, and clicks **Copy notes** to get a structured, per-screen, reading-order block (`#3 · <criterion> at x=46% y=31%: …`) to paste back — so a `[this iteration]`-class visual flag re-enters Execute with exact coordinates, mirroring an `open_questions[this-iteration]`.
- **Graceful + scoped:** a frameless (text-only / pre-capture) report stays read-only — no toolbar when there's nothing to annotate; an unreadable layer file renders read-only with a warning, never a crash. Pins persist in `localStorage` (keyed per branch via the report title), harmonize with the report's light/dark palette, and are keyboard-operable.
- **No new slot, no new skill, no new dependency:** the layer rides on the existing `verifyReportPath` report and `render-report.py` (stdlib-only). Captured frames gain a `class="annot-shot"` hook; #45's raster-data-URI allowlist + path-traversal guards are untouched (security-reviewed clean).
- **Honest limitation:** pins bind to the screenshot region in the report's DOM, not the live app's view tree — no CSS-selector / component resolution in the running product.
- Breaking changes: none.

## v1.6.1 — 2026-06-11

**Rendered visual capture + an ephemeral HTML walkthrough for `/flow:verify-build` — visual claims become real PASS/FAIL the autonomy loop can trust, and the human opens a real report at the merge gate (Deliverable-quality track V2/V3a). SAFETY (verify-build gate + findings schema + frame persistence).**

- **Capture-and-persist (SKILL §5a), a11y-gated:** for each declared `Visual-walk` state, flow drives the platform's screenshot MCP itself (XcodeBuildMCP on iOS returns a native frame path; bundled `/verify` only narrates frames to the fresh-context judges — SV2), **in order: snapshot the a11y tree → assert the intended state → screenshot** (never screenshot-then-assume), with a named drive ladder (UI-automation → launch/env hook → can't-reach ⇒ `Unknown` + `not_tested`). Persists a path-referenced `screenshot` + an `a11y_snapshot` (text/status from the a11y tree, not pixels).
- **Two additive findings-buffer fields** (`schema_version` stays `1.0`): `criteria[].grounding` (need / design-language / craft-commitment / open-question) + top-level `open_questions[]` (subjective human calls, distinct from epistemic `Unknown`).
- **Rubric re-grounded:** visual claims judged **pairwise-vs-baseline** (no baseline ⇒ Unknown; first run seeds it), text from the a11y tree.
- **Stdlib HTML renderer (`lib/render-report.py`):** buffer → one self-contained ephemeral report (`verifyReportPath` slot) with grounding callouts, per-dimension verdict cards, a standalone "Open questions for you" block, and a coverage checklist. Raster-data-URI allowlist (security hardening).
- **Loop gate:** an `open_questions[routing=this-iteration]` entry blocks Step 8 auto-advance.
- New `verifyReportPath` slot (22 slots). **Validated by a cold skill-driven `/flow:verify-build` run on a real iOS surface** — round 1 caught 3 `§5a` prose gaps (fixed + FB-0050), round 2 green (FB-0049).
- **Breaking changes:** none.

---

## v1.6.0 — 2026-06-11

**New `/flow:audit-coverage` reviewer closes the under-declaration hole: it flags behavior changes in the diff that no declared `**Spec-walk:**` criterion covers — a behavior verify-build never tested, so the v1.5.3 Test plan would be honestly all-green while the change ships unverified. SAFETY (auditor agent + ship pipeline).**

- **`/flow:audit-coverage` — coverage auditor (13th user-visible skill):** compares the workspace diff against the plan's declared `**Spec-walk:**` criteria and flags each **user-perceptible behavior change no criterion covers**. The complement to verify-build: verify-build checks the declared criteria *pass*; audit-coverage checks the declared set is *complete*. Reuses the `auditor` agent via a new **"Undeclared change"** category (coverage mode) + the existing `extract-criteria.py` parser — no new agent, no duplicated discipline.
- **Routes to the draft manifest, never a hard halt:** each gap is a `[decision-required]` finding → the PR opens as a **draft** until the criterion is declared + verified (re-run verify-build) or the human waives it at the merge gate. The agent must **not** auto-add the missing criterion (grading its own homework). Wired in as the fourth `/flow:ship` Step 2 final-pass reviewer and at the Step 8 readiness boundary.
- **Runs on all platforms** (under-declaration isn't platform-specific — unlike verify-build it does **not** skip on `platform: library|none`); self-skips on doc/test/refactor-only diffs or a plan with no `**Spec-walk:**` block.
- **Honest limitation:** best-effort LLM judgment — it raises the completeness bar, it does **not** deterministically guarantee it (a subtle undeclared behavior can still slip past as a false negative). Not a substitute for the human read at the merge gate. Signal + low-false-positive behavior pinned by `evals/` fixtures (catches a genuine under-declaration; stays silent on a fully-covered diff).

**Breaking changes:** none. Additive — a new reviewer + one new auditor category (coverage mode only); the existing four auditor categories and all other skills are unchanged.

---

## v1.5.3 — 2026-06-11

**The PR `## Test plan` is now rendered from the verify-build findings buffer — a non-forgeable record of behavioral verification, not a hand-authored checklist. The human verifies testing was done and merges, instead of re-verifying. SAFETY (ship pipeline).**

- **`/flow:ship` Step 7 renders `## Test plan` via `skills/ship/lib/render-test-plan.py`:** one checkbox per `**Spec-walk:**` criterion whose state IS the buffer's machine `aggregated_verdict` — `PASS → [x]` (with the adversarial fresh-context judge's evidence quote), `FAIL`/`Unknown → [ ]` (with the judge's reason). The agent can no longer hand-check a box: a green box means a real judge returned PASS. Closes the gap where the Test plan was empty `- [ ]` placeholders disconnected from the verification that actually ran.
- **`not_tested[]` checklist now surfaces in the PR body** (previously only on verify-build's stdout), so the explicit "what we did NOT test" gaps reach the merge gate.
- **Honest fallback, never a forged or stale render:** when verify-build skipped (`verifyEnabled=false`, `platform=library|none`), produced no buffer, or the buffer is stale (its branch/sha ≠ current HEAD) or malformed, the section renders `⚠️ No behavioral gate ran (<reason>); manual verification required` with an unchecked manual line. A `platform: library` repo — including flow's own — always takes this fallback (expected, not a gap).
- **Scope:** attests **behavioral/text** verification only (not visual — that's the Deliverable-quality track's V2), and only over criteria the plan **declared**. A behavior changed without a declared Spec-walk criterion is not yet gated — closing that under-declaration hole (wire `/flow:audit-completion` coverage into the readiness chain) is a queued follow-up. Renderer behavior pinned by `evals/run_render_evals.py`.

**Breaking changes:** none. Additive — Summary + Flow-run table unchanged; the `## Test plan` is now script-rendered rather than hand-authored, and degrades to the manual fallback wherever no buffer exists (i.e. every pre-v1.5.3 case).

---

## v1.5.2 — 2026-06-05

**Makes doc-currency automatic: every `/flow:ship` reconciles the forward-looking roadmap + plan, and a mechanical gate blocks any ship that would leave them stale. Also corrects the upgrade docs. SAFETY (ship pipeline + manifests).**

- **`/flow:ship` Step 5a — doc-currency reconciliation (every ship):** refresh roadmap "Now" (current version, Recently-shipped, ▶ Next-up pointer), sweep shipped plan items → Recently Completed, and clear shipped `FB-XXXX` reservations.
- **`/flow:ship` Step 5b — automatic currency gate:** mechanically asserts the manifest version appears in roadmap "Now" + plan "Current Focus"; blocks the ship and requires reconciliation on drift. Enforced **in the pipeline**, not via the manual `/flow:doctor`.
- **`/flow:doctor` Check 2.6 (secondary):** a manual mirror of the gate for spotting drift between ships — explicitly not the enforcement.
- **`docs/upgrade.md` corrected:** `/plugin marketplace update <name>` updates the installed plugin in one step (not catalog-only); the doc now leads with `autoUpdate` (the no-command path) and fixes the stale "2-command ritual" + the autoUpdate config-example shape.
- Dogfooded: this release fixes the live staleness (roadmap "Now" had read "v1.2.6"; plan "Current Focus" "v1.3.0"), and the new gate self-verifies on this very PR.
- **Breaking changes:** none.

## v1.5.1 — 2026-06-05

**Adds a `Visual-walk` plan field — declared visual/UX acceptance criteria for UI changes. First (cheapest) link in the Deliverable-quality roadmap track toward an autonomous high-quality deliverable.**

- **New plan field `Visual-walk`** (UI changes only; gated on the existing `uiSurface` config slot; N/A under spike/tiny). A plan declares checkable visual/UX assertions — e.g. "empty state renders the zero-data illustration"; "primary button uses the accent token, not a hardcoded hex"; "enter motion ≤ 200ms" — written against the design-language doc (`designLanguagePath`), parallel to the existing `Spec-walk`.
- **Closes a dangling reference:** `workflow.md` Step 8 already told the agent to "dial in visual quality against the plan's declared visual criteria," but no plan field declared them. `Visual-walk` is now that home; Step 8 names the field.
- **Declaration-only.** The criteria are not yet mechanically verified — today's consumers are the agent's Step 8/9 visual dial-in and the human at the plan-approval + merge gates. Rendered capture + verification land in a later roadmap link (V2).
- Touches plan contract surfaces only (`plan-discipline.md`, `planner.md`, `workflow.md`); no new skill, no new schema slot (reuses `uiSurface`). Skill count (12) and slot count (21) unchanged.
- **Breaking changes:** none.

## v1.5.0 — 2026-06-02

**Ship-time gate semantics: unresolved blockers route to a draft PR + NOT-READY manifest, never a silent proceed or a hard mid-loop halt. SAFETY.**

- **Resolution-confidence axis** on `/flow:security-review` + `/flow:accessibility-review`: every BLOCKER is tagged `[auto-fixable]` (one clear, mechanically-verifiable fix) or `[decision-required]` (multiple valid fixes / out-of-repo action like rotating a leaked secret / un-auto-fixable). Default to `[decision-required]` when unsure (FB-0011 ESCALATE-by-default).
- **`/flow:ship` routing:** `[auto-fixable]` BLOCKERs are fixed in-tree; `[decision-required]` BLOCKERs are added to a **draft manifest**. If the manifest is non-empty, the PR opens as a **draft** with a `🚫 NOT READY TO MERGE` block pinned at the top — so an unresolved blocker reaches you at the merge gate instead of halting the loop or producing a merge-ready-looking PR. The manifest integrates with the `## Flow run` PR body (v1.4.1).
- **`/flow:verify-build` at ship is now a confirmation re-run, not discovery.** Behavioral + visual dialing-in happens at the Step 8/9 readiness boundary; ship re-runs verify-build to catch a regression. A non-converging FAIL/Unknown (after the FB-0012 bounded mechanical fix) routes to the draft manifest rather than hard-halting. Visual sign-off folds into the merge gate.
- **Reviewer + ship-spike skills are now model-invocable** (`disable-model-invocation: false` on `/flow:audit-plan`, `/flow:audit-completion`, `/flow:critique-plan`, `/flow:ship-spike`) — the only two human gates are plan approval + PR merge; no skill is itself a gate. The `context: fork` reviewers rely on the v1.4.2 session-discovery fix to resolve transcripts from worktree cwds. Docs (README + workflow.md) updated to label them accurately (BOTH, never cold-start; ship-spike judgment-gated).
- **The v1.4.0 auto-advance predicate is unchanged** — auto-advancing *into* ship still requires a verify-build PASS (FB-0018 invariant). Only ship-*internal* failure handling changed. **Invariant: no merge-ready PR is ever produced on a non-PASS build.**
- `/flow:ship-spike` keeps its verify-build hard-halt (separate scope; follow-up tracks adopting draft-routing there).
- **Breaking changes:** none. New schema slots: none.

## v1.4.2 — 2026-06-02

**Reviewers no longer silently run context-starved from worktree / dotted-path sessions (`extract_session.py` session-discovery fix). SAFETY.**

- `find_session_file` (the session-transcript locator behind `/flow:audit-plan`, `/flow:audit-completion`, `/flow:critique-plan`) reconstructed the `~/.claude/projects/<dir>` name by replacing only `/` with `-`. Claude Code replaces **every** non-alphanumeric character (so `.`, `_`, spaces too). Any working directory containing a `.` — e.g. every `.claude/worktrees/...` session — mismatched, and the reviewers reported "session file not found" and audited nothing. Encoding now mirrors Claude Code exactly.
- Discovery now **prefers an exact match via `CLAUDE_CODE_SESSION_ID`** (which Claude Code exports into spawned subprocesses, including a skill's `!`-backtick substitution), independent of cwd encoding; the corrected cwd-slug is the deterministic fallback, and an unresolved lookup still returns `None` gracefully (no crash). The session-id is validated to `[A-Za-z0-9_-]+` before it reaches the filesystem glob, so a tampered/malformed value can't wildcard-match or traverse to other transcripts.
- New regression fixture `plugins/flow/evals/security/test_session_discovery.py` covers the encoding (dotted / `_` / space paths), the session-id primary, the slug fallback, the graceful-`None` case, glob-injection payloads, and the ambiguous-id guard.

**Breaking changes:** none. Pure correctness fix to session preprocessing; reviewer output schemas, slot counts, and all other surfaces unchanged. Consumers running from a normal (dot-free) project root were unaffected; the fix additionally hardens worktree / dotted-path usage.

## v1.4.1 — 2026-06-01

**PR descriptions now document the full flow-loop run — a per-step `## Flow run` table replaces the generic `## Reviews` blurb.**

- `/flow:ship` §7 PR body gains a `## Flow run` table: one row per loop step (Clarify → Plan+critique → Execute → Preflight → /simplify → /flow:staff-review → security/a11y/verify-build → Doc synthesis), each marked `✓` (ran) or `skipped (<reason>)`, with a **Notable** cell for genuine signal (a plan-critic catch, a load-bearing decision, a fixed BLOCKER, a real review finding) or `—` when routine. The ship agent fills it from the session's loop history and is **instructed not to manufacture notes**.
- Skip reasons are mode- and config-dependent and always named: spike skips `/simplify` + `/flow:staff-review`; tiny also skips the spec-walk; `/flow:accessibility-review` skips on `uiSurface:false` or a non-UI diff; `/flow:security-review` on a doc-only diff; `/flow:verify-build` on `verifyEnabled:false` or `platform` `library`/`none`. (`skipped — not yet shipped` is reserved for a step genuinely absent from the running flow version — never written for a step that actually ran.)
- `/flow:ship-spike` writes a trimmed version of the same table (fewer rows; `/simplify` + `/flow:staff-review` pre-marked `skipped (spike)`).
- `plugins/flow/docs/workflow.md` §10 + the spike section narrate the new PR-body shape; the dogfood dev-side `/ship` mirrors it. Follow-ups remain canonical in the roadmap/plan docs — the table only points at them; the PR is still never merged.

**Breaking changes:** none. Additive — Summary + Test plan are unchanged; only the trailing review blurb is replaced by the richer table.

## v1.4.0 — 2026-05-30

**`/flow:ship` is now auto-invocable — the autonomous-loop trigger (human gates stay at plan + merge).**

- `/flow:ship` frontmatter `disable-model-invocation` flipped `true → false`. The agent auto-advances from Step 8 into the ship pipeline when the **ship-readiness predicate** holds — every spec-walk checkbox checked, no open BLOCKER from `/simplify` or `/flow:staff-review`, no unresolved MEDIUM/LOW-confidence assumption, and `/flow:verify-build` would return PASS (not merely "didn't fail") — AND the FB-0011 risk gate is clear (no unclear path / significant risk / competing comparable options / one-way-door). Otherwise it stops and presents.
- `plugins/flow/docs/workflow.md` Step 8 rewritten as a **conditional gate**; `plugins/flow/rules/general.md` adds a workflow-discipline bullet encoding the trigger.
- **Stays manual:** when `/flow:verify-build` is skipped (`platform` `library`/`none`, or a doc-only diff) there is no behavioral gate, so those still require an explicit "ship it"; `/flow:ship-spike` keeps `disable-model-invocation: true` (spikes are user-initiated by nature).
- The two load-bearing human gates — **plan approval (Step 2)** and **merge (Step 11)** — are untouched. Ship still never merges.

**Breaking changes:** none. Additive — typing `/flow:ship` / saying "ship it" works exactly as before; the new path is autonomous advance only once a driven loop reaches Step 8 with a green predicate. It never starts from a cold request. Reviewer/skill output schemas unchanged.

> **Note:** v1.2.6 (bounded-retry mechanical preflight) and v1.3.0 (`/flow:verify-build`) shipped without CHANGELOG entries — backfill tracked as a follow-up.

## v1.2.5 — 2026-05-27

**Adversarial sharpening of the reviewer pipeline (PR J; research-grounded — see Anthropic's "adversarial review step" best-practice + CriticGPT recall results).**

- `auditor` agent gains a **Self-check before emitting** step: each finding must survive an attempted disproof — name the specific session text that would invalidate the finding, re-scan for it, drop if found or if the lookup is fuzzy. Mitigates the documented "reviewer prompted to find gaps will report some even when work is sound" failure mode.
- `plan-critic` agent gains the same self-check adapted to the two-citation rule: each finding must survive an attempted third citation that would resolve the apparent conflict. Plan-critic's `Internal incoherence` category now also explicitly covers **fan-out contradictions within the plan** (count/name/slot/version referenced in N places where values disagree) — PR-G FOLLOW-UP #5 absorbed.
- `lens-staff-engineer` agent gains an explicit **adversarial reading** preamble ("assume the diff is broken — what's the most likely break?"). This is the engineer-lens analog of the security lens's threat-model stance; the published research convergence is that explicit "find the break" framing materially raises recall on real defects.
- `/flow:security-review` agent prompt shifts to **fully red-team identity** ("you are a red-team operator; your goal is to find an exploitable vulnerability — not to evaluate whether the code is good"). Adds a trace-input-source-back disprove step: if the dangerous sink can't be reached via a concrete attacker scenario, drop the finding. Operational logic (FB-0006/FB-0007 source-file early-exit, FB-0008 `[ -z ]` defaultBranch fallback chain discipline, FB-0009 fail-fast gh+jq, three-source diff capture) unchanged.
- All four edited prompts adopt Anthropic's verbatim *"flag only gaps that affect correctness or the stated requirements, and treat the rest as optional"* warning at the top of each prompt, before any category logic — the explicit countermeasure to the over-engineering tax adversarial framing brings.

**Breaking changes:** none. Prompt-only PR; existing eval fixtures remain green. Reviewer output schema unchanged. The change is additive: clean diffs continue to produce `No issues flagged.` / `APPROVED`; the sharper recall surfaces on diffs that genuinely warrant it.

## v1.2.4 — 2026-05-27

**Workflow-spawn skip prevention (FB-0010 workflow-step sub-class).**

- `/flow:staff-review` now ends with an explicit "After this skill" footer naming `/flow:ship` as the canonical next step. Reframes the existing "ends with work ready, not merged" line into actionable forward motion.
- `/flow:ship` Step 1.0 workflow-step assumption surface gains `⚠️` visual emphasis per ASSUMES line + a REMINDER paragraph explicitly naming the "never bypass `/flow:ship` with `gh pr create`" rule.
- `plugins/flow/docs/workflow.md` Step 10 adds a "Never bypass `/flow:ship`" subsection. Names the failure mode: skipping `/flow:ship` skips the entire Step 2 (security + a11y reviews) of the pipeline, and the `STATUS: SKIPPED` audit-trail signal is load-bearing even on docs-only PRs.
- Defends against the 9th FB-0010 incident, surfaced during PR H1 when the author skipped spawning `/flow:security-review` + `/flow:accessibility-review` and ran `gh pr create` directly. 1 incident isn't usually enough for FB encoding, but the fix is trivially mechanizable (prompt-level reminders + workflow.md discipline statement).

**Breaking changes:** none. Additive workflow guardrails — no skill behavior or contract changed.

## v1.2.3 — 2026-05-27

**Consistency discipline (FB-0010 defense for the recurring bug class.)**

- `lens-staff-engineer` agent now explicitly hunts two flavors of "consistency that depends on author memory": silent-skip on edge case (failures swallowed via `2>/dev/null` / unset-fallback / regex inversion) + fan-out contradiction (count/name/slot referenced in N places, only some updated).
- `/flow:doctor` gains **Check 2.5** comparing the schema's actual slot count (`jq '.properties | keys | length'`) against any documented "N slots" claim in `CLAUDE.md` / `README.md` / `docs/` / `core-docs/` / `dev-docs/`. Flags WARN on mismatch.
- `plugins/flow/docs/workflow.md` Step 4 adds a "Consistency sweep" paragraph naming the discipline at preflight, before `/simplify` runs.
- Defends against the most-recurring bug class flow's own development has surfaced — 6 incidents across PRs 1, B, D, E, F (pass 1), F (pass 2).

**Breaking changes:** none. Additive prompt + new doctor check + new workflow.md paragraph.

## v1.2.2 — 2026-05-26

**Consumer dogfood-readiness.**

- New skill: `/flow:doctor` — PASS/FAIL/WARN punch-list verifying flow is correctly installed + project is correctly configured. Use after `bootstrap.sh` or any time something feels off.
- New scaffolder: `template/base/bootstrap.sh` — one-command project setup (`bash bootstrap.sh --stack web|swift|tauri-rust-ts`). Idempotent; re-running on a populated project skips existing files.
- New walkthrough: `docs/first-pr.md` — step-by-step concrete guide for your first PR through the loop.
- Refreshed `README.md` + `template/base/CLAUDE.md.template` — explains the 3-layer enforcement mechanism (auto-loading rules + skill triggers + `/flow:ship` Step 1.0 surface).

**Breaking changes:** none.

## v1.2.1 — 2026-05-25

**Consumer-feedback follow-ups (5 fixes from md-manager's first real-consumer dogfood report).**

- **Stale-base preflight** in `/flow:ship`, `/flow:ship-spike`, `/flow:staff-review` Step 1 — prevents the "fork from old base → phantom-deletion diff" class of waste before any expensive review runs.
- **Marketplace install verification** docs (`docs/bootstrap.md` + `docs/migration.md`) — adds `/plugin marketplace list | grep '^flow'` step to catch the silent-omission failure when a stale `extraKnownMarketplaces` key points at flow's URL under a non-canonical name (FB-0005).
- **`/flow:ship` Step 1.0 workflow-step assumption surface** — prints which workflow steps `/flow:ship` ASSUMES already ran (critique-plan, simplify, staff-review). Skips become visible at ship time.
- **Per-diff non-UI early-exit** in `/flow:security-review` + `/flow:accessibility-review` — checks the diff for source/UI files; skips with `STATUS: SKIPPED` if none present. Saves spawn cost on docs-only PRs even for `uiSurface: true` projects.
- **`gh` + `jq` CLI fail-fast** — `/flow:ship` + `/flow:ship-spike` Step 1 check `command -v gh` / `command -v jq` and exit 1 with install hint if missing, rather than exit 127 at the invocation site. `/flow:staff-review` adds warn-only check (gh is optional there).

**Breaking changes:** none. All additive guardrails.

## v1.2.0 — 2026-05-25

**Consumer scaffolding (template directory + bootstrap/migration docs).**

- New `template/base/` — Tier 1 (CLAUDE.md.template, flow.config.json.example, .claude/settings.json.example, .claude/rules/safety.md.template, README.md.template, .gitignore.template) + Tier 2 (5 core-docs scaffolds: spec, plan, roadmap, history, feedback with format headers).
- New `template/stacks/{web,swift,tauri-rust-ts}/` — per-stack overlays: preflight runner, CI workflow, `.gitignore.append`, UI/dev-server rules (web + tauri), link skill (web + tauri).
- New `docs/bootstrap.md` — step-by-step adoption walkthrough for new projects, all 3 stacks covered.
- New `docs/migration.md` — 3-stage migration pattern for existing projects with prior `.claude/` content (install non-breaking → dogfood validate → delete duplicates).
- New security regression fixtures: `plugins/flow/evals/security/test_cwd_constraint.py` + `test_malicious_config.py` — protects against path traversal + shell-meta injection through `flow.config.json` values.
- Schema's first published slot set (current count lives in `plugins/flow/schema/flow.config.schema.json` — the single source of truth).

**Breaking changes:** none. Templates are consumer-pulled, not plugin-pushed.

## v1.1.0 — 2026-05-24

**Full workflow surface backfill.**

- 5 new shipped skills: `/flow:staff-review` (4 parallel lenses), `/flow:security-review`, `/flow:accessibility-review`, `/flow:ship-spike` (spike-mode lightweight pipeline), `/flow:workflow-help` (11-step loop + resolved config slots).
- 6 new shipped agents: `planner` + `docs` (context-isolation helpers), plus 4 staff-review lens agents (`lens-staff-engineer`, `lens-ux-designer`, `lens-design-engineer`, `lens-push-further`).
- 4 portable auto-loading rules: `general.md` (workflow discipline on every edit), `plan-discipline.md` (required plan fields + LOW=gate), `documentation.md` (history/feedback/plan format rules), `exploration.md` (§ Exploration triggers).
- New memory tool: `plugins/flow/tools/memory/check.mjs` — failure-pattern corpus cap + audit-due check.
- New `plugins/flow/schema/flow.config.schema.json` — JSON Schema for `flow.config.json`. The schema is the single source of truth for slot count + names; the README + `/flow:doctor` Check 2.5 derive from it.
- New default hooks at `plugins/flow/hooks/default-hooks.json` — opt-in PreToolUse hooks (sensitive-file write blocker + path-validation warn).
- `/flow:ship` PR-1 limitations backfilled (`/flow:security-review` + `/flow:accessibility-review` now wire in; memory machinery now active).

**Breaking changes:** none. PR-1 placeholder behavior replaced with real implementations.

## v1.0.0 — 2026-05-24

**Marketplace restructure + rename from `byamron/llm-auditor` → `by-dev-tools/flow`.**

- Repository renamed in place + restructured into Anthropic marketplace + plugin shape: marketplace at `.claude-plugin/marketplace.json` (one plugin: `flow`); plugin manifest at `plugins/flow/.claude-plugin/plugin.json`.
- 5 shipped skills: `/flow:ship` (port from md-manager's `/ship`), `/flow:audit-plan`, `/flow:audit-completion`, `/flow:critique-plan`, `/flow:log-disagreement` (the last 4 ported from the prior `assumption-auditor` plugin).
- 2 shipped agents: `auditor`, `plan-critic`.
- New canonical loop reference: `plugins/flow/docs/workflow.md` — the 11-step managed-autonomy loop.
- Pre-v1.0.0 content recoverable via `git checkout pre-flow-plugin`.

**Breaking changes:** install identity changed. Old `assumption-auditor@llm-auditor` users must re-add via `/plugin marketplace add by-dev-tools/flow && /plugin install flow@flow`. GitHub maintains a `byamron/llm-auditor` → `by-dev-tools/flow` redirect, so old clones still pull from the same place. The old user-scope `extraKnownMarketplaces.llm-auditor` key continues to resolve at the URL level but is invisible to the resolver (`enabledPlugins.<plugin>@<marketplace>` matches the marketplace's `name` field, NOT the user-scope settings key) — see FB-0005 and `docs/migration.md` for the install verification step that catches this.

---

## Notes on versioning

- Flow follows **semver as a discipline, not a contract**. Patch bumps (`1.2.x`) aim to be additive; minor bumps (`1.y.0`) add user-visible surface; major bumps (`x.0.0`) are reserved for breaking changes (none have happened). The discipline is enforced by `lens-staff-engineer` review + `/flow:doctor` Check 2.5 + author care — there is no mechanical gate today that BLOCKS a breaking change from landing in a patch bump. Always verify upgrades with `/flow:doctor`; treat any patch-level regression as a bug worth filing.
- The plugin manifest version (`plugins/flow/.claude-plugin/plugin.json`) and marketplace metadata version (`.claude-plugin/marketplace.json`) are kept in sync.
- **Docs-only changes at the repo root** (e.g., this CHANGELOG itself, `docs/upgrade.md`) ship without a version bump — they don't change plugin behavior and consumers fetch them from GitHub directly, not via `/plugin install`.
