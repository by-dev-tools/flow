# FB-0141 — `CLAUDE_PLUGIN_ROOT` is not guaranteed inside a forked skill's `!`-block, and a flow-repo-relative fallback is not a fallback

**Date:** 2026-11-01
**Source type:** review feedback (external agent field report, relayed as user direction)
**Applies to:** every `!`-preprocessor block in a `context: fork` skill; all helper-script
resolution in `plugins/flow/skills/*/SKILL.md`; `run_scratch_isolation_evals.py`; CLAUDE.md
§ How to Work 3; `flow_scratch.py`'s module docstring
**Surfaced by:** an external agent working in `byamron/portfolio` against an installed flow **1.29.0**:
every `/flow:audit-skips` run reported `stamp_unverifiable`, while running
`skills/audit-skips/lib/skip-audit-checks.py` directly worked. Relayed by Ben.

## What was said

`/flow:audit-skips`, run against an installed flow **1.29.0** in `byamron/portfolio`, reported
`stamp_unverifiable` on every invocation, while invoking `skills/audit-skips/lib/skip-audit-checks.py`
directly worked. Nothing was wrong with the handoff, the repo, or python3 — the gate could not reach
its own checker.

## Synthesized rule

**A resolution arm that only resolves inside this repo is not a fallback, and neither resolution arm
may be assumed.** Resolve a plugin helper through the host variable *or* the host's install record,
identity-check every candidate root, keep the checkout arm for dogfooding, and prove it with a case
staged from a simulated install — never from this checkout, where the broken arm is the working one.

## The correction

Two beliefs this repo had written down were wrong, and they compounded.

**1. CLAUDE.md § How to Work 3 says `CLAUDE_PLUGIN_ROOT` is "unset in Bash-tool calls and set in
`!`-preprocessor blocks."** The second half does not hold. Measured 2026-11-01, v1.64.0, one session:
`Skill("flow:audit-skips")` (`context: fork`) ran its `!`-block with **CPR unset**, while
`Skill("flow:audit-plan")` — also `context: fork`, and whose block is
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py` with *no* fallback — ran fine in the same
session. So CPR is present in some forked context blocks and absent in others. **Why it differs is
NOT established** (see Limits). `flow_scratch.py`'s own docstring asserts the same thing — "a skill's
`!`-block ... where CLAUDE_PLUGIN_ROOT IS set" — and `dev-docs/history/2026-07-29-safety-flow-s-ephemeral-scratch-moves-from-tmp-to-a-repo-loc.md`
repeats it as the reason the read side may use a Python helper. All three say the same unmeasured thing.

**2. `plugins/flow/...` is not a fallback; it is a second way to fail.** It is **flow-repo-relative**.
In a consumer project that path cannot exist by construction, so the "two-arm" resolution
(`$CLAUDE_PLUGIN_ROOT`, else `plugins/flow/...`) has **no arm that works for an installed plugin when
the host variable is absent** — which is precisely the situation belief 1 said could not arise.

## Why it survived 35 releases

Arm 2 resolves in exactly one place: the flow checkout. So every test, and every dogfooding run,
exercised the arm that works. `run_scratch_isolation_evals.py`'s `block-*` cases
`export CLAUDE_PLUGIN_ROOT="{FLOW}"` before executing the block — they could not observe an unset CPR —
and the case that would have caught it (`checkout-cpr-unset-resolves`) **passes on the broken code**,
because in the checkout the broken arm is the working one. A measurement that can only return clean:
`general.md` item 4, in the harness built to execute the shipped block *because* a prior bug hid there.

## How to apply

- **A fallback that resolves only inside this repo is not a fallback.** Before writing
  `plugins/flow/<x>`, ask what that path means in a consumer project. If the answer is "nothing", the
  arm is decoration and the real behaviour on that branch is failure.
- **Never assume either resolution arm.** Both are now measured to miss. Resolve through the host's
  install record (`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/installed_plugins.json`), identity-check
  each candidate against its own `.claude-plugin/plugin.json`, and keep the checkout arm for
  dogfooding only.
- **Not a glob.** `~/.claude/plugins/cache/*/flow/*/` is the obvious shortcut and is wrong: a host can
  hold several cached versions (this one holds 1.29.0 and 1.64.0), so a glob can run one version's
  engine against another version's handoff.
- **A regression case for an install-path bug must come from a simulated install.** In-repo it is
  structurally invisible. Pair the consumer-layout positive with its mutation (remove the install
  record → must refuse), and name each assertion separately so the failure says which one died
  (FB-0136).
- **When a gate says "I could not verify", suspect the gate's own resolution before the subject.**
  `stamp_unverifiable` is the honest, fail-closed output, and it was correct every time — the gate was
  never able to look. Fail-closed stopped this from becoming a false clean pass; it did not stop it
  from being invisible, because nobody reads a "couldn't verify" line as a bug report.

## Limits of what was measured

- Why CPR is set for one forked skill and unset for another in one session is **unknown**. I could not
  probe the fork's environment: edits to the installed SKILL.md have no effect (the skill body is
  cached at session start) and `claude -p` is not logged in on this host. The fix therefore assumes
  neither state.
- **One tempting hypothesis is already refuted — do not spend a probe on it.** "CPR is dropped on
  programmatic `Skill()` invocation but kept when the user types the command" is a natural guess and it
  is wrong: both `flow:audit-plan` (CPR set) and `flow:audit-skips` (CPR unset) were invoked through
  the **Skill tool**, in one session, same mode, opposite outcome. Whatever the cause is, it is not
  invocation mode.
- The 1.29.0 report was not re-run. Its shape matches exactly, and 1.29.0's installed SKILL.md carries
  resolution identical to 1.64.0's (and *does* ship `scripts/flow_scratch.py`, so "the release lacked
  the checker" is not the mechanism) — but this is inference from an identical artifact, not a
  reproduction of their session.
- The fix could not be verified through a real forked invocation this session, for the same
  body-caching reason (FB-0107): a ship run's prose comes from the installed tree. It is verified by
  extracting and executing the shipped `!`-block, which was shown to be faithful — the real fork's
  output was **byte-identical** to the extracted block run with CPR unset and the fallback absent.

## The class, not the instance — ~35 sites, not five

**I first wrote "five `!`-block fork skills." That was a ~7x under-count**, caught by this PR's own
`/simplify` reuse pass and then verified by grep. The flow-repo-relative arm is also in **13
`resolve-doc-slot.sh` preludes across 8 skills** and **17 bare `${CLAUDE_PLUGIN_ROOT:-plugins/flow}`
defaults across 5**. Anyone closing the roadmap item after four skills closes ~31 open sites.

**Fix the fail-OPEN instances first.** `audit-skips` failed *closed* — it announced "I cannot verify"
on every run. `audit-plan` and `audit-completion` have **no fallback at all**, so an unset CPR makes
the command `python3 /scripts/extract_session.py`, the extractor never runs, and the reviewer audits an
**empty session context** — then reports "No issues flagged." Verified: `plugins/flow/agents/auditor.md`
has *no* empty-context guard, so nothing catches it. A reviewer that cannot see, returning the output
that means "I looked and it was fine."

**The bare-default form is a separate, security-shaped item.** `${CLAUDE_PLUGIN_ROOT:-plugins/flow}`
is an *unconditional* cwd-relative `python3` target with no identity check — the shape
`skills/doctor/SKILL.md`'s own SECURITY header records as having shipped once and been arbitrary code
execution from any repo the user opened. It needs the default *removed*, not widened, so it must not
be folded into the reachability port.

**And the port must carry the security decision, not just the mechanics** — see below. Copying the
three arms into four more deployed prompts without it propagates a cwd-execution arm four times.

## A content check is not an identity check

Worth separating, because I got it wrong in the first draft and the wrong version is the flattering one.

Both greps in the resolver (`"name": *"flow"` on a candidate's own `plugin.json`) detect a
**mis-install**. Neither authenticates anything: no file inside a tree can authenticate that tree
against whoever wrote it. What makes the install-record arm safe is not its grep but its *location* —
forging it means writing to the user's own config dir, where `settings.json` hooks already live, so
anyone who can do that has easier options. The cwd-relative arm has no such property, and this block
runs after a `cd` into the repo under review. My first draft wrote that a failed lookup "degrades to a
loud refusal, never a false pass"; it degrades to the **cwd arm**. Write what the gate detects, not
what you hope it prevents.

Related: [[FB-0107-dogfooding-runs-the-installed-plugin-not-the-branch-under-review]],
[[FB-0136-a-detector-validated-only-against-its-own-vocabulary]], [[FB-0082]], [[FB-0074]].
