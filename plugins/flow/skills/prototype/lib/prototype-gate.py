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

# Platforms that may NOT take the one-line browser-delivery exit below. These are
# unambiguously proxied surfaces; letting an author declare their way out of the
# only guard § 9.4 has would defeat it.
ALWAYS_PROXY_PLATFORMS = {"ios", "android"}

# Closed verdict set for a feasibility row. Open sets rot: a typo'd verdict would
# otherwise read as a considered judgment.
FEASIBILITY_VERDICTS = ("native-standard", "native-custom", "expensive", "infeasible")

# A row whose verdict is anything but `native-standard` must reach the human AT
# gate 1, before approval — a look you cannot afford must not be approved before
# its price is stated.
MUST_SURFACE_VERDICTS = tuple(v for v in FEASIBILITY_VERDICTS if v != "native-standard")

SURFACE_VALUES = ("visual", "non-visual")
MODE_VALUES = ("feature", "spike", "tiny")

# Committed markers. `gate-execute` reads these and nothing else — see its
# docstring for why the arming signal must survive the workspace.
GATE_DECL_RE = re.compile(r"^\s*\*\*Pre-execution gate:\*\*\s*(?P<gate>[a-z-]+)\s*$", re.M)
DIGEST_RE = re.compile(r"^\s*\*\*Prototype approved:\*\*\s*(?P<body>.+)$", re.M)

# Brief header: `**Mode:** feature · **Surface:** visual` (either order, either
# on one line or two — the separator is cosmetic, the declarations are not).
MODE_RE = re.compile(r"\*\*Mode:\*\*\s*(?P<v>[A-Za-z-]+)")
SURFACE_RE = re.compile(r"\*\*Surface:\*\*\s*(?P<v>[A-Za-z-]+)")

FEASIBILITY_HEAD_RE = re.compile(r"^\s*\*\*Feasibility\*\*", re.M | re.I)
PROXY_DISCLOSURE_RE = re.compile(r"HTML proxy of an?\s+(?P<plat>[A-Za-z]+)\s+surface", re.I)
BROWSER_DELIVERY_RE = re.compile(
    r"Delivery medium:\s*browser\b.*?prototype is the artifact", re.I | re.S
)

ANNOTATION_LAYER = (
    Path(__file__).resolve().parent.parent.parent / "verify-build" / "lib" / "annotation-layer.html"
)


# --------------------------------------------------------------------------- helpers

def _emit(obj) -> int:
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
        return json.loads(config_path.read_text(encoding="utf-8")), warnings, "ok"
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
    return False if cfg.get("uiSurface") is False else True


def _role(cfg):
    r = cfg.get("role")
    return r if r in ("designer", "engineer") else None


def _platform(cfg):
    p = cfg.get("platform")
    return p if isinstance(p, str) and p else None


def _git(*args, cwd=None):
    try:
        out = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=10
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _stamp(root=None):
    return {
        "repo": _git("rev-parse", "--show-toplevel", cwd=root) or "",
        "branch": _git("branch", "--show-current", cwd=root) or "",
        "head": _git("rev-parse", "--short", "HEAD", cwd=root) or "",
    }


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


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
            reasons.append(
                "role: designer is SUPPRESSED by uiSurface: false — recorded, never "
                "silently honored (same shape and resolution as visual-significance.py's gate 1)."
            )
    return _emit({
        "armed": bool(ui),
        "ui_surface": ui,
        "role": role,
        "brief_required": bool(ui),
        "reasons": reasons,
        "schema": SCHEMA_VERSION,
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
            "schema": SCHEMA_VERSION,
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
            reasons.append(
                "role: designer SUPPRESSED by uiSurface: false — recorded, not silently dropped."
            )
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
    """Every `- <name> — <verdict> — <reason>` row under the Feasibility heading.
    Returns (rows, unverdicted) where a row is (name, verdict)."""
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
        found = [v for v in FEASIBILITY_VERDICTS if re.search(r"\b%s\b" % re.escape(v), line)]
        if found:
            # Longest match wins so `native-custom` is not read as `native-standard`.
            rows.append((line.strip(), sorted(found, key=len)[-1]))
        else:
            unverdicted.append(line.strip())
    return rows, unverdicted


def cmd_contract(args) -> int:
    cfg, warnings, cfg_state = _read_config(args.config)
    platform = _platform(cfg)
    proto_dir = Path(args.dir)
    reasons = list(warnings)

    proto = _prototype_file(proto_dir)
    if proto is None:
        return _emit({
            "ok": False, "platform": platform, "feasibility_required": None,
            "must_surface": [], "schema": SCHEMA_VERSION,
            "reasons": reasons + ["no prototype.html in %s — nothing to contract-check." % proto_dir],
        })

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
        return _emit({
            "ok": True, "platform": platform, "feasibility_required": False,
            "must_surface": [], "schema": SCHEMA_VERSION,
            "reasons": reasons + [
                "platform: web — the prototype IS the delivery medium, so the feasibility "
                "read has nothing to proxy. The single exempt value."
            ],
        })

    has_block = feas.is_file() and bool(FEASIBILITY_HEAD_RE.search(text))
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
        if browser_delivery and platform in ALWAYS_PROXY_PLATFORMS:  # noqa: SIM114
            problems.append(
                "the one-line browser-delivery declaration is NOT available to platform %s — "
                "an unambiguously proxied surface cannot declare its way out of the only "
                "guard § 9.4 has. Enumerate the affordances." % platform
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
    return _emit({
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
        "schema": SCHEMA_VERSION,
    })


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

    qp = Path(args.quote_file)
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
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        cmd_contract(argparse.Namespace(dir=str(proto_dir), config=args.config))
    contract = json.loads(buf.getvalue())
    if not contract.get("ok"):
        print("REFUSED: the prototype's contract does not pass, so gate 1 is unreachable.\n  %s"
              % "\n  ".join(contract.get("problems") or ["(no detail)"]), file=sys.stderr)
        return 2

    record = {
        "schema": SCHEMA_VERSION,
        "prototype": proto.name,
        "sha256": _sha256(proto),
        "stamp": _stamp(),
        "platform": contract.get("platform"),
        "contract_ok": True,
        "must_surface": contract.get("must_surface", []),
        "approved_by_human_quote": quote,
    }
    out = proto_dir / "approval.json"
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return _emit({
        "ok": True,
        "record": str(out),
        "sha256": record["sha256"],
        "digest_line": render_digest(record),
        "reasons": [
            "Gate 1 recorded. Add the digest line above to the plan doc — that committed "
            "line, not this .flow/ record, is what `gate-execute` reads (see its docstring)."
        ],
        "schema": SCHEMA_VERSION,
    })


def render_digest(record) -> str:
    """The line that goes in the PLAN DOC. `.flow/` is gitignored, so this
    committed digest — not approval.json — is the durable half."""
    st = record.get("stamp", {})
    return "**Prototype approved:** `%s` · %s · repo=%s branch=%s head=%s" % (
        record.get("sha256", "")[:16],
        json.dumps(record.get("approved_by_human_quote", ""), ensure_ascii=False)[:160],
        Path(st.get("repo", "")).name or "?", st.get("branch", "?"), st.get("head", "?"),
    )


# --------------------------------------------------------------------------- verify

def cmd_verify(args) -> int:
    proto_dir = Path(args.dir)
    rec_path = proto_dir / "approval.json"
    problems = []
    if not rec_path.is_file():
        return _emit({"ok": False, "schema": SCHEMA_VERSION,
                      "problems": ["no approval.json in %s" % proto_dir]})
    try:
        record = json.loads(rec_path.read_text(encoding="utf-8"))
    except ValueError:
        return _emit({"ok": False, "schema": SCHEMA_VERSION,
                      "problems": ["approval.json is malformed JSON"]})

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
    now = _stamp()
    was = record.get("stamp") or {}
    if was.get("branch") and now.get("branch") and was["branch"] != now["branch"]:
        problems.append("stamp branch MISMATCH — recorded on %r, now on %r (FB-0082)"
                        % (was["branch"], now["branch"]))
    return _emit({"ok": not problems, "problems": problems,
                  "digest_line": render_digest(record), "schema": SCHEMA_VERSION})


# --------------------------------------------------------------------------- gate-execute

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
        return _emit({"ok": False, "gate": None, "schema": SCHEMA_VERSION,
                      "problems": ["plan doc not found at %s" % plan_path]})
    text = plan_path.read_text(encoding="utf-8")

    m = GATE_DECL_RE.search(text)
    gate = m.group("gate") if m else None
    if gate != "prototype":
        return _emit({
            "ok": True, "gate": gate, "has_digest": bool(DIGEST_RE.search(text)),
            "spec_walk_items": None, "problems": [], "schema": SCHEMA_VERSION,
            "reasons": ["plan doc declares no prototype gate — classic path, nothing to assert."],
        })

    problems = []
    if not DIGEST_RE.search(text):
        problems.append(
            "plan declares `Pre-execution gate: prototype` but carries NO `**Prototype "
            "approved:**` digest. Either gate 1 never happened, or its record was lost with "
            "the workspace — both mean no human has approved anything on this branch."
        )

    items = None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "verify-build" / "lib"))
        import walk_extract  # the SAME parser four other consumers use, not a private copy
        # Bare label, NOT the bold form: walk_extract.heading_re() adds the `**…:**`
        # wrapper itself, so passing "**Spec-walk:**" matches nothing and silently
        # reports zero criteria — which would fail this guard CLOSED on a plan that
        # does have a Spec-walk. Same argument the four sibling consumers pass.
        block = walk_extract.extract_block(text, "Spec-walk")
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

    return _emit({"ok": not problems, "gate": gate, "has_digest": bool(DIGEST_RE.search(text)),
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
    html = proto.read_text(encoding="utf-8")
    warnings = []
    try:
        layer = ANNOTATION_LAYER.read_text(encoding="utf-8")
    except OSError:
        return _emit({
            "ok": True, "injected": False, "schema": SCHEMA_VERSION,
            "reasons": ["[WARN] annotation layer unreadable at %s — prototype presented READ-ONLY. "
                        "The human can still look; they just cannot pin comments." % ANNOTATION_LAYER],
        })
    if "id=\"an-dock\"" in html or "an-dock" in html:
        warnings.append("annotation layer already present — not injected twice.")
        return _emit({"ok": True, "injected": False, "reasons": warnings, "schema": SCHEMA_VERSION})

    idx = html.rfind("</body>")
    out = (html[:idx] + layer + html[idx:]) if idx != -1 else (html + layer)
    if idx == -1:
        warnings.append("[WARN] no </body> found — layer appended at end of file.")
    proto.write_text(out, encoding="utf-8")
    return _emit({"ok": True, "injected": True, "bytes_added": len(out) - len(html),
                  "source": str(ANNOTATION_LAYER), "reasons": warnings, "schema": SCHEMA_VERSION})


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
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
