#!/usr/bin/env python3
"""
Deterministic engine behind `/flow:prototype` — D1 Phase 2 (FB-0081, FB-0113,
FB-0114; `dev-docs/handoffs/d1-prototype-first-gate.md` § Phase 2).

D1 moves a UI change's FIRST human gate from the plan to a prototype. This file
holds every part of that move that must be mechanical rather than judged:

  arming        Config-only: does Step 2 take the D1 branch at all? Readable
                BEFORE any brief exists, which is the whole reason it is split
                out of `trigger`.
  trigger       Reads the brief's DECLARED `Mode` + `Surface` (plus `role`) and
                resolves the path + the pre-execution gate.
  contract      The prototype artifact's own contract — the § 9.4 feasibility
                read, asserted rather than advisory.
  approve       Gate-1 capture. Refuses without a human quote or a passing
                contract. Untrusted text arrives as a FILE PATH, never argv
                (FB-0108).
  verify        Re-checks a recorded approval against the artifact on disk.
  gate-execute  "A plan always exists" (§ 2.5). Reads COMMITTED state only.
  present       Injects the existing annotation layer. Authors no markup.

THE INVARIANT THE WHOLE FILE EXISTS TO HOLD, stated once:

    Exactly ONE pre-execution human gate, always — prototype approval XOR plan
    approval. Never both (that is the ceremony D1 removes). Never neither (that
    is a gate silently deleted). AND a plan exists before Execute.

`trigger` therefore returns `pre_execution_gate` on every path, including every
degradation, and the eval sweeps the whole fixture matrix asserting exactly one
value per row and that BOTH values occur (the positive half — an assertion that
only forbids is satisfiable by deleting a branch; see `.claude/rules/general.md`
§ Consistency item 3).

Fail direction is always CLASSIC: a malformed brief, an absent brief, or an
unreadable config degrade to the plan gate, never to prototype-first. Classic is
the fail-safe because it is the path where the human still gates. The three keep
DISTINCT reasons — `trigger` runs only after `/flow:prototype` writes the brief,
so an absent one is a failed write, not a normal state, and collapsing them
would train a reader to ignore the warning.

Stdlib only. Python 3.7+. Every subcommand prints one JSON object to stdout and
exits 0 unless the operation itself is a refusal (`approve`), so a caller can
always parse a verdict rather than a traceback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------- config

SCHEMA_VERSION = 1

# The ONE platform value for which the prototype IS the delivery medium, so the
# feasibility read has nothing to say. Everything else — including `platform`
# UNSET, which is the documented default (bundled /run autodetects) — requires
# it. Defining the rule as the complement of this set rather than as a list of
# native platforms is deliberate: an enumeration silently exempts any enum value
# added later, and `platform` unset is the configuration an iOS consumer most
# commonly ships (see the § 9.4 note in the module docstring's handoff ref).
BROWSER_NATIVE_PLATFORM = "web"

# Who may take the one-line browser-delivery exit — an ALLOWLIST, deliberately, and
# this was a denylist (`{"ios","android"}`) until /simplify's altitude pass pointed
# out it was the exact shape argued against eight lines above: an enumeration of
# native platforms silently exempts any enum value added later. `react-native`,
# `flutter`, `macos`, `electron` would each have been able to declare their way out
# of the only guard § 9.4 has — the same hole the complement rule had just closed
# for unset `platform`. Two rules about one question ("is this a proxy?") pointing
# opposite ways.
#
# As an allowlist the default inverts: a platform nobody has thought about yet
# CANNOT self-declare browser delivery, and adding one to the schema is a
# deliberate act here rather than a silent exemption there.
# `web` is deliberately ABSENT: it short-circuits at `required = platform != "web"` before
# this set is consulted, so listing it would be dead code — and would imply web needs the
# one-liner when it needs no feasibility block at all.
BROWSER_DELIVERY_ELIGIBLE = {"library", "none", "cli", "tauri"}

# Closed verdict set for a feasibility row. Open sets rot: a typo'd verdict would
# otherwise read as a considered judgment.
FEASIBILITY_VERDICTS = ("native-standard", "native-custom", "expensive", "infeasible")

# A row whose verdict is anything but `native-standard` must reach the human AT
# gate 1, before approval — a look you cannot afford must not be approved before
# its price is stated.
MUST_SURFACE_VERDICTS = tuple(v for v in FEASIBILITY_VERDICTS if v != "native-standard")

# ONE wording, because the eval greps for the substring `SUPPRESS` and two
# hand-written copies would drift without failing it.
SUPPRESSED_MSG = ("role: designer is SUPPRESSED by uiSurface: false — a project that declares "
                  "no UI surface has nothing to prototype. Recorded, never silently honored "
                  "(same shape and resolution as visual-significance.py's gate 1).")

SURFACE_VALUES = ("visual", "non-visual")
MODE_VALUES = ("feature", "spike", "tiny")

# Committed markers. `gate-execute` reads these and nothing else — see its
# docstring for why the arming signal must survive the workspace.
GATE_DECL_RE = re.compile(r"^\s*\*\*Pre-execution gate:\*\*\s*(?P<gate>[a-z-]+)\s*$", re.M)
# The digest line, parsed rather than merely detected. An earlier version captured
# `body` and threw it away, so the guard asserted only that a line EXISTS — the agent
# writes the line, the agent's guard checks the line is there. It now has to contain a
# sha-shaped token and a non-empty quoted approval, which is the difference between
# "a marker is present" and "the marker carries what it claims to".
DIGEST_RE = re.compile(
    # `[^"\n]`, not `[^"]`: a negated class crosses newlines, so a quote left unclosed by
    # truncation matched ANY later `"` in the plan doc and reported mangled cross-line text
    # as a well-formed digest. The trailing `(?P<tail>.*)$` is not decoration either — the
    # stamp check reads `branch=` out of it, and without it group(0) stopped at the closing
    # quote, so that check silently never fired: a guard that looked present and matched
    # nothing.
    r"^\s*\*\*Prototype approved:\*\*\s*`(?P<sha>[0-9a-f]{8,64})`\s*·\s*"
    r"(?P<quote>\"[^\"\n]*\"|'[^'\n]*')(?P<tail>.*)$",
    re.M,
)

# Brief header: `**Mode:** feature · **Surface:** visual` (either order, either
# on one line or two — the separator is cosmetic, the declarations are not).
MODE_RE = re.compile(r"\*\*Mode:\*\*\s*(?P<v>[A-Za-z-]+)")
SURFACE_RE = re.compile(r"\*\*Surface:\*\*\s*(?P<v>[A-Za-z-]+)")

FEASIBILITY_HEAD_RE = re.compile(r"^\s*\*\*Feasibility\*\*", re.M | re.I)
PROXY_DISCLOSURE_RE = re.compile(r"HTML proxy of an?\s+(?P<plat>[A-Za-z]+)\s+surface", re.I)
# Per-LINE (re.M, no re.S). Under re.S this was `…browser\b.*?prototype is the artifact`
# across the whole file, which is quadratic on a feasibility.md carrying many
# "Delivery medium: browser" lines and no terminator — measured ~14s at 8k repeats.
# A local hang of the agent's own run rather than a privilege crossing, but the
# declaration is a single line by construction, so scanning the whole file bought nothing.
BROWSER_DELIVERY_RE = re.compile(
    r"^.*Delivery medium:\s*browser\b.*prototype is the artifact.*$", re.I | re.M
)

ANNOTATION_LAYER = (
    Path(__file__).resolve().parent.parent.parent / "verify-build" / "lib" / "annotation-layer.html"
)


# --------------------------------------------------------------------------- helpers

def _emit(obj) -> int:
    # Injected here, not repeated at every return: a future path cannot forget it.
    obj.setdefault("schema", SCHEMA_VERSION)
    json.dump(obj, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def _read_config(config_path):
    """Returns (cfg_dict, warnings, state) where state is `ok` | `absent` |
    `malformed`.

    ABSENT and MALFORMED are NOT the same thing and callers must not treat them
    alike. Absent is legitimate — flow ships documented defaults for every slot,
    and a project with no config is supported. Malformed means the file exists
    and cannot be read, so `uiSurface` and `role` are UNKNOWN — and deciding
    where a human gate sits from unknown config is the silent-wrong-config
    failure the jq guards exist to prevent. `trigger` fails CLOSED to the
    classic plan gate on malformed; absent proceeds on documented defaults.
    """
    warnings = []
    if config_path is None:
        config_path = Path("flow.config.json")
    config_path = Path(config_path)
    if not config_path.is_file():
        warnings.append(
            "[WARN] flow.config.json not found at %s — using documented defaults "
            "(uiSurface=true, role unset, platform unset)." % config_path
        )
        return {}, warnings, "absent"
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        # A JSON document that parses but is not an OBJECT (`[]`, `"x"`, `3`) is
        # malformed FOR THIS PURPOSE. Without this guard `_ui_surface` raised
        # AttributeError and the process exited 1 with a traceback and no JSON —
        # violating this module's own docstring promise that every subcommand emits
        # a parseable verdict. `toolchain.py` already carries the isinstance guard;
        # this reader shipped without it.
        if not isinstance(cfg, dict):
            warnings.append(
                "[WARN] config_malformed: flow.config.json at %s is valid JSON but not an "
                "object (%s), so no slot can be read. Failing CLOSED to the classic plan gate."
                % (config_path, type(cfg).__name__)
            )
            return {}, warnings, "malformed"
        return cfg, warnings, "ok"
    except (ValueError, OSError) as exc:
        warnings.append(
            "[WARN] config_malformed: flow.config.json at %s is unreadable (%s), so "
            "uiSurface and role are UNKNOWN. Failing CLOSED to the classic plan gate "
            "rather than moving a human gate on a guess." % (config_path, exc.__class__.__name__)
        )
        return {}, warnings, "malformed"


def _ui_surface(cfg) -> bool:
    # Explicit `false` opts out; anything else (including absent) is true. The
    # `if x is False` form rather than `cfg.get("uiSurface", True)` mirrors
    # FB-0058's jq boolean-slot fix — a falsy-but-not-false value must not invert.
    return cfg.get("uiSurface") is not False


def _role(cfg):
    r = cfg.get("role")
    return r if r in ("designer", "engineer") else None


def _platform(cfg):
    p = cfg.get("platform")
    return p if isinstance(p, str) and p else None


def _flow_scratch():
    """The canonical stamp helpers (FB-0082), imported rather than re-implemented.

    An earlier draft hand-rolled `_git` + `_stamp` here. They were strictly worse
    than what already shipped: three git subprocesses where `current_stamp()`
    deliberately folds two into one `rev-parse --show-toplevel --short HEAD`, and
    a `verify` comparison that checked only `branch` — so the same branch name in a
    *different clone* verified clean, and a symlinked worktree (macOS `/var` →
    `/private/var`) produced a spurious mismatch that `check_stamp()`'s realpath
    normalization already handles. Re-implementing a helper whose own feedback ID
    the copy was citing is the duplication this repo names most often."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "scripts"))
    import flow_scratch
    return flow_scratch


def _stamp(root=None):
    return _flow_scratch().current_stamp(cwd=root)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _safe_path(path: Path, what: str, base: Path) -> Path:
    """Refuse a symlink, and refuse a path that escapes the directory it belongs to.

    CWE-59. `.flow/` is an ordinary repo path with none of git's `.git` special-casing,
    so a branch can COMMIT `.flow/prototypes/<branch>/prototype.presented.html` as a
    symlink to `~/.ssh/authorized_keys` — tracked files are checked out regardless of
    the `.gitignore` this skill writes — and the write lands on the attacker's target.
    `gh pr checkout` here is documented as executing the branch, so the checkout IS the
    attack step. The read side matters as much: a planted `approval-quote.txt ->
    ~/.aws/credentials` splices up to 150 bytes of it into the COMMITTED plan-doc digest.

    Confinement is to `base` — the directory the caller named — NOT to an absolute
    `.flow/`. An earlier draft hardcoded the latter and refused every legitimate run
    outside a repo (including this harness's tempdirs), which is a gate that fails
    closed on its own users: security theatre that costs correctness. Symlink refusal is
    what actually defeats the planted-link attack; `base` confinement is what stops
    `../../..` traversal through the argument.

    `skills/ship/lib/manifest-triage.py` already holds this standard for its producer
    files; this is the same guard, not a new invention.
    """
    if path.is_symlink():
        raise SecurityRefusal("%s is a symlink (%s) — refusing to follow it; a write or read "
                              "through it lands wherever the link points (CWE-59)." % (what, path))
    try:
        resolved = path.resolve()
        resolved.relative_to(base.resolve())
    except ValueError:
        raise SecurityRefusal("%s resolves to %s, outside %s — refusing to read or write "
                              "outside the directory it belongs to." % (what, path.resolve(), base))
    except SecurityRefusal:
        raise
    except Exception:  # noqa: BLE001 - an unresolvable path must not fail OPEN
        raise SecurityRefusal("%s could not be confined to %s — refusing rather than acting on "
                              "an unverified path." % (what, base))
    # A symlinked ancestor inside `base` defeats a file-only check.
    for parent in [resolved] + list(resolved.parents):
        if parent == base.resolve():
            break
        if parent.is_symlink():
            raise SecurityRefusal("%s sits under a symlinked directory (%s) — refusing "
                                  "(CWE-59)." % (what, parent))
    return path


class SecurityRefusal(Exception):
    """A path refused by _safe_path. Surfaced as a clean refusal, never a traceback."""


def _prototype_file(proto_dir: Path):
    p = proto_dir / "prototype.html"
    return p if p.is_file() else None


# --------------------------------------------------------------------------- brief

def _parse_brief(brief_path):
    """Returns (mode, surface, state, warnings).

    `state` is one of `ok` | `absent` | `malformed`, kept DISTINCT rather than
    collapsed into a single failure: `trigger` runs only after the skill writes
    the brief, so `absent` means the write did not happen (an anomaly worth
    naming precisely) while `malformed` means the file exists and is wrong.
    Both route to classic; only the diagnosis differs.
    """
    warnings = []
    if brief_path is None:
        return None, None, "absent", ["[WARN] no --brief given; cannot read a declared Mode/Surface."]
    bp = Path(brief_path)
    if not bp.is_file():
        return None, None, "absent", [
            "[WARN] brief_absent: no brief at %s. /flow:prototype writes the brief "
            "BEFORE trigger runs, so an absent brief here means that write did not "
            "happen — not a normal pre-write state." % bp
        ]
    try:
        text = bp.read_text(encoding="utf-8")
    except OSError as exc:
        return None, None, "malformed", ["[WARN] brief at %s unreadable (%s)." % (bp, exc.__class__.__name__)]

    m = MODE_RE.search(text)
    s = SURFACE_RE.search(text)
    mode = m.group("v").lower() if m else None
    surface = s.group("v").lower() if s else None

    if mode is None and surface is None:
        return None, None, "malformed", [
            "[WARN] brief at %s declares neither **Mode:** nor **Surface:** — the "
            "trigger's two declared inputs. See workflow.md § D1 design-brief template." % bp
        ]
    if mode is not None and mode not in MODE_VALUES:
        warnings.append("[WARN] brief declares Mode: %r, not one of %s — treated as unset." % (mode, list(MODE_VALUES)))
        mode = None
    if surface is not None and surface not in SURFACE_VALUES:
        warnings.append("[WARN] brief declares Surface: %r, not one of %s — treated as unset." % (surface, list(SURFACE_VALUES)))
        surface = None
    return mode, surface, "ok", warnings


# --------------------------------------------------------------------------- arming

def cmd_arming(args) -> int:
    """Config-only. Answers "does Step 2 take the D1 branch at all?" — and must
    be answerable BEFORE a brief exists, which is exactly why it is not folded
    into `trigger`. `trigger` reads the brief; the brief is written on the D1
    branch; so a single combined predicate could never decide whether to take
    that branch without already being on it."""
    cfg, warnings, cfg_state = _read_config(args.config)
    ui = _ui_surface(cfg)
    role = _role(cfg)
    reasons = list(warnings)
    # Same fail-closed direction as `trigger`: an unreadable config means uiSurface
    # is UNKNOWN, and the D1 branch must not be taken on a guess. Reported as
    # not-armed rather than defaulted-armed, so the two subcommands cannot disagree
    # about the same config.
    if cfg_state == "malformed":
        reasons.append("config_malformed — uiSurface unknown; the D1 branch is unavailable "
                       "and Step 2 is the classic plan gate.")
        return _emit({"armed": False, "ui_surface": None, "role": role,
                      "brief_required": False, "config_state": cfg_state, "reasons": reasons})
    if ui:
        reasons.append("uiSurface is not false — the D1 branch is available.")
        if role == "designer":
            reasons.append("role: designer — a brief is expected to declare Surface: visual.")
    else:
        reasons.append(
            "uiSurface: false — project declares NO UI surface, so there is nothing "
            "to prototype. The D1 branch is unavailable; Step 2 is the classic plan gate."
        )
        if role == "designer":
            reasons.append(SUPPRESSED_MSG)
    return _emit({
        "armed": bool(ui),
        "ui_surface": ui,
        "role": role,
        "brief_required": bool(ui),
        "config_state": cfg_state,
        "reasons": reasons,
    })


# --------------------------------------------------------------------------- trigger

def cmd_trigger(args) -> int:
    cfg, warnings, cfg_state = _read_config(args.config)
    ui = _ui_surface(cfg)
    role = _role(cfg)
    mode, surface, brief_state, brief_warnings = _parse_brief(args.brief)
    reasons = list(warnings) + list(brief_warnings)

    def out(path, gate, why):
        reasons.append(why)
        return _emit({
            "path": path,
            "pre_execution_gate": gate,
            "brief_required": True,
            "brief_state": brief_state,
            "mode": mode,
            "surface": surface,
            "role": role,
            "ui_surface": ui,
            "config_state": cfg_state,
            "reasons": reasons,
            })

    # An unreadable config means uiSurface/role are UNKNOWN. Fail closed.
    if cfg_state == "malformed":
        return out("classic", "plan",
                   "config_malformed — uiSurface/role unknown; the classic plan gate stands.")

    # Gate 1 of the predicate: a project that declares NO UI surface is never
    # routed to prototype-first, and `role: designer` does not override it. This
    # binds OUTSIDE the OR below — see the suppression note in cmd_arming.
    if not ui:
        if role == "designer":
            reasons.append(SUPPRESSED_MSG)
        return out("classic", "plan", "uiSurface: false vetoes prototype-first; the plan gate stands.")

    if brief_state != "ok":
        return out("classic", "plan",
                   "brief %s — failing CLOSED to the classic plan gate, where the human still gates."
                   % brief_state)

    # The declared visual signal. `role: designer` implies visual without it.
    visual = (surface == "visual") or (role == "designer" and surface is None)
    if not visual:
        return out("classic", "plan",
                   "no visual signal (Surface: %s, role: %s) — classic plan gate." % (surface, role))

    # Proportionality. An EXCLUSION, not a whitelist: written as `mode in
    # {feature}` the collapsed row below would demand Mode be both `feature` and
    # `tiny`, making D1's only escape hatch unreachable.
    if mode == "tiny":
        return out("collapsed", "plan",
                   "Mode: tiny — the surface does not earn a prototype. Clarify + brief, no "
                   "review passes, no prototype; the pre-execution gate stays at plan approval.")
    if mode == "spike":
        return out("classic", "plan",
                   "Mode: spike — spike carries its own reduced-rigor path and its own ship; "
                   "D1 does not fold into it.")

    return out("prototype-first", "prototype",
               "uiSurface true + visual declared + Mode %s — the human's first gate is the "
               "prototype." % (mode or "feature"))


# --------------------------------------------------------------------------- contract

def _feasibility_rows(text):
    """Every `- <affordance> — <verdict> — <reason>` row under the Feasibility
    heading. Returns (rows, unverdicted); a row is (full line, verdict)."""
    rows, unverdicted = [], []
    m = FEASIBILITY_HEAD_RE.search(text)
    if not m:
        return rows, unverdicted
    body = text[m.end():]
    for line in body.splitlines():
        if re.match(r"^\s*#{1,6}\s+\S", line) or re.match(r"^\s*\*\*[^*]+\*\*\s*$", line):
            break
        if not re.match(r"^\s*[-*+]\s+\S", line):
            continue
        m = re.search(r"\b(%s)\b" % "|".join(FEASIBILITY_VERDICTS), line)
        if m:
            rows.append((line.strip(), m.group(1)))
        else:
            unverdicted.append(line.strip())
    return rows, unverdicted


def cmd_contract(args) -> int:
    return _emit(_contract(Path(args.dir), args.config))


def _contract(proto_dir: Path, config_path):
    """The contract verdict as a dict. Split out so `approve` can call it
    directly rather than re-invoking the CLI through a stdout capture — that
    round-trip coupled a refusal path to `cmd_contract` emitting nothing but
    JSON, so any stray print() would have broken `approve` rather than
    `contract`."""
    args = argparse.Namespace(dir=str(proto_dir), config=config_path)
    cfg, warnings, cfg_state = _read_config(args.config)
    platform = _platform(cfg)
    proto_dir = Path(args.dir)
    reasons = list(warnings)

    proto = _prototype_file(proto_dir)
    if proto is None:
        # `return {...}`, NOT `_emit({...})` — this is the dict-returning half of the
        # function. Returning _emit()'s int made cmd_contract call _emit(int), which
        # printed one JSON doc and THEN raised AttributeError: the "always parseable,
        # never a traceback" promise in this module's docstring, broken by the very
        # refactor that split this function out of the CLI command.
        return {
            "ok": False, "platform": platform, "feasibility_required": None,
            "must_surface": [],
            "reasons": reasons + ["There is no prototype.html in %s yet, so there is nothing "
                                  "to check. Build the prototype first." % proto_dir],
        }

    # The feasibility read lives in a SIBLING document, not inside the HTML.
    # Three reasons, and the third is the load-bearing one:
    #   1. The prototype is a design artifact; the feasibility read is prose
    #      about buildability. Different kinds of thing.
    #   2. An HTML-comment-embedded block is invisible to the human looking at
    #      the rendered page — exactly the reader it exists to warn.
    #   3. Keeping it out of the HTML is what lets `present` stay a pure
    #      injector, which is what keeps this engine from becoming a second
    #      browser-UI emitter outside uiFilePatterns (see cmd_present).
    feas = proto_dir / "feasibility.md"
    text = feas.read_text(encoding="utf-8", errors="replace") if feas.is_file() else ""

    required = platform != BROWSER_NATIVE_PLATFORM
    if not required:
        return {
            "ok": True, "platform": platform, "feasibility_required": False,
            "must_surface": [],
            "reasons": reasons + [
                "platform: web — the prototype IS the delivery medium, so the feasibility "
                "read has nothing to proxy. The single exempt value."
            ],
        }

    has_block = bool(FEASIBILITY_HEAD_RE.search(text))  # text is "" when the file is absent
    rows, unverdicted = _feasibility_rows(text)
    browser_delivery = bool(BROWSER_DELIVERY_RE.search(text))
    proxy_disclosed = bool(PROXY_DISCLOSURE_RE.search(text))
    problems = []

    if platform is None:
        reasons.append(
            "platform UNSET — counted as non-web and failing CLOSED. Remedies, both "
            "one line: set \"platform\" in flow.config.json, or declare the block."
        )

    # Positive and negative asserted TOGETHER. Checking only "no unverdicted row"
    # would pass on a prototype with no block at all — satisfiable by deletion
    # (general.md § Consistency item 3).
    if not has_block:
        problems.append(
            "feasibility read ABSENT (expected a `**Feasibility**` block in %s) and platform "
            "is %s (non-web). Required unless platform == \"web\"." % (feas, platform or "unset")
        )
    else:
        if browser_delivery and platform not in BROWSER_DELIVERY_ELIGIBLE:
            problems.append(
                "the one-line browser-delivery declaration is NOT available to platform %s — "
                "only %s may take it, and anything else is treated as a proxied surface that "
                "cannot declare its way out of the only guard § 9.4 has. Enumerate the "
                "affordances." % (platform or "unset", sorted(BROWSER_DELIVERY_ELIGIBLE))
            )
        elif browser_delivery:
            reasons.append(
                "browser-delivery declared: the prototype is the artifact, not a proxy, so "
                "one line satisfies the block on platform %s." % (platform or "unset")
            )
        else:
            if not rows:
                problems.append("feasibility block present but declares NO affordance rows.")
            if unverdicted:
                problems.append(
                    "%d feasibility row(s) carry no verdict from %s: %s"
                    % (len(unverdicted), list(FEASIBILITY_VERDICTS), unverdicted[:3])
                )
            if not proxy_disclosed:
                problems.append(
                    "no proxy disclosure — a non-web prototype must state that it is an HTML "
                    "proxy of a <platform> surface and that type rendering, motion and system "
                    "chrome will differ."
                )

    must_surface = [r for r, v in rows if v in MUST_SURFACE_VERDICTS]
    return {
        "ok": not problems,
        "platform": platform,
        "feasibility_path": str(feas),
        "feasibility_required": True,
        "browser_delivery_declared": browser_delivery,
        "proxy_disclosed": proxy_disclosed,
        "rows": len(rows),
        "must_surface": must_surface,
        "problems": problems,
        "reasons": reasons,
    }


# --------------------------------------------------------------------------- approve

def cmd_approve(args) -> int:
    """Gate 1 capture.

    THREE refusals, each paired with the positive it protects:
      - no quote / empty quote  ⇒ refuse. The agent cannot approve on the
        human's behalf, and the record's whole evidentiary value is the human's
        own words.
      - contract not ok         ⇒ refuse. That is what makes § 9.4's feasibility
        read ASSERTED rather than advisory: a native prototype with no
        feasibility read cannot reach gate 1 at all.
      - no prototype.html       ⇒ refuse. Nothing to hash.

    The quote arrives ONLY as a file path written by the Write tool. There is
    deliberately no `--quote` string flag: FB-0108's rule is to close the unsafe
    door rather than add a safe one beside it, and this is the first new
    interface since that landed.
    """
    proto_dir = Path(args.dir)
    proto = _prototype_file(proto_dir)
    if proto is None:
        print("REFUSED: no prototype.html in %s — nothing to approve." % proto_dir, file=sys.stderr)
        return 2

    qp = _safe_path(Path(args.quote_file), "--quote-file", Path(args.quote_file).parent)
    if not qp.is_file():
        print("REFUSED: --quote-file %s does not exist. Gate 1 records the human's VERBATIM "
              "approval; an agent may not approve on their behalf." % qp, file=sys.stderr)
        return 2
    quote = qp.read_text(encoding="utf-8").strip()
    if not quote:
        print("REFUSED: --quote-file %s is empty/whitespace-only. An empty quote is not an "
              "approval." % qp, file=sys.stderr)
        return 2

    # Re-run the contract rather than trusting a caller-passed verdict: a gate
    # that accepts "I already checked" is not a gate.
    contract = _contract(proto_dir, args.config)
    if not contract.get("ok"):
        print("REFUSED: the prototype's contract does not pass, so gate 1 is unreachable.\n  %s"
              % "\n  ".join(contract.get("problems") or ["(no detail)"]), file=sys.stderr)
        return 2

    record = {
        "prototype": proto.name,
        "sha256": _sha256(proto),
        "stamp": _stamp(),
        "platform": contract.get("platform"),
        "contract_ok": True,
        "must_surface": contract.get("must_surface", []),
        "approved_by_human_quote": quote,
    }
    out = _safe_path(proto_dir / "approval.json", "the approval record", proto_dir)
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return _emit({
        "ok": True,
        "record": str(out),
        "sha256": record["sha256"],
        "digest_line": render_digest(record),
        "reasons": [
            "Gate 1 recorded. Paste BOTH lines above into the plan doc verbatim — those "
            "committed lines, not this .flow/ record, are what `gate-execute` reads, and it "
            "requires both."
        ],
    })


def render_digest(record) -> str:
    """BOTH lines that go in the PLAN DOC — `.flow/` is gitignored, so these committed
    lines, not approval.json, are the durable half.

    Emits the gate declaration too, not only the approval digest: `gate-execute`
    requires both, and an earlier version printed one while the skill said "the two
    lines approve prints". An agent following that pasted one line and the guard then
    failed with "plan doc declares no prototype gate" — a self-inflicted failure at the
    hand-off. Print what must be pasted; never ask the caller to author half a contract.
    """
    st = record.get("stamp", {})
    # Truncate the RAW text, then serialize — never the other way round. Slicing the
    # json.dumps output dropped the closing quote, breaking DIGEST_RE in BOTH directions:
    # a false RED (no match → a correctly-approved author accused of skipping gate 1) and,
    # with a newline-crossing class, a false GREEN on a later stray quote. Truncation is
    # also VISIBLE — a paragraph-length approval cut mid-word under a heading promising
    # "verbatim" is a quiet lie — and newlines are folded so the digest is one line by
    # construction rather than by hoping nobody pastes a multi-line approval.
    raw = " ".join((record.get("approved_by_human_quote", "") or "").split())
    if len(raw) > 150:
        raw = raw[:149] + "…"
    return ("**Pre-execution gate:** prototype\n"
            "**Prototype approved:** `%s` · %s · repo=%s branch=%s head=%s") % (
        record.get("sha256", "")[:16],
        json.dumps(raw, ensure_ascii=False),
        Path(st.get("repo", "")).name or "?", st.get("branch", "?"), st.get("head", "?"),
    )


# --------------------------------------------------------------------------- verify

def cmd_verify(args) -> int:
    proto_dir = Path(args.dir)
    rec_path = proto_dir / "approval.json"
    problems = []
    if not rec_path.is_file():
        return _emit({"ok": False, "problems": ["no approval.json in %s" % proto_dir]})
    try:
        record = json.loads(rec_path.read_text(encoding="utf-8"))
    except ValueError:
        return _emit({"ok": False, "problems": ["approval.json is malformed JSON"]})

    if not (record.get("approved_by_human_quote") or "").strip():
        problems.append("record carries no human approval quote")

    proto = _prototype_file(proto_dir)
    if proto is None:
        problems.append("prototype.html is gone; the record describes nothing")
    else:
        live = _sha256(proto)
        if live != record.get("sha256"):
            # Kept DISTINCT from the stamp mismatch below — collapsing "edited
            # after approval" into "wrong workspace" would hide which one happened.
            problems.append(
                "sha256 MISMATCH — the prototype changed after approval, so the record no "
                "longer describes what the human saw (recorded %s, on disk %s)"
                % (str(record.get("sha256"))[:12], live[:12])
            )
    # Delegate to flow_scratch.check_stamp rather than comparing fields here: it
    # covers repo/branch/head (not just branch), realpath-normalizes the repo so a
    # symlinked worktree is not a false mismatch, and refuses a non-string field
    # instead of raising. check_stamp expects the stamp under `flow_stamp`.
    ok_stamp, reason = _flow_scratch().check_stamp({"flow_stamp": record.get("stamp") or {}})
    if not ok_stamp:
        problems.append("workspace stamp MISMATCH — %s (FB-0082)" % reason)
    return _emit({"ok": not problems, "problems": problems,
                  "digest_line": render_digest(record), "schema": SCHEMA_VERSION})


# --------------------------------------------------------------------------- gate-execute

def _parse_digest_stamp(tail: str) -> dict:
    """Pull `repo=`/`branch=`/`head=` out of a committed digest line's tail.

    Returns only the keys actually present, so `check_stamp` compares what the digest
    claims and nothing else. A digest written by an older flow that omits a field is a
    weaker stamp, not a mismatch — but a field that IS present and disagrees is refused.
    """
    out = {}
    # `repo` is deliberately NOT compared, and the reason is not cosmetic. This digest
    # is COMMITTED — it travels to every clone of the repository — so an absolute path
    # is the one field guaranteed to differ for a legitimate reader on another machine.
    # Comparing it would refuse every fresh clone and every CI checkout, which is a gate
    # failing closed on its own honest users. (`render_digest` writes only the basename
    # for readability anyway, so it was never comparable to what `current_stamp()`
    # returns.) `branch` and `head` are portable and carry the real claim: this approval
    # was recorded for THIS work.
    for field in ("branch", "head"):
        m = re.search(r"\b%s=(\S+)" % field, tail)
        if m:
            out[field] = m.group(1)
    return out


def _active_region(text: str) -> str:
    """Everything ABOVE the FIRST `Spec-walk` heading — the active PR's header block.

    Bounding at the first heading, not the second, is load-bearing and an earlier draft
    got it wrong. With the boundary at the SECOND heading, a retained PR's digest still
    fell inside the region, because a retained section's `**Prototype approved:**` line
    sits *above its own* Spec-walk: the layout is [active gate] [active Spec-walk]
    [retained gate] [retained digest] [retained Spec-walk], so a second-heading boundary
    swallows the retained digest and the bypass survived the fix. Verified by running the
    attack, which is the only reason it was caught.

    The contract this implies, and the skill states it: **the gate declaration and the
    approval digest go ABOVE the active `Spec-walk` block.** That is where `approve`
    prints them to be pasted and where every other plan header field already lives.
    """
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "verify-build" / "lib"))
        import walk_extract
        rx = walk_extract.heading_re("Spec-walk")
    except Exception:  # noqa: BLE001 - never fail OPEN on an import problem
        return text
    lines = text.splitlines(keepends=True)
    for i, ln in enumerate(lines):
        if rx.match(ln):
            return "".join(lines[:i])
    return text


def cmd_gate_execute(args) -> int:
    """"A plan must ALWAYS exist" (§ 2.5) — pulled forward out of Phase 3,
    because THIS PR is what removes the human plan gate from the D1 path, and a
    PR that creates a hazard ships the guard for it.

    Reads COMMITTED state only — the plan doc's `**Pre-execution gate:**`
    declaration and `**Prototype approved:**` digest — and makes NO trigger
    call. That is the whole fix, and an earlier design missed it: arming on a
    live `trigger` meant arming on the brief, the brief lives in gitignored
    `.flow/`, so wiping the workspace dropped the guard to `ok: true`
    VACUOUSLY — no human plan gate and no plan assertion, which is precisely
    FB-0080's condition. Two opposite worlds rendering identically green is
    general.md § Consistency item 3, committed by the check written to satisfy
    it.

    Three states, all derivable from git alone:
      declaration + digest + active Spec-walk  ⇒ ok
      declaration, missing either              ⇒ RED
      no declaration                           ⇒ classic path, ok, costs nothing
    """
    plan_path = Path(args.plan)
    if not plan_path.is_file():
        return _emit({"ok": False, "gate": None, "problems": ["plan doc not found at %s" % plan_path]})
    full_text = plan_path.read_text(encoding="utf-8")

    # SCOPE THE MARKERS TO THE ACTIVE SECTION. This was the gate bypass: the
    # Spec-walk half was correctly scoped to the FIRST (active) block, while the
    # gate + digest halves used `search()` over the entire document. In this repo's
    # own convention — active PR at the top, merged PRs retained below — the SECOND
    # D1 PR would inherit the FIRST one's `**Prototype approved:**` line and
    # `gate-execute` would return ok:true for work that never passed gate 1. No
    # attacker required; a committed plan doc with a planted pair does it too.
    # The reverse also bit: a retained `**Pre-execution gate:** plan` line above the
    # active section routed to the classic no-op and skipped the plan-exists check
    # entirely, so the guard asserted nothing at all.
    # The MARKERS are read from the active header region; the Spec-walk BLOCK is
    # extracted from the full document, because walk_extract does its own
    # first-block scoping and needs the heading the region deliberately excludes.
    header = _active_region(full_text)

    m = GATE_DECL_RE.search(header)
    gate = m.group("gate") if m else None
    digest_m = DIGEST_RE.search(header)
    has_digest = digest_m is not None

    # An UNRECOGNIZED gate literal is RED, not "classic, nothing to assert". The old
    # `!= "prototype"` fell open on anything else — including `prototype-first`, which is
    # this engine's own `path` value and travels beside `pre_execution_gate` in the agent's
    # context, so a one-word slip silently disarmed the guard holding the "never neither"
    # half of the invariant. Green in two opposite worlds is the clause-3 shape, committed
    # here by the check written to enforce it.
    if gate is not None and gate not in ("prototype", "plan"):
        return _emit({
            "ok": False, "gate": gate, "has_digest": has_digest, "spec_walk_items": None,
            "problems": ["The plan declares an unrecognized pre-execution gate, %r. It must be "
                         "exactly `prototype` or `plan` — note `prototype-first` is the PATH "
                         "name, not the gate name." % gate],
        })
    if gate != "prototype":
        return _emit({
            "ok": True, "gate": gate, "has_digest": has_digest,
            "spec_walk_items": None, "problems": [],             "reasons": ["plan doc declares no prototype gate — classic path, nothing to assert."],
        })

    problems = []
    if not has_digest:
        problems.append(
            "plan declares `Pre-execution gate: prototype` but carries no WELL-FORMED "
            "`**Prototype approved:**` digest (expected a `<sha>` token and a quoted verbatim "
            "approval). Either gate 1 never happened, its record was lost with the workspace, "
            "or the line was hand-written — all three mean no human approval is evidenced here."
        )
    elif not (digest_m.group("quote") or "").strip("\"'").strip():
        # `.strip()` after the quote-chars: `· "   "` is an empty approval wearing
        # three spaces, and the un-stripped form passed this arm.
        problems.append(
            "the `**Prototype approved:**` digest carries an EMPTY approval quote — a marker "
            "shaped like an approval with nothing in it."
        )
    else:
        # A stamp that is rendered but never checked is decoration (FB-0082). DELEGATED to
        # flow_scratch.check_stamp — the same helper `verify` uses — rather than compared
        # here.
        #
        # The hand-rolled version this replaces was the bug CI caught. It read
        # `if got_branch and want["branch"] and they differ`, which SHORT-CIRCUITS when the
        # local branch is unknown — and `git branch --show-current` returns empty in a
        # detached HEAD, which is how CI checks out. So the gate FAILED OPEN in CI and
        # closed locally: the worst possible split, and the failure direction was "approve
        # work that was never approved". Meanwhile `verify`, using check_stamp, failed
        # CLOSED on the identical unknown. Two handlers for one missing fact, disagreeing.
        # One handler removes the disagreement by construction.
        fs = _flow_scratch()
        here = fs.current_stamp(cwd=str(plan_path.resolve().parent))
        # `repo` is pinned to the local value so only branch/head are actually asserted —
        # see _parse_digest_stamp for why a committed absolute path must never be compared.
        # Passing `expect` explicitly (rather than letting check_stamp resolve it) keeps
        # the comparison set visible at the call site instead of implied by the helper.
        parsed = {"repo": here.get("repo", ""), **_parse_digest_stamp(digest_m.group("tail") or "")}
        ok_stamp, reason = fs.check_stamp({"flow_stamp": parsed}, expect=here)
        if not ok_stamp:
            problems.append(
                "the approval digest does not belong to this workspace — %s. An approval "
                "recorded elsewhere is not an approval for this work; re-approve here rather "
                "than inheriting a digest." % reason
            )

    items = None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "verify-build" / "lib"))
        import walk_extract  # the SAME parser four other consumers use, not a private copy
        # Bare label, NOT the bold form: walk_extract.heading_re() adds the `**…:**`
        # wrapper itself, so passing "**Spec-walk:**" matches nothing and silently
        # reports zero criteria — which would fail this guard CLOSED on a plan that
        # does have a Spec-walk. Same argument the four sibling consumers pass.
        block = walk_extract.extract_block(full_text, "Spec-walk")
        items = len(block.get("items") or [])
        if block.get("all_demoted"):
            problems.append(
                "every Spec-walk block is DEMOTED (all belong to merged PRs) — there is no "
                "active plan, only history (the v1.30.0 all_demoted lifecycle bug, in a fifth consumer)."
            )
        elif items == 0:
            problems.append("plan doc resolves NO active Spec-walk block — no plan exists to Execute against.")
    except Exception as exc:  # noqa: BLE001 - a broken import must not fail OPEN
        problems.append("could not resolve the Spec-walk block via walk_extract (%s) — failing "
                        "CLOSED rather than assuming a plan exists." % exc.__class__.__name__)

    return _emit({"ok": not problems, "gate": gate, "has_digest": has_digest,
                  "spec_walk_items": items, "problems": problems, "schema": SCHEMA_VERSION})


# --------------------------------------------------------------------------- present

def cmd_present(args) -> int:
    """Injects the EXISTING annotation layer before </body> and authors nothing
    of its own.

    The obvious design was to render flow-authored chrome into the page (a
    feasibility banner, a "what approval means" footer). That would make this
    file a SECOND browser-UI emitter alongside render-report.py — which sits
    inside flow.config.json.uiFilePatterns precisely because it emits browser UI
    — and shipping it outside that pattern would permanently exclude the new
    emitter from flow's own visual and a11y gates. So every piece of gate-1
    chrome goes in the CHAT hand-off instead, and the byte-diff eval pins that
    the output is input + the partial and nothing else.
    """
    proto = Path(args.file)
    if not proto.is_file():
        print("no prototype at %s" % proto, file=sys.stderr)
        return 2
    # Write a SEPARATE presented file; never mutate the source. Injecting in place
    # made the recorded sha cover "prototype + injected layer", and made a second
    # present (after an iteration round) indistinguishable from a post-approval edit
    # at `verify` — the string-sniff dedupe guard was a bandaid for that coupling.
    # Source stays the thing approved; presentation is idempotent by construction.
    presented = _safe_path(proto.with_suffix(".presented.html"), "the presented file", proto.parent)
    html = proto.read_text(encoding="utf-8")
    warnings = []
    try:
        layer = ANNOTATION_LAYER.read_text(encoding="utf-8")
    except (OSError, ValueError):  # ValueError = non-UTF-8 / corrupt partial
        # Still write the presented file, so the caller always has ONE path to hand over.
        # Returning ok:true with no `presented` key told the agent to "give the human the
        # presented path" when no such file existed.
        presented.write_text(html, encoding="utf-8")
        return _emit({
            "ok": True, "injected": False, "presented": str(presented),
            "open_this": "Open %s — it is READ-ONLY: the comment layer could not be loaded, so "
                         "ask for feedback in chat rather than on the page." % presented.name,
            "reasons": ["[WARN] The comment overlay could not be read from %s, so the page is "
                        "view-only. The human can still look; they just cannot pin comments."
                        % ANNOTATION_LAYER],
        })
    idx = html.rfind("</body>")
    out = (html[:idx] + layer + html[idx:]) if idx != -1 else (html + layer)
    if idx == -1:
        warnings.append("[WARN] no </body> found — layer appended at end of file.")
    presented.write_text(out, encoding="utf-8")
    return _emit({"ok": True, "injected": True, "bytes_added": len(out) - len(html),
                  "presented": str(presented), "source": str(ANNOTATION_LAYER),
                  # The hash of what was PRESENTED, so the digest `approve` later records
                  # is eyeballable against it. `verify` catches edits AFTER approval;
                  # nothing caught staleness BEFORE it — across iteration rounds a human
                  # may still have round 3's tab open and approve a look the source has
                  # moved past.
                  "source_sha256": _sha256(proto),
                  "reasons": warnings,
                  "open_this": "Open %s — the source %s stays unmodified, and is what "
                               "`approve` hashes." % (presented.name, proto.name)})


# --------------------------------------------------------------------------- cli

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1] if __doc__ else "")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("arming", help="config-only: is the D1 branch available?")
    a.add_argument("--config")
    a.set_defaults(fn=cmd_arming)

    t = sub.add_parser("trigger", help="resolve path + pre-execution gate from the BRIEF")
    t.add_argument("--brief")
    t.add_argument("--config")
    t.set_defaults(fn=cmd_trigger)

    c = sub.add_parser("contract", help="the prototype artifact's § 9.4 contract")
    c.add_argument("--dir", required=True)
    c.add_argument("--config")
    c.set_defaults(fn=cmd_contract)

    ap_ = sub.add_parser("approve", help="record gate 1 (requires a human quote FILE)")
    ap_.add_argument("--dir", required=True)
    # NOTE: there is deliberately NO `--quote` string flag. See cmd_approve.
    ap_.add_argument("--quote-file", required=True)
    ap_.add_argument("--config")
    ap_.set_defaults(fn=cmd_approve)

    v = sub.add_parser("verify", help="re-check a recorded approval against disk")
    v.add_argument("--dir", required=True)
    v.set_defaults(fn=cmd_verify)

    g = sub.add_parser("gate-execute", help="a plan must exist before Execute (committed state only)")
    g.add_argument("--plan", required=True)
    g.set_defaults(fn=cmd_gate_execute)

    pr = sub.add_parser("present", help="inject the existing annotation layer; author nothing")
    pr.add_argument("--file", required=True)
    pr.set_defaults(fn=cmd_present)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except SecurityRefusal as exc:
        # A refusal is an outcome, not a crash: print it plainly and exit non-zero.
        print("REFUSED: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
