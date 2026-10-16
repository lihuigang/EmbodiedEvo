# Goal

Complete the current SO-101 task in one continuous Test episode. Read the frozen skills and
lessons, inspect live observations, and adapt them to this seed. The frozen knowledge is
read-only; scene-specific notes belong in `scratch/` and current code in `submission/`.

Read `primitives/primitives.md` and use `python scripts/env.py instruction`, `observe`,
`exec submission/solution.py`, `status`, and `finish`. Submitted code runs incrementally in a
persistent Python namespace. Reset is forbidden in Test. Inspect at most two current camera
frames per iteration and reserve actions for verification and recovery.

## Budgets

| Budget | Total allowance | Remaining at session start |
|---|---:|---:|
| Code-execution requests | {{EXECUTION_BUDGET}} | {{EXECUTION_BUDGET}} |
| Native action steps | {{NATIVE_ACTION_LIMIT}} | {{NATIVE_ACTION_LIMIT}} |

This task permits {{NATIVE_ACTION_LIMIT}} native action steps for the entire Test scene and
{{EXECUTION_BUDGET}} execution slots. Neither can be restored. Query `status` before acting,
stop action loops on `terminated` or `truncated`, and call `finish` when done.
