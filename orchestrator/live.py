"""Launch options for watching a real episode, outside the agent workspace."""

from __future__ import annotations

import math
import sys


def validate_viewer(cfg, viewer, fps, *, test_gpus=None):
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("Viewer FPS must be finite and positive")
    if viewer and cfg.simulator.backend != "mujoco_so101":
        raise ValueError("--viewer requires the mujoco_so101 backend")
    if viewer and test_gpus is not None:
        raise ValueError("--viewer requires sequential scenes; omit --test-gpus/--test-gpu-slots")


def simulator_command(cfg, *, viewer=False, fps=15):
    validate_viewer(cfg, viewer, fps)
    interpreter = cfg.python
    if viewer and sys.platform == "darwin":
        interpreter = interpreter.with_name("mjpython")
        if not interpreter.is_file():
            raise ValueError("macOS live viewer requires mjpython in the simulator environment")
    command = [str(interpreter), "-m", "orchestrator.session"]
    if viewer:
        command += ["--viewer", "--viewer-fps", str(fps)]
    return command


def simulator_env(gpu, backend, *, viewer=False):
    from orchestrator.resources import sim_env

    env = sim_env(gpu, backend)
    if viewer and sys.platform.startswith("linux"):
        # EGL is for headless rendering; GLFW owns the visible desktop window.
        env["MUJOCO_GL"] = "glfw"
        env.pop("PYOPENGL_PLATFORM", None)
    return env
