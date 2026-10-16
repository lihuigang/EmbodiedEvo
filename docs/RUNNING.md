# Running EmbodiedEvo backends

Complete [installation](INSTALL.md) and [Codex API configuration](CODEX_API.md),
then run from the repository root. Use an
explicit new `--run-dir` for each experiment. Directory prefixes use
`YYYYMMDDHHMM`; append a descriptive suffix to distinguish same-minute runs.

## Local Playground and Test

```bash
RUN_DIR="runs/$(date +%Y%m%d%H%M)_stack_bowls"
.venv/bin/embodiedevo run --task RoboDojo --env-task stack_bowls \
  --run-dir "$RUN_DIR" --gpu 0
```

`explore` and `test` can also be run separately against the same directory.
The configured default is 25 Test scenes. `--test-scenes N` sets a run-specific
count; use the same count for separate explore and test commands. Counts and
task settings are pinned, so do not change them during resume. A small smoke or
subset run is not a full benchmark evaluation.

```bash
.venv/bin/embodiedevo test --task tasks_baseline/RoboDojo --env-task stack_bowls \
  --run-dir "runs/$(date +%Y%m%d%H%M)_stack_bowls_baseline" --gpu 0
```

The default templates explicitly select a model and reasoning effort; use values
supported by your provider. No provider URL or key is included. Model credentials
remain in an external CLI home.

## SO-101 MuJoCo

After preparing `.venv-mujoco`, run the seeded pick-and-place task without a GPU flag:

```bash
RUN_DIR="runs/$(date +%Y%m%d%H%M)_so101_pick_cube"
.venv/bin/embodiedevo run --task SO101MuJoCo --run-dir "$RUN_DIR"

.venv/bin/embodiedevo test --task tasks_baseline/SO101MuJoCo \
  --run-dir "runs/$(date +%Y%m%d%H%M)_so101_pick_cube_baseline"
```

The regular and baseline templates each select ten Test seeds. Compare the exact same
seed plan when reporting transfer effects; report success rate, native actions, execution
requests, wall time and model usage, and retain every failed scene. A smoke result proves
the integration and task mechanics only, not agent performance or sim-to-real transfer.

### Live Codex SO-101 sessions

With the model login configured as described in `docs/CODEX_API.md` and the Docker
agent image built, preflight and launch one Playground plus five Test scenes:

```bash
./scripts/run_codex_so101.sh --check
./scripts/run_codex_so101.sh --run-dir "runs/$(date +%Y%m%d%H%M)_codex_so101_live"
```

The second command makes model requests using the task's configured model and effort.
The first command makes none and does not prove endpoint access or quota. Set
`EMBODIEDEVO_CODEX_HOME` to the intended external login directory before launching.

The equivalent lower-level command is:

```bash
.venv/bin/embodiedevo run --task SO101MuJoCo --viewer --viewer-fps 15 \
  --test-scenes 5 --run-dir "runs/$(date +%Y%m%d%H%M)_codex_so101_live"
```

The window shows states from the actual Agent-controlled episode in `top_cam`.
Physics advances only on Agent actions at 20 Hz; the display refreshes at up to 15 FPS.
While Codex thinks, the robot stays still. GUI manipulation affects only a display copy
of the model and state. Closing the window interrupts the scene, which is preserved as
an infrastructure interruption; it never grants an automatic retry. Test scenes run
sequentially, each with its own Agent, simulator, read-only frozen Skills/Lessons, and
the original 300-action limit. The viewer does not supply object poses or a controller.
Codex must write its own controller and learned knowledge during Playground.

Use `--viewer` with `explore` or `test` to watch individual phases; keep the same
`--test-scenes` value for paired commands. The wrapper also accepts `--headless`.
The viewer cannot be combined with parallel Test GPU slots. On macOS the simulator
uses its `mjpython`; on Linux a desktop/display is required and rendering uses GLFW.

On macOS, the SO-101 session uses a short-lived TCP listener with a random per-episode
token, because a host Unix socket cannot be shared directly with Linux containers.
The token stays outside the run archive and is removed with the temporary session
directory. Requests are authenticated before execution and credentials are excluded
from ledgers. The container reaches the host at `host.lima.internal` for Colima or
`host.docker.internal` for Docker Desktop; override `EMBODIEDEVO_AGENT_HOST` if needed.
Some Colima bridges do not resolve `host.lima.internal` inside containers. In that
case, set `EMBODIEDEVO_AGENT_HOST` to the address returned by
`colima ssh -- getent hosts host.lima.internal`. If API access requires a local proxy,
set `EMBODIEDEVO_AGENT_HTTPS_PROXY` to a proxy address reachable from the container,
not the container's own loopback. The launcher overrides both upper- and lowercase
proxy variables so Docker client defaults cannot silently select a different proxy.
The listener binds host interfaces to reach the VM; use a trusted local network.
Linux sessions retain Unix socket transport.

Run a no-model live transport diagnostic separately:

```bash
.venv/bin/python -m scripts.smoke_session --task SO101MuJoCo --viewer \
  --gpu '' --run-dir "runs/$(date +%Y%m%d%H%M)_live_protocol"
```

For host-only diagnosis, add `--host-client`. That skips Docker isolation and must
not be reported as a model run. Episode records include `viewer.json`, `runtime.json`,
`simulator.log`, action history, camera feedback/videos and original results. Archival
replay is headless and does not replace the live episode outcome.

## Native official evaluator

After obtaining a frozen Playground run, use the
[XPolicyLab integration](../integrations/robodojo_policy/README.md) to run the
native evaluator. The direct session runner and native evaluator produce
different report formats. Keep their provenance and scope explicit when
comparing results. Full official scene counts and aggregation rules come from
the selected upstream benchmark revision, not from a short local diagnostic.

## Concurrency and output

Start with one simulator per GPU. `--test-gpus 0,1 --test-gpu-slots 1` enables
bounded concurrent Test scenes on resources already assigned to you. The optional
SIF route validates the selected physical GPU against the current Slurm allocation;
no cluster scheduler or node list is shipped.

Inspect the run's `protocol.json`, `resolved.json`, `runtime.json`, per-scene
results, agent sessions and raw submission feedback. Ledgers and Test plans
remain host-only. The repository ignores all run output.

If launching a command in the background, redirect stdin, stdout and stderr to
`/dev/null`, or pass `subprocess.DEVNULL` for all three streams in Python. Use the
run's existing status and feedback files for monitoring; do not create a separate
launcher log. Stop only processes belonging to your own run.
