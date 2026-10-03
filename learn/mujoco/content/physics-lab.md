Twelve experiments, one per physical idea, each running MuJoCo 3.14.0 in this page. Every one starts with a question. Write your prediction down before pressing Play, then explain any difference between what you predicted and what happened; the lesson that covers the idea is linked under each experiment.

## 1. Gravity and mass

Two balls, 2 kg and 0.1 kg, released together. Does the heavy one land first? What changes if gravity is halved? If the light ball becomes 5 kg?

```lab simlab
{"title": "Gravity and mass", "model": "ball_drop", "height": 220,
 "camera": {"azimuth": -90, "elevation": 6, "distance": 2.3, "target": [0, 0, 0.5]},
 "controls": [
   {"label": "gravity, z component", "unit": "m/s^2", "set": "model.opt.gravity[2]", "min": -20, "max": 0, "step": 0.01, "value": -9.81, "digits": 2},
   {"label": "mass of the blue ball", "unit": "kg", "apply": "model.body_mass[2] = value; mj.mj_setConst(model, data)", "min": 0.01, "max": 5, "step": 0.01, "value": 0.1, "digits": 2}],
 "plots": [{"ylabel": "centre height (m)", "window": 1.5, "ymin": 0, "ymax": 1.05, "traces": [{"label": "orange, 2 kg", "expr": "data.qpos[2]"}, {"label": "blue", "expr": "data.qpos[9]", "dash": true}]}]}
```

Covered in [Lesson 0.1](#/lesson/0.1).

## 2. Friction on a slope

A block of friction coefficient 0.4 rests on a ramp. Coulomb's law says it slides when the slope's tangent exceeds the coefficient: above 21.8 degrees. Set the angle just below and just above, and the friction coefficient, and check. Then watch closely below the threshold: does it stay perfectly still?

```lab simlab
{"title": "Friction on a slope", "model": "incline", "height": 230,
 "camera": {"azimuth": -90, "elevation": 8, "distance": 1.4, "target": [0, 0, 0.25]},
 "controls": [
   {"label": "slope angle", "unit": "deg", "init": true, "reset": true, "min": 0, "max": 40, "step": 0.5, "value": 15, "digits": 1,
    "apply": "const a = value * Math.PI / 180; data.mocap_quat.set([Math.cos(a / 2), 0, Math.sin(a / 2), 0], 0); data.qpos.set([data.mocap_pos[0] + 0.04 * Math.sin(a), data.mocap_pos[1], data.mocap_pos[2] + 0.04 * Math.cos(a), Math.cos(a / 2), 0, Math.sin(a / 2), 0], 0); data.qvel.fill(0); ctx.angle = a"},
   {"label": "friction coefficient (ramp and block)", "apply": "model.geom_friction[3] = value; model.geom_friction[6] = value; ctx.mu = value", "min": 0.05, "max": 1.2, "step": 0.01, "value": 0.4, "digits": 2}],
 "readouts": [
   {"label": "tan(angle)", "expr": "Math.tan(ctx.angle || 0)", "digits": 3},
   {"label": "friction coefficient", "expr": "ctx.mu", "digits": 3},
   {"label": "Coulomb says", "expr": "Math.tan(ctx.angle || 0) > ctx.mu ? 'slides' : 'holds'"},
   {"label": "speed along slope (mm/s)", "expr": "1000 * Math.hypot(data.qvel[0], data.qvel[1], data.qvel[2])", "digits": 3}],
 "plots": [{"ylabel": "block speed (mm/s)", "window": 5, "traces": [{"label": "speed (mm/s)", "expr": "1000 * Math.hypot(data.qvel[0], data.qvel[1], data.qvel[2])"}]}],
 "note": "Changing the angle re-places the block at rest on the tilted ramp. Below the threshold, the speed is tiny but not zero: MuJoCo's friction is regularized and allows slow slip (Lesson 0.3 measures it)."}
```

Covered in [Lesson 0.3](#/lesson/0.3); Level 9 derives the friction model.

## 3. Damping and energy

The pendulum swings from horizontal. With no damping, does its energy stay constant in this simulation? Add damping: does the energy decay exponentially, linearly, or neither?

```lab simlab
{"title": "Damping and energy", "model": "pendulum", "key": 0, "height": 220,
 "camera": {"azimuth": -90, "elevation": 5, "distance": 1.8, "target": [0, 0, 0.75]},
 "controls": [{"label": "joint damping", "unit": "N m s/rad", "set": "model.dof_damping[0]", "min": 0, "max": 0.5, "step": 0.005, "value": 0, "digits": 3}],
 "readouts": [{"label": "energy (J)", "expr": "lib.energy().total", "digits": 5}],
 "plots": [{"ylabel": "energy (J)", "window": 10, "traces": [{"label": "kinetic + potential (J)", "expr": "lib.energy().total"}]},
           {"ylabel": "angle (rad)", "window": 10, "traces": [{"label": "q (rad)", "expr": "data.qpos[0]"}]}]}
```

Covered in [Lesson 1.3](#/lesson/1.3).

## 4. Elasticity and collisions

Two balls collide in zero gravity. Which settings make the collision elastic? Is momentum conserved even when energy is not?

```lab simlab
{"title": "Elasticity and momentum", "model": "two_balls", "key": 0, "height": 200,
 "camera": {"azimuth": -90, "elevation": 5, "distance": 1.5, "target": [0, 0, 0.3]},
 "controls": [{"label": "contact damping ratio", "apply": "model.geom_solref[1] = value; model.geom_solref[3] = value", "min": 0.02, "max": 1.0, "step": 0.01, "value": 0.2, "digits": 2, "reset": true}],
 "readouts": [
   {"label": "total momentum (kg m/s)", "expr": "model.body_mass[1] * data.qvel[0] + model.body_mass[2] * data.qvel[6]", "digits": 6},
   {"label": "kinetic energy (J)", "expr": "0.5 * model.body_mass[1] * data.qvel[0] ** 2 + 0.5 * model.body_mass[2] * data.qvel[6] ** 2", "digits": 4}],
 "plots": [{"ylabel": "velocity (m/s)", "window": 1.2, "traces": [{"label": "orange (m/s)", "expr": "data.qvel[0]"}, {"label": "blue (m/s)", "expr": "data.qvel[6]"}]}]}
```

Covered in [Lesson 4.3](#/lesson/4.3).

## 5. Contact stiffness and penetration

A cube lands on a table. Soft contacts let it sink slightly. Make the contact softer (larger time constant): how deep does it rest, and how deep does it go at impact?

```lab simlab
{"title": "Contact softness", "model": "cube_table", "height": 220,
 "camera": {"azimuth": -70, "elevation": 12, "distance": 1.0, "target": [0, 0, 0.05]},
 "toggles": ["contacts", "forces"], "overlays": {"contacts": true, "forces": true}, "forceScale": 0.01,
 "controls": [{"label": "contact time constant (both cubes and floor)", "unit": "s", "apply": "for (let g = 0; g < model.ngeom; g++) model.geom_solref[2 * g] = value", "min": 0.004, "max": 0.2, "step": 0.002, "value": 0.02, "digits": 3, "reset": true}],
 "readouts": [
   {"label": "dropped cube penetration (mm)", "expr": "1000 * (0.04 - data.qpos[2])", "digits": 3},
   {"label": "resting cube penetration (mm)", "expr": "1000 * (0.04 - data.qpos[9])", "digits": 3},
   {"label": "contacts", "expr": "data.ncon", "digits": 0}],
 "plots": [{"ylabel": "penetration (mm)", "window": 3, "traces": [{"label": "dropped cube (mm)", "expr": "1000 * (0.04 - data.qpos[2])"}, {"label": "resting cube (mm)", "expr": "1000 * (0.04 - data.qpos[9])", "dash": true}]}],
 "note": "Penetration here is 40 mm minus the cube centre's height, which is exact for a cube lying flat. While the dropped cube tumbles, the number is meaningless; read it once the cube is at rest."}
```

Level 9.2 derives the relation between the time constant and the penetration.

## 6. Torque and angular acceleration

A constant torque on the pendulum. Its angular acceleration at the bottom of the swing is torque over the moment of inertia about the pivot, 0.2501 kg m². Set a torque and compare.

```lab simlab
{"title": "Torque", "model": "pendulum", "height": 220,
 "camera": {"azimuth": -90, "elevation": 5, "distance": 1.8, "target": [0, 0, 0.75]},
 "controls": [{"label": "motor torque", "unit": "N m", "param": "tau", "min": -3, "max": 3, "step": 0.05, "value": 1.0, "digits": 2}],
 "controller": "data.ctrl[0] = ctx.tau",
 "readouts": [
   {"label": "qacc (rad/s^2)", "expr": "data.qacc[0]", "digits": 4},
   {"label": "torque / I_pivot (rad/s^2)", "expr": "ctx.tau / 0.2501", "digits": 4},
   {"label": "angle (rad)", "expr": "data.qpos[0]", "digits": 3}],
 "note": "The two numbers agree only at q = 0, where gravity has no lever arm. Away from the bottom, qacc includes the gravity torque -m g L sin(q)."}
```

## 7. Angular momentum and gyroscopic motion

A box spun about its intermediate principal axis flips end over end while its angular momentum stays fixed. Spin it about the other two axes: does it flip?

```lab simlab
{"title": "Spin stability", "model": "tumbling_box", "key": 0, "height": 220,
 "camera": {"azimuth": -70, "elevation": 20, "distance": 0.8, "target": [0, 0, 0.5]},
 "controls": [
   {"type": "button", "label": "Spin about x", "run": "mj.mj_resetData(model, data); data.qvel[3] = 6; data.qvel[4] = 0.001"},
   {"type": "button", "label": "Spin about y (intermediate)", "run": "mj.mj_resetData(model, data); data.qvel[4] = 6; data.qvel[3] = 0.001"},
   {"type": "button", "label": "Spin about z", "run": "mj.mj_resetData(model, data); data.qvel[5] = 6; data.qvel[4] = 0.001"}],
 "plots": [{"ylabel": "ω, body axes (rad/s)", "window": 10, "traces": [{"label": "wx", "expr": "data.qvel[3]"}, {"label": "wy", "expr": "data.qvel[4]"}, {"label": "wz", "expr": "data.qvel[5]"}]}]}
```

Covered in [Lesson 4.2](#/lesson/4.2).

## 8. Chaos and energy conservation

A double pendulum from a high release. Two runs from almost the same start separate within seconds. Is the energy conserved by MuJoCo's default integrator? By RK4?

```lab simlab
{"title": "Chaos", "model": "double_pendulum", "key": 0, "height": 220, "trail": "tip",
 "camera": {"azimuth": -90, "elevation": 5, "distance": 1.9, "target": [0, 0, 0.7]},
 "controls": [
   {"type": "select", "label": "integrator", "set": "model.opt.integrator", "options": [["Euler", 0], ["RK4", 1], ["implicitfast", 3]], "value": 0, "reset": true},
   {"label": "initial angle of link 1", "unit": "rad", "set": "data.qpos[0]", "init": true, "reset": true, "min": 1.5, "max": 2.5, "step": 0.0001, "value": 2.0, "digits": 4}],
 "readouts": [{"label": "energy (J)", "expr": "lib.energy().total", "digits": 5}],
 "plots": [{"ylabel": "energy (J)", "window": 20, "traces": [{"label": "total (J)", "expr": "lib.energy().total"}]}],
 "note": "Change the initial angle by 0.0001 rad and compare the trails after 10 s."}
```

Covered in [Lesson 1.3](#/lesson/1.3).

## 9. Stability of a stiff servo

A position servo holds the pendulum. Explicit integration is stable only below $h < 2/\omega$ with $\omega = \sqrt{k_p/I}$. Find the largest stable timestep for a given stiffness, then switch the integrator.

```lab simlab
{"title": "Numerical stability", "model": "pendulum_servo", "height": 200,
 "camera": {"azimuth": -90, "elevation": 5, "distance": 1.9, "target": [0, 0, 0.75]},
 "setup": "data.qpos[0] = 1.0",
 "controls": [
   {"label": "stiffness kp", "unit": "N m/rad", "apply": "model.actuator_gainprm[0] = value; model.actuator_biasprm[1] = -value", "min": 10, "max": 40000, "step": 10, "value": 5000, "digits": 0},
   {"label": "timestep h", "unit": "s", "set": "model.opt.timestep", "min": 0.001, "max": 0.02, "step": 0.001, "value": 0.002, "digits": 3, "reset": true},
   {"type": "select", "label": "integrator", "set": "model.opt.integrator", "options": [["Euler", 0], ["implicitfast", 3], ["discrete", 4]], "value": 0, "reset": true}],
 "readouts": [{"label": "explicit limit 2/w (ms)", "expr": "2000 * Math.sqrt(0.2501 / model.actuator_gainprm[0])", "digits": 2}, {"label": "angle (rad)", "expr": "data.qpos[0]", "digits": 4}]}
```

Covered in [Lesson 1.3](#/lesson/1.3).

## 10. Constraints: joint limits

The cart-pole's cart runs on a rail limited to $\pm 1.5$ m. Push it hard into the end. A joint limit is a constraint, solved like a contact: how far past the limit does the cart go at impact?

```lab simlab
{"title": "A joint limit is a soft constraint", "model": "cartpole", "height": 200,
 "camera": {"azimuth": -90, "elevation": 8, "distance": 3.2, "target": [0.5, 0, 0.6]},
 "controls": [{"label": "push force", "unit": "N", "param": "f", "min": 0, "max": 20, "step": 0.5, "value": 15, "digits": 1}],
 "controller": "data.ctrl[0] = ctx.f",
 "readouts": [{"label": "cart position (m)", "expr": "data.qpos[0]", "digits": 4}, {"label": "past the limit (mm)", "expr": "Math.max(0, 1000 * (data.qpos[0] - 1.5))", "digits": 2}],
 "plots": [{"ylabel": "cart position (m)", "window": 4, "refLines": [{"y": 1.5, "label": "limit"}], "traces": [{"label": "x (m)", "expr": "data.qpos[0]"}]}]}
```

## 11. Constraints: equality coupling

The gripper's fingers are tied by a joint equality and driven through a tendon. Close it on the cube and read both finger positions: how equal does a soft equality keep them under load?

```lab simlab
{"title": "Equality constraints", "model": "gantry_gripper", "key": 0, "height": 220, "autoplay": true,
 "camera": {"azimuth": -60, "elevation": 20, "distance": 0.9, "target": [0.1, 0, 0.2]},
 "controls": [
   {"label": "carriage z target", "unit": "m", "set": "data.ctrl[2]", "min": -0.34, "max": 0.05, "step": 0.005, "value": 0.0},
   {"label": "grip half-opening", "unit": "m", "set": "data.ctrl[3]", "min": 0, "max": 0.04, "step": 0.001, "value": 0.04}],
 "readouts": [
   {"label": "left finger (mm)", "expr": "1000 * data.qpos[3]", "digits": 3},
   {"label": "right finger (mm)", "expr": "1000 * data.qpos[4]", "digits": 3},
   {"label": "difference (um)", "expr": "1e6 * (data.qpos[3] - data.qpos[4])", "digits": 2}]}
```

Covered in [Lesson 2.3](#/lesson/2.3).

## 12. Momentum transfer in a push

A mocap pusher moves at constant speed and shoves a cube. The cube's speed depends on friction with the floor. Change the cube's friction and predict whether it keeps up with the pusher or lags behind.

```lab simlab
{"title": "Pushing", "model": "cube_table", "height": 220,
 "camera": {"azimuth": -90, "elevation": 20, "distance": 1.2, "target": [0, 0, 0.05]},
 "toggles": ["contacts", "forces"], "overlays": {"forces": true}, "forceScale": 0.02,
 "controls": [{"label": "cube friction (both cubes)", "apply": "model.geom_friction[3] = value; model.geom_friction[6] = value", "min": 0.05, "max": 1.5, "step": 0.01, "value": 0.5, "digits": 2}],
 "controller": "data.mocap_pos[0] = 0.35 - 0.1 * Math.max(0, data.time - 0.5)",
 "readouts": [
   {"label": "pusher x (m)", "expr": "data.mocap_pos[0]", "digits": 3},
   {"label": "resting cube x (m)", "expr": "data.qpos[7]", "digits": 3},
   {"label": "contact normal force on cube (N)", "expr": "lib.normalForce('rest_cube')", "digits": 2}],
 "note": "The pusher starts moving at t = 0.5 s at 0.1 m/s toward -x. The normal force readout sums all contacts on the cube, floor included."}
```

Levels 9 and 10 treat contact and pushing in depth.
