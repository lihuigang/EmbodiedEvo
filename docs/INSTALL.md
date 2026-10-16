# Installation

EmbodiedEvo uses three separate environments: host orchestration, the RoboDojo
simulator, and a thin coding-agent container. Native XPolicyLab evaluation also
uses a small policy-server environment. Run the commands below from the checkout
root. No step needs access to the original private development repository.

## Host Python environment

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-host.txt -e '.[dev]'
.venv/bin/python -m unittest discover -s tests -v
```

Python 3.11+ is required for orchestration. These tests use deterministic fakes
and CPU resources. The real XPolicyLab transport suite is skipped until that
external dependency is installed. Tests do not validate native physics or model
performance.

`requirements-host.txt` pins the host dependencies used for the export's CPU
validation (Python 3.12.7 on Linux). Keep those pins out of the simulator's
environment, which follows its own upstream dependency constraints.

## SO-101 MuJoCo runtime

The SO-101 backend has a separate, CPU-capable simulator environment. The helper
installs pinned MuJoCo bindings and MuJoCo Menagerie, then prefetches only the
`robotstudio_so101` model into the ignored `vendor/mujoco-menagerie-cache/` directory:

```bash
bash scripts/prepare_mujoco_so101.sh
.venv-mujoco/bin/python -m scripts.smoke_mujoco_so101 \
  --run-dir "runs/$(date +%Y%m%d%H%M)_so101_native_smoke"
```

Open the interactive MuJoCo window from the repository root:

```bash
./scripts/view_mujoco_so101.sh
./scripts/view_mujoco_so101.sh --camera top_cam --seed 0
./scripts/view_mujoco_so101.sh --camera wrist_cam --seed 0
```

Close the window to stop the simulator. Use `--camera free` for the movable 3D view,
or run `./scripts/view_mujoco_so101.sh --check` to verify scene loading without a window.
The viewer caps rendering at 15 FPS by default. Use `--fps 30` when smoother rendering
is needed, or `--paused` for the lowest-power static inspection mode.

Run the complete five-position pick-and-place demonstration in the live top camera:

```bash
./scripts/demo_mujoco_so101_pick_place.sh --seeds 11 12 13 14 15
```

The demo sends the same Cartesian IK and normalized gripper actions used by the agent
interface, runs each scene in real time, and prints the result of every seeded episode.

MuJoCo 3.3.7 and `mujoco-menagerie==2026.9.0` are pinned by the `mujoco` extra.
The model cache is external runtime material and is not committed. Override its
location with `MENAGERIE_CACHE_DIR` before both provisioning and execution. Linux
headless execution defaults to EGL; on macOS the native MuJoCo renderer is used.
The smoke runs real physics, both RGB cameras, joint and XYZ-IK actions, deterministic
reset, Test reset rejection, and a physical pick-and-place without Docker or a model call.

### Updating an existing installation

The project package and CLI are now `embodiedevo`, environment variables use
`EMBODIEDEVO_`, and the policy is `EmbodiedEvo`. Reinstall the editable package
with the command above, update exported settings and launch scripts, and build
the configured `embodiedevo-agent:latest` image before starting new runs.
Existing run evidence and local runtime profiles are not migrated automatically.
For a vendor snapshot created under a previous project name, provision an
independent copy in a fresh checkout; the helper refuses to overwrite a snapshot
without the current provenance marker.

## RoboDojo runtime and assets

First obtain a working installation using the official
[RoboDojo installation guide](https://robodojo-benchmark.com/doc/usage/install-and-download/).
Install the required assets and initialize the Isaac Lab, CuRobo and XPolicyLab
dependencies according to that revision's instructions. Keep a record of source
commits and asset revisions.

The included provisioning helper copies that installation into this repository:

```bash
bash scripts/prepare_robodojo.sh /path/to/RoboDojo /path/to/conda/envs/RoboDojo
```

It needs `conda`, `rsync`, and a working source conda environment. It creates
`.venv-robodojo/` and `vendor/robodojo/` as independent local installations, rebinds
editable dependencies, and runs the upstream asset-path generator on the new
copy. The original source installation is left in place. The helper retains the
source snapshot's `packaging==23.0` compatibility pin; validate that pin if using
a different native runtime revision.

`vendor/robodojo/.embodiedevo-provisioned.json` records the source commit,
submodules and hash of pre-existing source patches. The source patch is kept
locally in `.embodiedevo-source.patch`. These files and all vendor assets are
ignored by Git. Treat the provisioned source as read-only during experiments.

This distribution does not contain the simulator image or the exact historical
runtime patches. A different RoboDojo revision must be validated with the smoke
commands below; code export alone does not reproduce historical scores.

## Codex API configuration

Before starting agents, follow [Configure the Codex API](CODEX_API.md): select
the official API or a compatible gateway, create a dedicated configuration home,
save the API key, and check credentials and endpoint access. Ready-to-copy
templates are provided in `configs/codex.openai.example.toml` and
`configs/codex.custom.example.toml`.

The launcher stages `config.toml` and `auth.json`; a key exported only in the
host shell is not automatically passed to Docker. Keep `EMBODIEDEVO_CODEX_HOME`
set in the shell or job that launches the experiment. The task's `[agent]` model
and reasoning effort override defaults in the Codex configuration.

## Thin agent container

Build directly from the repository root; the host needs Docker, not a Codex or
Node.js installation:

```bash
docker build -t embodiedevo-agent:latest docker/agent
docker run --rm --network none embodiedevo-agent:latest codex --version
docker run --rm --network none embodiedevo-agent:latest \
  python -c 'import numpy, PIL, imageio; print("image tools OK")'
```

The standalone `docker/agent/Dockerfile` installs `@openai/codex@0.159.2` from
npm in a build stage, then includes its complete platform package and Node.js
runtime in a Python 3.11 image. The version is pinned; changing it is explicit:

```bash
docker build --build-arg CODEX_VERSION=0.159.2 \
  -t embodiedevo-agent:latest docker/agent
```

The npm installation method follows the [official Codex installation example](https://developers.openai.com/cookbook/examples/codex/build_iterative_repair_loops_with_codex).
This is the same thin-container separation used in EAHarness. The build is
independent of that checkout and of any host CLI files. It includes Git,
ripgrep, ffmpeg, NumPy, Pillow and imageio; the simulator and CUDA remain outside
the agent image. `docker/agent/.dockerignore` limits the context to build files.
No API key, provider configuration, workspace, task data or assets enter the
image. The build and version/import checks make no model API calls.

An optional wrapper runs that same build, performs the checks and prints the
resulting image ID:

```bash
bash scripts/build_agent_image.sh
# Optional custom image tag:
bash scripts/build_agent_image.sh embodiedevo-agent:custom
```

The default tag matches both task templates. A different existing tag does not
satisfy `embodiedevo-agent:latest`; build the configured tag before launching.
Docker images are local to each execution host. To reuse a verified build on a
node without registry access:

```bash
docker save -o /path/outside/git/embodiedevo-agent.tar embodiedevo-agent:latest
# On the execution host:
docker load -i /path/outside/git/embodiedevo-agent.tar
docker image inspect embodiedevo-agent:latest --format '{{.Id}}'
```

Record the image ID and CLI version with the run evidence. A successful image
build checks the agent container; a live episode also needs the separately
provisioned RoboDojo runtime and assets.

At launch, the orchestrator stages provider configuration and authentication
from `EMBODIEDEVO_CODEX_HOME`, or the operator's normal Codex home if unset.
Host plugins, memories and project configuration are excluded. Set the explicit
model and reasoning effort in `task.toml` before creating a run.

Optional site settings are environment variables:

| Variable | Purpose |
| --- | --- |
| `EMBODIEDEVO_CODEX_HOME` | External CLI configuration and authentication source |
| `EMBODIEDEVO_AGENT_HTTPS_PROXY` | Proxy used by the agent container |
| `EMBODIEDEVO_BUILD_HTTP_PROXY` | Proxy used during image construction |
| `EMBODIEDEVO_AGENT_BASE_IMAGE` | Python base image (`BASE_IMAGE` build argument) |
| `EMBODIEDEVO_AGENT_NODE_IMAGE` | Node.js build image (`NODE_IMAGE`) |
| `EMBODIEDEVO_CODEX_VERSION` | Explicit CLI version (`CODEX_VERSION`) |
| `EMBODIEDEVO_AGENT_DEBIAN_MIRROR` | Debian mirror (`DEBIAN_MIRROR`) |
| `EMBODIEDEVO_AGENT_PIP_INDEX_URL` | Python package index (`PIP_INDEX_URL`) |
| `EMBODIEDEVO_AGENT_NPM_REGISTRY` | npm registry (`NPM_REGISTRY`) |
| `EMBODIEDEVO_RUNTIME_DIR` | Host directory for short-lived sockets and locks |
| `EMBODIEDEVO_USE_RECIPE` | `1` includes public task recipes; `0` omits them |

Build variables are consumed by the wrapper. With `docker build`, pass the
corresponding `--build-arg` directly. The agent's `filtered` network setting is
a Docker bridge with outbound access; `none` disables container networking.

On hosts that require the shell's HTTP proxy for registry/package downloads:

```bash
docker build --build-arg HTTP_PROXY --build-arg HTTPS_PROXY \
  -t embodiedevo-agent:latest docker/agent
```

These predefined Docker build arguments take their values from the environment;
do not write proxy credentials or model API keys into the Dockerfile.

## Smoke check

Use an available GPU assigned to you. These diagnostics use the configured
Playground scene and do not open a formal Test plan or call a model:

```bash
.venv-robodojo/bin/python -m scripts.smoke_robodojo --env-task stack_bowls \
  --gpu 0 --run-dir "runs/$(date +%Y%m%d%H%M)_native_smoke"
.venv/bin/python -m scripts.smoke_session --task RoboDojo --env-task stack_bowls \
  --gpu 0 --run-dir "runs/$(date +%Y%m%d%H%M)_session_smoke"
```

Read each run's `smoke.json`; native simulator shutdown can mask an earlier
exception behind a zero process exit code. Do not report diagnostics as scores.

## Native evaluation policy server

RoboDojo's simulator and the XPolicyLab server can require different versions of
`websockets`. Keep the policy server in a separate environment:

```bash
python3 -m venv .venv-robodojo-policy
.venv-robodojo-policy/bin/python -m pip install -e '.[policy]'
```

The policy bootstrap imports the repository-local `vendor/robodojo/XPolicyLab`.
Install any additional dependencies required by that upstream revision in the
policy environment. See [the integration guide](../integrations/robodojo_policy/README.md)
for native evaluation and the optional image/Slurm route.
