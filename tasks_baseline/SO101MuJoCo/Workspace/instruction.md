# Goal

Complete the current SO-101 task using only the native primitives and current-scene feedback.
Read `primitives/primitives.md`, query the instruction, inspect top/wrist camera frames, and
submit incremental code through `python scripts/env.py exec submission/solution.py`.

The Python namespace and physical scene persist across submissions. Put current code in
`submission/`, scene-specific notes in `scratch/`, and inspect the read-only numbered history
under `observations/`. Reset is forbidden. `status` and `finish` cost no execution slots.

## Budgets

| Budget | Total allowance | Remaining at session start |
|---|---:|---:|
| Code-execution requests | {{EXECUTION_BUDGET}} | {{EXECUTION_BUDGET}} |
| Native action steps | {{NATIVE_ACTION_LIMIT}} | {{NATIVE_ACTION_LIMIT}} |

This task permits {{NATIVE_ACTION_LIMIT}} native action steps for this Test scene and
{{EXECUTION_BUDGET}} code-execution requests. Query `status` before acting, preserve failures,
and call `finish` after success or when no useful recovery remains.
