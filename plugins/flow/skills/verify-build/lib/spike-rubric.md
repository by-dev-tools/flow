# Spike-mode rubric

This file is loaded by `/flow:verify-build` Step 6 when spike mode is active. Spike mode replaces the plan-derived criteria with three fixed checks; the judge runs single-dimension (`correctness` only) since `regression` and `scope-creep` are not meaningful absent a plan defining scope.

The rubric structure mirrors `lib/rubric.md` (PASS / FAIL / Unknown, two-citation rule, Unknown ⇒ block) so a consumer of the findings buffer cannot tell from the schema whether it was a spike or a full run except by inspecting `metadata.spike_mode`.

---

# Spike-mode behavior verification

You judge whether bundled `/verify`'s observations demonstrate three fixed launch-and-smoke checks on a feature that has no plan. You are spawned in `correctness` dimension only — spike mode is too coarse for `regression` or `scope-creep` judgment (the latter two are not meaningful without a plan to define what's in vs out of scope).

## When this rubric fires

This 3-check smoke rubric is used by exactly two Step-2 paths (see `SKILL.md` § 2):

1. **Explicit spike** (`MODE=spike`) — invoked by `/flow:ship-spike`. The user/agent has explicitly chosen the lower bar. The orchestrator stamps `metadata.spike_mode=true` and every criterion `provenance: "spike-rubric"`.
2. **Docs-only no-plan fallback** (`MODE=no-plan` + `NO_PLAN_SCOPE=docs-only`) — the plan path is missing or has no `**Spec-walk:**` block AND the diff touches no source files, so there is little runtime behavior to verify. The orchestrator stamps `metadata.no_plan_fallback=true` and `provenance: "spike-rubric"`.

**This rubric does NOT fire for a *source-touching* no-plan diff.** That case takes the robust judged path (`SKILL.md` § 2b: diff-derived criteria + the full Step-4 adversarial transform + Step-6 judges, provenance `adversarial-judged`) — production code that merely lacks a plan artifact gets a real judged verification, not a 3-check smoke test.

Don't apply full-rubric strictness; do apply the same evidence + Unknown discipline. Your verdict is still machine-produced (you run in fresh context), so it earns `spike-rubric` provenance — never `hand-authored`.

## The three checks (fixed)

These are the "criteria" for spike mode. Treat them as criteria in the same shape as full-mode plan criteria — same verdict definitions, same two-citation rule, same Unknown-aware gate.

### Check 1: Launch

**Criterion text (verbatim — use this exact string in output):**
> "Launch — the app starts without immediately crashing, panicking, or failing to bind/serve."

Looking for evidence of:
- App process started and remained running for at least one observable moment
- No fatal-error stack trace at startup
- For server/web: bound to expected port; for CLI: process didn't exit before stdin/argv processed; for TUI/Electron: UI rendered
- For library: not applicable — spike mode for library projects should have been skipped before reaching the judge

PASS evidence example: "Server listening on port 5173. Initial page rendered with title 'My App'."
FAIL evidence example: "Process exited with code 1. stderr: 'Cannot find module: ./missing-dep'."
Unknown evidence example: "Bundled /verify output was empty; cannot confirm launch succeeded."

### Check 2: One happy step

**Criterion text (verbatim):**
> "One happy step — the most obvious happy-path action executes one step successfully and produces an observable side effect."

What "the most obvious happy-path action" means varies by platform:
- **Web/Electron:** load the page, click the most-prominent interactive element (the primary call-to-action button, the main nav item).
- **CLI:** run the command with the documentation example invocation; check exit code + stdout.
- **Server:** issue the documented health-check or root request; check status code + payload.
- **TUI:** start the app, press the first documented keybinding.
- **iOS/Android:** launch, tap the most-prominent UI element on the home/initial screen.

PASS requires: action executed AND an observable side effect occurred (network request, state change, navigation, file write, log line).

PASS evidence example: "Clicked the 'Sign in' button. Modal appeared with email + password fields."
FAIL evidence example: "Clicked 'Sign in' button; no visible response; no network request fired; no console activity."
Unknown evidence example: "Couldn't determine which action was the happy-path action; nothing in the verify output suggests one was tried."

### Check 3: No log errors

**Criterion text (verbatim):**
> "No log errors — no uncaught console errors, unhandled promise rejections, ERROR-level log lines, or red stderr output during launch + the one step."

Looking for evidence of absent errors. Note: warnings are not errors. Deprecation notices are not errors. Info-level log lines are not errors. ERROR / FATAL / panic / unhandled-exception are errors.

PASS evidence example: "Console output during launch + sign-in click: 3 info lines, 0 warnings, 0 errors."
FAIL evidence example: "Console shows: TypeError: Cannot read property 'foo' of undefined at HomePage.tsx:42."
Unknown evidence example: "Bundled /verify did not capture console output; cannot confirm error-free."

## Verdict semantics — same as full mode

For each of the three checks, return PASS / FAIL / Unknown with two-citation evidence per `lib/rubric.md` discipline. Unknown verdicts block ship per FB-0011.

The spike rubric is deliberately minimal: three checks total, single dimension. A spike that passes all three checks isn't "verified" in the full sense; it's "didn't immediately collapse." The user explicitly chose spike mode by invoking the spike workflow, which carries the documented lower-bar semantics.

## Output schema

Same shape as `lib/rubric.md` — JSON with `dimension` + `verdicts[]`, but always exactly three entries in `verdicts[]` corresponding to the three checks above (in that order).

```json
{
  "dimension": "correctness",
  "spike_mode": true,
  "verdicts": [
    {
      "criterion": "Launch — the app starts without immediately crashing, panicking, or failing to bind/serve.",
      "verdict": "PASS|FAIL|Unknown",
      "evidence": [
        "<observation quote>",
        "<verbatim criterion text>"
      ],
      "notes": "<one sentence if FAIL or Unknown; empty if PASS>"
    },
    {
      "criterion": "One happy step — the most obvious happy-path action executes one step successfully and produces an observable side effect.",
      "verdict": "...",
      "evidence": ["...", "..."],
      "notes": "..."
    },
    {
      "criterion": "No log errors — no uncaught console errors, unhandled promise rejections, ERROR-level log lines, or red stderr output during launch + the one step.",
      "verdict": "...",
      "evidence": ["...", "..."],
      "notes": "..."
    }
  ]
}
```

Constraints:
- Exactly three verdicts entries, in the order above.
- Use the verbatim criterion text strings as shown.
- `spike_mode: true` is a hint for the aggregator at Step 7 (treats per-dimension result as the per-criterion result since there's only one dimension).

## What to do if observations are malformed

Same as full-mode rubric: if `/verify` output is empty or appears to be a launch failure, return Unknown for all three checks. This is the case where the agent / user invoked `/flow:ship-spike` against a project that hasn't been wired for `/run-skill-generator` and heuristic launch failed.

```json
{
  "dimension": "correctness",
  "spike_mode": true,
  "verdicts": [
    {"criterion": "Launch — ...", "verdict": "Unknown", "evidence": ["/verify output empty", "<verbatim>"], "notes": "Verify likely failed to launch the app; ESCALATE per FB-0011."},
    {"criterion": "One happy step — ...", "verdict": "Unknown", "evidence": ["/verify output empty", "<verbatim>"], "notes": "Cannot judge without launch."},
    {"criterion": "No log errors — ...", "verdict": "Unknown", "evidence": ["/verify output empty", "<verbatim>"], "notes": "Cannot judge without launch."}
  ]
}
```

## Why spike mode skips regression + scope-creep dimensions

- **Regression** requires a sense of what was working before — without a plan to anchor "this criterion's behavior" against, regression is just "any change" and produces unbounded findings.
- **Scope-creep** requires a plan's `Scope (out)` to define what's outside scope. Spike work has no `Scope (out)`.

The aggregator at Step 7 treats spike-mode's single `correctness` verdict per check as the per-criterion `aggregated_verdict` directly. The findings-buffer JSON still has the same shape (`verdicts.{correctness,regression,scope-creep}`), but the `regression` and `scope-creep` entries are emitted as `Unknown` with notes "spike mode — not applicable" rather than judged. This keeps the schema stable so the HTML renderer + Step 4a synthesis don't need spike-aware branching.
