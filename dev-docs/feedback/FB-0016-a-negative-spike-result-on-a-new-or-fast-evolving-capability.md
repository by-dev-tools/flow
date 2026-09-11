### FB-0016: A negative spike result on a new or fast-evolving capability is one data point, not a verdict to abandon — record a re-test trigger (across un-sampled problem types, incl. UI) instead of writing it off
**Date:** 2026-05-28
**Source:** user direction (stated during the dynamic-workflows reviewer-refutation spike)

**What was said:** The spike returned a negative result — blind independent refutation did not cut the reviewer false-positive tax on one shell-script diff (`bootstrap.sh`). The user directed: write the verdict honestly, but ALSO put it on the roadmap to re-test later with different problem types — "this feature is going to evolve so we don't want to completely write it off yet ... it will be important to test in some other projects with UI as well." Earlier in the same session the user also insisted the experiment run on "something useful and substantive where I will be able to judge the result," and steered the spike's scope to its highest-signal, lowest-cost shape.

**Synthesized rule:** When a spike, eval, or experiment yields a negative or surprising result about a **new or fast-evolving capability** (research-preview features, freshly-shipped primitives, anything still changing under us):

```
(a) Record the result honestly in history.md WITH the named limitation that
    bounds it (one diff / one problem type / already-reviewed-clean target /
    single-model / etc.). A conclusion is only as general as the sample.

(b) Do NOT treat one data point on one problem type as a general verdict to
    abandon the direction. Create a roadmap § Exploration entry with a
    `Surfaces when:` trigger to re-test as the capability matures — and
    enumerate the problem types NOT yet sampled (UI surfaces especially,
    genuinely-buggy / pre-review diffs, larger/migration scale).

(c) Capture the most promising untested variant the experiment pointed at,
    so the re-test starts ahead of where this one ended (here: informed-
    independent refutation + a significance rubric, vs the blind variant).

(d) Scope experiments to substantive, human-judgeable targets up front — a
    trivial or unjudgeable target produces a result you can't trust either way.
```

**Applies to:** spikes + research passes, evaluating new Claude Code / Anthropic capabilities (dynamic workflows, future primitives), roadmap § Exploration hygiene, history.md verdict entries.

**Validation:** First applied to the 2026-05-28 reviewer-refutation spike — verdict recorded in `history.md` ("Reviewer-refutation spike — verdict") with its single-diff limitation named, and re-test direction captured in `roadmap.md` § Exploration ("Dynamic-workflows-based review: re-test refutation across problem types, incl. UI"). See `dev-docs/research/dynamic-workflows-2026-05.md`.
