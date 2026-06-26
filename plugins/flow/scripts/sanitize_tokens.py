#!/usr/bin/env python3
"""Scrub personal-project tokens out of a lesson before it reaches the PUBLIC
flow repo. Used by /flow:contribute as a fail-closed gate.

The flow repo is public and must stay project-agnostic (CLAUDE.md: "plugin
artifacts must contain no project-specific tokens"). A lesson harvested in a
personal project carries that project's names/paths/urls in its evidence
window. This module scrubs them.

IMPORTANT — this script (itself a shipped plugin artifact) embeds NO
project-specific brand literals. The forbidden tokens (project names, design-
token prefixes, font/brand names) are NOT hardcoded here. Instead:
  - per-project tokens arrive at runtime via --project-token / --tokens-file
    (the harvest step records each origin project's tokens in known_tokens.json);
  - everything else is matched by STRUCTURAL shape, not by literal value.

Subcommands:
  scrub   stdin (or --file) → stdout, replacing matched tokens with neutral
          placeholders (<project>, <path>, <url>, <email>, <token>).
  scan    stdin (or --file) → exit 1 + list survivors on stderr if any
          project token or structural-leak pattern remains; exit 0 if clean.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Structural leak patterns — shape-based, never project-literal.
# Each is (compiled_regex, placeholder, label).
STRUCTURAL = [
    # Home / absolute filesystem paths (catch before generic tokens).
    (re.compile(r"(?:/Users/|/home/)[^\s\"'`)]+"), "<path>", "home-path"),
    (re.compile(r"~/[^\s\"'`)]+"), "<path>", "home-path"),
    # URLs (keep the FACT of a link, drop org/repo/host specifics).
    (re.compile(r"https?://[^\s\"'`)]+"), "<url>", "url"),
    # Emails.
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
     "<email>", "email"),
    # Design-token / CSS custom-property SHAPE: requires at least one internal
    # hyphen in the body (e.g. --space-4, --brand-fg) so ordinary CLI flags
    # like --mode / --write (single segment) are NOT matched.
    (re.compile(r"--[a-z][a-z0-9]*-[a-z0-9\-]+"), "<token>", "design-token"),
]


def _project_token_re(tok: str) -> re.Pattern:
    # SUBSTRING match (case-insensitive), deliberately NOT word-bounded. A slug
    # like "healthpulse" must also catch derived/compound identifiers that appear
    # in code and transcripts — "HealthPulseCore", "healthpulse_db" — which a
    # word-boundary match would miss, silently leaking the project name into the
    # PUBLIC flow repo (security review BLOCKER, FB-0059). Leak-prevention favors
    # over-scrub (fail-safe: a slug that is also a common substring may mangle an
    # unrelated word into `<project>…`, an accepted cost) over the under-scrub a
    # bounded match allows. The fail-closed `scan` uses the same matcher, so any
    # derived form that scrub somehow leaves also trips the scan → held, never
    # auto-shipped.
    return re.compile(re.escape(tok), re.IGNORECASE)


def load_project_tokens(args) -> list[tuple[str, re.Pattern]]:
    """Return (token, compiled_pattern) pairs, longest-token-first so a longer
    token isn't partially eaten by a shorter one. Patterns are compiled ONCE
    here so scrub + scan (often both run per invocation) don't recompile."""
    tokens: list[str] = []
    for t in args.project_token or []:
        t = t.strip()
        if t:
            tokens.append(t)
    if args.tokens_file:
        p = Path(args.tokens_file)
        if p.is_file():
            try:
                import json
                data = json.loads(p.read_text(encoding="utf-8"))
                for t in (data.get("tokens", []) if isinstance(data, dict) else []):
                    if isinstance(t, str) and t.strip():
                        tokens.append(t.strip())
            except (OSError, ValueError) as e:
                sys.stderr.write(
                    f"sanitize_tokens: ⚠️ could not read --tokens-file {p} ({e})\n")
    ordered = sorted(set(tokens), key=len, reverse=True)
    return [(tok, _project_token_re(tok)) for tok in ordered]


def scrub_text(text: str, project_tokens: list[tuple[str, re.Pattern]]) -> str:
    for _tok, rx in project_tokens:
        text = rx.sub("<project>", text)
    for rx, placeholder, _label in STRUCTURAL:
        text = rx.sub(placeholder, text)
    return text


def scan_text(text: str, project_tokens: list[tuple[str, re.Pattern]]) -> list[str]:
    survivors: list[str] = []
    for tok, rx in project_tokens:
        if rx.search(text):
            survivors.append(f"project-token: {tok}")
    for rx, _placeholder, label in STRUCTURAL:
        m = rx.search(text)
        if m:
            survivors.append(f"{label}: {m.group(0)[:60]}")
    return survivors


def _read_input(args) -> str:
    if args.file and args.file != "-":
        return Path(args.file).read_text(encoding="utf-8")
    return sys.stdin.read()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="scrub/scan project tokens")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("scrub", "scan"):
        sp = sub.add_parser(name)
        sp.add_argument("--file", default="-", help="input file ('-' = stdin)")
        sp.add_argument("--project-token", action="append", default=[],
                        help="a project-specific token to scrub (repeatable)")
        sp.add_argument("--tokens-file", default="",
                        help="known_tokens.json with a 'tokens' array")

    args = ap.parse_args(argv)
    text = _read_input(args)
    project_tokens = load_project_tokens(args)

    if args.cmd == "scrub":
        sys.stdout.write(scrub_text(text, project_tokens))
        return 0

    # scan (fail-closed)
    survivors = scan_text(text, project_tokens)
    if survivors:
        sys.stderr.write("UNSANITIZED — survivors:\n")
        for s in survivors:
            sys.stderr.write(f"  - {s}\n")
        return 1
    sys.stdout.write("clean\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
