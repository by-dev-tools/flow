#!/usr/bin/env python3
"""Regression test: extract_session.py session-transcript discovery.

Protects two safety-critical behaviors in `find_session_file` /
`slugify_cwd` (extract_session.py). Silent failure here starves the
reviewers of session context without surfacing an error — they emit
"session file not found" and audit nothing.

Class of bug this fixture protects against:

1. **cwd->slug encoding drift.** Claude Code names its
   `~/.claude/projects/<dir>` transcript directory by replacing *every*
   non-ASCII-alphanumeric character with `-` (so `/`, `.`, `_`, spaces all
   map to `-`). An earlier version replaced only `/`, so any path containing
   a `.` — e.g. every `.claude/worktrees/...` dev session — mismatched and
   the reviewers ran context-starved. This asserts the full encoding.

2. **session-id primary lookup.** When `CLAUDE_CODE_SESSION_ID` is exported
   (Claude Code sets it in spawned subprocesses, incl. skill `!`-backtick
   substitutions), discovery must resolve the transcript by exact id,
   independent of cwd encoding, and fall back to the cwd-slug only when the
   var is absent or doesn't resolve to exactly one file.

Run standalone: python3 plugins/flow/evals/security/test_session_discovery.py
Run via harness: python3 plugins/flow/evals/run_security_evals.py

Exit code 0 if all asserts pass; 1 if any assert fails.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Test lives at plugins/flow/evals/security/test_session_discovery.py
# Target lives at plugins/flow/scripts/extract_session.py
PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = PLUGIN_ROOT / "scripts"
assert (SCRIPTS / "extract_session.py").exists(), \
    f"extract_session.py not found at expected path: {SCRIPTS / 'extract_session.py'}"
sys.path.insert(0, str(SCRIPTS))
import extract_session as E  # noqa: E402


# slugify_cwd returns the dir name WITHOUT the leading `-`; the caller composes
# the project dir as f"-{slug}". We assert the composed dir name, which is what
# must match Claude Code's real `~/.claude/projects/<dir>` name.
SLUG_CASES = [
    # (cwd, expected composed project-dir name)
    ("/Users/benyamron/dev/flow/.claude/worktrees/interesting-sammet-bccfcf",
     "-Users-benyamron-dev-flow--claude-worktrees-interesting-sammet-bccfcf"),  # dotted: the bug
    ("/Users/x/my.app", "-Users-x-my-app"),          # `.` -> `-`
    ("/a/b_c/d e", "-a-b-c-d-e"),                     # `_` and space -> `-`
    ("/Users/Foo/Bar", "-Users-Foo-Bar"),            # case preserved, no collapsing
]


def check_slug() -> list[str]:
    failures = []
    for cwd, expected in SLUG_CASES:
        got = f"-{E.slugify_cwd(cwd)}"
        if got != expected:
            failures.append(f"slugify_cwd({cwd!r}) -> {got!r}, expected {expected!r}")
    return failures


def _write_session(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"type":"user","message":{"role":"user","content":"hi"},"uuid":"u1",'
        '"timestamp":"2026-06-02T00:00:00.000Z"}\n'
        '{"type":"assistant","message":{"role":"assistant","content":'
        '[{"type":"text","text":"a plan:\\n1. one\\n2. two\\n3. three"}]},'
        '"uuid":"u2","timestamp":"2026-06-02T00:00:01.000Z"}\n'
    )


def check_discovery() -> list[str]:
    failures = []
    saved_home = os.environ.get("HOME")
    saved_sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    saved_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            os.environ["HOME"] = str(tmp)  # Path.home() honours $HOME on POSIX
            projects = tmp / ".claude" / "projects"

            # --- Case 1: session-id primary resolves regardless of cwd ---
            sid = "abc12345-0000-4000-8000-000000000001"
            # transcript lives under a dir whose name does NOT match cwd, to
            # prove resolution is by id, not by cwd-slug.
            _write_session(projects / "-some-unrelated-dir" / f"{sid}.jsonl")
            os.environ["CLAUDE_CODE_SESSION_ID"] = sid
            # cwd points somewhere with no matching project dir at all
            os.chdir(tmp)
            found = E.find_session_file()
            if found is None or found.name != f"{sid}.jsonl":
                failures.append(
                    f"session-id primary: expected {sid}.jsonl, got {found!r}")

            # --- Case 2: session-id set but no matching file -> slug fallback ---
            os.environ["CLAUDE_CODE_SESSION_ID"] = "deadbeef-0000-4000-8000-000000000999"
            dotted = tmp / "proj.dir" / "sub"
            dotted.mkdir(parents=True, exist_ok=True)
            os.chdir(dotted)
            # Build the expected dir from the *actual* post-chdir cwd, not the
            # tempdir string: on macOS /tmp -> /private/tmp, so os.getcwd()
            # (what find_session_file reads) is symlink-resolved. Using it keeps
            # the test's expectation aligned with the function under test.
            slug_dir = projects / f"-{E.slugify_cwd(os.getcwd())}"
            _write_session(slug_dir / "ffffffff-0000-4000-8000-000000000002.jsonl")
            found = E.find_session_file()
            if found is None or found.parent != slug_dir:
                failures.append(
                    f"slug fallback (dotted cwd): expected file under {slug_dir}, got {found!r}")

            # --- Case 3: nothing resolves -> None (graceful, not crash) ---
            del os.environ["CLAUDE_CODE_SESSION_ID"]
            empty = tmp / "no-transcript-here"
            empty.mkdir(parents=True, exist_ok=True)
            os.chdir(empty)
            found = E.find_session_file()
            if found is not None:
                failures.append(f"no-match case: expected None, got {found!r}")

            # --- Case 4: glob / path-traversal injection via the env var ---
            # A tampered CLAUDE_CODE_SESSION_ID must NOT wildcard-match or
            # traverse to a planted transcript. With a metachar payload the id
            # guard rejects it -> falls back to the cwd slug, which (in an empty
            # cwd) resolves to nothing -> None. A planted transcript that `*`
            # WOULD match proves the guard is load-bearing.
            _write_session(projects / "-victim-dir" / "victim000-0000-4000-8000-000000000abc.jsonl")
            os.chdir(empty)  # cwd with no matching project dir
            for payload in ("*", "[a-z]*", "../../../etc/passwd", "*/*", "?"):
                os.environ["CLAUDE_CODE_SESSION_ID"] = payload
                found = E.find_session_file()
                if found is not None:
                    failures.append(
                        f"glob-injection: CLAUDE_CODE_SESSION_ID={payload!r} "
                        f"should not resolve, got {found!r}")

            # --- Case 5: ambiguous id (same id under two dirs) -> None ---
            # The len(matches)==1 guard must refuse to guess when a malformed CC
            # state leaves the same session id under two project dirs.
            dup = "dupe0000-0000-4000-8000-00000000dup0"
            _write_session(projects / "-dir-one" / f"{dup}.jsonl")
            _write_session(projects / "-dir-two" / f"{dup}.jsonl")
            if E._find_session_by_id(dup) is not None:
                failures.append("ambiguous id (>1 match): expected None, got a file")
    finally:
        os.chdir(saved_cwd)
        if saved_home is not None:
            os.environ["HOME"] = saved_home
        if saved_sid is not None:
            os.environ["CLAUDE_CODE_SESSION_ID"] = saved_sid
        else:
            os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
    return failures


def main() -> int:
    failures = check_slug() + check_discovery()
    if failures:
        print("FAIL: test_session_discovery")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("PASS: test_session_discovery (slug encoding + session-id primary + slug fallback + graceful None)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
