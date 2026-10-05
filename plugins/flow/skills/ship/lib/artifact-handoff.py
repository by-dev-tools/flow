#!/usr/bin/env python3
"""Render the PR-body hand-offs for flow's two kinds of visual artifact.

Two surfaces, one engine, because both are claims a PR body makes about a file a
human is being asked to look at:

  local-line  the hand-off for an EPHEMERAL, uncommitted artifact (the
              verify-build walkthrough; a gate-1 prototype). It states where the
              file can and cannot be opened, and names no client -- whether a
              given app opens a session-produced HTML file is unmeasured, so a
              claim about one would be exactly the unverified-completion class
              /flow:audit-completion exists to catch.

  frames      the `## Before / after` section: the committed visual-history
              frames for THIS PR, rendered so they appear in the PR body itself.
              Or one explicit line naming why there are none.

`frames` reads only the COMMITTED record -- the visual-history file on disk, and
`git ls-files` for whether each cited frame is actually tracked at HEAD. It never
reads the in-session entry JSON. That is the same non-forgeable-projection
discipline render-test-plan.py enforces: the body cannot claim an image that is
not in the commit, because the only thing it reads IS the commit.

Two measured constraints shape the output (paired probe, 2026-10-03):
  * `raw.githubusercontent.com` for a PUBLIC repo blob -> http 200.
  * the same shape for a PRIVATE repo blob -> http 404, unauthenticated.
So inline images are a public-repo-only mechanism. This fails CLOSED: anything
other than a confirmed-public repo gets `/blob/` links, which an authorised
viewer can open on any client. A wrongly-private verdict costs a missing inline
image; a wrongly-public verdict costs a BROKEN image plus a body that claims
something false -- reintroducing the exact defect the local-line half removes.

`--selftest` runs the engine against a temp git repo holding a known-positive and
a known-negative before anyone trusts a quiet result (.claude/rules/general.md
Consistency item 4). It is mutation-sensitive by construction: make
`git_tracked()` return True unconditionally and it exits non-zero.
"""

from __future__ import annotations

import argparse
import html as htmllib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

# Everything this engine reads out of the visual-history record -- a frame `src`, a
# figcaption, an alt string -- is text it does not control, pasted into a markdown
# construct in the body a human reads at the merge gate. The policy is SHARED with
# `render-test-plan.py` rather than re-derived: a private copy was weaker (it passed
# `<`, the HTML-comment opener) and would have put two escaping policies in one body.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from md_safe import code_span, inline, one_line  # noqa: E402  (sibling-module import, house pattern)

HEADING = "## Before / after"

# The client names this engine must never emit. Research § 6 Q1/Q2 -- whether a
# given client opens a session-produced HTML file, and what a tapped file:// path
# does there -- are open and unanswered. Stating the ARTIFACT's own property is
# true on every client; naming a client is a guess that would also be wrong in
# the sync-the-files-to-a-laptop case.
FORBIDDEN_CLIENTS = ("iOS", "iPhone", "iPad", "Android", "Safari", "Conductor")

SHA40 = re.compile(r"^[0-9a-f]{40}$")



def die(msg: str) -> "None":
    sys.stderr.write("⚠️ [artifact-handoff] %s\n" % msg)
    raise SystemExit(2)


# ---------------------------------------------------------------- local-line

def render_local_line(kind: str, path: str) -> str:
    """One honest sentence about an uncommitted, machine-local artifact.

    The wording states a property of the FILE -- not committed, reachable only
    from the machine that produced it, not from this page -- so it survives
    whatever any particular client turns out to do.
    """
    if kind == "walkthrough":
        line = (
            "Walkthrough — a file on one machine's disk, not committed and not reachable "
            "from this page. You can only open it where this pipeline ran: %s."
            % code_span(one_line(path, 200))
        )
    elif kind == "prototype":
        line = (
            "Your prototype is a local file — it lives at %s, and you can only open it "
            "where this session ran, not from a link. The small floating comment dock is "
            "flow's, not the design." % code_span(one_line(path, 200))
        )
    else:
        die("unknown --kind %r (expected walkthrough|prototype)" % kind)
        return ""
    # Warn, do NOT die. The property is already asserted twice in CI (this file's
    # `--selftest` and the eval harness), so this copy can only fire in a window
    # where CI did not run -- and there its failure mode was WORSE than the defect:
    # `die()` exits 2, and the shipped call site is
    # `python3 "$AH" local-line … || echo "⚠️ … renderer absent at $AH"`, so a
    # reworded sentence printed a false "the renderer is missing" diagnosis and no
    # hand-off at all. A warning keeps the line flowing and still says what is wrong.
    for name in FORBIDDEN_CLIENTS:
        if name.lower() in line.lower():
            sys.stderr.write(
                "⚠️ [artifact-handoff] this hand-off names a client (%r). State the "
                "artifact's property, not a client's behaviour — whether a given app "
                "opens a session-produced file is unmeasured. Emitting it anyway.\n"
                % name)
    return line


# ------------------------------------------------------- the committed record

def newest_entry(vh_text: str) -> "dict | None":
    """Parse the FIRST <article class="vh-entry"> -- the file is reverse-chronological.

    Returns {"branch", "figures": [{"label","alt","src"|None,"recon":bool}]} or None
    when the record carries no entry at all.
    """
    starts = [m.start() for m in re.finditer(r'<article class="vh-entry"', vh_text)]
    if not starts:
        return None
    end = starts[1] if len(starts) > 1 else len(vh_text)
    block = vh_text[starts[0]:end]

    branch = None
    meta = re.search(r'<div class="meta">(.*?)</div>', block, re.S)
    if meta:
        code = re.search(r"<code>(.*?)</code>", meta.group(1), re.S)
        if code:
            branch = htmllib.unescape(code.group(1)).strip()

    figures = []
    for fig in re.finditer(r"<figure>(.*?)</figure>", block, re.S):
        body = fig.group(1)
        cap = re.search(r"<figcaption>(.*?)</figcaption>", body, re.S)
        label = inline(htmllib.unescape(cap.group(1))) if cap else ""
        # `recon` is tested FIRST, deliberately. The writer does not escape an
        # agent-authored `html` block, so a CSS/SVG reconstruction may legally carry
        # an inline or data-URI `<img>`; testing img first classified it as a cited
        # frame and printed "cites 1 frame that is not in the commit
        # (`data:image/png;base64,…`)" -- fails closed, with the wrong reason and a
        # base64 fragment pasted into the body.
        if '<div class="recon"' in body:
            figures.append({"label": label, "src": None, "alt": "", "recon": True})
            continue
        img = re.search(r'<img src="(.*?)" alt="(.*?)">', body, re.S)
        if img:
            figures.append({
                "label": label,
                "src": htmllib.unescape(img.group(1)).strip(),
                "alt": inline(htmllib.unescape(img.group(2))),
                "recon": False,
            })
    return {"branch": branch, "figures": figures}


def git_tracked(rel_path: str, root: str, sha: str = "HEAD") -> bool:
    """Does `sha` contain this path as a BLOB? The question that makes the URL honest.

    `git ls-files --error-unmatch` was the wrong question: it answers "is this in the
    INDEX?", while the URL is pinned to `--sha`. So a frame `git add`-ed but not
    committed passed, and rendered as an inline image at a commit that does not
    contain it -- a broken image in the PR body, which this skill's own prose calls
    strictly worse than an honest absence. `cat-file -t <sha>:<path>` asks about the
    exact ref the URL names, so the predicate and the link cannot disagree, and a
    `--sha` predating the asset is caught too.

    Requiring the type to be `blob` is load-bearing, not decoration: `cat-file -e`
    succeeds for ANY object, so a `src` naming a DIRECTORY passed and rendered a
    broken image at a tree URL -- the predicate and the link disagreeing in precisely
    the way the sentence above promises they cannot. A `<rev>:<path>^{blob}` peel does
    NOT work here, measured: in the `<rev>:<path>` form git parses `^{blob}` as part of
    the PATH and reports it missing, so that spelling would have refused every
    legitimate frame. The type check is the one that discriminates.

    MUTATION TARGET: `--selftest` asserts an uncommitted frame is excluded, so making
    this return True unconditionally turns the selftest red. That pairing is the point
    -- a committed-asset check nobody can break is not a check.
    """
    try:
        r = subprocess.run(
            ["git", "cat-file", "-t", "%s:%s" % (sha, rel_path)],
            cwd=root, capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0 and r.stdout.strip() == "blob"


def _gh_repo_json(root: str) -> dict:
    """`gh repo view` as a dict, or {} when gh is absent / erroring / unparseable.

    Collapsing every failure to {} is what lets the caller state the fail-closed
    default ONCE, at its exit. It previously re-stated `vis = "unknown"` on each of
    three failure paths plus the exit, so a fourth failure mode would have had to
    remember a fourth copy -- and forgetting it would be invisible, because the exit
    silently covered it (.claude/rules/general.md Consistency item 2).
    """
    gh = shutil.which("gh")
    if not gh:
        return {}
    try:
        r = subprocess.run([gh, "repo", "view", "--json", "isPrivate,nameWithOwner"],
                           cwd=root, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return {}
        data = json.loads(r.stdout or "{}")
        return data if isinstance(data, dict) else {}
    except (OSError, subprocess.SubprocessError, ValueError):
        return {}


def resolve_repo_and_visibility(mode: str, repo_arg: "str | None", root: str):
    """-> (slug|None, "public"|"private"|"unknown").

    `mode` is the --private flag: 'false' forces public, 'true' forces private,
    'auto' asks gh. gh absent, unauthenticated, or erroring -> 'unknown', which
    renders exactly like private. Failing closed is the whole design.
    """
    slug = repo_arg
    vis = {"true": "private", "false": "public"}.get(mode)

    if slug is None or vis is None:
        data = _gh_repo_json(root)
        reported = str(data.get("nameWithOwner") or "")
        if slug is None and reported:
            slug = reported
        # Only trust gh's visibility for the repo gh is actually describing. With an
        # explicit `--repo` that disagrees with the local checkout, the slug would
        # have come from the flag and `isPrivate` from a DIFFERENT repository -- a
        # public verdict for someone else's repo is how a private blob gets an inline
        # `<img>`. Disagreement falls through to `unknown`, i.e. links.
        # `slug == reported` UNCONDITIONALLY. The first cut read
        # `(not reported or slug == reported)`, which made an absent
        # `nameWithOwner` SATISFY the very guard the comment above promises — a
        # `{"isPrivate": false}` payload with no slug yielded `public` for a slug
        # then taken from `git remote get-url`, i.e. possibly a different repo. A
        # latent fail-open in the one gate whose whole job is to fail closed.
        if vis is None and isinstance(data.get("isPrivate"), bool) and slug == reported:
            vis = "private" if data["isPrivate"] else "public"

    if slug is None:
        # Last resort for the slug only -- never for visibility. A remote URL
        # says nothing about whether the repo is public.
        try:
            r = subprocess.run(["git", "remote", "get-url", "origin"], cwd=root,
                               capture_output=True, text=True, timeout=20)
            if r.returncode == 0:
                m = re.search(r"(?:github\.com[:/])([^/]+/[^/]+?)(?:\.git)?\s*$", r.stdout)
                if m:
                    slug = m.group(1)
        except (OSError, subprocess.SubprocessError):
            pass

    return slug, (vis or "unknown")


def _omit(reason: str) -> str:
    """The section, with one explicit line saying why there is nothing to show.

    The shared opener lives HERE and not in the seven callers: it is the one string
    that must read identically across every omission branch, and it was the only
    part not centralised.
    """
    return "%s\n\nNo frames to show: %s" % (HEADING, reason)


def _omit_with_record(reason: str, vh_path: str) -> str:
    """An omission that points at the record, WITH the caveat the happy path carries.

    The full-value branch ends "GitHub shows that file's source, not the rendered
    page" -- the single most useful sentence in the render, because it tells a reader
    what tapping that path will and will not get them. Six omission branches handed
    over the SAME path with a bare `See \`X\``, and the asymmetry landed hardest where
    it was least affordable: a recon-only entry is meaningful ONLY when rendered, and
    it is the branch every flow ship takes. The happy path anticipated the confusion;
    the common path reproduced it.
    """
    return _omit("%s The record is %s — note that GitHub shows that file's source, not "
                 "the rendered page." % (reason, code_span(one_line(vh_path, 160))))


def render_frames(vh_path: str, branch: str, sha: str, root: str,
                  repo_arg: "str | None", private_mode: str) -> str:
    """The `## Before / after` section, or one line naming why there isn't one."""
    if not SHA40.match(sha or ""):
        die("--sha must be a full 40-character commit sha (got %r). A short sha can "
            "become ambiguous and a branch name 404s once the branch is deleted at merge."
            % sha)

    vh_abs = Path(vh_path)
    if not vh_abs.is_absolute():
        vh_abs = Path(root) / vh_path
    try:
        text = vh_abs.read_text(encoding="utf-8")
    except OSError:
        # The ONLY branch that does not get the record caveat: there is no file to
        # caveat. Stated here so the asymmetry reads as deliberate.
        return _omit(
            "there is no visual-history record at %s, so this PR has no committed "
            "before/after frames to embed." % code_span(one_line(vh_path, 160)))

    entry = newest_entry(text)
    if entry is None:
        # NOT `_omit_with_record`: the caveat earns its line only where the record
        # holds something the reader might want. On a genuinely EMPTY record it would
        # point them at a file this same sentence just called empty, and spend a
        # second line explaining how that file renders. The no-FIGURES arm below
        # keeps the caveat, because there the entry exists and carries the rationale.
        return _omit(
            "the visual-history record at %s carries no entries yet."
            % code_span(one_line(vh_path, 160)))

    # Load-bearing: on a ship where the visual-history step legitimately skipped, the
    # newest entry belongs to a PREVIOUS PR. Embedding its frames would show the
    # reviewer a different change's before/after while labelling it this one's --
    # worse than no images at all, and the default if this is not checked.
    # `(entry["branch"] or "") != branch` compared two empty strings as EQUAL, and
    # both halves are reachable: `branch` is documented-optional in the entry-JSON
    # contract, and the shipped call site passes `$(git branch --show-current)`,
    # which is EMPTY on a detached HEAD. So a branchless entry from a previous PR
    # plus a detached HEAD embedded that PR's frames under this one's name — the
    # outcome this check exists to prevent, produced by the check itself. An absent
    # value is never a match (general.md item 4: a zero-match filter is not a
    # confirmation).
    if not branch or not entry["branch"] or entry["branch"] != branch:
        return _omit_with_record(
            "the newest visual-history entry belongs to a different change (its recorded "
            "branch is %s, and this PR's is %s), so embedding its frames would show you "
            "a different change's before/after under this PR's name."
            % (code_span(one_line(entry["branch"], 120)) if entry["branch"]
               else "not recorded",
               code_span(one_line(branch, 120)) if branch else "not resolvable here"),
            vh_path)

    cited = [f for f in entry["figures"] if f["src"]]
    recon = [f for f in entry["figures"] if f["recon"]]

    if not cited:
        if recon:
            return _omit_with_record(
                "this PR's visual-history entry carries hand-built diagrams rather than "
                "screenshots, so there is no committed image to embed.", vh_path)
        return _omit_with_record(
            "this PR's visual-history entry carries no before/after figures.", vh_path)

    # The repo-relative path is the load-bearing value -- it is what makes a URL
    # honest -- so it is resolved ONCE here and read back below. Recomputing it at
    # each URL builder was three chances for the three to drift apart.
    for f in cited:
        f["rel"] = _sibling(vh_path, f["src"])
    frames = [f for f in cited if git_tracked(f["rel"], root, sha)]
    if not frames:
        return _omit_with_record(
            "this PR's visual-history entry cites %d %s that %s not in the commit this "
            "PR points at (%s), so there is nothing GitHub can resolve."
            % (len(cited), "frame" if len(cited) == 1 else "frames",
               "is" if len(cited) == 1 else "are",
               ", ".join(code_span(one_line(f["rel"], 120)) for f in cited)), vh_path)

    slug, vis = resolve_repo_and_visibility(private_mode, repo_arg, root)
    if not slug:
        return _omit_with_record(
            "this pipeline couldn't confirm which GitHub repo to link to, so it isn't "
            "guessing at image URLs.", vh_path)

    record = ("The full record — rationale, decision test, questions carried — is %s. "
              "GitHub shows that file's source, not the rendered page; these frames are "
              "its pictures." % code_span(one_line(vh_path, 160)))

    rows = []
    if vis == "public":
        for f in frames:
            url = "https://raw.githubusercontent.com/%s/%s/%s" % (
                slug, sha, url_path(f["rel"]))
            cap, alt = _caption_and_alt(f)
            # The bold caption line is emitted only when there IS a caption: an empty
            # label rendered `****`, four literal asterisks, on the one branch a
            # reader actually looks at.
            # The `\n` between caption and image is the ONE load-bearing soft break
            # in this engine: GitHub renders it as a line break, which is what puts
            # the label directly above its frame. Every prose paragraph here is one
            # logical line for the opposite reason — do not "normalize" this one.
            rows.append(("**%s**\n" % cap if cap else "") + "![%s](%s)" % (alt, url))
        return "%s\n\nCommitted frames from this PR's visual-history entry, pinned to %s.\n\n%s\n\n%s" % (
            HEADING, code_span(sha[:7]), "\n\n".join(rows), record)

    for f in frames:
        url = "https://github.com/%s/blob/%s/%s" % (slug, sha, url_path(f["rel"]))
        cap, alt = _caption_and_alt(f)
        rows.append("- [%s](%s)" % (cap or alt, url))

    if vis == "private":
        lead = ("Private repo, so GitHub can't show these inline. Open them directly — they "
                "need the same GitHub sign-in this page did:")
    else:
        lead = ("Couldn't tell whether this repo is public, so these are links rather than "
                "inline images. Open them directly — they may need the same GitHub sign-in "
                "this page did:")
    # All three arms close the same way. The private + unknown arms previously named
    # neither the record nor the SHA pin -- so the one population this half of the
    # change exists for (a private `uiSurface:true` consumer) got the thinner
    # hand-off, and was never told the frames are pinned to a commit rather than to
    # the branch tip, which is the whole point of pinning them.
    return "%s\n\n%s\n\n%s\n\nPinned to %s. %s" % (
        HEADING, lead, "\n".join(rows), code_span(sha[:7]), record)


def _caption_and_alt(f: dict):
    """-> (caption, alt). `alt` is NEVER empty; `caption` may be.

    An empty `alt` is markdown's signal for a DECORATIVE image: a screen-reader
    user at the merge gate is told nothing is there, and a reader whose image
    failed to load sees a blank line. `insert-visual-history.py` defaults `label`
    to "" and only warns about a missing `alt`, so both are reachable without
    malice -- and this section was moved to the top of the body precisely for the
    reader who most needs the text alternative.

    When `alt` is absent the caption is reused as alt AND kept visible. An earlier
    cut suppressed the visible caption to avoid a screen reader announcing the same
    string twice, but on the inline-image arm that removed the Before/After label
    entirely -- two unlabelled stacked frames, on the narrow viewport this work
    targets, with no way to tell which was which. One duplicate announcement is the
    cheaper cost.
    """
    cap = f.get("label") or ""
    alt = f.get("alt") or ""
    if not alt:
        # `inline()`, not raw. This is the engine's THIRD markdown text position
        # (after `label` and `alt`, both escaped at parse time), and it was the one
        # with no policy: `src` arrives `htmllib.unescape`-d, so a filename holding
        # `)` or a newline broke the `![…](…)` construct open from the ALT side --
        # the identical breakout `url_path()` closes in the sibling branch of this
        # same `if`. One body, one policy, all three positions.
        alt = cap or inline("before/after frame %s (no caption recorded)"
                            % Path(f.get("src") or "").name)
    return cap, alt


def url_path(rel: str) -> str:
    """Percent-encode a repo-relative path for use inside a URL.

    This was the one value in this engine that NO escaping policy touched: `label`
    and `alt` go through `inline()`, and a rejected `src` goes through
    `code_span(one_line(...))`, but the ACCEPTED path was interpolated raw into
    `![alt](url)`. A committed frame whose FILENAME embeds a newline plus markdown
    (`assets/a\n\n[Approve](https://evil)\nb.png`) therefore broke the image
    construct open and rendered the attacker's lines as live markdown in the body a
    human reads at the merge gate — including, potentially, a forged `## Test plan`
    heading above the real one, which is the section `pr-coherence.py` keys on.

    Percent-encoding subsumes the space/paren/angle cases an angle-bracketed
    destination was special-casing, and unlike `<…>` it is immune to line endings
    (a `<…>` destination may not contain one, per CommonMark). `safe="/"` keeps the
    path separators, which must stay literal for the URL to resolve.

    Precondition for the attack is a tracked file whose name holds control
    characters — loud in `git status` and in the diff, and the author is a
    collaborator — so this is low severity. It ships because the fix is one call and
    because an unneutralized sink in a published artifact should not exist at all.
    """
    return urllib.parse.quote(str(rel), safe="/")


def _repo_root():
    """`flow_scratch.repo_root()`, imported rather than re-implemented.

    A private `git rev-parse --show-toplevel` in a shipped `skills/*/lib/` file is
    the exact shape `run_prototype_gate_evals.py::engine-has-no-private-git-helper`
    exists to refuse one directory over. Lazy + guarded because `scripts/` is not on
    the path by default and a missing helper must degrade (the caller falls back to
    cwd) rather than break a ship.
    """
    try:
        scripts = str(Path(__file__).resolve().parents[3] / "scripts")
        if scripts not in sys.path:          # else sys.path grows on every call
            sys.path.insert(0, scripts)
        import flow_scratch  # noqa: PLC0415  (lazy by design — see docstring)
        return flow_scratch.repo_root()
    except Exception:  # noqa: BLE001  (any failure means "fall back to cwd")
        return None


def _sibling(vh_path: str, src: str) -> str:
    """Resolve a frame src, which is relative to the visual-history file's own dir.

    No traversal guard here, deliberately: `normpath` may well walk out of the repo, and
    the `git ls-files --error-unmatch` check downstream is what refuses it. One gate --
    "is it tracked at HEAD" -- answers traversal, absolute paths and typos alike, and a
    second overlapping guard would be a second thing to keep correct.
    """
    parent = str(Path(vh_path).parent)
    rel = os.path.normpath(os.path.join(parent, src)) if parent not in ("", ".") else src
    return rel.replace(os.sep, "/")


# ------------------------------------------------------------------ selftest

def _git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


_VH = """<!doctype html><html><body>
<article class="vh-entry" id="e1">
<h2>Empty activity feed</h2>
<div class="meta">#9<span class="sep">·</span>2026-10-03<span class="sep">·</span><code>%(branch)s</code></div>
<div class="ba">%(figs)s</div>
</article>
</body></html>"""

_FIG_IMG = ('<figure><figcaption>%(label)s</figcaption>'
            '<img src="%(src)s" alt="%(alt)s"></figure>')
_FIG_RECON = ('<figure><figcaption>%(label)s</figcaption><div class="recon">'
              '<div style="height:4px"></div></div></figure>')

def _head_sha(root) -> str:
    """The temp repo's REAL head.

    A fabricated sha used to be fine, because the predicate asked the index. Now it
    asks `cat-file -e <sha>:<path>` — the same ref the URL names — so a fixture sha
    must be a commit that exists, which is exactly the coupling the fix introduced.
    """
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                          text=True, timeout=20).stdout.strip()


def selftest() -> int:
    """Known-positive FIRST, then the negatives. Mutation-sensitive by design."""
    fails = []

    def check(name, cond, detail=""):
        if not cond:
            fails.append("%s%s" % (name, (": " + detail) if detail else ""))

    with tempfile.TemporaryDirectory() as td:
        root = os.path.join(td, "repo")
        assets = os.path.join(root, "dev-docs", "visual-history-assets")
        os.makedirs(assets)
        _git(["init", "-q", "-b", "main"], root)
        _git(["config", "user.email", "s@e.lf"], root)
        _git(["config", "user.name", "selftest"], root)

        vh_rel = "dev-docs/visual-history.html"
        for n in ("feed-empty-before.png", "feed-empty-after.png", "untracked.png"):
            Path(assets, n).write_bytes(b"\x89PNG\r\n\x1a\n")

        figs_two = "".join(_FIG_IMG % {
            "label": lbl, "src": "visual-history-assets/" + f, "alt": alt}
            for lbl, f, alt in [
                ("Before — activity feed, empty", "feed-empty-before.png",
                 "blank gray panel with no call to action"),
                ("After — activity feed, empty", "feed-empty-after.png",
                 "centered illustration and a button"),
            ])
        Path(root, vh_rel).write_text(_VH % {"branch": "feat/empty_feed", "figs": figs_two},
                                      encoding="utf-8")
        # Commit the record + exactly TWO of the three frames. `untracked.png`
        # stays on disk and out of the index on purpose.
        _git(["add", vh_rel,
              "dev-docs/visual-history-assets/feed-empty-before.png",
              "dev-docs/visual-history-assets/feed-empty-after.png"], root)
        _git(["commit", "-qm", "selftest"], root)
        SHA = _head_sha(root)
        check("fixture/real-sha", bool(SHA40.match(SHA)), repr(SHA))

        # --- KNOWN POSITIVE: public repo, two committed frames -> two inline images.
        pub = render_frames(vh_rel, "feat/empty_feed", SHA, root, "acme/app", "false")
        check("positive/heading", pub.startswith(HEADING + "\n\n"), repr(pub[:40]))
        check("positive/two-images", pub.count("![") == 2, "count=%d" % pub.count("!["))
        check("positive/raw-host", pub.count("https://raw.githubusercontent.com/acme/app/") == 2)
        check("positive/full-sha", len(re.findall(r"/[0-9a-f]{40}/", pub)) == 2,
              "urls must carry the 40-char sha, not a short one or a branch")
        check("positive/no-branch-name", "feat/empty_feed" not in pub)
        check("positive/alt-text", "blank gray panel with no call to action" in pub)
        check("positive/record-pointer", vh_rel in pub, pub)

        # --- a frame with neither figcaption nor alt: never `****`, never an empty
        # alt (an empty alt is markdown's DECORATIVE signal, so a screen-reader user
        # at the merge gate is told nothing is there).
        Path(root, vh_rel).write_text(_VH % {
            "branch": "feat/empty_feed",
            "figs": '<figure><figcaption></figcaption>'
                    '<img src="visual-history-assets/feed-empty-before.png" alt=""></figure>',
        }, encoding="utf-8")
        bare = render_frames(vh_rel, "feat/empty_feed", SHA, root, "acme/app", "false")
        check("bare/no-empty-emphasis", "****" not in bare, bare)
        check("bare/has-a-text-alternative", "![](" not in bare, bare)
        check("bare/names-the-file", "feed-empty-before.png" in bare, bare)
        Path(root, vh_rel).write_text(_VH % {"branch": "feat/empty_feed", "figs": figs_two},
                                      encoding="utf-8")

        # --- KNOWN NEGATIVE (the mutation target): an UNTRACKED frame is never
        # emitted. Make git_tracked() return True unconditionally and this fails.
        Path(root, vh_rel).write_text(_VH % {
            "branch": "feat/empty_feed",
            "figs": figs_two + _FIG_IMG % {
                "label": "Third", "src": "visual-history-assets/untracked.png",
                "alt": "not committed"},
        }, encoding="utf-8")
        mixed = render_frames(vh_rel, "feat/empty_feed", SHA, root, "acme/app", "false")
        check("negative/untracked-excluded", "untracked.png" not in mixed,
              "an uncommitted frame reached the PR body — the committed-asset check is not working")
        check("negative/tracked-still-emitted", mixed.count("![") == 2,
              "count=%d" % mixed.count("!["))

        # --- a sha that PREDATES the frames emits nothing. The URL and the predicate
        # now read the same ref, so they cannot disagree — the arm an index-based
        # predicate could not express at all.
        PRE_SHA = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=root,
                                 capture_output=True, text=True,
                                 timeout=20).stdout.strip()
        if PRE_SHA and PRE_SHA != SHA:
            early = render_frames(vh_rel, "feat/empty_feed", PRE_SHA, root, "acme/app",
                                  "false")
            check("negative/sha-predating-frames-omits", "![" not in early, early)

        # --- all-untracked -> omission naming the frames, no image syntax at all.
        Path(root, vh_rel).write_text(_VH % {
            "branch": "feat/empty_feed",
            "figs": _FIG_IMG % {"label": "Only", "src": "visual-history-assets/untracked.png",
                                "alt": "x"}}, encoding="utf-8")
        none_tracked = render_frames(vh_rel, "feat/empty_feed", SHA, root, "acme/app", "false")
        check("negative/all-untracked-omits", "![" not in none_tracked)
        check("negative/all-untracked-names-reason",
              "not in the commit this PR points at" in none_tracked, none_tracked)

        # --- private + gh-absent: /blob/ links for the SAME two frames, zero raw host.
        Path(root, vh_rel).write_text(_VH % {"branch": "feat/empty_feed", "figs": figs_two},
                                      encoding="utf-8")
        priv = render_frames(vh_rel, "feat/empty_feed", SHA, root, "acme/app", "true")
        check("private/no-raw-host", "raw.githubusercontent.com" not in priv)
        check("private/two-blob-links", priv.count("/blob/%s/" % SHA) == 2,
              "count=%d" % priv.count("/blob/%s/" % SHA))
        check("private/no-image-syntax", "![" not in priv)
        check("private/says-why",
              "Private repo" in priv and "can't show these inline" in priv, priv)
        # All three arms must close the same way: the record AND the sha pin. The
        # private arm named neither, so the one population this half of the change
        # exists for got the thinner hand-off.
        check("private/names-the-record", vh_rel in priv, priv)
        check("private/names-the-sha-pin",
              "Pinned to" in priv and SHA[:7] in priv, priv)

        # The gh-ABSENT arm is deliberately NOT here. Driving it in-process means
        # mutating `os.environ["PATH"]`, and a mutable-global dance with restore
        # logic does not belong in a library a consumer imports. The arm is covered
        # faithfully, as a subprocess with its own `env=`, by
        # evals/run_artifact_handoff_evals.py::test_visibility_three_arms
        # (`visibility/gh-absent-*`). What this selftest owes per
        # .claude/rules/general.md item 4 is the known-positive plus the untracked
        # known-negative, and both are above.

        # --- branch mismatch: zero rows, and the reason says so.
        mism = render_frames(vh_rel, "some/other-branch", SHA, root, "acme/app", "false")
        check("mismatch/zero-rows", "![" not in mism and "/blob/" not in mism)
        check("mismatch/names-reason",
              "different change" in mism and "feat/empty_feed" in mism, mism)
        # The branch names must land as CODE spans, not escaped text: `feat/empty_feed`
        # carries an underscore precisely so a `code_span(inline(...))` regression
        # would show up here as a visible backslash instead of hiding behind a
        # metacharacter-free fixture name.
        check("mismatch/no-visible-escapes", "\\_" not in mism, mism)

        # --- recon-only: the no-frames line, not an empty section.
        Path(root, vh_rel).write_text(_VH % {
            "branch": "feat/empty_feed",
            "figs": (_FIG_RECON % {"label": "Before"}) + (_FIG_RECON % {"label": "After"}),
        }, encoding="utf-8")
        rec = render_frames(vh_rel, "feat/empty_feed", SHA, root, "acme/app", "false")
        check("recon/no-image-syntax", "![" not in rec)
        check("recon/names-reason",
              "hand-built diagrams" in rec and "no committed image" in rec, rec)
        check("recon/not-empty-section", len(rec.split("\n\n", 1)[-1].strip()) > 40)

        # --- missing record: still a complete section with a reason.
        gone = render_frames("dev-docs/nope.html", "feat/empty_feed", SHA, root, "acme/app", "false")
        check("missing/names-reason", "no visual-history record" in gone)

    # --- local-line, both kinds.
    w = render_local_line("walkthrough", ".flow/report.html")
    p = render_local_line("prototype", "/abs/.flow/prototypes/s/prototype.presented.html")
    check("local/walkthrough-uncommitted", "not committed" in w)
    check("local/walkthrough-where", "only open it where" in w, w)
    check("local/prototype-local-file", "local file" in p)
    check("local/prototype-where", "only open it where" in p, p)
    for name in FORBIDDEN_CLIENTS:
        check("local/no-client-%s" % name, name.lower() not in (w + p).lower())

    if fails:
        print("[artifact-handoff] SELFTEST FAIL — %d check(s):" % len(fails))
        for f in fails:
            print("  - %s" % f)
        return 1
    print("[artifact-handoff] SELFTEST PASS — known-positive, known-negatives, both renderers")
    return 0


# ---------------------------------------------------------------------- main

def main(argv) -> int:
    ap = argparse.ArgumentParser(prog="artifact-handoff.py", add_help=True,
                                 description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true",
                    help="run the engine's own known-positive + known-negatives")
    sub = ap.add_subparsers(dest="cmd")

    ll = sub.add_parser("local-line", help="hand-off line for an uncommitted local artifact")
    ll.add_argument("--kind", required=True, choices=["walkthrough", "prototype"])
    ll.add_argument("--path", required=True)

    fr = sub.add_parser("frames", help="the `## Before / after` section, or why there is none")
    fr.add_argument("--visual-history", required=True,
                    help="flow.config.json.visualHistoryPath (repo-relative)")
    fr.add_argument("--branch", required=True, help="this PR's branch; must match the entry")
    fr.add_argument("--sha", required=True, help="full 40-char pushed HEAD")
    fr.add_argument("--repo", default=None, help="owner/name; resolved via gh when omitted")
    # OVERRIDE, not a shipped path: every call site in ship/ship-spike/prototype uses
    # the default `auto`, which resolves visibility and fails closed. `false` forces
    # the inline-image arm with no check, so a future call site passing it would
    # bypass the gate entirely — pinned by
    # run_artifact_handoff_evals.py::wiring/no-shipped-call-site-passes-private.
    fr.add_argument("--private", default="auto", choices=["auto", "true", "false"],
                    help="OVERRIDE for tests; shipped call sites must use the default "
                         "`auto` so the visibility gate actually runs")
    fr.add_argument("--root", default=None, help="repo root (default: cwd's toplevel)")

    args = ap.parse_args(argv)
    # argparse owns the flag. A pre-parse `"--selftest" in argv` scan matched it
    # ANYWHERE, so `frames --repo --selftest` silently ran the selftest instead of
    # erroring, and the declared flag was never read.
    if args.selftest:
        return selftest()
    if args.cmd == "local-line":
        print(render_local_line(args.kind, args.path))
        return 0
    if args.cmd == "frames":
        root = args.root or (_repo_root() or os.getcwd())
        print(render_frames(args.visual_history, args.branch, args.sha, root,
                            args.repo, args.private))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
