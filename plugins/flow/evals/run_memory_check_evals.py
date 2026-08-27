#!/usr/bin/env python3
"""Eval harness for `tools/memory/check.mjs --dead` (roadmap #3, memory-effectiveness
instrumentation — reduced scope: `--dead` only, see dev-docs/history.md for the scope cut).

`--dead` mechanically surfaces failure-pattern memory entries with no Fire-log activity
(falling back to First-seen, then file mtime) in N days (default 60), so `/flow:ship` § 4b.vi's
periodic audit agent judges archive-vs-keep on a deterministic candidate list instead of
computing date arithmetic across up to 30 entries itself.

This harness builds a real fixture memory directory (under `~/.claude/projects/`, since
`check.mjs`'s `validateMemoryDir` refuses any path outside that root — see its top-of-file
comment) with synthetic `feedback_*.md` entries, invokes the real `check.mjs` via subprocess,
and asserts on stdout/exit codes. No mocking of the artifact under test.

The `.last-audit` marker `check.mjs` writes lives beside the script itself (per-install, not
per-fixture-dir — see check.mjs's own comment on why), so any `--audit-due` invocation here
saves and restores it to avoid polluting real ship-counter state across eval runs.

Stdlib only. Run:
    python3 plugins/flow/evals/run_memory_check_evals.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
CHECK_MJS = HERE.parent / "tools" / "memory" / "check.mjs"
MARKER = CHECK_MJS.parent / ".last-audit"
NODE = shutil.which("node") or "node"

NOW = datetime.now()

_failures: list[str] = []


def check(name, ok, detail=""):
    if ok:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}\n        {detail}")
        _failures.append(name)


def days_ago(n: int) -> str:
    return (NOW - timedelta(days=n)).strftime("%Y-%m-%d")


def entry_text(*, first_seen_days_ago: int | None = None, fire_days_ago: list[int] | None = None,
                fire_days_ago_split: bool = False) -> str:
    """Build a synthetic feedback_*.md entry. `fire_days_ago_split=True` writes each fire date
    as its OWN `**Fire log**` bullet line (rather than comma-joined onto one line) — nothing
    pins which shape a freehand append produces, so the parser must union both."""
    lines = ["- **Source** — test fixture"]
    if first_seen_days_ago is not None:
        lines.append(f"- **First seen** — {days_ago(first_seen_days_ago)} on branch test")
    if fire_days_ago is not None:
        if fire_days_ago_split:
            lines.extend(f"- **Fire log** — {days_ago(n)}" for n in fire_days_ago)
        else:
            dates = ", ".join(days_ago(n) for n in fire_days_ago)
            lines.append(f"- **Fire log** — {dates}")
    lines.append("- **Pattern** — fixture entry, not a real failure pattern")
    return "\n".join(lines) + "\n"


def run_check(args: list[str], memory_dir: Path) -> tuple[int, str, str]:
    env = dict(os.environ)
    env["MEMORY_DIR"] = str(memory_dir)
    proc = subprocess.run(
        [NODE, str(CHECK_MJS), *args],
        env=env,
        capture_output=True, text=True, timeout=20,
    )
    return proc.returncode, proc.stdout, proc.stderr


def build_fixture(root: Path) -> Path:
    memory_dir = root / "memory"
    memory_dir.mkdir(parents=True)

    # Fires recently and long ago — last activity is the MOST RECENT fire (10d), not stale.
    (memory_dir / "feedback_fresh_fire.md").write_text(
        entry_text(first_seen_days_ago=200, fire_days_ago=[90, 10]))

    # Only fired once, long ago — stale under the default 60d threshold.
    (memory_dir / "feedback_stale_fire.md").write_text(
        entry_text(first_seen_days_ago=200, fire_days_ago=[90]))

    # Never fired; First-seen fallback puts it just past the default boundary — stale.
    (memory_dir / "feedback_stale_unfired.md").write_text(
        entry_text(first_seen_days_ago=61))

    # Never fired; First-seen fallback puts it just inside the default boundary — not stale.
    (memory_dir / "feedback_fresh_unfired.md").write_text(
        entry_text(first_seen_days_ago=59))

    # Fired 45 days ago: not stale under the default (60d) but IS stale under an override (30d).
    (memory_dir / "feedback_mid_fire.md").write_text(
        entry_text(first_seen_days_ago=200, fire_days_ago=[45]))

    # No Fire log, no First seen bullet at all — legacy/malformed-input path. mtime is "now"
    # at fixture-build time, so it's never stale; the point of this fixture is "doesn't crash".
    (memory_dir / "feedback_legacy_no_dates.md").write_text(
        "- **Source** — test fixture\n- **Pattern** — pre-this-feature entry format\n")

    # A non-feedback-prefixed file must be ignored by every subcommand (matches listEntries's
    # existing filter — regression coverage, not new behavior).
    (memory_dir / "notes.md").write_text("not a memory entry\n")

    # Fires written as TWO SEPARATE "Fire log" bullet lines (90d ago, then 10d ago) rather than
    # comma-joined on one line — nothing pins which shape a freehand append produces. Must NOT
    # be stale: the parser has to union dates across every matching line, not just the first.
    (memory_dir / "feedback_split_fire_lines.md").write_text(
        entry_text(first_seen_days_ago=200, fire_days_ago=[90, 10], fire_days_ago_split=True))

    # Real Fire log is a single stale fire (90d ago), but the Pattern field's PROSE bolds
    # "**Fire log**"/"**First seen**" while discussing the feature itself, with recent dates
    # nearby. An unanchored "contains **Label** anywhere in the line" match would misread those
    # prose dates as real activity and report this entry as fresh — it must still be flagged.
    (memory_dir / "feedback_prose_mentions_fire_log.md").write_text(
        f"- **Source** — test fixture\n"
        f"- **First seen** — {days_ago(200)} on branch test\n"
        f"- **Fire log** — {days_ago(90)}\n"
        f"- **Pattern** — do not confuse this with **Fire log** semantics from {days_ago(10)} "
        f"or **First seen** claims from {days_ago(5)}\n"
    )

    # No Fire log, no First seen — mtime is the ONLY resolvable tier — but backdated past the
    # default 60d threshold, so this must actually surface as stale via mtime (unlike
    # feedback_legacy_no_dates.md above, whose mtime is "now" and stays fresh). Exercises the
    # third fallback tier in the STALE set, not just the "doesn't crash" path.
    stale_mtime_path = memory_dir / "feedback_stale_mtime_only.md"
    stale_mtime_path.write_text("- **Source** — test fixture\n- **Pattern** — no dates, old mtime\n")
    backdated = time.time() - (90 * 86400)
    os.utime(stale_mtime_path, (backdated, backdated))

    return memory_dir


def main() -> int:
    print("memory-check evals (roadmap #3, --dead)")

    check("check.mjs exists", CHECK_MJS.exists(), f"not found at {CHECK_MJS}")
    if not CHECK_MJS.exists():
        print("\nFAILED: check.mjs missing, cannot continue")
        return 1

    projects_root = Path.home() / ".claude" / "projects"
    projects_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="memcheck-eval-", dir=projects_root) as td:
        memory_dir = build_fixture(Path(td))

        # ---- --dead: default 60-day threshold ----
        rc, out, err = run_check(["--dead"], memory_dir)
        check("--dead: exits 0", rc == 0, f"rc={rc} stderr={err!r}")
        EXPECTED_DEFAULT = [
            ("feedback_stale_fire.md", True, "single fire, 90d ago"),
            ("feedback_stale_unfired.md", True, "First-seen fallback, 61d"),
            ("feedback_fresh_fire.md", False, "most-recent fire wins, 10d"),
            ("feedback_fresh_unfired.md", False, "First-seen, 59d"),
            ("feedback_mid_fire.md", False, "fired 45d ago, under default 60d"),
            ("feedback_legacy_no_dates.md", False, "mtime fallback = now"),
            ("notes.md", False, "not feedback_-prefixed"),
            ("feedback_split_fire_lines.md", False,
             "fires on two separate Fire-log bullet lines; most recent (10d) must still win"),
            ("feedback_prose_mentions_fire_log.md", True,
             "real fire is 90d ago; Pattern-field prose mentioning **Fire log** must NOT count"),
            ("feedback_stale_mtime_only.md", True, "no dates at all; mtime backdated 90d"),
        ]
        for name, expected, reason in EXPECTED_DEFAULT:
            verb = "flags" if expected else "does NOT flag"
            check(f"--dead: {verb} {name} ({reason})", (name in out) == expected, f"stdout={out!r}")
        check("--dead: reports a fire count alongside each stale entry",
              "0 fires" in out and "1 fire" in out, f"stdout={out!r}")
        check("--dead: enriches each line with an ISO date and the resolving tier",
              f"{days_ago(90)}" in out and "via fire" in out and "via first-seen" in out
              and "via mtime" in out, f"stdout={out!r}")

        # ---- --dead --days=30: narrower window catches feedback_mid_fire.md too ----
        rc, out, err = run_check(["--dead", "--days=30"], memory_dir)
        check("--dead --days=30: exits 0", rc == 0, f"rc={rc} stderr={err!r}")
        check("--dead --days=30: now flags feedback_mid_fire.md (45d > 30d)",
              "feedback_mid_fire.md" in out, f"stdout={out!r}")
        check("--dead --days=30: still flags feedback_stale_fire.md",
              "feedback_stale_fire.md" in out, f"stdout={out!r}")
        check("--dead --days=30: still does not flag feedback_fresh_fire.md",
              "feedback_fresh_fire.md" not in out, f"stdout={out!r}")

        # ---- malformed --days values: each falls back to default, warns, doesn't crash ----
        # Validated against the RAW string, not parseInt()'s lenient coercion — parseInt("30.5")
        # is a valid integer (30), so a fractional/exponential/empty value must be caught before
        # parseInt runs, not after.
        for bad in ["bogus", "", "30.5", "1e5", "-5", "0"]:
            rc, out, err = run_check(["--dead", f"--days={bad}"], memory_dir)
            check(f"--dead --days={bad!r}: exits 0 (degrades, doesn't crash)", rc == 0,
                  f"rc={rc} stderr={err!r}")
            check(f"--dead --days={bad!r}: warns on stderr rather than silently defaulting",
                  "not a positive integer" in err, f"stderr={err!r}")
            check(f"--dead --days={bad!r}: still applies the default 60d threshold",
                  "feedback_stale_fire.md" in out and "feedback_mid_fire.md" not in out,
                  f"stdout={out!r}")

        # ---- duplicate --days flags: only the FIRST occurrence is honored, so the stderr
        # message always matches the days value actually in effect (never warns about a second
        # flag while silently keeping an earlier one, or vice versa). Invalid-first order proves
        # the invariant directly: the message names 'bogus' AND the effective threshold stays
        # the default (60d) — a later valid '30' is never reached, so feedback_mid_fire.md (45d)
        # is NOT flagged (45 < 60), the same as the single --days=bogus case above.
        rc, out, err = run_check(["--dead", "--days=bogus", "--days=30"], memory_dir)
        check("--dead --days=bogus --days=30: exits 0", rc == 0, f"rc={rc} stderr={err!r}")
        check("--dead --days=bogus --days=30: warns about the FIRST (invalid) occurrence",
              "not a positive integer" in err, f"stderr={err!r}")
        check("--dead --days=bogus --days=30: effective threshold is the default (60d), "
              "not the later 30 — message and behavior agree",
              "feedback_stale_fire.md" in out and "feedback_mid_fire.md" not in out,
              f"stdout={out!r}")

        # ---- an empty-but-existing memory dir: no crash, clean "no stale entries" message ----
        with tempfile.TemporaryDirectory(prefix="memcheck-empty-", dir=projects_root) as empty_td:
            empty_dir = Path(empty_td) / "memory"
            empty_dir.mkdir()
            rc, out, err = run_check(["--dead"], empty_dir)
            check("--dead on an empty memory dir: exits 0", rc == 0, f"rc={rc} stderr={err!r}")
            check("--dead on an empty memory dir: reports no stale entries",
                  "No entries stale" in out, f"stdout={out!r}")

        # ---- regression: --count and --list unaffected by this change ----
        rc, out, _ = run_check(["--count"], memory_dir)
        check("--count: regression, matches fixture's 9 feedback_ entries",
              rc == 0 and out.strip() == "9", f"rc={rc} stdout={out!r}")

        rc, out, _ = run_check(["--list"], memory_dir)
        check("--list: regression, still lists all 9 feedback_ entries",
              rc == 0 and out.count("feedback_") == 9, f"rc={rc} stdout={out!r}")

        # ---- regression: --audit-due still runs; marker saved/restored to avoid polluting
        # real ship-counter state (the marker lives beside check.mjs, not in memory_dir).
        saved_marker = MARKER.read_bytes() if MARKER.exists() else None
        try:
            rc, out, err = run_check(["--audit-due"], memory_dir)
            check("--audit-due: regression, exits 0 or 1 with an audit-due/not-due message",
                  rc in (0, 1) and ("audit due" in out or "audit not due" in out),
                  f"rc={rc} stdout={out!r} stderr={err!r}")
        finally:
            if saved_marker is None:
                MARKER.unlink(missing_ok=True)
            else:
                MARKER.write_bytes(saved_marker)

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} eval(s): {', '.join(_failures)}")
        return 1
    print("All memory-check evals passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
