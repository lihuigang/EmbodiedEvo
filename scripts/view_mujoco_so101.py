"""Open the seeded SO-101 task in MuJoCo's interactive viewer."""

from __future__ import annotations

import argparse
import json
import time


def positive_float(value):
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("speed must be greater than zero")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=0, help="nonnegative scene seed")
    parser.add_argument(
        "--camera",
        choices=("free", "top_cam", "wrist_cam"),
        default="free",
        help="initial viewer camera",
    )
    parser.add_argument(
        "--speed",
        type=positive_float,
        default=1.0,
        help="simulation speed multiplier (default: 1)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="load the scene and print its summary without opening a window",
    )
    args = parser.parse_args(argv)
    if args.seed < 0:
        parser.error("--seed must be nonnegative")

    from orchestrator.config import load_task
    from simulators.backend import build

    env = build(load_task("SO101MuJoCo"), seed=args.seed)
    try:
        cameras = [
            env.mujoco.mj_id2name(env.model, env.mujoco.mjtObj.mjOBJ_CAMERA, index)
            for index in range(env.model.ncam)
        ]
        if args.check:
            print(
                json.dumps(
                    {
                        "loaded": True,
                        "seed": args.seed,
                        "model": "robotstudio_so101",
                        "cameras": cameras,
                        "physics_timestep": env.model.opt.timestep,
                    },
                    indent=2,
                )
            )
            return 0

        import mujoco.viewer

        with mujoco.viewer.launch_passive(env.model, env.data) as viewer:
            if args.camera != "free":
                camera_id = env.mujoco.mj_name2id(
                    env.model, env.mujoco.mjtObj.mjOBJ_CAMERA, args.camera
                )
                viewer.cam.type = env.mujoco.mjtCamera.mjCAMERA_FIXED
                viewer.cam.fixedcamid = camera_id
            while viewer.is_running():
                started = time.monotonic()
                env.mujoco.mj_step(env.model, env.data)
                viewer.sync()
                interval = env.model.opt.timestep / args.speed
                time.sleep(max(0.0, interval - (time.monotonic() - started)))
    finally:
        env.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
