"""Host-only, one-way display of the live MuJoCo episode."""

from __future__ import annotations

import copy
import math
import time


class LiveViewer:
    def __init__(self, env, *, fps=15):
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("Viewer FPS must be finite and positive")
        import mujoco.viewer
        import numpy as np

        self.env = env
        self.interval = 1.0 / fps
        self.last_sync = float("-inf")
        # Mouse perturbations and GUI controls must never change episode state,
        # model options, collisions or actuators. Only the display copy is writable.
        self.model = copy.copy(env.model)
        self.data = env.mujoco.MjData(self.model)
        self.state_spec = env.mujoco.mjtState.mjSTATE_INTEGRATION
        self.state = np.empty(env.mujoco.mj_stateSize(env.model, self.state_spec))
        self._copy_state()
        self.handle = mujoco.viewer.launch_passive(self.model, self.data)
        camera = env.mujoco.mj_name2id(env.model, env.mujoco.mjtObj.mjOBJ_CAMERA, "top_cam")
        self.handle.cam.type = env.mujoco.mjtCamera.mjCAMERA_FIXED
        self.handle.cam.fixedcamid = camera
        self.sync(force=True)

    def _copy_state(self):
        mujoco = self.env.mujoco
        mujoco.mj_getState(self.env.model, self.env.data, self.state, self.state_spec)
        mujoco.mj_setState(self.model, self.data, self.state, self.state_spec)
        mujoco.mj_forward(self.model, self.data)

    def sync(self, *, force=False):
        if not self.handle.is_running():
            raise RuntimeError("Live viewer closed; episode interrupted by operator")
        now = time.monotonic()
        if force or now - self.last_sync >= self.interval:
            with self.handle.lock():
                self._copy_state()
            self.handle.sync()
            self.last_sync = now

    def after_action(self, started):
        # Keep native actions at 20 Hz for a watchable live run. Thinking/idle
        # time never advances physics or accumulates a catch-up backlog.
        from simulators.mujoco_so101 import CONTROL_HZ

        self.sync()
        time.sleep(max(0.0, 1.0 / CONTROL_HZ - (time.monotonic() - started)))

    def close(self):
        self.handle.close()
