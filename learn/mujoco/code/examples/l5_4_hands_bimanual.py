"""Lesson 5.4: one finger reused three times, two arms composed into one scene.

INPUT   hand3.xml (three-finger hand on a gantry), arm7.xml + gripper.xml (via
        mjcourse.model_builder)
PROCESS (1) show that the three fingers share every parameter through the "finger"
            default class, and that editing the class edits all of them;
        (2) grasp the ball and the can with three one-dimensional synergies, from 40
            randomized positions each;
        (3) compose the bimanual cell with MjSpec: names, counts, actuator lookup by
            name, collisions at home; then attach a second arm with a clashing prefix
OUTPUT  printed tables

Run:  python examples/l5_4_hands_bimanual.py
"""

import os

import mujoco
import numpy as np

from mjcourse import model_builder, model_path, stats

N_TRIALS = 20 if os.environ.get("MJC_FAST") == "1" else 40
OPEN = np.array([-0.3, 0.0])                   # pre-shape per finger: proximal spread out, distal straight
SYNERGIES = {                                  # closed pose per finger (proximal, distal), rad
    "whole finger (0.6, 1.0)": np.array([0.6, 1.0]),
    "distal only (0.0, 1.6)": np.array([0.0, 1.6]),
    "proximal only (1.0, 0.0)": np.array([1.0, 0.0]),
}


def finger_parameters() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("hand3")))
    print(f"  {'joint':<8}{'damping':>9}{'armature':>10}{'range (rad)':>16}{'servo kp':>10}{'tip friction':>14}")
    for f in (1, 2, 3):
        for part in ("prox", "dist"):
            j = model.joint(f"f{f}_{part}")
            a = model.actuator(f"f{f}_{part}")
            tip = model.geom(f"f{f}_tip")
            print(f"  {j.name:<8}{j.damping[0]:>9.3f}{j.armature[0]:>10.3f}{np.array2string(j.range, precision=1):>16}"
                  f"{a.gainprm[0]:>10.1f}{tip.friction[0]:>14.2f}")
    xml = model_path("hand3").read_text()
    line = '<joint type="hinge" axis="0 1 0" damping="0.02" armature="0.001"/>'
    edited = mujoco.MjModel.from_xml_string(xml.replace(line, line.replace("0.02", "0.05")))
    damping = [float(edited.joint(f"f{f}_{p}").damping[0]) for f in (1, 2, 3) for p in ("prox", "dist")]
    print(f"  edit the class in the XML, recompile: finger joint damping {damping}")

    spec = mujoco.MjSpec.from_file(str(model_path("hand3")))
    finger = spec.find_default("finger")
    finger.joint.damping[0] = 0.05                           # edit the class after parsing...
    probe = spec.worldbody.add_body(name="probe", pos=[0, 0, 1])
    probe.add_joint(finger, name="probe")                    # ...then create one new joint from it
    probe.add_geom(size=[0.01, 0, 0])
    model = spec.compile()
    damping = [float(model.joint(f"f{f}_{p}").damping[0]) for f in (1, 2, 3) for p in ("prox", "dist")]
    print(f"  edit the class through MjSpec: existing finger joints {damping}, "
          f"a joint created afterwards {float(model.joint('probe').damping[0])}")


def grasp(closed: np.ndarray, obj: str, offset: np.ndarray) -> tuple[bool, np.ndarray]:
    """Pre-shape, descend over the object's nominal position, close along the synergy, lift 0.15 m."""
    model = mujoco.MjModel.from_xml_path(str(model_path("hand3")))
    data = mujoco.MjData(model)
    adr = model.jnt_qposadr[model.joint(obj).id]
    nominal = data.qpos[adr:adr + 2].copy()
    data.qpos[adr:adr + 2] = nominal + offset                # the object is off-centre by `offset`

    def run(seconds: float) -> None:
        for _ in range(round(seconds / model.opt.timestep)):
            mujoco.mj_step(model, data)

    data.ctrl[0:2] = nominal                                 # the hand aims at the nominal position
    data.ctrl[3:9] = np.tile(OPEN, 3)
    run(0.6)
    for k in range(100):
        data.ctrl[2] = -0.18 * (k + 1) / 100
        run(0.01)
    run(0.3)
    for k in range(100):                                     # one scalar s: 0 = pre-shape, 1 = closed
        s = (k + 1) / 100
        data.ctrl[3:9] = np.tile(OPEN + s * (closed - OPEN), 3)
        run(0.01)
    run(0.5)
    touch = data.sensordata[3:6].copy()
    z0 = data.xpos[model.body(obj).id][2]
    for k in range(100):
        data.ctrl[2] = -0.18 + 0.15 * (k + 1) / 100
        run(0.01)
    run(1.0)
    return bool(data.xpos[model.body(obj).id][2] - z0 > 0.12), touch


def synergies() -> None:
    rng = np.random.default_rng(5)
    offsets = rng.uniform(-0.015, 0.015, size=(N_TRIALS, 2))
    ok, touch = grasp(SYNERGIES["whole finger (0.6, 1.0)"], "ball", np.zeros(2))
    print(f"  centred ball, whole-finger synergy: lifted {ok}, fingertip touch forces {np.round(touch, 2)} N")
    print(f"  {N_TRIALS} positions with the object off-centre by up to 15 mm in x and y:")
    for name, closed in SYNERGIES.items():
        cells = []
        for obj in ("ball", "can"):
            wins = sum(grasp(closed, obj, off)[0] for off in offsets)
            lo, hi = stats.wilson_interval(wins, N_TRIALS)
            cells.append(f"{obj} {wins:2d}/{N_TRIALS} [{lo:.2f}, {hi:.2f}]")
        print(f"    {name:<26} {'   '.join(cells)}")
    print("  (success: lifted by more than 12 cm with the palm's 15 cm lift; 95% Wilson intervals)")
    xs = (-0.015, -0.012, -0.009, -0.006, 0.006, 0.009, 0.012, 0.015)
    print(f"  ball offset along x only (finger 1 sits at +x), offsets {[round(1000 * x) for x in xs]} mm:")
    for name, closed in SYNERGIES.items():
        row = "".join("+" if grasp(closed, "ball", np.array([x, 0.0]))[0] else "." for x in xs)
        print(f"    {name:<26} {row}   (+ lifted, . lost)")


def bimanual() -> None:
    spec = model_builder.build_bimanual()
    model = spec.compile()
    data = mujoco.MjData(model)
    print(f"  bodies {model.nbody}, joints {model.njnt}, actuators {model.nu}, nq {model.nq}, nv {model.nv}")
    print(f"  actuators: {[model.actuator(i).name for i in range(model.nu)]}")
    left = model.actuator("left/gripper/grip").id
    right = model.actuator("right/gripper/grip").id
    print(f"  the two gripper commands by name: ctrl[{left}] and ctrl[{right}]")
    mujoco.mj_resetDataKeyframe(model, data, model.key("home").id)
    mujoco.mj_forward(model, data)
    pairs = sorted({" / ".join(sorted((model.geom(c.geom1).name, model.geom(c.geom2).name)))
                    for c in data.contact[:data.ncon]})
    print(f"  contacts at the home keyframe: {pairs}")

    scene = model_builder.build_bimanual()                   # attach a third arm with a prefix already in use
    extra = model_builder.build_arm7_gripper()
    frame = scene.worldbody.add_frame(name="extra_mount", pos=[1.2, 0, 0])
    try:
        frame.attach_body(extra.body("link0"), "left/", "")
        scene.compile()
        print("  a second 'left/' arm compiled (unexpected)")
    except Exception as err:                                 # MuJoCo reports the clash; record its message
        print(f"  attaching another arm with prefix 'left/': {type(err).__name__}: {str(err).splitlines()[0]}")


if __name__ == "__main__":
    print("(1) one finger definition, three fingers:")
    finger_parameters()
    print("(2) one-dimensional synergies:")
    synergies()
    print("(3) a bimanual cell from two copies of one arm:")
    bimanual()
