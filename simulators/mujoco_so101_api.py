"""SO-101 MuJoCo primitives; native dependencies stay lazy in the task adapter."""

from simulators.primitives import PrimitiveApi


class MuJoCoSO101LowLevelApi(PrimitiveApi):
    def functions(self):
        return {
            "get_instruction": self.get_instruction,
            "get_observation": self.get_observation,
            "step": self.step,
            "reset": self.reset,
        }

    def get_instruction(self):
        return self._env.task_prompt()

    def get_observation(self):
        return self._env.public_observation()

    def step(self, action):
        return self._env.control_step(action)
