"""Show five seeded SO-101 pick-and-place runs in the MuJoCo viewer."""

from __future__ import annotations

import argparse
import time

DEFAULT_SEEDS = (11, 12, 13, 14, 15)


def positive_number(value):
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return number


def show_for(viewer, seconds, fps):
    deadline = time.monotonic() + seconds
    interval = 1.0 / fps
    while time.monotonic() < deadline:
        if not viewer.is_running():
            raise RuntimeError("MuJoCo viewer was closed before the demo finished")
        started = time.monotonic()
        viewer.sync()
        time.sleep(max(0.0, interval - (time.monotonic() - started)))


def move(env, viewer, position, gripper, count, fps):
    interval = 1.0 / fps
    for _ in range(count):
        if env.done:
            break
        if not viewer.is_running():
            raise RuntimeError("MuJoCo viewer was closed before the demo finished")
        started = time.monotonic()
        env.control_step({"ee_position": position, "ee_joint_state": [gripper]})
        viewer.sync()
        time.sleep(max(0.0, interval - (time.monotonic() - started)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    parser.add_argument("--fps", type=positive_number, default=15.0)
    parser.add_argument("--lead-seconds", type=positive_number, default=3.0)
    parser.add_argument("--hold-seconds", type=positive_number, default=2.0)
    args = parser.parse_args(argv)
    if not args.seeds or any(seed < 0 for seed in args.seeds):
        parser.error("--seeds requires one or more nonnegative integers")

    import mujoco.viewer

    from orchestrator.config import load_task
    from simulators.backend import build

    env = build(load_task("SO101MuJoCo"), seed=args.seeds[0])
    results = []
    try:
        with mujoco.viewer.launch_passive(env.model, env.data) as viewer:
            camera_id = env.mujoco.mj_name2id(
                env.model, env.mujoco.mjtObj.mjOBJ_CAMERA, "top_cam"
            )
            viewer.cam.type = env.mujoco.mjtCamera.mjCAMERA_FIXED
            viewer.cam.fixedcamid = camera_id
            print(
                f"Live demo running: {len(args.seeds)} scenes, top_cam, "
                f"{args.fps:g} FPS.",
                flush=True,
            )
            for index, seed in enumerate(args.seeds, start=1):
                env.scene_seed = seed
                env.reset(seed=seed)
                cube = env.data.xpos[env._cube_id].copy()
                target = env.data.xpos[env._target_id].copy()
                print(
                    f"[{index}/{len(args.seeds)}] seed={seed}, "
                    f"cube=({cube[0]:.6f}, {cube[1]:.6f}, {cube[2]:.6f})",
                    flush=True,
                )
                show_for(
                    viewer,
                    args.lead_seconds if index == 1 else args.hold_seconds,
                    args.fps,
                )
                move(env, viewer, cube + (0, 0, 0.065), 1.0, 18, args.fps)
                move(env, viewer, cube + (0, 0, 0.012), 1.0, 18, args.fps)
                move(env, viewer, cube + (0, 0, 0.012), 0.0, 15, args.fps)
                move(env, viewer, cube + (0, 0, 0.065), 0.0, 18, args.fps)
                move(env, viewer, target + (0, 0, 0.076), 0.0, 18, args.fps)
                move(env, viewer, target + (0, 0, 0.028), 0.0, 18, args.fps)
                move(env, viewer, target + (0, 0, 0.028), 1.0, 15, args.fps)
                show_for(viewer, args.hold_seconds, args.fps)
                if not env.success:
                    raise RuntimeError(f"seed {seed} did not complete pick-and-place")
                results.append(seed)
                print(f"[{index}/{len(args.seeds)}] seed={seed}: success", flush=True)
            show_for(viewer, args.hold_seconds, args.fps)
    finally:
        env.close()

    print(f"Live demo complete: {len(results)}/{len(args.seeds)} succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
