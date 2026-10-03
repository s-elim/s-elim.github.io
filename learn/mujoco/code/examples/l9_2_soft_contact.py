"""Lesson 9.2: the soft contact model: solref, solimp, the regularizer and the solver.

INPUT   a ball on a plane, written below (frictionless contacts where friction would
        only add rows to the comparison)
PROCESS (1) resting penetration predicted from the model's equations and measured, for
            several time constants, a constant impedance, the direct solref format and
            three masses;
        (2) MuJoCo's own constraint quantities for the resting contact: impedance d,
            stiffness k, damping b, reference acceleration, regularizer R, and the force
            (A + R)^-1 (aref - a0) against efc_force;
        (3) bounce: rebound height against the damping ratio;
        (4) refsafe: a time constant below twice the timestep is raised to 2h
OUTPUT  printed tables

Run:  python examples/l9_2_soft_contact.py
"""

import mujoco
import numpy as np

G = 9.81
BALL = """<mujoco><option timestep="{h}"/><worldbody>
  <geom name="plane" type="plane" size="1 1 .1" condim="1" solref="{plane_solref}" solimp="{plane_solimp}"/>
  <body name="ball" pos="0 0 {z}"><freejoint/>
    <geom name="ball" size="0.05" mass="{m}" condim="1" solref="{solref}" solimp="{solimp}"/></body>
</worldbody></mujoco>"""
DEFAULT_SOLIMP = "0.9 0.95 0.001 0.5 2"


def impedance(r: float, solimp: list[float]) -> float:
    """d(r) from solimp = (d0, dw, width, midpoint, power), as in MuJoCo's documentation."""
    d0, dw, width, mid, power = solimp
    x = min(abs(r) / width, 1.0)
    if x >= 1.0:
        return dw
    y = x**power / mid ** (power - 1) if x <= mid else 1 - (1 - x) ** power / (1 - mid) ** (power - 1)
    return d0 + y * (dw - d0)


def predicted_rest(a0: float, solref: list[float], solimp: list[float]) -> float:
    """Solve d k r = (1 - d) a0 for the penetration r, with k from solref and d = d(r)."""
    r = 1e-4
    for _ in range(200):                                       # fixed point; converges quickly here
        d, dw = impedance(r, solimp), solimp[1]
        if solref[0] > 0:
            tc, dr = solref
            k = d / (dw**2 * tc**2 * dr**2)
        else:
            k = -solref[0] * d / dw**2
        r = (1 - d) * a0 / (d * k)
    return r


def ball_model(solref: str, solimp: str = DEFAULT_SOLIMP, mass: float = 1.0, h: float = 0.002, z: float = 0.05,
               plane: tuple[str, str] | None = None) -> mujoco.MjModel:
    """The ball scene; the plane gets the ball's contact parameters unless `plane` says otherwise."""
    plane_solref, plane_solimp = plane if plane else (solref, solimp)
    return mujoco.MjModel.from_xml_string(BALL.format(h=h, z=z, m=mass, solref=solref, solimp=solimp,
                                                      plane_solref=plane_solref, plane_solimp=plane_solimp))


def measured_rest(solref: str, solimp: str = DEFAULT_SOLIMP, mass: float = 1.0, h: float = 0.002,
                  plane: tuple[str, str] | None = None) -> float:
    model = ball_model(solref, solimp, mass, h, plane=plane)
    data = mujoco.MjData(model)
    for _ in range(round(3.0 / h)):
        mujoco.mj_step(model, data)
    return 0.05 - data.qpos[2]


def resting_penetration() -> None:
    print(f"  {'solref':<14}{'solimp':<22}{'mass (kg)':>10}{'predicted (mm)':>16}{'measured (mm)':>15}")
    cases = [("0.02 1", DEFAULT_SOLIMP, 1.0), ("0.01 1", DEFAULT_SOLIMP, 1.0), ("0.005 1", DEFAULT_SOLIMP, 1.0),
             ("0.02 1", "0.9 0.9 0.001 0.5 2", 1.0), ("-10000 -200", DEFAULT_SOLIMP, 1.0),
             ("0.02 1", DEFAULT_SOLIMP, 0.1), ("0.02 1", DEFAULT_SOLIMP, 10.0)]
    for solref, solimp, mass in cases:
        pred = predicted_rest(G, [float(v) for v in solref.split()], [float(v) for v in solimp.split()])
        meas = measured_rest(solref, solimp, mass)
        print(f"  {solref:<14}{solimp:<22}{mass:>10g}{1000 * pred:>16.4f}{1000 * meas:>15.4f}")
    # Mixing: ball 0.01 1, plane left at the default 0.02 1. Equal solmix: the contact uses the average.
    pred = predicted_rest(G, [0.015, 1.0], [0.9, 0.95, 0.001, 0.5, 2])
    meas = measured_rest("0.01 1", plane=("0.02 1", DEFAULT_SOLIMP))
    print(f"  ball 0.01 1 on a plane with the default 0.02 1: contact uses the average 0.015 1 -> "
          f"predicted {1000 * pred:.4f} mm, measured {1000 * meas:.4f} mm")


def internals() -> None:
    model = ball_model("0.02 1")
    data = mujoco.MjData(model)
    for _ in range(1500):
        mujoco.mj_step(model, data)
    mujoco.mj_forward(model, data)
    k, b, d, _ = data.efc_KBIP[0]
    r, v = data.efc_pos[0] - data.efc_margin[0], data.efc_vel[0]
    contact = data.contact[0]
    jacp = np.zeros((3, model.nv))
    mujoco.mj_jac(model, data, jacp, None, contact.pos, model.body("ball").id)
    jac = (contact.frame[:3] @ jacp).reshape(1, model.nv)      # normal row: the ball's velocity along the normal
    mass = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, mass)
    a_row = (jac @ np.linalg.solve(mass, jac.T)).item()        # A = J M^-1 J^T for this row
    a0 = (jac @ np.linalg.solve(mass, -data.qfrc_bias)).item()  # unconstrained acceleration along the normal
    f_formula = (data.efc_aref[0] - a0) / (a_row + data.efc_R[0])
    print(f"  residual r = {1000 * r:.4f} mm (negative: penetrating), velocity {v:.1e} m/s")
    print(f"  impedance d = {d:.5f}; d(r) from solimp = {impedance(r, [0.9, 0.95, 0.001, 0.5, 2]):.5f}")
    print(f"  efc_KBIP stiffness {k:.1f} = 1 / (dw^2 tc^2 dr^2) = {1 / (0.95**2 * 0.02**2):.1f}; the documentation's k = d * that = {d * k:.1f}")
    print(f"  efc_KBIP damping {b:.4f} = 2 / (dw tc) = {2 / (0.95 * 0.02):.4f}")
    print(f"  aref = {data.efc_aref[0]:.5f} m/s^2; -b v - d k r = {-b * v - d * k * r:.5f}")
    print(f"  R = {data.efc_R[0]:.6f}, (1 - d) / d * A_hat with A_hat = 1/m = 1: {(1 - d) / d:.6f}; A from J M^-1 J^T = {a_row:.6f}")
    print(f"  constraint force (A + R)^-1 (aref - a0) = {f_formula:.5f} N, efc_force = {data.efc_force[0]:.5f} N, weight m g = {G:.5f} N")


def bounce() -> None:
    print(f"  {'solref':<16}{'rebound / drop height':>22}")
    for solref in ("0.02 1", "0.02 0.5", "0.02 0.2", "0.02 0.1", "-10000 0"):
        model = ball_model(solref, h=0.0005, z=0.35)
        data = mujoco.MjData(model)
        peak, falling, contacted = 0.0, True, False
        for _ in range(round(1.5 / model.opt.timestep)):
            mujoco.mj_step(model, data)
            contacted |= data.ncon > 0
            if contacted and data.qvel[2] > 0:
                falling = False
            if not falling:
                peak = max(peak, data.qpos[2])
                if data.qvel[2] < 0:
                    break
        print(f"  {solref:<16}{(peak - 0.05) / 0.30:>22.3f}")


def refsafe() -> None:
    h = 0.002
    for solref in ("0.002 1", "0.004 1"):
        print(f"  timestep {h} s, solref {solref}: resting penetration {1000 * measured_rest(solref, h=h):.4f} mm")
    model = ball_model("0.002 1", h=h)
    model.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_REFSAFE
    data = mujoco.MjData(model)
    for _ in range(1500):
        mujoco.mj_step(model, data)
    print(f"  solref 0.002 1 with refsafe disabled: after 3 s the ball's centre is {data.qpos[2]:.3f} m high "
          f"(it started resting at 0.05 m): the contact is too stiff for the step and throws it into the air")


if __name__ == "__main__":
    print("(1) resting penetration of a ball on a plane (frictionless contact), predicted and measured")
    resting_penetration()
    print("(2) MuJoCo's constraint quantities for the resting contact (solref 0.02 1, default solimp)")
    internals()
    print("(3) drop from 30 cm: rebound height by damping ratio (timestep 0.5 ms)")
    bounce()
    print("(4) refsafe: time constants below 2 h")
    refsafe()
