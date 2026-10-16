# SO-101 MuJoCo native primitives

Submitted Python runs in one persistent simulator namespace. `np` exposes the restricted
NumPy surface; imports, files, networking, simulator internals and object ground truth are
not available. The only environment primitives are the four functions below.

## get_instruction()

Returns the episode instruction without advancing physics.

## get_observation()

Returns a detached copy of the latest observation. `vision.top_cam.color` and
`vision.wrist_cam.color` are 256×256 RGB uint8 images. `state.arm_joint_state` contains
the five arm angles in radians, `state.ee_joint_state` contains the normalized gripper
state (`0` closed, `1` open), and `state.ee_pose` is `[x,y,z,qw,qx,qy,qz]` in metres.
`action` contains the most recent joint/gripper targets. No cube or target pose is exposed.

## step(action)

Accepts exactly one of these finite action dictionaries:

```python
# Absolute joint targets (five radians plus normalized gripper).
step({'arm_joint_state': arm, 'ee_joint_state': [gripper]})

# Absolute XYZ target using damped least-squares IK with the gripper kept downward.
step({'ee_position': [x, y, z], 'ee_joint_state': [gripper]})
```

Joint targets are clamped to the SO-101 limits. Each call advances one 20 Hz controller
interval. It returns `(observation, reward, terminated, truncated, info)`; reward and
`info['success']` are the binary task signal. The released cube must remain stably inside
the green target for five control intervals. The native episode limit is 300 actions;
query `status` for the live remaining budget. Calls after success or truncation do not
advance physics.

## reset()

Playground only. Restores the same seeded cube layout and renews its 300-action attempt.
Python variables, used execution slots, elapsed time and cumulative action telemetry remain.
Reset is forbidden in Test, including through aliases.
