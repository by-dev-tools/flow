# Handoff — Anthropic blog/docs research → flow improvement findings

**Status:** research captured, unshipped; no plugin artifact changed. Ready for pickup.
**Branch:** `claude/twitter-x-flow-research-28ghls` (4 commits, pushed, working tree clean, **no PR**).
**Repo:** `by-dev-tools/flow`, branched off `main`.
**Session dates:** 2026-07-24 → 07-25.

---

## What this session did

The user asked to read Anthropic's published guidance (originally an X link; pivoted to `claude.com/blog` + docs once X proved unreachable) and synthesize how flow can better exploit what Claude now offers. Outcome: a 15-finding research block in `dev-docs/plan.md § RESEARCH`, one new feedback rule (**FB-0072**, model-recency), and this handoff. **Analysis only — zero changes to `plugins/flow/*`, scripts, or prompts.** All four commits touch `dev-docs/` exclusively.

Sources read in full: `[A]` the-new-rules-of-context-engineering (pasted), `[B]` a-field-guide-to-claude-fable-finding-your-unknowns, `[C]` building-verification-loops-in-claude-code-with-skills, `[D]` steering-claude-code, `[E]` getting-started-with-loops, `[F]` multi-agent-coordination-patterns. 42 blog posts enumerated total; 36 unread.

## The findings that matter (full detail in `plan.md § RESEARCH`, Findings 1–15)

- **F11 — reword CLAUDE.md rule 5 (do first; unblocks the rest).** Rule 5 says "never wrap a bundled skill"; `[C]` recommends "build a custom wrapper skill that invokes the original." Intents agree (don't *re-implement* — earned by FB-0015 — vs. wrap-to-*extend*), but the word "wrap" is inverted and a literal reading rejects a valid chain. Fix the wording in `CLAUDE.md:125` AND the shipped `plugins/flow/docs/workflow.md:70` ("does not wrap"), keep FB-0015's don't-reimplement intent, permit chaining/composition. FB-0010 sweep: `git grep -n "wrap\|parrot"`.
- **F10 — re-open the bundled `/verify` spike.** A native `/verify` skill now exists and `[C]` says try it first; native analogues also exist for staff-review (Code Review preview), spec validation, rubric grading. `verify-build` is the load-bearing gate, so this is a live rule-5 question. Existing `## SV2-spike` in plan.md predates the post — re-run it against the current `/verify`. Blocks F2 (splitting `ship`) from being wasted work.
- **F12 — pre-plan unknown-discovery step (largest product gap).** `[B]`'s leverage is *upstream* of the plan (blind-spot pass, interview-me, prototype-to-react, source-as-reference); `plan-critic` only critiques a plan that already encodes the author's blind spots. Net-new skill shape (`/flow:discover` or a step 1–2 phase), not a tweak.
- **F9 — flow isn't installed in cloud sessions (measured).** No `~/.claude/plugins/`, empty `enabledPlugins`. So `.claude/rules/general.md`'s "always `/flow:ship`, never `gh pr create`" is unfollowable here. Fix: setup script writes `.claude/settings.json` `enabledPlugins."flow@flow": true` + registers a local marketplace (clone flow to a known path — avoids the untested "does registering fetch content" question). **This is the prerequisite for opening any PR from a cloud session the sanctioned way.**
- **F13/F14/F15 — cheap follow-ons + validation.** Native `/goal` overlaps Spec-walk criteria (F13). `[F]` names flow's thesis as the industry's most common failure ("illusion of quality control without substance") AND documents the orchestrator bottleneck `staff-review`'s lens fan-out inherits → add to honest-limitations (F14). `general.md` ships `paths: ["**/*"]` = always-on in every consumer session; re-examine vs `[A]`'s cut-scaffolding mandate (F15).
- **F1–F8** (first pass): doctor/native-`/doctor` name collision (F1); `ship/SKILL.md` 1096 lines splits no prose (F2); this repo's CLAUDE.md is 41/136 lines of path tables (F3); possible ship-§4b auto-memory overlap, unverified (F4); the evals make the "80%-deleted, no loss" claim testable here (F5); `[A]`/`[B]` delete-vs-protect tension resolved as flow's own thesis (F6); 3 skill descriptions exceed the documented 1024-char limit (F7); flow's own 71-FB + fixture corpus may encode pre-Claude-5 assumptions (F8, coupled to F5 — audit fixtures BEFORE the strip-and-measure experiment or a stale fixture inverts the result).

## DO THIS FIRST — verify Anthropic engineering-blog access

`anthropic.com` / `www.anthropic.com` are in the environment's Custom allowlist (screenshot-confirmed) but were **NOT reachable from the previous container** (`403 Host not in allowlist` while `claude.com/blog` = 200). Likely the edit landed on a different environment than the running session, or the container needed a restart.

**Check:** `curl -sS -o /dev/null -w '%{http_code}\n' -L https://www.anthropic.com/engineering`
`200` → proceed. `403` → confirm you edited the environment THIS session runs on, or the allowlist just isn't picked up yet.

**Access mechanics:** the blog allowlist lives on the *environment* (server-side), inherited by every session — nothing in the repo grants it. **`WebFetch` 403s here regardless of the allowlist** (different network path); the working pattern is `curl` + a stdlib HTML→text extractor (regex strip of script/style, headings→`##`, tags→space, unescape). See `plan.md § RESEARCH` method note.

## Then — read these 5 engineering posts, fold in as Findings 16+ (priority order)

Higher-value than the 6 already read — they're about building agent *harnesses*, which is what flow IS.
1. `anthropic.com/engineering/effective-harnesses-for-long-running-agents` — closest thing to a spec for what flow attempts. **Read first.**
2. `anthropic.com/engineering/multi-agent-research-system` — primary source `[F]` only summarizes; firms up F14's orchestrator-bottleneck.
3. `anthropic.com/engineering/effective-context-engineering-for-ai-agents` — depth companion to `[A]`; bears on F2 + F3.
4. `anthropic.com/engineering/writing-tools-for-agents` — examples→interface-design at depth.
5. `anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills` — skill-authoring source of record.

Also unread and worth a pass (claude.com, already reachable): `ai-code-migration`, `artifacts-in-claude-code`, `how-anthropic-secures-its-ai-native-software-development-lifecycle`, `product-development-in-the-agentic-era`, `claude-model-and-effort-level-in-claude-code`, `harnessing-claudes-intelligence`.

## Open decisions (user's call — do not assume)

- **Open a PR?** Merging only buys discoverability-on-main (findings already survive on the branch). To be review-worthy the PR should carry a change — natural candidate is **F11**. But honoring `.claude/rules/general.md` (no `gh pr create`) requires `/flow:ship`, which needs **F9** done first. So: F9 → F11 → ship via `/flow:ship`, OR open manually and document the deviation.
- **Read remaining 36 posts, or start acting on findings?** User leaned toward wrapping up; not decided.
- **Does F12 become a scoped PR?** New skill shape — sizing is a plan-gate decision.

## Standing preference set this session

**FB-0072:** weight research by model era. The Claude 5 generation inverted six prior best practices, so older/undated guidance is *suspect*, not merely lower-priority — and this applies inward to flow's own FB corpus and fixtures. Record the model era a claim was made about, alongside the claim.
