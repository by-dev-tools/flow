#!/bin/bash
# Run every eval harness and report RED/GREEN **by exit code**.
#
# WHY THIS FILE EXISTS. The ad-hoc sweep it replaces was a one-liner typed into a
# shell over and over:
#
#   for f in plugins/flow/evals/run_*.py; do
#     out=$(python3 "$f" 2>&1 | tail -1)
#     case "$out" in *FAIL*|*Traceback*|*rror*) echo "RED ...";; esac
#   done
#
# It keys on the LAST OUTPUT LINE. `run_autoplan_evals.py` exits 1 while its last
# line reads `241/244 checks passed` — no "FAIL", no "error" — so the sweep reported
# the suite clean on four consecutive pushes while CI was red on the same SHAs, and
# "full eval sweep clean" went into four commit messages and a readiness report.
#
# This is `.claude/rules/general.md` § Consistency item 4's own corollary — "prefer a
# tool's own exit code over a grep of its output ... an exit code is a signal the
# tool's author designed and maintains against their own output format" — violated by
# the author of the sentence, in the instrument used to make the claim. The CV1 worker
# hit the identical defect a day earlier, which is what makes it a class rather than a
# slip: a convenience grep is the default thing a shell loop reaches for.
#
# Two properties this has and that one did not:
#   1. It keys on `$?`, so a harness's output format cannot hide its verdict.
#   2. `--selftest` proves it can report RED, by running a harness that is designed to
#      fail. An instrument that has only ever returned "clean" is not an instrument.
#
# It is NOT a replacement for `gh pr checks` — CI runs harnesses with arguments this
# does not reproduce, and the ship pipeline does not read CI status at all. Check both.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 2

if [ "${1:-}" = "--selftest" ]; then
    # A harness that must fail. If the runner reports this GREEN it cannot report RED.
    tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
    printf 'import sys\nprint("3/4 checks passed")\nsys.exit(1)\n' > "$tmp/run_selftest_evals.py"
    if python3 "$tmp/run_selftest_evals.py" >/dev/null 2>&1; then
        echo "⚠️ SELFTEST BROKEN: a harness exiting 1 was read as success." >&2; exit 2
    fi
    # And the shape that defeated the old sweep: non-zero exit, innocuous last line.
    last=$(python3 "$tmp/run_selftest_evals.py" 2>&1 | tail -1)
    case "$last" in
        *FAIL*|*Traceback*|*rror*)
            echo "⚠️ SELFTEST INCONCLUSIVE: the decoy's last line ($last) contains a failure" >&2
            echo "   token, so it does not reproduce the case that fooled the old sweep." >&2; exit 2 ;;
    esac
    echo "[eval-sweep] selftest OK — exits 1 while its last line reads '$last';"
    echo "             the exit code sees it, a last-line grep does not."
    exit 0
fi

red=0 total=0 failed=()
for f in plugins/flow/evals/run_*.py; do
    total=$((total + 1))
    if ! out=$(python3 "$f" 2>&1); then
        red=$((red + 1)); failed+=("$f")
        echo "RED  $(basename "$f")  — last line: $(printf '%s' "$out" | tail -1)"
    fi
done
if [ "$red" -gt 0 ]; then
    echo "[eval-sweep] $red of $total harnesses RED (by exit code):" >&2
    for f in "${failed[@]}"; do echo "   $f" >&2; done
    exit 1
fi
echo "[eval-sweep] $total of $total harnesses GREEN (by exit code)."
echo "[eval-sweep] NOT a substitute for CI — run 'gh pr checks <N>' before calling anything ready."
