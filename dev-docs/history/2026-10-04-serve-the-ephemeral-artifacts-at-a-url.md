## 2026-10-04 — Serve the two ephemeral artifacts at a URL a phone can open, without ever removing the honest line

**Branch:** `conductor/mobile-option-1-preview-url` · **Version:** v1.60.0 · **Roadmap:** D7 option 1 · **No new FB**

PR B of two. v1.59.0 made the hand-off *honest* about an unreachable file; this makes it *optionally reachable*. Option 1 from `dev-docs/research/2026-10-mobile-workflow.md` § 8.

### The constraint that reshaped the feature, and where it came from

Not from the research doc, and not from Ben's device results. From the host CLI's own `--help`:

> *"Each workspace has one preview URL; setting a different port keeps the URL."*

So the obvious design — serve the prototype on one port and the walkthrough on another, hand out two stable links — **cannot work**. Re-pointing the preview to a second port silently breaks the first link while leaving it looking perfectly valid, which is precisely the defect class v1.59.0 existed to remove. Both artifacts are staged into one `.flow/preview/` directory and handed out as `<url>/<file>`: one port, one URL, two stable paths.

This is the plan's most load-bearing decision and it was available for the cost of reading `--help` before designing. Worth recording as a method, not just an outcome.

### What shipped

A **`previewBackend` host adapter**, modelled directly on the existing `dispatchBackend` — three verbs (`serve` / `publish` / `unpublish`), a **closed** `{dir}`/`{port}` placeholder vocabulary, refuse-rather-than-escape, and a template carrying a shell operator rejected outright with the fix named ("put the backgrounding inside a script the template CALLS").

**There is deliberately no `{url}`.** The URL is the adapter's *output*, parsed from `publish`'s stdout — never a value a template supplies. A template that could compose the URL would let project config decide what the hand-off *claims*, which is the one thing a hand-off must not delegate.

### Tradeoffs

- **The URL is additive, never a replacement.** Measured twice (Ben, and the touch worker): a served preview's backend dies when its workspace sleeps while the URL *registration* survives. A link that looks live and is dead is strictly worse than a path that is honest about being local. The local line is the process-independent floor.
- **The URL is a bare autolink; the path stays a code span.** Deliberately opposite, because a code span renders as untappable monospace on a measured touch client. The rule — *render it the way the reader can act on it* — is written into the engine's docstring so the two treatments are not later "harmonised" into one. They look inconsistent and are not: the reader's available action differs.
- **`https` only.** `publish` printing an `http://` URL is refused with a stated reason rather than passed through: the page is sign-in-gated, so an unencrypted URL would downgrade the transport carrying that session. Gated twice — in the adapter and again in the renderer, since `--url` can also arrive from a caller that composed it by hand.
- **Never publish a port nothing is listening on.** The CLI's help says something must be listening; publishing a dead port yields a live-looking dead link. Checked before `publish`, and the predicate is validated against a *real* server on a real port before its negative is trusted.
- **Publish and leave, audience stated next to the link.** Teardown is `unpublish`, called only by `/flow:post-merge` — a ship is often followed by a human reading the page minutes later, and a link that dies mid-read is the worse failure. The orchestrator decided this and is telling Ben so he can overrule. The access statement goes *beside the link*, not only in docs: the person deciding whether to forward a URL is the one who needs to know who can open it.
- **Flow's own config sets the slot.** The orchestrator's addition, and the sharpest point in the review: a slot unset by default is a feature that runs **nowhere**, including here, and is therefore never exercised — the FB-0085 shape. `flow.config.json` is project config, so naming a vendor there is fine; the same name in `plugins/flow/**` would not be. `serve` calls `.claude/bin/flow-preview-serve.sh` because backgrounding needs the very operators the adapter refuses — which is exactly what `validate` tells an author to do.

### Measured, paired, in this repo

| Probe | Result |
|---|---|
| unauthenticated `curl` of a served page | `http=401`, 30 bytes, *"Sign in to view this preview."* |
| the same file via the local control (`127.0.0.1:8901`) | `http=200`, 86 bytes, content present |

So the sign-in gate is **real**, not merely documented — and the content is not exposed to an unauthenticated fetch. The pairing is the point: the 401 alone would not distinguish "gated" from "broken".

### What review changed, and the two defects worth naming

The first implementation shipped the feature's *shape* and got two things wrong that no test caught, both found by review:

1. **`<url>/<file>` was documented in four places and implemented in none.** The schema said flow "hands out `<url>/<file>`"; ship's prose said the same; the roadmap and this entry said it. Nothing composed it. The hand-off passed `publish`'s raw stdout — the **directory** URL — so a reader tapping the link got a server-generated index listing, and *both* artifacts got the identical link. "One URL, two stable paths" collapsed into one ambiguous one: precisely the live-looking-but-wrong hand-off this workstream exists to remove. The eval could not see it because it handed the renderer an already-composed URL — a pin one layer below the claim, which `.claude/rules/general.md` item 4's third corollary names exactly. The composition now happens in the helper and the eval drives *that*.
2. **A failed staging step still published.** `cp -f … || echo` with no flag, so when the walkthrough had not been generated — an explicitly supported state — flow served and published a URL for a file that was not there.

Both fixes landed with the restructure below, which the altitude lens argued for and I had declined on the first pass.

### The prose-shared block became a sourced helper, and the reviewer was right

The first cut put a 40-line serve/publish block in `/flow:ship` and told the other two skills, in prose, to "run ship's block with `ARTIFACT=…`". Three structural problems, not aesthetic ones:

- `ship-spike`'s instruction sat **after** the fence it modified, so a top-to-bottom reader executed the render with `PREVIEW_URL` empty — the exact silent drop the block warned about.
- "Run ship's block" was copy-with-two-mutations, since ship's block set `ARTIFACT` itself and ended with its own render.
- The only mechanical pin available on the two deferring callers was a case-insensitive grep for the phrase "same bash call" — a pin on a string, not a decision.

`skills/ship/lib/serve-preview.sh` is now sourced into each caller's existing fence (precedent: `verify-pr-body.sh`). The same-Bash-call constraint, which I had treated as an argument against a helper, is actually the argument *for* one: sourcing satisfies it by construction instead of by an instruction three skills have to remember.

### What the existing evals caught, which is the part worth keeping

Three failures came from checks that already existed, and each is a mechanism working rather than a surprise:

1. **`run_dispatch_backend_evals.py` § 7's exact artifact count** went 11 → 12 the moment `preview_backend.py` landed in `plugins/flow/lib/`. Its own comment predicted this: *"Bumping it is therefore the intended cost of adding a shared lib, not friction to route around."* It also means the new lib is covered by the **existing** host-literal sweep, so this PR adds no duplicate scan — it asserts the join instead.
2. **The slot-count fan-out** (`N slots`) fired at four shipped surfaces — `docs/workflow.md`, `doctor/SKILL.md`, `template/base/CLAUDE.md.template`, `README.md` — exactly the case `.claude/rules/general.md` item 2 names.
3. **The region-scoped no-client guard shipped in v1.59.0** fired on this PR's own rationale prose in `prototype/SKILL.md`. The guard is right and was kept: a reader skimming a hand-off region should not find a client named there, rationale or not. The measured detail lives in the engine docstring, outside the region.

### One extraction, and the delta it quietly carried

`dispatch_backend.render_template` was extracted and made public so both adapters share one refusal policy — not just its data. The plan had declared only a new sibling lib, so this was scope taken on a reviewer's argument: the first cut imported four module-privates and re-derived the control flow, and the copy had **already diverged** (preview's `validate` flagged an unexpanded `~/` that its own `render` passed through). Sharing deleted 56 lines and made that divergence impossible rather than remembered.

It also carried a behaviour change nobody asked for and nothing measured: dispatch's `render` now refuses `~/` too, where before only its `validate` did. Safe — a consumer with such a template was already being told it was invalid, and was already getting a literal unexpanded tilde at dispatch — but "safe and unmeasured" is how the next one ships unnoticed, so it is now pinned at the render layer with a paired positive. And generic-ising the message silently dropped FB-0108's `{message}` teaching from the refusal an author actually *hits*, while `validate` kept it, so nothing went red; restored through the same hint mechanism.

### One guard this PR had to narrow, and why that is not a weakening

The same no-client guard fired on the *rendered* hand-off, because both interpolated values legitimately contain a vendor name: the **audience** ("signed in to Conductor…") and the **URL's hostname**. Neither is a claim about a client's *behaviour* — one is a measured access fact from project config, the other is a real address. The guard is now scoped to flow's own authored wording by removing the interpolated values first, and paired: a client name in flow's own prose still warns. A warning that fired on every correctly-served hand-off would have trained people to ignore the warning, which this repo names as its own failure mode.

### Residual, stated rather than buried

**A reviewer without workspace read access gets nothing from the link**, and the local line is all they have. This is **inference, not measurement** — Ben's test was his own account on his own workspace, and nobody has tested a second viewer. It is a standing reason the local line is not optional, and it is recorded in roadmap D7 as such.

Also recorded in § Next at the orchestrator's instruction: `dispatchBackend` has the *same* unset gap in this repo that `previewBackend` just closed (observed consequence: `/flow:spawn` could not create workspaces here). Deliberately not fixed in this PR — it is the orchestration suite's wiring, not this feature's.
