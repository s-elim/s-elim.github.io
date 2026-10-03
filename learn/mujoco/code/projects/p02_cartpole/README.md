# Project 2: balance a cart-pole with LQR on MuJoCo's linearization

**Level** 8 (after Lessons 3.2, 8.1 and 8.2; Level 21.4 for the theory) · **Time** 3 to 4 hours · **Difficulty** 3 of 5

## Objective

Balance the course cart-pole (`models/cartpole.xml`) upright from a tilted start by linear-quadratic regulation, using MuJoCo itself to compute the linear model. You will see that MuJoCo is a source of models for control design, not only a place to test controllers.

## Prerequisites

- Lesson 1.1 (state and `mj_forward`), Lesson 3.2 (where this balance law first appears).
- Linear state-space models $x_{k+1} = A x_k + B u_k$ and the idea of a feedback gain.
- `scipy.linalg.solve_discrete_are`.

## Starter code

`starter.py` asks for three functions:

- `linearize(model, qpos)`: the discrete-time $A$ and $B$ of one `mj_step` around an equilibrium, from `mujoco.mjd_transitionFD` (finite differences of the transition map).
- `lqr_gain(a, b, q, r)`: the infinite-horizon discrete LQR gain $K$ with $u = -Kx$.
- `controller(k, data)`: the cart force for the current state $x = [q_\text{cart}, q_\text{pole}, \dot q_\text{cart}, \dot q_\text{pole}]$.

The tests use $Q = \mathrm{diag}(1, 10, 0.1, 0.1)$ and $R = 0.01$.

## Expected behaviour

The linear model predicts one simulated step from a small perturbation to within $2 \times 10^{-5}$. The closed-loop matrix $A - BK$ has all eigenvalues inside the unit circle. From a 0.15 rad tilt the pole never exceeds 0.2 rad, the cart stays within 1.4 m of the centre (the rail ends at 1.5 m), the force never exceeds the actuator's 20 N, and after 10 s the pole is upright to $10^{-3}$ rad. The same gains still balance a pole 50% heavier than the one they were designed for.

## Tests

```bash
MJC_IMPL=starter pytest projects/p02_cartpole
pytest projects/p02_cartpole
```

## Common failures

- **Linearizing at the wrong point.** In `cartpole.xml` the pole angle is 0 when upright; linearizing at the hanging position ($\pi$) gives a stable linear model and a controller that does nothing useful upright.
- **Feedback on the pole only.** A PD law on the pole angle can hold it for a while, then the cart runs into the end of the rail (this course's own first attempt in Lesson 3.2 did exactly that). LQR uses all four states.
- **Sign of the gain.** `scipy` returns $P$; the gain is $K = (R + B^\top P B)^{-1} B^\top P A$ and the control is $u = -Kx$.
- **Finite-difference step too large or too small.** `mjd_transitionFD` with `eps` around $10^{-6}$ is accurate here; check with the one-step prediction test.

## Extension challenges

1. Swing the pole up from hanging with an energy-based controller, then switch to LQR near upright.
2. Add an actuator delay (`delay` and `nsample` on the motor, MuJoCo 3.5+) and find the largest delay the LQR controller tolerates. Compare with a prediction from the linear model.
3. Design the controller for a pole 50% heavier and test it on the nominal one. Is robustness symmetric?

## Solution

`solution.py`, about 25 lines.
