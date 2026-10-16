from __future__ import annotations

import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from orchestrator.config import load_task
from orchestrator.files import test_seeds as sample_test_seeds
from orchestrator.session_runner import prepare_inputs, validate
from simulators.mujoco_so101 import (
    GRIPPER_CLOSED,
    GRIPPER_OPEN,
    MuJoCoSO101Task,
    _add_scene,
)
from simulators.mujoco_so101_api import MuJoCoSO101LowLevelApi
from simulators.primitives import PROGRAM_PRIMITIVES, SURFACES, load_surface


class SceneTests(unittest.TestCase):
    def test_scene_adds_task_objects_without_replacing_robot(self):
        source = '<mujoco><asset/><worldbody><body name="base"/></worldbody></mujoco>'
        root = ET.fromstring(_add_scene(source))
        self.assertIsNotNone(root.find("./worldbody/body[@name='base']"))
        self.assertIsNotNone(root.find("./worldbody/body[@name='cube']/freejoint"))
        self.assertIsNotNone(root.find("./worldbody/body[@name='target']"))
        self.assertIsNotNone(root.find("./worldbody/camera[@name='top_cam']"))

    def test_scene_rejects_model_without_worldbody(self):
        with self.assertRaisesRegex(RuntimeError, "worldbody"):
            _add_scene("<mujoco/>")


class InterfaceTests(unittest.TestCase):
    def test_surface_exposes_exact_protocol(self):
        self.assertEqual(SURFACES["mujoco_so101"], "MuJoCoSO101LowLevelApi")
        self.assertIs(load_surface("mujoco_so101"), MuJoCoSO101LowLevelApi)
        self.assertEqual(set(MuJoCoSO101LowLevelApi(None).functions()), PROGRAM_PRIMITIVES)

    def test_gripper_conversion_round_trips(self):
        self.assertEqual(MuJoCoSO101Task._normalize_gripper(GRIPPER_CLOSED), 0)
        self.assertEqual(MuJoCoSO101Task._normalize_gripper(GRIPPER_OPEN), 1)
        for value in (0.0, 0.2, 0.75, 1.0):
            radians = MuJoCoSO101Task._gripper_radians(value)
            self.assertAlmostEqual(MuJoCoSO101Task._normalize_gripper(radians), value)

    def test_action_vectors_reject_wrong_shape_and_nonfinite_values(self):
        for value in ([1, 2], [1, np.nan, 3], [[1, 2, 3]]):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "finite vector"):
                MuJoCoSO101Task._finite_vector({"x": value}, "x", 3)

    def test_control_budget_stops_native_physics(self):
        env = MuJoCoSO101Task.__new__(MuJoCoSO101Task)
        env.initialize(MuJoCoSO101LowLevelApi(env))
        env.max_steps = 2
        env._failure = None
        env._apply_action = Mock()
        env._update_success = Mock()
        env._native_observation = Mock(return_value={"instruction": "task", "state": {}})
        env.mujoco = SimpleNamespace(mj_step=Mock())
        env.model = env.data = object()
        env.observe(env._native_observation())

        self.assertFalse(env.control_step({})[3])
        self.assertTrue(env.control_step({})[3])
        env.control_step({})
        self.assertEqual(env.control_steps, 2)
        self.assertEqual(env._apply_action.call_count, 2)
        self.assertEqual(env.mujoco.mj_step.call_count, 20)

    def test_invalid_action_does_not_poison_simulator(self):
        env = MuJoCoSO101Task.__new__(MuJoCoSO101Task)
        env.initialize(MuJoCoSO101LowLevelApi(env))
        env.max_steps = 2
        env._failure = None
        env._apply_action = Mock(side_effect=ValueError("bad action"))
        env._update_success = Mock()
        env._native_observation = Mock()
        env.mujoco = SimpleNamespace(mj_step=Mock())
        env.model = env.data = object()

        with self.assertRaisesRegex(ValueError, "bad action"):
            env.control_step({})
        self.assertIsNone(env._failure)
        self.assertEqual(env.control_steps, 0)
        env.mujoco.mj_step.assert_not_called()

    def test_playground_reset_renews_attempt_preserving_cumulative_actions_and_globals(self):
        env = MuJoCoSO101Task.__new__(MuJoCoSO101Task)
        env.initialize(MuJoCoSO101LowLevelApi(env))
        env.scene_seed = 7
        env.native_step_limit = env.max_steps = 300
        env._live_viewer = None
        env._reset_native = Mock()
        env._native_observation = Mock(return_value={"instruction": "task", "state": {}})
        env.execution_phase = "playground"
        env.reset(seed=7)
        env.control_steps = 300
        env.truncated = True
        env._exec_globals["remember"] = 17
        env.reset_from_program()
        self.assertEqual(env.max_steps - env.control_steps, 300)
        self.assertEqual(env.control_steps, 300)
        self.assertEqual(env._exec_globals["remember"], 17)
        self.assertFalse(env.done)
        env.control_steps += 25
        env.reset_from_program()
        self.assertEqual(env.max_steps - env.control_steps, 300)
        self.assertEqual(env.control_steps, 325)
        env.execution_phase = "test"
        env._reset_native.reset_mock()
        with self.assertRaises(PermissionError):
            env.reset_from_program()
        env._reset_native.assert_not_called()


class ConfigurationTests(unittest.TestCase):
    def test_regular_and_baseline_task_definitions_prepare(self):
        for name, baseline in (("SO101MuJoCo", False), ("tasks_baseline/SO101MuJoCo", True)):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                cfg = load_task(name)
                self.assertEqual(cfg.baseline, baseline)
                self.assertEqual(cfg.simulator.backend, "mujoco_so101")
                self.assertEqual(cfg.simulator.env_task, "pick_cube")
                self.assertEqual(cfg.python.name, "python")
                validate(cfg)
                prepared = prepare_inputs(cfg, Path(tmp))
                self.assertIn("primitives/primitives.md", prepared)

    def test_generic_seed_sampling_excludes_playground(self):
        cfg = load_task("SO101MuJoCo")
        seeds = sample_test_seeds(cfg)
        self.assertEqual(len(seeds), cfg.test.scenes)
        self.assertEqual(len(set(seeds)), len(seeds))
        self.assertNotIn(cfg.playground.seed, seeds)

    def test_backend_build_dispatches_without_importing_mujoco_early(self):
        cfg = load_task("SO101MuJoCo")
        fake = Mock()
        with patch("simulators.mujoco_so101.MuJoCoSO101Task", return_value=fake) as constructor:
            from simulators.backend import build

            with self.assertRaisesRegex(TypeError, "Environment"):
                build(cfg, seed=7)
        constructor.assert_called_once_with(task_name="pick_cube", seed=7)


if __name__ == "__main__":
    unittest.main()
