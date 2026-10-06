#!/usr/bin/env python3
"""`captureBackend` — the host adapter that turns an HTML file flow produced into a PNG.

Flow authors two pages a human is asked to LOOK at: the gate-1 prototype and the
merge-gate walkthrough. v1.59.0 made the hand-off honest about where they live and
v1.60.0 made them optionally reachable at a URL. Both still require the reader to go
somewhere. This slot produces a still frame, which is the only route to a reader's eye
that needs no server, no sign-in, and no public repo — so it is the one that works
when the other two do not.

ONE verb, and the placeholder vocabulary is **closed**:

    screenshot  {url} {out} {width} {height}

All four are required. A template that cannot be told a width would silently produce
two identical frames under two different size labels — a picture that lies, which is
the one output this module refuses to produce (see `declares_utf8` for the same rule
applied to encoding).

**The target is a LOCAL FILE, never a URL the caller composes.** The engine derives
`{url}` itself with `file_url()`. That is deliberate and it is what makes the UTF-8
precondition checkable: a page flow cannot read the bytes of is a page flow cannot
confirm will render correctly, and capturing it anyway is the mojibake case below.
A served URL *does* capture fine (measured), but nothing in flow needs it, and the
flag would exist only to let a caller skip the precondition.

SUCCESS IS "A VALID PNG OF THE REQUESTED SIZE EXISTS", NEVER THE EXIT STREAM.
Measured 2026-10-06: a real headless run prints `Failed to connect to the bus` to
stderr on every invocation and still exits 0 with a correct PNG. A reader that treats
stderr as failure throws away every working capture; a reader that treats exit 0 as
success accepts a truncated file. So `capture()` reads the ARTIFACT — magic bytes plus
the IHDR dimensions — and the exit code only ever contributes to the stated *reason*
when the artifact already failed. The dimension check is what separates "captured the
page at this width" from "captured something".

DEGRADATION IS THE NORMAL CASE, NOT AN ERROR PATH. The slot is unset by default, so
every consumer that has not configured it keeps v1.60.0's behaviour byte-identical:
no image syntax anywhere, the link and the honest local line intact. Every failure
returns a stated reason and emits no frame. A frame is never claimed on a guess.

No vendor binary is named here, by the same rule that shaped `previewBackend`: the
plugin ships the workflow, the project's own `flow.config.json` supplies the mechanics.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import struct
import subprocess
import sys
from pathlib import Path

# ONE definition of the refusal policy — its APPLICATION (`render_template`, public
# since v1.60.0) as well as its data. A third copy of "refuse, never escape" is the
# fan-out class .claude/rules/general.md Consistency item 2 keeps charging this repo
# for, so this adapter calls the shared function exactly as `preview_backend` does.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dispatch_backend import (  # noqa: E402  (sibling-module import, house pattern)
    _PLACEHOLDER_RE,
    render_template,
)

PREFIX = "[capture-frames]"

KNOWN_PLACEHOLDERS = {"url", "out", "width", "height"}

VERBS = {
    "screenshot": (
        {"url", "out", "width", "height"},
        "render the page at {url} into the PNG file {out} at exactly {width}x{height} "
        "(the host's own headless-browser command)",
        "open the page yourself at that size and screenshot it, or accept the hand-off "
        "without a frame — which is correct and honest, just less immediate",
    ),
}

ESSENTIAL = {"screenshot"}

# THE FRAME SET, ORDERED, AND THE ORDER IS PHONE-FIRST ON PURPOSE. The whole
# workstream exists because review happens on a phone, so the phone frame is the one
# that leads — and when only ONE frame is wanted (the chat message's budget allows
# exactly one) it is the first entry that gets taken, by construction rather than by a
# caller remembering which index to slice.
#
# 390x844 is the iPhone 14/15 logical viewport. 1280x900 is a desktop window a
# prototype has to survive too: "works at exactly one width" is the defect a reviewer
# most wants to see, and it is invisible in a single frame.
#
# This table is the SHARED definition. `artifact-handoff.py` imports it to order and
# caption the rows it renders, so the writer and the reader cannot disagree about
# either the filenames or the sequence — a `sorted()` on disk would have put desktop
# first and quietly inverted the one ordering decision this table records.
FRAMES = (
    ("phone", 390, 844),
    ("desktop", 1280, 900),
)
FRAME_NAMES = tuple(n for n, _w, _h in FRAMES)
FRAME_SIZES = {n: (w, h) for n, w, h in FRAMES}

# A label identifies WHICH artifact a frame is of (`prototype`, `walkthrough`). It
# becomes a path component and then a caption, so it is bounded to a slug here rather
# than escaped at each of those positions. Refusing is cheap: every shipped caller
# passes a literal.
LABEL_RE = re.compile(r"\A[a-z0-9][a-z0-9-]{0,31}\Z")

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# `<meta charset="utf-8">`, `charset=UTF-8` in a Content-Type meta, or an XML decl.
# Case-insensitive, and `utf8` without the hyphen counts — browsers accept it.
_UTF8_RE = re.compile(rb"charset\s*=\s*[\"']?\s*utf-?8", re.I)


# ----------------------------------------------------------------- config slot

def load_backend(config_path="flow.config.json"):
    """Return (backend_dict, notes). Missing slot ⇒ ({}, [note]).

    An absent slot is NOT a warning in the scary sense — it is the documented default
    and the caller's behaviour is correct without it, so the note says so. Nobody
    should read "no capture adapter" as a broken install.
    """
    p = Path(config_path)
    if not p.is_file():
        return {}, [
            f"{PREFIX} {config_path} not found, so no capture adapter is configured. "
            f"No frames will be captured and no image will be claimed — the hand-off "
            f"names the artifact and says where it can be opened, which is correct."
        ]
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, [
            f"{PREFIX} ⚠️ {config_path} could not be read or parsed ({exc}); no capture "
            f"adapter is available. No frames will be captured."
        ]
    backend = data.get("captureBackend")
    if backend is None:
        return {}, [
            f"{PREFIX} no `captureBackend` slot, so this project captures no frames. The "
            f"hand-off is unchanged and still correct. To wire one, add a `screenshot` "
            f"command template; see the schema."
        ]
    if not isinstance(backend, dict):
        return {}, [
            f"{PREFIX} ⚠️ flow.config.json.captureBackend is present but is not an object "
            f"(got {type(backend).__name__}). Treating it as absent — fix the slot; a "
            f"malformed adapter is NOT the same as no adapter, and this project believes "
            f"it has one."
        ]
    return backend, []


def chat_image_dir(config_path="flow.config.json"):
    """-> (dir|None, notes). `chatImagePath` is unset by default, and unset is correct.

    Deliberately a config slot rather than a hardcoded scratch directory. The obvious
    candidate was one particular host's `.context/` convention — but that directory is
    ignored only via `.git/info/exclude`, which is LOCAL TO ONE CLONE and shared with
    nobody, so a consumer of flow has neither the directory nor the ignore rule.
    Hardcoding it in a plugin artifact is precisely the project-specific-token mistake
    `previewBackend` exists to avoid (FB-0085).
    """
    p = Path(config_path)
    if not p.is_file():
        return None, [f"{PREFIX} {config_path} not found, so no chat-image directory is "
                      f"configured; the chat hand-off carries no image."]
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, [f"{PREFIX} ⚠️ {config_path} unreadable ({exc}); no chat-image "
                      f"directory resolved."]
    raw = data.get("chatImagePath")
    if raw is None:
        return None, [f"{PREFIX} no `chatImagePath` slot, so the chat hand-off carries no "
                      f"image. That is the default and the line is still correct."]
    if not isinstance(raw, str) or not raw.strip():
        return None, [f"{PREFIX} ⚠️ flow.config.json.chatImagePath is present but is not a "
                      f"non-empty string; treating it as absent."]
    return raw.strip(), []


def validate(backend):
    """Per-verb report. Never raises.

    Every template problem is computed by actually calling `render()` with dummy
    values, not by a second hand-written copy of the checks — the shape
    `dispatch_backend.validate` arrived at after three defects of the one kind
    ("passes check, refuses at the call site"). `/flow:doctor` Check 2.14 exists to
    catch an adapter that would fail invisibly, so a green report over a template that
    cannot render would defeat it entirely.
    """
    report = {"verbs": {}, "usable": False, "configured": 0,
              "known_placeholders": sorted(KNOWN_PLACEHOLDERS),
              "frames": [{"name": n, "width": w, "height": h} for n, w, h in FRAMES]}
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
            found = set(_PLACEHOLDER_RE.findall(tmpl))
            dummies = {k: "x" for k in (found | required) & KNOWN_PLACEHOLDERS}
            _argv, err = render(backend, verb, dummies)
            problems = []
            if err:
                problems.append(
                    re.sub(r"^.*?refusing to render `%s`:\s*" % re.escape(verb), "", err))
            # The one class render() cannot see, because a value IS supplied for it: a
            # placeholder in the vocabulary that this verb is never given. It validates
            # clean and then refuses at the call site.
            extra = sorted(found - required)
            if extra:
                problems.append(
                    f"uses {', '.join('{%s}' % e for e in extra)}, which `{verb}` is never "
                    f"supplied — it would validate here and refuse at the call site. "
                    f"Required for `{verb}`: "
                    f"{', '.join('{%s}' % r for r in sorted(required))}.")
            entry.update(state="ok" if not problems else "invalid", problems=problems)
            if not problems:
                report["configured"] += 1
        report["verbs"][verb] = entry
    report["usable"] = all(report["verbs"][v]["state"] == "ok" for v in ESSENTIAL)
    return report


def render(backend, verb, values):
    """Return (argv, error). The refusal policy is `dispatch_backend.render_template`."""
    if verb not in VERBS:
        return None, f"{PREFIX} ⚠️ unknown verb {verb!r}. Known: {', '.join(sorted(VERBS))}."
    required, _purpose, manual = VERBS[verb]
    return render_template(
        backend.get(verb), verb, required, KNOWN_PLACEHOLDERS, values, PREFIX, manual,
        "captureBackend",
        shell_operator_hint=(" If your host needs flags that contain one, put them inside a "
                             "script the template CALLS, not in the template."),
        placeholder_hint=(" In particular there is no `{selector}` or `{wait}`: flow captures "
                          "a whole page it authored itself, and a template that could choose "
                          "WHAT to photograph would let config decide what the frame claims."))


# --------------------------------------------------------- reading the artifact

def png_size(path):
    """-> (width, height) for a real PNG, else None. The IHDR, not the filename.

    This is the check that distinguishes "captured the page at this width" from
    "captured something". Without it a backend that ignores `{width}` produces two
    byte-different frames labelled 390x844 and 1280x900 that are in fact the same
    viewport — two true-looking captions over one measurement.
    """
    try:
        with open(path, "rb") as fh:
            head = fh.read(24)
    except OSError:
        return None
    if len(head) < 24 or not head.startswith(_PNG_MAGIC):
        return None
    if head[12:16] != b"IHDR":
        return None
    try:
        w, h = struct.unpack(">II", head[16:24])
    except struct.error:
        return None
    return (w, h)


def declares_utf8(path):
    """Does this HTML declare UTF-8? Asserted BEFORE capture, and absence REFUSES.

    Measured: a page delivered without a charset declaration renders `✓` as `âœ“`.
    A screenshot of that page is strictly worse than no screenshot — it is a picture
    that lies, published into the one message a human is guaranteed to read, and
    nothing downstream can tell it from a correct one. So this refuses rather than
    warns.

    v1.60.0 already requires `<meta charset="utf-8">` in the agent-authored prototype
    and asserts that both renderers emit it, so this refusal should be unreachable in
    practice. That is exactly why it has to be loud if it ever fires.

    Read as BYTES, not text: a file this function is about to call badly-encoded is a
    file `read_text` may refuse to decode, and a UnicodeDecodeError here would report
    "cannot read" for a page whose real problem is the thing being tested.
    """
    try:
        blob = Path(path).read_bytes()
    except OSError:
        return False
    # Only the head: a declaration must precede the content it governs, and scanning a
    # whole base64-inlined report for it is both slow and wrong (a `charset=utf-8`
    # inside an inlined data URI is not a document declaration).
    return bool(_UTF8_RE.search(blob[:4096]))


def file_url(path):
    """An absolute local path as a `file://` URL.

    `as_uri()` percent-encodes, which keeps a path with a space or a `#` from
    splitting into a URL plus a fragment. The rendered value still has to survive
    `render_template`'s safe-value charset, so a sufficiently strange path produces a
    stated refusal rather than a mis-targeted capture.
    """
    return Path(path).resolve().as_uri()


def branch_slug(branch):
    """A branch name as one safe path component, or "" when there is nothing to slug.

    SHARED, and that is the point: this value names the directory a PR's frames are
    written to AND the directory they are read back from. Two copies of this function
    would mean a writer and a reader that agree today and diverge the first time
    someone "tidies" one of them — and the failure would be silent, because an empty
    read renders as the ordinary "no frames to show" line.

    Returns "" for a branch that slugs to nothing (empty, or all separators), so the
    caller can refuse. A detached HEAD yields an empty `git branch --show-current`,
    which must never become a real directory that a later PR also writes to.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", str(branch or "").lower()).strip("-")
    return slug[:64]


# ------------------------------------------------------------------- capturing

def capture(backend, target, out_dir, label, frames=FRAMES, timeout=90, config_dir=None):
    """Capture `frames` of the local HTML file `target` into `out_dir`.

    -> (captured, reasons): `captured` is a list of
    {"name","width","height","path","rel"} in FRAMES order; `reasons` is a list of
    plain-language strings naming everything that did not happen. Both may be
    non-empty — a run where the phone frame captured and the desktop one did not is a
    real state, and silently dropping either half of that report is the behaviour this
    module refuses.

    Never raises on a host problem. A capture is an optional convenience sitting
    upstream of a gate; a crash here would fail a ship over a missing screenshot.
    """
    reasons = []
    captured = []

    if not LABEL_RE.match(str(label or "")):
        return [], [f"{PREFIX} ⚠️ refusing to capture: label {label!r} is not a plain slug "
                    f"([a-z0-9-], 32 chars max). The label becomes a filename and then a "
                    f"caption, so it is bounded here rather than escaped at both."]

    tgt = Path(target)
    if not tgt.is_file():
        return [], [f"{PREFIX} no frames captured: there is nothing to photograph at "
                    f"{target} (a run that produced no such artifact is a supported "
                    f"state, not a failure)."]

    if not declares_utf8(tgt):
        return [], [f"{PREFIX} ⚠️ REFUSING to capture {target}: it declares no UTF-8 "
                    f"charset, and a page without one renders non-ASCII text as mojibake. "
                    f"A screenshot of a garbled page is worse than no screenshot — it is a "
                    f"picture that lies, and nothing downstream can tell it from a correct "
                    f"one. Add `<meta charset=\"utf-8\">` to the page."]

    rep = validate(backend)
    if not rep["usable"]:
        probs = "; ".join(rep["verbs"]["screenshot"].get("problems") or ["not configured"])
        return [], [f"{PREFIX} no frames captured: the capture adapter is not usable "
                    f"({probs}). This is the default state for a project that has not set "
                    f"`captureBackend`, and the hand-off is correct without it."]

    out = Path(out_dir)
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return [], [f"{PREFIX} ⚠️ could not create the frame directory {out_dir} ({exc}); "
                    f"no frames captured."]

    url = file_url(tgt)
    for name, width, height in frames:
        dest = out / ("%s-%s.png" % (label, name))
        # Remove a previous run's frame FIRST. Without this, a capture that fails
        # leaves the stale file in place and the artifact check passes on it — this
        # PR's body would then carry the previous iteration's picture, which is the
        # wrong-frame class the whole engine is built to refuse.
        try:
            dest.unlink()
        except OSError:
            pass
        argv, err = render(backend, "screenshot",
                           {"url": url, "out": str(dest), "width": width, "height": height})
        if err:
            reasons.append(err)
            continue
        rc, serr = None, ""
        try:
            proc = subprocess.run(argv, cwd=str(config_dir) if config_dir else None,
                                  capture_output=True, text=True, timeout=timeout)
            rc, serr = proc.returncode, (proc.stderr or "")
        except subprocess.TimeoutExpired:
            reasons.append(f"{PREFIX} ⚠️ the {name} capture did not finish within "
                           f"{timeout}s and was stopped; no {name} frame.")
            continue
        except (OSError, subprocess.SubprocessError) as exc:
            reasons.append(f"{PREFIX} ⚠️ the {name} capture command could not be run "
                           f"({exc}) — most likely the command is not on PATH. No "
                           f"{name} frame.")
            continue

        # THE ARTIFACT DECIDES. Not `rc`, and emphatically not `serr`: a real headless
        # run writes dbus noise to stderr on every single invocation and still produces
        # a correct PNG, so a stderr-sensitive reader would discard every working
        # capture. `rc` is consulted only to make the REASON specific once the artifact
        # has already failed the check.
        size = png_size(dest)
        if size is None:
            reasons.append(
                f"{PREFIX} ⚠️ the {name} capture produced no valid PNG at {dest} "
                f"(exit {rc}). Not emitting a frame."
                + (f" The command said: {serr.strip().splitlines()[-1][:200]}"
                   if serr.strip() else ""))
            try:
                dest.unlink()
            except OSError:
                pass
            continue
        if size != (width, height):
            reasons.append(
                f"{PREFIX} ⚠️ the {name} capture is {size[0]}x{size[1]}, not the "
                f"{width}x{height} that was asked for — so the frame and its label would "
                f"disagree. Most likely the `screenshot` template drops {{width}}/"
                f"{{height}}. Not emitting a frame.")
            try:
                dest.unlink()
            except OSError:
                pass
            continue
        captured.append({"name": name, "width": width, "height": height,
                         "path": str(dest), "rel": dest.name})
    return captured, reasons


def warn_if_not_ignored(path, root=None):
    """-> note|None. Is this capture directory git-ignored?

    Paired with the positive it protects rather than left implicit: a chat-image
    directory that git tracks turns every gate-1 presentation into working-tree
    changes that the next `git add -A` commits. That is not fatal — the image still
    renders, which is why this warns rather than refuses — but it is invisible, and
    "invisible and not fatal" is how a repo accumulates screenshots nobody chose to
    keep.
    """
    try:
        r = subprocess.run(["git", "check-ignore", "-q", str(path)],
                           cwd=str(root) if root else None, capture_output=True,
                           text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode == 0:
        return None
    return (f"{PREFIX} note: {path} is not git-ignored, so captured chat frames will show "
            f"up as working-tree changes and can be committed by accident. Add it to "
            f"`.gitignore` — these frames are for the chat message, not the repo.")


# ------------------------------------------------------------------ selftest

def selftest() -> int:
    """Known-positive FIRST, then the negatives (general.md Consistency item 4).

    Every arm drives a STUB backend — `python3 -c` writing bytes — because the thing
    under test is the adapter contract and the artifact check, not any host's browser.
    An arm needing a real browser would measure the vendor and would not run in CI.
    """
    import tempfile
    fails = []

    def check(name, cond, detail=""):
        if not cond:
            fails.append("%s%s" % (name, (": " + detail) if detail else ""))

    with tempfile.TemporaryDirectory() as td:
        page = Path(td, "p.html")
        page.write_text('<!doctype html><meta charset="utf-8"><p>ok ✓</p>',
                        encoding="utf-8")
        nocs = Path(td, "nocharset.html")
        nocs.write_text("<!doctype html><p>ok</p>", encoding="utf-8")
        helper = Path(td, "shot.py")
        # The stub reads the SAME argv the real command would: url out width height.
        # Modes are chosen by an env-free marker in argv[1] so one helper serves every
        # arm without a second template shape to keep in sync.
        helper.write_text(
            "import sys, struct, binascii\n"
            "mode, url, out, w, h = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])\n"
            "def png(w, h):\n"
            "    ihdr = struct.pack('>II', w, h) + b'\\x08\\x06\\x00\\x00\\x00'\n"
            "    c = struct.pack('>I', len(ihdr)) + b'IHDR' + ihdr + struct.pack('>I', binascii.crc32(b'IHDR'+ihdr) & 0xFFFFFFFF)\n"
            "    return b'\\x89PNG\\r\\n\\x1a\\n' + c\n"
            "if mode == 'ok':\n"
            "    open(out, 'wb').write(png(w, h))\n"
            "elif mode == 'noisy':\n"
            "    open(out, 'wb').write(png(w, h)); sys.stderr.write('Failed to connect to the bus\\n')\n"
            "elif mode == 'nothing':\n"
            "    pass\n"
            "elif mode == 'truncated':\n"
            "    open(out, 'wb').write(b'not a png at all')\n"
            "elif mode == 'wrongsize':\n"
            "    open(out, 'wb').write(png(100, 100))\n"
            "elif mode == 'fail':\n"
            "    sys.stderr.write('boom\\n'); sys.exit(3)\n",
            encoding="utf-8")

        def be(mode):
            return {"screenshot": "python3 %s %s {url} {out} {width} {height}"
                                  % (helper, mode)}

        outd = Path(td, "frames")

        # --- KNOWN POSITIVE: two frames, right sizes, FRAMES order, phone first.
        got, why = capture(be("ok"), page, outd, "prototype")
        check("positive/two-frames", len(got) == 2, "%r / %r" % (got, why))
        check("positive/no-reasons", not why, repr(why))
        check("positive/phone-first", [g["name"] for g in got] == ["phone", "desktop"],
              repr([g["name"] for g in got]))
        check("positive/sizes-asserted",
              [(g["width"], g["height"]) for g in got] == [(390, 844), (1280, 900)])
        check("positive/filenames", [g["rel"] for g in got] ==
              ["prototype-phone.png", "prototype-desktop.png"], repr(got))
        check("positive/real-dimensions-on-disk",
              png_size(got[0]["path"]) == (390, 844), repr(png_size(got[0]["path"])))

        # --- stderr noise is NOT failure. The measured real-world case.
        got, why = capture(be("noisy"), page, outd, "prototype")
        check("stderr/accepted", len(got) == 2 and not why, "%r / %r" % (got, why))

        # --- exits 0 writing nothing -> refused, and the reason says so.
        got, why = capture(be("nothing"), page, outd, "prototype")
        check("exit0-no-file/refused", not got, repr(got))
        check("exit0-no-file/reason", any("no valid PNG" in r for r in why), repr(why))

        # --- a truncated non-PNG -> refused.
        got, why = capture(be("truncated"), page, outd, "prototype")
        check("truncated/refused", not got and any("no valid PNG" in r for r in why),
              repr(why))
        check("truncated/stale-file-removed",
              not Path(outd, "prototype-phone.png").exists(),
              "a rejected capture left its file behind, so the next run can read it as "
              "this run's frame")

        # --- a PNG of the WRONG size -> refused, because the label would lie.
        got, why = capture(be("wrongsize"), page, outd, "prototype")
        check("wrongsize/refused", not got, repr(got))
        check("wrongsize/reason", any("not the 390x844" in r for r in why), repr(why))

        # --- non-zero exit -> refused with a stated reason (degrades loudly).
        got, why = capture(be("fail"), page, outd, "prototype")
        check("nonzero/refused", not got and len(why) == 2, repr(why))

        # --- command not on PATH -> refused, no crash.
        got, why = capture({"screenshot": "definitely-not-a-real-binary-xyz {url} {out} "
                                          "{width} {height}"}, page, outd, "prototype")
        check("absent-binary/refused", not got, repr(got))
        check("absent-binary/reason", any("could not be run" in r for r in why), repr(why))

        # --- UNSET slot -> refused, and the reason says unset is correct.
        got, why = capture({}, page, outd, "prototype")
        check("unset/refused", not got, repr(got))
        check("unset/reason-says-default", any("has not set" in r for r in why), repr(why))

        # --- a page with no charset declaration is REFUSED, and nothing is written.
        stale = Path(outd, "proto2-phone.png")
        got, why = capture(be("ok"), nocs, outd, "proto2")
        check("no-utf8/refused", not got, repr(got))
        check("no-utf8/reason", any("declares no UTF-8" in r for r in why), repr(why))
        check("no-utf8/nothing-written", not stale.exists(),
              "a page flow refused to capture still produced a file")
        # PAIRED with the positive: the same backend on a page that DOES declare it.
        got, _ = capture(be("ok"), page, outd, "proto2")
        check("utf8/paired-positive", len(got) == 2, repr(got))

        # --- missing target -> one plain reason, no crash.
        got, why = capture(be("ok"), Path(td, "nope.html"), outd, "prototype")
        check("missing-target/refused", not got and len(why) == 1, repr(why))

        # --- a bad label is refused before anything runs.
        got, why = capture(be("ok"), page, outd, "../evil")
        check("bad-label/refused", not got and any("plain slug" in r for r in why),
              repr(why))

    # --- closed vocabulary, both at validate AND at render.
    unk = {"screenshot": "cmd {url} {out} {width} {height} {selector}"}
    check("vocab/validate-refuses-unknown", not validate(unk)["usable"])
    _a, e = render(unk, "screenshot", {"url": "file:///x", "out": "/o.png",
                                       "width": 1, "height": 2})
    check("vocab/render-refuses-unknown", e is not None and "unknown placeholder" in (e or ""),
          repr(e))
    op = {"screenshot": "cmd {url} {out} {width} {height} & true"}
    check("vocab/validate-refuses-operator", not validate(op)["usable"])
    _a, e = render(op, "screenshot", {"url": "file:///x", "out": "/o.png",
                                      "width": 1, "height": 2})
    check("vocab/render-refuses-operator", e is not None and "shell operator" in (e or ""),
          repr(e))
    good = {"screenshot": "cmd --window-size={width},{height} --out {out} {url}"}
    # POSITIVE: without this, deleting the renderer would turn every line above green.
    check("vocab/good-template-validates", validate(good)["usable"], repr(validate(good)))
    check("vocab/all-four-required",
          not validate({"screenshot": "cmd {url} {out}"})["usable"])

    # --- the slug is one component, and an unsluggable branch yields "" not "-".
    check("slug/basic", branch_slug("conductor/chat-and-pr-screenshots")
          == "conductor-chat-and-pr-screenshots")
    check("slug/underscores", branch_slug("feat/empty_feed") == "feat-empty-feed")
    check("slug/no-traversal", "/" not in branch_slug("../../etc/passwd")
          and ".." not in branch_slug("../../etc/passwd"))
    check("slug/empty-stays-empty", branch_slug("") == "" and branch_slug("///") == "",
          "a detached HEAD must not become a real directory a later PR also writes to")

    if fails:
        print("[capture-frames] SELFTEST FAIL — %d check(s):" % len(fails))
        for f in fails:
            print("  - %s" % f)
        return 1
    print("[capture-frames] SELFTEST PASS — known-positive, nine negatives, closed vocabulary")
    return 0


# ---------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="capture_frames.py",
                                 description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true",
                    help="run the engine's own known-positive + known-negatives")
    sub = ap.add_subparsers(dest="cmd")

    c = sub.add_parser("check", help="validate the configured adapter")
    c.add_argument("--config", default="flow.config.json")

    r = sub.add_parser("render", help="render the screenshot argv (no capture)")
    r.add_argument("--config", default="flow.config.json")
    r.add_argument("--url"); r.add_argument("--out")
    r.add_argument("--width"); r.add_argument("--height")

    s = sub.add_parser("slug", help="this branch as one safe path component")
    s.add_argument("--branch", required=True)

    cap = sub.add_parser("capture", help="capture the frame set of one local HTML file")
    cap.add_argument("--config", default="flow.config.json")
    cap.add_argument("--target", required=True, help="local HTML file to photograph")
    cap.add_argument("--out-dir", required=True)
    cap.add_argument("--label", required=True,
                     help="which artifact this is a frame of, e.g. prototype")
    cap.add_argument("--only", default=None, choices=list(FRAME_NAMES),
                     help="capture just this frame (the chat message's budget is one image)")
    cap.add_argument("--timeout", type=int, default=90)

    cd = sub.add_parser("chat-dir", help="resolve flow.config.json.chatImagePath")
    cd.add_argument("--config", default="flow.config.json")

    a = ap.parse_args(argv)
    # argparse owns the flag; a pre-parse `"--selftest" in argv` scan would match it
    # anywhere and run the selftest instead of erroring on a malformed subcommand.
    if a.selftest:
        return selftest()

    if a.cmd == "check":
        backend, notes = load_backend(a.config)
        rep = validate(backend)
        rep["notes"] = notes
        print(json.dumps(rep, indent=2, sort_keys=True))
        return 0 if rep["usable"] else 1
    if a.cmd == "render":
        backend, notes = load_backend(a.config)
        for n in notes:
            sys.stderr.write(n + "\n")
        vals = {k: v for k, v in (("url", a.url), ("out", a.out),
                                  ("width", a.width), ("height", a.height))
                if v is not None}
        argvv, err = render(backend, "screenshot", vals)
        if err:
            sys.stderr.write(err + "\n")
            return 1
        print(shlex.join(argvv) if hasattr(shlex, "join") else " ".join(argvv))
        return 0
    if a.cmd == "slug":
        slug = branch_slug(a.branch)
        if not slug:
            sys.stderr.write(
                "%s ⚠️ %r slugs to nothing, so there is no per-PR frame directory to "
                "use. A detached HEAD reads as an empty branch name; frames would land "
                "in a shared directory another PR also writes to.\n" % (PREFIX, a.branch))
            return 1
        print(slug)
        return 0
    if a.cmd == "capture":
        backend, notes = load_backend(a.config)
        for n in notes:
            sys.stderr.write(n + "\n")
        frames = FRAMES if a.only is None else tuple(
            f for f in FRAMES if f[0] == a.only)
        got, why = capture(backend, a.target, a.out_dir, a.label, frames=frames,
                           timeout=a.timeout,
                           config_dir=Path(a.config).resolve().parent
                           if Path(a.config).is_file() else None)
        # Reasons go to stderr and frames to stdout, because stdout is what a caller
        # substitutes into a message a human reads. A reason printed on stdout would be
        # pasted into the chat as if it were a path.
        for w in why:
            sys.stderr.write(w + "\n")
        print(json.dumps({"frames": got, "reasons": why}, indent=2))
        return 0 if got else 1
    if a.cmd == "chat-dir":
        d, notes = chat_image_dir(a.config)
        for n in notes:
            sys.stderr.write(n + "\n")
        if not d:
            return 1
        note = warn_if_not_ignored(d, Path(a.config).resolve().parent)
        if note:
            sys.stderr.write(note + "\n")
        print(d)
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
