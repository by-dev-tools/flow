# Spec

Product vision, problem, solution, feature table with status, open questions. This is the **product** document — what we're building and why. The how lives in plan + history.

Read this when starting any new feature or debating scope.

---

## Vision

<!-- One paragraph. The world we want to exist when this product is done. -->

## Problem

<!-- Who has this problem? What does the status quo look like for them? Why is it costly to leave unsolved? -->

## Solution

<!-- The shape of the thing we're building. Not a feature list — a coherent description. -->

## Principles

<!-- Standing rules that govern product decisions. 3-5 max. Example:
1. **Polished over partial.** Every visible control does its job today. Wire-vs-defer.
2. **Scope expansion is additive.** Ship the smallest polished form first.
-->

---

## Features

| Feature | Status | Notes |
|---|---|---|
| _Example: Draft autosave_ | _Shipped_ | _Local-only; sync deferred to vN_ |
| _Example: Multi-pane editor_ | _Planned_ | |
| _Example: Repo sync_ | _Open question_ | _See § Open questions_ |

Status values: `Planned` / `In progress` / `Shipped` / `Deferred` / `Open question`.

---

## Open questions

<!-- Decisions deferred until evidence accumulates. Each entry: question + what we'd need to decide + when we revisit.

- **Persistence model: localStorage vs IndexedDB vs File System Access API.** Decide when: first PR that needs > 5MB of user content. Evidence: real usage size at first 10 active users.
- **Repo sync: GitHub API vs local FS watcher vs both.** Decide when: first user request for repo-edit workflow.
-->
