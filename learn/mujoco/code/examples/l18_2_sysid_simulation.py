"""Lesson 18.2: identification by simulation, with MuJoCo's sysid toolbox (Level 18).

INPUT   pendulum.xml with hidden mass 1.3 kg, damping 0.08 N m s/rad and friction loss 0.05 N m, driven
        and measured as in Lesson 18.1 (multisine up to 2.5 N m, 10 s, 0.5 mrad angle noise);
        the same pendulum with a 10 ms actuator delay that the model does not have;
        a ball dropped on a floor with hidden contact softness solref = (0.015 s, 0.25)
PROCESS (1) mujoco.sysid simulates the record and minimizes the angle error over (mass, damping,
            friction loss): with each sample stamped at the time it was measured, then stamped the way
            mujoco.rollout stamps its sensors; next to the 18.1 regression on the same record;
        (2) the delayed pendulum, fitted without a delay and with the delay as a fourth parameter
            (lower bound 0, then one timestep); how MuJoCo applies a delay shorter than one step;
            validation on a held-out excitation;
        (3) contact: the height error over 1.2 s of bounces along each solref parameter, fits from
            five starting points, a 40 x 40 grid; then a fit of the bounce apex heights alone, with
            the time constant fixed; validation on a drop from 0.3 m
OUTPUT  printed tables

Run:  python examples/l18_2_sysid_simulation.py          (about 2 minutes)
"""
# requires: sysid

import contextlib
import io
import os
import re

import mujoco
import numpy as np
from mujoco import sysid
from scipy.optimize import minimize_scalar
from scipy.signal import find_peaks, savgol_filter

from mjcourse import model_path

FAST = os.environ.get("MJC_FAST") == "1"
TRUE = {"mass": 1.3, "damping": 0.08, "frictionloss": 0.05}
GUESS = {"mass": 1.0, "damping": 0.0, "frictionloss": 0.0}
L, I_C, G, NOISE, H = 0.5, 1e-4, 9.81, 0.0005, 0.002


def pendulum_spec(p: dict, delay: float | None = None) -> mujoco.MjSpec:
    """pendulum.xml with parameters p; with `delay`, the actuator keeps a 20-sample history (linear)."""
    spec = mujoco.MjSpec.from_file(str(model_path("pendulum")))
    spec.body("pole").mass = p["mass"]
    spec.joint("hinge").damping = [p["damping"], 0.0, 0.0]       # polynomial damping: linear term first
    spec.joint("hinge").frictionloss = p["frictionloss"]
    if delay is not None:
        act = spec.actuator("torque")
        act.nsample, act.interp, act.delay = 20, 1, delay
    return spec


def multisine(t: np.ndarray, amplitude: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    freqs, phases = rng.uniform(0.2, 3.0, 5), rng.uniform(0, 2 * np.pi, 5)
    return amplitude * sum(np.sin(2 * np.pi * f * t + p) for f, p in zip(freqs, phases)) / 5


def simulate(spec: mujoco.MjSpec, torque: np.ndarray) -> np.ndarray:
    """Angle at t = k h, measured before step k applies torque[k] (as in Lesson 18.1)."""
    model = spec.compile()
    data = mujoco.MjData(model)
    q = np.empty(len(torque))
    for k, tau in enumerate(torque):
        q[k] = data.qpos[0]
        data.ctrl[0] = tau
        mujoco.mj_step(model, data)
    return q


def setter(path: str):
    """Modifier writing a scalar parameter into the spec (sysid calls it before each compile)."""
    def apply(spec, p):
        v = float(p.value[0])
        if path == "mass":
            spec.body("pole").mass = v
        elif path == "damping":
            spec.joint("hinge").damping = [v, 0.0, 0.0]
        elif path == "frictionloss":
            spec.joint("hinge").frictionloss = v
        else:
            spec.actuator("torque").delay = v
    return apply


def run_optimize(params, residual_fn) -> tuple[sysid.ParameterDict, object, int]:
    """sysid.optimize, with the backend's per-iteration log captured; returns the residual evaluations."""
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        opt, result = sysid.optimize(initial_params=params, residual_fn=residual_fn, optimizer="mujoco", verbose=False)
    found = re.search(r"Residual evals: (\d+)", log.getvalue())
    return opt, result, int(found.group(1)) if found else -1


def fit_pendulum(t, torque, q, stamp_shift: float, delay_bounds=None) -> tuple[dict, np.ndarray, int]:
    """Fit (mass, damping, friction loss[, delay]) to a measured angle; returns estimate, 95% half-widths, evals."""
    spec = pendulum_spec(GUESS, None if delay_bounds is None else 0.0)
    model = spec.compile()
    data = mujoco.MjData(model)
    x0 = sysid.create_initial_state(model, data.qpos, data.qvel, data.act)
    sequences = sysid.ModelSequences(
        "pendulum", spec, "record", x0, sysid.TimeSeries(t, torque[:, None]),
        sysid.TimeSeries.from_names(t + stamp_shift, q[:, None], model, names=["angle"]),
        allow_missing_sensors=True)                                     # the angular-velocity sensor is not measured
    params = sysid.ParameterDict()
    params.add(sysid.Parameter("mass", 1.0, 0.2, 5.0, modifier=setter("mass")))
    params.add(sysid.Parameter("damping", 0.01, 0.0, 1.0, modifier=setter("damping")))
    params.add(sysid.Parameter("frictionloss", 0.01, 0.0, 0.5, modifier=setter("frictionloss")))
    if delay_bounds is not None:
        params.add(sysid.Parameter("delay", 0.005, delay_bounds[0], delay_bounds[1], modifier=setter("delay")))
    residual_fn = sysid.build_residual_fn(models_sequences=[sequences])
    opt, result, evals = run_optimize(params, residual_fn)
    residuals, _, _ = residual_fn(result.x, opt)
    _, half_widths = sysid.calculate_intervals(residuals, result.jac)
    return {k: float(opt[k].value[0]) for k in opt.keys()}, half_widths, evals


def regression_sg(q, torque) -> np.ndarray:
    """The Lesson 18.1 estimate: Savitzky-Golay derivatives and least squares on the inverse dynamics."""
    qf, qd, qdd = (savgol_filter(q, 51, 3, deriv=k, delta=H) for k in range(3))
    sl = slice(30, len(q) - 30)
    x = np.c_[L * L * qdd + G * L * np.sin(qf), qd, np.sign(qd)][sl]
    return np.linalg.lstsq(x, (torque - I_C * qdd)[sl], rcond=None)[0]


def row(label: str, est: dict, hw=None) -> str:
    cells = [f"{est[k]:.5f}" + (f" +- {w:.5f}" if hw is not None else "") for k, w in
             zip(est, hw if hw is not None else [None] * len(est))]
    return f"  {label:<46}" + "".join(f"{c:>21}" for c in cells)


def rms_mrad(a, b) -> float:
    return 1000 * float(np.sqrt(np.mean((a - b) ** 2)))


BALL = """
<mujoco model="bounce">
  <option timestep="0.002"/>
  <worldbody>
    <geom name="floor" type="plane" size="1 1 0.05"/>
    <body name="ball" pos="0 0 0.5">
      <joint name="z" type="slide" axis="0 0 1"/>
      <geom name="ball" type="sphere" size="0.03" mass="0.1"/>
    </body>
  </worldbody>
  <sensor><jointpos name="height" joint="z"/></sensor>
</mujoco>"""
BALL_TRUE = (0.015, 0.25)


def ball_spec(tc: float, dr: float, z0: float = 0.5) -> mujoco.MjSpec:
    spec = mujoco.MjSpec.from_string(BALL)
    for g in ("floor", "ball"):
        spec.geom(g).solref = [tc, dr]
    spec.body("ball").pos = [0, 0, z0]
    return spec


def drop(tc: float, dr: float, z0: float = 0.5, seconds: float = 1.2) -> np.ndarray:
    """Height of the ball's centre (m) at t = k h, before step k."""
    model = ball_spec(tc, dr, z0).compile()
    data = mujoco.MjData(model)
    z = np.empty(round(seconds / H))
    for k in range(len(z)):
        z[k] = z0 + data.qpos[0]
        mujoco.mj_step(model, data)
    return z


def apexes(z: np.ndarray, count: int) -> np.ndarray:
    """Heights of the first `count` bounce apexes of a smoothed height record (fewer if it stops bouncing)."""
    smooth = savgol_filter(z, 15, 2)
    peaks, _ = find_peaks(smooth, prominence=0.005)
    return smooth[peaks[:count]]


def ball_fit(start, z_meas, t) -> tuple[float, float]:
    """sysid fit of (time constant, damping ratio) to the raw height record from a starting point."""
    spec = ball_spec(*start)
    model = spec.compile()
    data = mujoco.MjData(model)
    x0 = sysid.create_initial_state(model, data.qpos, data.qvel, data.act)
    sequences = sysid.ModelSequences(
        "ball", spec, "drop", x0, sysid.TimeSeries(t, np.zeros((len(t), 0))),
        sysid.TimeSeries.from_names(t + H, (z_meas - 0.5)[:, None], model, names=["height"]))

    def solref(i):
        def apply(s, p):
            for g in ("floor", "ball"):
                ref = list(s.geom(g).solref)
                ref[i] = float(p.value[0])
                s.geom(g).solref = ref
        return apply
    params = sysid.ParameterDict()
    params.add(sysid.Parameter("timeconst", start[0], 0.004, 0.1, modifier=solref(0)))   # MuJoCo clamps below 2 h
    params.add(sysid.Parameter("dampratio", start[1], 0.01, 2.0, modifier=solref(1)))
    opt, _, _ = run_optimize(params, sysid.build_residual_fn(models_sequences=[sequences]))
    return float(opt["timeconst"].value[0]), float(opt["dampratio"].value[0])


if __name__ == "__main__":
    t = np.arange(5000) * H
    torque = multisine(t, 2.5, seed=1)
    q = simulate(pendulum_spec(TRUE), torque) + np.random.default_rng(0).normal(0.0, NOISE, len(t))
    held_torque = multisine(t, 2.5, seed=7)
    q_held = simulate(pendulum_spec(TRUE), held_torque) + np.random.default_rng(2).normal(0.0, NOISE, len(t))
    print(f"MuJoCo {mujoco.__version__}; pendulum record of 10 s at {1000 * H:.0f} ms, angle noise {1000 * NOISE} mrad")
    print(f"  {'':<46}" + "".join(f"{k:>21}" for k in ("mass (kg)", "damping", "friction loss (N m)")))
    print(row("truth", TRUE))
    model = pendulum_spec(TRUE).compile()
    data = mujoco.MjData(model)
    data.ctrl[0] = 1.0
    for _ in range(2):
        mujoco.mj_step(model, data)
    stepped = data.sensordata[0]
    mujoco.mj_forward(model, data)
    print(f"  after two steps: time {data.time:.3f} s, qpos {data.qpos[0]:.3e}, angle sensor {stepped:.3e} "
          f"(after mj_forward: {data.sensordata[0]:.3e})")
    print("(1) simulation error minimized by mujoco.sysid, starting from 1.0, 0.01, 0.01")
    for label, shift in (("samples stamped at their measurement time", 0.0), ("samples stamped one step later, as rollout", H)):
        est, hw, evals = fit_pendulum(t, torque, q, shift)
        print(row(label, est, hw) + f"   ({evals} simulations)")
        if shift:
            best = est
    print(row("Lesson 18.1 regression (Savitzky-Golay)", dict(zip(TRUE, regression_sg(q, torque)))))
    print("  held-out excitation, angle RMS error: sysid estimate "
          f"{rms_mrad(simulate(pendulum_spec(best), held_torque), q_held):.2f} mrad, truth "
          f"{rms_mrad(simulate(pendulum_spec(TRUE), held_torque), q_held):.2f} mrad (the noise floor)")

    print("(2) the measured pendulum has a 10 ms actuator delay")
    for interp, name in ((1, "linear interpolation"), (0, "the last sample held")):
        lags = []
        for delay in (0.0, 0.001, 0.002, 0.003, 0.004):
            spec = pendulum_spec(TRUE, delay)
            spec.actuator("torque").interp = interp
            model = spec.compile()
            data = mujoco.MjData(model)
            for k in range(3):
                data.ctrl[0] = k + 1.0                                     # a ramp: the command at step k is k + 1
                mujoco.mj_step(model, data)
            lags.append(f"{1000 * delay:.0f} ms -> {3.0 - data.actuator_force[0]:.1f}")
        print(f"  delay with {name}, steps by which the force lags a ramp: " + ", ".join(lags))
    q_delay = simulate(pendulum_spec(TRUE, 0.010), torque) + np.random.default_rng(0).normal(0.0, NOISE, len(t))
    q_delay_held = simulate(pendulum_spec(TRUE, 0.010), held_torque) + np.random.default_rng(2).normal(0.0, NOISE, len(t))
    print(f"  {'':<46}" + "".join(f"{k:>21}" for k in ("mass (kg)", "damping", "friction loss (N m)", "delay (s)")))
    fits = {"model without a delay": fit_pendulum(t, torque, q_delay, H),
            "delay as a parameter, bounds 0 to 30 ms": fit_pendulum(t, torque, q_delay, H, (0.0, 0.03)),
            "delay as a parameter, bounds 2 to 30 ms": fit_pendulum(t, torque, q_delay, H, (H, 0.03))}
    for label, (est, hw, evals) in fits.items():
        print(row(label, est, hw) + f"   ({evals} simulations)")
    for label, (est, _, _) in fits.items():
        spec = pendulum_spec(est, est.get("delay"))
        print(f"  held-out excitation, {label:<40} angle RMS error {rms_mrad(simulate(spec, held_torque), q_delay_held):7.2f} mrad")

    print("(3) contact: a ball dropped from 0.5 m, height measured with 0.5 mm noise for 1.2 s; truth solref (0.015, 0.25)")
    z_meas = drop(*BALL_TRUE) + np.random.default_rng(0).normal(0.0, 0.0005, 600)
    t_ball = np.arange(600) * H
    rms_mm = lambda tc, dr: 1000 * float(np.sqrt(np.mean((drop(tc, dr) - z_meas) ** 2)))
    print("  highest point (mm) after the drop from 500 mm, damping ratio 0.25, time constant 1, 4, 5, 6, 8, 10, 15 ms: "
          + " ".join(f"{1000 * drop(tc, 0.25).max():.0f}" for tc in (0.001, 0.004, 0.005, 0.006, 0.008, 0.010, 0.015)))
    tcs, drs = np.linspace(0.010, 0.020, 11), np.linspace(0.20, 0.30, 11)
    print("  height RMS error (mm) along the time constant 0.010-0.020 s at the true damping ratio: "
          + " ".join(f"{rms_mm(a, 0.25):.1f}" for a in tcs))
    print("  height RMS error (mm) along the damping ratio 0.20-0.30 at the true time constant:   "
          + " ".join(f"{rms_mm(0.015, b):.1f}" for b in drs))
    starts = [(0.02, 1.0), (0.02, 0.5)] if FAST else [(0.02, 1.0), (0.02, 0.5), (0.02, 0.1), (0.005, 0.25), (0.04, 0.05)]
    results = []
    for start in starts:
        tc, dr = ball_fit(start, z_meas, t_ball)
        results.append((rms_mm(tc, dr), tc, dr))
        print(f"  sysid fit from {start}: time constant {tc:.4f} s, damping ratio {dr:.4f}, height RMS error "
              f"{results[-1][0]:.2f} mm, highest point {1000 * drop(tc, dr).max():.0f} mm")
    n = 10 if FAST else 40
    grid = [(rms_mm(a, b), a, b) for a in np.geomspace(0.004, 0.1, n) for b in np.geomspace(0.02, 2.0, n)]
    g_best = min(grid)
    print(f"  best of a {n} x {n} log grid: time constant {g_best[1]:.4f} s, damping ratio {g_best[2]:.4f}, "
          f"height RMS error {g_best[0]:.2f} mm; at the truth {rms_mm(*BALL_TRUE):.2f} mm")
    a_meas = apexes(z_meas, 2)
    print(f"  bounce apex heights measured: {', '.join(f'{1000 * a:.1f}' for a in a_meas)} mm")
    z_held = drop(*BALL_TRUE, z0=0.3) + np.random.default_rng(1).normal(0.0, 0.0005, 600)
    candidates = {"best raw-trajectory fit": min(results + [g_best])[1:]}
    for tc in (0.01, 0.02, 0.03):
        def cost(dr, tc=tc):
            a = apexes(drop(tc, dr), 2)
            return float(np.sum((a - a_meas) ** 2)) if len(a) == 2 else 1.0     # no second bounce: far off
        scan = np.geomspace(0.02, 1.5, 60)
        i = int(np.argmin([cost(d) for d in scan]))
        dr = minimize_scalar(cost, bounds=(scan[max(i - 1, 0)], scan[min(i + 1, 59)]), method="bounded",
                             options={"xatol": 1e-5}).x
        candidates[f"apex fit, time constant fixed at {tc}"] = (tc, float(dr))
    print("  held-out drop from 0.3 m (apex heights measured: "
          + ", ".join(f"{1000 * a:.1f}" for a in apexes(z_held, 2)) + " mm):")
    for label, (tc, dr) in candidates.items():
        z = drop(tc, dr, z0=0.3)
        print(f"    {label:<40} ({tc:.4f}, {dr:.4f}): apexes "
              + ", ".join(f"{1000 * a:.1f}" for a in apexes(z, 2)) + f" mm, height RMS error {1000 * np.sqrt(np.mean((z - z_held) ** 2)):.2f} mm")
