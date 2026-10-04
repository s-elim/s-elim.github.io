"""Lesson 18.1: identifying a pendulum's mass, damping and friction loss by least squares (Level 18 checkpoint).

INPUT   pendulum.xml with hidden parameters: mass 1.3 kg, joint damping 0.08 N m s/rad,
        friction loss 0.05 N m; the angle measured with Gaussian noise (0.5 mrad), the
        torque known (it is the command)
PROCESS the inverse dynamics tau = m (L^2 qdd + g L sin q) + I_c qdd + b qd + f sign(qd) are
        linear in (m, b, f) given q, qd, qdd. From 10 s of multisine excitation:
        (1) qd and qdd by finite differences of the noisy angle, and by a Savitzky-Golay
            filter; least-squares estimates from each;
        (2) uncertainty: the ordinary least-squares standard errors against a block bootstrap;
        (3) identifiability: a weak excitation (a tenth of the amplitude), the condition
            number of the regressor, how much of the record is slow, and a fit that leaves out
            samples slower than 0.1 rad/s, where the friction model is wrong;
        (4) validation: a held-out trajectory with a different excitation, simulated open loop
            with the true and with the estimated parameters
OUTPUT  printed tables

Run:  python examples/l18_1_sysid_least_squares.py
"""

import mujoco
import numpy as np
from scipy.signal import savgol_filter

from mjcourse import model_path

TRUE = {"mass": 1.3, "damping": 0.08, "frictionloss": 0.05}
L, I_C, G = 0.5, 1e-4, 9.81
NOISE = 0.0005                                       # angle noise (rad)


def pendulum(params: dict) -> tuple[mujoco.MjModel, mujoco.MjData]:
    model = mujoco.MjModel.from_xml_path(str(model_path("pendulum")))
    body, joint = model.body("pole").id, model.joint("hinge").id
    model.body_mass[body] = params["mass"]
    model.dof_damping[joint] = params["damping"]
    model.dof_frictionloss[joint] = params["frictionloss"]
    data = mujoco.MjData(model)
    mujoco.mj_setConst(model, data)                  # derived constants after editing the mass (Lesson 17.1)
    mujoco.mj_resetData(model, data)
    return model, data


def multisine(t: np.ndarray, amplitude: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    freqs, phases = rng.uniform(0.2, 3.0, 5), rng.uniform(0, 2 * np.pi, 5)
    return amplitude * sum(np.sin(2 * np.pi * f * t + p) for f, p in zip(freqs, phases)) / 5


def simulate(params: dict, torque: np.ndarray) -> np.ndarray:
    model, data = pendulum(params)
    q = np.empty(len(torque))
    for k, tau in enumerate(torque):
        q[k] = data.qpos[0]
        data.ctrl[0] = tau
        mujoco.mj_step(model, data)
    return q


def regressor(q, qd, qdd) -> np.ndarray:
    """Columns multiply (m, b, f); the known rotor inertia term goes to the left-hand side."""
    return np.c_[L * L * qdd + G * L * np.sin(q), qd, np.sign(qd)]


def derivatives(q: np.ndarray, h: float, method: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if method == "finite differences":
        qd = np.gradient(q, h)
        return q, qd, np.gradient(qd, h)
    window = 51                                       # 0.1 s at 2 ms, cubic fits
    return (savgol_filter(q, window, 3), savgol_filter(q, window, 3, deriv=1, delta=h),
            savgol_filter(q, window, 3, deriv=2, delta=h))


def fit(q, qd, qdd, tau, trim: int = 30, min_speed: float = 0.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Least squares on the samples away from the ends (and, optionally, faster than min_speed);
    returns (estimate, standard errors, residuals)."""
    sl = np.arange(trim, len(q) - trim)
    sl = sl[np.abs(qd[sl]) >= min_speed]
    x, y = regressor(q[sl], qd[sl], qdd[sl]), tau[sl] - I_C * qdd[sl]
    theta, *_ = np.linalg.lstsq(x, y, rcond=None)
    resid = y - x @ theta
    cov = resid.var(ddof=3) * np.linalg.inv(x.T @ x)
    return theta, np.sqrt(np.diag(cov)), resid


def block_bootstrap(q, qd, qdd, tau, blocks: int = 20, n: int = 500, seed: int = 0) -> np.ndarray:
    """Refit on resampled contiguous blocks of the record: errors that are correlated in time stay together."""
    rng = np.random.default_rng(seed)
    idx = np.array_split(np.arange(30, len(q) - 30), blocks)
    estimates = []
    for _ in range(n):
        pick = np.concatenate([idx[i] for i in rng.integers(0, blocks, blocks)])
        x, y = regressor(q[pick], qd[pick], qdd[pick]), tau[pick] - I_C * qdd[pick]
        estimates.append(np.linalg.lstsq(x, y, rcond=None)[0])
    return np.std(estimates, axis=0)


def row(name: str, theta, se=None) -> str:
    cells = [f"{v:.4f}" + (f" +- {s:.4f}" if se is not None else "") for v, s in zip(theta, se if se is not None else theta)]
    return f"  {name:<44}" + "".join(f"{c:>22}" for c in cells)


if __name__ == "__main__":
    model, _ = pendulum(TRUE)
    h = model.opt.timestep
    t = np.arange(round(10.0 / h)) * h
    rng = np.random.default_rng(0)
    torque = multisine(t, 2.5, seed=1)
    q_true = simulate(TRUE, torque)
    q = q_true + rng.normal(0.0, NOISE, len(q_true))
    print(f"MuJoCo {mujoco.__version__}; 10 s at {1000 * h:.0f} ms, angle noise {1000 * NOISE} mrad, "
          f"angle range {q_true.min():.2f} to {q_true.max():.2f} rad, peak speed {np.abs(np.gradient(q_true, h)).max():.2f} rad/s")
    print(f"  {'':<44}" + "".join(f"{k:>22}" for k in ("mass (kg)", "damping (N m s/rad)", "friction loss (N m)")))
    print(row("truth", list(TRUE.values())))
    print("(1) derivatives and estimates")
    for method in ("finite differences", "Savitzky-Golay"):
        theta, se, _ = fit(*derivatives(q, h, method), torque)
        print(row(method, theta))
    theta, se, resid = fit(*derivatives(q_true, h, "finite differences"), torque)
    print(row("finite differences of the noise-free angle", theta))
    print("(2) uncertainty of the Savitzky-Golay estimate")
    qs = derivatives(q, h, "Savitzky-Golay")
    theta, se, resid = fit(*qs, torque)
    print(row("ordinary least-squares standard errors", theta, se))
    print(row("block bootstrap standard errors", theta, block_bootstrap(*qs, torque)))
    lag1 = np.corrcoef(resid[:-1], resid[1:])[0, 1]
    print(f"  residual autocorrelation at one sample: {lag1:.3f}")
    print("(3) excitation and identifiability")
    for label, amplitude in (("full excitation (2.5 N m)", 2.5), ("weak excitation (0.25 N m)", 0.25)):
        tq = multisine(t, amplitude, seed=1)
        qq = simulate(TRUE, tq) + np.random.default_rng(1).normal(0.0, NOISE, len(t))
        dq = derivatives(qq, h, "Savitzky-Golay")
        x = regressor(*(d[30:-30] for d in dq))
        theta, _, _ = fit(*dq, tq)
        print(row(f"{label}, cond {np.linalg.cond(x / np.abs(x).max(axis=0)):.0f}", theta, block_bootstrap(*dq, tq)))
        speed = np.abs(dq[1][30:-30])
        fast = np.sum(speed >= 0.1)
        refit = (", ".join(f"{v:.4f}" for v in fit(*dq, tq, min_speed=0.1)[0]) if fast >= 100
                 else f"only {fast} samples, too few to fit")
        print(f"    peak speed {speed.max():.2f} rad/s; {np.mean(speed < 0.1):.0%} of samples slower than 0.1 rad/s; "
              f"fit without them: {refit}")
    print("(4) validation on a held-out trajectory (different multisine), open-loop simulation")
    estimate = dict(zip(TRUE, fit(*derivatives(q, h, "Savitzky-Golay"), torque)[0]))
    held_torque = multisine(t, 2.5, seed=7)
    q_held = simulate(TRUE, held_torque) + np.random.default_rng(2).normal(0.0, NOISE, len(t))
    filtered = dict(zip(TRUE, fit(*derivatives(q, h, "Savitzky-Golay"), torque, min_speed=0.1)[0]))
    for label, params in (("estimated parameters", estimate), ("estimated without samples slower than 0.1 rad/s", filtered),
                          ("finite-difference estimate", dict(zip(TRUE, fit(*derivatives(q, h, "finite differences"), torque)[0]))),
                          ("nominal guess (1.0 kg, no damping, no friction)", {"mass": 1.0, "damping": 0.0, "frictionloss": 0.0})):
        q_sim = simulate(params, held_torque)
        err = q_sim - q_held
        print(f"  {label:<48} angle RMS error {1000 * np.sqrt(np.mean(err**2)):7.2f} mrad, "
              f"after 1 s {1000 * np.sqrt(np.mean(err[:round(1 / h)]**2)):6.2f} mrad")
