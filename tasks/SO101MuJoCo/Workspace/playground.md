# Goal

Control the simulated SO-101 through code. In Playground, explore the fixed scene, solve
the task, and immediately record reusable controllers in `skills/` and failure guidance in
`lessons/`. Only those two directories transfer to Test.

Read `primitives/primitives.md`, then obtain the task with `python scripts/env.py instruction`.
Iterate through observation, a small action sequence, and feedback. Inspect at most two
`current_cam_*.png` images per iteration. Preserve failed attempts rather than retrying
silently. The simulator exposes only `get_instruction()`, `get_observation()`, `step(action)`
and `reset()`.

Each submitted `submission/solution.py` is an incremental segment executed from its first
line in a persistent Python namespace. Use `python scripts/env.py exec submission/solution.py`.
Use `status` freely; `instruction`, `observe`, `exec`, and standalone `reset` each consume
one execution slot. `finish` closes the session. Playground reset restores the same seed and
native action allowance but never restores execution slots or elapsed time.

## Budgets

| Budget | Total allowance | Remaining at session start |
|---|---:|---:|
| Code-execution requests | {{EXECUTION_BUDGET}} | {{EXECUTION_BUDGET}} |
| Native action steps per attempt | {{NATIVE_ACTION_LIMIT}} | {{NATIVE_ACTION_LIMIT}} |

This task permits {{NATIVE_ACTION_LIMIT}} native action steps per Playground attempt and
{{EXECUTION_BUDGET}} total execution slots. Run `python scripts/env.py status` before acting
and after substantial submissions. Finish once success is reported or useful exploration is
complete.
