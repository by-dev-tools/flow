#!/usr/bin/env python3
"""Host-toolchain ground truth: is the toolchain a platform needs present HERE?

Flow can already express "there is no runnable target" (`platform: library|none`,
`verifyEnabled: false`). It had no way to express "runnable in principle, just not
on *this* host" -- so a cloud Linux workspace on a `platform: ios` project either
burned a launch attempt to reach `Unknown`, or declared a skip the skip-auditor
mechanically refused. This module is the one fact both halves of the fix need.

TWO CONSUMERS, ONE DEFINITION (FB-0010):
  * `/flow:verify-build` SKILL.md 1.2 -- the PRODUCER. Self-skips (a third case
    beside `verifyEnabled=false` and `platform library|none`) when the toolchain
    is absent, instead of attempting a launch that cannot succeed.
  * `skills/audit-skips/lib/skip-audit-checks.py` -- the AUDITOR. Confirms a
    toolchain-absence claim against this same probe before calling it LEGITIMATE.

`absent()` IS THE PREDICATE -- never "missing() is non-empty".
    A platform's entry lists every binary its build needs. `missing()` reports
    which are unresolved; `absent()` is True only when EVERY one is. The gap is
    the partial-toolchain host (Xcode installed but `xcrun` off PATH): there
    `missing()` is non-empty while `absent()` is False, so the gate RUNS rather
    than being suppressed on a machine that could have performed it. Erring
    toward running is the conservative direction; erring toward skipping
    silently drops the behavioral gate, and the resulting manifest entry is
    CHECK_ONLY + blocked, so no waiver can subtract it.

WHY `ios` ONLY, and why widening this dict is not a one-line change:
    The producer has no NEEDS-JUDGMENT escape hatch -- a table that is wrong in
    the permissive direction suppresses the gate on a capable host, silently.
    Android is the concrete counter-example: the near-universal build entry point
    is the repo-local `./gradlew` wrapper, which `shutil.which("gradle")` never
    resolves, so every fully-equipped Android machine would self-skip on every
    run. `tauri` has the same unresolved question (`cargo` is usually present
    even where the platform toolchain is not). Admitting a platform requires a
    wrapper-aware probe AND a capable-host fixture, not a new dict key.

DELETION CRITERION (FB-0088): delete this table if `platform` ever gains a
first-class per-project toolchain declaration -- it would then encode knowledge
the project states directly, and re-deriving it is strictly worse.

Stdlib only. Python 3.7+.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

# platform (flow.config.json `platform` enum) -> the host binaries its build needs.
# See the module docstring before adding a key.
#
# The value is AND-semantics (every binary must be missing for `absent`), so a
# platform whose build has ALTERNATIVE entry points -- Android's `gradle` vs the
# repo-local `./gradlew` wrapper -- cannot be expressed by adding a key. Widening
# to those platforms changes the value SHAPE, not just the table's length.
PLATFORM_TOOLCHAIN = {
    "ios": ("xcodebuild", "xcrun"),
}

# THE SENTENCE, AND THE NEEDLES THAT MATCH IT, LIVE HERE TOGETHER -- deliberately.
# The producer (verify-build SKILL 1.2) writes this string as its `skip_reason`;
# the auditor (skip-audit-checks) requires one of these needles before it will even
# consult the host. That is a contract between two files, so it gets the same
# one-definition treatment the table does: a reason phrased in the SKILL and needles
# hand-kept in the auditor is the FB-0010 fan-out this module exists to prevent,
# just applied to prose instead of data. Both sides import from here.
SKIP_REASON_PREFIX = "toolchain absent:"
REASON_NEEDLES = ("toolchain", "simulator")


def required(platform):
    """The binaries `platform`'s build needs on this host. () if not toolchain-gated."""
    return PLATFORM_TOOLCHAIN.get(str(platform or ""), ())


def missing(platform, present=None):
    """Which of `platform`'s required binaries do NOT resolve on this host.

    `present` (an iterable of command names to treat as resolvable) exists for
    eval determinism only -- CI runners have no Apple toolchain, so the
    "toolchain present => SHOULD-RE-RUN" case would otherwise be unrunnable and
    would silently never execute. Production callers pass nothing and get the
    real `shutil.which`.
    """
    req = required(platform)
    if present is None:
        return [b for b in req if shutil.which(b) is None]
    have = set(present)
    return [b for b in req if b not in have]


def absent(platform, present=None):
    """True only when EVERY binary `platform` needs is missing.

    Not `bool(missing(...))` -- see the module docstring. A partially-equipped
    host must run the gate, not skip it. An un-gated platform is never absent
    (there is no toolchain requirement to be absent).
    """
    req = required(platform)
    if not req:
        return False
    return len(missing(platform, present)) == len(req)


def load_present(path):
    """Read the eval-determinism override: one command name per line.

    Public because BOTH CLIs accept `--which-from` and must agree byte-for-byte on
    the format. A second copy in the auditor is how the producer and the auditor
    would come to disagree about which binaries count as present.
    """
    if not path:
        return None
    return [ln.strip() for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()]


def skip_reason(platform, present=None):
    """The canonical `skip_reason` for a toolchain-absent skip.

    Returns None when the platform is not toolchain-gated, or when at least one of
    its binaries resolves -- i.e. exactly when the producer must NOT self-skip.
    """
    if not absent(platform, present):
        return None
    return f"{SKIP_REASON_PREFIX} {', '.join(missing(platform, present))} not on PATH"


class ConfigError(Exception):
    """flow.config.json is present but unusable. Distinct from 'absent' on purpose.

    The caller's exit code is the whole interface here: 0 means "skip the build",
    1 means "run it". A config we cannot parse must be NEITHER -- collapsing it into
    1 would make a corrupt config look exactly like a fully-equipped host, so the
    build would be attempted, fail to launch, and judge Unknown, which then reads as
    a regression the change never introduced. That is the precise bug this module
    exists to prevent, and it would be restored silently.
    """


def _platform_from_config(path):
    """The declared platform, or None when there is no config to read.

    A MISSING file is a normal condition (no config, no declared platform, run the
    build) -- but a file that is present and malformed is not, and gets a distinct
    exit code rather than a shrug. `json.loads("[]")` parses fine and then explodes
    on `.get`, so the isinstance check is load-bearing, not defensive noise.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        cfg = json.loads(raw)
    except ValueError as exc:
        raise ConfigError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(cfg, dict):
        raise ConfigError(f"{path} is not a JSON object (got {type(cfg).__name__})")
    return cfg.get("platform")


def main(argv):
    ap = argparse.ArgumentParser(
        description="Host-toolchain ground truth: is this platform's toolchain absent HERE?")
    # ONE subcommand on purpose. An earlier shape had `absent` (predicate) plus
    # `missing` (JSON list) plus `required`, which made the SKILL spawn python
    # twice and then strip JSON punctuation with sed to rebuild a sentence this
    # module could simply emit. `required` had no caller at all. The predicate the
    # shell needs and the sentence it writes are one question, so they are one call.
    ap.add_argument("command", choices=("skip-reason",))
    ap.add_argument("--platform", default=None, help="platform value (default: read from --config)")
    ap.add_argument("--config", default="flow.config.json")
    ap.add_argument("--which-from", default=None,
                    help="file of command names to treat as present (eval determinism only)")
    args = ap.parse_args(argv[1:])

    try:
        platform = args.platform if args.platform is not None else _platform_from_config(args.config)
    except ConfigError as exc:
        print(f"toolchain: {exc}", file=sys.stderr)
        return 2
    try:
        present = load_present(args.which_from)
    except OSError as exc:
        print(f"toolchain: cannot read --which-from {args.which_from}: {exc}", file=sys.stderr)
        return 2

    # Shell-facing contract, and the caller MUST distinguish all three:
    #   exit 0 + the sentence on stdout -> the toolchain is absent; skip the build.
    #   exit 1, no output               -> it is present (or the platform is not
    #                                      toolchain-gated); run the build.
    #   exit 2 + a diagnostic on stderr -> the check could not run at all.
    # A caller that folds 2 into 1 turns "I could not tell" into "everything is
    # fine", which is the failure mode this module was written to remove.
    reason = skip_reason(platform, present)
    if reason is None:
        return 1
    print(reason)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
