"""Showcase: arm7 writes "MuJoCo" on a vertical board under operational-space control (Lessons 6 and 8.3).

INPUT   arm7.xml from its home keyframe; the tool site "ee" writes on a virtual board, the plane 3 cm beyond
        the home position along x; letters 6 cm tall from a stroke font, read facing the robot
PROCESS each stroke segment is a minimum-jerk move at a set average speed; the pen lifts 3 cm off the board
        between strokes. Two controllers track the reference: operational space (bandwidth 30 rad/s,
        null-space posture, mjcourse.control.operational_space) and Jacobian transpose (Kp 400 N/m, Kd 40 N s/m,
        gravity compensated, as in Lesson 8.3). For average writing speeds of 5, 10, 20 and 40 cm/s:
        the RMS and largest distance between the tool and its reference while the pen is down, and the time
        to write the word
OUTPUT  printed table

Run:  python examples/showcase_robot_writes.py          (about 1 minute)
"""

import math
import os

import mujoco
import numpy as np

from mjcourse import control, model_path

FAST = os.environ.get("MJC_FAST") == "1"
HEIGHT, LIFT, WN, K_NULL = 0.06, 0.03, 30.0, 20.0


def circle(cx, cy, r, a0, a1, n):
    return [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in np.linspace(math.radians(a0), math.radians(a1), n)]


# Strokes in a letter box of width 1 and height 1.5 (cap height), baseline at 0.
FONT = {
    "M": [[(0, 0), (0, 1.5), (0.5, 0.6), (1, 1.5), (1, 0)]],
    "u": [[(0, 1), (0, 0.3), (0.3, 0), (0.7, 0), (1, 0.3)], [(1, 1), (1, 0)]],
    "J": [[(0.3, 1.5), (1, 1.5)], [(0.7, 1.5), (0.7, 0.35), (0.45, 0), (0.15, 0), (0, 0.3)]],
    "o": [circle(0.5, 0.5, 0.5, 90, 450, 17)],
    "C": [circle(0.75, 0.75, 0.75, 45, 315, 17)],
}
ADVANCE = {"M": 1.4, "u": 1.35, "J": 1.3, "o": 1.3, "C": 1.35}


def strokes(word: str, origin: np.ndarray) -> list[np.ndarray]:
    """3D strokes on the board: letter x -> world +y (readable facing the robot), letter y -> world z."""
    scale, out, cursor = HEIGHT / 1.5, [], 0.0
    width = sum(ADVANCE[c] for c in word) * scale
    for c in word:
        for stroke in FONT[c]:
            pts = [origin + [0.0, (cursor + u) * scale - width / 2, (v - 0.75) * scale] for u, v in stroke]
            out.append(np.array(pts))
        cursor += ADVANCE[c]
    return out


def min_jerk(a: np.ndarray, b: np.ndarray, duration: float, h: float):
    """Samples (position, velocity, acceleration, pen) of a minimum-jerk move from a to b."""
    n = max(round(duration / h), 1)
    for k in range(n):
        s = k / n
        p = 10 * s**3 - 15 * s**4 + 6 * s**5
        dp = (30 * s**2 - 60 * s**3 + 30 * s**4) / duration
        ddp = (60 * s - 180 * s**2 + 120 * s**3) / duration**2
        yield a + (b - a) * p, (b - a) * dp, (b - a) * ddp


def reference(word: str, start: np.ndarray, board_x: float, speed: float, h: float):
    """The full reference: pen-up travel at twice the writing speed, then each stroke on the board."""
    pos, out = start.copy(), []
    for stroke in strokes(word, np.array([board_x, start[1], start[2]])):
        lifted = stroke[0] - [LIFT, 0.0, 0.0]
        for a, b, down in ((pos, lifted, False), (lifted, stroke[0], False)):
            out += [(x, v, acc, down) for x, v, acc in min_jerk(a, b, max(np.linalg.norm(b - a) / (2 * speed), 0.15), h)]
        for a, b in zip(stroke[:-1], stroke[1:]):
            out += [(x, v, acc, True) for x, v, acc in min_jerk(a, b, max(np.linalg.norm(b - a) / speed, 0.05), h)]
        pos = stroke[-1] - [LIFT, 0.0, 0.0]
        out += [(x, v, acc, False) for x, v, acc in min_jerk(stroke[-1], pos, 0.15, h)]
    return out


def write(kind: str, speed: float) -> tuple[float, float, float]:
    """(RMS and largest pen-down error in mm, seconds to write)."""
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    data = mujoco.MjData(model)
    home = model.key_qpos[model.key("home").id].copy()
    data.qpos[:] = home
    mujoco.mj_forward(model, data)
    sid, h = model.site("ee").id, model.opt.timestep
    start = data.site_xpos[sid].copy()
    errors = []
    for x_d, v_d, a_d, down in reference("MuJoCo", start, start[0] + LIFT, speed, h):
        mujoco.mj_forward(model, data)
        if kind == "operational space":
            tau = control.operational_space(model, data, "ee", x_d, v_d, WN**2, 2 * WN, xdd_des=a_d,
                                            q_rest=home, k_null=K_NULL)
        else:
            jac = np.zeros((3, model.nv))
            mujoco.mj_jacSite(model, data, jac, None, sid)
            e, edot = x_d - data.site_xpos[sid], v_d - jac @ data.qvel
            tau = jac.T @ (400.0 * e + 40.0 * edot) + data.qfrc_bias + model.dof_damping * data.qvel
        data.ctrl[:] = np.clip(tau, *model.actuator_ctrlrange.T)
        mujoco.mj_step(model, data)
        if down:
            errors.append(np.linalg.norm(data.site_xpos[sid] - x_d))
    errors = 1000 * np.array(errors)
    return float(np.sqrt(np.mean(errors**2))), float(errors.max()), data.time


if __name__ == "__main__":
    print(f"MuJoCo {mujoco.__version__}; arm7 writes \"MuJoCo\", letters {100 * HEIGHT:.0f} cm tall, pen lifted {100 * LIFT:.0f} cm "
          "between strokes")
    print(f"  {'average speed':>14}  {'controller':<20}{'pen-down RMS error':>20}{'largest':>10}{'time to write':>15}")
    for speed in ((0.1,) if FAST else (0.05, 0.1, 0.2, 0.4)):
        for kind in ("operational space", "Jacobian transpose"):
            rms, peak, seconds = write(kind, speed)
            print(f"  {100 * speed:>9.0f} cm/s  {kind:<20}{rms:>17.2f} mm{peak:>7.2f} mm{seconds:>13.1f} s")
