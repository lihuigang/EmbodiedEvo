"""Open the seeded SO-101 task in MuJoCo's interactive viewer."""

from __future__ import annotations

import argparse
import json
import time


def positive_number(value):
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
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
        type=positive_number,
        default=1.0,
        help="simulation speed multiplier (default: 1)",
    )
    parser.add_argument(
        "--fps",
        type=positive_number,
        default=30.0,
        help="maximum GUI refresh rate (default: 30)",
    )
    parser.add_argument(
        "--paused",
        action="store_true",
        help="show a static scene without advancing physics",
    )
    parser.add_argument(
        "--duration",
        type=positive_number,
        help="close automatically after this many seconds",
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
            frame_interval = 1.0 / args.fps
            simulation_target = env.data.time
            deadline = time.monotonic() + args.duration if args.duration else None
            print(
                f"Viewer running: camera={args.camera}, fps={args.fps:g}, "
                f"paused={args.paused}. Close the window to stop.",
                flush=True,
            )
            while viewer.is_running():
                started = time.monotonic()
                if deadline is not None and started >= deadline:
                    break
                if not args.paused:
                    simulation_target += frame_interval * args.speed
                    while env.data.time < simulation_target:
                        env.mujoco.mj_step(env.model, env.data)
                viewer.sync()
                time.sleep(max(0.0, frame_interval - (time.monotonic() - started)))
    finally:
        env.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
