#!/usr/bin/env python3
"""Regression pin for skills/ship/lib/artifact-handoff.py and its four call sites.

Why this harness carries the whole behavioural load for its PR: flow's
`flow.config.json` sets `"platform": "library"`, so `/flow:verify-build`
self-skips — there is no behavioural gate above this file. It IS the gate.

And flow cannot dogfood the interesting half. Every entry in this repo's own
`dev-docs/visual-history.html` is an inline CSS/SVG reconstruction, so
`visual-history-assets/` does not exist here and a live ship only ever exercises
the no-frames branch. The committed-frame branch is therefore driven against a
temp git repo built per-case, and the recon branch is driven against THIS repo's
real newest entry (the one case where the live artifact is the right fixture).

Shape note (.claude/rules/general.md Consistency items 3 + 4): every negative
here is paired with the positive it protects, and the engine's own `--selftest`
is run and then MUTATED, so a selftest that could only ever print PASS would be
caught rather than trusted.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLOW = HERE.parent
REPO = FLOW.parent.parent
ENGINE = FLOW / "skills" / "ship" / "lib" / "artifact-handoff.py"
COHERENCE = FLOW / "skills" / "ship" / "lib" / "pr-coherence.py"
RENDER_TP = FLOW / "skills" / "ship" / "lib" / "render-test-plan.py"
INSERT_VH = FLOW / "skills" / "ship" / "lib" / "insert-visual-history.py"
SHIP = FLOW / "skills" / "ship" / "SKILL.md"
SPIKE = FLOW / "skills" / "ship-spike" / "SKILL.md"
PROTO = FLOW / "skills" / "prototype" / "SKILL.md"
SCHEMA = FLOW / "schema" / "flow.config.schema.json"
CI = REPO / ".github" / "workflows" / "ci.yml"
LIVE_VH = REPO / "dev-docs" / "visual-history.html"

# Imported, NOT re-typed. A sixth spelling of a five-site contract is how the first
# draft of this harness silently disabled its own coherence case: it guessed
# `flow:test-plan-provenance` (pr-coherence's SUBCOMMAND name), the guard never
# matched, and both arms ran unstamped. importlib because the engine's filename is
# hyphenated — the run_manifest_triage_evals.py pattern for exactly this.
_spec = importlib.util.spec_from_file_location("pr_coherence", COHERENCE)
_prc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_prc)
_PROVENANCE_MARKER = _prc.PROVENANCE_MARKER

# The engine itself, imported so the round-trip case can call `newest_entry` directly
# rather than inferring the parse from rendered output.
_espec = importlib.util.spec_from_file_location("artifact_handoff", ENGINE)
_engine = importlib.util.module_from_spec(_espec)
_espec.loader.exec_module(_engine)

# eval_utils names itself the HOIST TARGET for the temp-git-repo helper this repo has
# five hand-rolled copies of ("new harnesses import from here"), and
# run_rigor_marker_evals.py records what a sixth copy costs: it was already BEHIND,
# missing `-b main`. So: `git_repo` for init/identity, local code only for the two
# things it cannot express (binary frames, and staging two of three files).
from eval_utils import git_repo  # noqa: E402

# NOT a constant any more: the predicate reads `cat-file -e <sha>:<path>` — the same
# ref the URL names — so a fabricated sha correctly resolves to zero frames. Each
# fixture reports its real head, which is the coupling the fix introduced on purpose.
# A 40-hex literal for fixtures that only need the SHAPE of a sha (the coherence
# body is illustrative markdown, never resolved against a repo). Distinct name from
# `head_sha` so the two uses cannot be confused: one must exist, one must not.
ILLUSTRATIVE_SHA = "0f1e2d3c4b5a69788796a5b4c3d2e1f001234567"


def head_sha(root) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                          text=True, timeout=60).stdout.strip()
# Independent list, deliberately NOT imported from the engine: importing its
# constant would make this eval go green if a name were deleted from it.
CLIENTS = ("iOS", "iPhone", "iPad", "Android", "Safari", "Conductor")
BRANCH = "feat/empty_feed"

_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print("  PASS  %s" % name)
    else:
        print("  FAIL  %s%s" % (name, ("\n        " + detail) if detail else ""))
        _failures.append(name)


def engine(*args, cwd=None, env=None):
    p = subprocess.run([sys.executable, str(ENGINE), *args], capture_output=True,
                       text=True, cwd=cwd, env=env, timeout=60)
    return p.returncode, p.stdout, p.stderr


# --------------------------------------------------------------- the fixture

VH_TMPL = """<!doctype html><html><body>
<article class="vh-entry" id="e-new">
<h2>Activity feed, empty</h2>
<div class="meta">#9<span class="sep">&middot;</span>2026-10-03<span class="sep">&middot;</span><code>%(branch)s</code></div>
<div class="ba">%(figs)s</div>
</article>
<article class="vh-entry" id="e-old">
<h2>An earlier change</h2>
<div class="meta">2026-09-01<span class="sep">&middot;</span><code>old/branch</code></div>
<div class="ba"><figure><figcaption>Stale</figcaption><img src="visual-history-assets/stale.png" alt="stale"></figure></div>
</article>
</body></html>"""

VH_TMPL_NOBRANCH = """<!doctype html><html><body>
<article class="vh-entry" id="e-nobranch">
<h2>A previous PR, with no branch recorded</h2>
<div class="meta">#7<span class="sep">&middot;</span>2026-09-01</div>
<div class="ba">%(figs)s</div>
</article>
</body></html>"""

FIG_IMG = ('<figure><figcaption>%(label)s</figcaption>'
           '<img src="visual-history-assets/%(file)s" alt="%(alt)s"></figure>')
FIG_RECON = ('<figure><figcaption>%(label)s</figcaption>'
             '<div class="recon"><div style="height:4px"></div>'
             '<div class="recon-note">Reconstruction (capture unavailable)</div></div></figure>')

FRAMES = [
    ("Before — activity feed, empty", "feed-empty-before.png",
     "blank gray panel with no call to action"),
    ("After — activity feed, empty", "feed-empty-after.png",
     'centered illustration, one-line explanation, "Add your first entry" button'),
]


VH_REL = "core-docs/visual-history.html"


def _git(args, cwd):
    """Only for what `eval_utils` cannot express: staging a SUBSET of the files."""
    subprocess.run(["git", *args], cwd=cwd, check=True, timeout=60,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def build_repo(td: str, figs: str, commit_frames=("feed-empty-before.png",
                                                  "feed-empty-after.png"),
               branch: str = BRANCH, vh_text: "str | None" = None) -> str:
    """A temp git repo whose committed visual-history record is exactly `figs`.

    `git_repo` does init + branch + identity + one commit of the text files. The two
    things it cannot express are the whole point of the committed-asset case: the
    frames are BINARY, and exactly two of the three must be staged.
    """
    root = os.path.join(td, "repo")
    git_repo(Path(root), {VH_REL: vh_text if vh_text is not None
                          else VH_TMPL % {"branch": branch, "figs": figs}})
    assets = Path(root, "core-docs", "visual-history-assets")
    assets.mkdir(parents=True, exist_ok=True)
    for _, f, _a in FRAMES:
        (assets / f).write_bytes(b"\x89PNG\r\n\x1a\n")
    (assets / "uncommitted.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    if commit_frames:
        _git(["add", *["core-docs/visual-history-assets/%s" % f for f in commit_frames]],
             root)
        _git(["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "frames"], root)
    return root


def frames_cmd(root, branch=BRANCH, private="false", repo="acme/app", sha=None):
    rc, out, err = engine("frames", "--visual-history", VH_REL,
                          "--branch", branch, "--sha", sha or head_sha(root),
                          "--repo", repo, "--private", private, "--root", root, cwd=root)
    return rc, out, err


TWO_IMG = "".join(FIG_IMG % {"label": l, "file": f, "alt": a} for l, f, a in FRAMES)


# ------------------------------------------------------------------- the pins

def _handoff_region(text: str) -> "str | None":
    """Every paragraph and fence that instructs an agent about the hand-off.

    Region = from the first mention of `artifact-handoff.py` to the end of the
    paragraph after the last one. A whole-file grep cannot be used: `ship/SKILL.md`
    and `prototype/SKILL.md` both legitimately contain "iOS" in unrelated prose.
    """
    first = text.find("artifact-handoff.py")
    if first == -1:
        return None
    last = text.rfind("artifact-handoff.py")
    end = text.find("\n\n", last)
    end = len(text) if end == -1 else text.find("\n\n", end + 2)
    return text[max(0, first - 600):(len(text) if end == -1 else end)]


def test_committed_only():
    """Spec-walk 1 — an `<img>` row only for a COMMITTED asset. Paired."""
    with tempfile.TemporaryDirectory() as td:
        figs = TWO_IMG + FIG_IMG % {"label": "Third", "file": "uncommitted.png",
                                    "alt": "never committed"}
        root = build_repo(td, figs)
        rc, out, _ = frames_cmd(root)
        check("committed/exit-0", rc == 0, out)
        # positive: the two tracked frames ARE emitted...
        check("committed/tracked-emitted",
              out.count("feed-empty-before.png") == 1 and out.count("feed-empty-after.png") == 1,
              out)
        # ...negative: the untracked one is NOT. Alone this would pass if the
        # engine emitted nothing at all, which is why it is paired above.
        check("committed/untracked-excluded", "uncommitted.png" not in out, out)
        check("committed/exactly-two-rows", out.count("![") == 2, out)


def test_branch_match_paired():
    """Spec-walk 2 — identical entry, branch matching vs not."""
    with tempfile.TemporaryDirectory() as td:
        root = build_repo(td, TWO_IMG)
        _, match, _ = frames_cmd(root, branch=BRANCH)
        check("branch/match-emits-2", match.count("![") == 2, match)
        _, mism, _ = frames_cmd(root, branch="some/other-branch")
        check("branch/mismatch-emits-0", mism.count("![") == 0 and "/blob/" not in mism, mism)
        check("branch/mismatch-states-reason",
              "different change" in mism and "`%s`" % BRANCH in mism, mism)
        check("branch/mismatch-keeps-heading", mism.startswith("## Before / after"), mism)
        # The second (older) entry must never be reached — the file is
        # reverse-chronological and only the newest entry is this PR's.
        check("branch/older-entry-never-read", "stale.png" not in match + mism)


def test_branch_guard_is_not_vacuous():
    """Two empty strings are not a match. Both halves of this are reachable.

    `(entry["branch"] or "") != branch` compared "" to "" as EQUAL. `branch` is
    documented-optional in the entry-JSON contract, and the shipped call site passes
    `$(git branch --show-current)`, which is EMPTY on a detached HEAD — a real
    worktree state. So a branchless entry left by a PREVIOUS PR plus a detached HEAD
    embedded that PR's frames under this one's name: the outcome the check exists to
    prevent, produced by the check itself (general.md item 4 — a zero-match filter
    is not a confirmation).

    Paired: the same fixture with BOTH sides populated and equal must still emit.
    Without that, deleting the guard's whole branch would pass the negatives.
    """
    no_branch = VH_TMPL_NOBRANCH % {"figs": TWO_IMG}
    with tempfile.TemporaryDirectory() as td:
        root = build_repo(td, TWO_IMG, vh_text=no_branch)
        sha = head_sha(root)
        for label, br in (("both-empty", ""), ("entry-empty", BRANCH)):
            _, out, _ = frames_cmd(root, branch=br, sha=sha)
            check("vacuous/%s-emits-nothing" % label,
                  "![" not in out and "/blob/" not in out,
                  "a branchless entry was embedded under --branch %r: %s" % (br, out))
            check("vacuous/%s-says-not-recorded" % label, "not recorded" in out, out)

    with tempfile.TemporaryDirectory() as td:
        root = build_repo(td, TWO_IMG)          # entry DOES carry BRANCH
        sha = head_sha(root)
        _, empty_arg, _ = frames_cmd(root, branch="", sha=sha)
        check("vacuous/arg-empty-emits-nothing", "![" not in empty_arg, empty_arg)
        check("vacuous/arg-empty-says-unresolvable",
              "not resolvable here" in empty_arg, empty_arg)
        # The paired POSITIVE: populated and equal still emits, so none of the
        # negatives above can be satisfied by removing the guard.
        _, ok, _ = frames_cmd(root, branch=BRANCH, sha=sha)
        check("vacuous/populated-and-equal-still-emits", ok.count("![") == 2, ok)


def test_predicate_reads_the_same_ref_as_the_url():
    """A frame in the INDEX but not in the commit must NOT get a URL.

    `git ls-files --error-unmatch` answered "is this in the index?", while the URL is
    pinned to `--sha`. So a `git add`-ed, uncommitted frame rendered as an inline
    image at a commit that does not contain the blob — a broken image in the PR body,
    which this skill's own prose calls strictly worse than an honest absence.
    `cat-file -e <sha>:<path>` asks about the ref the URL names, so the two cannot
    disagree.
    """
    with tempfile.TemporaryDirectory() as td:
        root = build_repo(td, TWO_IMG, commit_frames=())   # frames exist, none committed
        _git(["add", "core-docs/visual-history-assets/feed-empty-before.png"], root)
        sha = head_sha(root)
        # Instrument validation: the staged-not-committed state must actually hold,
        # or this case proves nothing about the predicate.
        in_index = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--",
             "core-docs/visual-history-assets/feed-empty-before.png"],
            cwd=root, capture_output=True, timeout=60).returncode == 0
        in_commit = subprocess.run(
            ["git", "cat-file", "-e",
             "%s:core-docs/visual-history-assets/feed-empty-before.png" % sha],
            cwd=root, capture_output=True, timeout=60).returncode == 0
        check("ref/fixture-is-staged-not-committed", in_index and not in_commit,
              "in_index=%s in_commit=%s" % (in_index, in_commit))
        _, out, _ = frames_cmd(root, sha=sha)
        check("ref/staged-only-frame-excluded", "![" not in out, out)
        check("ref/says-not-in-the-commit",
              "not in the commit this PR points at" in out, out)

        # And a sha that PREDATES the frames emits nothing, even though they ARE
        # committed at HEAD — the arm an index-based predicate could not express.
        root2 = build_repo(td + "/b", TWO_IMG)
        first = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=root2,
                               capture_output=True, text=True, timeout=60).stdout.strip()
        head = head_sha(root2)
        check("ref/two-distinct-commits", bool(first) and first != head,
              "fixture has one commit, so the predating-sha arm is vacuous")
        if first and first != head:
            _, early, _ = frames_cmd(root2, sha=first)
            check("ref/sha-predating-frames-emits-nothing", "![" not in early, early)
            _, now, _ = frames_cmd(root2, sha=head)
            check("ref/sha-containing-frames-emits", now.count("![") == 2, now)


def test_visibility_three_arms():
    """Spec-walk 3 — public / private / gh-absent. Same two frames in all three."""
    with tempfile.TemporaryDirectory() as td:
        root = build_repo(td, TWO_IMG)
        sha = head_sha(root)
        _, pub, _ = frames_cmd(root, private="false", sha=sha)
        _, priv, _ = frames_cmd(root, private="true", sha=sha)

        ghless = os.path.join(td, "bin-no-gh")
        os.makedirs(ghless)
        os.symlink(shutil.which("git"), os.path.join(ghless, "git"))
        env = dict(os.environ, PATH=ghless)
        rc, auto, err = engine("frames", "--visual-history", VH_REL,
                               "--branch", BRANCH, "--sha", head_sha(root), "--repo", "acme/app",
                               "--private", "auto", "--root", root, cwd=root, env=env)
        check("visibility/gh-absent-exit-0", rc == 0, err)

        check("visibility/raw-in-public-only",
              "raw.githubusercontent.com" in pub
              and "raw.githubusercontent.com" not in priv
              and "raw.githubusercontent.com" not in auto,
              "pub=%s priv=%s auto=%s" % ("raw" in pub, "raw" in priv, "raw" in auto))
        for arm, body in (("private", priv), ("gh-absent", auto)):
            for _l, f, _a in FRAMES:
                check("visibility/%s-blob-%s" % (arm, f),
                      "https://github.com/acme/app/blob/%s/core-docs/visual-history-assets/%s"
                      % (sha, f) in body, body)
            check("visibility/%s-no-image-syntax" % arm, "![" not in body, body)
        check("visibility/private-says-why",
              "Private repo" in priv and "can't show these inline" in priv, priv)
        check("visibility/gh-absent-says-why",
              "Couldn't tell whether this repo is public" in auto, auto)
        # All three arms close the same way (record + sha pin). The private and
        # unknown arms named neither, so the one population option 2 exists for got
        # the thinner hand-off and was never told the frames are pinned to a commit.
        for arm, body in (("public", pub), ("private", priv), ("gh-absent", auto)):
            check("visibility/%s-names-the-record" % arm, VH_REL in body, body)
            check("visibility/%s-names-the-sha-pin" % arm,
                  sha[:7] in body and ("pinned to" in body or "Pinned to" in body), body)
            check("visibility/%s-no-visible-escapes" % arm, "\\_" not in body, body)


def test_recon_only_live_entry():
    """Spec-walk 4 — built from THIS repo's real newest entry, which is recon-only."""
    live = LIVE_VH.read_text(encoding="utf-8")
    first = live.find('<article class="vh-entry"')
    check("recon/live-record-exists", first != -1, "no vh-entry in %s" % LIVE_VH)
    nxt = live.find('<article class="vh-entry"', first + 1)
    newest = live[first:(nxt if nxt != -1 else len(live))]
    # The premise of this case, asserted rather than assumed: if flow ever commits
    # a real frame, this stops being the recon fixture and must be re-keyed.
    check("recon/live-entry-is-recon-only",
          '<div class="recon"' in newest and "<img src=" not in newest,
          "flow's newest visual-history entry now carries a committed frame — re-key this case")
    m = re.search(r"<code>(.*?)</code>", newest, re.S)
    live_branch = m.group(1).strip() if m else ""

    with tempfile.TemporaryDirectory() as td:
        root = os.path.join(td, "repo")
        git_repo(Path(root), {VH_REL: live})   # exact drop-in for eval_utils
        _, out, _ = frames_cmd(root, branch=live_branch)
        check("recon/no-image-syntax", "![" not in out, out)
        # Plain language, deliberately: this is the arm EVERY flow ship takes and the
        # likeliest consumer arm, and it was the one carrying implementation
        # vocabulary ("CSS/SVG reconstructions", "captures") at a merge gate read by
        # someone who does not need to know how the diagram was drawn.
        check("recon/states-reason",
              "hand-built diagrams" in out and "no committed image" in out, out)
        check("recon/no-implementation-vocabulary",
              not any(w in out for w in ("CSS/SVG", "captures", "recon")), out)
        check("recon/section-not-empty", len(out.split("\n\n", 1)[-1].strip()) > 60, out)


def test_reader_matches_the_writer():
    """The vh-entry markup contract: READ what `insert-visual-history.py` WRITES.

    `newest_entry()` re-derives the `<article class="vh-entry">` / `<div class="meta">`
    / `<figure>` / `<img src=… alt=…>` / `<div class="recon">` literals that
    `insert-visual-history.py` emits. Nothing shares them, and the failure direction is
    quiet: reorder an `<img>` attribute, add one, or rename the `recon` class in the
    WRITER and the reader finds zero figures, the engine takes its no-frames branch, and
    the PR body prints a plausible reason. Nothing fails.

    So the fixture is not hand-written markup — it is the writer's actual output, driven
    here. A writer-side change that breaks the reader now fails CI at this line. (The
    deeper fix, a shared contract module in the `manifest_contract.py` shape, is a named
    residual in roadmap D7 — it needs the writer in its write scope.)
    """
    entry = {
        "title": "Empty activity feed", "date": "2026-10-03", "branch": BRANCH,
        "grounding": {"type": "need", "statement": "the zero state said nothing"},
        "before_after": [
            {"label": lbl, "src": "visual-history-assets/" + f, "alt": alt}
            for lbl, f, alt in FRAMES
        ],
    }
    with tempfile.TemporaryDirectory() as td:
        root = Path(td, "repo")
        git_repo(root, {".keep": ""})
        target = root / VH_REL
        target.parent.mkdir(parents=True, exist_ok=True)
        w = subprocess.run([sys.executable, str(INSERT_VH), "--target", str(target)],
                           input=json.dumps(entry), capture_output=True, text=True,
                           timeout=60)
        check("roundtrip/writer-ran", w.returncode == 0 and target.exists(),
              (w.stdout + w.stderr)[-400:])
        if not target.exists():
            return
        written = target.read_text(encoding="utf-8")
        # Instrument validation: the writer must actually have emitted <img> rows,
        # otherwise "the reader found them" would be comparing two empties.
        check("roundtrip/writer-emitted-img-rows", written.count("<img src=") == 2,
              "count=%d" % written.count("<img src="))

        parsed = _engine.newest_entry(written)
        check("roundtrip/reader-found-the-entry", parsed is not None)
        if parsed is None:
            return
        check("roundtrip/reader-read-the-branch", parsed["branch"] == BRANCH,
              repr(parsed["branch"]))
        got = [(f["label"], f["src"], f["alt"]) for f in parsed["figures"] if f["src"]]
        want = [(lbl, "visual-history-assets/" + f, alt) for lbl, f, alt in FRAMES]
        check("roundtrip/reader-read-every-field", got == want,
              "writer emitted markup this reader does not parse — the vh-entry contract "
              "has split.\n        got  %r\n        want %r" % (got, want))

        # The recon shape too: it is what decides the "reconstructions, not captures"
        # branch, which is the branch flow's own every ship actually takes.
        recon_entry = dict(entry, before_after=[
            {"label": "Before", "html": "<svg/>", "recon": True}])
        w2 = subprocess.run([sys.executable, str(INSERT_VH), "--target", str(target)],
                            input=json.dumps(recon_entry), capture_output=True,
                            text=True, timeout=60)
        check("roundtrip/writer-ran-recon", w2.returncode == 0, (w2.stdout + w2.stderr)[-300:])
        parsed2 = _engine.newest_entry(target.read_text(encoding="utf-8"))
        check("roundtrip/reader-classifies-recon",
              parsed2 is not None and [f["recon"] for f in parsed2["figures"]] == [True],
              repr(parsed2 and parsed2["figures"]))


def test_url_shape():
    """Spec-walk 5 — every URL carries the 40-char sha; the branch never appears."""
    with tempfile.TemporaryDirectory() as td:
        root = build_repo(td, TWO_IMG)
        sha = head_sha(root)
        for private in ("false", "true"):
            _, out, _ = frames_cmd(root, private=private, sha=sha)
            urls = re.findall(r"https://\S+", out)
            check("url/%s-found" % private, len(urls) == 2, str(urls))
            for u in urls:
                check("url/%s-40-hex" % private, re.search(r"/[0-9a-f]{40}/", u) is not None, u)
                check("url/%s-no-short-sha" % private, sha[:7] not in u.replace(sha, ""), u)
            check("url/%s-no-branch-name" % private, BRANCH not in out, out)
        # A short or branch-shaped --sha is refused, not silently accepted: a
        # branch URL 404s the moment the branch is deleted at merge.
        for bad in (head_sha(root)[:7], BRANCH, ""):
            rc, _, _ = engine("frames", "--visual-history", VH_REL,
                              "--branch", BRANCH, "--sha", bad, "--repo", "acme/app",
                              "--private", "false", "--root", root, cwd=root)
            check("url/refuses-sha-%r" % bad, rc != 0, "accepted %r as a sha" % bad)


def test_md_safety_layering():
    """Escape for a TEXT position; contain for a CODE position; never both.

    The two strategies do not compose, and composing them is silent: inside a code
    span a backslash is a literal character, so `code_span(inline(path))` shows the
    reader `` `frames/\\[a\\]_b` `` instead of the path. Caught by this case after
    the first draft shipped exactly that pairing.
    """
    sys.path.insert(0, str(ENGINE.parent))
    import md_safe

    nasty = "frames/[a]_b*c<!--x-->.png"
    txt = md_safe.inline(nasty)
    code = md_safe.code_span(md_safe.one_line(nasty))
    check("mdsafe/text-position-escapes", "\\[" in txt and "\\<" in txt, txt)
    check("mdsafe/code-position-does-not-escape", "\\" not in code, code)
    check("mdsafe/code-position-contains", code.startswith("`") and code.endswith("`"), code)
    # NOT `"<!--" not in txt`: escaping turns it into `\<!--`, which still CONTAINS
    # that substring while being inert. The real property is that no `<` survives
    # UNESCAPED — assert that, or the check tests its own phrasing.
    check("mdsafe/no-unescaped-comment-opener",
          re.search(r"(?<!\\)<", txt) is None, txt)

    # The engine must use each in its own position. A code-span site that escapes
    # first is the defect above; a text-position site that does not escape is an
    # injection. Paired, so neither direction passes by deletion.
    src = ENGINE.read_text(encoding="utf-8")
    # Comment lines are excluded deliberately: the engine's own comments NAME the
    # `code_span(inline(` regression they guard against, so a whole-file substring
    # search reports the explanation as the defect.
    code_lines = [ln for ln in src.splitlines() if not ln.lstrip().startswith("#")]
    code_only = "\n".join(code_lines)

    # Real call sites, via `ast`. A substring count is satisfied by PROSE — the first
    # cut's threshold was partly met by `url_path`'s docstring saying "go through
    # `inline()`", because the filter above strips `#` lines and not docstrings. So
    # its margin was narrative: one more comment naming inline() plus one deleted
    # call site would have gone green.
    tree = ast.parse(src)
    def _calls(name):
        return sum(1 for n in ast.walk(tree)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                   and n.func.id == name)
    n_inline, n_code_span, n_one_line = (_calls("inline"), _calls("code_span"),
                                         _calls("one_line"))
    check("mdsafe/engine-contains-in-code-positions",
          "code_span(inline(" not in code_only
          and code_only.count("code_span(one_line(") >= 2,
          "code_span must wrap one_line (unescaped), never inline (escaped); "
          "found %d one_line call(s)" % code_only.count("code_span(one_line("))
    # COUNT the positions, do not name them. The first version listed two literals
    # and was structurally blind to a third text position (the last-resort alt, which
    # interpolated a filename raw) — a two-literal allowlist cannot notice a fourth.
    text_positions = code_only.count("inline(")
    # EXACT, because the engine has exactly three markdown TEXT positions: the
    # figcaption and the alt at the parse boundary, and the last-resort alt. An exact
    # count catches a REMOVED wrapper; it still cannot catch an ADDED raw sink (a
    # fourth position added without `inline()` leaves the count at three), which is
    # why the real guarantee is the behavioural property in
    # test_every_record_field_is_neutralized — that one does not care how a new sink
    # is spelled. Re-key this number deliberately if a position is genuinely added.
    check("mdsafe/exactly-three-text-positions-escape", n_inline == 3,
          "the engine has three markdown TEXT positions (figcaption, alt, last-resort "
          "alt) and each must be wrapped in inline(); found %d call site(s)." % n_inline)
    # A raw count comparison was wrong here (code_span=11, one_line=9) because two
    # code_span calls wrap `sha[:7]`, which is validated hex and needs no collapsing.
    # Assert the PROPERTY instead: every code_span argument is a one_line(...) call,
    # or a subscript of `sha`. Anything else is untrusted text entering a code span
    # without being collapsed to one line first.
    bad_code_spans = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "code_span"):
            continue
        a = n.args[0] if n.args else None
        ok = (isinstance(a, ast.Call) and isinstance(a.func, ast.Name)
              and a.func.id == "one_line")
        if not ok and isinstance(a, ast.Subscript) and isinstance(a.value, ast.Name):
            ok = a.value.id == "sha"
        if not ok:
            bad_code_spans.append(getattr(a, "lineno", "?"))
    check("mdsafe/every-code-span-collapses-first", not bad_code_spans,
          "code_span() must wrap one_line(...) (or a sha slice); unguarded at "
          "line(s) %r" % bad_code_spans)
    check("mdsafe/code-spans-exist", n_code_span >= 5,
          "found %d code_span call(s) — re-key if the engine genuinely shrank"
          % n_code_span)
    check("mdsafe/no-raw-unescape-into-a-text-position",
          "inline(htmllib.unescape(" in code_only,
          "record-derived text must be escaped at the parse boundary")

    # Longest arm: a figcaption long enough to be truncated must still be escaped,
    # and must not end mid-escape-sequence (a trailing lone backslash would escape
    # the construct's own closing bracket).
    # Metacharacters in the RETAINED prefix, so the real bound is exercised: the cap
    # applies to the SOURCE text and escaping runs after, so the result can reach
    # 2*limit. The first cut asserted `<= 52` for limit=50 and passed only because its
    # fixture's `[boom]` fell past the cut — a bound tighter than the documented
    # contract, held by accident.
    t = md_safe.inline("[" * 300, 50)
    check("mdsafe/truncation-caps-the-source", len(md_safe.one_line("[" * 300, 50)) <= 50,
          "%d" % len(md_safe.one_line("[" * 300, 50)))
    check("mdsafe/truncation-respects-the-documented-bound", len(t) <= 2 * 50,
          "docstring promises <= 2*limit; got %d" % len(t))
    check("mdsafe/truncation-actually-escaped-the-prefix", t.startswith("\\["), t[:8])
    check("mdsafe/truncation-leaves-no-dangling-escape", not t.endswith("\\"), t)
    # And the plain-prose case stays near the cap, so the 2x allowance is not a
    # licence for every string to double.
    plain = md_safe.inline("y" * 300, 50)
    check("mdsafe/truncation-plain-text-stays-at-cap", len(plain) <= 50, "%d" % len(plain))


def test_url_destination_cannot_break_out():
    """A frame FILENAME cannot break out of the `![…](…)` construct.

    The engine has THREE markdown text positions (`label`, `alt`, and the
    last-resort alt) plus one destination position. This case owns the DESTINATION.
    It was unneutralized while `label` and `alt` went through `inline()` — and the
    name of this case used to claim it was "the last" such sink, which a later review
    round disproved by finding the third text position still raw. A test name is a
    claim; this one is now scoped to what it actually covers. So a committed frame
    whose name embeds a newline plus markdown rendered the attacker's lines as live
    markdown in the body a human reads at the merge gate — potentially a forged
    `## Test plan` heading above the real one, which is the section `pr-coherence.py`
    keys on. Percent-encoding also subsumes the space/paren cases an angle-bracketed
    destination used to special-case, and unlike `<…>` it survives a line ending
    (a `<…>` destination may not contain one, per CommonMark).

    Threat model, stated: the precondition is a TRACKED file whose name holds control
    characters, loud in `git status` and in the diff, authored by a collaborator with
    commit access. Low severity; pinned because an unneutralized sink in a published
    artifact should not exist at all.
    """
    nasty = "a\n\n[Approve](https:evil)\nb (1).png"
    with tempfile.TemporaryDirectory() as td:
        root = os.path.join(td, "repo")
        figs = FIG_IMG % {"label": "Evil", "file": nasty, "alt": "x"}
        git_repo(Path(root), {VH_REL: VH_TMPL % {"branch": BRANCH, "figs": figs}})
        assets = Path(root, "core-docs", "visual-history-assets")
        assets.mkdir(parents=True, exist_ok=True)
        with open(os.path.join(str(assets), nasty), "wb") as fh:
            fh.write(b"\x89PNG")
        _git(["add", "-A"], root)
        _git(["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "nasty"], root)
        sha = head_sha(root)
        # Instrument validation: the hostile frame must actually be IN the commit,
        # or this case exercises the omission branch and proves nothing.
        tracked = subprocess.run(
            ["git", "cat-file", "-e",
             "%s:core-docs/visual-history-assets/%s" % (sha, nasty)],
            cwd=root, capture_output=True, timeout=60).returncode == 0
        check("urlpath/hostile-frame-is-committed", tracked,
              "fixture did not commit the control-char filename — the emitting path "
              "was never reached")
        _, out, _ = frames_cmd(root, sha=sha)
        check("urlpath/one-image-row", out.count("![") == 1, out)
        check("urlpath/newline-encoded", "%0A" in out, out)
        check("urlpath/brackets-encoded", "%5B" in out and "%5D" in out, out)
        check("urlpath/space-and-parens-encoded",
              "%20" in out and "%28" in out and "%29" in out, out)
        # The breakout this prevents: a standalone live link on its own line.
        check("urlpath/no-standalone-link",
              not any(ln.startswith("[Approve]") for ln in out.splitlines()), out)
        check("urlpath/separators-stay-literal",
              "core-docs/visual-history-assets/" in out, out)
        # Paired positive: an ordinary filename is NOT mangled, so the encoder
        # cannot be "fixed" by encoding everything.
        root2 = build_repo(td + "/plain", TWO_IMG)
        _, plain, _ = frames_cmd(root2)
        check("urlpath/ordinary-filename-unencoded",
              "feed-empty-before.png" in plain and "%" not in plain, plain)

    # Unit-level properties of the encoder, pinned because a future reader could
    # reasonably mistake two of them for bugs and "fix" them into defects.
    check("urlpath/separators-are-safe",
          _engine.url_path("a/b/c.png") == "a/b/c.png",
          "path separators must stay literal or the URL does not resolve")
    check("urlpath/literal-percent-is-encoded",
          _engine.url_path("a/x%20y.png") == "a/x%2520y.png",
          "a file literally NAMED `x%20y.png` must have its `%` encoded — this is "
          "correct, not double-encoding: `git cat-file -e` already validated that "
          "literal name, so the URL has to reproduce it")
    check("urlpath/non-ascii-is-utf8-encoded",
          _engine.url_path("a/caf\u00e9.png") == "a/caf%C3%A9.png",
          "a non-ASCII asset name is legitimate and must be UTF-8 percent-encoded")


def test_caption_and_alt_cover_every_combination():
    """All four (label present/absent x alt present/absent) states, explicitly.

    Reviewed twice with opposite conclusions, so the resolved behaviour is pinned
    rather than left to the next reader's judgment: when `alt` is absent the caption
    is reused as alt AND stays visible. Suppressing it cost the Before/After label on
    the only arm that shows images, which on a narrow viewport left two unlabelled
    stacked frames; one duplicate screen-reader announcement is the cheaper cost.
    """
    ca = _engine._caption_and_alt
    cap, alt = ca({"label": "Before", "alt": "a gray panel", "src": "x/a.png"})
    check("capalt/both-present-kept", (cap, alt) == ("Before", "a gray panel"),
          repr((cap, alt)))
    cap, alt = ca({"label": "Before", "alt": "", "src": "x/a.png"})
    check("capalt/alt-absent-reuses-caption-and-keeps-it",
          (cap, alt) == ("Before", "Before"), repr((cap, alt)))
    cap, alt = ca({"label": "", "alt": "a gray panel", "src": "x/a.png"})
    check("capalt/caption-absent-keeps-alt", (cap, alt) == ("", "a gray panel"),
          repr((cap, alt)))
    cap, alt = ca({"label": "", "alt": "", "src": "x/feed-empty.png"})
    check("capalt/both-absent-names-the-file",
          cap == "" and "feed-empty.png" in alt and "no caption recorded" in alt,
          repr((cap, alt)))
    # The invariant the rows depend on: alt is NEVER empty, in any of the four.
    for f in ({"label": "L", "alt": "A"}, {"label": "L", "alt": ""},
              {"label": "", "alt": "A"}, {"label": "", "alt": ""}):
        _c, a = ca(dict(f, src="x/y.png"))
        check("capalt/alt-never-empty-%r" % (tuple(sorted(f.items())),), bool(a),
              "an empty alt is markdown's DECORATIVE signal: %r" % (f,))
    # And the third text position is escaped, not raw.
    _c, a = ca({"label": "", "alt": "", "src": "x/a_b [c].png"})
    check("capalt/last-resort-alt-is-escaped", "\\_" in a and "\\[" in a, a)


def test_captions_land_escaped_in_text_positions():
    """A metacharacter-bearing caption is escaped in text, contained in code.

    The point of splitting `inline` (escape) from `one_line` (contain) is that a
    reader must never see the escaping. Pinning that needs a fixture with something
    TO escape — the default captions have no metacharacter, so the arms' own
    no-visible-escapes assertions were nearly vacuous even once their literal was
    corrected. The engine's `--selftest` made exactly this move for the branch name
    (`feat/empty_feed`); this is the caption half.
    """
    cap = "Before — activity_feed, empty [zero state]"
    figs = FIG_IMG % {"label": cap, "file": "feed-empty-before.png", "alt": "a_b [c]"}
    with tempfile.TemporaryDirectory() as td:
        root = build_repo(td, figs, commit_frames=("feed-empty-before.png",))
        sha = head_sha(root)
        for arm, private in (("public", "false"), ("private", "true")):
            _, out, _ = frames_cmd(root, private=private, sha=sha)
            check("caption/%s-row-emitted" % arm, ("![" in out or "/blob/" in out), out)
            # Escaped — so the metacharacters cannot reflow the construct...
            check("caption/%s-metachars-escaped" % arm,
                  "activity\\_feed" in out and "\\[zero state\\]" in out, out)
            # ...and NOT double-escaped, which is what the reader would see.
            check("caption/%s-no-double-escape" % arm, "\\\\_" not in out, out)
        # The code position (the record path in the trailer) must NOT be escaped.
        _, pub, _ = frames_cmd(root, private="false", sha=sha)
        check("caption/code-position-unescaped",
              "`core-docs/visual-history.html`" in pub, pub)
        # Instrument validation: confirm the fixture really carries a metacharacter,
        # or every assertion above is about a string with nothing to escape.
        check("caption/fixture-has-metachars", "_" in cap and "[" in cap, cap)


def test_every_record_field_is_neutralized():
    """Load every record field with a breakout payload; no unintended link survives.

    The source-shape checks enumerate the sinks they know about, so they are blind by
    construction to a sink somebody ADDS later — which is exactly what happened once
    already this review round (the last-resort alt). This case asserts the OUTPUT
    instead: whatever the engine does internally, the rendered section must contain
    no image or link destination other than the frame URLs it meant to emit.
    """
    payload = 'x](https://evil.example) ![pwn](https://evil.example/2) <!--c--> `t` *e* _u_'
    figs = ('<figure><figcaption>%s</figcaption>'
            '<img src="visual-history-assets/feed-empty-before.png" alt="%s"></figure>'
            % (payload, payload))
    with tempfile.TemporaryDirectory() as td:
        root = build_repo(td, figs, commit_frames=("feed-empty-before.png",))
        sha = head_sha(root)
        for arm, private in (("public", "false"), ("private", "true"),):
            _, out, _ = frames_cmd(root, private=private, sha=sha)
            # Instrument validation: the payload must actually have reached the body,
            # or "no evil host" is true because nothing was rendered at all.
            check("neutral/%s-payload-reached-the-body" % arm, "evil.example" in out,
                  "the hostile caption never reached the output, so this case proves "
                  "nothing: %s" % out)
            # The ONLY destinations may be the frame URLs the engine built. Note the
            # negative lookbehind: an ESCAPED `\]` does not open a link, so matching
            # a bare `](` would flag the engine's own correct output as a breakout.
            # (It did, on the first cut of this case — the assertion was wrong, not
            # the code.)
            dests = re.findall(r"(?<!\\)\]\((\S+?)\)", out)
            bad = [d for d in dests if "evil.example" in d]
            check("neutral/%s-no-attacker-destination" % arm, not bad,
                  "a record field reached a markdown DESTINATION: %r" % bad)
            check("neutral/%s-one-destination-only" % arm, len(dests) == 1,
                  "expected exactly the one frame URL, got %r" % dests)
            check("neutral/%s-destination-is-ours" % arm,
                  dests and ("raw.githubusercontent.com" in dests[0]
                             or "/blob/" in dests[0]), repr(dests))
            # Instrument validation for the lookbehind itself: it must still SEE an
            # unescaped destination, or "no attacker destination" is vacuous.
            probe = out + "\n[live](https://evil.example/probe)"
            check("neutral/%s-matcher-sees-an-unescaped-link" % arm,
                  any("evil.example/probe" in d
                      for d in re.findall(r"(?<!\\)\]\((\S+?)\)", probe)),
                  "the destination matcher cannot see a real link, so its silence "
                  "means nothing")
            # No inert-but-hidden content either.
            check("neutral/%s-no-live-comment-opener" % arm,
                  re.search(r"(?<!\\)<!--", out) is None, out)


def test_local_line():
    """Spec-walk 6 — names where it can and cannot be opened; names no client."""
    rc_w, w, _ = engine("local-line", "--kind", "walkthrough", "--path", ".flow/report.html")
    rc_p, p, _ = engine("local-line", "--kind", "prototype",
                        "--path", "/abs/.flow/prototypes/s/prototype.presented.html")
    check("local/exit-0", rc_w == 0 and rc_p == 0)
    check("local/walkthrough-not-committed", "not committed" in w, w)
    check("local/walkthrough-only-where", "only open it where" in w, w)
    check("local/walkthrough-carries-path", ".flow/report.html" in w, w)
    # It must NOT cross-reference the frames section: `frames` is a separate
    # subcommand whose common output is an omission line, and both skills delete the
    # heading when the renderer is absent — so a hard-coded "the frames are above"
    # produced a body claiming frames exist right below a line saying they do not.
    check("local/walkthrough-makes-no-claim-about-frames",
          "Before / after" not in w and "frames" not in w.lower(),
          "the local-line asserted something about a sibling subcommand's output: %r" % w)
    check("local/prototype-local-file", "local file" in p, p)
    check("local/prototype-only-where", "only open it where" in p, p)
    check("local/prototype-names-the-dock", "comment dock is flow's" in p, p)
    for name in CLIENTS:
        check("local/no-client-%s" % name, name.lower() not in (w + p).lower())
    rc_bad, _, _ = engine("local-line", "--kind", "nonsense", "--path", "x")
    check("local/unknown-kind-refused", rc_bad != 0)
    # The runtime guard WARNS and still emits (it must not `die`: the shipped call
    # site's `|| echo "renderer absent"` would then print a false diagnosis for a
    # reworded sentence). Validate the guard against a known positive rather than
    # trusting its silence — pair the quiet case above with a loud one.
    import contextlib
    import io
    inj = _engine.render_local_line
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        out = inj("walkthrough", "/tmp/x-iPhone-y.html")
    check("local/guard-warns-on-a-client-name", "names a client" in err.getvalue(),
          "the no-client guard stayed silent on a path containing 'iPhone': %r"
          % err.getvalue())
    check("local/guard-still-emits-the-line", "not committed" in out,
          "the guard suppressed the hand-off instead of warning: %r" % out)


def test_selftest_is_mutation_sensitive():
    """Spec-walk 7 — green now, and RED when the committed-asset check is broken.

    This is the instrument-validation pin (Consistency item 4): a `--selftest`
    that can only ever print PASS is not evidence about anything.
    """
    rc, out, err = engine("--selftest")
    check("selftest/green", rc == 0, out + err)
    src = ENGINE.read_text(encoding="utf-8")
    anchor = ('    try:\n        r = subprocess.run(\n'
              '            ["git", "cat-file", "-t", "%s:%s" % (sha, rel_path)],')
    check("selftest/mutation-anchor-present", anchor in src,
          "git_tracked()'s body changed shape — re-key the mutation below, do not delete it")
    if anchor not in src:
        return
    with tempfile.TemporaryDirectory() as td:
        mutant = Path(td, "artifact-handoff.py")
        mutant.write_text(src.replace(anchor, "    return True\n" + anchor, 1),
                          encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ENGINE.parent) + os.pathsep + env.get("PYTHONPATH", "")
        p = subprocess.run([sys.executable, str(mutant), "--selftest"],
                           capture_output=True, text=True, timeout=60, env=env)
        out = p.stdout + p.stderr
        # Instrument validation BEFORE the verdict: a mutant that died on import also
        # exits non-zero, so "non-zero" alone cannot distinguish "the mutation was
        # caught" from "the mutant never ran".
        check("selftest/mutant-actually-ran", "[artifact-handoff] SELFTEST" in out,
              "the mutant exited without running its selftest, so its exit code says "
              "nothing about the mutation: %r" % out[-400:])
        check("selftest/red-under-mutation", p.returncode != 0,
              "committed-asset check was neutered and --selftest still passed")
        check("selftest/mutation-names-the-break", "untracked" in out, out)


def test_option_3_sites_paired():
    """Spec-walk 8 — the bare hand-off is gone AND the honest one is wired in.

    Negative alone would pass if someone deleted the hand-off entirely
    (Consistency item 3), so each absence is paired with a presence.
    """
    ship = SHIP.read_text(encoding="utf-8")
    proto = PROTO.read_text(encoding="utf-8")
    spike = SPIKE.read_text(encoding="utf-8")

    check("sites/ship-bare-handoff-gone",
          "Walkthrough (local, uncommitted)" not in ship, "the bare claim is back in ship")
    check("sites/ship-renders-local-line",
          "local-line --kind walkthrough" in ship, "ship no longer renders the walkthrough line")
    # The walkthrough hand-off is a THREE-line render, so it must be a standalone
    # block and NOT a markdown table cell — "paste its stdout verbatim" is
    # unfollowable inside a row. Pinned because the first draft got this wrong.
    check("sites/ship-handoff-is-a-standalone-marker",
          "\n  {{rendered by lib/artifact-handoff.py local-line --kind walkthrough" in ship)
    check("sites/ship-handoff-not-in-a-table-cell",
          not any("artifact-handoff.py local-line" in ln and ln.strip().startswith("|")
                  for ln in ship.splitlines()),
          "a three-line render cannot be pasted into a markdown row")
    check("sites/ship-closing-line-points-at-the-block",
          "see the walkthrough hand-off block above" in ship)
    check("sites/ship-local-uncommitted-claim-gone",
          "the ephemeral walkthrough is **local + uncommitted** — open it at the path named"
          not in ship)

    check("sites/prototype-renders-local-line",
          "local-line --kind prototype" in proto, "prototype no longer renders the gate-1 line")
    check("sites/prototype-bare-so-they-can-open-gone",
          "— so they can open it. Mention that the small floating comment dock" not in proto)
    check("sites/prototype-keeps-the-dock-note",
          "comment dock is **flow's**" in proto, "the dock note was lost in the rewrite")

    # The fan-out half (Consistency item 2): ship-spike is a second hand-off
    # surface for the same two artifacts, so leaving it would ship a contradiction.
    check("sites/spike-renders-local-line", "local-line --kind walkthrough" in spike)
    check("sites/spike-renders-frames", "artifact-handoff.py frames" in spike)
    check("sites/spike-has-before-after-heading", "\n## Before / after\n" in spike)
    # The prohibition belongs to the HAND-OFF TEXT, wherever authored — so it is
    # scoped to each skill's hand-off region and carries all six names. The first
    # draft checked one file for three names, chosen because a whole-file grep was
    # impossible (ship/SKILL.md and prototype/SKILL.md both legitimately say "iOS"
    # elsewhere) — a prohibition enforced only where it happened to be vacuously true.
    for name, text in (("ship", ship), ("spike", spike), ("prototype", proto)):
        region = _handoff_region(text)
        check("sites/%s-handoff-region-found" % name, region is not None,
              "no artifact-handoff region in %s — re-key this check, do not drop it"
              % name)
        if region is None:
            continue
        for c in CLIENTS:
            check("sites/%s-handoff-names-no-%s" % (name, c),
                  c.lower() not in region.lower(),
                  "the hand-off instruction in %s names a client (%s): %r"
                  % (name, c, region[:300]))


def test_coherence_is_blind_to_the_new_section():
    """Spec-walk 9 — identical pr-coherence verdicts with and without the section."""
    section = ("## Before / after\n\nCommitted frames from this PR's visual-history entry, "
               "pinned to `0f1e2d3`.\n\n**Before**\n"
               "![a](https://raw.githubusercontent.com/acme/app/%s/core-docs/x.png)\n"
               % ILLUSTRATIVE_SHA)
    # The Test-plan section is produced by the REAL renderer, not hand-written with a
    # hand-spelled stamp. The first draft of this case hand-wrote it and guessed the
    # marker, so the guard never matched and both arms ran unstamped; the second
    # spelled the marker right and still failed, because a stamp without the v1.22.0
    # content digest attests nothing. Driving the renderer is the only way to get a
    # fixture that is actually what ship publishes — and it cannot drift.
    tp = subprocess.run([sys.executable, str(RENDER_TP), "/nonexistent-buffer.json",
                         "--skipped", "platform library"],
                        capture_output=True, text=True, timeout=60).stdout
    i = tp.find("## Test plan")
    check("coherence/renderer-produced-a-section", i != -1, repr(tp[:200]))
    tp = tp[i:]
    check("coherence/fixture-is-stamped", _PROVENANCE_MARKER in tp, tp[-200:])
    ready = "## Summary\n- does a thing\n\n%s" + tp
    notready = ("## Summary\n- does a thing\n\n🚫 **NOT READY TO MERGE**\n\n%s" + tp)

    for label, tmpl, is_draft in (("ready", ready, "false"), ("not-ready", notready, "true")):
        results = []
        for variant, ins in (("without", ""), ("with", section + "\n")):
            with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                             encoding="utf-8") as f:
                f.write(tmpl % ins)
                path = f.name
            try:
                p = subprocess.run([sys.executable, str(COHERENCE), "coherence",
                                    "--body-file", path, "--is-draft", is_draft],
                                   capture_output=True, text=True, timeout=60)
                results.append((variant, p.returncode, (p.stdout + p.stderr).strip()))
            finally:
                Path(path).unlink(missing_ok=True)
        for variant, ins in (("without", ""), ("with", section + "\n")):
            with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                             encoding="utf-8") as f:
                f.write(tmpl % ins)
                path = f.name
            try:
                q = subprocess.run([sys.executable, str(COHERENCE),
                                    "test-plan-provenance", "--body-file", path,
                                    "--require-section"],
                                   capture_output=True, text=True, timeout=60)
                results.append(("prov-" + variant, q.returncode,
                                (q.stdout + q.stderr).strip()))
            finally:
                Path(path).unlink(missing_ok=True)
        (_, prc0, pout0), (_, prc1, pout1) = results[2:]
        check("coherence/%s-prov-reached-a-verdict" % label,
              pout0.startswith("[pr-coherence] ") and prc0 == 0,
              "the stamped fixture did not pass provenance, so the with/without "
              "comparison would be vacuous: rc=%d out=%r" % (prc0, pout0))
        check("coherence/%s-prov-same-exit" % label, prc0 == prc1,
              "%d vs %d — the new sibling heading moved the Test-plan parse"
              % (prc0, prc1))
        check("coherence/%s-prov-same-verdict" % label, pout0 == pout1,
              "without=%r\n        with=%r" % (pout0, pout1))

        (_, rc0, out0), (_, rc1, out1) = results[:2]
        # Instrument validation FIRST (Consistency item 4): "identical" is only
        # evidence if the engine actually reached a verdict. Two arms that both
        # crashed on a malformed fixture are also identical, and prove nothing.
        check("coherence/%s-engine-reached-a-verdict" % label,
              out0.startswith("[pr-coherence] ") and rc0 in (0, 1),
              "rc=%d out=%r" % (rc0, out0))
        check("coherence/%s-same-exit" % label, rc0 == rc1, "%d vs %d" % (rc0, rc1))
        check("coherence/%s-same-verdict" % label, out0 == out1,
              "without=%r\n        with=%r" % (out0, out1))


def test_ship_wiring():
    """Spec-walk 10 — installed-else-checkout fallback + a `{{…}}` marker, not prose."""
    for name, text in (("ship", SHIP.read_text(encoding="utf-8")),
                       ("spike", SPIKE.read_text(encoding="utf-8")),
                       ("prototype", PROTO.read_text(encoding="utf-8"))):
        check("wiring/%s-installed-first" % name,
              '"${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/artifact-handoff.py"' in text, name)
        check("wiring/%s-checkout-fallback" % name,
              '"plugins/flow/skills/ship/lib/artifact-handoff.py"' in text, name)
    ship = SHIP.read_text(encoding="utf-8")
    spike = SPIKE.read_text(encoding="utf-8")
    for name, text in (("ship", ship), ("spike", spike)):
        calls = [ln for ln in text.splitlines() if "artifact-handoff.py" in ln
                 and " frames " in ln]
        check("wiring/%s-calls-frames" % name, len(calls) >= 1,
              "found %d — re-key this check, do not drop it" % len(calls))
        check("wiring/%s-no-call-site-passes-private" % name,
              not any("--private" in ln for ln in calls),
              "`--private` is a test OVERRIDE: `false` forces the inline-image arm "
              "with no check, so a shipped call site passing it bypasses the "
              "visibility gate entirely. Shipped sites must use the default `auto`.")

    check("wiring/ship-section-is-a-marker",
          "{{rendered by lib/artifact-handoff.py frames" in ship,
          "the `## Before / after` body slot must be a {{…}} marker, never hand-authored prose")
    # Placement (Decision 5): above `## Test plan`, so the thing the human most
    # wants to look at is not below a 14-row provenance table.
    i_sec, i_tp = ship.find("\n  ## Before / after\n"), ship.find("\n  ## Test plan\n")
    check("wiring/ship-section-above-test-plan", -1 < i_sec < i_tp,
          "sec=%d test-plan=%d" % (i_sec, i_tp))
    check("wiring/ship-section-below-summary", ship.find("\n  ## Summary\n") < i_sec)

    # ONE rule ("the first thing the human wants to look at"), TWO positions: a
    # spike's deliverable is its question and answer, so the section goes after
    # `## Recommendation`, not after `## Summary`. Pinned with the rule stated, so a
    # later reader does not "harmonise" the two and silently change what a spike PR
    # leads with.
    s_rec, s_sec, s_disp = (spike.find("\n## Recommendation\n"),
                            spike.find("\n## Before / after\n"),
                            spike.find("\n## Disposability\n"))
    check("wiring/spike-section-after-recommendation", -1 < s_rec < s_sec < s_disp,
          "rec=%d sec=%d disp=%d" % (s_rec, s_sec, s_disp))
    # The section must be OMITTED on a change with no visual surface — otherwise it
    # publishes "No frames to show: <reason>" on the majority of PRs, an explanation
    # for an absence nobody expected. Both surfaces read the SAME shared predicate
    # §5c and §7a read, so a third notion of "visually significant" cannot appear.
    for name, text in (("ship", ship), ("spike", spike)):
        check("wiring/%s-omits-section-when-not-visual" % name,
              "visual-significance.py" in text
              and ("not visually significant" in text
                   or "visual_significant" in text),
              "%s must gate the `## Before / after` section on the shared "
              "visual-significance verdict" % name)

    check("wiring/ship-states-the-two-position-rule",
          "One rule, two positions" in ship,
          "the placement rule must be written down where the position is chosen")
    # A8 — the re-ship checklist names BOTH rendered sections, not just the Test plan.
    check("wiring/reship-names-before-after",
          "Leave `## Before / after` pinned to the SHA it was rendered at" in ship)
    # A5 (cheap half) — an unreplaced {{…}} marker must not survive the read-back.
    # PIN THE DECISION, NOT THE STRING (general.md item 4's corollary): the first
    # version of this check grepped the whole file for one `--forbid "{{"` literal and
    # went green on the single ILLUSTRATIVE occurrence, while the two paths that
    # actually publish a body — and both of ship-spike's — had no such guard. A
    # whole-file literal search cannot tell "every publish site is guarded" from
    # "one example mentions it".
    for name, text in (("ship", ship), ("spike", spike)):
        calls = [ln for ln in text.splitlines() if "flow_verify_pr_write" in ln
                 and "$N" in ln]
        check("wiring/%s-has-readback-call-sites" % name, len(calls) >= 2,
              "found %d — re-key this check, do not drop it" % len(calls))
        # The forbidden literals are the marker PREFIXES, never a bare `{{`:
        # `--forbid` is a plain substring test (pr-coherence.py readback), so a bare
        # `{{` also rejects a body that legitimately quotes a Handlebars/Jinja/Vue
        # template — halting hand-off after a SUCCESSFUL write. Caught by
        # /flow:audit-coverage on the PR that introduced it, whose own body describes
        # these slots. Both prefixes are required: `{{rendered by` covers the three
        # renderer slots, `{{provenance` covers the version rows.
        unguarded = [ln.strip()[:120] for ln in calls
                     if '--forbid "{{rendered by"' not in ln
                     or '--forbid "{{provenance"' not in ln]
        check("wiring/%s-every-readback-forbids-markers" % name, not unguarded,
              "a published renderer slot is a renderer that never ran, and no other "
              "gate sees it. Unguarded read-back call(s):\n        "
              + "\n        ".join(unguarded))
        overbroad = [ln.strip()[:120] for ln in calls if '--forbid "{{"' in ln]
        check("wiring/%s-forbid-is-not-overbroad" % name, not overbroad,
              "a bare `--forbid \"{{\"` rejects a body that legitimately quotes a "
              "template; forbid the marker prefixes instead:\n        "
              + "\n        ".join(overbroad))


def test_served_html_declares_utf8():
    """Every HTML surface flow EMITS declares UTF-8, and the prototype must too.

    Measured on an iPhone, 2026-10-04: a page served by `python3 -m http.server`
    (which sends `text/html` with no charset parameter — and is what
    `.claude/launch.json` serves `.flow` with) left Safari on iOS to guess, and it
    fell back to Latin-1: a `\u2713` rendered as `\u00e2\u0153\u201c`. The two renderers
    already declared it; the agent-authored PROTOTYPE had nothing requiring it, and
    `/flow:prototype` Step 8 injects the glyph-bearing annotation layer into exactly
    that file — so the page the human is asked to approve was the one that garbles.
    """
    for label, path in (("report-renderer",
                         FLOW / "skills" / "verify-build" / "lib" / "render-report.py"),
                        ("visual-history-skeleton",
                         FLOW / "skills" / "ship" / "lib" / "visual-history-skeleton.html")):
        txt = path.read_text(encoding="utf-8")
        check("utf8/%s-declares-charset" % label,
              'charset="utf-8"' in txt.lower(), "%s has no utf-8 declaration" % path)
    proto = PROTO.read_text(encoding="utf-8")
    check("utf8/prototype-skill-requires-charset",
          'charset="utf-8"' in proto and "MUST declare" in proto,
          "the agent authors this HTML, so the requirement has to be stated in the "
          "skill — nothing else enforces it")
    # The annotation layer is a FRAGMENT injected into a host page, so it inherits the
    # host's charset rather than declaring its own. Asserted so a future reader does
    # not "fix" it by adding a second <head>.
    layer = (FLOW / "skills" / "verify-build" / "lib" / "annotation-layer.html"
             ).read_text(encoding="utf-8")
    check("utf8/annotation-layer-is-a-fragment",
          "<html" not in layer.lower() and "<!doctype" not in layer.lower(),
          "the layer became a full document — it now needs its own charset, and the "
          "injection target assumption changed")


def test_ci_wired():
    """Spec-walk 11 — and CI's own join step fails the build on an unwired harness."""
    ci = CI.read_text(encoding="utf-8")
    check("ci/this-harness-wired",
          "python3 plugins/flow/evals/%s" % Path(__file__).name in ci,
          "an unwired harness contributes zero regression protection while appearing to")


def test_stale_ui_surface_claim():
    """Scope addition — the `uiSurface:false` self-claim is gone, AND the true one is there.

    Paired, because a bare absence assertion would also pass if the whole
    sentence were deleted (Consistency item 3).
    """
    schema = SCHEMA.read_text(encoding="utf-8")
    ship = SHIP.read_text(encoding="utf-8")
    check("uisurface/schema-stale-gone",
          "flow's own repo is uiSurface:false" not in schema)
    check("uisurface/schema-true-claim-present",
          "flow is uiSurface:TRUE" in schema and "v1.24.0" in schema)
    check("uisurface/ship-stale-gone",
          "flow's own repo is `uiSurface:false`" not in ship)
    check("uisurface/ship-true-claim-present",
          "Flow's own repo is **`uiSurface: true`**" in ship)
    # ...and the live config still backs the claim the docs now make.
    cfg = (REPO / "flow.config.json").read_text(encoding="utf-8")
    check("uisurface/live-config-agrees", '"uiSurface": true' in cfg,
          "the config flipped — the docs this PR corrected are now wrong the other way")
    # The generic consumer-facing mechanism text must SURVIVE: `uiSurface:false`
    # is still a real consumer state the skills must describe.
    check("uisurface/mechanism-text-kept",
          "skipped (uiSurface:false)" in ship and "non-UI projects (`uiSurface:false`)" in schema)


def main() -> int:
    tests = (test_committed_only, test_branch_match_paired,
             test_branch_guard_is_not_vacuous,
             test_predicate_reads_the_same_ref_as_the_url,
             test_visibility_three_arms,
             test_recon_only_live_entry, test_reader_matches_the_writer,
             test_url_shape, test_md_safety_layering,
             test_url_destination_cannot_break_out,
             test_captions_land_escaped_in_text_positions,
             test_caption_and_alt_cover_every_combination,
             test_every_record_field_is_neutralized, test_local_line,
             test_selftest_is_mutation_sensitive, test_option_3_sites_paired,
             test_coherence_is_blind_to_the_new_section, test_ship_wiring,
             test_served_html_declares_utf8,
             test_ci_wired, test_stale_ui_surface_claim)
    print("[artifact-handoff] %d case groups" % len(tests))
    for fn in tests:
        print(" %s" % fn.__name__)
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            _failures.append("%s raised %s: %s" % (fn.__name__, type(exc).__name__, exc))
            print("  FAIL  %s raised %s: %s" % (fn.__name__, type(exc).__name__, exc))
    if _failures:
        print("\n[artifact-handoff] FAIL — %d check(s):" % len(_failures))
        for f in _failures:
            print("  - %s" % f)
        return 1
    print("\n[artifact-handoff] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
