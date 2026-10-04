"""Lesson 19.1: what latency, actuator mismatch and sensing do to a controller tuned in simulation (Level 19).

INPUT   pendulum.xml held at 0.05 rad by the Level 8 controller: PD on the angle with gravity
        compensation, u = kp (q* - q) - kd qdot + m g L sin q; MuJoCo's actuator delay (a 200-sample
        history, linear interpolation), first-order actuator dynamics and gear model the hardware
PROCESS (1) the delay margin, the extra actuator delay at which the loop starts to oscillate with growing
            amplitude, predicted from the loop's phase margin and crossover, then found by bisection in
            simulation, for four sets of gains; first with the plant I s^2, then with the gravity term
            that also passes through the delay;
        (2) actuator mismatch: a 20 ms motor lag, 80% of the modelled torque, and a 100 Hz controller;
        (3) sensing: a 4096-count encoder, velocity by differencing, and a low-pass filter on it:
            torque chatter against delay margin;
        (4) a transfer experiment on a "real" pendulum whose delay, motor lag, torque gain and mass are
            hidden: the stiff controller tuned in simulation, then software delay added until the loop
            oscillates, at two sets of gains, to measure the hidden phase loss and redesign
OUTPUT  printed tables

Run:  python examples/l19_1_sim_to_real.py          (about 2 minutes on 24 cores)
"""

import cmath
import math
import os
from multiprocessing import Pool

import mujoco
import numpy as np

from mjcourse import model_path

FAST = os.environ.get("MJC_FAST") == "1"
H, I_PIVOT, MGL, TARGET = 0.002, 0.2501, 1.0 * 9.81 * 0.5, 0.05
NOMINAL = {"delay": 0.0, "lag": 0.0, "gain": 1.0, "mass": 1.0}
HIDDEN = {"delay": 0.025, "lag": 0.008, "gain": 0.9, "mass": 1.1}        # the "real" pendulum
COUNTS = 4096                                                            # encoder resolution per turn


def pendulum(plant: dict, extra_delay: float = 0.0) -> mujoco.MjModel:
    """The pendulum with the plant's delay (+ extra), first-order motor lag, torque gain and mass."""
    spec = mujoco.MjSpec.from_file(str(model_path("pendulum")))
    spec.body("pole").mass = plant["mass"]
    act = spec.actuator("torque")
    act.nsample, act.interp, act.delay = 200, 1, plant["delay"] + extra_delay    # 200 samples hold 400 ms
    act.ctrlrange = [-100.0, 100.0]                                              # stay linear: no saturation
    act.gear = [plant["gain"], 0, 0, 0, 0, 0]
    if plant["lag"]:
        act.dyntype = mujoco.mjtDyn.mjDYN_FILTER
        act.dynprm = [plant["lag"]] + [0.0] * 9
    return spec.compile()


def run(job) -> np.ndarray:
    """Hold TARGET for `seconds`; returns the angle error per step, inf from the step where the loop left the
    linear range or MuJoCo reset a diverged state. job = (kp, kd, plant, extra delay, sensing, seconds) with
    sensing = None (true qvel) or (period in steps, filter cutoff in Hz or 0, quantize: bool)."""
    kp, kd, plant, extra, sensing, seconds = job
    model = pendulum(plant, extra)
    data = mujoco.MjData(model)
    period, cutoff, quantize = sensing or (1, 0.0, False)
    alpha = 1.0 if not cutoff else 1.0 - math.exp(-2 * math.pi * cutoff * H)      # first-order low-pass
    n = round(seconds / H)
    err, ctrl = np.empty(n), np.empty(n)
    q_prev, v, u = 0.0, 0.0, 0.0
    for k in range(n):
        q = data.qpos[0]
        if quantize:
            q = round(q * COUNTS / (2 * math.pi)) * 2 * math.pi / COUNTS
            v += alpha * ((q - q_prev) / H - v)
            q_prev = q
        else:
            v = data.qvel[0]
        if k % period == 0:
            u = kp * (TARGET - q) - kd * v + MGL * math.sin(q)                  # compensation for the nominal mass
        data.ctrl[0] = u
        mujoco.mj_step(model, data)
        err[k], ctrl[k] = TARGET - data.qpos[0], u
        if abs(err[k]) > 0.5 or data.time < (k + 1) * H - 1e-9:
            err[k:] = np.inf
            break
    return np.vstack([err, ctrl])


def growing(err: np.ndarray) -> bool:
    """The loop does not settle: it diverged, the spread of its error about the mean over the last quarter
    exceeds the third quarter's by 10%, or it sustains an oscillation above 5 mrad RMS (past the margin the
    pendulum can settle into a limit cycle instead of growing; an encoder alone keeps it moving by about a
    count; a static offset, such as a mass error leaves, is not an oscillation)."""
    n = len(err)
    if np.isinf(err).any():
        return True
    spread = [float(np.std(err[i * n // 4:(i + 1) * n // 4])) for i in range(4)]
    return spread[3] > 1.1 * spread[2] or (spread[3] > 0.005 and spread[3] > 0.5 * spread[1])


def measure_margin(job) -> tuple[float, float]:
    """Smallest extra delay at which the oscillation grows (bisection, 0.1 ms), and its frequency (rad/s)."""
    kp, kd, plant, sensing = job
    seconds = 8.0 if FAST else 20.0
    lo, hi = 0.0, 0.38
    if growing(run((kp, kd, plant, 0.0, sensing, seconds))[0]):
        return 0.0, float("nan")
    while hi - lo > 1e-4:
        mid = 0.5 * (lo + hi)
        lo, hi = (lo, mid) if growing(run((kp, kd, plant, mid, sensing, seconds))[0]) else (mid, hi)
    err = run((kp, kd, plant, lo, sensing, seconds))[0]
    tail = err[len(err) // 2:]
    crossings = np.flatnonzero(np.diff(np.sign(tail - tail.mean())) != 0)
    return hi, math.pi / (np.mean(np.diff(crossings)) * H) if len(crossings) > 2 else float("nan")


def loop_response(kp, kd, w, plant=NOMINAL, sensing=None, gravity=True) -> complex:
    """The linearized loop at frequency w (rad/s). With gravity, the plant is I s^2 + m g L and the compensation
    passes through the actuator: g A(s) e^(-s d) (C(s) - m g L) / (I s^2 + m g L); without, C(s) e^(-s d) / (I s^2).
    A zero-order hold over the control period T contributes e^(-s T/2)."""
    period, cutoff, quantize = sensing or (1, 0.0, False)
    inertia = 0.25 * plant["mass"] + 1e-4                     # m L^2 + I_c
    s = 1j * w
    if quantize:                                              # differenced, filtered velocity
        deriv = (1 - cmath.exp(-s * H)) / H
        if cutoff:
            a = 1.0 - math.exp(-2 * math.pi * cutoff * H)
            deriv *= a / (1 - (1 - a) * cmath.exp(-s * H))
    else:
        deriv = s
    c = kp + kd * deriv
    act = plant["gain"] / (1 + s * plant["lag"]) * cmath.exp(-s * (plant["delay"] + period * H / 2))
    if gravity:
        return act * (c - MGL) / (inertia * s * s + MGL * plant["mass"])
    return act * c / (inertia * s * s)


def predict_margin(kp, kd, plant=NOMINAL, sensing=None, gravity=True) -> tuple[float, float]:
    """Delay margin = phase margin / crossover frequency, from loop_response."""
    lo, hi = 0.5, 2000.0
    for _ in range(200):                                      # |loop| falls through 1 once
        mid = math.sqrt(lo * hi)
        lo, hi = (mid, hi) if abs(loop_response(kp, kd, mid, plant, sensing, gravity)) > 1 else (lo, mid)
    w = lo
    phase_margin = math.pi + cmath.phase(loop_response(kp, kd, w, plant, sensing, gravity))
    phase_margin = (phase_margin + math.pi) % (2 * math.pi) - math.pi
    return phase_margin / w, w


def gains(kp: float, zeta: float, inertia: float = I_PIVOT) -> tuple[float, float]:
    return kp, 2 * zeta * math.sqrt(kp * inertia)


if __name__ == "__main__":
    print(f"MuJoCo {mujoco.__version__}; pendulum I = {I_PIVOT} kg m^2, m g L = {MGL:.3f} N m, timestep {1000 * H:.0f} ms, "
          f"holding {TARGET} rad")
    with Pool(24) as pool:
        print("(1) delay margin: predicted from the loop, measured by bisection in simulation")
        print(f"    {'kp':>5} {'zeta':>5} {'kd':>6}   {'predicted, plant I s^2':>24}   {'with gravity in the loop':>26}   "
              f"{'measured':>8}   {'frequency at the margin (rad/s)':>32}")
        cases = [(20, 1.0), (20, 0.5), (80, 0.7), (200, 0.7)]
        jobs = [(*gains(kp, z), NOMINAL, None) for kp, z in cases]
        for (kp, z), job, (m, f) in zip(cases, jobs, pool.map(measure_margin, jobs)):
            p0, w0 = predict_margin(job[0], job[1], gravity=False)
            p1, w1 = predict_margin(job[0], job[1])
            print(f"    {kp:>5} {z:>5} {job[1]:>6.3f}   {1000 * p0:>13.1f} ms at {w0:>5.2f}   {1000 * p1:>15.1f} ms at {w1:>5.2f}   "
                  f"{1000 * m:>5.1f} ms   {f:>32.2f}")

        print("(2) actuator and controller mismatch, kp 80, zeta 0.7 (margin without them in (1))")
        kp, kd = gains(80, 0.7)
        variants = [("motor with a 20 ms first-order lag", {**NOMINAL, "lag": 0.02}, None),
                    ("motor giving 80% of the modelled torque", {**NOMINAL, "gain": 0.8}, None),
                    ("controller at 100 Hz (every 5 steps), held", NOMINAL, (5, 0.0, False))]
        results = pool.map(measure_margin, [(kp, kd, plant, sensing) for _, plant, sensing in variants])
        for (label, plant, sensing), (m, f) in zip(variants, results):
            p, w = predict_margin(kp, kd, plant, sensing)
            print(f"    {label:<44} predicted {1000 * p:5.1f} ms, measured {1000 * m:5.1f} ms (oscillating at {f:.2f} rad/s)")
        hold = run((kp, kd, {**NOMINAL, "gain": 0.8}, 0.0, None, 6.0))[0]
        print(f"    80% torque also leaves a static error: {1000 * hold[-1]:.2f} mrad at {TARGET} rad, predicted "
              f"{1000 * 0.2 * MGL * math.sin(TARGET) / (0.8 * kp + 0.2 * MGL * math.cos(TARGET)):.2f} mrad")

        print(f"(3) sensing: {COUNTS}-count encoder ({1000 * 2 * math.pi / COUNTS:.3f} mrad), velocity by differencing "
              "at 500 Hz, kp 80, zeta 0.7")
        sens = [("true angle and velocity", None), ("encoder, unfiltered velocity", (1, 0.0, True)),
                ("encoder, velocity filtered at 100 Hz", (1, 100.0, True)), ("encoder, velocity filtered at 30 Hz", (1, 30.0, True)),
                ("encoder, velocity filtered at 10 Hz", (1, 10.0, True))]
        holds = pool.map(run, [(kp, kd, NOMINAL, 0.0, s, 4.0) for _, s in sens])
        margins = pool.map(measure_margin, [(kp, kd, NOMINAL, s) for _, s in sens])
        for (label, s), hold, (m, _) in zip(sens, holds, margins):
            u = hold[1][len(hold[1]) // 2:]
            p, _ = predict_margin(kp, kd, NOMINAL, s)
            print(f"    {label:<38} torque chatter (std) {u.std():6.3f} N m, peak-to-peak {np.ptp(u):6.3f} N m; "
                  f"delay margin predicted {1000 * p:5.1f} ms, measured {1000 * m:5.1f} ms")

        print("(4) a transfer experiment; hidden: delay, motor lag, torque gain and mass of the real pendulum")
        stiff = gains(200, 0.7)
        p_sim, _ = predict_margin(*stiff)
        real_stiff = run((*stiff, HIDDEN, 0.0, (1, 30.0, True), 6.0))[0]
        print(f"    deploy kp 200, zeta 0.7 (simulated margin {1000 * p_sim:.1f} ms): "
              + ("the real loop does not settle" if growing(real_stiff) else "the real loop settles"))
        probes = [gains(10, 1.0), gains(40, 1.0)]
        sensing = (1, 30.0, True)
        points = []
        for g, (m, f) in zip(probes, pool.map(measure_margin, [(*g, HIDDEN, sensing) for g in probes])):
            p, w = predict_margin(*g, NOMINAL, sensing)
            # at the margin the real loop has gain 1 and phase -180 deg at f: one point of the hidden factor G(jf)
            nominal = loop_response(*g, f, NOMINAL, sensing) * cmath.exp(-1j * f * m)
            factor = -1 / nominal
            points.append((f, abs(factor), cmath.phase(factor)))
            print(f"    probe kp {g[0]:.0f}, zeta 1: model margin {1000 * p:5.1f} ms at {w:.2f} rad/s; real margin {1000 * m:5.1f} ms, "
                  f"oscillating at {f:.2f} rad/s -> hidden factor there: gain {abs(factor):.3f}, phase {math.degrees(cmath.phase(factor)):.1f} deg")
        # G(jw) = k e^(-jwd) / (1 + jw tau): the two gains give tau and k, the phases then give d
        (w1, g1, ph1), (w2, g2, ph2) = points
        ratio = (g1 / g2) ** 2                                                  # = (1 + w2^2 tau^2) / (1 + w1^2 tau^2)
        tau = math.sqrt(max((ratio - 1) / (w2 ** 2 - ratio * w1 ** 2), 0.0))
        k = g1 * math.sqrt(1 + (w1 * tau) ** 2)
        d = float(np.mean([(-ph - math.atan(w * tau)) / w for w, ph in ((w1, ph1), (w2, ph2))]))
        print(f"    fitted: torque gain {k:.3f}, motor lag {1000 * tau:.1f} ms, delay {1000 * d:.1f} ms "
              f"(hidden: gain {HIDDEN['gain']} with mass {HIDDEN['mass']} kg, lag {1000 * HIDDEN['lag']:.0f} ms, delay {1000 * HIDDEN['delay']:.0f} ms)")
        model_fit = {**NOMINAL, "delay": d, "lag": tau, "gain": k}
        for kp_try in (200, 120, 80, 40, 20):
            g = gains(kp_try, 0.7)
            p, _ = predict_margin(*g, model_fit, sensing)
            if p >= 0.02:
                break
        real_margin, _ = measure_margin((*g, HIDDEN, sensing))
        print(f"    stiffest kp keeping a 20 ms margin under the identified delay and lag: {kp_try} "
              f"(predicted margin {1000 * p:.1f} ms); on the real: margin {1000 * real_margin:.1f} ms")
