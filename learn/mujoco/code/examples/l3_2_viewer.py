"""Lesson 3.2: the passive viewer with your own control loop.

INPUT   cartpole.xml; a desktop session with a display (on macOS run with `mjpython`)
PROCESS open the passive viewer, balance the pole with a linear state-feedback law
        at real-time speed,
        toggle contact-point drawing every 2 s, close after 20 s or when the window closes
OUTPUT  an interactive window; the final pole angle printed at exit

Run:  python examples/l3_2_viewer.py      (mjpython on macOS)
"""
# requires: display

import time

import mujoco
import mujoco.viewer

from mjcourse import model_path


def main() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("cartpole")))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)              # pole tilted 0.15 rad
    with mujoco.viewer.launch_passive(model, data) as viewer:
        start = time.time()
        while viewer.is_running() and time.time() - start < 20:
            step_start = time.time()
            # Balance by pushing the cart. The gains are an LQR design on MuJoCo's own
            # linearization (mjd_transitionFD), derived in Level 21.4. Feedback on the cart's
            # position and velocity is needed too: feedback on the pole alone keeps it up for
            # a while, then the cart runs into the end of its rail.
            x, angle = data.qpos
            xdot, rate = data.qvel
            data.ctrl[0] = 9.81 * x + 70.0 * angle + 11.3 * xdot + 12.7 * rate
            mujoco.mj_step(model, data)
            with viewer.lock():                                # edit viewer state safely
                viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = int(data.time % 4 < 2)
            viewer.sync()                                      # push the new state to the window
            remaining = model.opt.timestep - (time.time() - step_start)
            if remaining > 0:
                time.sleep(remaining)
    print(f"final pole angle {data.joint('hinge').qpos[0]:+.4f} rad at t = {data.time:.2f} s")


if __name__ == "__main__":
    main()
