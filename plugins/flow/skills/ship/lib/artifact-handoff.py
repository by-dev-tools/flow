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

# The frame table and the branch slug are IMPORTED, never re-derived. `capture_frames`
# writes `pr-frames/<slug>/<label>-<name>.png`; this file reads it back. Two private
# copies of either value would be a writer and a reader that agree today and diverge
# the first time one is tidied -- and the divergence would be SILENT, because an empty
# read renders as the ordinary "no frames to show" line. Degrades to the
# visual-history source alone when the lib is unreachable, which is the pre-v1.65.0
# behaviour and still correct.
# `except Exception`, not `except ImportError`: computing the path can fail too.
# `parents[3]` raises IndexError for a copy of this file sitting at a shallower depth --
# which is exactly how `run_artifact_handoff_evals.py` runs its mutant (a temp-dir copy
# with PYTHONPATH set), so an ImportError-only guard crashed the engine on import and
# turned the MUTATION-SENSITIVITY pin red for a reason that had nothing to do with the
# mutation. A degraded import must degrade, including when the degradation is in the
# lookup rather than the module.
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
    from capture_frames import (  # noqa: E402
        FRAMES, FRAME_NAMES, FRAME_SIZES, SIDECAR, branch_slug, frames_dir)
except Exception:  # noqa: BLE001 - any failure means "no capture engine here"
    FRAMES = FRAME_NAMES = FRAME_SIZES = SIDECAR = branch_slug = frames_dir = None

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


def _audience_clause(audience: "str | None") -> str:
    """Who can open the link, stated NEXT TO the link.

    Not only in docs: the reader deciding whether to forward a URL is the one who
    needs to know its audience, and they are reading the hand-off, not the schema.
    Absent on purpose when the caller does not know — flow states what it was told,
    and inventing an audience would be the unverified-claim class this file exists
    to remove.
    """
    a = inline((audience or "").rstrip("."), 160)
    return (" — %s." % a) if a else ""


# ---------------------------------------------------------------- local-line

def render_local_line(kind: str, path: str, url: "str | None" = None,
                      audience: "str | None" = None,
                      chat_image: "str | None" = None) -> str:
    """One honest sentence about an uncommitted, machine-local artifact.

    The wording states a property of the FILE -- not committed, reachable only
    from the machine that produced it, not from this page -- so it survives
    whatever any particular client turns out to do.

    `url` is ADDITIVE and never a replacement. A served preview lives only as long as the process serving it, and the link can outlive that process — measured on one host, where the
    backend dies on workspace sleep while the URL registration survives — so a link
    can look live and be dead. The EMITTED line states the general property and not
    that host's policy: flow has measured one vendor, and an adapter pointed at a
    long-lived server has no sleep behaviour to describe. That is the same rule
    FORBIDDEN_CLIENTS enforces below, applied to hosts rather than clients. The local line is the process-independent
    floor; the URL is the convenience on top of it, and a reader who finds the link
    dead still has something true to act on.

    The URL is emitted as a BARE AUTOLINK, never a code span — the opposite of the
    treatment the path gets, deliberately. Measured on iOS: a code span renders as
    monospace text and is not tappable, so a code-spanned URL is unusable on the
    exact client this work is for.

    THE RULE: render it the way the reader can act on it. Monospace is the honest
    signal for a path that CANNOT be opened from the page; a live link is the honest
    signal for one that can. The two treatments look inconsistent and are not — they
    differ because the reader's available action differs. Do not "harmonise" them.

    `audience` goes NEXT TO the link, not only in docs — the person deciding whether
    to paste a URL onward is the one who needs to know who can open it.

    `chat_image` embeds ONE captured frame, and it is for a CHAT MESSAGE ONLY — never a
    PR body. The path is local and uncommitted, so in a PR body it would render as a
    broken image, which is the exact defect the rest of this engine exists to refuse.
    That is why it is accepted only for `--kind prototype`: the gate-1 presentation is
    the one hand-off flow renders into a chat message. A caller that passes it anywhere
    else gets a stated refusal, not a quietly-dropped flag.

    ONE image, deliberately. The ~100-word budget on the gate-1 message exists because
    "the messages I come to are too long and I don't really read them and I just end up
    approving anyway" — and while markdown image syntax costs no prose words, an image
    is not free attention. Two frames in a chat message is a scroll, which is the thing
    being fixed. The desktop frame is still committed and still in the PR body.
    """
    if url and not str(url).lower().startswith("https://"):
        # The adapter already refuses a non-https URL; this is the second gate,
        # because `url` can also arrive from a caller that composed it by hand.
        sys.stderr.write(
            "⚠️ [artifact-handoff] ignoring a non-https preview URL %r — the served page is "
            "sign-in-gated, so an unencrypted URL would downgrade the transport carrying that "
            "session. Emitting the local-path hand-off only.\n" % url)
        url = None
    clause = _audience_clause(audience)
    if kind == "walkthrough":
        if url:
            line = (
                "Walkthrough: %s%s If that link is dead, ask for it again and it will be "
                "re-served. The file itself is at %s, openable only where this pipeline ran."
                % (url, clause, code_span(one_line(path, 200)))
            )
        else:
            line = (
                "Walkthrough — a file on one machine's disk, not committed and not reachable "
                "from this page. You can only open it where this pipeline ran: %s."
                % code_span(one_line(path, 200))
            )
    elif kind == "prototype":
        if url:
            # The dock note sits directly after the audience, because it is the only
            # item that matters while the link WORKS; the fallback closes the line.
            line = (
                "Prototype: %s%s The small floating comment dock is flow's, not the design. "
                "If that link is dead, ask for it again and it will be re-served — or open "
                "%s, which works only where this session ran."
                % (url, clause, code_span(one_line(path, 200)))
            )
        else:
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
    # Scope the guard to FLOW'S OWN wording by removing the interpolated values
    # first. Its purpose is "flow must not claim a CLIENT'S BEHAVIOUR" — whether some
    # app opens a session-produced file is unmeasured. The two values removed here are
    # a different kind of statement and both legitimately contain a vendor name:
    #   · the audience is a measured ACCESS fact from project config, and "who can
    #     open this?" has no useful answer that avoids naming the sign-in;
    #   · the URL is a real address whose HOSTNAME is the host's, not flow's prose.
    # Checking the interpolated line flagged both, and a warning that fires on every
    # correctly-served hand-off is how people learn to ignore the warning — the
    # "teaches people to ignore the gate" failure this repo names explicitly.
    authored = line
    if clause:
        authored = authored.replace(clause, "")
    if url:
        authored = authored.replace(str(url), "")
    for name in FORBIDDEN_CLIENTS:
        if name.lower() in authored.lower():
            sys.stderr.write(
                "⚠️ [artifact-handoff] this hand-off names a client (%r). State the "
                "artifact's property, not a client's behaviour — whether a given app "
                "opens a session-produced file is unmeasured. Emitting it anyway.\n"
                % name)

    if chat_image:
        if kind != "prototype":
            sys.stderr.write(
                "⚠️ [artifact-handoff] ignoring --chat-image on --kind %s: a captured "
                "frame is a LOCAL, uncommitted file, and the only hand-off flow renders "
                "into a chat message is the gate-1 prototype. In a PR body that path is "
                "a broken image.\n" % kind)
        else:
            img = Path(chat_image)
            if not img.is_file():
                # Never claim a frame that is not there. A markdown image pointing at a
                # missing file is a broken image in the one message the human is
                # guaranteed to read -- strictly worse than the line without it, which
                # is already complete and correct.
                sys.stderr.write(
                    "⚠️ [artifact-handoff] no frame at %s, so the chat hand-off carries "
                    "no image. The line itself is unchanged and still correct.\n"
                    % chat_image)
            else:
                line += "\n\n![%s](%s)" % (_frame_alt(img.name, kind),
                                           url_path(chat_image))
    return line


def _frame_alt(filename: str, kind: str) -> str:
    """Alt text for a captured frame, derived from the name the capture engine wrote.

    Never empty: an empty alt is markdown's DECORATIVE signal, so the one reader who
    most needs the text alternative -- someone reading this gate on a screen reader --
    would be told nothing is there. Falls back to a generic that is true of any frame
    rather than guessing at a width it cannot confirm.
    """
    split = _split_frame_name(filename) if FRAME_NAMES else None
    if split:
        _label, frame = split
        w, h = FRAME_SIZES[frame]
        return inline("%s — first screen at %s width (%d×%d)"
                      % (kind.capitalize(), frame, w, h))
    return inline("%s screenshot" % kind.capitalize())


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


def render_frames(vh_path: str, branch_to_match: str, sha: str, root: str,
                  repo_arg: "str | None", private_mode: str) -> str:
    """The `## Before / after` section, or one line naming why there isn't one.

    `branch_to_match` is a value COMPARED against the branch recorded in the newest
    visual-history entry. On the sibling `captures` source the same CLI flag means
    something else entirely -- the source of a directory name -- so the two are bound
    to different identifiers rather than one `branch` that means whichever the reader
    assumes.
    """
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
    # Read as a VALUE TO MATCH, not as a path component — the other meaning the same
    # CLI flag carries on the `captures` source, one function below.
    if not branch_to_match or not entry["branch"] or entry["branch"] != branch_to_match:
        return _omit_with_record(
            "the newest visual-history entry belongs to a different change (its recorded "
            "branch is %s, and this PR's is %s), so embedding its frames would show you "
            "a different change's before/after under this PR's name."
            % (code_span(one_line(entry["branch"], 120)) if entry["branch"]
               else "not recorded",
               code_span(one_line(branch_to_match, 120)) if branch_to_match
               else "not resolvable here"),
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
    for f in frames:
        cap, alt = _caption_and_alt(f)
        rows.append({"rel": f["rel"], "cap": cap, "alt": alt})
    return _embed_section(
        rows, slug, vis, sha,
        public_lead="Committed frames from this PR's visual-history entry, pinned to %s."
                    % code_span(sha[:7]),
        closing=record)


def _embed_section(rows, slug, vis, sha, public_lead, closing):
    """The public/private/unknown embed policy — ONE copy, both frame sources.

    `rows` is already normalised to [{"rel", "cap", "alt"}], which is the only thing
    the two sources differ about: the visual-history source reads its captions out of
    a figcaption, the capture source derives them from the shared `FRAMES` table. The
    policy BELOW them — inline `<img>` only for a confirmed-public repo, `/blob/`
    links otherwise, and the sha pin named in every arm — is identical, and a second
    copy of it is the fan-out class this engine has already paid for once. Measured
    constraint it encodes, unchanged from v1.59.0: an unauthenticated raw fetch of a
    private blob returns 404, so a wrongly-public verdict costs a BROKEN image plus a
    body that claims something false. It fails closed.
    """
    out = []
    if vis == "public":
        for r in rows:
            url = "https://raw.githubusercontent.com/%s/%s/%s" % (
                slug, sha, url_path(r["rel"]))
            # The bold caption line is emitted only when there IS a caption: an empty
            # label rendered `****`, four literal asterisks, on the one branch a
            # reader actually looks at.
            # The `\n` between caption and image is the ONE load-bearing soft break
            # in this engine: GitHub renders it as a line break, which is what puts
            # the label directly above its frame. Every prose paragraph here is one
            # logical line for the opposite reason — do not "normalize" this one.
            out.append(("**%s**\n" % r["cap"] if r["cap"] else "")
                       + "![%s](%s)" % (r["alt"], url))
        return "%s\n\n%s\n\n%s\n\n%s" % (
            HEADING, public_lead, "\n\n".join(out), closing)

    for r in rows:
        url = "https://github.com/%s/blob/%s/%s" % (slug, sha, url_path(r["rel"]))
        out.append("- [%s](%s)" % (r["cap"] or r["alt"], url))

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
        HEADING, lead, "\n".join(out), code_span(sha[:7]), closing)


def captures_dir(vh_path: str, branch: str) -> "str | None":
    """Where THIS PR's captured frames live: `<dir of visualHistoryPath>/pr-frames/<slug>/`.

    Deliberately NOT the curated `visual-history-assets/` directory. `/flow:ship` §5c
    calls that record curated rather than a per-PR dump and enforces a hard skip it
    describes as "a mechanical floor against the per-PR-dump failure mode" (FB-0042);
    writing every PR's screenshots there would defeat the one rule that keeps it
    readable.

    THE OWN-PR GUARD IS THE DIRECTORY NAME, and that is a stronger guarantee than the
    visual-history source's. There, a previous PR's frames are excluded by COMPARING a
    recorded branch against this one -- a comparison that has already been wrong once
    (two empty strings compared equal). Here another PR's frames are not reachable at
    all: nothing outside this slug's directory is ever listed.
    """
    # `branch` is read here as the SOURCE OF A PATH COMPONENT -- which PR's directory
    # to look in -- NOT as a value to match against a recorded branch. That is the
    # other meaning the same flag carries on the `record` source, and the two are kept
    # under different parameter names at every read point for exactly that reason.
    if frames_dir is None:
        return None
    return frames_dir(vh_path, branch)


def _committed_descriptions(rel_dir: str, root: str, sha: str) -> dict:
    """label -> description, read from the sidecar AT THE NAMED SHA.

    `git show <sha>:<path>`, not the working tree, for the same reason every other read
    in this engine is pinned: the PR body is a projection of the commit, and a
    description that exists only in this session is a claim the commit does not support.
    Absent or unparseable is simply {} — the alt then names the label and the viewport,
    which is correct, just thinner.
    """
    try:
        r = subprocess.run(["git", "show", "%s:%s/%s" % (sha, rel_dir, SIDECAR)],
                           cwd=root, capture_output=True, text=True, timeout=20)
        if r.returncode != 0:
            return {}
        data = json.loads(r.stdout or "{}")
    except (OSError, subprocess.SubprocessError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    out = {}
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(v.get("title"), str) and v["title"].strip():
            out[str(k)] = v["title"]
    return out


def _split_frame_name(filename: str):
    """`prototype-phone.png` -> ("prototype", "phone"), else None.

    Split from the RIGHT against the known frame names, because a label may itself
    contain a hyphen (`verify-walkthrough`) while a frame name never does. A file the
    capture engine did not write returns None and is ignored -- the directory is
    flow's, but a human can still drop something in it, and a stray file must not
    become an unlabelled row in a PR body.
    """
    stem = filename[:-4] if filename.lower().endswith(".png") else None
    if not stem:
        return None
    for name in (FRAME_NAMES or ()):
        suffix = "-" + name
        if stem.endswith(suffix) and len(stem) > len(suffix):
            return stem[:-len(suffix)], name
    return None


def render_frames_auto(vh_path: str, branch: str, sha: str, root: str,
                       repo_arg: "str | None", private_mode: str) -> str:
    """Captures when this PR committed any, the curated record otherwise.

    THE SHIPPED CALL SITES USE THIS, and the reason is a defect this engine had for
    exactly one review cycle. `/flow:ship` chose its source from whether a capture
    ADAPTER validates — which says nothing about whether §5d actually captured. Every
    §5d skip (not visually significant, no prototype and no walkthrough, a refused
    page, a detached HEAD) still selected the captures source, so a consumer who
    configured the adapter AND had a curated visual-history entry with committed frames
    got "No frames to show" in place of their images. Both skills' own prose promised
    the opposite — "the section falls back to the visual-history record" — and that
    fallback simply did not exist.

    So the fall-through lives HERE, in the engine, rather than in two shell blocks that
    would each have to remember it. `--source captures` stays available and strict, and
    the evals drive that one: a mode whose failure is invisible must still be testable
    on its own.
    """
    section, had_frames = _captures_section(vh_path, branch, sha, root, repo_arg,
                                            private_mode)
    if had_frames:
        return section
    return render_frames(vh_path, branch, sha, root, repo_arg, private_mode)


def render_frames_from_captures(vh_path: str, branch_for_dir: str, sha: str, root: str,
                                repo_arg: "str | None", private_mode: str) -> str:
    """Captures ONLY — no fall-through. The strict mode the evals drive."""
    return _captures_section(vh_path, branch_for_dir, sha, root, repo_arg,
                             private_mode)[0]


def _captures_section(vh_path: str, branch_for_dir: str, sha: str, root: str,
                      repo_arg: "str | None", private_mode: str):
    """-> (section, had_frames). `had_frames` is what lets the caller fall through.

    A boolean rather than "did the text contain `![`": the private and unknown arms
    emit links and no image syntax, so a text test would fall through for exactly the
    population that most needs the frames (general.md item 4's exit-code corollary —
    prefer the signal the producer maintains over a grep of its output).
    """
    """The `## Before / after` section built from this PR's COMMITTED captured frames.

    Same discipline as the visual-history source and the same reason: the section is a
    projection of the COMMIT, never of this session. A frame earns a row only when
    `git cat-file -t <sha>:<path>` reports a blob, so the body cannot claim an image
    the commit does not contain. The only thing that differs is where the candidate
    list comes from -- a directory listing here, a parsed record there -- and the
    embed policy below both is one function.

    `branch_for_dir` names a DIRECTORY, not a value compared against anything. On the
    record source the same CLI flag means "the branch the newest entry must match";
    keeping one identifier for both meanings is how a guard quietly starts answering a
    different question than its caller thinks.
    """
    if not SHA40.match(sha or ""):
        die("--sha must be a full 40-character commit sha (got %r). A short sha can "
            "become ambiguous and a branch name 404s once the branch is deleted at merge."
            % sha)

    if branch_slug is None:
        return _omit("the capture engine could not be loaded, so this pipeline cannot "
                     "tell which directory holds this PR's frames. Nothing is guessed."), False

    rel_dir = captures_dir(vh_path, branch_for_dir)
    if rel_dir is None:
        return _omit(
            "this PR's branch name is %s, which yields no per-PR frame directory — so "
            "there is no directory that belongs to this change alone, and frames are "
            "never read from a shared one."
            % (code_span(one_line(branch_for_dir, 120)) if branch_for_dir
               else "not resolvable here (a detached HEAD reads as an empty branch)")), False

    abs_dir = Path(root) / rel_dir
    try:
        names = sorted(q.name for q in abs_dir.iterdir() if q.is_file())
    except OSError:
        names = []

    # Order by the SHARED frame table, phone first — not by the directory listing,
    # which sorts `desktop` above `phone` and would silently invert the one ordering
    # decision the table records (the phone frame leads because phone review is the
    # whole reason this exists).
    parsed = []
    for n in names:
        split = _split_frame_name(n)
        if split:
            parsed.append((split[0], split[1], n))
    parsed.sort(key=lambda t: (FRAME_NAMES.index(t[1]), t[0]))

    if not parsed:
        return _omit(
            "this PR committed no captured frames under %s. That is the normal state "
            "when the change has no visual surface, when no page was available to "
            "photograph, or when the capture was refused — each of which states its own "
            "reason in the pipeline log." % code_span(one_line(rel_dir, 160))), False

    cited = ["%s/%s" % (rel_dir, n) for _lbl, _fr, n in parsed]
    kept = [(lbl, fr, n) for lbl, fr, n in parsed
            if git_tracked("%s/%s" % (rel_dir, n), root, sha)]
    if not kept:
        return _omit(
            "this PR captured %d %s that %s not in the commit this PR points at (%s), "
            "so there is nothing GitHub can resolve. Frames have to be committed and "
            "pushed before the body can name them."
            % (len(cited), "frame" if len(cited) == 1 else "frames",
               "is" if len(cited) == 1 else "are",
               ", ".join(code_span(one_line(c, 120)) for c in cited))), False

    slug, vis = resolve_repo_and_visibility(private_mode, repo_arg, root)
    if not slug:
        # True, not False: frames DO exist in the commit — this pipeline just cannot name
        # the repo to link them from. Falling through to the record would print a
        # different, also-unresolvable section and bury the actual problem.
        return _omit("this pipeline couldn't confirm which GitHub repo to link to, so it "
                     "isn't guessing at image URLs."), True

    labels = []
    for lbl, _fr, _n in kept:
        if lbl not in labels:
            labels.append(lbl)
    described = _committed_descriptions(rel_dir, root, sha)

    rows = []
    for lbl, fr, n in kept:
        w, h = FRAME_SIZES[fr]
        # The label is in the caption ONLY when it disambiguates. With two labels in one
        # directory the captions were both "Phone — 390×844": two identical visible
        # strings, and in the links arm two links with the same text pointing at
        # different files (WCAG 2.4.4). With one label it is noise.
        prefix = ("%s — " % lbl) if len(labels) > 1 else ""
        what = described.get(lbl)
        rows.append({
            "rel": "%s/%s" % (rel_dir, n),
            # "first screen", not just the dimensions: a capture is ONE SCREENFUL at
            # that viewport, and a caption that reads as the page's size tells a reader
            # who scrolled nothing that they saw the whole thing.
            "cap": inline("%sFirst screen at %s width — %d×%d"
                          % (prefix.capitalize(), fr, w, h)),
            # The alt is the WHOLE content for someone who cannot see the image, so it
            # leads with what the page is — read from the committed sidecar — and the
            # viewport comes second. Without a description it degrades to naming the
            # label, which is thin but true; it is never empty, because an empty alt is
            # markdown's DECORATIVE signal and would tell a screen-reader user at the
            # merge gate that nothing is there.
            "alt": inline("%s — first screen at %s width, %d×%d"
                          % (what or lbl, fr, w, h)),
        })

    what_all = ", ".join(code_span(one_line(l, 60)) for l in labels)
    # Name the absence. The heading promises a comparison and this source renders one
    # state at two widths; a reader arriving at "Before / after" should not have to work
    # out for themselves that there is no before. (The heading itself is pinned at
    # several sites and a per-source heading is a real fan-out — roadmap, not here.)
    lead = ("Frames captured from this PR's %s, pinned to %s — not to the branch tip, so "
            "they keep resolving after the branch is deleted at merge. There is no "
            "*before* here: these are the surface as this PR leaves it, at two widths, "
            "each showing the first screen rather than the whole page."
            % (what_all, code_span(sha[:7])))
    closing = ("Committed under %s. They are this PR's own frames by construction: nothing "
               "outside that per-PR directory is read."
               % code_span(one_line(rel_dir, 160)))
    return _embed_section(rows, slug, vis, sha, public_lead=lead,
                          closing=closing), True


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


def _selftest_captures(check, root, vh_rel, cap_rel, CSHA, SHA, _git, _head_sha):
    """The captures + chat-image arms, split out so the engine-absent guard is ONE branch.

    Reached only when the shared frame table imported. Inlining these under an `if`
    would have put the whole block one indent deeper for a reason that is about imports,
    not about the assertions.
    """
    cap = render_frames_from_captures(vh_rel, "feat/empty_feed", CSHA, root,
                                      "acme/app", "false")
    check("captures/two-images", cap.count("![") == 2, cap)
    check("captures/phone-first", cap.index("phone width") < cap.index("desktop width"),
          cap)
    check("captures/dimensions-labelled", "390×844" in cap and "1280×900" in cap, cap)
    check("captures/names-the-label", "prototype" in cap, cap)
    check("captures/says-it-is-the-first-screen", cap.count("first screen") >= 2, cap)
    check("captures/names-the-absent-before", "no *before* here" in cap, cap)
    check("captures/ignores-non-frame-file", "stray" not in cap, cap)
    check("captures/full-sha", len(re.findall(r"/[0-9a-f]{40}/", cap)) == 2, cap)
    check("captures/alt-is-never-empty", "![](" not in cap, cap)

    # KNOWN NEGATIVE, and the mutation target: an UNCOMMITTED frame never appears.
    # It must carry a REAL frame suffix (`-phone`), or the non-frame-file filter
    # excludes it first and this arm passes whether or not `git_tracked` works --
    # which is what the first cut did, caught only by running the mutation.
    Path(root, cap_rel, "draft-phone.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    mixed_cap = render_frames_from_captures(vh_rel, "feat/empty_feed", CSHA, root,
                                            "acme/app", "false")
    check("captures/uncommitted-excluded", "draft-phone" not in mixed_cap, mixed_cap)
    check("captures/committed-still-emitted", mixed_cap.count("![") == 2, mixed_cap)
    Path(root, cap_rel, "draft-phone.png").unlink()

    # KNOWN NEGATIVE: ANOTHER PR's frames are unreachable -- not excluded by a
    # comparison, but never listed. The second directory is committed so that the
    # only thing stopping it is the slug, not trackedness.
    other = "dev-docs/pr-frames/other-branch"
    os.makedirs(os.path.join(root, other))
    Path(root, other, "prototype-phone.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    _git(["add", other], root); _git(["commit", "-qm", "other"], root)
    OSHA = _head_sha(root)
    mine = render_frames_from_captures(vh_rel, "feat/empty_feed", OSHA, root,
                                       "acme/app", "false")
    check("captures/other-prs-frames-unreachable", "other-branch" not in mine, mine)
    check("captures/mine-still-rendered", mine.count("![") == 2, mine)
    theirs = render_frames_from_captures(vh_rel, "other/branch", OSHA, root,
                                         "acme/app", "false")
    check("captures/each-branch-sees-its-own",
          "other-branch" in theirs and "feat-empty-feed" not in theirs, theirs)

    # A sha PREDATING the frames emits nothing -- the predicate and the URL read
    # the same ref, so they cannot disagree.
    early_cap = render_frames_from_captures(vh_rel, "feat/empty_feed", SHA, root,
                                            "acme/app", "false")
    check("captures/sha-predating-frames-omits", "![" not in early_cap, early_cap)

    # Private fails CLOSED here too -- the SAME policy function, not a second copy.
    priv_cap = render_frames_from_captures(vh_rel, "feat/empty_feed", CSHA, root,
                                           "acme/app", "true")
    check("captures/private-no-raw-host",
          "raw.githubusercontent.com" not in priv_cap and "![" not in priv_cap, priv_cap)
    check("captures/private-two-blob-links",
          priv_cap.count("/blob/%s/" % CSHA) == 2, priv_cap)

    # A branch that slugs to nothing (a detached HEAD) gets no directory at all.
    det = render_frames_from_captures(vh_rel, "", CSHA, root, "acme/app", "false")
    check("captures/unsluggable-branch-omits",
          "![" not in det and "no per-PR frame directory" in det, det)

    # The curated record is UNTOUCHED by any of this -- paired with the positive
    # that the per-PR directory is where the frames actually are.
    curated = sorted(q.name for q in Path(root, "dev-docs/visual-history-assets").iterdir())
    check("captures/curated-record-untouched",
          curated == ["feed-empty-after.png", "feed-empty-before.png", "untracked.png"],
          repr(curated))
    check("captures/frames-live-in-the-per-pr-dir",
          Path(root, cap_rel, "prototype-phone.png").is_file())

    # --- THE FALL-THROUGH. A capture source that found nothing must not retire the
    # curated record: that regression shipped for one review cycle and the only thing
    # that caught it was driving both sources against one repo.
    auto_hit = render_frames_auto(vh_rel, "feat/empty_feed", CSHA, root, "acme/app",
                                  "false")
    check("auto/prefers-captures-when-present",
          "pr-frames" in auto_hit and auto_hit.count("![") == 2, auto_hit)
    # Restore the two-figure record: an earlier arm left a recon-only entry in place, and
    # falling back onto THAT would prove only that the fall-through reached a different
    # omission. The arm has to land on a record that genuinely has frames.
    Path(root, vh_rel).write_text(_VH % {
        "branch": "feat/empty_feed",
        "figs": "".join(_FIG_IMG % {
            "label": lbl, "src": "visual-history-assets/" + f, "alt": alt}
            for lbl, f, alt in [
                ("Before — activity feed, empty", "feed-empty-before.png",
                 "blank gray panel with no call to action"),
                ("After — activity feed, empty", "feed-empty-after.png",
                 "centered illustration and a button"),
            ])}, encoding="utf-8")
    auto_miss = render_frames_auto(vh_rel, "feat/empty_feed", SHA, root, "acme/app",
                                   "false")
    check("auto/falls-back-to-the-record",
          "visual-history-assets" in auto_miss and auto_miss.count("![") == 2,
          "a sha with no committed captures must render the RECORD's frames, not an "
          "omission: %s" % auto_miss)
    check("auto/strict-captures-still-omits",
          "![" not in render_frames_from_captures(vh_rel, "feat/empty_feed", SHA, root,
                                                  "acme/app", "false"),
          "--source captures must stay strict; the fall-through belongs to `auto` alone")

    # ------------------------------------------------- the chat image
    frame = os.path.join(root, cap_rel, "prototype-phone.png")
    withimg = render_local_line("prototype", "/abs/p.presented.html",
                                chat_image=frame)
    check("chat/one-image", withimg.count("![") == 1, withimg)
    check("chat/alt-describes-the-frame",
          "phone width (390×844)" in withimg, withimg)
    check("chat/line-still-intact", "local file" in withimg, withimg)
    # NEGATIVE: a missing frame is never claimed.
    noimg = render_local_line("prototype", "/abs/p.presented.html",
                              chat_image=os.path.join(root, "nope.png"))
    check("chat/missing-frame-claims-nothing", "![" not in noimg, noimg)
    check("chat/line-unchanged-without-frame",
          noimg == render_local_line("prototype", "/abs/p.presented.html"), noimg)
    # NEGATIVE: never into a PR-body hand-off, where a local path is a broken image.
    wrongkind = render_local_line("walkthrough", "/abs/r.html", chat_image=frame)
    check("chat/refused-on-walkthrough", "![" not in wrongkind, wrongkind)


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

        # ---------------------------------------------------- the captures source
        # Same discipline, different candidate list. KNOWN POSITIVE first.
        cap_rel = "dev-docs/pr-frames/feat-empty-feed"
        os.makedirs(os.path.join(root, cap_rel))
        for n in ("prototype-phone.png", "prototype-desktop.png", "prototype-stray.txt"):
            Path(root, cap_rel, n).write_bytes(b"\x89PNG\r\n\x1a\n")
        _git(["add", cap_rel + "/prototype-phone.png", cap_rel + "/prototype-desktop.png",
              cap_rel + "/prototype-stray.txt"], root)
        _git(["commit", "-qm", "frames"], root)
        CSHA = _head_sha(root)

        if FRAME_NAMES is None:
            # The capture engine is unreachable -- this file running from a copy outside
            # the plugin tree, which is how `run_artifact_handoff_evals.py` drives its
            # mutant. Assert the DEGRADATION rather than skipping silently: no image
            # syntax and a stated reason. Then stop, because every arm in the helper
            # needs the shared frame table to say anything at all.
            degraded = render_frames_from_captures(vh_rel, "feat/empty_feed", CSHA, root,
                                                   "acme/app", "false")
            check("captures/degrades-when-engine-absent",
                  "![" not in degraded
                  and "capture engine could not be loaded" in degraded, degraded)
        else:
            _selftest_captures(check, root, vh_rel, cap_rel, CSHA, SHA, _git, _head_sha)
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
    print("[artifact-handoff] SELFTEST PASS — known-positive, known-negatives, all three renderers")
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
    ll.add_argument("--url", default=None,
                    help="ADDITIVE served URL (https only). The local path is still "
                         "emitted, because a served preview can die while its "
                         "registration survives.")
    ll.add_argument("--audience", default=None,
                    help="who can open --url, stated next to the link")
    ll.add_argument("--chat-image", default=None,
                    help="ONE captured frame to embed. CHAT MESSAGE ONLY — the path is "
                         "local and uncommitted, so in a PR body it is a broken image. "
                         "Accepted only with --kind prototype.")

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
    # A FLAG rather than a second subcommand, because the two sources share every
    # downstream rule -- tracked-at-the-named-sha, public/private, the sha pin, the
    # escaping -- and one surface is what keeps them from drifting apart. The cost is
    # that `--branch` now carries two meanings: on `record` it is a value MATCHED
    # against the newest entry's recorded branch, on `captures` it is the SOURCE OF A
    # DIRECTORY NAME. They are bound to differently-named parameters inside
    # (`branch_to_match` vs `branch_for_dir`) so the collision is visible where it is
    # read, not only in the head of whoever wrote it.
    fr.add_argument("--source", default="record",
                    choices=["record", "captures", "auto"],
                    help="`record` reads the committed visualHistoryPath entry (default, "
                         "unchanged); `captures` reads ONLY this PR's committed frames "
                         "under <dir of visualHistoryPath>/pr-frames/<branch-slug>/; "
                         "`auto` prefers those frames and falls back to the record when "
                         "this PR committed none. SHIPPED CALL SITES USE `auto` — a "
                         "configured capture adapter must never retire a consumer's "
                         "curated record.")

    args = ap.parse_args(argv)
    # argparse owns the flag. A pre-parse `"--selftest" in argv` scan matched it
    # ANYWHERE, so `frames --repo --selftest` silently ran the selftest instead of
    # erroring, and the declared flag was never read.
    if args.selftest:
        return selftest()
    if args.cmd == "local-line":
        print(render_local_line(args.kind, args.path, args.url, args.audience,
                                args.chat_image))
        return 0
    if args.cmd == "frames":
        root = args.root or (_repo_root() or os.getcwd())
        if args.source == "captures":
            print(render_frames_from_captures(args.visual_history, args.branch, args.sha,
                                              root, args.repo, args.private))
            return 0
        if args.source == "auto":
            print(render_frames_auto(args.visual_history, args.branch, args.sha, root,
                                     args.repo, args.private))
            return 0
        print(render_frames(args.visual_history, args.branch, args.sha, root,
                            args.repo, args.private))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
