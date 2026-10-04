---
name: orchestrate
description: >
  Boot or re-boot an orchestrator seat that drives other workspaces: read the
  project's plan and rules, re-derive live worker state from the dispatchBackend
  adapter, sweep open branches and open PRs (not just the default branch), find
  workers that have gone SILENT by last-activity rather than status, re-address
  the ping channel to this seat's session id, and load the gate policy — then
  report ready as one scannable decision, not a status dump. The standard first
  action of any orchestrator seat, and mandatory for a successor. Use on
  "/flow:orchestrate", "boot the orchestrator", "take over the seat". Also carries a
  digest-only path for "where do things stand" / "status": it re-runs the derivation,
  prints one phone-sized table, stores nothing, and deliberately skips the two
  boot-only steps.
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Bash, Write, Skill
---

# Task: boot an orchestrator seat, and leave nothing for the next one to rediscover

The orchestrator's product is **attention** — the human's. A seat that relays everything recreates the exact cost it exists to remove, so this skill's output is a decision, not a report.

**This skill wraps a checklist; the judgment stays yours.** It does not decide which worker matters, whether a plan is sound, or what to dispatch next. It makes sure the six things a fresh seat always needs are actually done, in an order where each one's failure is visible.

**Deletion criterion (FB-0088):** delete this skill when the backend exposes a single boot call that re-derives worker state, sweeps open branches and reports last-activity — at which point this is a wrapper over one command and should be deleted, not maintained.

## 0. Resolve the backend adapter (never a silent no-op)

```sh
ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
{ [ -n "$ROOT" ] && [ -d "$ROOT" ]; } || ROOT="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$ROOT" ] || ! cd "$ROOT" 2>/dev/null; then
  echo "[orchestrate] ROOT-UNRESOLVED — could not locate the repo from cwd $(pwd). Nothing below ran."
  exit 0
fi
LIB="${CLAUDE_PLUGIN_ROOT:-plugins/flow}/lib/dispatch_backend.py"
python3 "$LIB" check 2>&1 || true
```

Read the report. `slot_present: false` or any `absent`/`invalid` verb is **not** a reason to stop — the workflow still applies. It changes what you say: every step below whose verb is missing must be reported to the human as **"not performed, do this by hand"**, using the `manual_fallback` text the check prints. Never let a missing verb become a step you silently skipped.

## 1. Read the durable layer — by slot, and only the pointers

Resolve the doc slots through the **shared resolver** — never by reading `flow.config.json` yourself. It is the one thing that knows a slot may point at a directory (`[ -f ]` is false on one) and that an unresolved slot must be loud, not silent:

```sh
R="${CLAUDE_PLUGIN_ROOT}/lib/resolve-doc-slot.sh"; [ -f "$R" ] || { [ -f plugins/flow/.claude-plugin/plugin.json ] && grep -q '"name": *"flow"' plugins/flow/.claude-plugin/plugin.json 2>/dev/null && R=plugins/flow/lib/resolve-doc-slot.sh; }
for SLOT in planPath:dev-docs/plan.md roadmapPath:dev-docs/roadmap.md feedbackPath:dev-docs/feedback.md; do
  [ -f "$R" ] && sh "$R" "${SLOT%%:*}" "${SLOT#*:}" \
    || echo "⚠️ [resolve-doc-slot] not found — ${SLOT%%:*} was NOT resolved, so this seat has NO ${SLOT%%:*} context. Reinstall the flow plugin."
done
```

Then read: the project's canonical plan, `CLAUDE.md`, the feedback corpus, plan "Current Focus", roadmap "Now". **A seat that silently resolved nothing reads exactly like a project with no plan** — which is why the resolver is loud rather than defaulting.

**Read them; do not copy them into your own notes.** Durable design lives in git and is re-readable by any successor; a summary you hold in session context is a snapshot that goes stale and dies with the seat. The whole disposability invariant is that you hold nothing that isn't recoverable from git, the backend, or already delivered to the human.

## 2. Re-derive live worker state — never from a snapshot

Render and run `listWorkers`. Live state is the backend's, not a document's: a dispatch ledger with a `status` column was measured stale **within minutes** — it read "dispatched" for three workspaces the API already reported as deleted. If you catch yourself about to write a status table to disk, don't.

## 3. Ground-truth sweep — open branches and open PRs, not just the default branch

```sh
# `ls-remote` is a ref-only round trip that asks the remote directly — no `git fetch`
# first. A fetch here would download objects for every remote branch and then be read
# by nothing, and it is most expensive on exactly the repo this skill is for: a fleet
# with many live branches.
git ls-remote --heads origin | sed 's|.*refs/heads/||'
gh pr list --state open --json number,title,headRefName,isDraft --limit 60 2>/dev/null || \
  echo "[orchestrate] ⚠️ gh unavailable — open-PR state NOT swept; say so rather than assuming zero."
```

**When a merge lands, message every affected worker to rebase — immediately, without being asked.** A merge invalidates every open branch that shares a file with it, and the workers holding those branches cannot see the merge until you tell them. This is a resolve-silently call, not an escalation: it needs no decision, only prompt relay.

A sweep that reads only the default branch **does not see open branches**, and that gap has produced repeated version/feedback-number collisions: a worker re-derived its number from the default branch correctly and still collided with three numbers claimed on an open branch. Whatever contested resource this project serializes (version numbers, feedback IDs, doc slots), sweep both.

## 4. Sweep for `SILENT` workers — by last activity, never by status

> **If you are a successor, do step 5 first.** Until the ping channel is re-addressed every
> worker is silent *by construction* — they have all been pinging an address that died with
> the previous seat — so this sweep tells you nothing and will read every live worker as a
> phantom stall. The steps cannot simply swap (re-address needs step 2's worker list), which
> is why the interlock is stated rather than implied. The spec puts re-address first for
> exactly this reason.

Workers ping you when they finish or stall, so you react rather than poll. **But the failure this protocol most needs to report is the one it cannot:** a rate-limited worker has no turn in which to send anything. Its status reads `idle`, which is indistinguishable between "waiting at a gate", "done and forgot", and "died hours ago".

So for each live worker, render `workerStatus` and read the **last-activity timestamp**. Flag anything quiet for materially longer than its work should take. **This sweep finds quiet workers; it does not classify them** — `SILENT` here is the same token §8's digest renders, and §8 carries the test that separates a genuinely stalled worker from one parked at a plan gate. Do not treat silence as progress, and do not let the ping protocol's existence be mistaken for coverage.

## 5. Re-address the ping channel — the successor's true first action (see step 4's note)

> **Precondition — run this ONLY from the session that is becoming the addressee.** This step
> tells every live worker where to ping. Run from the seat that is taking over, it is correct;
> run from any other session, it points the whole fleet at **that** session and every
> subsequent ping is lost to a seat nobody is reading. So it belongs to a boot or a succession
> and to nothing else: any path that reuses steps 2–4 for *reporting* must skip it (§8 does).
> Stated here, at the step, rather than only in the caller — a precondition kept in its callers
> has to be re-remembered by each new one.

Every live worker is pinging a session id. On a succession that id is the **outgoing** seat's, it died with the seat, and the failure is invisible from both ends: pings go nowhere and you read the resulting silence as "nothing needs me."

Render `selfSession` to get your own id, then send **one message per worker** via `sendMessage` carrying it. Write each message with the Write tool to a scratch file and pass the path — never compose it as a quoted shell argument.

**One message per worker, not one batched message with per-worker sections.** A batched message got the wrong instruction read by the wrong worker, and the misroute is undetectable from both ends: the wrong recipient silently absorbs an instruction that was never theirs, and the intended worker has nothing to notice the absence of. One observed instance surfaced a fortnight late, and only because a worker volunteered it while reporting something else.

If `selfSession` is missing, **ask the human for the id** — do not skip the re-address.

## 6. Load the gate policy

Do **not** re-derive the four-axis rule in prose — `/flow:gate` implements it, and re-deriving is exactly what that engine exists to replace. Invoke it per decision: `Skill("flow:gate")`. Confirm `sensitivePaths` resolves:

```sh
# `--files-file /dev/null`, NOT `--print-defaults`: the latter returns before the
# config is ever read, so it proves the file is executable and nothing about THIS
# project's slot — a present-but-malformed `sensitivePaths`, the one case the
# predicate warns loudly about, would still print "available". And the `|| echo`
# branch is load-bearing: a bare `&& echo` prints nothing on failure, which is the
# silent-skip shape rather than a check.
# Parsed with python3 rather than jq deliberately: python3 is already a hard
# dependency of every lib this suite calls, and adding jq would oblige this skill
# to carry the repo's BLOCKING jq guard for one cosmetic line.
python3 "${CLAUDE_PLUGIN_ROOT:-plugins/flow}/lib/sensitive_paths.py" --files-file /dev/null \
  | python3 -c 'import json,sys; print("[orchestrate] sensitivePaths resolved from:", json.load(sys.stdin)["pattern_source"])' \
  || echo "⚠️ [orchestrate] the sensitivePaths predicate is NOT available — the gate's stakes axis cannot be computed this session. Reinstall the flow plugin."
```

Report `pattern_source` in the ready line. `default` on a project that *believes* it configured the slot is the interesting case, and it is invisible unless you say it.

## 7. Report ready — one decision, plus a one-line lay of the land

Apply the communication rules to **this output**, which is the first thing the human reads from you:

1. **Decide within scope; don't relay.** Anything inside the gate's green quadrant, you call. Escalate only what a red axis forces.
2. **Classify ships-or-paperwork before escalating anything.** If the choice produces an identical diff either way and the question is documentation placement or wording, it is your call — escalating it spends the human's attention on a null result. Run it — in full, because the flags are what it classifies on:

```sh
python3 "${CLAUDE_PLUGIN_ROOT:-plugins/flow}/skills/gate/lib/gate-classify.py" ships-or-paperwork \
  --changes-behavior <yes|no> --changes-consumer-surface <yes|no> --changes-gate-verdict <yes|no>
```

An unstated axis counts as `yes`, so a bare call classifies `behavioral` and you escalate something you could have decided — fail-safe, but it spends the attention this test exists to save. The test is cheap; run it every time, with the flags.
3. **One decision at a time.** Surface the single most pressing item, plus **one line** naming the other live threads and their state. Never a flat dump of unrelated asks; never silence about parallel threads either.
4. **Progressive disclosure.** Lead with what is needed. Default to scannable-in-seconds; let the human pull detail by asking.
5. **Every escalation carries recommendation + confidence + justification** and a return address, so the answer can be relayed back from this seat. The human should never have to ask for the confidence or the why, and should never have to open a worker workspace to unblock it.

Then state explicitly, in one line each: how many workers are live, how many are **silent** (step 4), anything the sweep in step 3 contradicts, and any backend verb that was missing so a step went unperformed.

**Large text blocks read worse than you assume.** A verbose orchestrator is the failure mode, not the thorough one.

## 8. `status` — the digest-only path, when the human wants state and not a boot

**Reached by what the human asked for, not by an argument.** "Where do things stand", "status",
"what's live" — a request for current state — is this path. A boot or a succession is steps 0–7.
If you cannot tell which was meant, do the full boot: it is a superset.

**Run steps 2, 3 and 4, then stop.** Those three already derive everything a digest needs —
live worker state from the backend (2), open branches and open PRs (3), last-activity quiet
times (4). This path adds **no second derivation**; if you find yourself computing state some
other way, you are on the wrong path.

**Skip steps 5 and 6, and skip them deliberately:**

- **Step 5 (re-address the ping channel) must not run mid-program.** It sends every live worker
  a new ping address. Run from a seat that is *already* the addressee, it is a no-op's worth of
  value for the cost of N messages; run from any other session, it points live workers at **that
  session** instead of the orchestrator, and every subsequent ping is lost to a seat nobody is
  reading. A status request is not a change of address, so it must never behave like one.
- **Step 6 (load the gate policy) is boot setup, not reporting.** This path classifies nothing
  and approves nothing, so it has no use for the four-axis rule. If reading the digest produces
  a decision, invoke `Skill("flow:gate")` for *that* decision — which is step 6's actual
  contract anyway.

Steps 0 and 1 still apply: resolve the backend (0) or you have nothing to derive from, and a
digest that silently resolved no plan slot reads exactly like a project with nothing in flight.

### The digest — derived on demand, never stored

**Write nothing.** No file under the project's doc slots, no scratch ledger, no status table on
disk anywhere. A status table with a `status` column was measured stale **within minutes** — it
read "dispatched" for three workspaces the API already reported deleted — which is the same
reason step 2 says "never from a snapshot". The digest's correctness comes entirely from being
recomputed; persist it and you have built the thing step 2 forbids.

Render it to the human like this:

```markdown
**Needs you:** <the single most pressing item, one line>

**Fleet** — 3 live · 1 silent · 2 open PRs · <UTC timestamp>

| Worker | State | PR | Quiet |
|---|---|---|---|
| <short-name-a> | GATE | [#181](https://github.com/<owner>/<repo>/pull/181) | 40m |
| <short-name-b> | WORKING† | [#182](https://github.com/<owner>/<repo>/pull/182) | 12m |
| <short-name-c> | SILENT† | — | 3h |

† derived by me, not reported by the worker.
```

When nothing needs the human, the first line is this instead — not omitted:

```markdown
**Needs you:** nothing — no worker is at a gate or blocked.
```

**`Needs you` comes FIRST, above the inventory.** Step 7 rule 4 is "lead with what is needed",
and it applies to this surface more than any other: the table is the tallest, widest element
here, so anything below it is what a narrow screen pushes off. The digest answers "where do
things stand"; the single line above it answers "do I have to do something". If the answer is
no, say so in those words — an omitted line is indistinguishable from a forgotten one.

**Four columns, and `Branch` is deliberately not one of them.** Measured on this project: 136
remote heads, mean branch-name length 34 characters, max 69. A row carrying one renders at
~100 characters, which on a phone either scrolls sideways or wraps into exactly the mush this
digest exists to replace. Four columns render at ~45. The branch is also the least necessary
thing here — the short-name already identifies the worker, and the PR link reaches the branch
in one tap. **If you add a column, re-check the width**; a template that fits only because its
placeholders are short is a template that breaks on first real data.

**No backticks in the cells.** A table cell is already delimited, and this is read in chat and
notification clients where a code span renders as literal backtick characters.

**The ~45-character figure assumes a client that RENDERS markdown.** In a raw-text client the
PR link's markup is visible and a row runs 88–99 characters — near the ~100 the `Branch` column
was dropped to avoid. That is the deliberate trade: the hyperlink is stated-as-not-optional
(see below) and a tappable PR number is worth more on a phone than a shorter raw row. Stated
rather than left for someone to rediscover as a contradiction.

### Two vocabularies, deliberately different sizes — do not unify them

**There are exactly two sets here, and they are not the same set.** Naming both explicitly,
because the obvious-looking "cleanup" is to collapse them and that would delete the digest's
whole reason for existing.

- **THE MESSAGE SET — exactly four, closed, never a fifth.** `GATE` · `DONE` · `BLOCKED` · `FYI`.
  This is what a *worker* may put in the `[w:…]` opener. It is a closed vocabulary and the eval
  enforces the closure at every contract site.
- **THE DIGEST SET — the four above, plus two derived values.** `WORKING` and `SILENT`. This is
  what the *seat* may render in the `State` column.

| State | Set | Where it comes from |
|---|---|---|
| `GATE` `DONE` `BLOCKED` `FYI` | message + digest | **Reported** — the worker's own last ping said so |
| `WORKING` | digest only | **Derived** — live, recent activity, nothing outstanding. The modal row |
| `SILENT` | digest only | **Derived** — quiet longer than its work should take, and not at a gate |

**Why they differ, which is the part a future editor needs.** The two sets answer different
questions. A message answers *"what is this worker telling me?"* — so it can only contain things
a worker is able to say, and a worker that has stopped speaking cannot send a status reporting
that it has stopped speaking. The digest answers *"where does everything stand?"* — which must
cover workers that said nothing at all, so it needs words no worker can send. **A set that is
closed over what a sender can utter and a set that is closed over what an observer can conclude
are different sets by construction.** They are not a duplication to be deduplicated.

**And the asymmetry is not cosmetic: `SILENT` is the single most valuable cell in the table.**
A worker killed by the rate limit has no turn in which to ping, so it reports nothing and its
backend status reads `idle` — indistinguishable from healthy. That is the failure this program
has paid for most, and a digest with no word for it would be blind to the exact thing it was
built to surface. Likewise, dropping `WORKING` would force "working normally" into `FYI`, which
then means both *"fine"* and *"possibly dead"* — collapsing the one distinction the human is
scanning for.

**So: adding a derived value to the MESSAGE contract is wrong, and removing a derived value from
the DIGEST is wrong.** If you find yourself making the two sets equal in either direction, the
change is a regression and this paragraph is the reason. (User direction, 2026-10-04.)

**Mark every derived cell with `†` and footnote it once per digest**, exactly as the template
above does, so the human can see which states a worker claimed and which you inferred. **Every
derived cell, including the modal `WORKING` row** — a marker applied only to the alarming value
tells the reader nothing, because then an unmarked cell means both "the worker said so" and "it
is fine".

`†` rather than `*`: a lone `*` is the one glyph markdown owns, and a naive client's
`\*([^*]+)\*` pairs the marker in one row with the next row's and italicises everything
between — in exactly the non-rendering clients the no-backticks rule above is written for.

**`SILENT` and `GATE` must be told apart mechanically, never by feel.** This is the distinction
that cost three wasted chases in one program (field manual § 8), and it is decidable from step
3's ground truth. Run both halves of the test — carrying only the positive half is how a dead
worker reads as a parked one:

- **`GATE`** — branch exists, **no open PR**, HEAD subject begins `plan:`. A worker told to stop
  at the plan gate and doing exactly that. Go read the plan; do not chase it for status.
- **`SILENT`** — **no branch on the remote at all**, or a branch with no new commits and a stale
  last-activity timestamp. This is the one to worry about.
- Neither shape matching is itself a result: say "could not classify" rather than defaulting to
  `GATE`, because `GATE` is the reassuring answer and defaulting to it is how the asymmetry bites.

**`<slug>` and `<branch>` are REPOSITORY-DERIVED, so treat them as untrusted — this block is
the one place in this section where a value you did not author reaches a command line.** Step 3's
sweep hands you branch names from `git ls-remote` and `gh pr list --json headRefName`; on any repo
that takes outside contributions, a fork's head-branch name is attacker-chosen. **`git
check-ref-format` permits `;`, `$(…)`, backticks, `|` and `&` in a ref name** (verified, not
assumed — it rejects only space, newline, `*`, `?`, `\`, `:`, `~`, `^`, `[`), and `${IFS}`
substitutes for the one character it forbids. So an unquoted paste here executes the name.

Apply `/flow:spawn` § 4's rule, **widened by one character**: reduce every interpolated value
to `[A-Za-z0-9._/-]` before it reaches the command line, then single-quote it. Spawn's class is
`[A-Za-z0-9._-]`; the slash is added here because a branch name legitimately contains one, and
it is harmless inside quotes. **The reduction is the real defence, not the quoting** — git also
permits an apostrophe in a ref name, so quotes alone would not hold. Quote anyway: the two
together fail safe if one is forgotten.

```sh
# <slug>/<branch>: reduce to [A-Za-z0-9._/-] FIRST, then paste inside the quotes.
# `grep -F --` also closes the incidental regex- and option-injection on <slug>.
git ls-remote --heads origin | grep -F -- '<slug>'   # branch on the remote at all?
gh pr list --head '<branch>' --json number           # PR open?
git log -1 --format=%s -- 'origin/<branch>'          # subject starts with "plan:"?
```

If a name does not survive that reduction, **say you could not classify the worker** rather than
running the command on the raw value — the same refuse-rather-than-escape policy
`lib/dispatch_backend.py` applies to every rendered verb.

**The `Quiet` column is a raw duration, not a verdict** — it is there so the human can disagree
with your classification, which is why `SILENT` is marked derived. Step 4 sets the threshold
("materially longer than its work should take"); it is per-worker judgment and the digest does
not pretend otherwise.

**Edge states — say them, don't improvise them.** Each run otherwise invents its own:

- **Zero live workers.** Print the `Needs you` and `Fleet` lines with an explicit `0 live` and
  one sentence distinguishing **"nothing is in flight"** from **"I could not derive the fleet"**
  (a missing `listWorkers` verb, an unresolved backend). Never a bare header row: an empty table
  and a failed derivation look identical, and §0 already makes this distinction for step 0.
- **Nothing needs you.** The `Needs you` line still renders, with the words above.
- **An absent value in any cell** — no PR, no branch, unknown duration — is `—`. One convention,
  so a reader never has to wonder whether `n/a`, blank and `—` mean different things.
- **A ping with no opener.** Nothing enforces the `[w:…]` convention, so this is the failure the
  contract's own stated limit predicts — and it lands here, in the one surface where the human
  would notice. Its status is **not** reported: derive the state from step 3's ground truth and
  mark it `†` like any other derived cell. **Never read a status out of the prose** of an
  unlabelled ping, and never render it as though it had carried one — an unlabelled ping and a
  labelled one must not look identical, or the digest quietly launders the gap.

**Hyperlink every PR number** — `[#181](https://github.com/<owner>/<repo>/pull/181)`, inline and
**inside the table**. Stated as not optional, and the lapse recurs specifically inside status
tables, which is exactly what this is.

**The digest reports; it does not escalate.** If reading it produces a decision, that decision
follows step 7's rules in its own message — one at a time, with recommendation, confidence and
justification. The one-line `Needs you` *names* the item; it is not the escalation.

**Deletion criterion:** delete this section when the backend (or Conductor's own per-workspace
rows) reports live worker state, branch, open PR and quiet time in one view the human can read
on a phone. The digest exists because that view does not demonstrably exist today — the vendor
claim that mobile rows match desktop detail is recorded as **unconfirmed**, from search results
rather than a fetched page. If it turns out to hold, this path costs one skill section and
should be deleted against this criterion rather than maintained beside a better surface.
