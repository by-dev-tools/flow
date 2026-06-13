# Coverage-audit context fixture — doc/test-only diff (must SKIP)

When the diff has no behavior-bearing source files (the assembly's source-file
filter, with the test/fixture/doc exclusion, finds nothing), the skill prints a
`[audit-coverage] SKIPPED` sentinel and the auditor reproduces it verbatim —
there is no behavior to under-declare. See sibling `.expected.txt`.

## Declared `**Spec-walk:**` criteria

{"criteria": ["README documents the new config slot."], "source_path": "dev-docs/plan.md", "source_heading": "**Spec-walk:**", "warnings": []}

## Workspace diff — source files changed vs the default branch

[audit-coverage] SKIPPED — no behavior-bearing source files in the diff (doc/test/refactor-only vs origin/main).
