#!/usr/bin/env python3
"""Regression pin for lib/capture_frames.py, the `captures` frame source, and the chat image.

Why this harness carries the behavioural load: flow's `flow.config.json` sets
`"platform": "library"`, so `/flow:verify-build` self-skips — there is no behavioural
gate above this file.

What it deliberately does NOT test: a browser. Every arm drives a STUB `screenshot`
backend (a short `python3` script that writes bytes), because the thing under test is
the adapter contract and the artifact check — closed vocabulary, refuse-not-escape,
success-is-the-artifact, degrade loudly, never claim a frame on a guess. An arm needing
a real headless browser would measure the vendor rather than flow and would not run in
CI.

The live measurements this feature rests on are recorded in the history entry and in
`flow.config.json`'s own comment, not re-run here:
  * google-chrome 151.0.7922.169, `--headless --screenshot={out} --window-size=w,h`,
    produced real PNGs of exactly 390x844 and 1280x900 (2026-10-06).
  * every such run printed `Failed to connect to the bus` to stderr and exited 0 —
    which is the whole reason `capture()` reads the artifact and not the exit stream.
  * a raw URL pinned to a PR-branch sha that a squash-merge DISCARDED still returns
    http 200, paired against an all-zeros sha returning 404. That is what makes a
    committed per-PR frame keep resolving after the branch is deleted at merge.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLOW = HERE.parent
REPO = FLOW.parent.parent
LIB = FLOW / "lib" / "capture_frames.py"
ENGINE = FLOW / "skills" / "ship" / "lib" / "artifact-handoff.py"
SCHEMA = FLOW / "schema" / "flow.config.schema.json"
CI = REPO / ".github" / "workflows" / "ci.yml"
SHIP = FLOW / "skills" / "ship" / "SKILL.md"
SPIKE = FLOW / "skills" / "ship-spike" / "SKILL.md"
PROTO = FLOW / "skills" / "prototype" / "SKILL.md"
DOCTOR = FLOW / "skills" / "doctor" / "SKILL.md"

_spec = importlib.util.spec_from_file_location("capture_frames", LIB)
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)

_espec = importlib.util.spec_from_file_location("artifact_handoff", ENGINE)
A = importlib.util.module_from_spec(_espec)
_espec.loader.exec_module(A)

_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print("  PASS  %s" % name)
    else:
        print("  FAIL  %s%s" % (name, ("\n        " + detail) if detail else ""))
        _failures.append(name)


# A stub backend. `mode` selects the failure shape; the remaining argv is exactly what
# a real command receives, so the template under test is the real template shape.
_STUB = """
import sys, struct, binascii
mode, url, out, w, h = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
def png(w, h):
    ihdr = struct.pack('>II', w, h) + b'\\x08\\x06\\x00\\x00\\x00'
    c = struct.pack('>I', len(ihdr)) + b'IHDR' + ihdr + struct.pack('>I', binascii.crc32(b'IHDR'+ihdr) & 0xFFFFFFFF)
    return b'\\x89PNG\\r\\n\\x1a\\n' + c
if mode == 'ok':
    open(out, 'wb').write(png(w, h))
elif mode == 'noisy':
    open(out, 'wb').write(png(w, h))
    sys.stderr.write('Failed to connect to the bus: Could not parse server address\\n')
elif mode == 'nothing':
    sys.exit(0)
elif mode == 'truncated':
    open(out, 'wb').write(b'<html>not a png</html>')
elif mode == 'ignores-size':
    open(out, 'wb').write(png(800, 600))
elif mode == 'dpr':
    open(out, 'wb').write(png(w * 2, h * 2))
elif mode == 'fail':
    sys.stderr.write('could not start browser\\n'); sys.exit(3)
"""


def _stub(td):
    p = Path(td, "stub.py")
    p.write_text(_STUB, encoding="utf-8")
    return p


def _be(td, mode):
    return {"screenshot": "python3 %s %s {url} {out} {width} {height}" % (_stub(td), mode)}


def _page(td, name="p.html", charset=True, title="Empty activity feed"):
    p = Path(td, name)
    p.write_text(('<!doctype html><meta charset="utf-8">' if charset else "<!doctype html>")
                 + ("<title>%s</title>" % title if title else "")
                 + "<p>state ✓</p>", encoding="utf-8")
    return p


def _extract_sh_block(path, heading):
    """The first ```sh fence under `heading` in a SKILL.md, or None.

    Extracted rather than copied into the test so the thing under test is the thing
    that ships — a transcribed copy would pass while the shipped block was broken.
    """
    text = path.read_text(encoding="utf-8")
    if heading not in text:
        return None
    after = text[text.index(heading):]
    m = re.search(r"```sh\n(.*?)\n```", after, re.S)
    return m.group(1) if m else None


def _git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _repo(td):
    """A temp git repo with a visual-history path and this PR's frame directory."""
    root = Path(td, "repo")
    (root / "dev-docs").mkdir(parents=True)
    _git(["init", "-q", "-b", "main"], root)
    _git(["config", "user.email", "e@v.al"], root)
    _git(["config", "user.name", "evals"], root)
    Path(root, "dev-docs", "visual-history.html").write_text(
        "<!doctype html><html><body></body></html>", encoding="utf-8")
    _git(["add", "-A"], root)
    _git(["commit", "-qm", "base"], root)
    return root


def _png(w, h):
    import binascii
    ihdr = struct.pack(">II", w, h) + b"\x08\x06\x00\x00\x00"
    c = struct.pack(">I", len(ihdr)) + b"IHDR" + ihdr + struct.pack(
        ">I", binascii.crc32(b"IHDR" + ihdr) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + c


def _head(root):
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                          text=True, timeout=20).stdout.strip()


# ---------------------------------------------------------------- the criteria

# v1.60.0's exact output, WRITTEN OUT rather than imported. Importing the renderer and
# comparing it to itself would pass for any wording whatsoever — the criterion is
# "byte-identical to what v1.60.0 shipped", and only a literal can express that.
V160_PROTOTYPE_LOCAL = (
    "Your prototype is a local file — it lives at "
    "`/abs/.flow/prototypes/feed/prototype.presented.html`, and you can only open it "
    "where this session ran, not from a link. The small floating comment dock is "
    "flow's, not the design."
)
V160_WALKTHROUGH_LOCAL = (
    "Walkthrough — a file on one machine's disk, not committed and not reachable from "
    "this page. You can only open it where this pipeline ran: `.flow/report.html`."
)
V160_PROTOTYPE_SERVED = (
    "Prototype: https://ws-abc.example.show/prototype.presented-2b7c91de.html — anyone "
    "in the acme-eng org. The small floating comment dock is flow's, not the design. If "
    "that link is dead, ask for it again and it will be re-served — or open "
    "`/abs/p.html`, which works only where this session ran."
)


def test_unset_is_byte_identical():
    """With no adapter and no image, every hand-off is exactly what v1.60.0 emitted."""
    check("unset/prototype-local",
          A.render_local_line("prototype",
                              "/abs/.flow/prototypes/feed/prototype.presented.html")
          == V160_PROTOTYPE_LOCAL,
          A.render_local_line("prototype",
                              "/abs/.flow/prototypes/feed/prototype.presented.html"))
    check("unset/walkthrough-local",
          A.render_local_line("walkthrough", ".flow/report.html") == V160_WALKTHROUGH_LOCAL,
          A.render_local_line("walkthrough", ".flow/report.html"))
    check("unset/prototype-served",
          A.render_local_line(
              "prototype", "/abs/p.html",
              "https://ws-abc.example.show/prototype.presented-2b7c91de.html",
              "anyone in the acme-eng org") == V160_PROTOTYPE_SERVED,
          A.render_local_line(
              "prototype", "/abs/p.html",
              "https://ws-abc.example.show/prototype.presented-2b7c91de.html",
              "anyone in the acme-eng org"))
    # And `--source record` is untouched: the default is still `record`, so an existing
    # call site that never learns about `--source` keeps its exact behaviour.
    hlp = subprocess.run([sys.executable, str(ENGINE), "frames", "--help"],
                         capture_output=True, text=True, timeout=30).stdout
    check("unset/record-is-still-the-default", "default: record" in hlp or
          "`record` reads the committed" in hlp, hlp[:400])
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td, "flow.config.json")
        cfg.write_text("{}", encoding="utf-8")
        be, notes = C.load_backend(str(cfg))
        check("unset/no-backend", be == {} and notes and "no `captureBackend` slot" in notes[0])
        d, _n = C.chat_image_dir(str(cfg))
        check("unset/no-chat-dir", d is None)
        got, why = C.capture(be, _page(td), Path(td, "out"), "prototype")
        check("unset/no-frames", got == [] and len(why) == 1, repr(why))


def test_only_a_valid_png_counts():
    """Four arms. Only a real PNG of the requested size is accepted."""
    with tempfile.TemporaryDirectory() as td:
        page, out = _page(td), Path(td, "out")
        got, why = C.capture(_be(td, "ok"), page, out, "prototype")
        check("png/real-capture-accepted", len(got) == 2 and not why, "%r %r" % (got, why))
        check("png/dimensions-asserted-on-disk",
              [C.png_size(g["path"]) for g in got] == [(390, 844), (1280, 900)])

        got, why = C.capture(_be(td, "nothing"), page, out, "prototype")
        check("png/exit-0-writing-nothing-refused", not got, repr(got))
        check("png/exit-0-reason-stated", all("no valid PNG" in r for r in why), repr(why))

        got, why = C.capture(_be(td, "truncated"), page, out, "prototype")
        check("png/truncated-refused", not got and all("no valid PNG" in r for r in why),
              repr(why))
        check("png/truncated-file-not-left-behind",
              not Path(out, "prototype-phone.png").exists(),
              "a rejected capture that leaves its file behind lets the NEXT run read a "
              "stale frame as this run's")

        got, why = C.capture(_be(td, "ignores-size"), page, out, "prototype")
        check("png/wrong-size-refused", not got, repr(got))
        check("png/wrong-size-reason-names-both",
              any("800x600" in r and "390x844" in r for r in why), repr(why))
        check("png/wrong-size-blames-the-template",
              any("drops {width}/{height}" in r for r in why), repr(why))
        # PAIRED: an exact-multiple mismatch is a DIFFERENT diagnosis. Sending a
        # retina-capturing author to inspect a placeholder that is in fact correct is a
        # refusal whose reason is wrong, which is worse than one that is merely strict.
        got, why = C.capture(
            {"screenshot": "python3 %s dpr {url} {out} {width} {height}" % _stub(td)},
            page, out, "prototype")
        check("png/dpr-refused", not got, repr(got))
        check("png/dpr-named-as-dpr",
              any("device-pixel-ratio 2" in r for r in why), repr(why))
        check("png/dpr-does-not-blame-the-template",
              not any("drops {width}/{height}" in r for r in why), repr(why))


def test_stderr_noise_is_not_failure():
    """The measured real-world case: dbus noise on stderr, exit 0, a correct PNG."""
    with tempfile.TemporaryDirectory() as td:
        got, why = C.capture(_be(td, "noisy"), _page(td), Path(td, "out"), "prototype")
        check("stderr/noisy-run-accepted", len(got) == 2 and not why, "%r %r" % (got, why))
        # PAIRED: the same reader must still refuse a run that wrote nothing. Without
        # this, "ignore stderr" and "ignore everything" are indistinguishable.
        got2, why2 = C.capture(_be(td, "nothing"), _page(td), Path(td, "out"), "prototype")
        check("stderr/paired-negative-still-refused", not got2 and why2)


def test_utf8_is_required_before_capture():
    """Paired: a page declaring utf-8 captures; the same page without it is refused."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td, "out")
        good, bad = _page(td, "good.html"), _page(td, "bad.html", charset=False)
        check("utf8/predicate-positive", C.declares_utf8(good))
        check("utf8/predicate-negative", not C.declares_utf8(bad))
        got, _why = C.capture(_be(td, "ok"), good, out, "ok")
        check("utf8/declared-captures", len(got) == 2, repr(got))
        got, why = C.capture(_be(td, "ok"), bad, out, "nope")
        check("utf8/undeclared-refused", not got, repr(got))
        check("utf8/reason-stated", any("declares no UTF-8" in r for r in why), repr(why))
        check("utf8/nothing-written", not Path(out, "nope-phone.png").exists(),
              "a page flow refused to capture still produced a file")
        # Variants a browser accepts must not be refused: the predicate is about the
        # page being readable, not about one spelling.
        for variant in ('<meta charset=UTF-8>', "<meta charset='utf8'>",
                        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">'):
            p = Path(td, "v.html")
            p.write_text("<!doctype html>" + variant, encoding="utf-8")
            check("utf8/accepts %s" % variant[:28], C.declares_utf8(p))


def test_degrades_loudly():
    """Three arms — unset, command absent, command fails. Each: no image, one reason."""
    with tempfile.TemporaryDirectory() as td:
        page, out = _page(td), Path(td, "out")
        arms = {
            "slot-unset": ({}, "has not set"),
            "not-on-path": ({"screenshot": "flow-no-such-binary-xyzzy {url} {out} "
                                           "{width} {height}"}, "could not be run"),
            "exits-nonzero": (_be(td, "fail"), "no valid PNG"),
        }
        for name, (backend, needle) in arms.items():
            got, why = C.capture(backend, page, out, "prototype")
            check("degrade/%s-no-frames" % name, not got, repr(got))
            check("degrade/%s-states-a-reason" % name,
                  bool(why) and any(needle in r for r in why), repr(why))
            # And the hand-off is unchanged: a degraded capture never touches the line.
            check("degrade/%s-handoff-byte-identical" % name,
                  A.render_local_line("walkthrough", ".flow/report.html")
                  == V160_WALKTHROUGH_LOCAL)


def test_closed_vocabulary():
    """Accepted at validate AND at render for the known four; refused for anything else.

    Both layers, because `validate` passing while `render` refuses is the exact
    "passes check, fails at the call site" defect `render_template` was extracted to
    remove — and the shared function is what this reuses rather than a third copy.
    """
    good = {"screenshot": "shot --size {width}x{height} --out {out} {url}"}
    check("vocab/four-accepted-at-validate", C.validate(good)["usable"])
    argv, err = C.render(good, "screenshot",
                         {"url": "file:///a.html", "out": "/tmp/a.png",
                          "width": 390, "height": 844})
    check("vocab/four-accepted-at-render", err is None and argv is not None, repr(err))
    check("vocab/values-substituted",
          argv == ["shot", "--size", "390x844", "--out", "/tmp/a.png", "file:///a.html"],
          repr(argv))

    unknown = {"screenshot": "shot {url} {out} {width} {height} {selector}"}
    check("vocab/unknown-refused-at-validate", not C.validate(unknown)["usable"])
    _a, err = C.render(unknown, "screenshot",
                       {"url": "file:///a", "out": "/o", "width": 1, "height": 2})
    check("vocab/unknown-refused-at-render",
          err is not None and "unknown placeholder" in err, repr(err))

    amp = {"screenshot": "shot {url} {out} {width} {height} & disown"}
    check("vocab/operator-refused-at-validate", not C.validate(amp)["usable"])
    _a, err = C.render(amp, "screenshot",
                       {"url": "file:///a", "out": "/o", "width": 1, "height": 2})
    check("vocab/operator-refused-at-render",
          err is not None and "shell operator" in err, repr(err))

    for missing in ("shot {url} {out} {width}", "shot {url} {out}", "shot {out} {width} {height}"):
        check("vocab/incomplete-refused: %s" % missing,
              not C.validate({"screenshot": missing})["usable"])

    # The policy is the SHARED one, not a private copy: refusing rather than escaping
    # an unsafe VALUE is `render_template`'s rule and must hold here unchanged.
    _a, err = C.render(good, "screenshot",
                       {"url": "file:///a", "out": "/tmp/a b.png", "width": 1, "height": 2})
    check("vocab/unsafe-value-refused-not-escaped",
          err is not None and "outside the safe set" in err, repr(err))
    check("vocab/no-second-copy-of-the-policy",
          "render_template" in LIB.read_text(encoding="utf-8"),
          "this adapter must CALL dispatch_backend.render_template, not re-derive it")


def test_only_frames_in_the_commit():
    """Paired: a committed frame renders; staged-but-uncommitted and pre-dating do not."""
    with tempfile.TemporaryDirectory() as td:
        root = _repo(td)
        d = root / "dev-docs" / "pr-frames" / "feat-empty-feed"
        d.mkdir(parents=True)
        for n, (w, h) in (("prototype-phone.png", (390, 844)),
                          ("prototype-desktop.png", (1280, 900))):
            (d / n).write_bytes(_png(w, h))
        PRE = _head(root)
        _git(["add", "dev-docs/pr-frames"], root)
        _git(["commit", "-qm", "frames"], root)
        SHA = _head(root)

        ok = A.render_frames_from_captures("dev-docs/visual-history.html",
                                           "feat/empty_feed", SHA, str(root),
                                           "acme/app", "false")
        check("commit/two-images", ok.count("![") == 2, ok)
        check("commit/pinned-to-full-sha",
              len(re.findall(r"/%s/" % SHA, ok)) == 2, ok)

        # STAGED but not committed -> absent. `git ls-files` would have said yes.
        (d / "prototype-phone.png").write_bytes(_png(390, 844))
        (d / "draft-phone.png").write_bytes(_png(390, 844))
        _git(["add", "dev-docs/pr-frames/feat-empty-feed/draft-phone.png"], root)
        staged = A.render_frames_from_captures("dev-docs/visual-history.html",
                                               "feat/empty_feed", SHA, str(root),
                                               "acme/app", "false")
        check("commit/staged-not-committed-excluded", "draft-phone" not in staged, staged)
        check("commit/committed-still-there", staged.count("![") == 2, staged)
        (d / "draft-phone.png").unlink()
        _git(["rm", "-q", "--cached",
              "dev-docs/pr-frames/feat-empty-feed/draft-phone.png"], root)

        # A sha PREDATING the frames -> nothing, because the predicate reads the same
        # ref the URL names.
        early = A.render_frames_from_captures("dev-docs/visual-history.html",
                                              "feat/empty_feed", PRE, str(root),
                                              "acme/app", "false")
        check("commit/sha-predating-omits", "![" not in early, early)
        check("commit/sha-predating-says-why", "not in the commit" in early, early)

        # A file the capture engine did not write is never a row.
        (d / "notes.txt").write_text("x", encoding="utf-8")
        (d / "random.png").write_bytes(_png(10, 10))
        _git(["add", "dev-docs/pr-frames"], root)
        _git(["commit", "-qm", "junk"], root)
        SHA2 = _head(root)
        strict = A.render_frames_from_captures("dev-docs/visual-history.html",
                                               "feat/empty_feed", SHA2, str(root),
                                               "acme/app", "false")
        check("commit/non-frame-files-ignored",
              "notes.txt" not in strict and "random.png" not in strict
              and strict.count("![") == 2, strict)


def test_own_pr_frames_only():
    """Two per-PR directories committed; each branch sees exactly its own."""
    with tempfile.TemporaryDirectory() as td:
        root = _repo(td)
        for slug in ("feat-a", "feat-b"):
            d = root / "dev-docs" / "pr-frames" / slug
            d.mkdir(parents=True)
            for n, (w, h) in (("prototype-phone.png", (390, 844)),
                              ("prototype-desktop.png", (1280, 900))):
                (d / n).write_bytes(_png(w, h))
        _git(["add", "-A"], root)
        _git(["commit", "-qm", "both"], root)
        SHA = _head(root)

        a = A.render_frames_from_captures("dev-docs/visual-history.html", "feat/a", SHA,
                                          str(root), "acme/app", "false")
        check("own/a-sees-two", a.count("![") == 2, a)
        check("own/a-names-no-b", "feat-b" not in a, a)
        b = A.render_frames_from_captures("dev-docs/visual-history.html", "feat/b", SHA,
                                          str(root), "acme/app", "false")
        check("own/b-names-no-a", "feat-a" not in b and b.count("![") == 2, b)
        # The guard is the DIRECTORY, so it holds even for a branch with no directory.
        c = A.render_frames_from_captures("dev-docs/visual-history.html", "feat/c", SHA,
                                          str(root), "acme/app", "false")
        check("own/unknown-branch-sees-nothing",
              "![" not in c and "feat-a" not in c and "feat-b" not in c, c)
        # A detached HEAD (empty branch) must never resolve to a shared directory.
        det = A.render_frames_from_captures("dev-docs/visual-history.html", "", SHA,
                                            str(root), "acme/app", "false")
        check("own/detached-head-refuses",
              "![" not in det and "no per-PR frame directory" in det, det)
        # The writer and the reader must call ONE slug function: two copies agree today
        # and diverge silently, because an empty read renders as the ordinary "no frames
        # to show" line. Asserted as the IMPORT plus behavioural agreement -- an identity
        # check would be comparing two separate importlib loads of the same file, which
        # is false for a correct implementation.
        src = ENGINE.read_text(encoding="utf-8")
        check("own/slug-is-imported-not-rederived",
              "from capture_frames import" in src and "branch_slug" in src, "")
        check("own/no-private-slug-regex-in-the-reader",
              'sub(r"[^a-z0-9]+"' not in src,
              "a second slugifier in the reader is the fan-out class; it must import one")
        for b in ("feat/empty_feed", "conductor/chat-and-pr-screenshots", "", "///",
                  "../../etc/passwd", "Feature/ABC-123_x"):
            check("own/slug-agrees-on %r" % b, A.branch_slug(b) == C.branch_slug(b),
                  "%r vs %r" % (A.branch_slug(b), C.branch_slug(b)))


def test_private_fails_closed():
    """Three arms: --private false | true | auto-with-gh-unreachable."""
    with tempfile.TemporaryDirectory() as td:
        root = _repo(td)
        d = root / "dev-docs" / "pr-frames" / "feat-a"
        d.mkdir(parents=True)
        for n, (w, h) in (("prototype-phone.png", (390, 844)),
                          ("prototype-desktop.png", (1280, 900))):
            (d / n).write_bytes(_png(w, h))
        _git(["add", "-A"], root); _git(["commit", "-qm", "f"], root)
        SHA = _head(root)

        pub = A.render_frames_from_captures("dev-docs/visual-history.html", "feat/a", SHA,
                                            str(root), "acme/app", "false")
        check("private/public-arm-inlines", pub.count("![") == 2
              and pub.count("https://raw.githubusercontent.com/") == 2, pub)

        priv = A.render_frames_from_captures("dev-docs/visual-history.html", "feat/a", SHA,
                                             str(root), "acme/app", "true")
        check("private/no-raw-host", "raw.githubusercontent.com" not in priv, priv)
        check("private/no-image-syntax", "![" not in priv, priv)
        check("private/two-blob-links", priv.count("/blob/%s/" % SHA) == 2, priv)
        check("private/names-the-sha-pin", "Pinned to" in priv and SHA[:7] in priv, priv)

        # gh ABSENT with --private auto. Driven as a SUBPROCESS with its own `env=`,
        # because mutating os.environ["PATH"] in-process is a global with restore logic
        # that does not belong in a test of a library a consumer imports.
        #
        # `git` is symlinked IN deliberately. The first cut emptied PATH entirely, so
        # `git cat-file` failed, no frame was tracked, and the arm went green on the
        # "nothing is in the commit" branch -- it would have passed with the visibility
        # gate deleted. The arm has to reach the visibility decision to measure it.
        bin_ = Path(td, "gh-less-bin"); bin_.mkdir(exist_ok=True)
        import shutil as _sh
        _gitbin = _sh.which("git")
        if _gitbin:
            try:
                os.symlink(_gitbin, bin_ / "git")
            except OSError:
                pass
        check("private/gh-absent-arm-can-see-git", (bin_ / "git").exists(),
              "without git on PATH this arm measures trackedness, not visibility")
        env = dict(os.environ, PATH=str(bin_))
        r = subprocess.run(
            [sys.executable, str(ENGINE), "frames", "--source", "captures",
             "--visual-history", "dev-docs/visual-history.html", "--branch", "feat/a",
             "--sha", SHA, "--repo", "acme/app", "--root", str(root)],
            capture_output=True, text=True, timeout=60, env=env)
        check("private/gh-absent-exits-clean", r.returncode == 0, r.stderr[:300])
        check("private/gh-absent-no-inline-images", "![" not in r.stdout, r.stdout)
        check("private/gh-absent-no-raw-host",
              "raw.githubusercontent.com" not in r.stdout, r.stdout)
        check("private/gh-absent-says-it-could-not-tell",
              "Couldn't tell whether this repo is public" in r.stdout, r.stdout)
        check("private/policy-is-shared-not-copied",
              ENGINE.read_text(encoding="utf-8").count("raw.githubusercontent.com/%s/%s/%s")
              == 1,
              "the public/private embed policy must exist ONCE; a second copy is how one "
              "source fails open while the other fails closed")


def test_curated_record_untouched():
    """Captures never reach visual-history-assets/, paired with where they DO land."""
    with tempfile.TemporaryDirectory() as td:
        root = _repo(td)
        curated = root / "dev-docs" / "visual-history-assets"
        curated.mkdir()
        (curated / "kept.png").write_bytes(_png(10, 10))
        before = sorted(q.name for q in curated.iterdir())
        vh_before = Path(root, "dev-docs", "visual-history.html").read_bytes()

        out = A.captures_dir("dev-docs/visual-history.html", "feat/empty_feed")
        check("curated/dir-is-pr-frames",
              out == "dev-docs/pr-frames/feat-empty-feed", repr(out))
        check("curated/dir-is-not-the-record-assets-dir",
              "visual-history-assets" not in (out or ""), repr(out))
        got, why = C.capture(_be(td, "ok"), _page(td), root / out, "prototype")
        check("curated/positive-frames-landed", len(got) == 2, "%r %r" % (got, why))
        check("curated/assets-unchanged",
              sorted(q.name for q in curated.iterdir()) == before)
        check("curated/record-file-unchanged",
              Path(root, "dev-docs", "visual-history.html").read_bytes() == vh_before)
        check("curated/frames-are-in-the-per-pr-dir",
              sorted(q.name for q in (root / out).iterdir())
              == [C.SIDECAR, "prototype-desktop.png", "prototype-phone.png"],
              repr(sorted(q.name for q in (root / out).iterdir())))


def test_auto_never_retires_the_record():
    """THE BLOCKER v1.65.0's own staff-review caught, pinned so it cannot come back.

    `/flow:ship` picks its source from whether the capture ADAPTER validates, which says
    nothing about whether anything was captured. With `--source captures` that silently
    replaced a consumer's curated visual-history frames with "No frames to show" the
    moment they configured an adapter — and both skills' prose promised the opposite in
    the same diff. The fall-through lives in the engine; this is the arm that proves it.
    """
    with tempfile.TemporaryDirectory() as td:
        root = _repo(td)
        # A CURATED record with a real committed frame, and NO captures for this branch.
        assets = root / "dev-docs" / "visual-history-assets"
        assets.mkdir()
        (assets / "before.png").write_bytes(_png(10, 10))
        Path(root, "dev-docs", "visual-history.html").write_text(
            '<!doctype html><html><body><article class="vh-entry"><h2>X</h2>'
            '<div class="meta">#1<span class="sep">·</span>2026-10-06'
            '<span class="sep">·</span><code>feat/a</code></div><div class="ba">'
            '<figure><figcaption>Before — empty feed</figcaption>'
            '<img src="visual-history-assets/before.png" '
            'alt="blank gray panel with no call to action"></figure></div>'
            '</article></body></html>', encoding="utf-8")
        _git(["add", "-A"], root); _git(["commit", "-qm", "curated"], root)
        SHA = _head(root)

        auto = A.render_frames_auto("dev-docs/visual-history.html", "feat/a", SHA,
                                    str(root), "acme/app", "false")
        check("auto/falls-back-to-the-curated-record",
              auto.count("![") == 1 and "visual-history-assets/before.png" in auto,
              "a configured adapter with zero captures must NOT retire the record: %s" % auto)
        check("auto/keeps-the-records-real-alt",
              "blank gray panel with no call to action" in auto, auto)
        # Paired: `captures` stays strict, so the fall-through is a property of `auto`
        # alone rather than a behaviour nobody can test in isolation.
        strict = A.render_frames_from_captures("dev-docs/visual-history.html", "feat/a",
                                               SHA, str(root), "acme/app", "false")
        check("auto/strict-captures-still-omits", "![" not in strict, strict)

        # And when captures DO exist, auto prefers them.
        d = root / "dev-docs" / "pr-frames" / "feat-a"
        d.mkdir(parents=True)
        for n, (w, h) in (("prototype-phone.png", (390, 844)),
                          ("prototype-desktop.png", (1280, 900))):
            (d / n).write_bytes(_png(w, h))
        _git(["add", "-A"], root); _git(["commit", "-qm", "frames"], root)
        SHA2 = _head(root)
        auto2 = A.render_frames_auto("dev-docs/visual-history.html", "feat/a", SHA2,
                                     str(root), "acme/app", "false")
        check("auto/prefers-captures-when-present",
              auto2.count("![") == 2 and "pr-frames" in auto2, auto2)

        # The SHIPPED call sites must pass `auto`. Without this the engine is correct and
        # the composed surface is still broken — the layer-mismatch corollary.
        for name, f in (("ship", SHIP), ("ship-spike", SPIKE)):
            txt = f.read_text(encoding="utf-8")
            check("auto/%s-passes-auto-not-captures" % name,
                  "SRC=auto" in txt and "SRC=captures" not in txt, name)


def test_alt_text_says_what_the_frame_shows():
    """The alt is the whole content for a reader who cannot see the image.

    "prototype at phone width, 390×844" names the FRAME and says nothing about the page.
    The sidecar carries the captured page's own <title>, read back out of the commit, so
    the alt can lead with what the surface is.
    """
    with tempfile.TemporaryDirectory() as td:
        root = _repo(td)
        d = root / "dev-docs" / "pr-frames" / "feat-a"
        got, why = C.capture(_be(td, "ok"), _page(td, title="Activity feed — empty state"),
                             d, "prototype")
        check("alt/capture-succeeded", len(got) == 2, "%r %r" % (got, why))
        check("alt/sidecar-written", (d / C.SIDECAR).is_file())
        _git(["add", "-A"], root); _git(["commit", "-qm", "f"], root)
        SHA = _head(root)

        out = A.render_frames_from_captures("dev-docs/visual-history.html", "feat/a", SHA,
                                            str(root), "acme/app", "false")
        check("alt/leads-with-the-page",
              out.count("![Activity feed — empty state —") == 2, out)
        check("alt/still-names-the-viewport",
              "390×844" in out and "1280×900" in out, out)
        check("alt/says-it-is-the-first-screen", out.count("irst screen") >= 4,
              "captions say `First screen`, alts say `first screen` — both must, or a "
              "reader concludes the frame is the whole page: %s" % out)
        check("alt/never-empty", "![](" not in out, out)

        # DEGRADES, not breaks: with no sidecar in the commit the alt names the label.
        # Read from the COMMIT, so deleting it from the working tree changes nothing —
        # which is the projection discipline, asserted rather than assumed.
        (d / C.SIDECAR).unlink()
        same = A.render_frames_from_captures("dev-docs/visual-history.html", "feat/a",
                                             SHA, str(root), "acme/app", "false")
        check("alt/reads-the-commit-not-the-worktree", same == out,
              "deleting the sidecar from the working tree changed the render, so the "
              "renderer is reading the session rather than the commit")
        _git(["rm", "-q", "--cached", "dev-docs/pr-frames/feat-a/%s" % C.SIDECAR], root)
        _git(["commit", "-qm", "drop sidecar"], root)
        SHA2 = _head(root)
        thin = A.render_frames_from_captures("dev-docs/visual-history.html", "feat/a",
                                             SHA2, str(root), "acme/app", "false")
        check("alt/degrades-to-the-label", thin.count("![prototype —") == 2, thin)
        check("alt/degraded-is-still-never-empty", "![](" not in thin, thin)


def test_frames_dir_is_composed_once():
    """The writer and the reader must resolve the SAME per-PR directory.

    This is the one contract both halves agree on, and it was briefly a shell literal in
    two SKILL.md files plus a Python constant in the renderer. The divergence would have
    been silent: the reader's "committed no captured frames" line is indistinguishable
    from a correct skip. Pinned at the COMPOSED layer — the shell's own command — not
    just in the engine.
    """
    for vh, br, want in (("dev-docs/visual-history.html", "feat/empty_feed",
                          "dev-docs/pr-frames/feat-empty-feed"),
                         ("core-docs/visual-history.html", "conductor/x-y",
                          "core-docs/pr-frames/conductor-x-y"),
                         ("visual-history.html", "a/b", "pr-frames/a-b")):
        check("frames-dir/engine %s" % br, C.frames_dir(vh, br) == want,
              repr(C.frames_dir(vh, br)))
        check("frames-dir/reader-agrees %s" % br, A.captures_dir(vh, br) == want,
              repr(A.captures_dir(vh, br)))
        # The CLI the shell actually calls, driven as the shell calls it.
        r = subprocess.run([sys.executable, str(LIB), "frames-dir",
                            "--visual-history", vh, "--branch", br],
                           capture_output=True, text=True, timeout=30)
        check("frames-dir/cli %s" % br, r.returncode == 0 and r.stdout.strip() == want,
              "%r / %r" % (r.stdout, r.stderr))
    r = subprocess.run([sys.executable, str(LIB), "frames-dir",
                        "--visual-history", "dev-docs/visual-history.html", "--branch", ""],
                       capture_output=True, text=True, timeout=30)
    check("frames-dir/cli-refuses-unsluggable", r.returncode != 0 and not r.stdout.strip(),
          "%r / %r" % (r.stdout, r.stderr))
    # The SHELL must call it rather than compose the path itself.
    ship = SHIP.read_text(encoding="utf-8")
    check("frames-dir/ship-calls-the-engine", 'frames-dir --visual-history' in ship,
          "ship must ask the engine for the directory, not compose `pr-frames/$SLUG`")
    check("frames-dir/ship-composes-no-literal", '/pr-frames/$SLUG' not in ship,
          "a shell literal here is a second copy of the one contract both halves share")


def test_chat_message_budget():
    """ONE image, zero prose cost, and nothing claimed when there is no frame."""
    with tempfile.TemporaryDirectory() as td:
        got, _why = C.capture(_be(td, "ok"), _page(td), Path(td, "out"), "prototype",
                              frames=C.FRAMES[:1])
        check("chat/only-one-frame-captured", len(got) == 1 and got[0]["name"] == "phone",
              repr(got))
        frame = got[0]["path"]

        line = A.render_local_line("prototype", "/abs/p.presented.html",
                                   "https://ws.example.test/p.html",
                                   "anyone in the acme-eng org", frame)
        check("chat/exactly-one-image", line.count("![") == 1, line)
        check("chat/alt-is-never-empty", "![](" not in line, line)
        check("chat/alt-names-the-width", "phone width (390×844)" in line, line)
        # The image costs no prose EXCEPT one scoping clause, and that clause is the
        # point: the frame is of `prototype.html`, which has no dock, so a reader seeing
        # a dock-free picture under a sentence about a dock would hunt for it. Assert
        # the difference is EXACTLY that clause — not "roughly the same", which would
        # let any future prose creep in unnoticed.
        prose = line.split("\n\n![")[0]
        bare = A.render_local_line("prototype", "/abs/p.presented.html",
                                   "https://ws.example.test/p.html",
                                   "anyone in the acme-eng org")
        SCOPE = " — it is in the page itself, not in the frame below"
        check("chat/prose-differs-by-exactly-the-dock-scoping",
              prose.replace(SCOPE, "") == bare,
              "the image changed the prose by more than the dock-scoping clause:\n%r\nvs\n%r"
              % (prose, bare))
        check("chat/scoping-clause-is-present-with-a-frame", SCOPE in prose, prose)
        check("chat/scoping-clause-absent-without-a-frame", SCOPE not in bare, bare)
        words = len(re.findall(r"\S+", prose))
        check("chat/prose-within-budget", words <= 55, "%d words: %s" % (words, prose))
        check("chat/link-is-a-bare-autolink-not-a-code-span",
              "`https://" not in line, line)

        # No frame -> no claim, and the line is unchanged.
        none = A.render_local_line("prototype", "/abs/p.presented.html",
                                   chat_image=str(Path(td, "missing.png")))
        check("chat/missing-frame-claims-nothing", "![" not in none, none)
        check("chat/missing-frame-line-unchanged",
              none == A.render_local_line("prototype", "/abs/p.presented.html"))
        # And never in a PR body, where a local path is a broken image.
        wrong = A.render_local_line("walkthrough", "/abs/r.html", chat_image=frame)
        check("chat/refused-on-the-pr-body-handoff", "![" not in wrong, wrong)


def test_capture_step_states_a_reason_on_every_path():
    """`/flow:ship` §5d, driven as the SHELL — not as the Python under it.

    This pins the COMPOSED layer. Every other arm in this harness drives a Python
    entry point; §5d is a shell block that decides whether this PR gets frames at all,
    and `general.md` item 4's corollary is explicit that a criterion verified one layer
    below the surface it describes can be green while the surface is false. So the block
    is extracted from the shipped SKILL.md and run.

    The four skip arms must each state their OWN reason. That is not stylistic: two of
    them were briefly collapsed into one message, and the result was a confident
    "a detached HEAD reads as empty" printed for a missing capture engine — a diagnosis
    of a condition nobody had measured.
    """
    import shutil
    block = _extract_sh_block(SHIP, "### 5d. Capture this PR's frames")
    check("5d/block-extracted", block is not None and "pr-frames" in (block or ""),
          "could not find §5d's shell block — re-key this extraction, do not drop it")
    if not block:
        return

    def run(td, *, significant=True, target=True, engine=True, detached=False,
            plan=True, buffer=True):
        root = Path(td, "r"); shutil.rmtree(root, ignore_errors=True)
        (root / "dev-docs").mkdir(parents=True)
        (root / ".flow" / "prototypes" / "p").mkdir(parents=True)
        _git(["init", "-q", "-b", "main"], root)
        _git(["config", "user.email", "e@v.al"], root); _git(["config", "user.name", "e"], root)
        stub = _stub(td)
        cfg = {"visualHistoryPath": "dev-docs/visual-history.html",
               "verifyFindingsPath": ".flow/f.json", "planPath": "dev-docs/plan.md",
               "captureBackend": {"screenshot":
                   "python3 %s ok {url} {out} {width} {height}" % stub}}
        (root / "flow.config.json").write_text(json.dumps(cfg), encoding="utf-8")
        if buffer:
            (root / ".flow" / "f.json").write_text(
                json.dumps({"metadata": {"visual_significant": bool(significant)}}),
                encoding="utf-8")
        if plan:
            (root / "dev-docs" / "plan.md").write_text("# p\n", encoding="utf-8")
        (root / "dev-docs" / "visual-history.html").write_text("<html></html>", encoding="utf-8")
        if target:
            (root / ".flow" / "prototypes" / "p" / "prototype.html").write_text(
                '<!doctype html><meta charset="utf-8"><title>T</title><p>x</p>',
                encoding="utf-8")
        _git(["add", "-A"], root); _git(["commit", "-qm", "b"], root)
        if detached:
            _git(["checkout", "-q", "--detach"], root)
        else:
            _git(["checkout", "-q", "-b", "feat/a"], root)
        env = dict(os.environ)
        # An absent engine is simulated by pointing the plugin root at nothing AND
        # removing the checkout-relative fallback, which is how §5d resolves `$CF`.
        env["CLAUDE_PLUGIN_ROOT"] = str(FLOW) if engine else str(Path(td, "nope"))
        r = subprocess.run(["sh", "-c", block], cwd=str(root), capture_output=True,
                           text=True, timeout=180, env=env)
        return (r.stdout + r.stderr), root

    with tempfile.TemporaryDirectory() as td:
        # KNOWN POSITIVE FIRST — without it, four "it skipped" assertions are satisfied
        # by a block that can only ever skip (general.md item 4).
        out, root = run(td)
        frames = sorted(q.name for q in
                        (root / "dev-docs/pr-frames/feat-a").iterdir()) \
            if (root / "dev-docs/pr-frames/feat-a").is_dir() else []
        check("5d/positive-captures-two-frames",
              frames == [C.SIDECAR, "prototype-desktop.png", "prototype-phone.png"],
              "the happy path produced %r — every skip assertion below is vacuous if "
              "this block cannot capture at all. out=%s" % (frames, out[-400:]))
        staged = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=str(root),
                                capture_output=True, text=True).stdout
        check("5d/positive-stages-the-frames", "pr-frames/feat-a" in staged, staged)

        arms = {
            "not-significant": (dict(significant=False), "visual_significant=false"),
            "no-engine": (dict(engine=False), "capture engine not found"),
            "no-target": (dict(target=False), "no prototype and no walkthrough"),
            "detached-head": (dict(detached=True), "could not derive a per-PR directory"),
        }
        seen = {}
        for name, (kw, needle) in arms.items():
            out, root = run(td, **kw)
            check("5d/%s-states-its-reason" % name, needle in out,
                  "expected %r in:\n%s" % (needle, out[-500:]))
            check("5d/%s-captures-nothing" % name,
                  not (root / "dev-docs/pr-frames").exists(),
                  "a skip arm wrote frames anyway")
            seen[name] = needle
        # The reasons must be DISTINCT. Collapsing two of these produced a confident
        # diagnosis of a condition nobody measured, which is the defect this pins.
        check("5d/every-arm-has-its-own-reason", len(set(seen.values())) == len(arms),
              repr(seen))

        # THE FIFTH PATH, found by the second coverage audit: no plan doc. §5d then
        # computes significance from the DIFF ALONE, so a plan declaring
        # `Visual-walk: N/A` cannot suppress capture — the exact suppression #183
        # shipped — reachable through a misconfigured `planPath` rather than through
        # the plan. The behaviour kept is warn-and-continue, matching §5c and §7b
        # (making §5d uniquely refuse would be a new divergence between three sites
        # that read the same verdict); what this pins is that the warning is LOUD, so
        # a plan-less verdict is never silently taken for a plan-informed one.
        out, root = run(td, plan=False, buffer=False)
        check("5d/no-plan-doc-warns-loudly", "running WITHOUT plan context" in out, out[-400:])
        check("5d/no-plan-doc-names-the-path",
              "no plan doc at" in out, out[-400:])
        # The warning is ADDITIVE, not a substitute: with no buffer and no plan the
        # heuristic correctly also reports not-significant, so both lines appear. What
        # must hold is that the plan-less warning is its own sentence and never doubles
        # as one of the skip reasons — a reader has to be able to tell "I skipped" from
        # "I decided without the plan". (The first cut asserted the skip reason was
        # ABSENT, which was wrong about the code, not about the contract.)
        check("5d/no-plan-warning-is-its-own-sentence",
              "running WITHOUT plan context" not in " ".join(seen.values()),
              "the plan-less warning collides with a skip reason: %r" % seen)
        check("5d/no-plan-still-reports-the-significance-verdict",
              any(n in out for n in seen.values()),
              "a plan-less run must still say what it decided, not fall silent: %s"
              % out[-400:])


def test_ignore_state_is_a_tristate_and_reaches_a_human():
    """Three states, and "could not measure" is never reported as "not ignored".

    Found undeclared by the scoped coverage re-run over the slice the full pass could
    not read — and both halves of this behaviour were themselves review-round fixes:
    the note could not reach a human because its only call site swallowed stderr, and
    the predicate went silent on its own "could not measure".
    """
    import shutil
    with tempfile.TemporaryDirectory() as td:
        def chat_dir_json(root, slot):
            (root / "flow.config.json").write_text(
                json.dumps({"chatImagePath": slot}), encoding="utf-8")
            r = subprocess.run([sys.executable, str(LIB), "chat-dir", "--json",
                                "--config", str(root / "flow.config.json")],
                               cwd=str(root), capture_output=True, text=True, timeout=60)
            return json.loads(r.stdout), r.stderr

        repo = Path(td, "repo"); repo.mkdir()
        _git(["init", "-q", "-b", "main"], repo)
        (repo / ".gitignore").write_text(".flow/\n", encoding="utf-8")
        (repo / "docs").mkdir()

        got, err = chat_dir_json(repo, ".flow/chat-frames")
        check("ignore/true-when-ignored", got["ignored"] is True, repr(got))
        check("ignore/true-emits-no-note", not got["notes"], repr(got["notes"]))

        got, err = chat_dir_json(repo, "docs/frames")
        check("ignore/false-when-tracked", got["ignored"] is False, repr(got))
        check("ignore/false-names-the-directory-and-the-risk",
              any("docs/frames" in n and "committed by accident" in n
                  for n in got["notes"]), repr(got["notes"]))

        # NOT a git repo: the state cannot be measured. `None`, never `False` — a
        # confident "is not git-ignored" for something nobody measured is the
        # unverified-claim class the whole engine exists to refuse.
        bare = Path(td, "bare"); bare.mkdir()
        got, err = chat_dir_json(bare, "frames")
        check("ignore/null-when-unmeasurable", got["ignored"] is None, repr(got))
        check("ignore/null-is-not-false", got["ignored"] is not False, repr(got))
        check("ignore/null-says-it-could-not-determine",
              any("could not determine" in n for n in got["notes"]), repr(got["notes"]))

        # PAIRED POSITIVE — the two shipped consumers must SURFACE it, not re-derive it.
        proto = PROTO.read_text(encoding="utf-8")
        check("ignore/prototype-does-not-swallow-the-note",
              '"$CF" chat-dir 2>/dev/null' not in proto,
              "the only shipped caller discarding stderr makes this note unreachable — "
              "which is exactly how it shipped unreadable once already")
        doc = DOCTOR.read_text(encoding="utf-8")
        check("ignore/doctor-reads-the-engine", "chat-dir --json" in doc)
        check("ignore/doctor-does-not-rederive",
              'git check-ignore -q "$CIP"' not in doc,
              "one predicate, one copy — a second one cannot be a tristate by accident")
        # The FOURTH outcome, one axis up from the tristate: the REPORT itself is
        # unparseable (engine missing, python3 absent). Before the fix this printed a
        # confident "chatImagePath unset", because an empty string pipes through jq with
        # exit 0 — "could not read" reported as "is not configured", which is the same
        # could-not-measure collapse the tristate below it exists to prevent.
        blk = _extract_sh_block(DOCTOR, "**Check 2.14")
        check("ignore/doctor-block-extracted", blk is not None and "chat-dir --json" in (blk or ""))
        if blk:
            (repo / "flow.config.json").write_text(
                json.dumps({"captureBackend": {"screenshot": "c {url} {out} {width} {height}"},
                            "chatImagePath": ".flow/chat-frames"}), encoding="utf-8")
            env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(Path(td, "no-such-plugin-root")))
            r = subprocess.run(["sh", "-c", blk], cwd=str(repo), capture_output=True,
                               text=True, timeout=120, env=env)
            o = r.stdout + r.stderr
            check("ignore/doctor-skips-on-an-unreadable-report",
                  "[SKIP] chatImagePath" in o, o[-400:])
            check("ignore/doctor-does-not-claim-unset-on-an-unreadable-report",
                  "chatImagePath unset" not in o,
                  "doctor reported the slot as unset for a report it could not read: %s"
                  % o[-400:])
        for arm in ("[WARN] chatImagePath", "[SKIP] chatImagePath", "[PASS] chatImagePath"):
            check("ignore/doctor-renders %s" % arm, arm in doc,
                  "doctor must render all three states, or the tristate collapses at "
                  "the surface a human reads")


def test_captured_frames_are_not_their_own_evidence():
    """PAIRED: flow's own pr-frames do not signal; a consumer's own asset still does.

    `/flow:ship` §5d commits PNGs into `pr-frames/<slug>/`, but it runs ONLY when
    `visual_significant` is already true — so counting those frames as an asset signal
    makes flow's own output the reason its own gate fires. Circular: the frames exist
    because the answer was true, so they cannot be why it is true. Found by running the
    §5d trigger's three arms in sequence after #183, where arm 3's frames made arm 2 (an
    explicit `Visual-walk: N/A`) read as visually significant on the asset path.

    The exclusion is a LITERAL in `visual-significance.py` rather than an import — that
    file is a `sensitivePaths` gate whose one existing cross-module import failing
    silently is what #183 shipped to fix. So the two definitions are pinned to agree
    HERE instead, and this check fails if either side moves.
    """
    vs = (FLOW / "skills" / "verify-build" / "lib" / "visual-significance.py")
    src = vs.read_text(encoding="utf-8")
    check("circular/exclusion-present", "FLOW_CAPTURED_FRAMES" in src)

    # THE DURABLE ARM: drive the shipped script and compare the VERDICT. The first cut
    # asserted the literal `"not FLOW_CAPTURED_FRAMES.search(p)" in src` — which went
    # green with the filter applied at ONE of the two sites that decide the verdict, so
    # a captured frame still flipped a pure-refactor change to significant while the
    # already-applied filter had removed that path from the signals list. The verdict
    # flipped with nothing naming the file that flipped it, and the pin could not tell.
    # An outcome test needs no list of sites and cannot go stale as sites are added
    # (general.md item 4: pin the decision, not a string that currently implies it).
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td, "flow.config.json")
        cfg.write_text(json.dumps({"uiSurface": True,
                                   "visualFilePatterns": r"\.(css|html)$"}),
                       encoding="utf-8")
        empty = Path(td, "empty.diff"); empty.write_text("", encoding="utf-8")
        frame = C.frames_dir("dev-docs/visual-history.html", "feat/a") + "/prototype-phone.png"

        def verdict(rows):
            f = Path(td, "files.txt")
            f.write_text("".join(r + "\n" for r in rows), encoding="utf-8")
            r = subprocess.run([sys.executable, str(vs), "--config", str(cfg),
                                "--files-from", str(f), "--diff-from", str(empty)],
                               capture_output=True, text=True, timeout=60)
            try:
                return json.loads(r.stdout)["visual_significant"]
            except (ValueError, KeyError):
                return "UNPARSEABLE: %s / %s" % (r.stdout[:200], r.stderr[:200])

        rename_only = ["R100\tsrc/old.css\tsrc/new.css"]
        # KNOWN POSITIVE first: the instrument must be able to return both answers, or a
        # "false" below proves nothing (general.md item 4).
        check("circular/instrument-can-say-true",
              verdict(rename_only + ["A\tsrc/img/hero.png"]) is True,
              "a consumer's own added asset must still read as visually significant — "
              "without this the two assertions below pass for a filter that swallows "
              "everything")
        check("circular/baseline-rename-only-is-false",
              verdict(rename_only) is False, "the baseline arm is not false")
        check("circular/flows-own-frame-does-not-flip-the-verdict",
              verdict(rename_only + ["A\t" + frame]) is False,
              "adding ONLY flow's own captured frame flipped the verdict — the "
              "exclusion is missing at one of the sites that decide it")
        check("circular/consumer-asset-in-a-pr-frames-named-dir-still-signals",
              verdict(rename_only + ["A\tdocs/my-pr-frames-guide.png"]) is True,
              "the exclusion swallowed a path that is real evidence")
        # THE GATE BYPASS, pinned. The first exclusion matched a bare `pr-frames/`
        # segment anywhere, so a contributor who named a directory `pr-frames/` in their
        # own PR silently suppressed the visual gate for a real UI asset — measured by
        # /flow:security-review, and in the expensive polarity (the gate goes quiet).
        # These paths have ONE segment after `pr-frames/`, where the engine always
        # writes two.
        for impostor in ("src/assets/pr-frames/hero.png",
                         "pr-frames/hero.png",
                         "docs/pr-frames/diagram.png"):
            check("circular/not-engine-written-still-signals %s" % impostor,
                  verdict(rename_only + ["A\t" + impostor]) is True,
                  "a path flow's capture engine would never write suppressed the gate — "
                  "a suppression an unrelated contributor can trigger by naming a "
                  "directory is a bypass")
        # And a suppression must NAME what it suppressed: the floor message otherwise
        # reads "diff touches no UI or asset files", which is false for a diff that
        # touched one. An exclusion a report will not name is indistinguishable from a
        # pattern that never matched.
        f = Path(td, "named.txt")
        f.write_text("R100\tsrc/old.css\tsrc/new.css\nA\t" + frame + "\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(vs), "--config", str(cfg),
                            "--files-from", str(f), "--diff-from", str(empty)],
                           capture_output=True, text=True, timeout=60)
        sig = " ".join(json.loads(r.stdout).get("visual_signals", []))
        check("circular/suppression-names-the-files-it-suppressed",
              "excluded as flow's OWN captured frames" in sig and frame in sig, sig)
        check("circular/suppression-does-not-claim-the-files-are-absent",
              "diff touches no UI or asset files" not in sig, sig)
    # The two definitions must name the SAME directory.
    # DOTALL + optional newline: the pattern was re-scoped across two lines when the
    # gate bypass was fixed, and a single-line extraction then found nothing — which
    # would have silently skipped every assertion below it rather than failing. The
    # `check("circular/pattern-found")` guard is what made that loud instead.
    m = re.search(r'FLOW_CAPTURED_FRAMES = re\.compile\(\s*r"(.*?)"\s*\)', src, re.S)
    check("circular/pattern-found", m is not None, src[:200])
    if m:
        check("circular/names-the-shared-directory", C.PR_FRAMES_DIR in m.group(1),
              "the exclusion regex %r no longer names capture_frames.PR_FRAMES_DIR "
              "(%r) — one of the two moved" % (m.group(1), C.PR_FRAMES_DIR))
        rx = re.compile(m.group(1))
        # NEGATIVE: a captured frame is excluded. The probe is BUILT FROM frames_dir()
        # rather than typed as a literal — if the directory composition ever changes
        # shape, a hardcoded probe would keep passing while the exclusion stopped
        # covering what flow actually writes (general.md item 4: pin the decision, not a
        # string that currently implies it).
        for vh in ("dev-docs/visual-history.html", "visual-history.html"):
            probe = C.frames_dir(vh, "feat/a") + "/prototype-phone.png"
            check("circular/flows-frame-excluded %s" % probe, bool(rx.search(probe)),
                  "the exclusion no longer covers the path the capture engine writes")
        # ...and the POSITIVE, without which the exclusion could be widened to
        # everything and every line above would still pass.
        for keep in ("src/img/hero.png", "assets/pr-frames.png",
                     "core-docs/visual-history-assets/before.png",
                     "docs/my-pr-frames-guide.png"):
            check("circular/still-signals %s" % keep, not rx.search(keep),
                  "the exclusion swallowed a path that is real evidence")


def test_no_vendor_token_in_plugin():
    """No host browser is named in any plugin artifact — paired with the positive."""
    # SCOPED to the artifacts this feature introduces, deliberately. The repo-wide
    # host-literal sweep is already owned by run_dispatch_backend_evals.py § 7 over
    # `plugins/flow/lib/` with its own curated literal list and its own exact artifact
    # count -- which is the line that notices a new shared lib. Re-running a broader
    # sweep here would re-litigate decisions made elsewhere (verify-build's SKILL.md
    # names the per-platform MCPs on purpose; `safari` appears inside a measured-client
    # note) and would fail on `main`.
    # BROWSER BINARIES a `screenshot` template might hardcode. Deliberately not a list of
    # every vendor word: `Safari` legitimately appears in two shipped artifacts, and in
    # both cases naming it is the point -- the measured Latin-1 charset fallback that
    # Decision 3 exists for, and `FORBIDDEN_CLIENTS`, which names clients in order to
    # forbid them. A sweep that flagged those would be telling an author to delete the
    # measurement.
    vendor = ("google-chrome", "chromium", "firefox", "msedge", "puppeteer",
              "webkit2png", "wkhtmltoimage", "headlesschrome")
    scanned = 0
    targets = [LIB, SCHEMA, PROTO, SHIP, SPIKE, DOCTOR, ENGINE]
    for f in targets:
        scanned += 1
        txt = f.read_text(encoding="utf-8", errors="replace").lower()
        for v in vendor:
            check("vendor/%s carries no %r" % (f.name, v), v not in txt)
    # A HARD LITERAL, not `len(targets)`: the latter is a tautology in both directions —
    # empty the list and every `v not in txt` assertion vanishes while `0 == 0` passes
    # (general.md item 3, a prohibition satisfiable by deletion). Re-key this number when
    # a target is genuinely added; that is the intended cost.
    check("vendor/scan-covered-every-target", scanned == 7, str(scanned))
    # And the shared-lib sweep that owns `plugins/flow/lib/` must have COUNTED this new
    # file: an exact count is the mechanism, and leaving it stale is how a new lib
    # enters the directory unswept.
    sweep = (HERE / "run_dispatch_backend_evals.py").read_text(encoding="utf-8")
    n_libs = len(list((FLOW / "lib").glob("*.py")))
    check("vendor/shared-lib-sweep-count-bumped",
          ("scanned == %d" % (6 + n_libs)) in sweep,
          "run_dispatch_backend_evals.py § 7 scans 4 SKILL.md + 2 skill libs + every "
          "plugins/flow/lib/*.py (now %d). Its exact count must be bumped with the new "
          "lib, or the sweep silently stops covering the directory." % n_libs)
    # POSITIVE 1: the schema documents a GENERIC example, so the rule above is not
    # satisfied by the slot having no documentation at all.
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    ex = schema["properties"]["captureBackend"]["examples"][0]["screenshot"]
    check("vendor/schema-shows-a-generic-example",
          "{url}" in ex and "{out}" in ex and "{width}" in ex and "{height}" in ex, ex)
    for v in vendor:
        check("vendor/schema-example-names-no-vendor %r" % v, v not in ex.lower())
    # POSITIVE 2: flow's OWN config DOES name a real one, or the feature ships off
    # everywhere and is exercised nowhere (FB-0085).
    cfg = json.loads((REPO / "flow.config.json").read_text(encoding="utf-8"))
    check("vendor/flows-own-config-sets-the-slot",
          isinstance(cfg.get("captureBackend"), dict)
          and bool(cfg["captureBackend"].get("screenshot")), repr(cfg.get("captureBackend")))
    check("vendor/flows-own-config-sets-the-chat-dir",
          isinstance(cfg.get("chatImagePath"), str) and bool(cfg["chatImagePath"]))


def test_schema_declares_the_slots():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    props = schema["properties"]
    check("schema/captureBackend-declared", "captureBackend" in props)
    check("schema/chatImagePath-declared", "chatImagePath" in props)
    check("schema/screenshot-sub-slot",
          "screenshot" in props["captureBackend"]["properties"])
    # The slot-count fan-out is DELIBERATELY NOT RE-CHECKED HERE. It is a real contract,
    # and it is already owned by `run_merge_status_evals.py`, which runs the shared
    # `doctor/lib/slot_count_scan.py` over `plugins/` + `template/` + `README.md` — a
    # strict superset of anything this harness would scan. The private `r"(\d+) slots"`
    # regex that used to sit here was a FOURTH copy of a shape that module's own header
    # documents escaping three ways (a newline wrap, an interposed adjective, a hyphen:
    # `39\n slots`, `39 schema slots`, `39-slot` all evade it), guarding a contract that
    # was already guarded — and its `if doc.is_file()` meant a moved doc registered zero
    # checks and stayed green. One contract, one scanner.


def test_skills_wire_the_capture():
    """The engine is reachable from the three skills that must use it."""
    proto = PROTO.read_text(encoding="utf-8")
    check("wiring/prototype-captures", "capture_frames.py" in proto)
    check("wiring/prototype-passes-chat-image", "--chat-image" in proto)
    check("wiring/prototype-captures-the-unpresented-prototype",
          '--target "$PROTO_DIR/prototype.html"' in proto, "")
    check("wiring/prototype-does-not-swallow-the-reasons",
          '"$CF" chat-dir 2>/dev/null' not in proto,
          "chat-dir's whole output is the STATED REASON a frame did not happen; "
          "suppressing it turns a stated reason into a silent skip")
    check("wiring/prototype-reads-the-path-from-the-engine",
          'd["frames"][0]["path"]' in proto,
          "re-deriving `<label>-<frame>.png` in a skill is a second copy of the engine's "
          "naming contract, and it fails silently")
    check("wiring/prototype-takes-one-frame", "--only phone" in proto,
          "the chat message's budget is ONE image; --only phone is how that is expressed "
          "in the command rather than in a comment")
    ship = SHIP.read_text(encoding="utf-8")
    check("wiring/ship-captures", "capture_frames.py" in ship)
    check("wiring/ship-renders-from-captures", 'frames --source "$SRC"' in ship)
    check("wiring/ship-stages-the-frames", 'git add "$FRAME_DIR"' in ship)
    check("wiring/ship-captures-the-unpresented-prototype",
          "prototypes/*/prototype.html" in ship
          and "prototypes/*/prototype.presented.html" not in ship,
          "a still of `presented.html` photographs flow's own annotation dock, which is "
          "why the hand-off has to apologise for it in prose")
    check("wiring/ship-distinguishes-a-missing-engine",
          "capture engine not found at $CF" in ship,
          "collapsing that into the branch-name arm diagnoses a detached HEAD for a "
          "condition nobody measured")
    check("wiring/ship-gates-on-visual-significance",
          "visual-significance.py" in ship and "[pr-frames] skipped (visual_significant=false)" in ship,
          "capture must read the SAME authoritative verdict §5c and §7b read")
    check("wiring/ship-refuses-a-detached-head",
          "could not derive a per-PR directory" in ship,
          "an empty branch name must refuse, never fall back to a shared directory")
    spike = SPIKE.read_text(encoding="utf-8")
    check("wiring/spike-renders-from-captures", 'frames --source "$SRC"' in spike)
    # The source choice must come from the tool's EXIT CODE, not from grepping a render
    # (.claude/rules/general.md item 4, exit-code corollary).
    for name, txt in (("ship", ship), ("ship-spike", spike)):
        check("wiring/%s-chooses-source-by-exit-code" % name,
              'check >/dev/null 2>&1 && SRC=auto' in txt, name)
    # NEGATIVE paired with a POSITIVE: verify-build must NOT capture (it has no drive
    # primitive and no a11y assertion, so a frame from it would be "screenshot whatever
    # is on screen", which its own step 1c forbids) -- but it must SAY so, or this
    # assertion is satisfied by the section being deleted.
    vb = (FLOW / "skills" / "verify-build" / "SKILL.md").read_text(encoding="utf-8")
    check("wiring/verify-build-does-not-capture",
          "capture_frames.py capture" not in vb and "--chat-image" not in vb)
    check("wiring/verify-build-says-why-not",
          "`captureBackend` is NOT a substitute" in vb,
          "without the positive, deleting the whole boundary note turns the line above "
          "green (general.md item 3)")


def test_doctor_checks_the_slot():
    doc = DOCTOR.read_text(encoding="utf-8")
    check("doctor/has-check-2.14", "Check 2.14" in doc and "captureBackend" in doc)
    check("doctor/warn-not-fail",
          "[WARN] captureBackend is present but incomplete" in doc, "")
    check("doctor/silent-when-absent",
          "deliberately silent: no capture adapter is the normal case" in doc)
    check("doctor/reports-the-chat-dir", "chatImagePath" in doc)
    check("doctor/chat-dir-absent-is-not-a-warning",
          "[WARN] captureBackend is configured but chatImagePath" not in doc,
          "PR-body-frames-without-a-chat-image is a supported configuration; a warning "
          "that fires on a correct setup teaches people to ignore the warnings")
    check("doctor/does-not-reimplement-the-ignore-predicate",
          "chat-dir --json" in doc and 'git check-ignore -q "$CIP"' not in doc,
          "one predicate, one copy — and the engine's is a tristate, so `could not "
          "measure` is never reported as `not ignored`")
    check("doctor/drives-the-engine",
          "lib/capture_frames.py\" check" in doc,
          "the check must DRIVE the engine, not re-implement its validation")


def test_ci_wired():
    ci = CI.read_text(encoding="utf-8")
    check("ci/this-harness-wired",
          "python3 plugins/flow/evals/%s" % Path(__file__).name in ci,
          "an unwired harness contributes zero regression protection while appearing to")


def test_engine_selftests_pass():
    """Both engines' own known-positive/known-negative suites, by EXIT CODE.

    By exit code and not by grepping the last line: `run_autoplan_evals.py` exits 1
    while printing `241/244 checks passed`, which is how a four-push green streak
    happened over a red CI (tools/eval-sweep.sh).
    """
    for name, path in (("capture_frames", LIB), ("artifact-handoff", ENGINE)):
        r = subprocess.run([sys.executable, str(path), "--selftest"],
                           capture_output=True, text=True, timeout=180)
        check("selftest/%s" % name, r.returncode == 0,
              (r.stdout or "")[-1200:] + (r.stderr or "")[-400:])


def main() -> int:
    tests = (test_unset_is_byte_identical, test_only_a_valid_png_counts,
             test_stderr_noise_is_not_failure, test_utf8_is_required_before_capture,
             test_degrades_loudly, test_closed_vocabulary,
             test_only_frames_in_the_commit, test_own_pr_frames_only,
             test_private_fails_closed, test_curated_record_untouched,
             test_chat_message_budget, test_auto_never_retires_the_record,
             test_alt_text_says_what_the_frame_shows, test_frames_dir_is_composed_once,
             test_capture_step_states_a_reason_on_every_path,
             test_ignore_state_is_a_tristate_and_reaches_a_human,
             test_captured_frames_are_not_their_own_evidence,
             test_no_vendor_token_in_plugin,
             test_schema_declares_the_slots, test_skills_wire_the_capture,
             test_doctor_checks_the_slot, test_ci_wired, test_engine_selftests_pass)
    print("[capture-frames] %d case groups" % len(tests))
    for fn in tests:
        print(" %s" % fn.__name__)
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            _failures.append("%s raised %s: %s" % (fn.__name__, type(exc).__name__, exc))
            print("  FAIL  %s raised %s: %s" % (fn.__name__, type(exc).__name__, exc))
    if _failures:
        print("\n[capture-frames] FAIL — %d check(s):" % len(_failures))
        for f in _failures:
            print("  - %s" % f)
        return 1
    print("\n[capture-frames] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
