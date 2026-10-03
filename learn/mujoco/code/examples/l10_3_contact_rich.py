"""Lesson 10.3: contact-rich tasks: peg insertion, a drawer, a door, pushing.

INPUT   peg_insert.xml (arm7 with a peg of radius 12 mm over a square hole of half-width 14 mm:
        2 mm clearance per side); articulated.xml (arm7 + gripper, a cabinet with a drawer and a
        door); push.xml (arm7 + gripper used as a pusher, a puck and a goal)
PROCESS (1) peg insertion with the hole's position known to within e mm (8 error directions):
            a stiff Cartesian impedance (20 kN/m); a compliant one (2 kN/m across, 1 kN/m along the
            hole) whose descending target never runs more than 5 mm below the tip, so the push
            stays near 5 N; the compliant one plus a spiral search when the peg stalls on the rim;
            outcome, peak and final contact force, largest tilt of the peg;
        (2) spiral search time against position error, compared with pi e^2 / (p v);
        (3) a drawer pulled 15 cm along a direction pitched alpha above its slide, stiff and
            compliant (500 N/m): force across the slide against K L sin(alpha), jaws pried open;
        (4) a door opened 0.3 rad by tracking an arc whose radius is off by -20 to +20 %, stiff
            and compliant, and by pulling along the handle's own motion with no hinge model;
        (5) a puck pushed to a goal from random starts with random friction: open loop from the
            exact start, open loop from a noisy start estimate (sigma 10 mm), closed loop
OUTPUT  printed tables

Run:  python examples/l10_3_contact_rich.py
"""

import math
import os

import mujoco
import numpy as np

from mjcourse import control, kinematics, model_path, spatial

FAST = os.environ.get("MJC_FAST") == "1"
DIRECTIONS = np.arange(2 if FAST else 8) * math.pi / (1 if FAST else 4)   # error directions for the peg (rad)
WN = 20.0                                       # joint-space bandwidth for approach moves (rad/s)
K_NULL = 20.0                                   # null-space posture stiffness (N m/rad)


def min_jerk(s: float) -> float:
    s = min(max(s, 0.0), 1.0)
    return 10 * s**3 - 15 * s**4 + 6 * s**5


def contact_force(model, data, geoms_a: set[int], geoms_b: set[int]) -> np.ndarray:
    """World-frame force that geoms_a exert on geoms_b, summed over their contacts."""
    total, f = np.zeros(3), np.zeros(6)
    for i in range(data.ncon):
        c = data.contact[i]
        if c.geom1 in geoms_a and c.geom2 in geoms_b:
            sign = 1.0                                  # the contact normal points from geom1 to geom2
        elif c.geom2 in geoms_a and c.geom1 in geoms_b:
            sign = -1.0
        else:
            continue
        mujoco.mj_contactForce(model, data, i, f)
        total += sign * (c.frame.reshape(3, 3).T @ f[:3])
    return total


def geom_ids(model, names) -> set[int]:
    return {model.geom(n).id for n in names}


class Arm:
    """arm7 in one of the gripper scenes: joint-space approach moves, gripper commands, impedance steps."""

    def __init__(self, scene: str):
        self.m = mujoco.MjModel.from_xml_path(str(model_path(scene)))
        self.d = mujoco.MjData(self.m)
        m, d = self.m, self.d
        mujoco.mj_resetDataKeyframe(m, d, m.key("home").id)
        mujoco.mj_forward(m, d)
        mass = np.zeros((m.nv, m.nv))
        mujoco.mj_fullM(m, d, mass)
        self.kp, self.kd = np.diag(mass)[:7] * WN**2, 2 * np.diag(mass)[:7] * WN
        self.target = d.qpos[:7].copy()
        self.h = m.opt.timestep
        self.down = spatial.mat_to_quat(d.site("gripper/tcp").xmat.reshape(3, 3))

    def hold(self, n: int = 1) -> None:
        m, d = self.m, self.d
        for _ in range(n):
            mujoco.mj_forward(m, d)
            tau = self.kp * (self.target - d.qpos[:7]) - self.kd * d.qvel[:7] + d.qfrc_bias[:7]
            d.ctrl[:7] = np.clip(tau, m.actuator_ctrlrange[:7, 0], m.actuator_ctrlrange[:7, 1])
            mujoco.mj_step(m, d)

    def move(self, pos: np.ndarray, quat: np.ndarray, seconds: float) -> None:
        result, _ = kinematics.solve_ik_restarts(self.m, "gripper/tcp", pos, quat, q_init=self.d.qpos.copy(),
                                                 joints=list(range(7)), restarts=10, seed=0, tol_pos=5e-4, tol_rot=5e-3)
        if not result.success:
            raise RuntimeError(f"IK failed for {pos}")
        start, goal, n = self.target.copy(), result.qpos[:7].copy(), round(seconds / self.h)
        for k in range(n):
            self.target = start + (goal - start) * min_jerk((k + 1) / n)
            self.hold()
        self.hold(round(0.3 / self.h))

    def grip(self, command: float, seconds: float = 0.6) -> None:
        self.d.ctrl[7] = command
        self.hold(round(seconds / self.h))

    def impedance(self, x_des, quat, k_pos, k_rot, q_rest) -> None:
        mujoco.mj_forward(self.m, self.d)
        self.d.ctrl[:7] = control.cartesian_impedance(self.m, self.d, "gripper/tcp", x_des, quat, k_pos, k_rot,
                                                      q_rest=q_rest, k_null=K_NULL)
        mujoco.mj_step(self.m, self.d)

    def tcp(self) -> np.ndarray:
        return self.d.site("gripper/tcp").xpos.copy()


# ---------------------------------------------------------------- (1, 2) peg insertion
PEG_DELTA = 0.005                 # the compliant target runs at most 5 mm below the tip
PITCH, SEARCH_SPEED = 0.002, 0.01  # spiral pitch (m per turn) and path speed (m/s)


def insert(error: float, angle: float, mode: str, seconds: float = 10.0) -> dict:
    """Insert the peg into a hole believed to be `error` m away (direction `angle`) from where it is."""
    m = mujoco.MjModel.from_xml_path(str(model_path("peg_insert")))
    d = mujoco.MjData(m)
    mujoco.mj_resetDataKeyframe(m, d, m.key("home").id)
    mujoco.mj_forward(m, d)
    tip, h = m.site("tool/peg_tip").id, m.opt.timestep
    home, down = d.qpos.copy(), spatial.mat_to_quat(d.site_xmat[tip].reshape(3, 3))
    top = d.site("hole_top").xpos.copy()
    estimate = top[:2] + error * np.array([math.cos(angle), math.sin(angle)])
    start, above = d.site_xpos[tip].copy(), np.r_[estimate, top[2] + 0.03]
    peg, block = {m.geom("tool/peg").id}, geom_ids(m, ("hole_px", "hole_nx", "hole_py", "hole_ny", "hole_floor"))
    xy, z_des, theta = estimate.copy(), above[2], 0.0
    out = {"inserted": None, "peak": 0.0, "tilt": 0.0, "stalled": None, "dropped": None, "late": []}
    for k in range(round(seconds / h)):
        t = k * h
        mujoco.mj_forward(m, d)
        x = d.site_xpos[tip]
        if t < 1.5:                                                    # to 3 cm above the estimate
            target, k_pos = start + (above - start) * min_jerk(t / 1.2), 2000.0
        elif mode == "stiff":
            z_des = max(z_des - 0.02 * h, 0.002)                       # descend at 2 cm/s to 2 mm below the floor
            target, k_pos = np.r_[xy, z_des], 20000.0
        else:
            z_des = max(z_des - 0.02 * h, x[2] - PEG_DELTA, 0.002)    # never more than PEG_DELTA below the tip
            on_rim = x[2] > top[2] - 0.001
            if mode == "search" and on_rim and z_des <= x[2] - PEG_DELTA + 1e-6 and out["stalled"] is None:
                out["stalled"] = t
            if mode == "search" and out["stalled"] is not None and out["dropped"] is None:
                if on_rim:                                             # Archimedean spiral around the estimate
                    r = PITCH * theta / (2 * math.pi)
                    theta += SEARCH_SPEED * h / max(r, 0.001)
                    xy = estimate + r * np.array([math.cos(theta), math.sin(theta)])
                else:
                    out["dropped"] = t
            target, k_pos = np.r_[xy, z_des], np.array([2000.0, 2000.0, 1000.0])
        d.ctrl[:] = control.cartesian_impedance(m, d, "tool/peg_tip", target, down, k_pos, 300.0, q_rest=home, k_null=K_NULL)
        mujoco.mj_step(m, d)
        force = float(np.linalg.norm(contact_force(m, d, peg, block)))
        out["peak"] = max(out["peak"], force)
        out["tilt"] = max(out["tilt"], math.degrees(math.acos(min(1.0, -d.site_xmat[tip][8]))))
        out["late"].append(force)
        if out["inserted"] is None and d.site_xpos[tip][2] < 0.012:
            out["inserted"] = t
        if out["inserted"] is not None and t > out["inserted"] + 1.0:          # seated and settled
            break
    out["final"] = float(np.mean(out["late"][-round(0.5 / h):]))
    out["tip_z"] = d.site_xpos[tip][2]
    return out


def outcome(r: dict) -> str:
    if r["inserted"] is not None:
        return "inserted" if r["tilt"] < 2.0 else "forced in, tilted"
    return "stalled on the rim" if r["tilt"] < 2.0 else "jammed, tilted"


def peg_table() -> None:
    print(f"  {'controller':<20}{'e (mm)':>7}  {'outcomes over directions':<44}{'peak (N)':>9}{'final (N)':>10}{'tilt (deg)':>11}")
    for mode, label in (("stiff", "stiff 20 kN/m"), ("compliant", "compliant"), ("search", "compliant + search")):
        for e in (0.0, 1.5, 3.0, 5.0):
            runs = [insert(e / 1000, a, mode) for a in DIRECTIONS]
            names = [outcome(r) for r in runs]
            summary = ", ".join(f"{names.count(n)} {n}" for n in dict.fromkeys(names))
            print(f"  {label:<20}{e:>7.1f}  {summary:<44}{np.median([r['peak'] for r in runs]):>9.1f}"
                  f"{np.median([r['final'] for r in runs]):>10.1f}{max(r['tilt'] for r in runs):>11.1f}")


def search_table() -> None:
    print(f"  {'e (mm)':>7}{'inserted':>10}{'searched':>10}{'mean search (s)':>17}{'max search (s)':>16}{'pi e^2/(p v) (s)':>18}")
    for e in ((3.0, 8.0) if FAST else (3.0, 5.0, 8.0, 12.0)):
        runs = [insert(e / 1000, a, "search", seconds=30.0) for a in DIRECTIONS]
        times = [r["dropped"] - r["stalled"] for r in runs if r["dropped"] is not None and r["stalled"] is not None]
        bound = math.pi * (e / 1000) ** 2 / (PITCH * SEARCH_SPEED)
        print(f"  {e:>7.1f}{sum(r['inserted'] is not None for r in runs):>7d}/{len(runs)}{len(times):>10d}"
              f"{np.mean(times) if times else float('nan'):>17.2f}{max(times) if times else float('nan'):>16.2f}{bound:>18.2f}")


# ---------------------------------------------------------------- (3) drawer
R_FRONT_BAR = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]], float)     # tool along +x, jaws close vertically
R_FRONT_POST = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)   # tool along +x, jaws close horizontally
PADS = ("gripper/pad_left", "gripper/pad_right", "gripper/finger_left", "gripper/finger_right")


def grasp_handle(arm: Arm, site: str, rotation: np.ndarray) -> np.ndarray:
    quat = spatial.mat_to_quat(rotation)
    handle = arm.d.site(site).xpos.copy()
    arm.grip(0.04, 0.1)
    arm.move(handle - np.array([0.08, 0, 0]), quat, 2.0)
    arm.move(handle, quat, 1.0)
    arm.grip(0.0, 0.8)
    return quat


def drawer(alpha_deg: float, k_pos: float, length: float = 0.15, seconds: float = 3.0) -> tuple[float, float, float]:
    arm = Arm("articulated")
    m, d = arm.m, arm.d
    quat = grasp_handle(arm, "drawer_handle", R_FRONT_BAR)
    x0, q_rest, a = arm.tcp(), d.qpos[:7].copy(), math.radians(alpha_deg)
    pull = np.array([-math.cos(a), 0.0, math.sin(a)])      # believed direction; the slide is along -x
    pads, handle = geom_ids(m, PADS), geom_ids(m, ("drawer_handle", "drawer_handle_l", "drawer_handle_r"))
    opening0, pried = d.ten_length[0], 0.0
    n = round(seconds / arm.h)
    for k in range(n + round(1.0 / arm.h)):
        arm.impedance(x0 + length * min_jerk((k + 1) / n) * pull, quat, k_pos, 300.0, q_rest)
        pried = max(pried, d.ten_length[0] - opening0)
    across = abs(contact_force(m, d, pads, handle)[2])
    return d.joint("drawer").qpos[0], across, pried


def drawer_table() -> None:
    print(f"  {'controller':<16}{'alpha (deg)':>12}{'opened (mm)':>13}{'force across slide (N)':>24}{'K L sin(alpha) (N)':>20}{'jaws pried (mm)':>17}")
    for label, k_pos in (("stiff 20 kN/m", 20000.0), ("compliant", 500.0)):
        for alpha in (0, 5, 10, 20):
            opened, across, pried = drawer(alpha, k_pos)
            print(f"  {label:<16}{alpha:>12d}{1000 * opened:>13.1f}{across:>24.1f}"
                  f"{k_pos * 0.15 * math.sin(math.radians(alpha)):>20.1f}{1000 * pried:>17.1f}")


# ---------------------------------------------------------------- (4) door
DOOR_GOAL = -0.3                  # rad; the door opens toward the robot, negative about +z


def door(mode: str, radius_error: float = 0.0, seconds: float = 3.0, lead: float = 0.02,
         goal: float = DOOR_GOAL) -> tuple[float, float, list[str]]:
    """Open the door with the hand's orientation held fixed: the vertical bar turns between
    the pads, so the grasp acts as a hinge. Returns the door angle, the peak radial force on
    the handle and the arm's self-contacts at the end."""
    arm = Arm("articulated")
    m, d = arm.m, arm.d
    quat = grasp_handle(arm, "door_handle", R_FRONT_POST)
    x0, q_rest = arm.tcp(), d.qpos[:7].copy()
    hinge_true = np.r_[d.body("door").xpos[:2], x0[2]]
    believed = x0 + (hinge_true - x0) * (1 + radius_error)        # the hinge, as far off as the radius error says
    pads, handle = geom_ids(m, PADS), geom_ids(m, ("door_handle", "door_handle_t", "door_handle_b"))
    k_pos = 20000.0 if mode == "stiff" else 500.0
    direction, last, peak = np.array([-1.0, 0.0, 0.0]), x0.copy(), 0.0
    n = round(seconds / arm.h)
    for k in range(n + round(1.0 / arm.h)):
        x = arm.tcp()
        if mode == "follow":                       # pull along the handle's own motion, no hinge model
            if np.linalg.norm((x - last)[:2]) > 2e-4:
                moved = np.r_[(x - last)[:2] / np.linalg.norm((x - last)[:2]), 0.0]
                if moved @ direction > 0.5:        # a rebound is not a new direction: ignore reversals
                    direction = moved
                last = x
            x_des = x + lead * direction if d.sensor("door_angle").data[0] > goal else x
        else:                                      # track an arc about the believed hinge
            th = goal * min_jerk((k + 1) / n)
            rel = x0 - believed
            x_des = believed + np.array([math.cos(th) * rel[0] - math.sin(th) * rel[1],
                                         math.sin(th) * rel[0] + math.cos(th) * rel[1], rel[2]])
        arm.impedance(x_des, quat, k_pos, 300.0, q_rest)
        radial = hinge_true - d.site("door_handle").xpos
        radial[2] = 0.0
        peak = max(peak, abs(contact_force(m, d, pads, handle) @ radial) / np.linalg.norm(radial))
    arm_bodies = {m.body(f"link{i}").id for i in range(1, 8)}
    self_contacts = sorted({f"{m.geom(c.geom1).name}-{m.geom(c.geom2).name}" for c in d.contact[:d.ncon]
                            if m.geom_bodyid[c.geom1] in arm_bodies and m.geom_bodyid[c.geom2] in arm_bodies})
    return d.joint("door").qpos[0], peak, self_contacts


def door_table() -> None:
    print(f"  goal {math.degrees(DOOR_GOAL):.1f} deg")
    print(f"  {'controller':<26}{'radius error':>13}{'door (deg)':>12}{'peak radial force (N)':>23}")
    for mode, label in (("stiff", "stiff arc 20 kN/m"), ("compliant", "compliant arc 500 N/m")):
        for err in (0.0, -0.1, 0.1, -0.2, 0.2):
            angle, peak, _ = door(mode, err)
            print(f"  {label:<26}{err:>+13.0%}{math.degrees(angle):>12.1f}{peak:>23.1f}")
    angle, peak, _ = door("follow")
    print(f"  {'follow the motion 500 N/m':<26}{'no model':>13}{math.degrees(angle):>12.1f}{peak:>23.1f}")
    angle, _, contacts = door("follow", goal=-1.2, seconds=6.0)
    print(f"  reach: following the motion toward 1.2 rad stops at {math.degrees(angle):.1f} deg; "
          f"arm self-contacts then: {', '.join(contacts) or 'none'}")


# ---------------------------------------------------------------- (5) pushing
R_PUCK, FACE_HALF_WIDTH, PUSHER_HALF, TCP_Z, PUSH_SPEED = 0.035, 0.016, 0.008, 0.03, 0.05


def push(puck_xy: np.ndarray, mu: float, closed_loop: bool, estimate_error: np.ndarray, delta: float = 0.003) -> float:
    """Push the puck to the goal with the closed fingers. The pushing face is 32 mm wide,
    perpendicular to the hand's x axis; yaw turns it about the vertical."""
    arm = Arm("push")
    m, d = arm.m, arm.d
    adr = m.jnt_qposadr[m.joint("puck").id]
    d.qpos[adr:adr + 3] = [*puck_xy, 0.02]
    for name in ("floor", "puck"):
        m.geom_friction[m.geom(name).id, 0] = mu
    mujoco.mj_forward(m, d)
    goal = d.site("goal").xpos[:2].copy()

    def puck() -> np.ndarray:
        return d.body("puck").xpos[:2].copy()

    def face(yaw: float) -> np.ndarray:
        return spatial.quat_mul(np.array([math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]), arm.down)

    estimate = puck() + estimate_error
    u = (goal - estimate) / np.linalg.norm(goal - estimate)
    yaw = math.atan2(u[1], u[0])
    arm.grip(0.0, 0.3)
    start = estimate - (R_PUCK + PUSHER_HALF + 0.03) * u
    arm.move(np.r_[start, 0.12], face(yaw), 1.5)
    arm.move(np.r_[start, TCP_Z], face(yaw), 1.0)
    target, q_rest = arm.tcp()[:2], d.qpos[:7].copy()
    distance, travelled = np.linalg.norm(goal - estimate) + 0.03 + delta, 0.0
    for _ in range(round(8.0 / arm.h)):
        if closed_loop:
            p = puck()
            if np.linalg.norm(goal - p) > 0.005:
                to_goal = (goal - p) / np.linalg.norm(goal - p)
                yaw = math.atan2(to_goal[1], to_goal[0])               # face normal from the puck to the goal
                step = p - (R_PUCK + PUSHER_HALF - delta) * to_goal - target
                if np.linalg.norm(step) > PUSH_SPEED * arm.h:
                    step *= PUSH_SPEED * arm.h / np.linalg.norm(step)
                target = target + step
        elif travelled < distance:
            target, travelled = target + PUSH_SPEED * arm.h * u, travelled + PUSH_SPEED * arm.h
        arm.impedance(np.r_[target, TCP_Z], face(yaw), 2000.0, 300.0, q_rest)
    return float(np.linalg.norm(puck() - goal))


def push_table() -> None:
    n = 4 if FAST else 20
    rng = np.random.default_rng(3)
    starts = np.c_[rng.uniform(0.42, 0.48, n), rng.uniform(-0.03, 0.03, n)]
    mus, errors = rng.uniform(0.3, 0.7, n), rng.normal(0.0, 0.01, (n, 2))
    goal = mujoco.MjModel.from_xml_path(str(model_path("push"))).site("goal").pos[:2]
    lateral = []
    for s, e in zip(starts, errors):                      # component of the error across the push line
        u = (goal - s - e) / np.linalg.norm(goal - s - e)
        lateral.append(abs(e @ np.array([-u[1], u[0]])))
    print(f"  {n} starts in x 0.42-0.48, y -0.03-0.03 m; floor and puck friction 0.3-0.7; goal {goal} m")
    print(f"  {'strategy':<34}{'median error (mm)':>18}{'max (mm)':>10}{'within 1 cm':>13}")
    results = {}
    for label, closed, errs in (("open loop, exact start", False, np.zeros((n, 2))),
                                ("open loop, start sigma 10 mm", False, errors),
                                ("closed loop, start sigma 10 mm", True, errors)):
        out = np.array([push(s, mu, closed, e) for s, mu, e in zip(starts, mus, errs)])
        results[label] = out
        print(f"  {label:<34}{1000 * np.median(out):>18.1f}{1000 * out.max():>10.1f}{(out < 0.01).sum():>10d}/{n}")
    open_noisy = results["open loop, start sigma 10 mm"]
    off_face = [i for i, lat in enumerate(lateral) if lat > FACE_HALF_WIDTH]
    print(f"  open loop with noise: starts whose error across the push line exceeded the face half-width "
          f"({1000 * FACE_HALF_WIDTH:.0f} mm): {len(off_face)}, final errors (mm) "
          + ", ".join(f"{1000 * open_noisy[i]:.0f}" for i in off_face))
    within = [i for i in range(n) if i not in off_face]
    if within:
        print(f"  the others: final error minus start-estimate error, median {1000 * np.median([open_noisy[i] - np.linalg.norm(errors[i]) for i in within]):+.1f} mm")


if __name__ == "__main__":
    print(f"MuJoCo {mujoco.__version__}; peg error directions: {len(DIRECTIONS)}")
    print("(1) peg insertion, 2 mm clearance, hole position known to within e")
    peg_table()
    print("(2) spiral search (pitch 2 mm, 10 mm/s) time against position error")
    search_table()
    print("(3) drawer pulled 15 cm along a direction pitched alpha above its slide")
    drawer_table()
    print("(4) door opened 0.3 rad")
    door_table()
    print("(5) pushing a puck to a goal")
    push_table()
