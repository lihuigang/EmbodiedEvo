"""Run the real SO-101 MuJoCo backend without Docker or a model call."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

import numpy as np


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    run = args.run_dir.resolve()
    if run.exists():
        raise FileExistsError("Smoke requires a fresh --run-dir")
    run.mkdir(parents=True)

    from orchestrator.config import load_task
    from orchestrator.files import write_json
    from simulators.backend import build
    from simulators.primitives import rgb_images

    result = {
        "passed": False,
        "kind": "mujoco-so101-native-smoke",
        "seed": args.seed,
        "python": sys.executable,
        "scored": False,
    }
    env = None
    try:
        cfg = load_task("SO101MuJoCo")
        env = build(cfg, seed=args.seed)
        first = env.public_observation()
        frames = rgb_images(first)
        assert set(frames) == {"top_cam", "wrist_cam"}
        assert all(frame.shape == (256, 256, 3) for frame in frames.values())
        assert all(frame.dtype == np.uint8 and frame.std() > 1 for frame in frames.values())
        assert first["state"]["arm_joint_state"].shape == (5,)
        assert first["state"]["ee_joint_state"].shape == (1,)
        assert first["state"]["ee_pose"].shape == (7,)
        settled_cube = env.data.qpos[env._cube_qpos : env._cube_qpos + 3].copy()

        hold = {key: value for key, value in first["action"].items()}
        transition = env.control_step(hold)
        assert len(transition) == 5 and env.control_steps == 1
        position = env.public_observation()["state"]["ee_pose"][:3]
        env.control_step({"ee_position": position, "ee_joint_state": [1.0]})
        assert env.control_steps == 2
        tool_axis = env.data.site_xmat[env._ee_site].reshape(3, 3)[:, 0]
        assert tool_axis @ np.array([0.0, 0.0, -1.0]) > 0.95

        env.execution_phase = "playground"
        env.reset_from_program()
        assert env.max_steps - env.control_steps == env.native_step_limit
        reset_cube = env.data.qpos[env._cube_qpos : env._cube_qpos + 3]
        assert np.allclose(reset_cube, settled_cube, atol=1e-9)
        env.execution_phase = "test"
        rejected = env.step("again = reset\nagain()")
        assert not rejected[-1]["ok"] and "PermissionError" in rejected[-1]["stderr"]

        env.execution_phase = "playground"
        env.reset_from_program()
        cube = env.data.xpos[env._cube_id].copy()
        target = env.data.xpos[env._target_id].copy()

        def move(position, gripper, count=18):
            for _ in range(count):
                if env.done:
                    break
                env.control_step(
                    {"ee_position": position, "ee_joint_state": [gripper]}
                )

        move(cube + (0, 0, 0.065), 1.0)
        move(cube + (0, 0, 0.012), 1.0)
        move(cube + (0, 0, 0.012), 0.0, count=15)
        move(cube + (0, 0, 0.065), 0.0)
        move(target + (0, 0, 0.076), 0.0)
        move(target + (0, 0, 0.028), 0.0)
        move(target + (0, 0, 0.028), 1.0, count=15)
        transition = env.transition(float(env.success))
        assert transition[1] == 1.0 and transition[2] and env.success
        result.update(
            passed=True,
            cameras={name: list(frame.shape) for name, frame in frames.items()},
            joint_action_checked=True,
            ik_action_checked=True,
            deterministic_reset_checked=True,
            playground_reset_budget_checked=True,
            test_reset_rejected=True,
            physical_pick_and_place_checked=True,
            native_action_limit=env.native_step_limit,
        )
    except BaseException:
        result["error"] = traceback.format_exc()
        raise
    finally:
        write_json(run / "smoke.json", result)
        if env is not None:
            env.close()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
