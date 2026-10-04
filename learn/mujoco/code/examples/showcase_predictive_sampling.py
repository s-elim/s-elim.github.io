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
