Thirteen broken simulations, each presented the same way: **symptom, diagnosis, root cause, fix, general lesson**. Ten are broken models you can open in the playground; three are bugs in code. Try each one before unfolding its answer. Every case is checked by the course's test suite: `tests/test_broken_models.py` asserts that each broken model shows its symptom and that the fix described here removes it, and `examples/clinic_code_bugs.py` reproduces the three code bugs.

## A triage procedure

Before the cases, the order in which to look, cheapest first:

1. **Read MuJoCo's warnings.** `data.warning[i].number` counts every warning type; a non-zero bad-acceleration count means MuJoCo already reset your state at least once.
2. **Print the model you actually have.** Sizes (`nq`, `nv`, `nu`), joint ranges (in radians), masses, `opt.timestep`, `opt.integrator`. Many bugs are a unit or a default you did not expect.
3. **Look at the scene with overlays.** Joint axes, body frames, contact points and forces show most geometric bugs in seconds.
4. **Check conservation.** In a situation where something should be conserved (energy without damping, momentum without external forces), measure it.
5. **Shrink the timestep.** If the behaviour changes, the problem is numerical; if it does not, it is in the model or your code.
6. **Reduce the scene.** Remove everything that is not needed to show the symptom.

## Models

```debug
{"title": "Case 1: the box falls through the floor", "model": "broken_fall_through",
 "symptom": "A box released half a metre above a plane passes straight through it and keeps falling. No warning is printed.",
 "diagnosis": "Turn on contact drawing: there are no contacts at all, so this is not a contact that failed, it is a contact that was never generated. Print <code>model.geom_contype</code> and <code>model.geom_conaffinity</code>.",
 "cause": "The floor has <code>contype=\"2\" conaffinity=\"2\"</code>; the box has the defaults, 1 and 1. MuJoCo generates a contact between two geoms only if <code>contype</code> of one shares a bit with <code>conaffinity</code> of the other. 2 and 1 share no bit, so the pair is filtered out before collision detection.",
 "fix": "Remove the two attributes from the floor (or give the box a matching bit). The test checks that the box then rests at z = 0.05 m.",
 "lesson": "Collision filtering is silent. When something passes through something else with no contact listed, check the bitmasks before the solver settings (Level 9.1)."}
```

```debug
{"title": "Case 2: the arm explodes", "model": "broken_explode",
 "symptom": "A two-link arm with springy joints flies apart within a fraction of a second, MuJoCo prints <code>Nan, Inf or huge value in QACC</code>, and the state resets.",
 "diagnosis": "The links weigh 50 g and the joint springs have stiffness 2000 N m/rad, so the natural frequency is high: with a link inertia of about 0.0015 kg m² about its joint, $\\omega \\approx \\sqrt{2000/0.0015} \\approx 1150$ rad/s. The timestep is 10 ms.",
 "cause": "Explicit integration of a spring is stable only for $h < 2/\\omega \\approx 1.7$ ms (Lesson 1.3). At 10 ms each step amplifies the error.",
 "fix": "Either use a timestep below the limit (the test uses 0.5 ms) or switch to <code>integrator=\"discrete\"</code>, which treats joint stiffness implicitly and is stable at 10 ms. Both pass the test.",
 "lesson": "Stiffness, mass and timestep belong together. When a model explodes, compute $2/\\omega$ for its stiffest, lightest part before touching anything else."}
```

```debug
{"title": "Case 3: the elbow will not bend", "model": "broken_degrees",
 "symptom": "A motor applies 2 N m to the elbow for a full second. The elbow moves about 0.06 rad and stops.",
 "diagnosis": "Print <code>model.jnt_range</code>: the elbow's range is [0, 0.0436] rad, not [0, 2.5] rad.",
 "cause": "The file has no <code>&lt;compiler angle=\"radian\"/&gt;</code>, so MJCF reads angles in degrees: <code>range=\"0 2.5\"</code> means 0 to 2.5 degrees. The joint limit (itself a soft constraint) lets the joint overshoot slightly under load, which is why it reaches 0.06 rad rather than 0.044.",
 "fix": "Add <code>&lt;compiler angle=\"radian\"/&gt;</code>. The elbow then swings past 1 rad under the same torque.",
 "lesson": "State the angle unit in every model you write, even when it is the default (Lesson 2.1)."}
```

```debug
{"title": "Case 4: the grasp slips", "model": "broken_weak_grip",
 "symptom": "The gripper closes on a 0.4 kg cube and lifts slowly, and the cube slides out and stays on the floor. The same gripper lifts the course's 0.1 kg cube easily.",
 "diagnosis": "Estimate the friction budget: each finger squeezes with about 8 N (servo stiffness 800 N/m times a 2 cm closing error, split over two fingers), so two contacts can carry $2\\mu \\times 8$ N. With the pads' $\\mu = 1.5$ that is 24 N, far above the cube's 3.9 N weight. Yet it slips. Print the friction of an active contact: <code>data.contact[i].friction</code>.",
 "cause": "The contact uses $\\mu = 0.15$, the cube's value, not the pads'. The cube geom has <code>priority=\"2\"</code>, higher than the pads' 1, and when priorities differ MuJoCo uses the higher-priority geom's friction coefficients and condim (with equal priorities it would take the element-wise maximum; margins and gaps are summed regardless). With $\\mu = 0.15$ the budget is 2.4 N, less than the weight.",
 "fix": "Remove <code>priority=\"2\"</code> from the cube. The pads' friction then applies and the cube lifts (the test checks it rises above 0.25 m).",
 "lesson": "Contact parameters belong to pairs, not geoms. Check which geom wins (priority, then solmix) before tuning either (Level 9.2)."}
```

```debug
{"title": "Case 5: gravity does nothing to the forearm", "model": "broken_wrong_axis",
 "symptom": "A horizontal forearm on a hinge is released and stays horizontal.",
 "diagnosis": "Turn on joint axes. The hinge axis points straight up.",
 "cause": "<code>axis=\"0 0 1\"</code>: the forearm rotates about the vertical, and gravity, which acts vertically, has no lever arm about a vertical axis.",
 "fix": "<code>axis=\"0 1 0\"</code>, a horizontal axis perpendicular to the forearm. It then swings down.",
 "lesson": "Joint axes are in the body's frame and are easiest to check by looking (Lesson 2.1)."}
```

```debug
{"title": "Case 6: the camera image is upside down", "model": "broken_upside_down_camera",
 "symptom": "Images rendered from the camera <code>front</code> show the floor at the top.",
 "diagnosis": "Print the camera's world axes: <code>data.cam_xmat[0].reshape(3, 3)</code>. Its second column, the image's up direction, is (0, 0, -1).",
 "cause": "<code>xyaxes=\"0 -1 0 0 0 -1\"</code> sets the camera's x axis to -y and its y axis to -z. The view direction (the camera's -z) is correct, so the camera looks at the scene, but rotated 180 degrees about the line of sight.",
 "fix": "<code>xyaxes=\"0 1 0 0 0 1\"</code>. MuJoCo cameras look along their -z axis with +y up; $x \\times y$ must point away from the scene.",
 "lesson": "Check a camera with its axes, not with an image (Lesson 11.1)."}
```

```debug
{"title": "Case 7: a fast ball passes through a shelf", "model": "broken_tunneling",
 "symptom": "A 1 cm ball dropped at 8 m/s onto a 6 mm shelf passes through it and lands on the floor. Halving, even tenfold reducing, the timestep does not help, nor does a shelf ten times thicker.",
 "diagnosis": "Count contacts during the fall: there are some. This is not tunneling (a collision missed between steps); MuJoCo saw the contact.",
 "cause": "The default contact has a 20 ms time constant. A soft contact hit at speed $v_0$ sinks roughly $v_0/(e\\,\\omega)$ with $\\omega \\approx 1/\\tau$: about 6 cm at 8 m/s, more than the shelf's half-thickness plus the ball's radius. Once the ball's centre passes the shelf's mid-plane, the contact normal flips and pushes it out the far side.",
 "fix": "Stiffen the contact: <code>solref=\"0.002 1\"</code> on the geoms. MuJoCo will not let a time constant drop below twice the timestep (<code>refsafe</code>), so the timestep must go down too: 1 ms. Together they hold the ball on the shelf; either alone does not (the test checks all three cases).",
 "lesson": "Soft contacts have a speed limit set by their time constant. Fast impacts on thin objects need stiffer contacts, and stiffer contacts need smaller timesteps (Level 9.2, 9.4)."}
```

```debug
{"title": "Case 8: the servo cannot hold the arm up", "model": "broken_sagging_servo",
 "symptom": "A 2 kg, 0.5 m arm under a position servo commanded to 0 rad (horizontal) hangs far below horizontal.",
 "diagnosis": "Read the gains: <code>model.actuator_gainprm[0, 0]</code> is 1. The gravity torque at horizontal is $m g L/2 = 2 \\times 9.81 \\times 0.25 = 4.9$ N m.",
 "cause": "The <code>position</code> actuator's default <code>kp</code> is 1 N m/rad. To hold 4.9 N m it would need a 4.9 rad error.",
 "fix": "Set the gains for the load: <code>kp=\"500\" kv=\"20\"</code> gives a steady sag of about $4.9/500 \\approx 0.01$ rad. Gravity compensation (the body's <code>gravcomp</code> attribute, or adding <code>qfrc_bias</code> in a torque controller) removes it entirely.",
 "lesson": "A P controller under a constant load has steady-state error load/kp. Compute the load before choosing gains (Level 8.1)."}
```

```debug
{"title": "Case 9: the box lies on its side", "model": "broken_xyzw_quat",
 "symptom": "A box meant to be yawed 90 degrees about z appears tipped onto its side.",
 "diagnosis": "Read <code>quat=\"0 0 0.7071068 0.7071068\"</code> as MuJoCo does: w = 0, which is a 180-degree rotation, about the axis (0, 0.707, 0.707).",
 "cause": "The author wrote a 90-degree rotation about z in (x, y, z, w) order, as SciPy and three.js print quaternions. MuJoCo reads (w, x, y, z).",
 "fix": "<code>quat=\"0.7071068 0 0 0.7071068\"</code>, or the unambiguous <code>euler=\"0 0 1.5707963\"</code> with radians.",
 "lesson": "Every quaternion that crosses a library boundary needs its order checked (Lesson 4.1)."}
```

```debug
{"title": "Case 10: the servo oscillates forever", "model": "broken_undamped_servo",
 "symptom": "A servo commanded to 0.5 rad overshoots and keeps oscillating around the target with constant amplitude.",
 "diagnosis": "Read <code>actuator_biasprm[0, 2]</code>: the velocity term $-k_v$ is zero. There is no joint damping and no gravity.",
 "cause": "A position actuator with <code>kp</code> but no <code>kv</code> is a pure spring. With no damping anywhere, a spring oscillates without decay.",
 "fix": "Add damping: for critical damping $k_v = 2\\sqrt{k_p I}$. Here $I = m L^2/3 = 0.167$ kg m², so <code>kv=\"11.5\"</code>; the test checks it settles within 0.01 rad. MuJoCo can compute this for you: the position actuator also accepts <code>dampratio</code>.",
 "lesson": "Every spring needs a damper; the damping ratio, not the gain, decides overshoot (Level 8.1)."}
```

## Code

The last three cases live in Python, where most bugs live. All three are reproduced by `examples/clinic_code_bugs.py`:

```python file=examples/clinic_code_bugs.py
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
```
Output:

```text
bug 1, stale observation after reset:
  ee position returned by reset: without mj_forward [ 0.3515 -0.      0.0203], with mj_forward [0.5562 0.     0.3042]; error 350.0 mm
bug 2, observation and action logged one step apart:
  observation logged before the step: replay error 0.0e+00
  observation logged after the step:  replay error 3.0e-02
bug 3, hard-coded indices after the scene changes:
  original scene                   qpos[3] = +1.6000   data.joint('j4').qpos = +1.6000
  one extra object declared first  qpos[3] = +1.0000   data.joint('j4').qpos = +1.6000
```

```debug
{"title": "Case 11: the first observation of every episode is wrong",
 "symptom": "A reinforcement-learning agent learns, but its first action in each episode is erratic. The environment's <code>reset()</code> returns an end-effector position 350 mm from where the arm actually is.",
 "diagnosis": "Compare the observation <code>reset()</code> returns with the same quantity after an explicit <code>mj_forward</code>.",
 "cause": "<code>reset()</code> writes <code>qpos</code> and reads <code>site_xpos</code>, which is computed by forward kinematics. Without <code>mj_forward</code> it still holds the pose from the end of the previous episode.",
 "fix": "Call <code>mujoco.mj_forward(model, data)</code> after setting the state in <code>reset()</code>, before building the observation.",
 "lesson": "Any time you write state yourself, recompute derived quantities before reading them (Lesson 1.1)."}
```

```debug
{"title": "Case 12: a cloned policy works in training and fails in closed loop",
 "symptom": "A behaviour-cloning policy reaches a low validation loss on logged data and performs poorly when run on the robot or in simulation.",
 "diagnosis": "Replay the log: start from the first logged state, apply the logged actions one by one, and compare the resulting states with the logged ones. A correct log replays exactly (error 0.0 here); this one does not (error 0.03).",
 "cause": "The logger recorded the observation after <code>mj_step</code> next to the action that produced it, so each pair is (state after the action, action). The policy learned to predict the action from its own consequence, which is information it never has when it acts.",
 "fix": "Record the observation before applying the action. Add the replay test to the data pipeline so the error cannot return.",
 "lesson": "Time-alignment bugs are invisible in loss curves. A replay test catches them in one line (Level 14)."}
```

```debug
{"title": "Case 13: the observation changed meaning",
 "symptom": "A policy that worked yesterday fails after a colleague added one object to the scene. No error is raised.",
 "diagnosis": "Print the observation's components by name and by index side by side.",
 "cause": "The observation used <code>data.qpos[3]</code> as \"the elbow angle\". A new free object declared before the robot shifted every robot index by 7: <code>qpos[3]</code> is now the new object's quaternion $w$, 1.0, while the elbow is still at 1.6.",
 "fix": "Build observations by name (<code>data.joint('j4').qpos</code>), or compute indices from <code>model.jnt_qposadr</code> once at construction, and assert the observation layout in a test.",
 "lesson": "Hard-coded indices are latent bugs. Every scene change triggers them (Lesson 3.1)."}
```

## More cases

Further cases appear inside the lessons where their topic is taught: rendering without the far-plane mask and reading empty pixels as 80 m of depth (Lesson 3.2), stored JavaScript views going dead after an allocation (Lesson 3.4), an `arccos`-based rotation error that reports zero for real errors (Lesson 4.1), and a balance controller that only looked right until it was tested without a viewer (Lesson 3.2).
