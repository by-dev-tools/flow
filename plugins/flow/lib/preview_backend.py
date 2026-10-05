#!/usr/bin/env python3
"""`previewBackend` — the host adapter that puts an ephemeral HTML artifact at a URL.

Flow produces two artifacts a human is asked to LOOK at and cannot reach: the gate-1
prototype and the merge-gate walkthrough. PR A made the hand-off honest about that.
This slot makes it optionally reachable, without naming any vendor's CLI anywhere in
a plugin artifact — the project supplies the mechanics, exactly as `dispatchBackend`
and `typecheckCmd`/`preflightCmd` already do.

Three verbs, and the placeholder vocabulary is **closed**:

    serve      {dir} {port}   start something listening on {port} serving {dir}
    publish    {port}         share {port}; print a URL on stdout
    unpublish  (none)         stop sharing

There is deliberately **no `{url}`**: the URL is this adapter's OUTPUT, parsed from
`publish`'s stdout, never a value a template interpolates. A template that could
compose the URL would let a config decide what the hand-off claims, which is the one
thing the hand-off must not let it do.

THE CONSTRAINT THAT SHAPES THE CALLERS, from the host CLI's own help and not from any
assumption: a workspace has **one** preview URL, and pointing it at a different port
keeps the same URL. So two artifacts cannot hold two live links. Callers serve ONE
directory containing both and hand out `<url>/<file>`; re-pointing to a second port
would silently break the first link while leaving it looking valid — the exact defect
`artifact-handoff.py` exists to remove.

DEGRADATION IS THE NORMAL CASE, NOT AN ERROR PATH. The slot is unset by default, so
every consumer that has not configured it keeps PR A's behaviour byte-identical. And
a configured adapter can still fail — the thing on the port can die, the CLI can be
unauthenticated — so every failure returns a stated reason and the caller falls back
to the honest local line. A URL is never emitted on a guess.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import socket
import subprocess
import sys
import urllib.parse
from pathlib import Path

# ONE definition of the refusal policy — the policy's APPLICATION (`render_template`,
# public) as well as its data. The first cut here re-derived the control flow and had
# already diverged in one direction: its `validate` flagged an unexpanded `~/` that
# its `render` passed through. Two copies of a refusal policy is the fan-out class
# this repo keeps paying for (.claude/rules/general.md Consistency item 2), so the
# shared function lives in `dispatch_backend` and both adapters call it. Only the two
# remaining privates are policy DATA this module also needs for its own `validate`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dispatch_backend import (  # noqa: E402  (sibling-module import, house pattern)
    _PLACEHOLDER_RE,
    _TEMPLATE_FORBIDDEN,
    _TEMPLATE_REJECT_UNEXPANDED,
    render_template,
)

PREFIX = "[preview-backend]"

KNOWN_PLACEHOLDERS = {"dir", "port"}

# Verb → (required placeholders, what it is for, what to do by hand if absent).
VERBS = {
    "serve": (
        {"dir", "port"},
        "start something listening on {port} that serves {dir} (the host's own command, "
        "typically a background static server)",
        "serve the directory yourself and set the preview by hand, or accept the local "
        "path hand-off — which is correct and honest, just less convenient",
    ),
    "publish": (
        {"port"},
        "share {port} at the workspace's preview URL and print that URL on stdout",
        "publish the port by hand and paste the URL, or accept the local path hand-off",
    ),
    "unpublish": (
        set(),
        "stop sharing the preview URL. DELIBERATELY UNCALLED by any shipped skill: the decision was publish-and-leave, because a ship is often followed by a human reading the page minutes later and a link dying mid-read is the worse failure. It exists so an operator (or a future teardown step) has one verb to call rather than a vendor command to remember",
        "stop the share by hand when you are done reviewing",
    ),
}

# Only `serve` and `publish` are needed for the feature to work. `unpublish` is a
# teardown nobody is blocked on, so its absence is a note, not a failure — stated
# here because "required" is otherwise read as "all three".
ESSENTIAL = {"serve", "publish"}

# A URL is accepted only in this shape. `https` ONLY, deliberately: the page is
# sign-in-gated, so handing a human an `http://` URL for it would downgrade the
# transport carrying that session. A project whose host prints `http://` gets a
# stated refusal rather than a quiet downgrade.
_URL_RE = re.compile(r"(?<![A-Za-z0-9.+-])https://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+")
_HTTP_ONLY_RE = re.compile(r"(?<![A-Za-z0-9.+-])http://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+")


def load_backend(config_path="flow.config.json"):
    """Return (backend_dict, warnings). Missing slot ⇒ ({}, [note]).

    An absent slot is NOT a warning in the scary sense — it is the documented
    default, and the caller's behaviour is correct without it. The note says so, so
    nobody reads "no preview adapter" as a broken install.
    """
    p = Path(config_path)
    if not p.is_file():
        return {}, [
            f"{PREFIX} {config_path} not found, so no preview adapter is configured. "
            f"The hand-off will name the local file and say where it can be opened — "
            f"which is correct, just not reachable from another device."
        ]
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, [
            f"{PREFIX} ⚠️ {config_path} could not be read or parsed ({exc}); no preview "
            f"adapter is available. Falling back to the local-path hand-off."
        ]
    backend = data.get("previewBackend")
    if backend is None:
        return {}, [
            f"{PREFIX} no `previewBackend` slot, so this project serves nothing. The "
            f"hand-off names the local file and says where it can be opened. To wire one, "
            f"add `serve` and `publish` command templates; see the schema."
        ]
    if not isinstance(backend, dict):
        return {}, [
            f"{PREFIX} ⚠️ flow.config.json.previewBackend is present but is not an object "
            f"(got {type(backend).__name__}). Treating it as absent — fix the slot; a "
            f"malformed adapter is NOT the same as no adapter, and this project believes "
            f"it has one."
        ]
    return backend, []


def validate(backend):
    """Per-verb report. Never raises.

    Every template problem is computed by actually calling `render()` with dummy
    values, NOT by a second hand-written copy of the checks. That is the shape
    `dispatch_backend.validate` arrived at after three defects of one kind — "passes
    `check`, refuses at dispatch" — and it is the only version that cannot drift,
    because the thing being validated is the thing that will run. `/flow:doctor`
    Check 2.13's whole purpose is catching an adapter that would fail invisibly, so a
    green report over a template that cannot render would defeat it entirely.
    """
    report = {"verbs": {}, "usable": False, "configured": 0,
              "known_placeholders": sorted(KNOWN_PLACEHOLDERS)}
    for verb, (required, purpose, manual) in VERBS.items():
        tmpl = backend.get(verb)
        entry = {"purpose": purpose, "manual_fallback": manual,
                 "essential": verb in ESSENTIAL}
        if tmpl is None:
            entry.update(state="absent", problems=[f"`{verb}` is not configured"])
        elif not isinstance(tmpl, str) or not tmpl.strip():
            entry.update(state="invalid",
                         problems=[f"`{verb}` must be a non-empty string"])
        else:
            # Dummy values for exactly the placeholders the template uses, so the
            # only failures reported are the template's own.
            found = set(_PLACEHOLDER_RE.findall(tmpl))
            dummies = {k: "x" for k in (found | required) & KNOWN_PLACEHOLDERS}
            _argv, err = render(backend, verb, dummies)
            problems = []
            if err:
                # Strip the whole known prefix, not a hand-rolled slice. The first cut
                # split on "refusing to render" and lstripped punctuation, which left
                # a stray backtick and the verb name glued to the problem ("serve`:
                # template is missing...") in a WARN a human reads at setup.
                problems.append(
                    re.sub(r"^.*?refusing to render `%s`:\s*" % re.escape(verb), "", err))
            # The one class render() cannot see, because a value IS supplied for it:
            # a placeholder in the vocabulary that this verb is never given. It
            # validates clean and then refuses at the call site.
            extra = sorted(found - required)
            if extra:
                problems.append(
                    f"uses {', '.join('{%s}' % e for e in extra)}, which `{verb}` is "
                    f"never supplied — it would validate here and refuse at the call "
                    f"site. Required for `{verb}`: "
                    f"{', '.join('{%s}' % r for r in sorted(required)) or '(none)'}."
                )
            entry.update(state="ok" if not problems else "invalid", problems=problems)
            if not problems:
                report["configured"] += 1
        report["verbs"][verb] = entry
    # `usable` is the ONLY verdict any caller reads (doctor Check 2.13, the eval
    # harness, and `main`'s exit code). A second near-synonymous `ok` was carried
    # over from dispatch and read by nothing here, so it is gone rather than left for
    # a future reader to adjudicate between two booleans.
    report["usable"] = all(report["verbs"][v]["state"] == "ok" for v in ESSENTIAL)
    return report


def render(backend, verb, values):
    """Return (argv, error). The refusal policy is `dispatch_backend.render_template`."""
    if verb not in VERBS:
        return None, f"{PREFIX} ⚠️ unknown verb {verb!r}. Known: {', '.join(sorted(VERBS))}."
    required, _purpose, manual = VERBS[verb]
    return render_template(
        backend.get(verb), verb, required, KNOWN_PLACEHOLDERS, values, PREFIX, manual,
        "previewBackend",
        shell_operator_hint=(" If your host needs a background process, put the backgrounding "
                       "inside a script the template CALLS, not in the template."))


def extract_url(stdout: str):
    """Pull exactly one https URL out of a host command's stdout, or refuse.

    The host's output format is not flow's to specify, so this reads it tolerantly —
    but it never GUESSES. Zero URLs, or more than one distinct URL, is a refusal with
    a stated reason, because a hand-off that names the wrong URL is worse than one
    that names a local path.
    """
    text = stdout or ""
    urls, rejected = [], []
    for u in _URL_RE.findall(text):
        u = u.rstrip(".,;)]}'\"")
        try:
            parsed = urllib.parse.urlsplit(u)
        except ValueError:
            continue
        # Userinfo makes a URL read as one host and navigate to another, which is the
        # one thing a link handed to a human must not do. Refuse, never sanitize.
        if "@" in parsed.netloc or not parsed.hostname:
            rejected.append(u)
            continue
        if u not in urls:
            urls.append(u)
    if len(urls) == 1:
        return urls[0], None
    if not urls and rejected:
        return None, (
            f"{PREFIX} ⚠️ `publish` printed a URL flow refuses to hand over "
            f"({rejected[0]!r}): it carries userinfo before the host, so it reads as one "
            f"destination and navigates to another. No URL emitted; the hand-off names "
            f"the local file."
        )
    if not urls:
        if _HTTP_ONLY_RE.search(text):
            return None, (
                f"{PREFIX} ⚠️ `publish` printed an `http://` URL, not `https://`. Refusing "
                f"it deliberately: the page is sign-in-gated, so an unencrypted URL would "
                f"downgrade the transport carrying that session. No URL emitted; the "
                f"hand-off names the local file instead."
            )
        return None, (
            f"{PREFIX} `publish` printed no https URL, so there is nothing to hand over. "
            f"The hand-off names the local file and says where it can be opened."
        )
    return None, (
        f"{PREFIX} ⚠️ `publish` printed {len(urls)} distinct URLs "
        f"({', '.join(urls[:3])}{'…' if len(urls) > 3 else ''}) and flow will not guess "
        f"which one a human should open. No URL emitted."
    )


def port_is_listening(port, host="127.0.0.1", timeout=1.0) -> bool:
    """Is anything accepting connections on `port`?

    The host CLI's own help says "something must be listening on the port inside the
    workspace", so publishing a dead port produces a URL that 404s or hangs — a
    live-looking dead link, which is the failure this whole workstream exists to
    remove. Checked before `publish`, never after.
    """
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except (OSError, ValueError, OverflowError):
        return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="preview_backend.py")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check", help="validate the configured adapter")
    c.add_argument("--config", default="flow.config.json")
    r = sub.add_parser("render", help="render one verb's argv")
    r.add_argument("verb", choices=sorted(VERBS))
    r.add_argument("--config", default="flow.config.json")
    r.add_argument("--dir")
    r.add_argument("--port")
    e = sub.add_parser("extract-url", help="read one https URL from stdin")
    e.add_argument("--stdin", action="store_true")
    l = sub.add_parser("listening", help="is anything on this port?")
    l.add_argument("--port", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "check":
        backend, warns = load_backend(a.config)
        rep = validate(backend)
        rep["warnings"] = warns
        print(json.dumps(rep, indent=2, sort_keys=True))
        return 0 if rep["usable"] else 1
    if a.cmd == "render":
        backend, warns = load_backend(a.config)
        for w in warns:
            sys.stderr.write(w + "\n")
        values = {k: v for k, v in (("dir", a.dir), ("port", a.port)) if v is not None}
        argvv, err = render(backend, a.verb, values)
        if err:
            sys.stderr.write(err + "\n")
            return 1
        print(shlex.join(argvv) if hasattr(shlex, "join") else " ".join(argvv))
        return 0
    if a.cmd == "extract-url":
        url, err = extract_url(sys.stdin.read())
        if err:
            sys.stderr.write(err + "\n")
            return 1
        print(url)
        return 0
    if a.cmd == "listening":
        ok = port_is_listening(a.port)
        print("listening" if ok else "not-listening")
        return 0 if ok else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
