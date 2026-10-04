"""Lesson 20.4: derivatives, callbacks, plugins and the C API (Level 20).

INPUT   cartpole.xml (2 dof, a force on the cart), balanced upright at the origin; a pendulum driven by the
        mujoco.pid actuator plugin; c/minimal_step.c
PROCESS (1) mjd_transitionFD: the one-step linearization (A, B) of the upright cart-pole; how well A dx predicts
            one step from perturbations of size 1e-1 to 1e-7; centred against forward differences;
        (2) a discrete LQR controller from (A, B): which initial pole angles it balances in 5 s;
        (3) a control callback: its cost per step from Python, how often mjd_transitionFD calls it, and what it
            does to the B it reports;
        (4) the plugins shipped with the Python package, and the PID plugin holding a pendulum at 0.5 rad;
        (5) the C program c/minimal_step.c compiled against the package's headers and library, against Python
OUTPUT  printed tables

Run:  python examples/l20_4_extending.py          (part 5 needs a C compiler, cc)
"""

import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import mujoco
import numpy as np
from scipy.linalg import solve_discrete_are

from mjcourse import model_path

CODE = Path(__file__).resolve().parents[1]


def upright() -> tuple[mujoco.MjModel, mujoco.MjData]:
    model = mujoco.MjModel.from_xml_path(str(model_path("cartpole")))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return model, data


def linearize(model, data, eps: float = 1e-6, centered: bool = True) -> tuple[np.ndarray, np.ndarray]:
    nx = 2 * model.nv + model.na
    a, b = np.zeros((nx, nx)), np.zeros((nx, model.nu))
    mujoco.mjd_transitionFD(model, data, eps, centered, a, b, None, None)
    return a, b


def next_state(model, x: np.ndarray, u: float = 0.0) -> np.ndarray:
    """One step from state x = (qpos, qvel) of the cart-pole (its qpos is a vector space: no quaternions)."""
    data = mujoco.MjData(model)
    data.qpos[:], data.qvel[:] = x[:model.nq], x[model.nq:]
    data.ctrl[0] = u
    mujoco.mj_step(model, data)
    return np.r_[data.qpos, data.qvel]


def balance(model, gain: np.ndarray, angle: float, seconds: float = 5.0) -> tuple[bool, float]:
    data = mujoco.MjData(model)
    data.qpos[1] = angle
    peak = 0.0
    while data.time < seconds:
        u = float(-gain @ np.r_[data.qpos, data.qvel])
        peak = max(peak, abs(u))
        data.ctrl[0] = u                                   # the actuator clamps it to +-20 N
        mujoco.mj_step(model, data)
    return bool(abs(data.qpos[1]) < 0.01 and abs(data.qpos[0]) < 1.4), peak


if __name__ == "__main__":
    model, data = upright()
    print(f"MuJoCo {mujoco.__version__}; cart-pole upright, timestep {model.opt.timestep} s")
    a, b = linearize(model, data)
    print("(1) mjd_transitionFD, centred, eps 1e-6: A (4 x 4) and B (4 x 1), state (cart, pole, cart velocity, pole rate)")
    for row_a, row_b in zip(a, b):
        print("    " + " ".join(f"{v:+.6f}" for v in row_a) + "   |   " + f"{row_b[0]:+.6e}")
    a_fwd, b_fwd = linearize(model, data, centered=False)
    moving = mujoco.MjData(model)
    moving.qpos[:], moving.qvel[:] = [0.2, 0.6], [0.5, -1.0]
    mujoco.mj_forward(model, moving)
    gaps = [np.abs(linearize(model, moving, e)[0] - linearize(model, moving, e, centered=False)[0]).max() for e in (1e-6, 1e-4)]
    print(f"    forward against centred differences, largest gap in A: {np.abs(a_fwd - a).max():.1e} here (a symmetric point); "
          f"at the moving state (0.2, 0.6, 0.5, -1.0): {gaps[0]:.1e} with eps 1e-6, {gaps[1]:.1e} with eps 1e-4")
    rng = np.random.default_rng(0)
    direction = rng.normal(size=4)
    direction /= np.linalg.norm(direction)
    x0 = np.zeros(4)
    base = next_state(model, x0)
    cells = []
    for s in (1e-1, 1e-2, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7):
        dx = s * direction
        actual, predicted = next_state(model, x0 + dx) - base, a @ dx
        cells.append(f"{s:.0e}: {np.linalg.norm(actual - predicted) / np.linalg.norm(predicted):.1e}")
    print("    one step from a perturbation of size s, relative error of A dx: " + ", ".join(cells))

    print("(2) discrete LQR from (A, B): Q = diag(1, 10, 1, 1), R = 0.1")
    q, r = np.diag([1.0, 10.0, 1.0, 1.0]), np.array([[0.1]])
    p = solve_discrete_are(a, b, q, r)
    gain = np.linalg.solve(r + b.T @ p @ b, b.T @ p @ a)[0]
    closed = np.abs(np.linalg.eigvals(a - np.outer(b[:, 0], gain))).max()
    print(f"    gain K = [{', '.join(f'{k:.2f}' for k in gain)}]; largest closed-loop eigenvalue magnitude {closed:.5f}")
    for angle in (0.1, 0.3, 0.5, 0.7, 0.9):
        ok, peak = balance(model, gain, angle)
        print(f"    start at {angle:.1f} rad: {'balanced' if ok else 'not balanced'} after 5 s, largest commanded force {peak:6.1f} N")

    print("(3) a control callback")
    calls = [0]

    def callback(m, d):
        calls[0] += 1
        d.ctrl[0] = float(-gain @ np.r_[d.qpos, d.qvel])
    rates = {}
    for label, cb in (("no callback", None), ("Python callback", callback)):
        mujoco.set_mjcb_control(cb)
        d = mujoco.MjData(model)
        d.qpos[1] = 0.1
        t0, n = time.perf_counter(), 20000
        for _ in range(n):
            mujoco.mj_step(model, d)
        rates[label] = (time.perf_counter() - t0) / n
    print(f"    microseconds per step: without {1e6 * rates['no callback']:.2f}, with a Python control callback "
          f"{1e6 * rates['Python callback']:.2f}")
    mujoco.set_mjcb_control(callback)
    calls[0] = 0
    a_cb, b_cb = linearize(model, data)
    mujoco.set_mjcb_control(None)
    print(f"    mjd_transitionFD with the callback installed called it {calls[0]} times; |B| with it {np.linalg.norm(b_cb):.2e} "
          f"(without: {np.linalg.norm(b):.2e}); A with it equals A - B K to {np.abs(a_cb - (a - np.outer(b[:, 0], gain))).max():.1e}")

    print("(4) plugins shipped with the Python package")
    plugin_dir = Path(mujoco.__file__).parent / "plugin"
    for lib in sorted(plugin_dir.glob("*.so")) + sorted(plugin_dir.glob("*.dll")) + sorted(plugin_dir.glob("*.dylib")):
        names = sorted(set(re.findall(rb"mujoco\.(?!so\b)[a-z_]+(?:\.[a-z_]+)*", lib.read_bytes())))  # not "libmujoco.so"
        print(f"    {lib.name}: " + ", ".join(n.decode() for n in names))
    pid = mujoco.MjModel.from_xml_string("""<mujoco>
  <extension><plugin plugin="mujoco.pid"><instance name="pid">
    <config key="kp" value="40"/><config key="ki" value="20"/><config key="kd" value="4"/></instance></plugin></extension>
  <worldbody><body><joint name="hinge" type="hinge" axis="0 1 0"/>
    <geom type="capsule" fromto="0 0 0 0 0 -0.5" size="0.02" mass="1"/></body></worldbody>
  <actuator><plugin joint="hinge" plugin="mujoco.pid" instance="pid" actdim="1"/></actuator></mujoco>""")
    d = mujoco.MjData(pid)
    d.ctrl[0] = 0.5
    while d.time < 6.0:
        mujoco.mj_step(pid, d)
    print(f"    mujoco.pid (kp 40, ki 20, kd 4) holding a 1 kg pendulum at 0.5 rad: angle after 6 s {d.qpos[0]:.4f} rad, "
          f"integrator state (act) {d.act[0]:.4f}")

    print("(5) c/minimal_step.c")
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None or os.name == "nt":
        print("    no C compiler found (or Windows); skipped")
    else:
        mj = Path(mujoco.__file__).parent
        library = next(mj.glob("libmujoco.so*"), None) or next(mj.glob("libmujoco*.dylib"))
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "minimal_step"
            cmd = [compiler, str(CODE / "c" / "minimal_step.c"), f"-I{mj / 'include'}", str(library), f"-Wl,-rpath,{mj}", "-o", str(exe)]
            subprocess.run(cmd, check=True)
            out = subprocess.run([str(exe), str(model_path("cartpole"))], check=True, capture_output=True, text=True).stdout.strip()
        print(f"    {out}")
        m = mujoco.MjModel.from_xml_path(str(model_path("cartpole")))
        d = mujoco.MjData(m)
        mujoco.mj_resetDataKeyframe(m, d, 0)
        for _ in range(1000):
            mujoco.mj_step(m, d)
        c_qpos = np.array([float(v) for v in out.split("qpos =")[1].split()])
        print(f"    Python, same model and steps: qpos = {' '.join(f'{v:.17g}' for v in d.qpos)}; "
              f"largest difference {np.abs(c_qpos - d.qpos).max():.1e}")
