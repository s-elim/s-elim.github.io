"""Lesson 1.3: what the integrator choice changes, measured.

INPUT   double_pendulum.xml (conservative, chaotic) and pendulum.xml with its
        torque motor swapped for a position servo of varying stiffness and damping
PROCESS (1) energy error after 20 s for each integrator at h = 2 ms;
        (2) does a servo-held pendulum stay stable at h = 2, 10 and 20 ms?
OUTPUT  two tables; "UNSTABLE" means MuJoCo raised its bad-acceleration warning
        (and, as it always does then, reset the state)

Run:  python examples/l1_3_integrators.py
"""

import mujoco

from mjcourse import model_path

INTEGRATORS = {"Euler": 0, "RK4": 1, "implicit": 2, "implicitfast": 3, "discrete": 4}


def energy_error(integrator: int, timestep: float, seconds: float = 20.0) -> float:
    model = mujoco.MjModel.from_xml_path(str(model_path("double_pendulum")))
    model.opt.integrator, model.opt.timestep = integrator, timestep
    model.opt.enableflags |= mujoco.mjtEnableBit.mjENBL_ENERGY
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    mujoco.mj_forward(model, data)
    e0 = data.energy.sum()
    for _ in range(round(seconds / timestep)):
        mujoco.mj_step(model, data)
    return 100.0 * (data.energy.sum() - e0) / abs(e0)


def servo_is_stable(kp: float, kv: float, integrator: int, timestep: float, seconds: float = 3.0) -> bool:
    xml = model_path("pendulum").read_text().replace(
        '<motor name="torque" joint="hinge" gear="1" ctrlrange="-3 3"/>',
        f'<position name="servo" joint="hinge" kp="{kp}" kv="{kv}"/>')
    model = mujoco.MjModel.from_xml_string(xml)
    model.opt.integrator, model.opt.timestep = integrator, timestep
    data = mujoco.MjData(model)
    data.qpos[0] = 1.0                        # start 1 rad away from the target 0
    for _ in range(round(seconds / timestep)):
        mujoco.mj_step(model, data)
    return data.warning[mujoco.mjtWarning.mjWARN_BADQACC].number == 0


if __name__ == "__main__":
    print("double pendulum, energy error after 20 s at h = 2 ms")
    for name, code in INTEGRATORS.items():
        print(f"  {name:<13s} {energy_error(code, 0.002):+8.2f} %")

    print("\nposition servo on the pendulum (I = 0.25 kg m^2), stable for 3 s?")
    cases = [(100, 60), (20000, 5)]
    print(f"  {'kp, kv':<14s}{'h (ms)':>7s}" + "".join(f"{n:>14s}" for n in ("Euler", "implicitfast", "discrete")))
    for kp, kv in cases:
        for h in (0.002, 0.01, 0.02):
            cells = ["stable" if servo_is_stable(kp, kv, INTEGRATORS[n], h) else "UNSTABLE"
                     for n in ("Euler", "implicitfast", "discrete")]
            print(f"  {f'{kp}, {kv}':<14s}{1000 * h:>7.0f}" + "".join(f"{c:>14s}" for c in cells))
