#!/usr/bin/env python3
"""Resolve + validate + render the `dispatchBackend` adapter's commands.

Canonical cloud-workflow plan §4.10: the orchestrator suite ships in flow, and
"host-agnosticism is preserved by an adapter, not by exclusion" — the mechanics
of spawning a workspace, messaging a session and listing workers live behind a
`dispatchBackend` config slot, "so plugin artifacts carry no host-hardcoded
tokens and flow's project/host-agnostic quality bar holds."

The slot holds **command templates the consumer writes**, exactly the shape
`typecheckCmd` / `preflightCmd` already use one level down: the plugin ships the
*workflow*, the project's `flow.config.json` supplies the *command*. The
rejected alternative was a backend *name* the plugin maps to a built-in command
table — which would have put host literals straight back into shipped artifacts,
i.e. the thing the adapter exists to prevent.

Five verbs, and the placeholder vocabulary is **closed**:

    listWorkers   (no placeholders)      re-derive live state; never a snapshot
    createWorker  {name} {messageFile}   spawn a worker, first message = the brief
    sendMessage   {session} {messageFile} message an existing session
    workerStatus  {session}              last-activity, for the silent-worker sweep
    selfSession   (no placeholders)      this seat's own id — the ping return address

**Why there is no `{message}` placeholder, and why an unknown placeholder is a
hard error.** The orchestrator field manual's trap T6 records the shell-
composition hazard firing *four times in one session* among authors who had each
just finished reasoning about it — a refuted design, then silent data loss, then
unintended execution, and then the report of the third mangled by the third.
FB-0108 then took untrusted text off `add-entry`'s command line entirely rather
than quoting it at the call sites, on the principle that you fix the interface,
not the callers. A worker's brief and a worker's status line are agent-composed
prose about code: they routinely contain backticks around command and file
names, which is the highest-risk possible content to interpolate. So message
bodies travel as a **path** and only as a path. A template that names
`{message}` is rejected rather than escaped, because an escape is something an
author has to remember and a closed vocabulary is not.

Substitution values are additionally restricted to a conservative charset — no
spaces, no quotes, no shell metacharacters, no leading `-`. flow generates these
values itself (a scratch path, a session id, a branch name), so the restriction
costs nothing and removes the argument-injection case as well as the shell one.

**Never silently no-ops.** An absent slot, a missing verb and a malformed
template each produce a loud `⚠️` naming the documented manual fallback
(CLAUDE.md: "never silently no-op on a missing slot"). Degrading quietly here
would be the worst available failure, because the caller would conclude a worker
was dispatched when nothing ran.

**Deletion criterion (FB-0088):** delete when the backend CLI accepts structured
input (JSON on stdin) for every verb, so there is no command string to render
and no metacharacter boundary to defend.

Stdlib only. No network, no subprocess — this module renders commands, it never
runs them. Python 3.7+.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path

PREFIX = "[dispatch-backend]"

# The closed vocabulary. A template may use only these, and every one of them is
# supplied by a real call site — a placeholder the schema advertises but nothing
# supplies passes `check` and then fails at `render`, which is exactly the
# check-passes/dispatch-fails class the doctor check exists to prevent. `{branch}`
# was in this set with no required verb and no supplier, and was removed.
KNOWN_PLACEHOLDERS = {"name", "messageFile", "session"}

# Verb → (required placeholders, what it is for, what to do by hand if absent).
VERBS = {
    "listWorkers": (
        set(),
        "re-derive live worker state (§4.4 'state is live', §4.9 succession)",
        "list the live workspaces in your host's UI or CLI and paste the result",
    ),
    "createWorker": (
        {"name", "messageFile"},
        "spawn a worker whose first message is the dispatch brief (§4.10 instruct-not-remote-invoke)",
        "create the workspace by hand and paste the brief as its first message",
    ),
    "sendMessage": (
        {"session", "messageFile"},
        "message an existing session — re-address broadcasts, follow-ups, gate relays (§4.8 rules 5/6)",
        "open the worker and paste the message",
    ),
    "workerStatus": (
        {"session"},
        "last-activity timestamp for the silent-worker sweep (field manual T2)",
        "check each worker's last activity by hand; do NOT read `status`, which cannot "
        "distinguish 'waiting at a gate' from 'rate-limited hours ago'",
    ),
    "selfSession": (
        set(),
        "this seat's own session id — the address workers ping back on (§4.8 rule 6, §4.9 step 4)",
        "ask the human for this session's id; do NOT skip the re-address, because a failed "
        "re-address produces silence and silence reads as 'no worker needs anything' (FB-0105)",
    ),
}

_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
# Conservative: letters, digits and a small punctuation set. No spaces, no
# quotes, no `;` `|` `&` `$` backtick `<` `>` `(` `)` `*` `?` `~` `!` `#`.
_SAFE_VALUE_RE = re.compile(r"\A[A-Za-z0-9._/@:+=-]+\Z")
# Template-level metacharacters. A consumer's own config is more trusted than a
# runtime value, but a template carrying a shell operator turns one rendered
# command into two, and nothing downstream would report it.
_TEMPLATE_FORBIDDEN = [";", "|", "&", "`", "$(", ">", "<", "\n", "\\"]
# `~` is not a shell operator, so it is not forbidden — but `shlex.quote` single-quotes
# it in the `command` field, so `cli --home ~/x` renders a LITERAL `~/x` the shell will
# not expand. Silently different from what the author wrote, which is the one outcome
# this module refuses to produce, so it is called out at validation rather than left to
# surprise someone.
_TEMPLATE_WARN = ["~"]


def load_backend(config_path="flow.config.json"):
    """Return (backend_dict, warnings). Missing slot ⇒ ({}, [loud warning])."""
    warnings = []
    p = Path(config_path)
    if not p.is_file():
        return {}, [
            f"{PREFIX} ⚠️ {config_path} not found, so no dispatchBackend adapter is configured. "
            f"Every dispatch step below must be done by hand."
        ]
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, [
            f"{PREFIX} ⚠️ {config_path} could not be read or parsed ({exc}); no dispatchBackend "
            f"adapter is available. Every dispatch step below must be done by hand."
        ]
    backend = data.get("dispatchBackend")
    if backend is None:
        return {}, [
            f"{PREFIX} ⚠️ flow.config.json has no `dispatchBackend` slot, so this project has no "
            f"dispatch adapter. The orchestrator workflow still applies — every step that would "
            f"call the backend must be performed by hand, and the skill will tell you which. "
            f"To wire one, add the five verbs (listWorkers, createWorker, sendMessage, "
            f"workerStatus, selfSession) as command templates; see the schema."
        ]
    if not isinstance(backend, dict):
        return {}, [
            f"{PREFIX} ⚠️ flow.config.json.dispatchBackend is present but is not an object (got "
            f"{type(backend).__name__}). Treating it as absent — fix the slot; a malformed adapter "
            f"is NOT the same as no adapter and this project believes it has one."
        ]
    return backend, warnings


def validate(backend):
    """Return a per-verb report. Never raises."""
    # Emitted so consumers (doctor's remediation text, docs) read the vocabulary
    # from the one definition rather than restating it — it was written out in
    # three places, with nothing to catch a miss.
    report = {"verbs": {}, "ok": True, "configured": 0,
              "known_placeholders": sorted(KNOWN_PLACEHOLDERS)}
    for verb, (required, purpose, manual) in VERBS.items():
        tmpl = backend.get(verb)
        entry = {"purpose": purpose, "manual_fallback": manual}
        if tmpl is None:
            entry.update(state="absent", problems=[f"`{verb}` is not configured"])
            report["ok"] = False
        elif not isinstance(tmpl, str) or not tmpl.strip():
            entry.update(state="invalid", problems=[f"`{verb}` must be a non-empty string"])
            report["ok"] = False
        else:
            problems = []
            found = set(_PLACEHOLDER_RE.findall(tmpl))
            unknown = sorted(found - KNOWN_PLACEHOLDERS)
            missing = sorted(required - found)
            if unknown:
                problems.append(
                    f"unknown placeholder(s) {', '.join('{%s}' % u for u in unknown)} — the "
                    f"vocabulary is closed to {', '.join('{%s}' % k for k in sorted(KNOWN_PLACEHOLDERS))}. "
                    f"In particular there is no `{{message}}`: message bodies travel as "
                    f"`{{messageFile}}` and only as a path (field manual T6 / FB-0108)."
                )
            if missing:
                problems.append(
                    f"missing required placeholder(s) {', '.join('{%s}' % m for m in missing)}"
                )
            # Per-verb, not just global. A template naming a placeholder that IS in the
            # vocabulary but is NOT supplied to THIS verb passed validation and then refused
            # at render — byte-identical to the `{branch}` defect, which was closed globally
            # while this half stayed open. `render()` computes `found - values`; `validate`
            # must compute the same thing from the contract, or the two disagree about what
            # a valid template is.
            for warn in _TEMPLATE_WARN:
                if warn in tmpl:
                    problems.append(
                        f"template contains {warn!r}, which is NOT expanded — values are quoted, so "
                        f"it renders literally and the shell will not expand it. Write the full path."
                    )
                    break
            extra = sorted(found - required)
            if extra:
                problems.append(
                    f"placeholder(s) {', '.join('{%s}' % e for e in extra)} are not supplied to "
                    f"`{verb}` — nothing passes them, so this template validates here and then "
                    f"refuses at dispatch. Required for this verb: "
                    f"{', '.join('{%s}' % r for r in sorted(required)) or '(none)'}."
                )
            for bad in _TEMPLATE_FORBIDDEN:
                if bad in tmpl:
                    problems.append(
                        f"template contains {bad!r}, a shell operator — one rendered command would "
                        f"become two, and nothing downstream would report it"
                    )
                    break
            # Parse it the same way `render()` will. An unbalanced quote compiles fine,
            # passes every check above, and then raises an uncaught ValueError at
            # dispatch — the agent gets a traceback instead of the promised loud refusal
            # with a manual fallback, i.e. the "dispatch silently did not happen" outcome.
            # `check` and `render` must agree on what a valid template is, so they run
            # the same parser.
            try:
                shlex.split(tmpl)
            except ValueError as exc:
                problems.append(
                    f"template is not parseable as a command line ({exc}) — most likely an "
                    f"unbalanced quote. It would fail at dispatch, not here."
                )
            entry.update(state="ok" if not problems else "invalid", template=tmpl, problems=problems)
            if problems:
                report["ok"] = False
            else:
                report["configured"] += 1
        report["verbs"][verb] = entry
    return report


def render(backend, verb, values):
    """Return (argv, error). `argv` is None when the command cannot be rendered.

    Split with `shlex`, not `str.split()`. Values are already restricted to a
    charset shlex cannot misparse, but the TEMPLATE is the consumer's prose and may
    legitimately quote a placeholder (`--message-file "{messageFile}"`) — a naive
    split leaves the quotes inside the argument and the backend reports a
    file-not-found on a path that exists. Refusing to remember an escape is this
    module's whole argument; making an ad-hoc quoting decision here would undercut it.
    """
    if verb not in VERBS:
        return None, f"{PREFIX} ⚠️ unknown verb {verb!r}. Known: {', '.join(sorted(VERBS))}."
    required, _purpose, manual = VERBS[verb]
    tmpl = backend.get(verb)
    if not isinstance(tmpl, str) or not tmpl.strip():
        return None, (
            f"{PREFIX} ⚠️ `{verb}` is not configured in flow.config.json.dispatchBackend. "
            f"Do this by hand instead: {manual}. This step was NOT performed."
        )
    for bad in _TEMPLATE_FORBIDDEN:
        if bad in tmpl:
            return None, (
                f"{PREFIX} ⚠️ refusing to render `{verb}`: its template contains {bad!r}, a shell "
                f"operator. Fix the slot; flow will not run a template it cannot bound."
            )
    found = set(_PLACEHOLDER_RE.findall(tmpl))
    unknown = sorted(found - KNOWN_PLACEHOLDERS)
    if unknown:
        return None, (
            f"{PREFIX} ⚠️ refusing to render `{verb}`: unknown placeholder(s) "
            f"{', '.join('{%s}' % u for u in unknown)}. The vocabulary is closed; there is no "
            f"`{{message}}` because message bodies travel as a path, never as an argument."
        )
    missing_required = sorted(required - found)
    if missing_required:
        return None, (
            f"{PREFIX} ⚠️ refusing to render `{verb}`: template is missing required placeholder(s) "
            f"{', '.join('{%s}' % m for m in missing_required)}."
        )
    unsupplied = sorted(found - set(values))
    if unsupplied:
        return None, (
            f"{PREFIX} ⚠️ refusing to render `{verb}`: no value supplied for "
            f"{', '.join('{%s}' % u for u in unsupplied)}."
        )
    for key in sorted(found):
        val = str(values[key])
        if not _SAFE_VALUE_RE.match(val):
            return None, (
                f"{PREFIX} ⚠️ refusing to render `{verb}`: value for {{{key}}} contains characters "
                f"outside the safe set [A-Za-z0-9._/@:+=-] (no spaces, quotes or shell "
                f"metacharacters). Refused rather than escaped — an escape is something an author "
                f"has to remember (field manual T6, which fired four times in one session among "
                f"authors who had just reasoned about it)."
            )
        if val.startswith("-"):
            return None, (
                f"{PREFIX} ⚠️ refusing to render `{verb}`: value for {{{key}}} starts with '-' and "
                f"would be read as a flag by the backend."
            )
    rendered = _PLACEHOLDER_RE.sub(lambda m: str(values[m.group(1)]), tmpl)
    try:
        return shlex.split(rendered), None
    except ValueError as exc:
        # Never a traceback. Every other failure in this module returns the loud refusal
        # plus the named manual fallback, and an unparseable template is not the one
        # place to make the caller guess what happened.
        return None, (
            f"{PREFIX} ⚠️ refusing to render `{verb}`: the template is not parseable as a "
            f"command line ({exc}) — most likely an unbalanced quote in "
            f"flow.config.json.dispatchBackend. Do this by hand instead: {manual}. "
            f"This step was NOT performed."
        )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="dispatch_backend.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="validate the configured adapter (used by /flow:doctor)")
    c.add_argument("--config", default="flow.config.json")

    r = sub.add_parser("render", help="render one verb's command, refusing anything unsafe")
    r.add_argument("verb", choices=sorted(VERBS))
    r.add_argument(
        "--set", action="append", default=[], metavar="KEY=VALUE",
        help="placeholder value, e.g. --set session=abc --set messageFile=.flow/brief.md",
    )
    r.add_argument("--config", default="flow.config.json")

    args = ap.parse_args(argv)
    backend, warnings = load_backend(args.config)
    for w in warnings:
        print(w, file=sys.stderr)

    if args.cmd == "check":
        report = validate(backend)
        report["slot_present"] = bool(backend)
        print(json.dumps(report, indent=2))
        return 0 if report["ok"] else 1

    values = {}
    for pair in args.set:
        if "=" not in pair:
            print(f"{PREFIX} ⚠️ --set expects KEY=VALUE, got {pair!r}.", file=sys.stderr)
            return 2
        k, v = pair.split("=", 1)
        values[k.strip()] = v
    argv_out, err = render(backend, args.verb, values)
    if err:
        print(err, file=sys.stderr)
        print(json.dumps({"argv": None, "rendered": False, "verb": args.verb}, indent=2))
        return 1
    # `shlex.quote` per element, not `" ".join` — the join would drop the quoting shlex
    # just resolved, so a template like `--label "my worker"` would render a `command`
    # that is two shell arguments. Every SKILL.md says "run the rendered command", so this
    # is the field an agent copies. (`shlex.join` is 3.8+; this repo targets 3.7.)
    command = " ".join(shlex.quote(a) for a in argv_out)
    print(json.dumps({"argv": argv_out, "command": command, "rendered": True, "verb": args.verb}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
