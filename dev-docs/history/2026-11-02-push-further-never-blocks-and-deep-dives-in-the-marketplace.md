# SAFETY — Push-further never blocks, and deep-dives joins the marketplace (v1.66.0)

**Date:** 2026-11-02
**Branch:** `florence-v6`
**Commit / PR:** [this commit] · deep-dives itself: `by-dev-tools/deep-dives@f57f4a7`
**Feedback:** FB-0141

**SAFETY:** touches the install surface (`.claude-plugin/marketplace.json`, `.claude/rules/safety.md`).
Preserved: flow's own entry, its description↔`plugin.json` parity, and version parity, all still
enforced by `run_plugin_desc_evals.py`. Added: a second, GitHub-sourced entry whose descriptions now
fall under that harness's caps too, and a by-name read in `plugin-provenance.py` so the second entry
cannot be reported as flow's version. Both manifests pass `claude plugin validate`, and a real install
from this checkout succeeded.

## What was done

- The push-further lens now states that it never blocks, and that a missing quality the surface
  doesn't call for is not a finding. Its questions are framed as prompts that fit any surface. On
  interaction surfaces, Josh Puckett's eight lenses are offered as an optional extra frame.
- lens-experience's Lens B (push-further at the brief/plan gate) carries the same rule.
- New eval `run_push_further_evals.py` pins that guarantee, running a mutation of each of its
  seven checks on every run and failing if any stays green.
- A new public repo, [`by-dev-tools/deep-dives`](https://github.com/by-dev-tools/deep-dives), holds a
  second plugin for interactive design sessions. Its first skill is `puckett-uncommon-care`. This
  marketplace lists it by GitHub source.
- `plugin-provenance.py` reads flow's marketplace entry by name instead of `plugins[0]`.

## Why

Ben asked to find and centralize the permutations of Puckett's "uncommon care" across his projects.
The inventory found seven definitions in nine repos, in two shapes:

- the automated push-further lens: flow's agent, plus a pre-flow inline copy in md-manager;
- a standalone 8-lens `/uncommon-care` critique: ui-playground, todolist, mini-design-system, and
  designer (vendored from mini-design-system).

They had drifted. Flow's lens covered six of the eight lenses, and the good rules were split across
copies. Flow's lens and `exploration` skill both pointed at a deep-dive skill "not yet shipped".

## Design decisions

- **Two surfaces, not one doctrine with two lengths.** The first proposal re-homed the standalone
  critique in flow as a longer automated pass. Ben's correction (FB-0141) was that the second version
  should be a *session the human is in*. Re-homing the automated version would only have produced
  more of the lens's judgment, while the session puts the taste call with the human.
- **The lens is not bound to the eight lenses.** The first plan re-grounded the lens on all eight,
  with a drift check. Ben pointed out that the lens reviews every diff, not only deep interactions,
  so binding it would make it wrong on most of its inputs. The eight now appear in the lens only as
  an optional frame for interactions. With one authoritative copy (in deep-dives) and no rigid tie,
  the drift check was dropped. There is nothing to keep in sync.
- **The session lives outside flow.** Ben: ui-playground has no flow config on purpose, because it's
  for incubating ideas, and flow's process costs time and tokens there. A skill inside flow means
  enabling flow, and that brings its model-invoked rule-skills (plan-before-code, confidence
  verdicts) into the repos where they cost the most. Ben then widened the plugin's purpose: it will
  also hold `yuan-brand`, which another session in this workspace is building. Hence the umbrella
  name `deep-dives`.
- **Own repo rather than a second plugin directory here.** In this repo every tweak would go through
  the ship pipeline, a history entry and evals, which is the heavy process deep-dives exists to
  avoid. Listing it here by GitHub source keeps it installable from the marketplace users already
  have.
- **Attribution in the open.** At Ben's request, deep-dives' README credits Josh Puckett (Dive Club
  episode, Interface Craft) and Jason Yuan (Dive Club episode) plainly. It states that the doctrine
  files are an AI-assisted reading not checked against a transcript, and that the project is not
  affiliated. Both episode URLs were verified via YouTube oEmbed. Quotes in the Puckett doctrine are
  marked *(summary)*, because they come from a third-party write-up, not the audio.

## Technical decisions

- **The eval checks labels against an allow-list.** The lens's output labels must equal the three
  buckets exactly, so a new blocking label fails whatever it's called. The selftest's mutation for
  this check is `must-fix`, which shares no token with `BLOCKER` (FB-0136's out-of-enumeration
  positive).
- **The triage negative is paired with a positive.** "No bucket on the BLOCKER line" is paired with
  "every bucket routed on some non-blocking line", so deleting the buckets from triage cannot turn
  the check green (general.md item 3).
- **/simplify trimmed the lens prompt** (the eight-lens list mostly restated the lens's own
  questions, so it now names only the two Puckett adds: range→depth and metaphor integrity) and
  folded the selftest into every run, so CI carries one step. Its altitude pass found that Lens B of
  lens-experience runs the same lens at the brief gate without the rule, so the rule and a label
  check now cover it too. Lens A's experience-gap BLOCKER was left alone: it is FB-0046's deliberate
  plan-gate ambition check, and changing it is Ben's call, not this PR's.
- **The absence rule is pinned as text.** For a prompt, the sentence a model reads *is* the
  mechanism. The docstring says so instead of pretending this is behavioral coverage.
- **Provenance reads by name, falling back to `metadata.version`.** It no longer takes the first
  entry, and a flow entry with no version must not borrow the sibling's. The new test covers both
  orders plus the no-version world, and it went red when the read was reverted to `plugins[0]`.
- **The deep-dives marketplace entry carries no `version`.** `plugin.json` in deep-dives is the
  single source, so there is no second copy to drift.

## Tradeoffs discussed

- **Personal skill vs plugin.** A skill in `personal-user-skills` (already linked into the Mac's
  `~/.claude/skills`) would give a bare `/puckett-uncommon-care` with zero setup, but it would not
  exist in cloud workspaces. The plugin form costs the `deep-dives:` prefix. The docs say every
  plugin skill is prefixed, and that was confirmed in Claude Code's plugin-marketplace reference.
- **designer and mini-design-system** keep their ledger-writing copies for now. Both repos are
  inactive, so Ben deferred them.
- **Cleanup of the other copies** (todolist, ui-playground, md-manager's inline lens) is
  deliberately a follow-up, one PR per repo, after this lands.

## Lessons learned

- A concept copied into many repos had drifted in two directions at once: vocabulary (6 vs 8 lenses)
  and purpose (automated critique vs human session). The vocabulary drift was easy to see; the
  purpose split only surfaced when Ben named it.

## Merge-gate decisions (Ben, 2026-11-03)

- **deep-dives' `main` is now protected (security finding, option 1a).** The marketplace lists deep-dives
  unpinned, and its `main` had no protection while flow's did, so anything pushed there would have reached
  flow-marketplace installs unreviewed. Chosen over pinning a `sha` (every deep-dives tweak would need a
  flow PR, the process deep-dives exists to avoid) and over a separate marketplace. Applied: a PR is
  required, with zero approvals so Ben can merge his own; admins included; force-push and deletion
  blocked. Verified from this workspace via `gh api` (`protected: true`, `enforce_admins: true`). The
  roadmap § Next entry on trusting deep-dives' `main` stays open for the day it ships executable code.
- **The lens's deep-dives pointer is now pinned (coverage finding).** `session-pointer` in
  `run_push_further_evals.py`.

