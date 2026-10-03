"""Lesson 10.2: a scripted pick-and-place pipeline, measured over randomized initial states.

INPUT   pick_place.xml (arm7 + gripper, three cubes, a tray); the red cube is placed at a
        random position in a 20 x 20 cm area with a random yaw, the other cubes are set aside
PROCESS a state machine over 6-D task-space waypoints:
            approach above the cube -> descend -> close -> check the grasp from contacts
            -> lift -> carry above the tray -> lower -> open -> retreat
        each waypoint is converted to joint angles by inverse kinematics, joints follow
        minimum-jerk paths tracked by PD with gravity compensation; success is judged
        from where the cube ends up, after the gripper has let go and moved away.
        (1) 100 episodes with the exact cube pose;
        (2) the cube's position estimated with Gaussian error (sigma 5, 10, 15 mm per axis),
            run blind (no checks) and with the contact check plus one retry from a fresh
            estimate;
        (3) the capture region: one cube pose, a deterministic position error swept along
            and across the gripper's closing axis, run blind; the measured half-widths then
            predict the blind success rates of (2)
OUTPUT  success rates with Wilson intervals, failure categories, what the checks caught,
        a paired comparison of blind and checked runs (same states, same first estimate),
        the capture region and the predicted blind success rates

Run:  python examples/l10_2_pick_place.py
"""

import math
import os

import mujoco
import numpy as np

from mjcourse import kinematics, model_path, spatial, stats

EPISODES = 20 if os.environ.get("MJC_FAST") == "1" else 100
SEED = 10
AREA = ((0.40, 0.60), (-0.20, 0.00))              # x, y ranges of the cube centre (m): 20 x 20 cm
WN, H = 20.0, 0.002                               # joint feedback bandwidth (rad/s), timestep (s)
OPEN, CLOSED = 0.04, 0.0                          # gripper half-opening commands (m)


class Episode:
    def __init__(self, cube_xy: np.ndarray, yaw: float):
        self.model = mujoco.MjModel.from_xml_path(str(model_path("pick_place")))
        self.data = mujoco.MjData(self.model)
        m, d = self.model, self.data
        mujoco.mj_resetDataKeyframe(m, d, m.key("home").id)
        self.arm = np.arange(7)
        for name, xy in (("green_cube", (-0.6, 0.6)), ("blue_cube", (-0.6, -0.6))):   # out of the way
            adr = m.jnt_qposadr[m.joint(name).id]
            d.qpos[adr:adr + 3] = [*xy, 0.02]
        adr = m.jnt_qposadr[m.joint("red_cube").id]
        d.qpos[adr:adr + 7] = [*cube_xy, 0.02, math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]
        d.ctrl[7] = OPEN
        mujoco.mj_forward(m, d)
        self.cube, self.cube_geom = m.body("red_cube").id, m.geom("red_cube").id
        self.pads = (m.geom("gripper/pad_left").id, m.geom("gripper/pad_right").id)
        self.home = d.qpos[:7].copy()
        self.down = spatial.mat_to_quat(d.site("gripper/tcp").xmat.reshape(3, 3))   # tool pointing down at home
        mass = np.zeros((m.nv, m.nv))
        mujoco.mj_fullM(m, d, mass)
        self.kp = np.diag(mass)[:7] * WN**2
        self.kd = 2 * np.diag(mass)[:7] * WN
        self.target = d.qpos[:7].copy()

    def step(self, n: int = 1) -> None:
        m, d = self.model, self.data
        for _ in range(n):
            mujoco.mj_forward(m, d)
            tau = self.kp * (self.target - d.qpos[:7]) - self.kd * d.qvel[:7] + d.qfrc_bias[:7]
            d.ctrl[:7] = np.clip(tau, m.actuator_ctrlrange[:7, 0], m.actuator_ctrlrange[:7, 1])
            mujoco.mj_step(m, d)

    def move_to(self, pos: np.ndarray, yaw: float, seconds: float) -> bool:
        """IK for the tcp pose, then a minimum-jerk joint path of the given duration."""
        quat = spatial.quat_mul(np.array([math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]), self.down)
        q_init = self.data.qpos.copy()
        result, _ = kinematics.solve_ik_restarts(self.model, "gripper/tcp", pos, quat, q_init=q_init,
                                                 joints=list(range(7)), restarts=5, seed=0, tol_pos=5e-4, tol_rot=5e-3)
        if not result.success:
            return False
        start, goal = self.target.copy(), result.qpos[:7].copy()
        n = round(seconds / H)
        for k in range(n):
            s = (k + 1) / n
            self.target = start + (goal - start) * (10 * s**3 - 15 * s**4 + 6 * s**5)
            self.step()
        self.step(round(0.2 / H))                    # settle
        return True

    def grip(self, command: float, seconds: float = 0.6) -> None:
        self.data.ctrl[7] = command
        self.step(round(seconds / H))

    def grasped(self) -> bool:
        """Both pads touch the cube and the jaws stopped on it, neither open nor fully closed."""
        d = self.data
        touching = set()
        for c in d.contact[:d.ncon]:
            pair = {c.geom1, c.geom2}
            for pad in self.pads:
                if pair == {pad, self.cube_geom}:
                    touching.add(pad)
        opening = d.ten_length[0]
        return len(touching) == 2 and 0.01 < opening < 0.035

    def cube_pos(self) -> np.ndarray:
        return self.data.xpos[self.cube].copy()

    def tipped(self) -> bool:
        """The cube's own z axis is more than 45 degrees from vertical: it was knocked onto another face."""
        return self.data.xmat[self.cube][8] < math.cos(math.pi / 4)


def attempt_grasp(ep: Episode, estimate: np.ndarray, yaw: float) -> bool:
    """Approach the estimated cube pose, descend, close; True if the move succeeded."""
    return (ep.move_to(np.array([*estimate, 0.15]), yaw, 1.5)
            and ep.move_to(np.array([*estimate, 0.022]), yaw, 1.0))


def run_episode(cube_xy: np.ndarray, yaw: float, sigma: float = 0.0, check: bool = True,
                retries: int = 0, rng: np.random.Generator | None = None,
                bias: np.ndarray | None = None) -> tuple[str, int, bool]:
    """One pick-and-place. Returns (outcome, grasp attempts, whether the cube was knocked onto
    another face before a close). With check=False nothing is verified along the way; the
    outcome is judged only at the end, from the cube's position. `bias` replaces the random
    perception error with a fixed one."""
    ep = Episode(cube_xy, yaw)
    tray = ep.data.site("tray_center").xpos.copy()
    grasp_yaw = (yaw + math.pi / 4) % (math.pi / 2) - math.pi / 4        # a cube looks the same every 90 degrees
    attempts, tipped = 0, False

    def result(outcome: str) -> tuple[str, int, bool]:
        return outcome, attempts, tipped

    while True:
        attempts += 1
        error = bias if bias is not None else (rng.normal(0.0, sigma, 2) if sigma > 0 else 0.0)
        estimate = ep.cube_pos()[:2] + error                              # perception
        if not attempt_grasp(ep, estimate, grasp_yaw):
            return result("IK failed")
        tipped = tipped or ep.tipped()
        ep.grip(CLOSED)
        if not check or ep.grasped():
            break
        ep.grip(OPEN, 0.4)                                               # let go, back off, look again
        ep.move_to(np.array([*estimate, 0.15]), grasp_yaw, 0.8)
        if attempts > retries:
            return result("grasp missed")
    if not ep.move_to(np.array([*estimate, 0.15]), grasp_yaw, 1.0):
        return result("IK failed")
    if check and (ep.cube_pos()[2] < 0.08 or not ep.grasped()):
        return result("dropped while lifting")
    if not ep.move_to(np.array([tray[0], tray[1], 0.15]), 0.0, 1.5):
        return result("IK failed")
    if check and ep.cube_pos()[2] < 0.08:
        return result("dropped while carrying")
    if not ep.move_to(np.array([tray[0], tray[1], 0.07]), 0.0, 0.8):
        return result("IK failed")
    ep.grip(OPEN, 0.5)
    ep.move_to(np.array([tray[0], tray[1], 0.15]), 0.0, 0.8)
    ep.step(round(0.5 / H))
    p = ep.cube_pos()
    inside = abs(p[0] - tray[0]) < 0.07 and abs(p[1] - tray[1]) < 0.07 and p[2] < 0.06
    if inside:
        return result("success")
    if np.linalg.norm(p[:2] - cube_xy) < 0.05:
        return result("never picked up (found only at the end)")
    return result("missed the tray")


def report(label: str, results: list[tuple[str, int, bool]], states: np.ndarray) -> None:
    outcomes = [o for o, _, _ in results]
    n = len(outcomes)
    wins = outcomes.count("success")
    lo, hi = stats.wilson_interval(wins, n)
    lucky = sum(o == "success" and t for o, _, t in results)
    print(f"  {label:<44} success {wins:3d}/{n} = {wins / n:.2f}  95% Wilson [{lo:.2f}, {hi:.2f}]"
          + (f"  ({lucky} only after knocking the cube onto another face)" if lucky else ""))
    for category in sorted(set(outcomes) - {"success"}):
        idx = [i for i, o in enumerate(outcomes) if o == category]
        print(f"      {category}: {len(idx)}  e.g. (x, y, yaw deg) "
              + "; ".join(f"({states[i, 0]:.3f}, {states[i, 1]:.3f}, {math.degrees(states[i, 2]):.0f})" for i in idx[:3]))


def capture_region(cube_xy: np.ndarray, max_mm: int = 40) -> dict[str, int]:
    """Sweep a fixed position error along and across the closing axis (cube yaw 0, blind) and
    print the outcome runs. Returns, per axis, the largest error with a clean success on both sides."""
    axes = Episode(cube_xy, 0.0).data.site("gripper/tcp").xmat.reshape(3, 3)
    closing = axes[:2, 1] / np.linalg.norm(axes[:2, 1])                  # the fingers slide along tcp y
    clean = {}
    for name, direction in (("along the closing axis", closing), ("across the closing axis", np.array([-closing[1], closing[0]]))):
        limits = []
        for sign in (1, -1):
            runs = []
            for mm in range(max_mm + 1):
                outcome, _, tipped = run_episode(cube_xy, 0.0, check=False, bias=sign * mm / 1000 * direction)
                label = "success after knocking the cube over" if outcome == "success" and tipped else outcome
                if runs and runs[-1][0] == label:
                    runs[-1][2] = mm
                else:
                    runs.append([label, mm, mm])
            limits.append(runs[0][2] if runs[0][0] == "success" else -1)
            print(f"  {name}, {'+' if sign > 0 else '-'}: " + "; ".join(f"{a}-{b} mm {lab}" for lab, a, b in runs))
        clean[name] = min(limits)
    return clean


def sign_test(wins: int, losses: int) -> float:
    """Exact two-sided p-value for discordant pairs (McNemar's exact test)."""
    n = wins + losses
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(wins, losses) + 1)) / 2**n
    return min(1.0, 2 * tail)


def two_sided(t: float, sigma: float) -> float:
    """P(|e| <= t) for e ~ N(0, sigma^2)."""
    return math.erf(t / (sigma * math.sqrt(2)))


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    states = np.column_stack([rng.uniform(*AREA[0], EPISODES), rng.uniform(*AREA[1], EPISODES),
                              rng.uniform(-math.pi / 4, math.pi / 4, EPISODES)])
    print(f"{EPISODES} initial states (seed {SEED}): red cube in x {AREA[0]}, y {AREA[1]} m, yaw +-45 deg, MuJoCo {mujoco.__version__}")
    print("(1) exact cube pose")
    report("contact checks on", [run_episode(s[:2], s[2]) for s in states], states)
    print("(2) cube position estimated with error (Gaussian, per axis)")
    blind_rates = {}
    for sigma in (0.005, 0.010, 0.015):
        blind = [run_episode(s[:2], s[2], sigma, check=False, rng=np.random.default_rng([SEED, i])) for i, s in enumerate(states)]
        checked = [run_episode(s[:2], s[2], sigma, check=True, retries=1, rng=np.random.default_rng([SEED, i])) for i, s in enumerate(states)]
        report(f"sigma {1000 * sigma:.0f} mm, blind", blind, states)
        report(f"sigma {1000 * sigma:.0f} mm, contact check + 1 retry", checked, states)
        print(f"      retries used: {sum(a > 1 for _, a, _ in checked)} episodes")
        gains = sum(c[0] == "success" and b[0] != "success" for b, c in zip(blind, checked))
        losses = sum(b[0] == "success" and c[0] != "success" for b, c in zip(blind, checked))
        print(f"      paired: checked succeeded where blind failed on {gains} states, the reverse on {losses}; "
              f"exact sign test p = {sign_test(gains, losses):.2g}")
        blind_rates[sigma] = sum(o == "success" for o, _, _ in blind) / len(blind)
    print("(3) capture region at cube (0.50, -0.10), yaw 0, blind, fixed position error")
    clean = capture_region(np.array([0.50, -0.10]))
    t_close, t_across = clean["along the closing axis"], clean["across the closing axis"]
    print(f"  clean capture half-widths: {t_close} mm along, {t_across} mm across the closing axis")
    print("  predicted blind success P(|e_along| <= t_along) P(|e_across| <= t_across) vs measured in (2)")
    for sigma, measured in blind_rates.items():
        p = two_sided(t_close / 1000, sigma) * two_sided(t_across / 1000, sigma)
        print(f"    sigma {1000 * sigma:.0f} mm: predicted {p:.2f}, measured {measured:.2f}")
