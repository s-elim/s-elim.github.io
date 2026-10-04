# Project 4: joint PD and gravity compensation on the 7-DOF arm

**Level** 8 (after Lessons 8.1 and 8.2) · **Time** 3 hours · **Difficulty** 2 of 5

## Objective

Implement joint-space PD and PD with gravity compensation for `models/arm7.xml` (torque motors on all seven joints), design the gains from the arm's own inertia, and characterize the step response. Then predict, without simulating, how far the arm sags when the compensation is switched off.

## Prerequisites

- Lesson 8.1 (PD control, the second-order step response, damping ratio).
- Lesson 8.2 (gravity compensation from `qfrc_bias`).
- Lesson 7.2 for the joint-space mass matrix and `mj_fullM`.

## Starter code

`starter.py` asks for two constants and three functions:

- `OMEGA`, `ZETA`: the natural frequency and damping ratio you design for.
- `design_gains(model, data, omega, zeta)`: per-joint $k_p$ and $k_d$ that make each joint, taken alone, a second-order system with that $\omega$ and $\zeta$.
- `pd_torque(model, data, q_des, kp, kd, compensate)`: the torque command, with gravity compensation when `compensate` is true, inside `ctrlrange`.
- `predicted_steady_error(model, q_des, kp)`: the steady error $q_\text{des} - q$ without compensation, computed from statics alone.

## Expected behaviour

All results below are from the reference solution ($\omega$ = 18 rad/s, $\zeta$ = 1) starting at the `home` keyframe with a 0.3 rad step on every joint.

- **With compensation.** The largest overshoot is 2.35% and every joint is within 1% of its target after 0.472 s. The design uses the diagonal of the mass matrix, so the joints are coupled through its off-diagonal terms; that coupling is what leaves a 2.35% overshoot where a critically damped single joint would have none. Shoulder yaw and pitch (j1, j2) saturate their torque limits for 10 ms and 18 ms at the start of the step.
- **The speed limit.** At $\omega$ = 14 rad/s nothing saturates, but the slowest joint takes 0.61 s to settle. The 0.5 s requirement therefore costs about 20 ms of saturation on the two shoulder joints: their 80 N m limits are shared between the step and a 24.5 N m gravity load at j2.
- **Without compensation.** The arm sags. Shoulder pitch (j2) ends 0.0489 rad from its target and the elbow (j4) 0.0251 rad. Predicting the error as load at $q_\text{des}$ divided by $k_p$ gets j2 within 1.4% but misses j4 by 20%. The shoulder's sag changes the configuration and therefore the load the elbow carries. Solving the equilibrium $k_p\,e = \text{load}(q_\text{des} - e)$ by fixed-point iteration matches all five loaded joints to the fourth decimal.

## Tests

```bash
MJC_IMPL=starter pytest projects/p04_joint_pd
pytest projects/p04_joint_pd
```

Four tests: gains of the right shape and sign; the compensated step (overshoot under 5%, within 1% after 0.5 s, every command inside `ctrlrange`); the steady error without compensation within 10% of your prediction on every loaded joint; and the compensated steady error under $10^{-4}$ rad. The first-order prediction fails the third test, and $\omega$ = 12 fails the second.

## Common failures

- **Compensating with a stale `qfrc_bias`.** After `mj_step`, `data.qfrc_bias` belongs to the state before the step. Here that changes the torque by at most 0.32 N m and the trajectory by at most 0.5 mrad, so the tests cannot see it. On a stiffer, faster or heavier system the stale term is a real error. Call `mj_forward` (or at least `mj_kinematics` plus `mj_rne`) first.
- **Gains tuned for one pose that ring at another.** Start the same design at the `zero` keyframe (arm straight up) and the largest overshoot is 38%, and the arm has still not settled after 1.5 s. Shoulder yaw's inertia grows from 0.065 to 0.49 kg m² as the arm tips over, so gains sized at the start leave the joint underdamped by a factor of about $\sqrt{7.6} \approx 2.8$. That factor is inferred from the inertia ratio.
- **Ignoring armature.** `mj_fullM` includes the 0.05 kg m² armature on every joint. On the wrist joints that is most of the inertia (0.05 of 0.0546 kg m² at j5), so gains computed from link inertia alone are about 12 times too small there.
- **Prediction from the target pose.** See the 20% miss at j4 above.

## Extension challenges

1. Gain scheduling: recompute the gains from `mj_fullM` every step, and show the `zero`-pose step now meets the same criteria.
2. Replace the diagonal design with $\tau = M(q)(\omega^2 e - 2\zeta\omega \dot q) + \text{bias}$ (computed torque) and compare overshoot and peak torque.
3. Add 20 ms of actuator delay and find the largest $\omega$ that still settles without ringing.

## Solution

`solution.py`, about 35 lines.
