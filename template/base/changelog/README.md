# Changelog

Consumer-facing release notes. For per-PR design decisions + tradeoffs, see the history doc (verbose, internal-tracking).

## One file per release

**Every release is its own file: `vX.Y.Z.md`.** There is no rollup and no index, deliberately — either would recreate the
merge conflict this structure removes, since every release would append to it.

Plain `ls` sorts lexically, which puts `v1.10.0` before `v1.9.0`. Use **`ls -v`** (version sort), or read the `## vX.Y.Z`
heading inside each file.

Format: each entry has a date, version, headline, 2-4 bullets, and an explicit "Breaking changes:" callout.

Point `flow.config.json.changelogPath` at this directory. `/flow:land`'s currency check resolves either a directory or a
single file, so a project that prefers one `CHANGELOG.md` can keep it.
