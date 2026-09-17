---
name: handoff
description: >
  Rotate an orchestrator seat: flush pending durable currency through the normal
  ship path, INVENTORY AND EXTERNALIZE every sandbox-local artifact that matters,
  generate a brief that points rather than duplicates, mechanically verify it
  names nothing the successor cannot reach, deliver it as the successor's first
  message, and run the archive-safety check on the outgoing seat. Rotation is
  meant to be cheap — offer it before it is urgent. Use on "/flow:handoff",
  "rotate the seat", "hand off to a new orchestrator". Never merges.
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Bash, Write, Skill
---

# Task: make the seat disposable, then dispose of it

The model fails if the orchestrator seat becomes a **hostage** — a full-context session the human won't leave for fear of losing accumulated state. The fix is not a better handoff document. It is the invariant that makes the document optional: **the seat holds no state that isn't recoverable from git, the backend, or already delivered to the human.**

If that holds, rotating loses nothing and the reluctance dissolves at the root. The brief is an *accelerant, not a lifeline* — a fresh seat with no brief at all reconstructs its whole world from git plus a live backend query. The brief only saves it from re-deriving the small in-flight delta.

**So the UX matters as much as the steps: offer a wind-down proactively on a long session** ("this is getting long — want the succession brief so you can rotate freely?"). Detecting context-fill from inside a session is imperfect, so lean on cheap frequent rotation rather than a hard threshold. The seat is a role, not a vessel.

**Deletion criterion (FB-0088):** delete when the seat stops being disposable-by-rotation — e.g. context ceases to be the binding constraint, so succession is no longer routine — or if `/flow:ship` absorbs the durable-currency flush such that steps 1–2 become unconditional.

## 1. Flush durable currency — through the normal ship path

Anything decided but not yet written down (a resolved decision, a roadmap item that is now closed, a feedback entry earned this session) goes to git **now**. Between a merge and the next ship, that currency lives only in this session; if the session ends first, it is lost. The next feature ship is the normal path and a session-end flush is the backstop — this is the backstop.

Compose with the project's ship pipeline rather than reimplementing it: `Skill("flow:ship")`. **Currency reaches the default branch through a reviewed PR, never a direct push** — speeding the handoff does not license skipping the merge gate.

If there is nothing pending, say so explicitly. "Nothing to flush" is a real answer; silence is not.

## 2. Externalize sandbox-local artifacts — the step that has actually failed

A file this seat created that is **not in git** is recoverable from neither the forge nor the backend (the backend exposes transcripts and workspace metadata, **not** sandbox filesystems) and **dies when the sandbox is torn down**.

```sh
git status --porcelain
git stash list
ls -la .context/ .flow/ 2>/dev/null
```

**Name `.flow/usage.tsv` explicitly if `/flow:spawn` ran in this seat.** It is the dispatch routing record — `model · effort · why · outcome` per dispatch — and it is the one artifact whose whole value is accumulating across dispatches. It lives in session scratch, so without this step every rotation silently resets the audit trail the routing policy is supposed to be tuned against.

Inventory every such file and externalize each one:

- **repo content** → commit it (it rides the step-1 PR);
- **not repo content** (a vendor report, a generated deliverable, anything that would cross a project's own file-layout boundaries) → **hand its contents to the human**, in the chat, now.

This sharpens the invariant to: recoverable from git, the backend, **or already-delivered-to-the-human** — and a sandbox-local file is recoverable from none of the three. The first real succession in this program pointed its successor at a sandbox-local report path it could not reach; the report survived only because it had already been shown to the human. That near-miss is why this step exists and why it is second, not last.

## 3. Write the brief — it points, it does not duplicate

Write with the **Write tool** to `.flow/succession-brief.md`. Three sections, and it stays tiny precisely because the first two layers flush continuously:

```markdown
# Succession brief — <seat>

## Read first
<the project's canonical plan (⭐), CLAUDE.md, the feedback corpus, plan "Current Focus",
 roadmap "Now"> — links/paths in the repo, never a summary of them.

## Live workers
Re-derive: run the backend's listWorkers verb. Do NOT trust any list written here.

## In flight
<the handful of threads and pending decisions not yet resolved — the only genuinely new content>

## Your first action
Re-address the ping channel. Every live worker is pinging MY session id, which dies with this
seat. Get your own id (the backend's selfSession verb) and broadcast it — ONE message per
worker, composed into a file. Nothing in your environment will reveal that the channel is
stale; the symptom is silence, and silence reads as "nothing needs me".
```

It is **generated at hand-off, not maintained**, and delivered through the backend rather than committed: a handoff is *live*, not durable currency, and committing it would add per-rotation PR churn plus a snapshot that is stale the instant it lands. A stale committed snapshot would be **worse** than re-deriving live.

## 4. Verify the brief mechanically — do not eyeball it

```sh
python3 "${CLAUDE_PLUGIN_ROOT:-plugins/flow}/skills/handoff/lib/brief-check.py" \
  --brief-file .flow/succession-brief.md
```

Exit 1 ⇒ **do not hand it over.** It checks three things, and the two positive ones are there because a prohibition alone is satisfiable by writing nothing:

- **no reference the successor cannot reach** — no path in this sandbox;
- **at least one durable pointer** — a URL, git remote state, a live backend query, or content already delivered to the human;
- **the re-address instruction is present** — the one handoff step that cannot be left to inference.

Fix and re-run until it passes. This is the rule that was written down and then broken by the person who wrote it, which is the signature of something that belongs in code.

## 5. Deliver it — as the successor's first message

```sh
python3 "${CLAUDE_PLUGIN_ROOT:-plugins/flow}/lib/dispatch_backend.py" \
  render createWorker --set name=<successor-name> --set messageFile=.flow/succession-brief.md
```

Run the rendered command. If `createWorker` is missing, print the brief in full and tell the human to paste it — never let the handoff quietly not happen.

Tell the successor to run `/flow:orchestrate` as its first action; that skill performs the re-address the brief describes.

## 6. Archive-safety on the outgoing seat

```sh
python3 "${CLAUDE_PLUGIN_ROOT:-plugins/flow}/skills/post-merge/lib/merge-status.py" archive-check
```

A workspace is safe to archive when **all four** hold:

1. its PR is **merged**;
2. all **committed** work is in the default branch;
3. nothing **uncommitted or unaccounted** remains in the sandbox — the check above answers this, and it is the one thing only the sandbox can answer;
4. any pending forward-doc reconciliation is **tracked to fold into the next ship** *and* you hold correct live state — **not** "the default branch is fully reconciled right now."

Point 4 is the one that changes under an orchestrator: doc-currency stops being an archive *blocker* and becomes a tracked *follow-up*, because the next workspace is spawned with a brief rather than cold-reading the default branch. Stale forward docs cannot mislead an agent that is not reading them.

## 7. Report — one line, then stop

State: what was flushed (or that nothing was pending), what was externalized and where each thing went, that the brief passed the check, the successor's name, and the archive verdict for this seat. Then end the turn. Do not keep working in a seat you have just handed over — two live seats messaging the same workers is the batched-message failure with extra steps.
