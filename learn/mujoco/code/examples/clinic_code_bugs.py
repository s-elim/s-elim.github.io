"""Debugging clinic: three bugs that live in code, not in models.

INPUT   reach.xml (arm7 with a mocap target) and pick_place.xml
PROCESS (1) a reset() that writes qpos and reads the end-effector position without
            mj_forward returns the position of the previous episode;
        (2) a logger that records the observation after mj_step next to the action
            that produced it shifts every (observation, action) pair by one step,
            which a replay test exposes;
        (3) an observation built from hard-coded qpos indices silently reads a
            different joint after one object is added to the scene
OUTPUT  each bug's effect, measured, next to the corrected version

Run:  python examples/clinic_code_bugs.py
"""

import mujoco
import numpy as np

from mjcourse import model_path


def stale_reset() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("reach")))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 1)                 # episode 1 starts at "home"
    mujoco.mj_forward(model, data)
    for _ in range(200):
        mujoco.mj_step(model, data)                             # the arm sags without control

    def reset(call_forward: bool) -> np.ndarray:
        data.qpos[:] = model.key("home").qpos                   # episode 2: back to home
        data.qvel[:] = 0
        if call_forward:
            mujoco.mj_forward(model, data)
        return data.site("ee").xpos.copy()                      # the first observation of the episode

    stale = reset(call_forward=False)
    fresh = reset(call_forward=True)
    print(f"  ee position returned by reset: without mj_forward {np.round(stale, 4)}, "
          f"with mj_forward {np.round(fresh, 4)}; error {1e3 * np.linalg.norm(stale - fresh):.1f} mm")


def misaligned_log() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("pendulum")))
    rng = np.random.default_rng(0)
    actions = rng.uniform(-3, 3, size=100)

    def record(after_step: bool) -> list[tuple[np.ndarray, float]]:
        data = mujoco.MjData(model)
        data.qpos[0] = 0.3
        log = []
        for a in actions:
            before = np.r_[data.qpos, data.qvel]
            data.ctrl[0] = a
            mujoco.mj_step(model, data)
            log.append((np.r_[data.qpos, data.qvel] if after_step else before, a))
        return log

    def replay_error(log) -> float:
        """Start from the first logged state, apply the logged actions, compare states."""
        data = mujoco.MjData(model)
        data.qpos[0], data.qvel[0] = log[0][0]
        worst = 0.0
        for state, a in log:
            worst = max(worst, float(np.max(np.abs(np.r_[data.qpos, data.qvel] - state))))
            data.ctrl[0] = a
            mujoco.mj_step(model, data)
        return worst

    print(f"  observation logged before the step: replay error {replay_error(record(False)):.1e}")
    print(f"  observation logged after the step:  replay error {replay_error(record(True)):.1e}")


def hard_coded_indices() -> None:
    xml = model_path("pick_place").read_text()
    extra = ('<body name="extra" pos="0.3 -0.4 0.02"><freejoint/><geom type="sphere" size="0.02"/></body>\n'
             '    <attach model="arm" body="link0" prefix=""/>')
    tmp = model_path("pick_place").parent / "_clinic_tmp.xml"   # next to the original, so attachments resolve
    for label, scene in (("original scene", xml),
                         ("one extra object declared first", xml.replace('<attach model="arm" body="link0" prefix=""/>', extra))):
        tmp.write_text(scene)
        try:
            model = mujoco.MjModel.from_xml_path(str(tmp))
        finally:
            tmp.unlink()
        data = mujoco.MjData(model)
        mujoco.mj_resetDataKeyframe(model, data, model.key("home").id)
        by_index = data.qpos[3]                                  # "the elbow angle", written as index 3
        by_name = data.joint("j4").qpos[0]
        print(f"  {label:<32s} qpos[3] = {by_index:+.4f}   data.joint('j4').qpos = {by_name:+.4f}")


if __name__ == "__main__":
    print("bug 1, stale observation after reset:")
    stale_reset()
    print("bug 2, observation and action logged one step apart:")
    misaligned_log()
    print("bug 3, hard-coded indices after the scene changes:")
    hard_coded_indices()
