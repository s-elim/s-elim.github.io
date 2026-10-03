The mathematics in this course is introduced where a robot first needs it, not in a block at the start. This page lists every topic in the order a learner meets it, with the lesson that teaches it and the lab or code that checks it against MuJoCo. Each topic follows the same pattern in its lesson: intuition first, then every symbol defined, a picture or lab, the derivation where it earns its place, a Python implementation, and the link to the MuJoCo field or function that computes the same thing.

## Prerequisites

Comfort with vectors, matrices, the dot and cross products, and derivatives of functions of one variable. Everything else is built up. If linear algebra is rusty, the first half of any introductory course on it is enough; the course never needs more than eigenvalues of symmetric $3 \times 3$ matrices before Level 7.

## The sequence

| Topic | Where | Checked against |
|---|---|---|
| State, ODEs, the timestep | [0.1](#/lesson/0.1) | falling ball: simulated vs. exact $z(t)$ |
| First-order integration error, $\tfrac12 g h t$ | [0.1](#/lesson/0.1) | measured to the printed digit for five timesteps |
| Generalized coordinates, $n_q$ versus $n_v$ | [1.2](#/lesson/1.2) | `mj_differentiatePos`, `mj_integratePos` |
| Quaternion integration on the unit sphere | [1.2](#/lesson/1.2) | quaternion norm after `mj_integratePos` |
| Integrator stability: $h < 2/\omega$, $h < 2I/c$ | [1.3](#/lesson/1.3) | servo stability table, five integrators |
| Energy drift of single-step versus RK4 methods | [1.3](#/lesson/1.3) | double pendulum, 20 s |
| Frames and the composition of rigid transforms | [2.1](#/lesson/2.1), [4.1](#/lesson/4.1) | site pose composed by hand vs. `site_xpos` |
| Rotation matrices, quaternions, Euler sequences | [4.1](#/lesson/4.1) | `mju_euler2Quat`, `mju_rotVecQuat`, six sequences |
| Exponential and logarithm maps on rotations, geodesic angle | [4.1](#/lesson/4.1) | `mjcourse.spatial` tests; arccos precision loss |
| $SE(3)$, homogeneous transforms and their inverses | [4.1](#/lesson/4.1) | `transform_inv` test |
| Mass properties of primitives, parallel-axis theorem | [2.2](#/lesson/2.2), [4.2](#/lesson/4.2) | `body_mass`, `body_inertia`, `body_iquat` |
| Principal axes; inertia triangle inequality | [4.2](#/lesson/4.2) | L-shaped body; compiler error |
| Euler's equations and the intermediate-axis instability | [4.2](#/lesson/4.2) | tumbling box flips; linearized growth rate |
| Newton-Euler equations for one body | [4.3](#/lesson/4.3) | `qacc` of a free body under a known wrench |
| Momentum, energy, restitution | [4.3](#/lesson/4.3) | two-ball collision table |
| Actuator force law $p = a u + b_0 + b_1 l + b_2 \dot l$ | [2.3](#/lesson/2.3) | `actuator_force` for four actuator types |
| Forward kinematics as a product of transforms | [6.1](#/lesson/6.1) | planned |
| Jacobians, velocity kinematics, singular values | [6.2](#/lesson/6.2) | `mj_jacSite` against finite differences (in `mjcourse.kinematics` tests) |
| Damped least squares, null-space projection | [6.3](#/lesson/6.3) | `mjcourse.kinematics.solve_ik` |
| Lagrangian mechanics; $M(q)\ddot q + c(q, \dot q) = \tau$ | [7.1](#/lesson/7.1) | planned: two-link $M(q)$ against `mj_fullM` |
| Forward and inverse dynamics | [7.2](#/lesson/7.2) | planned: `mj_inverse` |
| Linear second-order systems: damping ratio, overshoot, settling | [8.1](#/lesson/8.1) | planned |
| Feedback linearization; operational-space inertia $\Lambda = (J M^{-1} J^\top)^{-1}$ | [8.2](#/lesson/8.2), [8.3](#/lesson/8.3) | `mjcourse.control` |
| Soft constraints: reference acceleration, impedance | [9.2](#/lesson/9.2) | planned |
| Convex optimization of constraint forces; friction cones | [9.2](#/lesson/9.2), [9.3](#/lesson/9.3) | planned |
| Pinhole camera model, intrinsics, extrinsics, projection | [11.1](#/lesson/11.1) | planned |
| MDPs, policy gradients, advantage estimation | [13.1](#/lesson/13.1), [13.2](#/lesson/13.2) | planned |
| Least squares and identifiability (condition numbers) | [18.1](#/lesson/18.1) | planned |
| Finite-difference derivatives of the transition map | [20.4](#/lesson/20.4) | planned: `mjd_transitionFD` |
| Confidence intervals for success rates; bootstrap | [21.2](#/lesson/21.2), [Research mode](#/page/research-mode) | `mjcourse.stats` |

Rows marked "planned" belong to lessons whose text is not written yet; the topic and its place in the sequence are fixed.

## How to use this page

If you came to the course for its mathematics, follow the table top to bottom and do the derivation boxes with pen and paper before reading them. Every derivation in the course ends at something you can check numerically, and the check is the point: a derivation that MuJoCo disagrees with has an error in it, in the derivation, in the model, or in your understanding of what MuJoCo computes. Finding which is the skill.
