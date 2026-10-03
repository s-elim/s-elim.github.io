# Project 1: a pendulum simulator that matches MuJoCo

**Level** 1 (after Lessons 0.1 and 1.3) · **Time** 2 to 3 hours · **Difficulty** 1 of 5

## Objective

Write your own simulator for the course pendulum (`models/pendulum.xml`) in NumPy, with two integrators, and show that it reproduces MuJoCo's trajectory step by step. The point is to see that MuJoCo is not magic: for a model this simple, a page of code computes the same numbers.

## Prerequisites

- Lesson 0.1: state, integration, the semi-implicit Euler update.
- Lesson 1.3: what each MuJoCo integrator does.
- Python and NumPy.

## Starter code

`starter.py` declares the model's parameters and two functions to fill in:

- `acceleration(theta, omega, damping, torque)`: the angular acceleration. Work out the sign from the model file: the hinge axis is $+y$ and the bob hangs at $(0, 0, -L)$.
- `simulate(theta0, omega0, h, steps, method, damping)`: returns an array of shape `(steps + 1, 2)` of `(theta, omega)`, for `method` in `"euler"` (semi-implicit) and `"rk4"`.

## Expected behaviour

From $\theta_0 = 1$ rad at rest with $h$ = 2 ms, your semi-implicit Euler trajectory equals MuJoCo's `Euler` trajectory to $10^{-9}$ for 1000 steps, and your RK4 trajectory equals MuJoCo's `RK4` to $10^{-8}$. RK4 conserves energy to better than $10^{-6}$ J over 10 s at 1 ms. The small-angle period equals $2\pi\sqrt{I/(mgL)}$ within 0.2%.

## Tests

```bash
MJC_IMPL=starter pytest projects/p01_pendulum     # your code
pytest projects/p01_pendulum                      # the reference solution
```

Six tests: the sign of the acceleration, agreement with MuJoCo under `Euler` and under `RK4`, RK4 energy conservation, the small-angle period, and damping that brings the pendulum to rest.

## Common failures

- **Sign error in gravity.** The trajectory oscillates but drifts away from MuJoCo's within a few steps. Recheck which way positive $\theta$ moves the bob.
- **Using $I = mL^2$.** The model adds a rotor inertia `I_C` = $10^{-4}$ kg m²; without it the agreement stops at about $4 \times 10^{-4}$ relative error.
- **Explicit Euler instead of semi-implicit.** Updating position with the old velocity gives an energy that grows steadily and a trajectory that disagrees with MuJoCo after the first step.
- **RK4 off by a step.** Storing the state before the update instead of after shifts the whole array by one row.

## Extension challenges

1. Add joint damping to the comparison. MuJoCo's `Euler` integrates joint damping implicitly (Lesson 1.3); implement $v_{t+h} = (v_t + h\,a_{\text{undamped}})/(1 + h b/I)$ and match it with damping 0.2.
2. Add a constant motor torque and match MuJoCo with `data.ctrl` set.
3. Plot the energy error against time for both methods at $h$ = 1, 2, 5 and 10 ms, and fit its growth.

## Solution

`solution.py` is the reference implementation. Read it after the tests pass for your own code, not before.
