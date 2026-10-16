# SO-101 MuJoCo Test primitives

Submitted Python runs in one persistent simulator namespace. `np` exposes restricted NumPy;
imports, files, networking, simulator internals and object ground truth are unavailable.

## get_instruction()

Returns the episode instruction without advancing physics.

## get_observation()

Returns top and wrist RGB images plus five arm angles, normalized gripper state, and the
end-effector pose `[x,y,z,qw,qx,qy,qz]`. No cube or target ground-truth pose is exposed.

## step(action)

Use either absolute joint targets:

```python
step({'arm_joint_state': arm, 'ee_joint_state': [gripper]})
```

or an absolute XYZ target through downward-gripper damped least-squares IK:

```python
step({'ee_position': [x, y, z], 'ee_joint_state': [gripper]})
```

The gripper value is normalized (`0` closed, `1` open). One call advances one 20 Hz
controller interval. The return value is Gymnasium's five-tuple; reward and success are
binary. The released cube must remain stably inside the green target for five intervals.
Test has one 300-action allowance and no reset primitive.
