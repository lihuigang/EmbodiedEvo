"""Viewer launch and state-isolation checks; no GUI or model request required."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from orchestrator import session_runner
from orchestrator.__main__ import main
from orchestrator.config import load_task
from orchestrator.live import simulator_command, simulator_env, validate_viewer


class LaunchTests(unittest.TestCase):
    def test_macos_uses_mjpython_only_for_visible_sessions(self):
        cfg = load_task("SO101MuJoCo")
        with patch("orchestrator.live.sys.platform", "darwin"), patch(
            "pathlib.Path.is_file", return_value=True
        ):
            visible = simulator_command(cfg, viewer=True)
            headless = simulator_command(cfg)
        self.assertEqual(visible[0], str(cfg.python.with_name("mjpython")))
        self.assertIn("--viewer", visible)
        self.assertEqual(headless, [str(cfg.python), "-m", "orchestrator.session"])

    def test_linux_viewer_uses_glfw_and_headless_keeps_egl(self):
        with patch("orchestrator.live.sys.platform", "linux"), patch.dict(
            "os.environ", {"MUJOCO_GL": "egl", "PYOPENGL_PLATFORM": "egl"}
        ):
            visible = simulator_env(None, "mujoco_so101", viewer=True)
            headless = simulator_env(None, "mujoco_so101")
        self.assertEqual(visible["MUJOCO_GL"], "glfw")
        self.assertNotIn("PYOPENGL_PLATFORM", visible)
        self.assertEqual(headless["MUJOCO_GL"], "egl")

    def test_invalid_options_fail_before_launch_or_scene_plan_creation(self):
        cfg = load_task("SO101MuJoCo")
        for fps in (0, -1, float("nan"), float("inf")):
            with self.subTest(fps=fps), self.assertRaises(ValueError):
                validate_viewer(cfg, True, fps)
        with self.assertRaisesRegex(ValueError, "sequential"):
            validate_viewer(cfg, True, 15, test_gpus=["0"])
        with self.assertRaisesRegex(ValueError, "mujoco_so101"):
            validate_viewer(load_task("RoboDojo"), True, 15)

    def test_cli_forwards_live_options_to_both_stages(self):
        with patch.object(session_runner, "explore", return_value=0) as explore, patch.object(
            session_runner, "test", return_value=0
        ) as evaluate:
            self.assertEqual(main([
                "run", "--task", "SO101MuJoCo", "--run-dir", "runs/202610161200_live",
                "--viewer", "--viewer-fps", "12", "--test-scenes", "5",
            ]), 0)
        for call in (explore.call_args, evaluate.call_args):
            self.assertTrue(call.kwargs["viewer"])
            self.assertEqual(call.kwargs["viewer_fps"], 12)
            self.assertEqual(call.args[0].test.scenes, 5)

    def test_cli_rejects_parallel_viewer_before_starting_playground(self):
        with patch.object(session_runner, "explore") as explore, contextlib.redirect_stderr(
            io.StringIO()
        ), self.assertRaises(SystemExit):
            main([
                "run", "--task", "SO101MuJoCo", "--run-dir", "runs/202610161200_live",
                "--viewer", "--test-gpus", "0,1",
            ])
        explore.assert_not_called()


@unittest.skipUnless(importlib.util.find_spec("mujoco"), "requires the native MuJoCo runtime")
class SnapshotTests(unittest.TestCase):
    def test_display_perturbation_and_sync_never_modify_live_physics(self):
        import mujoco
        import mujoco.viewer
        import numpy as np

        from simulators.live_viewer import LiveViewer

        model = mujoco.MjModel.from_xml_string('''<mujoco><worldbody>
            <body name="object"><freejoint/><geom type="sphere" size="0.1"/></body>
            <camera name="top_cam" pos="0 0 1"/>
            </worldbody></mujoco>''')
        data = mujoco.MjData(model)
        handle = Mock()
        handle.lock.side_effect = contextlib.nullcontext
        source_qpos = data.qpos.copy()
        source_gravity = model.opt.gravity.copy()
        with patch.object(mujoco.viewer, "launch_passive", return_value=handle):
            viewer = LiveViewer(SimpleNamespace(model=model, data=data, mujoco=mujoco))
        viewer.data.qpos[0] = 99
        viewer.data.xfrc_applied[:] = 100
        viewer.model.opt.gravity[:] = 0
        viewer.sync(force=True)
        np.testing.assert_array_equal(data.qpos, source_qpos)
        np.testing.assert_array_equal(model.opt.gravity, source_gravity)
        np.testing.assert_array_equal(data.xfrc_applied, 0)
        np.testing.assert_array_equal(viewer.data.qpos, data.qpos)
        data.qpos[0] = 0.25
        viewer.sync(force=True)
        self.assertEqual(viewer.data.qpos[0], 0.25)
        handle.is_running.return_value = False
        with self.assertRaisesRegex(RuntimeError, "interrupted by operator"):
            viewer.sync()
        viewer.close()
        handle.close.assert_called_once()

    def test_idle_sync_does_not_advance_time_or_action_budget(self):
        from simulators.live_viewer import LiveViewer

        viewer = LiveViewer.__new__(LiveViewer)
        viewer.sync = Mock()
        with patch("simulators.live_viewer.time.monotonic", return_value=10.02), patch(
            "simulators.live_viewer.time.sleep"
        ) as sleep:
            viewer.after_action(10)
        self.assertAlmostEqual(sleep.call_args.args[0], 0.03)
        viewer.sync.assert_called_once()


if __name__ == "__main__":
    unittest.main()
