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
