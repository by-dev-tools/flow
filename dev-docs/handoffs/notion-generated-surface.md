# Handoff — generated, read-only Notion surface (PLAN GATE, NOT APPROVED)

> **Status: 🟠 DRAFT — awaiting the human plan gate. NOT approved, NOT started.**
> Nothing in this plan has been executed. No `tools/notion-publish/`, no
> `.claude/skills/publish-state/`, no `ci.yml` change, no plugin artifact exists.
> This document is committed **only** so the plan-gate work survives an ephemeral
> workspace — per `dev-docs/README.md` § Handoffs, check this banner before
> treating it as active.
>
> **Seven open calls in §10 need a human decision before any execution.**
> The recommendation in §2 is: **ship nothing to the plugin** — 100% repo-local
> dev tooling, zero `plugins/flow/**` changes, no version bump.

---


**Branch:** `conductor/notion-read-only-generated-surface`
**Mode:** feature (dev-tooling, NOT shipped)
**Version:** v1.37.0 → **unchanged** (zero `plugins/flow/**` changes ⇒ no bump, no CHANGELOG entry)

**Mechanics re-verified at rebase onto `24332a6` (2026-09-06), not carried from the first draft:** `origin/main` advanced by one PR while this workspace was rate-limited (#143, "§2.4 resolved — RunLocalCommand exists"). Re-read directly at that ref: **version is still `1.37.0`** (unchanged by #143), **FB high-water is still `FB-0099`**, so **FB-0100 remains correct**. #144 (`spike: AGENTS.md vs skills`) is the only open PR and touches nothing this plan touches. FB-0099's reservation line is *still* present and *still* stale ("Held until MERGE", #142 merged) — the sweep in §0 is still owed.
**FB number:** **FB-0100.** High-water re-read at rebase: FB-0099 is merged on `main` via #142/`478fe17`, so FB-0100 is the next free number.

> **Corrected at the plan gate.** An earlier draft of this line claimed § Currently reserved was **empty**. It is not — it holds **nine** live lines (FB-0099, FB-0096, FB-0089, FB-0095, FB-0013, FB-0014, FB-0058, FB-0062, FB-0067). My `sed -n '/## Currently reserved/,/^## /p'` range terminated on the *Protocol* section's own mention of that heading, so it printed the protocol text and stopped before the list. Re-read by anchoring on the **last** occurrence of the heading. FB-0100 is unaffected (it is above every reserved number), but the "nobody is racing" premise was false, and **FB-0099's line is now stale** — it reads "Held until MERGE" and #142 has merged. Sweeping it into a cleared note is part of this PR's first commit, per this file's own convention.

**FB-0100's headline:** *"A generated human-facing surface is one-way and read-only: nothing in the repo may read it, depend on it, or be broken by its deletion."* That is the standing constraint from the design session — real user direction, synthesizable, and the property every mechanical choice in this plan (§4.5, §2, the exit story) defends. The reservation line will carry it verbatim, per § Protocol step 2's required shape. **If you'd rather this PR carry no FB number**, say so and I will drop the reservation, the `feedback.md` edit, and the two criteria that pin them — the plan gate flagged that reserving a number silently pre-decides whether a correction is being recorded, and it is your call, not mine.

Reserved *before* drafting the `feedback.md` entry and pushed as its own first commit, per `dev-docs/reserved-feedback-numbers.md` § Protocol ("push your reservation immediately — the early push is the race-detection mechanism") and CLAUDE.md's "Reserve an FB number **before** drafting its entry". *(An earlier draft cited this as the "FB-0098 protocol"; FB-0098 is about fixing a check rather than the data that exposed it and says nothing about reservation — exactly the wrong-concept cross-reference `reserved-feedback-numbers.md` § Why this exists warns will propagate into commit messages, history and PR bodies.)*
**Status:** DRAFT — at the plan gate. Not executed.

---

## 0. Restated request

Build a **generated, one-way, read-only** Notion surface mirroring flow's project state. Notion is never a source of truth: no skill, gate, or config slot reads it; nothing in git depends on it; deleting the whole workspace leaves the repo unaffected. Two page types (DASHBOARD — overwritten each regeneration; CASE STUDY — accumulating, milestone cadence), plus `visual-history.html` embedded as a live interactive HTML block. Every page SHA-stamped + generation-timestamped. Regenerated at `/flow:land`. No prototype workspace. Comment *capability* granted, comment *automation* deferred.

The design decision is approved and is **not** re-litigated below. What this plan decides is the *implementation*: where the code lives relative to CLAUDE.md's three-surface boundary, how the token is supplied, how regeneration is triggered, and how every failure mode fails loudly.

---

## 1. Verified facts (re-verified this session — the brief said to re-check anything I depend on)

Fetched from `developers.notion.com` / `notion.com/help` on 2026-09-06. Marked ✅ confirmed, ⚠️ **changed since the design session**, ❓ residual.

| # | Fact | Status |
|---|---|---|
| F1 | `api.notion.com` reachable from this sandbox (`GET /v1/users` → `401`, i.e. up and unauthenticated) | ✅ measured |
| F2 | Solo (1-owner) free workspace: **unlimited blocks**. Multi-member free: 1,000 blocks, 3-day grace, then upgrade required | ✅ confirmed verbatim on the block-usage help page |
| F3 | Rate limit: **~3 req/s average per connection**, bursts allowed; plus a per-workspace limit scaled to plan. Over-limit → HTTP **429**, `rate_limited`, `additional_data.rate_limit_reason`; honor `Retry-After`, exponential backoff + jitter, capped retries | ✅ confirmed |
| F4 | **Per-request** payload caps: **1000 block elements**, **500 KB**, block arrays **100 elements**; rich_text content **2000 chars** | ✅ confirmed — **new constraint, see §4.3** |
| F5 | File Upload API accepts `text/html` / `application/html`. Free workspace: **5 MiB per file**; single-part for ≤20 MB | ✅ confirmed |
| F6 | HTML block is real: upload `.html`, attach via `embed.file_upload` on create/update → "the Notion app renders the file's contents interactively in a **sandboxed iframe** instead of linking out" | ✅ confirmed verbatim on the block reference |
| F7 | `embed.url` is a **temporary signed URL**; an embed "always reads back with a `url`, never a `file_upload`". Notion-hosted file URLs are valid **1 hour** (`expiry_time`); docs explicitly say *"Don't cache or statically reference these URLs"* | ✅ confirmed — **exact TTL now known: 1 h** |
| F8 | Comments: `GET /v1/comments` returns only **un-resolved (open)** comments. `block_id` is the query param **for both pages and blocks** (pages are blocks) | ✅ confirmed — validates the "don't resolve early" rule |
| F9 | Auth: current platform issues **Personal Access Tokens** from the Developer portal (moved into the Notion sidebar 2026-08-19; platform 3.5 shipped 2026-05-13) | ⚠️ **changed — see §5** |
| F10 | PAT capabilities are exactly two: **"Notion API"** = *"Read, create, update, and search content; **read and create comments**"*, and **"Workers"**. There is no separate read-comments toggle | ⚠️ **changed — see §5.2** |
| F11 | A PAT **inherits its creator's own workspace/page permissions** — *"no additional sharing with a bot connection is required"*, unlike internal connections which need explicit per-page sharing | ⚠️ **changed — removes a setup step** |
| F12 | PATs **expire**: 7 / 30 / 90 / 180 days or 1 year; **default 1 year**; after expiry requests return `unauthorized` | ⚠️ **new operational fact — see §6.3** |
| F13 | `.gitignore:10` is a bare `tools/` — it **does** ignore newly-created paths under `tools/`. `tools/model-measure/` + `tools/harness_audit/` are tracked only because they were force-added | ✅ **measured in-repo — see §4.6** |
| F14 | Largest tracked HTML is `annotation-layer.html` at 60 KB; `dev-docs/visual-history.html` is **10 KB**; all of `dev-docs/` is 2.6 MB | ✅ measured |
| F15 | `dev-docs/plan.md` = **735 KB**, `history.md` = **673 KB**, `roadmap.md` = **371 KB**, `spec.md` = 8.7 KB. `roadmap.md` `## Now` alone is **139 KB across 40 paragraphs** | ✅ measured — **new constraint, see §4.3** |
| F16 | A web-search snippet claimed "workspace block limits for the Free workspace take effect on September 8, 2026" (two days away). The authoritative help page contains **no such date** and states solo-free = unlimited | ❓ **unresolved discrepancy — see §7 R1** |

**Facts from the brief NOT re-verified** (not depended on by this plan): Notion AI tiering, which two MCP query tools are tier-gated, `makenotion/notion-mcp-server#175`. This plan uses **raw REST only and no databases/data sources**, so all three are out of its dependency set. The MCP bug still governs the *manual* comment path and is documented as such (§8).

---

## 2. Three-surface recommendation (the question asked)

### Recommendation: **ship nothing. 100 % repo-local dev tooling. Zero `plugins/flow/**` changes, zero schema change, zero version bump.**

**Confidence: HIGH.**

**Justification — four independent reasons, any one of which is sufficient:**

1. **Nothing here is generic.** The extraction contract is "flow's own `dev-docs/` section headings"; the dashboard schema is Ben's taste; the workspace, token, parent page and case-study cadence are his. CLAUDE.md's project-agnostic bar ("plugin artifacts must contain no project-specific tokens") would be violated by every interesting line.

2. **The one shippable candidate — a generic `landPublishCommand` config slot — should be declined on security grounds.** It would let a repo-controlled file (`flow.config.json`) execute an arbitrary shell command from inside a shipped skill, in **every** repo that installs flow. A single-line PR to that file becomes code execution at land time. That is a new, broad attack surface introduced for exactly one known beneficiary. This is a *stronger* objection than the aesthetic one, and it is why I am not proposing the slot even in a hardened form.

3. **Slot-count fan-out is this repo's most expensive recurring bug class.** 33 → 34 slots touches the schema, `docs/workflow.md`, `template/base/CLAUDE.md.template`, `bootstrap.sh`'s key count, `/flow:doctor`'s frontmatter, and the wrap-tolerant `no-stale-slot-count-in-shipped-surfaces` eval. `dev-docs/history.md` records this sweep going wrong **three separate times** (value-vs-class grep, YAML line-wrap invisibility, `bootstrap.sh` stale at 28). Paying that cost for one consumer is FB-0094's exact cut criterion, and FB-0088's "a hook slot encodes a *procedure*, not a fact."

4. **`/flow:land` is being modified concurrently.** A sibling dispatch is fragmenting `CHANGELOG.md`, which may leave `/flow:land` SKILL.md:295's `[ -f "$CHANGELOG" ]` guard pointing at a directory. Zero plugin change ⇒ **zero merge collision with that dispatch, and zero dependency on which way it resolves.** See §3.

**What would flip this:** a second project (not flow, not Ben's) wanting the same generated-surface hook. Then the slot is worth designing *properly* — with an allowlisted command path, not a free-form string. Recorded as the deletion/promotion criterion in §9.

### Surface map

| Path | Surface | Shipped? |
|---|---|---|
| `tools/notion-publish/**` | project-dev infra (CLAUDE.md § 3) | ❌ no |
| `.claude/skills/publish-state/SKILL.md` | project-dev infra (`.claude/skills/`, alongside `/ship` + `/preship`) | ❌ no |
| `dev-docs/**` (plan, history, feedback, README, workflow) | plugin's own dev-tracking (CLAUDE.md § 2) | ❌ no |
| `.github/workflows/ci.yml` | project-dev infra — eval wiring only, **no token, no live API call** | ❌ no |
| `plugins/flow/**`, `.claude-plugin/`, `README.md`, `template/` | plugin artifacts | **untouched** |

Precedent is exact: CLAUDE.md already describes `tools/model-measure/` and `tools/harness_audit/` as *"dev tooling, no shipped `/flow:*` skill invokes it."* `tools/notion-publish/` is the third entry in that table.

---

## 3. Coordination with the concurrent `/flow:land` dispatch

**Attachment point: none inside `/flow:land`.** This plan does not add, move, reorder, or reword a single line of `plugins/flow/skills/land/SKILL.md`. My `git diff origin/main --stat` will contain zero `plugins/flow/` paths.

**What I assume about `/flow:land`, and how little it is:** only that it continues to exist and to be human-invoked. I depend on **no step number**, no §4 CHANGELOG block, no `$CHANGELOG` variable, no ordering. The sibling dispatch can renumber §4–§8, turn `changelogPath` into a directory, or replace the `-f` guard with `-e` — none of it reaches this branch.

**Explicitly, my attachment point is NOT near the CHANGELOG block.** It is outside the skill entirely: the human types `/publish-state` after `/flow:land`'s reconciliation PR merges (§4.1).

**Why not compose `Skill("flow:land")` from `/publish-state`:** `/flow:land` § 0 enumerates *exactly two* legitimate entry points (a human typed `/flow:land`; `/flow:post-merge` § 3 called it) and says "anything else … is not a valid entry." A repo-local wrapper would be a silent third. Adding one requires amending a shipped contract — which is both a plugin change and a collision with the sibling. Declined.

---

## 4. Design

### 4.1 Invocation — **OPEN CALL 1** (see §10)

`/publish-state` — repo-local skill in `.claude/skills/`, human-invoked, thin wrapper over `python3 tools/notion-publish/publish.py`. Convention: run it immediately after `/flow:land`'s `docs: land #N` PR merges.

**All publishable content is read at the ref — `git show origin/main:<path>` — never from the working tree. There is no checkout, no branch switch, and no clean-tree requirement.**

This replaces an earlier design that checked out `main`, fast-forwarded, and restored the starting branch. The plan gate caught that the working tree was never needed: §4.2 item 5 and the milestone trigger *already* read straight out of git objects at a ref, and sections 2/3/4/6 can do the same (`git show origin/main:dev-docs/plan.md`, `:dev-docs/roadmap.md`, `:dev-docs/spec.md`, `:dev-docs/README.md`, `:dev-docs/visual-history.html` → temp file → upload). Four things follow:

- **The whole checkout apparatus disappears** — branch switch, `--ff-only`, restore-on-every-exit-path, the hoisted dirty-tree check, the HEAD-match and clean-tree precondition rows, and roughly ten eval cases. A publishing tool should not move someone's checkout, and now it cannot.
- **It fixes a bootstrap bug.** `git switch main` on any run *before this PR merges* removes `tools/notion-publish/publish.py` from the tree — the skill's own `python3 tools/notion-publish/publish.py` invocation would have failed on first use, every time, until the tool was on `main`.
- **Publish and `--check` become symmetric.** Both need only that the fetch succeeded.
- **It is strictly more correct.** "Never publish a branch's state" is now structural rather than enforced by a precondition: the publisher has no way to read a branch's state.

The one remaining git precondition, in both modes, is §4.1's `git fetch origin main` succeeding — see below. The precondition's error message names this recovery explicitly, so the fatal is **self-resolving rather than merely loud**. This is also the honest correction to Open call 1's "one typed command" — it is one command, but the command does real git work, and that work is stated here rather than left to the operator.

**`origin/main` is refreshed before it is trusted — in both modes.** `git rev-parse origin/main` reads a *local remote-tracking ref*; nothing refreshes it on its own. A workspace whose ref lags would publish month-old state under a stamp asserting it is `main`, and `--check` would report exit 0 "fresh" — the silently-green staleness mode the stamp and the read-back exist to prevent. **The design's answer is to repair the ref, not to detect and refuse:** every mode begins with `git fetch origin main`, and every subsequent read resolves against the *post-fetch* tip. A failed fetch is **fatal** per §4.4 (never a `|| true`; an unfetchable remote means the answer is unknown, not "fresh").

*(An earlier draft argued this from a `HEAD == origin/main` precondition — which the table below deletes, since content is read at the ref. The hazard was real; the rationale described the superseded checkout design.)* `origin/main` is the authority for three separate things — the precondition, `Recently shipped` (§4.2 item 5) and the case-study range — so one stale ref would corrupt all three.

**Preconditions — now identical in both modes**, since neither reads the working tree:

| Precondition | publish (default) | `--check` |
|---|---|---|
| `NOTION_TOKEN` + `NOTION_PARENT_PAGE_ID` in env | fatal if absent | fatal if absent |
| `git fetch origin main` succeeded | fatal if not | fatal if not |
| HEAD / branch / tree state | **irrelevant** — content is read at `origin/main` | **irrelevant** |

Both modes run from any branch, dirty or clean, including this one.

`--check` mode: fetch the live dashboard's stamp, compare it to `origin/main` (not to HEAD), print `[notion-publish] STALE: Notion at <sha7> (<n> commits behind main <sha7>)`. **Runnable from any branch or dirty tree** — it reads, it never writes.

**Distinct exit codes**, so a caller can tell "the dashboard is stale" from "the probe is broken":

- `0` — fresh (Notion stamp == `origin/main`)
- `2` — **stale** (probe worked; the answer is "behind")
- `3` — **never published** — no `Dashboard` child exists under the parent yet. (This is also why a vanished Notion cannot break anything: `--check` reports it as an answer, and no skill consumes that answer.) `--check` **does not create it** (it reads, it never writes), so this cannot collapse into either "fresh" or "error": it is the expected state between your setup (§5) and the first publish, and it needs its own answer.
- `1` — **error** (token, network, 403, 429-exhausted, malformed stamp — the §4.4 loud-failure path)

### 4.2 Page model

**DASHBOARD** (one page, overwritten every run). Sections, in order:
1. **Stamp** (first block once the archive completes; see §4.4 for why read-back targets it by id, not by position): `Generated <ISO-8601 UTC> from <full 40-char SHA> (<sha7>) · main` — full SHA so it is machine-comparable, short SHA so it is human-scannable.
2. **Now / Current Focus** — `dev-docs/plan.md` § `## Current Focus` (6.6 KB, fits comfortably).
3. **Roadmap** — `dev-docs/roadmap.md` § `## Now`, bounded. **Bound re-derived at the plan gate against the file's real shape**, because my first rule ("top-level narrative + `### ` headings with their first paragraph") measured out to near-nothing: `## Now` is line 9 and `### ▶ ACTIVE PROGRAM` is line 11, so there *is* no top-level narrative, and every current-state paragraph sits after that heading's first paragraph. The rule would have rendered four headings and four opening lines — one of them the bare table-header row `| Item | Depends on | Reason |` — eliding exactly the "what shipped / what's next" content the section exists to convey, and §11 would have called it green because extraction raised no error.

   The bound is instead anchored on the file's actual status markers, all measured:
   - the `**Plugin at v<origin/main's version>` paragraph (line 15 today), **truncated at its first `Recently shipped:`**. **Absent ⇒ benign announced skip, NOT fatal** — the section renders without it and prints `no status paragraph for v<X> in § Now`. Measured: only **4** such paragraphs exist (v1.37.0, v1.35.0, v1.36.0, v1.32.0) across ~15 shipped versions, and one of the four names a version `roadmap.md:19` says was *never shipped*. Writing that paragraph is a convention nothing enforces, so making the strictest failure rule depend on it would exit 1 with nothing published on the first version bump whose author skips it — and the only check that would surface it is a [LOCAL] one deliberately kept off every automatic path — that phrase is reliably the boundary between current status and accumulated history, which its 31 occurrences confirm;
   - the `**▶ Next up:` pointer paragraph (line 41). Anchored on a line *starting* `**▶ Next up:` — the bare phrase also appears at line 72 as a back-reference (`the ▶ Next up pointer in § Now`), which the bold-lead-plus-colon form excludes. Exactly one match required; ≥2 fatal;
   - every `### ` heading under `## Now` (4 today), for orientation.

   **Which anchors are fatal, and why they differ.** The `▶ Next up:` anchor and the § Now heading set are structural — a project that has § Now has them — so absence there is fatal (§7 R3). The version paragraph is not: it is a hand-written convention with measured 4-of-15 coverage, so it degrades to an announced skip. The rule is *ambiguity is fatal; measured-unreliable absence is announced*, which is the same distinction §4.2 item 4 draws for `spec.md`.

   **The criteria that assert against the *live* `dev-docs/` run locally only and are NOT wired into CI.** Caught at the plan gate: not editing `roadmap.md` is not the same as not depending on it. A CI job asserting against the live § Now would turn every future reword of that section — the sibling dispatch's territory, and every version-bump PR — into a red build attributed to an unrelated author. That is a hard dependency on exactly the file §2 reason 4 claims zero dependency on, and §7 R3's fatal-on-miss does not help: it protects the operator running the tool, not a third party whose doc edit reddens CI. **CI runs the fixture-backed cases only**, so §2 reason 4's "zero dependency on which way the sibling resolves" stays true as stated. The version-interpolated anchor is a further reason to keep it out of CI: it resolves to exactly one match today only because § Now happens to carry a paragraph for `origin/main`'s exact version, which is a convention nothing enforces.

   Everything else is elided behind the §4.3 truncation callout. **Not** the full 139 KB.
4. **Spec** — `dev-docs/spec.md` in full (8.7 KB), **preceded by a rendered status callout**. Verified during the plan gate: `spec.md` itself carries **no** staleness banner — the ⚠️ **Known stale** marker lives one level up, in `dev-docs/README.md` § Living docs. So the generator extracts `dev-docs/README.md`'s status cell for `spec.md` and renders it above the section. It does **not** add a banner to `spec.md` (`dev-docs/README.md` § Rules forbids that), and it does not render the spec bare — which would launder a stale source into a clean-looking page. Two absence cases, deliberately distinguished (the plan gate caught that collapsing them punishes a cleanup the repo has already queued):
   - **`dev-docs/spec.md` does not exist** ⇒ **benign skip** with a printed reason. `dev-docs/README.md` § Rules explicitly invites retiring it ("Fix or retire it; don't add to it"), so a documented, already-queued cleanup must not turn the publisher into a permanent exit-1. Same shape as the zero-entry case-study range.
   - **`spec.md` exists but `dev-docs/README.md` carries no status cell for it** ⇒ **fatal** (§7 R3). That is genuine ambiguity — the section would otherwise render a possibly-stale spec with no staleness signal, which is the laundering §4.2 forbids.
5. **Recently shipped** — **derived from git, not extracted from `roadmap.md`.** Source: `git log origin/main --oneline -n 5`, whose subjects carry the merged PR number (`478fe17 docs: existing-repo design-language migration brief (FB-0099) (#142)`).

   **Corrected at the plan gate — my first two drafts were wrong on the facts.** I asserted the `Recently shipped:` phrase occurred "twice" in `roadmap.md`. Re-measured without a truncating `| head`: it occurs **31 times across 10 lines** (15, 17, 19, 21, 25, 27, 29, 31, 37, 39). So the "≥2 ⇒ fatal" rule I had just written would have made **every publish against the current repo exit 1** before section 5 rendered. Three reasons the git anchor is right rather than merely a patch:
   - **Structural, not prose.** A merge subject's `(#N)` is machine-generated; a bold phrase inside an accumulating narrative paragraph is not, and all 31 occurrences sit inside `## Now` (lines 9–75) — so sections 3 and 5 would also have rendered the same shipped-version prose twice.
   - **Zero coupling to anything in motion.** `CHANGELOG.md` would be the other natural source, but a sibling dispatch is fragmenting it into one-file-per-entry (§3). `git log` is unaffected by that dispatch and by any doc rename.
   - **`roadmap.md` needs no edit**, so this PR does not touch a file the roadmap-heavy sibling work may also be moving.
6. **Visual history** — an `embed` block backed by an upload of `dev-docs/visual-history.html` (10 KB, F14; ceiling is 5 MiB, F5).

**Page identity — how each page is located across runs.** `NOTION_PARENT_PAGE_ID` names the parent only; the two child pages are resolved by **title lookup among the parent's own children**: `GET /v1/blocks/{parent}/children`, paginated, selecting `child_page` blocks titled exactly `Dashboard` and `Case study`. Not found ⇒ **create once under the parent, then reuse forever**.

**Creation timing differs by page, and this is load-bearing** (caught at the plan gate): the dashboard is created **eagerly** on any publish; the **case study is created lazily — only at its first actual milestone append**. Creating it eagerly would leave a page holding a creation stamp and no append stamp, which on the next run reads as "has content but is unstamped" ⇒ the fatal branch below, permanently blocking the first append. Lazy creation makes "just created" and "first append" the same event by construction, so the fatal branch means only what it says: *someone published without stamping.* No page id is ever persisted to disk — which matters, because a fresh Conductor workspace has no local state at all, and an id-in-a-file design would create a *second* dashboard on every new workspace while `--check` fetched the stale first one. **The tool persists no state** — it writes exactly one ephemeral artifact, the `visual-history.html` payload extracted from the ref, into a `tempfile.TemporaryDirectory()` that is removed on every exit path (the §4.4 `stat` size pre-flight runs against that path). Deliberately **not** `/tmp` by hand and **not** the repo-local `.flow/`: FB-0082 moved flow's *inter-process* scratch to `.flow/` because a forked skill cannot see a parent's `/tmp` file, but nothing here is shared across processes, so a self-cleaning temp dir is both correct and leaves no artifact behind. That is also why it ships no `.gitignore` of its own: an earlier draft listed one, but the root `tools/` rule already excludes the whole subtree (git does not descend into an excluded directory to consult a nested ignore file), everything is staged with `git add -f`, and there is no ephemeral artifact for it to exclude.

Title lookup over `POST /v1/search` was rejected: search is an eventually-consistent index, so a just-created page can be missing from it, and a lookup miss here means "create a duplicate."

**Ambiguity is fatal, as everywhere else:** ≥2 children with the same title ⇒ error naming both page ids. Never "take the first."

**Overwrite is scoped to the dashboard page's own children, and is APPEND-THEN-ARCHIVE — never archive-then-append.** Order: record the existing children → append the new block set in ≤100-block batches (F4) → **read-back assert the new stamp** → only then archive the old children. Archive-first was the earlier draft and is unsafe: any §4.4 failure landing in the window between the archive loop and the stamp append (429-exhausted, network drop, 403) would leave the dashboard **empty and unstamped** — the very state the plan treats as fatal-on-read elsewhere — and the read-back would never fire, because it only runs on a path that reached the write. With append-first, an interrupted run leaves a page that still has its previous content plus a partial new set: degraded and visibly so, but never destroyed. It is *never* resolved against the parent, which would archive the accumulating case study. Idempotent: two consecutive runs at the same SHA produce the same page.

**CASE STUDY** (one page, append-only, never overwritten).

**Milestone trigger** = the minor version changed since the **last case-study append** (`1.37.x` → `1.38.0`). `--milestone` forces an append; `--no-milestone` suppresses.

**The trigger's anchor is the case study's own append stamp — never the dashboard's.** Corrected at the plan gate: I resolved this ambiguity for the *range* anchor and left it open for the *trigger*, which is the same defect one paragraph apart. Neither stamp format records a version, and no local state persists, so "the last published stamp" had no readable prior value at all. If the trigger had resolved against the dashboard stamp, **any** publish after a minor bump — including a `--no-milestone` run — would advance it to the bumped SHA, the next run would compare 1.38.0 to 1.38.0, and the append would never fire. The milestone would be permanently lost on the one page that cannot be re-run to fix.

Mechanically: `to_sha` = the newest case-study append stamp's end-SHA; prior version = `json.loads(git show <to_sha>:plugins/flow/.claude-plugin/plugin.json)["version"]`. Compare its `major.minor` to **`origin/main`'s** — `git show origin/main:plugins/flow/.claude-plugin/plugin.json` — never to HEAD's.

**No `jq`.** An earlier draft piped through `jq -r .version`, which violates CLAUDE.md's stdlib-only bar, contradicts §4.7's own declared dependency set, and — worse — would have misdiagnosed itself: on a host without `jq` the trigger falls into the "prior version unparseable ⇒ fatal" branch naming the *wrong cause*. That is exactly the silent-degradation shape `dev-docs/research/jq-absence-handling-2026-06.md` documents across 16 skills with **no fix shipped**. All six existing `tools/**/*.py` use `import json`; so does this one.
- No case-study page yet ⇒ **first run is a milestone by definition** (creates the page, appends the full history).
- Prior version missing or unparseable at `<to_sha>` ⇒ **fatal**, same rule as the range anchor. Never guess.

Trigger and range now read the *same* anchor, so they cannot disagree about what has already been published.

**Content selection — by git diff, not by parsing headings.** Corrected at the plan gate: my earlier "render the `history.md` entries belonging to that minor version" was exactly the unanchored-prose ambiguity this plan declares fatal, and measurement confirms it is unworkable — `dev-docs/history.md` has **37** `## ` headings, of which only **4** carry a version string (the rest are date-plus-title, e.g. `## 2026-09-03 — Existing-repo design-language migration brief (FB-0099)`). Worse, this is the one page type that **accumulates and cannot be re-run to fix**, so a wrong selection is permanent.

Instead: the appended section is the set of `## ` entries **added to `dev-docs/history.md` across a commit range** — `git diff <from>..origin/main -- dev-docs/history.md`, taking complete added `## ` blocks. This needs no heading convention at all and cannot drift when the convention changes.

**The range anchor is a per-append stamp — not either page's first-block stamp.** Corrected at the plan gate; the obvious reading is wrong in both directions:
- The **dashboard's** stamp is rewritten every land, so using it would cover only the delta since the last *non-milestone* publish and **silently drop** every entry added between lands.
- The **case study's** first-block stamp is written once at creation and never overwritten, so using it would **re-append** everything already published.

Both are silent corruption of the one page that accumulates and cannot be re-run to fix. So each appended section begins with its own stamp block: `Appended <ISO-8601 UTC> · range <from_sha7>..<to_sha7>` (full SHAs retained in the same block for machine comparison). `<from>` for the next append is read back from the **most recent append-stamp block among the case-study page's children**. The two pages' watermarks are then fully independent, and consecutive appends are disjoint and gap-free by construction.

- **First-ever append** (page was just created by this run, zero append stamps) ⇒ range is the full history. Correct and benign.
- **No append stamp but the page already has content** ⇒ **fatal**. Something published without stamping; the plan will not guess what is already there.
- Append stamp present but unparseable ⇒ **fatal**. Never guess a range.
- Range yields zero added entries ⇒ **not** fatal: skip with a printed reason (`nothing added to history.md in <range>`). A milestone with no new history is a real, benign state.

The generator **writes no narrative of its own** — it renders what a human already wrote.

### 4.3 Size + limits handling (from F4/F15 — new since the design session)

`dev-docs/` is far larger than the design session assumed: `plan.md` is 735 KB and `roadmap.md` § `## Now` alone is 139 KB in 40 paragraphs. Three consequences:

- **The dashboard is a *report*, not a mirror.** This matches the approved decision ("the 'catch me up' report, rendered") — recording it because the measured sizes make it load-bearing rather than stylistic.
- **Chunk, don't truncate.** A paragraph over 2000 chars is split across multiple `rich_text` objects **within one block** — lossless, no ellipsis, no silent drop. Block arrays are appended ≤100 per request, so total page size is unbounded; only *per-request* size is capped.
- **Truncation is unavoidable in exactly two places, and both must announce themselves.** §4.2 item 3 elides twice, not once — a section-footer count cannot express a mid-paragraph cut, so an implementation that silently drops the paragraph tail would otherwise pass:
1. **Items dropped from § Now** → the rendered section ends with `Truncated: N further items in dev-docs/roadmap.md § Now`. **N counts the elided `**`-lead status paragraphs plus the `###` items whose bodies were not rendered** — the unit is stated here because "N correct" is not otherwise evaluable.
2. **The tail of the rendered status paragraph**, cut at its first `Recently shipped:` (measured: line 15 is 727 chars, cut at 574, so **153 characters elided**) → an inline elision marker on that paragraph itself, naming where the rest lives.

A bound whose elision is invisible is the FB-0010 silent-skip defect; a bound that announces itself is a report.

### 4.4 Loud-failure contract (the mid-turn instruction)

Every failure exits **`1`** and prints `[notion-publish] ERROR: <cause>` to stderr. (**Two non-zero exits are not errors**, both from `--check`: `2` = stale and `3` = never published — successful probes reporting answers the caller needs to distinguish from a broken probe. Every other non-zero exit is `1` and carries an `ERROR:` line. The contract reads identically in §4.1, §4.4 and §11.) No `2>/dev/null`, no `|| true`, no `// empty`, no bare `except:`. Enumerated paths, each with a distinct message and its own test:

| Failure | Detection | Message names |
|---|---|---|
| `NOTION_TOKEN` unset/empty | pre-flight | how to supply it (§5.3) |
| HTTP 401 `unauthorized` | response code | "token invalid or **expired** — PATs expire (max 1 yr); reissue in the Developer portal" (F12) |
| HTTP 403 `restricted_resource` | response code | block-limit / permission, with the F2 solo-vs-multi-member distinction |
| HTTP 429 `rate_limited` | response code | retried per `Retry-After` + jittered backoff, **capped**; exhausted retries = ERROR, never a shrug (F3) |
| Network unreachable / DNS / TLS | exception | the endpoint attempted |
| Payload over per-request cap | pre-flight measurement | the offending section + its measured size (F4) |
| HTML upload > 5 MiB | pre-flight `stat` | measured size vs the 5 MiB ceiling (F5) |
| Embed attach failed | response | the file-upload id |
| **Read-back mismatch** | see below | intended SHA vs SHA actually on the page, naming which page |
| `git fetch origin main` failed | pre-flight, **both modes** | the remote + that `origin/main` may be stale — never degrades to "use the local ref" |
| `--check` finds no `Dashboard` page | title lookup | "never published — run `/publish-state`". **Exit 3, not 1** — a correct answer, not a broken probe. `--check` never creates a page |
| Publish interrupted mid-overwrite | any failure between append start and archive | names that the page holds both old and partial-new blocks, and that a re-run is safe and idempotent. Old children are **not** archived on this path |

**Read-back is the anti-Potemkin check**, mirroring the established `plugins/flow/skills/ship/lib/verify-pr-body.sh` pattern (re-fetch after every write, assert it took). After writing, the script re-fetches and asserts the live stamp equals the SHA it intended to publish — **against a different target per page, which the plan gate caught was unstated and wrong under either default reading**:

- **Dashboard** → the **newly appended stamp block, by the id returned from the append** — *not* the page's first block. Under append-then-archive the new stamp lands *after* the still-present old children and the read-back runs *before* the archive, so at read-back time the page's first block is still the **previous** run's stamp: a first-block read-back would mismatch and exit 1 on every publish after the first. Same by-id rule the case study uses. "The stamp is the page's first block" is true only *after* the archive completes, and is asserted there.
- **Case study** → the **newest append-stamp block**, *never* the page's first block. The first block is a creation stamp that is stale **by design** on every append after the first (a v1.38.0 creation stamp against a v1.39.0 append), so reading it back would exit 1 *after* the append was already written — leaving a partially-published, permanently-red state on the one page that cannot be re-run to fix. Scoping read-back to the dashboard alone was the other wrong answer: §4.2's "no append stamp but the page already has content ⇒ fatal" branch depends on appends being reliably stamped, so the append needs its own verification. This is the mechanism that makes "the page silently stopped updating while everything reported green" a *hard failure*. It also naturally re-reads `embed.url` fresh, satisfying F7's never-cache rule.

**Per `.claude/rules/general.md` § Consistency discipline rule 3** (a prohibition satisfiable by deletion is not a check), the eval pairs each negative with a positive:
- negative: no silent-fallback idiom appears in the source; **positive:** each enumerated failure path, *executed* against a stubbed transport, produces a non-zero exit **and** an `ERROR:` line.
- negative: no `plugins/flow/` path in the diff; **positive:** `tools/notion-publish/publish.py` exists and `.claude/skills/publish-state/SKILL.md` names it.

### 4.5 Read-only enforcement (the whole safety story)

Mechanically asserted by `run_notion_publish_evals.py`, not by discipline:
- No file under `plugins/flow/`, `.claude/rules/`, or `flow.config.json` references the **Notion API surface** — the token set `api.notion.com`, `NOTION_TOKEN`, `NOTION_PARENT_PAGE_ID`, `notion-publish`, `publish-state` — **paired** with the positive that `tools/notion-publish/publish.py` does. **Not a bare case-insensitive `notion` match:** "notion" is an ordinary English word, so that form would redden any future PR whose shipped prose writes "the notion that" — the same substring over-match this plan anchors against one section later for `README.md`, and it would misfire on an unrelated author rather than on us. (Verified: zero hits for either form under those paths today, so only the narrow version stays correct later.)
- The publisher performs **no Notion→repo write path**: it never opens a repo file for writing, and the only endpoints it calls are page/block create/update/archive + file upload. Asserted by executing it against a stubbed transport and diffing the tree.
- The `GET /v1/comments` endpoint is **not called anywhere** (automation deferred). Paired positive: the manual procedure is documented in `dev-docs/workflow.md` (§8).

**Exit story — the complete removal procedure**, since "if it vanished, the repo is unaffected" is the load-bearing property and a removal that reddens CI does not satisfy it:
1. `rm -rf tools/notion-publish .claude/skills/publish-state`
2. delete the `notion-publish` job from `.github/workflows/ci.yml` — otherwise CI invokes a harness that no longer exists
3. revert the **three** `CLAUDE.md` sites (§ 3 tools row, line 74, line 133) — otherwise three references point at a deleted command and path
4. revert the dated review line from `dev-docs/plan.md` § Handoff Notes (§9's actual trigger) and the Notion comment-rules section from `dev-docs/workflow.md` (and any `dev-docs/README.md` pointer added with it) — otherwise a living doc still teaches comment etiquette for a surface that no longer exists
5. delete the Notion pages; revoke the PAT

Nothing outside those five steps changes: no `plugins/flow/**` file, no schema, no config slot. *(Two earlier drafts got this list wrong — first omitting steps 2–4 entirely, then omitting step 4. Both were caught at the plan gate, which is why §11's criterion derives the step count from this section rather than asserting a literal number: a hardcoded "four" went green over the omission.)*

### 4.6 The `tools/` gitignore trap (F13 — verified, would have silently eaten this PR)

`.gitignore:10` is a bare `tools/`, which ignores **new** paths there. The existing `tools/*` files are tracked only because someone force-added them; `git check-ignore` reports them clean *because tracked files bypass ignore rules*, which is exactly how this hides. A fresh `tools/notion-publish/` would be invisible to `git status` and ship as an empty directory — FB-0089's documented pattern and FB-0010's silent-skip class.

**Fix:** `git add -f` at commit time (matching how the existing two got there), **plus** a positive mechanical guard — the eval asserts `git ls-files tools/notion-publish/` returns the exact expected file list. A dropped file fails CI instead of shipping. I am *not* restructuring `.gitignore` into `tools/*` + negations: that changes ignore semantics for two unrelated tracked toolchains, which is out of scope.

### 4.7 Files

| Path | New? | Purpose |
|---|---|---|
| `tools/notion-publish/publish.py` | new | the generator (stdlib only: `urllib`, `json`, `hashlib`, `subprocess`) |
| `tools/notion-publish/extract.py` | new | `dev-docs/` section extraction → block list; pure, no network |
| `tools/notion-publish/README.md` | new | setup, the three comment rules, the deletion criterion |
| `tools/notion-publish/run_notion_publish_evals.py` | new | offline evals, stubbed transport, **zero live API calls**. Three modes (§11): **no flag** = fixture-backed [CI] cases; **`--live-docs`** = the [LOCAL] cases asserting against live `dev-docs/`; **`--pr-shape`** = the one-shot [PRE-SHIP] diff-shape cases, merge-base-anchored. CI invokes it with **no flag** — that is the mechanism keeping §2 reason 4 true |
| `.claude/skills/publish-state/SKILL.md` | new | repo-local invocation |
| `CLAUDE.md` | edit | **three** sites, `git grep`-derived not guessed (FB-0010 fan-out; `dev-docs/feedback.md:579` — "centralizing doesn't close the fan-out unless every call site is wired in the same PR"): (1) § 3 tools table gains a `tools/notion-publish/` row; (2) **line 74**, the `.claude/skills/` row's list "(`/ship`, `/preship`)"; (3) **line 133**, the prose "Dev-side slash commands: `/ship` …, `/preship` …" sentence. Sites 2 and 3 are the *same* command list in two places — `git grep -n '/preship'` returns exactly these two, and the plan gate caught site 3 after an earlier draft committed to only two edits |
| `.github/workflows/ci.yml` | edit | a **new job** for `run_notion_publish_evals.py`, sibling to the existing `model-measure` and `harness-audit` jobs (there is no single "dev-tooling job" — an earlier draft named a target that does not exist). Fixture-backed cases only; **no token, no live API call**. Note: `ci.yml`'s mechanical harness↔runner join check is scoped to `ls plugins/flow/evals/run_*.py`, so `tools/**` harnesses sit structurally outside it — as `model-measure` and `harness-audit` already do — which is precisely the "a run with 19 of 20 harnesses is byte-identical to one with all 20" class its own FB-0074 comment records |
| `dev-docs/{plan,history,feedback,README,workflow}.md` | edit | tracking |
| `dev-docs/reserved-feedback-numbers.md` | edit | reserve FB-0100 **and** sweep FB-0099's stale "Held until MERGE" line into a cleared note (§0) |
| `dev-docs/roadmap.md` | edit | **§ Exploration entry only** — the secret-hook hardening routed out of scope by §6.2 / §10 Open call 4. Precedent: both dev-tooling PRs #136 and #138 edit this file. **No `## Now` edit**, so no collision with the roadmap-heavy sibling work |

**Stdlib only** (CLAUDE.md quality bar) — `urllib.request`, no `requests`, no `notion-client`.

---

## 5. What Ben must do — I cannot create the integration

**I cannot do any of this, and I will not stub it or claim it works.** The plan is executable up to the point of a live call; the first real publish requires these three steps.

### 5.1 Create the token
Notion → **Settings → Developer portal** (in the sidebar since 2026-08-19) → **New token** → name it (e.g. `flow-publish`) → select the workspace → select the **"Notion API"** capability → choose expiration (**recommend 1 year**, the max) → **Create token** → copy it once (it cannot be viewed again).

### 5.2 On the "read comments" setup constraint — satisfied, by a simpler mechanism than the brief anticipated

The brief says to grant "read comments" at connection time because the capability is fixed then. **On the current platform that toggle no longer exists as a separate item, and there is nothing to miss.** PATs expose exactly two capabilities (F10), and the "Notion API" one is defined as *"Read, create, update, and search content; **read and create comments**."* Selecting it grants comment reading. The fixed-at-connection-time hazard is real but applies to **OAuth connections**, not PATs.

Two knock-on simplifications: a PAT **inherits Ben's own page permissions**, so there is **no per-page "share with the integration" step** (F11) — a whole class of "the integration can't see the page" failures is removed. And the manual comment path stays a single `GET /v1/comments?block_id=<page_id>` call, as the brief intended.

**If Ben would rather create an OAuth connection** (e.g. to also use the hosted MCP later), the original constraint applies in full: check read-comments at connection time, and expect to share pages explicitly. Flagged, not decided — see §10 Open call 3.

### 5.3 Create the parent page + supply the env vars
Create one page in the workspace (e.g. `flow`) and copy its 32-char id from the URL. Then supply, **as environment variables only**:

```
NOTION_TOKEN=ntn_...
NOTION_PARENT_PAGE_ID=<32 hex chars>
```

Never a committed file, never a CLI argument (argv is visible in `ps`), never a repo path.

---

## 6. Secrets

### 6.1 How the token is supplied
Env var, read via `os.environ`, absent ⇒ loud fatal (§4.4). Never written to disk by the tool. Never logged: the eval asserts no code path interpolates `NOTION_TOKEN` into a printed/raised string, **paired** with the positive that the `Authorization` header is set from it.

### 6.2 Does the repo's secret-blocking hook cover this? — **Partially. I will not claim more.**

`.claude/settings.json`'s `PreToolUse` hook matches `Edit|Write` and blocks `file_path` containing `.env`, `credentials`, or `secret`. Assessed honestly:

- ✅ Covers: Claude using Edit/Write to create `.env` / `*credentials*` / `*secret*` in this repo.
- ❌ **Does not cover** a file written via **Bash** (heredoc, `tee`, `>`), which is this session's default working mode.
- ❌ **Does not cover** a token pasted into a normally-named tracked file (`publish.py`, a `.md`).
- ❌ **Does not cover** `git commit` / `git push` at all — there is no pre-commit secret scan in this repo.
- ❌ A `ntn_`-prefixed PAT does not match any of the three substrings by name.

**Controls this PR adds — labelled by what they actually do, not by what I'd like them to do:**
1. `run_notion_publish_evals.py` scans **all tracked files** for Notion-token-shaped literals (`ntn_[A-Za-z0-9]{20,}`, legacy `secret_[A-Za-z0-9]{40,}`) and fails on a hit — with a `scanned > 0` assertion so an empty sweep cannot pass vacuously (the exact vacuous-pass class `dev-docs/history.md` records being fixed twice).

   **This is post-push DETECTION, not prevention — an earlier draft called it a "compensating control" for the commit/push gap, which it cannot be.** CI runs only after the commit has reached GitHub, so by the time it goes red the PAT is already in remote history. **Required response to a hit: rotate the token immediately** (revoke in the Developer portal, issue a new one) — history rewriting is not sufficient and not the first move. The genuine prevention is a pre-commit/pre-push scan, which is the same `.claude/settings.json` hardening routed to § Exploration by Open call 4; this PR does not add it, and the honest statement of coverage is that the commit/push gap remains open.
2. `tools/notion-publish/README.md` states env-var-only supply as a rule, not a suggestion.
3. The tool writes **no** local state, so there is no on-disk artifact that could accumulate a token in the first place.

Hardening `.claude/settings.json`'s hook itself (adding a Bash matcher, or a `ntn_` content scan) is a **real, separable improvement** to project-dev infra that would benefit every future session. It is **out of this PR's scope** — I am routing it to `dev-docs/roadmap.md` § Exploration rather than silently absorbing it (FB-0095: don't narrow, and don't widen without surfacing).

### 6.3 Token expiry (F12 — new)
PATs expire, 1 year max. A 401 is a **loud** failure naming expiry as the likely cause and pointing at the Developer portal. Recorded in the README with the issue date so renewal is a known date, not a surprise outage. This is precisely the "silently stops updating while everything reports green" mode the mid-turn note warns about, so it is a first-class enumerated failure rather than a footnote.

---

## 7. Risks

**R1 — the September 8 2026 free-workspace block-limit discrepancy (F16).** A search snippet asserted a limit taking effect two days from now; the authoritative help page states solo-free = unlimited and carries no such date. I could not resolve it and am **not** asserting either way. Impact is bounded: if a limit does land, the API returns `403 restricted_resource`, which §4.4 already treats as a loud fatal naming the block limit. The surface fails visibly rather than silently degrading — which is the property that matters. **No mitigation work is proposed**; the honest handling already exists.

**R2 — expiring signed URLs (F7).** `embed.url` lives 1 hour. Handled by never persisting it: the read-back re-fetches. Nothing in the repo ever stores a Notion URL.

**R3 — extraction coupling to `dev-docs/` anchors.** If `## Current Focus` is renamed, extraction breaks. Handled loudly: a missing anchor **in the fatal set** (`## Current Focus`; the § Now heading set + `**▶ Next up:`; `README.md`'s spec status cell when `spec.md` exists) is a **fatal** error naming the anchor and the file — never an empty section. **Two measured exceptions degrade to an announced skip instead**, both justified where they are defined: `**Plugin at v<version>` (§4.2 item 3 — 4-of-15 coverage, unenforced convention) and an absent `spec.md` (§4.2 item 4 — retirement is invited by `dev-docs/README.md` § Rules). One rule, stated identically here, in §4.2 and in §11. (`/flow:land` § 2's own `[land] WARN` on a no-match is the in-repo precedent for refusing a silent no-op.)

**Two of the six sections do not have a heading anchor at all**, so a heading-shaped defense would not cover them — surfaced at the plan gate and handled explicitly rather than assumed away:
- **"Recently shipped"** — the `Recently shipped:` phrase occurs **31 times across 10 lines** in `roadmap.md` (measured; I twice asserted "twice" from truncated greps). No disambiguation rule over that prose is defensible, so section 5 **does not read `roadmap.md`** — it derives from `git log origin/main` (§4.2 item 5).
- **The spec staleness callout** lives in a `dev-docs/README.md` **table cell**, not in `spec.md` at all (§4.2 item 4). Rule: missing cell is fatal.

The general principle: *ambiguity is as fatal as absence.* "Take the first match" is the silent-skip defect wearing a different hat — it renders something plausible instead of failing. And the meta-lesson from this plan gate, which is FB-0010's own "grep the shape, not the value" corollary: **a `grep | head` is not a measurement.** Both wrong facts in this plan came from a truncated pipe, and both survived one full critique round before being caught. Every anchor count in §11 is now derived by a `wc -l`-style full count, never a previewed one.

**R4 — `roadmap.md` § Now is 139 KB.** Bounded rendering with a visible truncation callout (§4.3). Never a silent elision.

---

## 8. Comments — capability granted, automation deferred

**No pull-back pipeline is built.** No code calls `GET /v1/comments`; §4.5 asserts that mechanically. Three operating rules documented in `tools/notion-publish/README.md` + `dev-docs/workflow.md`:

1. **Do not resolve a Notion comment until an agent has picked it up.** The API returns only un-resolved comments (F8 ✅ re-verified) — resolving early makes it permanently invisible.
2. **Prefer page-level comments over inline block comments** for anything meant to be read back. The official Notion MCP server has an open `page_id`/`block_id` bug (`makenotion/notion-mcp-server#175`) preventing inline-comment retrieval; raw REST is the reliable path, and page-level comments are retrieved with `block_id=<page_id>` (F8).
3. **The API can reply to an existing thread but cannot start an inline discussion.** Ben starts a thread; an agent replies.

---

## 9. Deletion criterion (FB-0088 corollary (b))

**Delete `tools/notion-publish/` + `.claude/skills/publish-state/` when either holds:**

- **(a)** **Precondition: §5 setup completed and at least one publish succeeded** (a `Dashboard` page exists). Then, at the second `/flow:land` after that first publish, Ben confirms he has not opened the dashboard. **The precondition is load-bearing** — without it, "has not opened the dashboard" is trivially true when no dashboard exists, which relocates the ambiguity from the command to the bootstrap rather than removing it, and mandates deleting correct code because setup (which is outside this plan's control, §5) had not happened yet. If setup has not happened by then, that is its own conversation, not a deletion trigger. **The criterion is about value, not habit** — the plan gate caught that an earlier version measured whether `/publish-state` had *fired*, which is unusable here: this design deliberately removes every mechanism that would fire it automatically and then forbids the reminder that would compensate, so "not run twice" is indistinguishable from "the human forgot an unenforced manual step." That retires the surface on evidence about diligence rather than usefulness. Asking is one question and answers the actual question. **The correct response to a "no" is removal, not adding a reminder to keep it alive** — FB-0077's precedent is a check that outlived its feature because nobody had written down when to retire it.
- **(b)** The dashboard's content becomes available in a surface Ben already reads (e.g. the repo renders its own status page), making the Notion copy a second place to keep current.

**The criterion needs a trigger that is actually read.** Its only home in an earlier draft was `tools/notion-publish/README.md`, which nothing in the loop opens — the same "nobody wrote down when to retire it" shape §9 cites FB-0077 for, and doubly so since the trigger names an event inside `/flow:land`, a skill §3 deliberately leaves untouched. So it also goes in **`dev-docs/plan.md` § Handoff Notes as a dated review line** naming the two-land checkpoint, which is a doc the loop does read.

**Removal is the full procedure in §4.5**, not just `rm -rf` — it includes deleting the `ci.yml` job and reverting the three `CLAUDE.md` sites. Stated here because a deletion criterion that leaves CI red does not deliver the property it exists to protect.

**Promotion criterion (the inverse):** if a second, non-Ben project wants the same generated-surface hook, revisit the `landPublishCommand` slot from §2 — designed properly, with an allowlisted command path rather than a free-form string.

---

## 10. Open calls — recommendation + confidence + justification (FB-0090)

**Open call 1 — invocation coupling to `/flow:land`.**
**Recommendation:** human types `/publish-state` right after `/flow:land`'s PR merges; coupling is conventional + documented, with `--check` as the loud staleness probe and the SHA stamp as the visible honesty mechanism.
**Confidence: MEDIUM.** The approved decision says "regenerated at `/flow:land`," and this is one manual step short of that letter.
**Justification:** a mechanical hook needs either the shipped-skill change §2 argues against on security + fan-out + collision grounds, or a third entry point into `/flow:land` § 0's two-item contract (§3). Both are worse than one typed command. The approved decision's own reasoning supports this: it names the SHA stamp as *the* staleness mitigation, i.e. staleness is designed to be **visible**, not impossible. **If you want true auto-fire**, the honest option is amending `/flow:land` § 0 to admit a human-invoked wrapper. I will do that instead if you say so — but it is not free, and the costs belong in the decision rather than in the execution: it makes this a **shipped** change, so **v1.37.0 → v1.38.0**, a CHANGELOG entry, and the two Spec-walk criteria asserting a zero-`plugins/flow/` diff get rewritten. It also collides directly with the in-flight `/flow:land` dispatch (§3) and should wait for that to land. Net: the mode of this PR flips from dev-tooling to plugin surface, which is the same cost §2 uses to argue against the config slot.

**Open call 2 — case-study *cadence* (this asks only when to append, not what).**
**Recommendation:** append when the **minor version changes** (`1.37.x` → `1.38.0`), with `--milestone` / `--no-milestone` overrides.
**Confidence: MEDIUM-HIGH.**
**Justification:** "milestone, not per-PR" needs a definition, and minor-version is the only cadence signal already maintained in-repo. The alternative (you tag milestones by hand) is more faithful to "progression narrative" but adds an authoring step, and an unmaintained tag list degrades to per-PR or to nothing.
**Open call 6 — does rendering the per-PR log verbatim actually satisfy "the progression narrative"?**
**Recommendation:** yes for v1 — append the `history.md` entries added across the range, verbatim.
**Confidence: LOW-MEDIUM.** This is the weakest recommendation in the plan and I'd rather you decide it than inherit it.
**Justification:** the approved decision calls the case study "the progression narrative," and `dev-docs/history.md` is by its own index entry the **per-PR decision log** ("what, why, tradeoffs"). So a milestone append is a concatenation of per-PR entries — *milestone cadence over per-PR content*, which is not obviously the same thing as a narrative of progression. I recommend it anyway because the alternative is the generator writing narrative of its own, and a generated surface that paraphrases the human's record is exactly the kind of thing that drifts from the repo without anyone noticing — the failure mode this whole design exists to avoid. **Two alternatives if you disagree:** (a) the case study renders only the `## ` *headings* across the range plus the version delta, i.e. a spine rather than a transcript; or (b) it renders a human-authored `dev-docs/case-study.md` that you write at milestones, with the generator doing nothing but transport. (b) is the most faithful to "narrative" and the most honest about authorship; it costs you a writing step per milestone.
*(An earlier draft asserted this was "no longer an open question," which quietly resolved a substitution the decision did not authorize — surfacing it rather than absorbing it, per FB-0095.)*

**Note on what is *not* open:** selecting entries by parsing version strings out of headings is retracted on measurement — only **4 of 37** history headings carry one. Whatever content rule you pick, the *range* is the git-diff range in §4.2.

**Open call 3 — PAT vs OAuth connection.**
**Recommendation:** PAT.
**Confidence: HIGH.** Simpler (no OAuth round-trip), inherits Ben's own permissions so no per-page sharing (F11), includes comment reading in its single capability (F10), and matches a solo workspace.
**Justification:** the only reason to prefer OAuth is the hosted MCP server, which this plan deliberately does not use (raw REST, no databases — sidestepping the tier-gated query tools entirely). **If Ben wants the MCP path too, say so** — then §5.2's original fixed-at-connection-time constraint applies in full and read-comments must be checked at connection time.

**Open call 5 — `--check` reads Notion, which the approved decision's own words appear to forbid. This is a constraint question, not just a scope question.**
**Recommendation:** keep `--check`, but **only as a CLI diagnostic a human runs (`python3 tools/notion-publish/publish.py --check`) — NOT exposed through `/publish-state`, and nothing branches on it programmatically.**
**Confidence: MEDIUM.**
**The constraint it brushes against:** the decision says *"No skill, gate, or config slot ever reads it."* An earlier draft shipped `--check` inside `.claude/skills/publish-state/` and justified it as "queryable by an agent" — which is precisely a skill reading Notion and branching on the result. The plan gate caught that I had surfaced `--check` as a *scope* addition and never tested it against the *read-direction* constraint. Keeping it CLI-only satisfies the letter: no skill reads Notion, the repo still cannot depend on it (a vanished Notion just reports "never published"), and a human retains the loud staleness probe. **If you want it inside the skill anyway**, that is a real relaxation of the decision's third sentence and yours to make — I won't take it silently.
**Justification:** the approved decision names the SHA stamp as *the* staleness mitigation, and `--check` is a second mechanism with its own exit-code contract and precondition matrix. That is real added surface the request did not ask for, and the plan gate flagged it as drift — correctly. I recommend keeping it anyway for one reason: the stamp alone is a **passive** mitigation — it makes staleness legible *to a human who opens the page*. The mid-turn instruction asks for staleness to fail **loudly**, and a stamp nobody reads is exactly the "silently stops updating while everything reports green" mode. `--check` is what makes the stamp queryable at all — by a human, on demand. **If you'd rather hold v1 to the letter of the decision, cut it.** Cost re-derived **by class, not by flag string** — §11 criteria that scope to this mode either as `--check` *or* as "both modes": **6 of them, 3 deleted and 3 amended**:
- *deleted:* the four-value exit-code contract; the exit-3 never-published probe; the CLI-only constraint (it exists solely to bound `--check`);
- *amended:* the stale-`origin/main` criterion (survives as publish-only); the failed-fetch criterion (drops from two eval cases to one); the dirty-tree/non-`main` criterion (drops from "both modes" to publish only).

The publisher loses ~40 lines; the stamp is untouched; it can be added later with no rework. *(Three earlier drafts miscounted this — "6" from memory, then "3" with wrong membership in both directions, then "4" from a **literal `--check` grep** that structurally could not see the two criteria naming the same mode as "both modes". That last miss is the value-vs-class grep error this plan rules against twice — "class not value, per FB-0010", and "a `grep | head` is not a measurement" — committed inside the correction for it. The count is now derived by class.)*

**Open call 7 — this ships verified offline-only; nothing here exercises the live Notion API.**
**Recommendation:** ship it anyway, with the [LIVE] criterion left visibly unchecked and the PR body saying plainly that the tool is unverified end-to-end at merge.
**Confidence: MEDIUM-HIGH.**
**Justification:** every [CI]/[LOCAL]/[PRE-SHIP] criterion is satisfiable with zero Notion contact — deliberate, since no token belongs in CI, but it means CI can be fully green over a tool that has never authenticated. The alternative is to block the PR on your §5 setup, which puts a merge behind a manual step outside the repo. I'd rather merge the offline-verified tool with the gap stated in the PR body than either wait or, worse, let a green Spec-walk imply verification it doesn't have. **If you'd rather I hold the PR until one live publish succeeds, say so** — I'll do the setup walkthrough with you first and check the box for real.

**Open call 4 — hardening the secret-blocking hook (§6.2).**
**Recommendation:** out of scope here; route to `roadmap.md` § Exploration.
**Confidence: HIGH** on the scope call, **MEDIUM** on urgency.
**Justification:** it is a genuine gap (no Bash matcher, no commit-time scan) that predates this PR and affects every session, so folding it in would be scope-widening on a dev-tooling PR (FB-0095). The compensating CI scan in §6.2 covers *this* token class specifically.

---

## 11. Spec-walk (acceptance criteria — none checked; nothing is executed)

**Every criterion below is tagged with the bucket that runs it.** The plan gate caught that an untagged list plus a CI job is a trap: the repo-state criteria (zero-`plugins/flow/` diff, version unchanged, slot count 33) are one-shot properties of *this* PR, and wiring them into a job that runs on every `pull_request` would redden the next PR that legitimately edits `plugins/flow/**` — the repo's primary surface. That is the same red-build-for-an-unrelated-author outcome §4.2 rejects, one layer over.

| Tag | Runner | When |
|---|---|---|
| **[CI]** | `run_notion_publish_evals.py`, no flags | every PR — fixture-backed behavioural cases only; each must hold for **all** future PRs, not just this one |
| **[LOCAL]** | `run_notion_publish_evals.py --live-docs` | on demand — asserts against the live `dev-docs/`, whose shape is the sibling dispatch's territory |
| **[PRE-SHIP]** | `run_notion_publish_evals.py --pr-shape` | once, before this PR opens — one-shot diff-shape properties of this PR. **Never in CI** |

**Every [PRE-SHIP] criterion is anchored on `git merge-base origin/main HEAD`, not on `origin/main` directly** — it must measure *this PR's own diff*, not the distance to a moving `main`. Otherwise the in-flight CHANGELOG-fragmentation dispatch merging (or any version-bump PR) would redden this plan's most load-bearing criterion for reasons unrelated to this PR — meaning the sibling's resolution *does* reach this branch, through the criterion, falsifying §2 reason 4.

- [ ] **[PRE-SHIP]** `git diff $(git merge-base origin/main HEAD) --name-only` contains **zero** paths matching `^plugins/flow/`, `^\.claude-plugin/`, `^template/`, or the **exact repo-root path** `^README\.md$`. *Verify:* mechanical check over the name column, paired with the positive that the tool's own files exist. **The root-README match is anchored deliberately** — a substring `README.md` test would flag this PR's own `tools/notion-publish/README.md` (§4.7), making the plan's single most load-bearing criterion fail on a correct implementation, whose likely repair is to *weaken the pattern* rather than anchor it. Anchoring it here removes that temptation before it exists.
- [ ] **[PRE-SHIP]** This PR's own diff changes neither `plugin.json` nor the changelog surface. *Verify:* **paired, rename-survivable, and merge-base-anchored.** Let `BASE=$(git merge-base origin/main HEAD)`. Positive: the changelog surface at `BASE` (file *or* directory — the sibling is fragmenting `CHANGELOG.md` into one-file-per-entry, §3) resolves and exists, and its entry set is byte-identical between `BASE` and `HEAD`; positive: `plugin.json` parses at both refs and reports the **same** version at both — **read from `BASE`, not hardcoded to `1.37.0`**, so a rebase or an unrelated merge cannot redden it. An unpaired `git diff --  CHANGELOG.md` empty-check was the earlier form and is exactly `.claude/rules/general.md` rule 3's "prohibition satisfiable by deletion" — after the sibling's rename the literal pathspec matches nothing, the diff is empty for the wrong reason, and the criterion goes green having verified nothing.
- [ ] **[PRE-SHIP]** This PR's own diff leaves `flow.config.json` and the schema untouched; slot count unchanged. *Verify:* merge-base-anchored diff empty; `[0-9]+ slots?` class-grep identical at `BASE` and `HEAD` (class not value, per FB-0010).
- [ ] **[CI]** Dashboard is overwritten (not appended) on re-run, and two runs at the same SHA are **identical except the generation timestamp**. *Verify:* eval against a stubbed transport with an **injected frozen clock**, asserting the recorded request sequence. (The stamp embeds generation time, so byte-identity is unsatisfiable except by same-second coincidence — an earlier draft's wording would have passed or failed on clock timing rather than on the idempotency it exists to check.)
- [ ] **[LOCAL]** The rendered Roadmap section contains the `▶ Next up:` pointer, **and either** `origin/main`'s version string **or** the literal `no status paragraph for v<X> in § Now` skip line — not merely "extraction raised no error". *Verify:* content assertion against the live `roadmap.md`, plus a fatal case when `**▶ Next up:` matches ≥2 lines. **Stated as a disjunction deliberately:** an unconditional version-string assertion is unsatisfiable in the announced-skip state §4.2 declares correct — and by measurement (4 status paragraphs across ~15 versions) that state is *likely* at the next bump, so the unconditional form would go red on a design-sanctioned outcome and pressure the implementer to make the missing paragraph fatal after all.
- [ ] **[CI]** **Both §4.3 elisions announce themselves.** (a) Items dropped from § Now → the section ends with `Truncated: N further items`, N counting elided `**`-lead paragraphs plus unrendered `###` items (unit per §4.3). (b) The status paragraph cut at `Recently shipped:` carries an **inline elision marker**. *Verify:* four fixture cases — elision→callout with correct N; nothing elided→no callout; paragraph cut→marker present; paragraph not cut→no marker. An earlier single-criterion version covered only (a), so silently dropping the paragraph tail passed it.
- [ ] **[CI]** **A >2000-char paragraph round-trips losslessly**, split across multiple `rich_text` objects within one block — no ellipsis, no dropped tail. *Verify:* eval reassembling the emitted `rich_text` array and asserting byte-equality with the source paragraph. (Measured: the rendered `**▶ Next up:` paragraph, `roadmap.md` line 41, is **3029 chars** — genuinely over the limit, so this path runs on every real publish. An earlier draft pointed at line 15, which is **727 chars** and would have sent an implementer to a fixture that never exercises chunking at all.)
- [ ] **[CI]** `--check` exits **3** when no `Dashboard` page exists, and creates nothing. *Verify:* paired — exit-code assertion + a negative asserting zero write calls were recorded on the stubbed transport.
- [ ] **[CI]** Every page's first block is the stamp, carrying full SHA + `sha7` + ISO-8601 UTC time. *Verify:* eval on the generated block list.
- [ ] **[CI]** `visual-history.html` attaches via `embed.file_upload`; `embed.url` is never persisted anywhere in the repo. *Verify:* eval + a tracked-file grep for Notion file-URL shapes.
- [ ] **[CI]** Case study appends on a minor bump and never overwrites. *Verify:* eval across a simulated `1.37.0 → 1.37.1 → 1.38.0` sequence.
- [ ] **[CI]** **Each** enumerated failure in §4.4 exits non-zero **and** emits `ERROR:`. *Verify:* one executed eval case per row — not a grep for the absence of `|| true`.
- [ ] **[CI]** Read-back mismatch is fatal, **for each page against its own target, both resolved by id**: dashboard → the stamp block just appended (never the page's first block, which is still the previous run's stamp at read-back time); case-study append → newest append-stamp block. Plus: **after** the archive completes, the dashboard's first block **is** the new stamp — asserted as its own post-archive positive. *Verify:* three eval cases — dashboard mismatch exits non-zero; case-study append mismatch exits non-zero; **a case-study append whose creation stamp is legitimately older than the append does NOT fail** (the false-positive case that would otherwise redden the accumulating page permanently).
- [ ] **[CI]** The dashboard's Spec section is preceded by the staleness callout extracted from `dev-docs/README.md`'s status cell. *Verify:* three fixture cases — (a) cell present → rendered section contains the `Known stale` marker; (b) `spec.md` present but no cell → non-zero exit; (c) **`spec.md` absent → benign skip with a printed reason, exit 0** (so retiring `spec.md`, which `dev-docs/README.md` § Rules invites, cannot permanently break the publisher).
- [ ] **[CI]** "Recently shipped" is derived from `git log origin/main --oneline -n 5` and **reads no bytes of `roadmap.md`**. *Verify:* paired — negative (the section's code path never opens `roadmap.md`) **and** positive (rendered output matches the real `git log` subjects), since the negative alone is satisfiable by deleting the section.
- [ ] **[LOCAL]** **`extract.py` against the real `dev-docs/` as it stands today** produces dashboard sections **2, 3 and 4** (Current Focus, Roadmap, Spec+staleness-callout) without error, with each anchor named. *Verify:* the eval calls `extract.py`'s pure functions directly against the live repo. Scoped honestly: sections 1 (stamp), 5 (`git log`) and 6 (embed upload) are **not** `dev-docs/` extraction and do not live in `extract.py` — an earlier draft claimed this criterion covered "all six sections" and credited it with catching the "Recently shipped" defect, which is false twice over now that section 5 is off the extraction path entirely.
- [ ] **[CI]** **All six sections render end-to-end** against a stubbed transport *and* stubbed git calls. *Verify:* render-level eval — the layer where "all six" is actually assertable.
- [ ] **[CI]** A run started with a **rewound** local `origin/main` publishes the **post-fetch** tip: the stamp equals `git rev-parse origin/main` measured *after* the fetch, never the pre-fetch value, and `--check` compares against the post-fetch tip too. *Verify:* eval over a temp repo whose tracking ref is rewound behind a reachable remote; assert stamp == post-fetch SHA and != pre-fetch SHA. **This is the staleness hole, stated as what fetch-first actually guarantees** — an earlier version demanded a *non-zero exit* here, which the design never produces (the fetch succeeds and repairs the ref), so it was only satisfiable by making the eval's fetch fail, collapsing it into the separate failed-fetch criterion and never exercising this case at all.
- [ ] **[CI]** Case study is created **lazily** (first milestone append), not eagerly on publish. *Verify:* paired — negative (a non-milestone publish creates no `Case study` child) + positive (the next milestone run creates it and appends in the same run).
- [ ] **[CI]** The milestone **trigger** reads the case study's own append stamp, never the dashboard's. *Verify:* paired — positive (a `--no-milestone` publish after a minor bump still leaves the next run detecting the milestone) + negative (no code path reads the dashboard stamp for a version comparison). This is the case that catches the permanently-lost-milestone failure.
- [ ] **[CI]** Prior version missing/unparseable at the anchor SHA is fatal; no case-study page is a milestone by definition. *Verify:* two eval cases.
- [ ] **[CI]** **All publishable content is read via `git show origin/main:<path>`; no code path reads a `dev-docs/` file from the working tree, and the tool never runs `git switch`, `git checkout`, `git merge` or `git reset`.** *Verify:* paired — negative (no working-tree open of any `dev-docs/` path; no branch-mutating git verb anywhere in the source) + positive (a publish run against a temp repo whose *working tree* differs from `origin/main` renders `origin/main`'s content, proving the read really goes to the ref). The negative alone is satisfiable by deleting the reads.
- [ ] **[CI]** `.claude/skills/publish-state/SKILL.md` frontmatter sets `disable-model-invocation: true`. *Verify:* **paired** — positive (the key is present and `true`) + negative (no `Skill()` call anywhere names `publish-state`). The negative alone is satisfiable by deleting the skill; the positive alone would pass if something still invoked it programmatically. Matches the repo's own line: `.claude/skills/ship` (side-effecting) sets it, `preship` (read-only) does not. **[CI], not [PRE-SHIP]** — this is a standing invariant, not a diff-shape property: its negative half is a repo-wide `Skill()` grep that only a *future* PR can violate, and a check that stops running is the FB-0077 shape this plan invokes elsewhere.
- [ ] **[CI]** A missing `**Plugin at v<version>` status paragraph is a **benign announced skip**, not fatal; a missing `▶ Next up:` anchor or § Now heading set **is** fatal. *Verify:* three fixture cases. Measured basis: only 4 such paragraphs exist across ~15 shipped versions, so fatal here would break publishing on the first bump whose author skips the convention.
- [ ] **[CI]** `--check` is a **CLI-only** diagnostic: `.claude/skills/publish-state/SKILL.md` does not expose it and nothing branches on its exit code. *Verify:* **paired** — negative (no `--check` in the skill, no programmatic consumer of its exit code) + positive (the CLI accepts the flag and returns the four-value contract). Pins the decision's "no skill ever reads it" constraint mechanically rather than by prose.
- [ ] **[CI]** The `visual-history.html` payload is written to a `tempfile.TemporaryDirectory()` removed on **every** exit path, success or failure. *Verify:* paired — positive (upload reads from that path) + negative (no residual file after each enumerated failure case).
- [ ] **[CI]** Overwrite is **append → read-back → archive**, never archive-first. *Verify:* paired — positive (recorded request order puts every archive call after the stamp read-back) + negative (a failure injected mid-append leaves the old children un-archived, so the page is never empty-and-unstamped). Ordering, not mere presence, is the property.
- [ ] **[CI]** Both modes run successfully from a **dirty tree on a non-`main` branch** — the state of this very workspace. *Verify:* eval; this is also the standing regression guard against the checkout apparatus creeping back.
- [ ] **[CI]** **Every version read resolves at `origin/main`, never at HEAD** — the roadmap anchor's interpolated version, the milestone trigger's current version, and the rendered version string. *Verify:* publish from a branch whose `plugin.json` differs from `origin/main`'s; assert it renders `origin/main`'s version, finds the roadmap anchor (rather than hitting the fatal missing-anchor branch), and detects **no** spurious milestone. This is the case that catches a case-study append firing for a version that is not on `main` — on the one page that cannot be re-run to fix.
- [ ] **[CI]** A failed `git fetch origin main` is fatal in **both** modes and never degrades to the local ref. *Verify:* two eval cases.
- [ ] **[CI]** **The fatal anchor set is exactly:** `## Current Focus` (plan.md), the § Now heading set + `**▶ Next up:` (roadmap.md), and `dev-docs/README.md`'s spec status cell **when `spec.md` exists**. Each missing ⇒ fatal, naming the anchor and the file — never an empty section. **The two announced-skip exceptions are `**Plugin at v<version>` and an absent `spec.md`.** *Verify:* one eval case per member of the fatal set, plus the two skip cases. Stated as an explicit set rather than "every anchor", because the unqualified form contradicted the two carve-outs directly above it.
- [ ] **[PRE-SHIP]** `dev-docs/roadmap.md` gains the § Exploration entry for secret-hook hardening, and this PR's roadmap diff touches **no other section**. *Verify:* positive grep for the entry + `git diff` hunk-range assertion.
- [ ] **[PRE-SHIP]** FB-0099's stale "Held until MERGE" reservation line is swept to a cleared note in the same commit that reserves FB-0100. *Verify:* read the diff.
- [ ] **[CI]** `--check` exits **0** when the live stamp == `origin/main`, **2** when behind, **3** when never published, **1** on a probe error. *Verify:* four eval cases.
- [ ] **[PRE-SHIP]** **(a)** Every `CLAUDE.md` site listing the dev-side commands also names `/publish-state`. *Verify:* class-grep — `git grep -n '/preship' CLAUDE.md` returns N sites (2 today: lines 74, 133) and **all N** also name `/publish-state`, with `N > 0` asserted. Derived from the file, so a third command-list site added later cannot pass vacuously.
- [ ] **[PRE-SHIP]** **(b)** `CLAUDE.md` § 3's tools table has a row naming `tools/notion-publish/`. *Verify:* its own positive grep. Split from (a) deliberately — the tools row names a **path**, not a command, so the `/preship`-derived class-grep structurally never inspects it and (a) alone would go green over its absence.
- [ ] **[CI]** The two child pages are resolved by title lookup under the parent, created once if absent, and ≥2 same-title children is fatal. *Verify:* three eval cases (absent / one / two) against a stubbed transport.
- [ ] **[CI]** **A dashboard overwrite leaves the case study's blocks intact.** *Verify:* eval asserting every archive call targets a child of the *dashboard* page id, never the parent id — the specific mistake that would silently destroy the accumulating page.
- [ ] **[CI]** Case-study content is selected by `git diff <last_stamp>..origin/main -- dev-docs/history.md`, and **no code path parses a version string out of a history heading**. *Verify:* paired — positive (selection matches a fixture range) + negative (no version regex over headings).
- [ ] **[CI]** The case-study range anchor is a **per-append stamp block**, never the dashboard's stamp and never the case-study page's first block. *Verify:* paired — positive (the anchor is read from the newest append-stamp among the page's children) + negative (no code path reads the dashboard page for a range).
- [ ] **[CI]** The case-study append-stamp block is written **last**, after a read-back of the entry blocks. *Verify:* paired — positive (recorded request order puts the stamp write after the entry batches and after their read-back) + negative (**a failure injected after the first entry batch leaves no advanced watermark**, and the next append's range still includes every entry the interrupted run dropped). This is the permanent-silent-data-loss path; ordering, not presence, is the property.
- [ ] **[CI]** The first-ever backfill announces itself (`first-ever backfill: N entries across M requests`) before starting. *Verify:* eval; measured basis is 37 entries / 673 KB, guaranteed multi-batch.
- [ ] **[CI]** **Two consecutive milestone appends separated by an intervening non-milestone publish produce disjoint, gap-free entry sets.** *Verify:* eval simulating land → land(milestone) → land → land(milestone) and asserting the union equals every added entry with no duplicates. This is the case that catches both failure directions the plan gate found.
- [ ] **[CI]** First-ever append on a freshly created page takes the full history; an unstamped-but-non-empty page is fatal; an unparseable stamp is fatal; a zero-entry range is a printed skip, not a failure. *Verify:* four eval cases.
- [ ] **[CI]** No code path reads Notion into the repo, and `GET /v1/comments` is never called. *Verify:* paired **at the transport seam** — negative (no `/v1/comments` request recorded across every exercised case) + positive (the stub records the *complete* endpoint set actually called, asserted equal to the expected page/block/file-upload set, so the negative cannot be satisfied by making no calls at all). Plus a tree-diff after a stubbed run proving no repo file was written.
- [ ] **[PRE-SHIP]** The three manual comment rules (§8) are documented in `dev-docs/workflow.md` and `tools/notion-publish/README.md`. *Verify:* content assertion. **Tagged [PRE-SHIP], not [CI]** — it asserts the content of a live `dev-docs/` file, and in CI it would redden the build for any future author who rewords that section, exactly as §4.2 argues.
- [ ] **[CI]** No tracked file contains a Notion-token-shaped literal, with `scanned > 0` asserted. *Verify:* eval.
- [ ] **[CI]** **The token value never reaches stderr or an exception string.** *Verify:* paired (§6.1) — negative (run every enumerated §4.4 failure case through the stubbed transport with a sentinel token value; assert the sentinel appears in no captured stderr and no raised message, including the 401 path that names token expiry) + positive (the `Authorization` header is built from `NOTION_TOKEN`). The tracked-file scan above cannot cover this: it inspects committed files, while the risk here is a runtime `[notion-publish] ERROR:` line that §4.4 requires every failure path to print.
- [ ] **[CI]** All expected `tools/notion-publish/` files are actually tracked despite `.gitignore:10`. *Verify:* `git ls-files tools/notion-publish/` exact-list assertion (§4.6). **[CI], not [PRE-SHIP]** — it inspects only paths this PR owns, so it can never redden an unrelated author, and it must keep running: the `.gitignore:10` trap applies to every *future* file added there, which a one-shot check would silently miss.
- [ ] **[PRE-SHIP]** `.github/workflows/ci.yml` contains an executable `run:` step invoking `tools/notion-publish/run_notion_publish_evals.py`, in its own job. *Verify:* positive assertion that the step exists, that it **passes no flag at all** (argv after the script path is empty), and that the harness exits 0 when CI runs it. **Assert emptiness, not a forbidden-flag list** — an earlier draft forbade only `--live-docs`, which a `--pr-shape` step would satisfy: green on this PR, then red on the next PR that legitimately edits `plugins/flow/**`, which is the exact outcome the bucket split exists to prevent. Without this the entire criteria apparatus can ship unwired — contributing zero regression protection while appearing to — and `ci.yml`'s own join check does not cover `tools/**` (§4.7).
- [ ] **[CI]** Evals run fully offline — zero network, zero live API call. *Verify:* **at the transport seam, not by import-grep.** `publish.py` takes its HTTP transport as an injectable dependency; the harness registers a stub that **raises** on any real network call, and the eval asserts (positive) that every enumerated §4.4 failure case was exercised *through* that stub. The `run_shadow_sampler_evals.py` import-grep precedent does not transfer — it asserts the tool source imports no networking module, which `publish.py` must fail by design since it imports `urllib`; narrowing that grep to the harness file alone would go green while the harness still reached the live API through the real transport. That is the negative-assertion-alone shape `.claude/rules/general.md` § Consistency discipline rule 3 forbids.
- [ ] **[PRE-SHIP]** `dev-docs/README.md` indexes nothing new under `research/`/`handoffs/`; CLAUDE.md § 3's tools table gains the third row. *Verify:* read.
- [ ] **[PRE-SHIP]** FB-0100 reserved in `reserved-feedback-numbers.md` in its own first commit, before the `feedback.md` entry is drafted. *Verify:* `git log -p` on that file.
- [ ] **[PRE-SHIP]** `dev-docs/plan.md` § Handoff Notes gains a **dated review line** naming the two-land deletion checkpoint (§9). *Verify:* content assertion. **This is the criterion that matters** — the README home below is one §9 itself identifies as unread, so pinning only that would let the PR go green while shipping exactly the FB-0077 shape §9 exists to prevent.
- [ ] **[PRE-SHIP]** Deletion criterion (§9) **and the full removal procedure (§4.5)** are written into `tools/notion-publish/README.md`, not only into this plan. *Verify:* **derive the step count from §4.5** and assert the README names every one of them — never a hardcoded number, since a literal "four" is exactly what went green over the missing `workflow.md` step. A deletion criterion whose procedure leaves CI red does not satisfy "if it vanished, the repo is unaffected".
