"""Preflight and launch Codex learning plus five live SO-101 Test scenes."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from orchestrator import launch_agent
from orchestrator.__main__ import main as run
from orchestrator.config import load_task
from orchestrator.live import simulator_command


def preflight(cfg, *, viewer):
    errors = []
    if not cfg.python.is_file():
        errors.append("Prepare the simulator: bash scripts/prepare_mujoco_so101.sh")
    try:
        simulator_command(cfg, viewer=viewer)
    except ValueError as exc:
        errors.append(str(exc))
    try:
        launch_agent.require_image(cfg.agent.image)
    except RuntimeError as exc:
        errors.append(str(exc))
    try:
        with tempfile.TemporaryDirectory(prefix="embodiedevo-preflight-") as directory:
            staged = launch_agent.stage_home(Path(directory) / "home") / ".codex"
            if not (staged / "auth.json").is_file():
                errors.append(
                    "No saved login; configure EMBODIEDEVO_CODEX_HOME (docs/CODEX_API.md)"
                )
    except (ValueError, OSError) as exc:
        errors.append(str(exc))
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir", type=Path, help="fresh runs/YYYYMMDDHHMM_description directory"
    )
    parser.add_argument("--check", action="store_true", help="check setup without model calls")
    parser.add_argument("--test-scenes", type=int, default=5)
    parser.add_argument("--viewer-fps", type=float, default=15)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args(argv)
    if not args.check and args.run_dir is None:
        parser.error("--run-dir is required for a real run")
    cfg = load_task("SO101MuJoCo")
    errors = preflight(cfg, viewer=not args.headless)
    if errors:
        for error in errors:
            print(f"Setup needed: {error}")
        return 1
    print(f"Ready: Codex, model={cfg.agent.model}, effort={cfg.agent.reasoning_effort}.")
    print("Local setup checked; model access and quota have not been tested.")
    if args.check:
        return 0
    command = [
        "run", "--task", "SO101MuJoCo", "--run-dir", str(args.run_dir),
        "--test-scenes", str(args.test_scenes), "--viewer-fps", str(args.viewer_fps),
    ]
    if not args.headless:
        command.append("--viewer")
    return run(command)


if __name__ == "__main__":
    raise SystemExit(main())
