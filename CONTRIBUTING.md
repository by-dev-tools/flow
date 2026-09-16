# Contributing to flow

## ⚠️ Checking out a branch in this repo RUNS that branch's code

**Before you `gh pr checkout` someone else's PR here, understand what that does.**

This repository's `.claude/settings.json` registers a `SessionStart` hook
(`.claude/hooks/flow-plugin-currency.sh`) that keeps the installed flow plugin current — see
[`dev-docs/feedback/FB-0107-*`](dev-docs/feedback/) for why it exists. That hook script is a **file
in the repository**, so it is rewritten by whatever branch is checked out, and it runs
**automatically at session start with no approval prompt**.

So: `gh pr checkout <someone-else's-PR>` followed by opening a Claude Code session executes that
contributor's version of the hook script, as you.

**Treat checking out an untrusted branch as equivalent to running it.** If you only want to *read* a
diff, read it without checking it out — `gh pr diff <N>`, or the GitHub web UI. Both avoid putting
the branch's files on disk where an automatic hook can reach them.

### What is and is not mitigated

- **Mitigated:** the hook no longer executes any *other* repository file. It resolves its provenance
  engine only from the **installed** plugin tree (via the registry's `installPath`) and refuses,
  loudly, to fall back to this checkout's copy. A currency check has no business running the branch
  under review.
- **Not mitigated:** the hook script itself. It lives in the repo and any branch can rewrite it.

### Why this is documented rather than fixed

The obvious fix is to make a change to the hook re-trigger Claude Code's approval prompt — either by
inlining the hook body into `settings.json`, or by hash-checking the script from the command string.
**Both rest on the assumption that Claude Code re-prompts when a `settings.json` hook command string
changes, and that assumption was measured to be false in the environment it was tested in:**

- A **first-ever** hook command string, in a brand-new project directory, executed with no prompt.
- The command string was then **changed**, and the new one executed with no re-approval.
- No hook-approval state is recorded anywhere (`~/.claude.json` has `allowedTools: []`,
  `hasTrustDialogAccepted: false`, and no hook key at any depth) — so there is nothing for a
  change-detector to compare against.

Shipping a hash check on top of that would be a control that *looks* like it closes the hole while
enforcing nothing. That is strictly worse than documenting the residual honestly.

**The measurement was taken in a sandboxed, non-interactive cloud workspace, which is not the
threat case.** The threat case is a maintainer on an interactive machine. If you can confirm that an
interactive Claude Code session re-prompts on a changed hook command string, the hash-check fix
becomes viable and should be built — the experiment is: edit the `command` string in
`.claude/settings.json`, start a session, observe whether you are asked to approve it.

## Everything else

See [`CLAUDE.md`](CLAUDE.md) for repository layout, the three-surface boundary, and the quality bar.
