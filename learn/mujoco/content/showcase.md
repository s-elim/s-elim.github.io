Simulations worth watching, each running MuJoCo 3.14.0 in this page. Every number quoted comes from the Python script printed under its demo, which uses the same model and the same algorithm as the lab; the labs measure live, and their numbers match the scripts where both report the same quantity.

## 1. A planner in the page

A cart-pole hangs straight down. Nothing in its controller was learned and nothing describes a swing-up: every 40 ms the planner imagines a set of futures by simulating the cart-pole forward for one second under perturbed copies of its current plan, scores each with a running cost (pole upright, cart near the centre, little effort), and keeps the best. This is predictive sampling, a sampling-based model-predictive controller (Howell et al., arXiv:2212.00541). The faint lines are the pole tip in every imagined future; the orange line is the plan being executed. Shove the pole and watch the futures fan out.

```lab mpc
{"title": "A planner in the page", "height": 300}
```

The script runs the same planner on 20 starts per setting, each perturbed by 0.05 rad, and calls a run a success when the pole stays within 0.2 rad of upright for the last 2 of 10 seconds with the cart inside its rails.

| Samples per replan | 4 | 8 | 16 | 32 | 64 | 128 |
|---|---|---|---|---|---|---|
| success | 0/20 | 2/20 | 3/20 | 9/20 | 18/20 | 20/20 |
| planning time per replan | 0.90 ms | 0.87 ms | 1.17 ms | 1.70 ms | 2.76 ms | 5.11 ms |

| Horizon (64 samples) | 0.25 s | 0.5 s | 1 s | 2 s |
|---|---|---|---|---|
| success | 0/20 | 9/20 | 18/20 | 4/20 |

More samples help without exception, at a cost linear in their number. The horizon has a narrow sweet spot: a quarter second cannot see past the effort of a swing-up, and with the plan's four knots a 2 s horizon spaces them 0.67 s apart, too coarse to balance (inference). The planner also copes with a model it gets wrong. It always assumes a 0.2 kg pole, and balances a 0.3 kg pole in 20 of 20 starts and a 0.4 kg pole in 19 of 20, because it replans from the measured state every 40 ms. A shove of 3 rad/s to the balanced pole at t = 6 s is recovered by the end of the run in 13 of 20. Lesson 21.4 builds on this planner.

```python file=examples/showcase_predictive_sampling.py
"""Showcase: swinging up and balancing a cart-pole with predictive sampling, a sampling-based MPC
(Howell et al., arXiv:2212.00541).

INPUT   cartpole.xml from its hanging keyframe, the pole perturbed by 0.05 rad (normal); a force on the cart
        within +-20 N; the planner simulates the same model at a 10 ms timestep
PROCESS every 40 ms: a control spline with 4 knots over the horizon is perturbed by Gaussian noise at three
        scales (0.5, 2 and 8 N); every candidate, and the unperturbed one, is rolled out from the current state
        with mujoco.rollout; the cheapest is applied until the next replan. Running cost
        (1 - cos theta) + 0.1 x^2 + 0.01 xdot^2 + 0.001 thetadot^2 + 1e-4 u^2.
        Success: |theta| < 0.2 rad for the last 2 s of 10 s, with the cart inside the rails.
        (1) number of samples, 20 starts each; (2) horizon, 64 samples; (3) a pole heavier than the planner
        believes, and a shove of 3 rad/s to the balanced pole at t = 6 s
OUTPUT  printed tables

Run:  python examples/showcase_predictive_sampling.py          (about 3 minutes)
"""

import os
import time

import mujoco
import mujoco.rollout as rollout
import numpy as np

from mjcourse import model_path

FAST = os.environ.get("MJC_FAST") == "1"
FULL = mujoco.mjtState.mjSTATE_FULLPHYSICS
SCALES = np.array([0.5, 2.0, 8.0])
KNOTS, REPLAN, PLAN_DT, LIMIT = 4, 0.04, 0.01, 20.0


def cartpole(pole_mass: float = 0.2) -> mujoco.MjModel:
    spec = mujoco.MjSpec.from_file(str(model_path("cartpole")))
    spec.geom("pole").mass = pole_mass
    return spec.compile()


def cost(states: np.ndarray, ctrl: np.ndarray) -> np.ndarray:
    """Summed running cost per candidate; states are (N, T, 1 + nq + nv) with time first."""
    x, th, xd, thd = states[..., 1], states[..., 2], states[..., 3], states[..., 4]
    c = (1 - np.cos(th)) + 0.1 * x**2 + 0.01 * xd**2 + 0.001 * thd**2 + 1e-4 * ctrl[..., 0] ** 2
    return c.sum(axis=1)


def episode(seed: int, samples: int = 64, horizon: float = 1.0, real_pole: float = 0.2, shove: bool = False,
            seconds: float = 10.0) -> tuple[bool, float, float]:
    """(success, time when the pole first comes within 0.2 rad of upright, planning seconds per replan)."""
    rng = np.random.default_rng(seed)
    model = cartpole(real_pole)
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("hanging").id)
    data.qpos[1] += rng.normal(0.0, 0.05)
    mujoco.mj_forward(model, data)
    plan = cartpole()                                    # the planner's model: the nominal 0.2 kg pole
    plan.opt.timestep = PLAN_DT
    plan_datas = [mujoco.MjData(plan) for _ in range(8)]
    steps = round(horizon / PLAN_DT)
    knot_t, step_t = np.linspace(0.0, horizon, KNOTS), np.arange(steps) * PLAN_DT
    nominal, t_nominal = np.zeros(KNOTS), 0.0
    state = np.empty(mujoco.mj_stateSize(model, FULL))
    upright, planning, angles = None, 0.0, []
    replans = round(seconds / REPLAN)
    for k in range(replans):
        nominal = np.interp(knot_t + (data.time - t_nominal), knot_t, nominal)    # shift the plan forward
        t_nominal = data.time
        noise = SCALES[np.arange(samples - 1) % len(SCALES)][:, None] * rng.standard_normal((samples - 1, KNOTS))
        candidates = np.vstack([nominal, np.clip(nominal + noise, -LIMIT, LIMIT)])
        ctrl = np.stack([np.interp(step_t, knot_t, c) for c in candidates])[..., None]
        mujoco.mj_getState(model, data, state, FULL)
        t0 = time.perf_counter()
        states, _ = rollout.rollout(plan, plan_datas, np.tile(state, (samples, 1)), ctrl)
        planning += time.perf_counter() - t0
        nominal = candidates[int(np.argmin(cost(states, ctrl)))]
        if shove and k == round(6.0 / REPLAN):
            data.qvel[1] += 3.0
        for _ in range(round(REPLAN / model.opt.timestep)):
            data.ctrl[0] = np.interp(data.time - t_nominal, knot_t, nominal)
            mujoco.mj_step(model, data)
        angle = abs((data.qpos[1] + np.pi) % (2 * np.pi) - np.pi)
        angles.append(angle)
        if upright is None and angle < 0.2:
            upright = data.time
    last = np.array(angles[-round(2.0 / REPLAN):])
    success = bool((last < 0.2).all() and abs(data.qpos[0]) < 1.45)
    return success, upright if upright is not None else float("nan"), planning / replans


def summary(results) -> str:
    ok = np.array([r[0] for r in results])
    up = np.array([r[1] for r in results if r[0]])
    up_text = f"median {np.median(up):.2f} s" if len(up) else "-"
    return (f"success {ok.mean():.2f} ({ok.sum()}/{len(ok)}), swing-up {up_text}, "
            f"planning {1000 * np.mean([r[2] for r in results]):.2f} ms per replan")


if __name__ == "__main__":
    starts = range(4) if FAST else range(20)
    print(f"MuJoCo {mujoco.__version__}; replan every {1000 * REPLAN:.0f} ms, {KNOTS} knots, noise scales "
          f"{SCALES.tolist()} N, planner timestep {1000 * PLAN_DT:.0f} ms; {len(starts)} starts per row")
    print("(1) number of samples, horizon 1 s")
    for n in ((4, 64) if FAST else (4, 8, 16, 32, 64, 128)):
        print(f"    {n:>4} samples: " + summary([episode(s, samples=n) for s in starts]))
    print("(2) horizon, 64 samples")
    for horizon in ((0.5, 1.0) if FAST else (0.25, 0.5, 1.0, 2.0)):
        print(f"    {horizon:>4} s: " + summary([episode(s, horizon=horizon) for s in starts]))
    print("(3) 64 samples, horizon 1 s, the planner always assumes a 0.2 kg pole")
    for pole in (0.3, 0.4):
        print(f"    real pole {pole} kg: " + summary([episode(s, real_pole=pole) for s in starts]))
    print("    nominal pole, shoved by 3 rad/s at t = 6 s: " + summary([episode(s, shove=True) for s in starts]))
```
Output:

```text
MuJoCo 3.14.0; replan every 40 ms, 4 knots, noise scales [0.5, 2.0, 8.0] N, planner timestep 10 ms; 20 starts per row
(1) number of samples, horizon 1 s
       4 samples: success 0.00 (0/20), swing-up -, planning 0.90 ms per replan
       8 samples: success 0.10 (2/20), swing-up median 1.34 s, planning 0.87 ms per replan
      16 samples: success 0.15 (3/20), swing-up median 0.88 s, planning 1.17 ms per replan
      32 samples: success 0.45 (9/20), swing-up median 0.84 s, planning 1.70 ms per replan
      64 samples: success 0.90 (18/20), swing-up median 0.88 s, planning 2.76 ms per replan
     128 samples: success 1.00 (20/20), swing-up median 0.94 s, planning 5.11 ms per replan
(2) horizon, 64 samples
    0.25 s: success 0.00 (0/20), swing-up -, planning 1.16 ms per replan
     0.5 s: success 0.45 (9/20), swing-up median 0.64 s, planning 1.71 ms per replan
     1.0 s: success 0.90 (18/20), swing-up median 0.88 s, planning 2.76 ms per replan
     2.0 s: success 0.20 (4/20), swing-up median 0.84 s, planning 5.33 ms per replan
(3) 64 samples, horizon 1 s, the planner always assumes a 0.2 kg pole
    real pole 0.3 kg: success 1.00 (20/20), swing-up median 0.98 s, planning 2.70 ms per replan
    real pole 0.4 kg: success 0.95 (19/20), swing-up median 1.04 s, planning 2.76 ms per replan
    nominal pole, shoved by 3 rad/s at t = 6 s: success 0.65 (13/20), swing-up median 0.92 s, planning 2.77 ms per replan
```

## 2. Twins

Two double pendulums hang from one pivot, released from the same angles except for 10⁻⁹ rad in the blue one's first joint. For about six seconds they move as one; then they part, and nothing afterwards resembles the other. The plot shows the gap on a log scale and a dashed line for the growth predicted by the largest Lyapunov exponent. The gap follows that line until it saturates near 1 rad, about eight decades later.

```lab chaos
{"title": "Twins, 1e-9 rad apart", "height": 300}
```

The exponent, measured by renormalizing the gap between two copies every 0.1 s for 100 s, is 2.65 per second: a gap grows tenfold every 0.87 s. So each factor of 1000 in the initial gap buys only about 2.6 s of agreement:

| Initial gap | 10⁻³ rad | 10⁻⁶ rad | 10⁻⁹ rad | 10⁻¹² rad |
|---|---|---|---|---|
| gap passes 0.1 rad, measured | 1.63 s | 3.87 s | 6.29 s | 9.90 s |
| predicted, ln(0.1/ε)/λ | 1.74 s | 4.35 s | 6.96 s | 9.57 s |

The integrator is an initial-condition error of its own. Against RK4 at 0.25 ms, RK4 at 2 ms departs by 0.1 rad after 5.14 s, Euler at 2 ms after 1.01 s. Over 60 s, Euler removes 34% of the energy, and implicitfast gives exactly the same numbers, because it treats only velocity-dependent forces implicitly and this pendulum has none. RK4 conserves energy to the printed precision. No single trajectory of a chaotic system can be reproduced for long, but statistics can be. Over 300 s, three RK4 runs, at two timesteps and with a 10⁻⁹ rad offset, agree on the mean tip height (−0.088 to −0.098 m) and on how often the second link flips over (59 to 63 times a minute). The energy-losing integrators give −0.3965 m and 5 flips a minute: a different motion, not a noisier one. A simulation of a chaotic system is validated by its statistics, and only after its energy is right. The integrators are Lesson 1.3's subject.

```python file=examples/showcase_chaos.py
"""Showcase: chaos in a double pendulum, and what a simulation of a chaotic system can promise.

INPUT   double_pendulum.xml released from (2.0, 0.5) rad, no damping
PROCESS (1) the largest Lyapunov exponent by Benettin's method: two copies 1e-9 rad apart, the separation in
            (q, qdot) renormalized every 0.1 s for 100 s, RK4 at 1 ms;
        (2) twins: the second copy offset by eps = 1e-3 ... 1e-12 rad in the first joint; the time at which the
            joint angles first differ by 0.1 rad, against ln(0.1 / eps) / lambda;
        (3) the integrator: Euler, implicitfast and RK4 at 2 ms and RK4 at 1 ms, each against RK4 at 0.25 ms:
            when it departs by 0.1 rad, and its energy drift over 60 s;
        (4) statistics: the mean height of the tip and how often the second link flips over, over 300 s,
            for the same integrators and offsets
OUTPUT  printed tables

Run:  python examples/showcase_chaos.py          (about 2 minutes)
"""

import math
import os

import mujoco
import numpy as np

from mjcourse import model_path

FAST = os.environ.get("MJC_FAST") == "1"
INTEGRATORS = {"Euler": mujoco.mjtIntegrator.mjINT_EULER, "implicitfast": mujoco.mjtIntegrator.mjINT_IMPLICITFAST,
               "RK4": mujoco.mjtIntegrator.mjINT_RK4}


def pendulum(integrator: str = "RK4", dt: float = 0.001, offset: float = 0.0) -> tuple[mujoco.MjModel, mujoco.MjData]:
    model = mujoco.MjModel.from_xml_path(str(model_path("double_pendulum")))
    model.opt.integrator, model.opt.timestep = INTEGRATORS[integrator], dt
    model.opt.enableflags |= mujoco.mjtEnableBit.mjENBL_ENERGY
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("release").id)
    data.qpos[0] += offset
    mujoco.mj_forward(model, data)
    return model, data


def energy(data) -> float:
    return float(data.energy[0] + data.energy[1])


def angles_at(model, data, times: np.ndarray) -> np.ndarray:
    """Joint angles at the given times (s, increasing), stepping the simulation."""
    out = np.empty((len(times), 2))
    for i, t in enumerate(times):
        while data.time < t - 1e-12:
            mujoco.mj_step(model, data)
        out[i] = data.qpos
    return out


def lyapunov(seconds: float, d0: float = 1e-9, every: float = 0.1) -> float:
    m1, a = pendulum()
    m2, b = pendulum(offset=d0)
    total, n = 0.0, round(seconds / every)
    for _ in range(n):
        for _ in range(round(every / m1.opt.timestep)):
            mujoco.mj_step(m1, a)
            mujoco.mj_step(m2, b)
        delta = np.r_[b.qpos - a.qpos, b.qvel - a.qvel]
        d = float(np.linalg.norm(delta))
        total += math.log(d / d0)
        b.qpos[:] = a.qpos + delta[:2] * d0 / d                  # renormalize along the grown direction
        b.qvel[:] = a.qvel + delta[2:] * d0 / d
    return total / (n * every)


def departure(reference: np.ndarray, other: np.ndarray, times: np.ndarray, threshold: float = 0.1) -> float:
    gap = np.abs(np.angle(np.exp(1j * (other - reference)))).max(axis=1)
    hit = np.flatnonzero(gap > threshold)
    return float(times[hit[0]]) if len(hit) else float("nan")


def statistics(integrator: str, dt: float, offset: float, seconds: float) -> tuple[float, float, float]:
    """(mean tip height above the pivot in m, flips of link 2 per minute, relative energy change)."""
    model, data = pendulum(integrator, dt, offset)
    e0, tip, heights, flips = energy(data), model.site("tip").id, [], 0
    rel = (data.qpos[1] + math.pi) % (2 * math.pi)
    for _ in range(round(seconds / dt)):
        mujoco.mj_step(model, data)
        heights.append(data.site_xpos[tip][2] - 1.0)
        now = (data.qpos[1] + math.pi) % (2 * math.pi)
        if abs(now - rel) > math.pi:                            # the relative angle wrapped past upside-down
            flips += 1
        rel = now
    return float(np.mean(heights)), flips / (seconds / 60), (energy(data) - e0) / abs(e0)


if __name__ == "__main__":
    print(f"MuJoCo {mujoco.__version__}; double pendulum released from (2.0, 0.5) rad")
    lam = lyapunov(20.0 if FAST else 100.0)
    print(f"(1) largest Lyapunov exponent (RK4, 1 ms): {lam:.2f} per second; a gap grows tenfold every {math.log(10) / lam:.2f} s")
    print("(2) twins offset by eps in the first joint: time until the joint angles differ by 0.1 rad")
    times = np.arange(1, round(30.0 / 0.001) + 1) * 0.001
    ref = angles_at(*pendulum(), times)
    for eps in (1e-3, 1e-6, 1e-9, 1e-12):
        t = departure(ref, angles_at(*pendulum(offset=eps), times), times)
        print(f"    eps {eps:.0e}: measured {t:5.2f} s, predicted ln(0.1/eps)/lambda {math.log(0.1 / eps) / lam:5.2f} s")
    print("(3) integrators against RK4 at 0.25 ms: departure by 0.1 rad, and energy change over 60 s")
    fine = angles_at(*pendulum("RK4", 0.00025), times)
    for name, dt in (("Euler", 0.002), ("implicitfast", 0.002), ("RK4", 0.002), ("RK4", 0.001)):
        t = departure(fine, angles_at(*pendulum(name, dt), times), times)
        model, data = pendulum(name, dt)
        e0 = energy(data)
        for _ in range(round(60.0 / dt)):
            mujoco.mj_step(model, data)
        print(f"    {name:<13} {1000 * dt:.0f} ms: departs at {t:5.2f} s; energy change after 60 s {100 * (energy(data) - e0) / abs(e0):+8.3f} %")
    seconds = 60.0 if FAST else 300.0
    print(f"(4) statistics over {seconds:.0f} s: mean tip height below the pivot, flips of the second link per minute")
    for name, dt, eps in (("RK4", 0.001, 0.0), ("RK4", 0.001, 1e-9), ("RK4", 0.002, 0.0), ("implicitfast", 0.002, 0.0), ("Euler", 0.002, 0.0)):
        mean_h, flips, de = statistics(name, dt, eps, seconds)
        print(f"    {name:<13} {1000 * dt:.0f} ms, eps {eps:.0e}: mean tip height {mean_h:+.4f} m, {flips:5.1f} flips per minute, "
              f"energy change {100 * de:+.3f} %")
```
Output:

```text
MuJoCo 3.14.0; double pendulum released from (2.0, 0.5) rad
(1) largest Lyapunov exponent (RK4, 1 ms): 2.65 per second; a gap grows tenfold every 0.87 s
(2) twins offset by eps in the first joint: time until the joint angles differ by 0.1 rad
    eps 1e-03: measured  1.63 s, predicted ln(0.1/eps)/lambda  1.74 s
    eps 1e-06: measured  3.87 s, predicted ln(0.1/eps)/lambda  4.35 s
    eps 1e-09: measured  6.29 s, predicted ln(0.1/eps)/lambda  6.96 s
    eps 1e-12: measured  9.90 s, predicted ln(0.1/eps)/lambda  9.57 s
(3) integrators against RK4 at 0.25 ms: departure by 0.1 rad, and energy change over 60 s
    Euler         2 ms: departs at  1.01 s; energy change after 60 s  -34.004 %
    implicitfast  2 ms: departs at  1.01 s; energy change after 60 s  -34.004 %
    RK4           2 ms: departs at  5.14 s; energy change after 60 s   -0.000 %
    RK4           1 ms: departs at  6.27 s; energy change after 60 s   -0.000 %
(4) statistics over 300 s: mean tip height below the pivot, flips of the second link per minute
    RK4           1 ms, eps 0e+00: mean tip height -0.0875 m,  59.0 flips per minute, energy change -0.000 %
    RK4           1 ms, eps 1e-09: mean tip height -0.0977 m,  63.4 flips per minute, energy change -0.000 %
    RK4           2 ms, eps 0e+00: mean tip height -0.0900 m,  59.4 flips per minute, energy change -0.001 %
    implicitfast  2 ms, eps 0e+00: mean tip height -0.3965 m,   5.0 flips per minute, energy change -40.588 %
    Euler         2 ms, eps 0e+00: mean tip height -0.3965 m,   5.0 flips per minute, energy change -40.588 %
```
