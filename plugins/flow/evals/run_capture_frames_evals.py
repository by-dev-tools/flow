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
elif mode == 'fail':
    sys.stderr.write('could not start browser\\n'); sys.exit(3)
"""


def _stub(td):
    p = Path(td, "stub.py")
    p.write_text(_STUB, encoding="utf-8")
    return p


def _be(td, mode):
    return {"screenshot": "python3 %s %s {url} {out} {width} {height}" % (_stub(td), mode)}


def _page(td, name="p.html", charset=True):
    p = Path(td, name)
    p.write_text(('<!doctype html><meta charset="utf-8">' if charset else "<!doctype html>")
                 + "<p>state ✓</p>", encoding="utf-8")
    return p


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
              == ["prototype-desktop.png", "prototype-phone.png"])


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
        # The prose is unchanged by the image: strip the image line and the result must
        # be byte-identical to the served line without it.
        prose = line.split("\n\n![")[0]
        check("chat/prose-byte-identical-without-image",
              prose == A.render_local_line("prototype", "/abs/p.presented.html",
                                           "https://ws.example.test/p.html",
                                           "anyone in the acme-eng org"), prose)
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
    check("vendor/scan-covered-every-target", scanned == len(targets), str(scanned))
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
    # The slot count is a fan-out contract (general.md item 2): a doc that still claims
    # the old number is a contradiction a reader will find tomorrow.
    n = len(props)
    for doc in (FLOW / "docs" / "workflow.md", REPO / "template" / "base" / "CLAUDE.md.template"):
        if doc.is_file():
            txt = doc.read_text(encoding="utf-8")
            stale = [m for m in re.findall(r"(\d+) slots", txt) if int(m) != n]
            check("schema/slot-count-current in %s" % doc.name, not stale,
                  "doc claims %r, schema has %d" % (stale, n))


def test_skills_wire_the_capture():
    """The engine is reachable from the three skills that must use it."""
    proto = PROTO.read_text(encoding="utf-8")
    check("wiring/prototype-captures", "capture_frames.py" in proto)
    check("wiring/prototype-passes-chat-image", "--chat-image" in proto)
    check("wiring/prototype-takes-one-frame", "--only phone" in proto,
          "the chat message's budget is ONE image; --only phone is how that is expressed "
          "in the command rather than in a comment")
    ship = SHIP.read_text(encoding="utf-8")
    check("wiring/ship-captures", "capture_frames.py" in ship)
    check("wiring/ship-renders-from-captures", 'frames --source "$SRC"' in ship)
    check("wiring/ship-stages-the-frames", 'git add "$FRAME_DIR"' in ship)
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
              'check >/dev/null 2>&1 && SRC=captures' in txt, name)
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
             test_chat_message_budget, test_no_vendor_token_in_plugin,
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
