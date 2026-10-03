The final exam tests whether you can do what the course claims to teach: predict what MuJoCo will do before running it, find a fault from evidence, build a controller and a learning pipeline that meet a stated standard, and report an experiment that another researcher would accept. It has three parts. You pass when you pass all three.

| Part | What it tests | Format | Time | Pass mark |
|---|---|---|---|---|
| A | Prediction and understanding | 20 self-checking questions below | 60 min | 17 of 18 graded questions correct on the first attempt, plus both open answers matching the reference on every point |
| B | Practical skill | five tasks with measured acceptance criteria | 2 to 3 days | every criterion met |
| C | Research judgement | an experiment, a report and a defence | 1 week | at least 3 of 4 on every rubric line |

**Rules.** Open documentation: the MuJoCo docs, the changelog, the course lessons and your own notes. No course solutions (`solution.py` files) and no asking another person except where a task says so. Answer Part A before you run anything; the point is the prediction.

**Status.** Part A is live on this page. Part B tasks 1 and 2 can be taken today; tasks 3 to 5 use the acceptance criteria of Projects 4, 11 or 13, and 18, whose specifications are fixed but whose starter code and tests are not yet built (see [Projects](#/page/projects)). Part C can be taken today with the tools in [Research mode](#/page/research-mode).

## Part A: prediction and understanding

```quiz
{"id": "final-a", "title": "Final exam, part A", "questions": [
  {"kind": "mcq", "q": "A body's orientation in <code>mjData.xquat</code> is <code>[0.7071, 0, 0, 0.7071]</code>. What rotation is this?",
   "options": ["90 degrees about x", "90 degrees about z", "180 degrees about z", "It is not a unit quaternion"],
   "answer": 1,
   "explain": "<p>MuJoCo quaternions are scalar first, $(w, x, y, z)$. $w = \\cos(\\theta/2) = 0.7071$ gives $\\theta$ = 90 degrees, and the vector part points along $z$ (Lesson 4.1).</p>"},
  {"kind": "mcq", "q": "A scene has one free-floating cube and a 7-joint hinge arm with two slide-joint fingers. What are <code>nq</code> and <code>nv</code>?",
   "options": ["nq = 16, nv = 15", "nq = 15, nv = 15", "nq = 16, nv = 16", "nq = 13, nv = 15"],
   "answer": 0,
   "explain": "<p>A free joint has 7 position coordinates (3 position, 4 quaternion) and 6 velocity coordinates. Each hinge and slide joint has one of each: $nq = 7 + 7 + 2 = 16$, $nv = 6 + 7 + 2 = 15$ (Lesson 1.2).</p>"},
  {"kind": "numeric", "q": "A ball falls freely from rest for exactly 1 s under the default Euler integrator, $h$ = 2 ms, $g$ = 9.81 m/s². How many millimetres further does it fall than the exact $\\frac{1}{2} g t^2$?",
   "answer": 9.81, "tol": 0.02, "unit": "mm",
   "explain": "<p>Semi-implicit Euler updates velocity first, then position with the new velocity, so after $n$ steps $z = -g h^2 n(n+1)/2 = -\\frac12 g t^2 - \\frac12 g h t$. The extra drop is $\\frac12 \\times 9.81 \\times 0.002 \\times 1$ m = 9.81 mm. MuJoCo 3.14.0 gives 9.810 mm (Lesson 0.1).</p>"},
  {"kind": "mcq", "q": "You double the mass of a ball resting on the floor, with default contact parameters. Its steady-state penetration into the floor:",
   "options": ["doubles", "increases by a factor of the square root of 2", "stays the same", "halves"],
   "answer": 2,
   "explain": "<p><code>solref</code> specifies the contact's dynamics as a reference <em>acceleration</em>, a mass-spring-damper with unit mass. The resulting penetration depends on gravity and the contact parameters, not on the body's mass: 0.37 mm for both balls in Lesson 0.1.</p>"},
  {"kind": "numeric", "q": "A joint with inertia 0.02 kg m² is driven by a velocity actuator with <code>kv</code> = 8 N m s/rad, simulated with <code>Euler</code>. What is the largest stable timestep, in ms?",
   "answer": 5, "tol": 0.05, "unit": "ms",
   "explain": "<p>Under <code>Euler</code>, actuator damping is integrated explicitly: $h < 2I/k_v = 2 \\times 0.02 / 8$ s = 5 ms (Lesson 1.3). <code>implicitfast</code> removes the limit.</p>"},
  {"kind": "numeric", "q": "A position servo with <code>kp</code> = 400 N m/rad holds a joint of inertia 0.04 kg m², no damping. Above what timestep, in ms, does semi-implicit Euler become unstable?",
   "answer": 20, "tol": 0.1, "unit": "ms",
   "explain": "<p>$\\omega = \\sqrt{k_p / I} = 100$ rad/s, and semi-implicit Euler is stable for $h\\omega < 2$: $h$ < 20 ms (Lesson 1.3).</p>"},
  {"kind": "mcq", "q": "A floor geom has sliding friction 0.3, a box on it 0.9, both with default priority. What sliding friction does their contact use? And if the floor's <code>priority</code> is set to 1?",
   "options": ["0.6, then 0.3", "0.9, then 0.3", "0.3, then 0.9", "0.27, then 0.3"],
   "answer": 1,
   "explain": "<p>With equal priority MuJoCo takes the element-wise maximum; with unequal priority the higher-priority geom's values are used. MuJoCo 3.14.0 reports 0.9 and 0.3 for exactly this pair. The mixing rules are in the computation chapter of the documentation; Level 9 covers them.</p>"},
  {"kind": "mcq", "q": "In <code>mjData.contact[i]</code>, the contact normal (first row of <code>frame</code>) points:",
   "options": ["from geom1 towards geom2", "from geom2 towards geom1", "always upwards", "along the relative velocity"],
   "answer": 0,
   "explain": "<p>The normal points from <code>geom1</code> to <code>geom2</code>. For a ball resting on a floor plane, MuJoCo 3.14.0 lists the floor as <code>geom1</code> and gives the normal $(0, 0, 1)$. Code that assumes a fixed order breaks silently when the scene changes; check both <code>geom1</code> and <code>geom2</code> as Lesson 0.1 does.</p>"},
  {"kind": "mcq", "q": "You want to tilt a ramp gradually during a running simulation. Which is correct?",
   "options": ["Write the ramp body's <code>model.body_quat</code> each step", "Make the ramp a mocap body and write <code>data.mocap_quat</code>", "Recompile the model with a new ramp angle each step", "Apply a torque to the ramp body through <code>xfrc_applied</code>"],
   "answer": 1,
   "explain": "<p>The docs list a static body's <code>body_pos</code> and <code>body_quat</code> as unsafe to change at runtime, because derived quantities computed at compile time go stale. Mocap bodies exist for exactly this; the incline experiment in the Physics lab uses one. A torque does nothing to a static body.</p>"},
  {"kind": "mcq", "q": "A sensor is declared with <code>noise=\"0.01\"</code>. What does MuJoCo do with that value?",
   "options": ["Adds Gaussian noise with standard deviation 0.01 to <code>sensordata</code>", "Adds uniform noise in [-0.01, 0.01]", "Nothing during simulation: it is stored in the model for your own code to use", "Low-pass filters the sensor"],
   "answer": 2,
   "explain": "<p>The <code>noise</code> attribute is metadata; it does not affect <code>sensordata</code>. If you want noise, your code adds it (Lesson 2.3).</p>"},
  {"kind": "mcq", "q": "You restore <code>qpos</code>, <code>qvel</code> and <code>act</code> from a recorded step and replay the same controls. In a contact-rich scene the replay can differ from the original in the last bits, and the difference can grow. What else must you restore for a bit-exact replay?",
   "options": ["Nothing: MuJoCo is not deterministic, so bit-exact replay is impossible", "The rest of the integration state (warm-start accelerations and other fields in <code>mjSTATE_INTEGRATION</code>)", "The model's timestep", "The random seed of the renderer"],
   "answer": 1,
   "explain": "<p>MuJoCo is deterministic on the same build and hardware, but bit-exact replay needs the full integration state, which includes the solver's warm start. <code>mj_getState</code> with <code>mjSTATE_INTEGRATION</code> captures it. Lesson 1.1 measures the difference: $10^{-13}$ without the warm start, zero with it.</p>"},
  {"kind": "predict", "q": "A box with three distinct principal moments of inertia, in zero gravity, is spun about its intermediate axis with a tiny perturbation. What does it do over the next ten seconds?",
   "options": ["Keeps spinning steadily about the same axis", "Flips over periodically while its angular momentum stays fixed", "Slows down until it stops", "Drifts to spin about the axis of largest inertia and stays there"],
   "answer": 1,
   "explain": "<p>Rotation about the intermediate axis is unstable for a rigid body (the Dzhanibekov effect). Without dissipation the motion is periodic: the box flips over and back while angular momentum and, under RK4, energy are conserved. Settling into the major axis needs dissipation, which a rigid body in MuJoCo does not have (Lesson 4.2).</p>",
   "sim": {"model": "tumbling_box", "key": 0, "height": 220}},
  {"kind": "mcq", "q": "A Gymnasium episode ends because the 500-step time limit is reached while the task is unfinished. What should <code>step</code> return?",
   "options": ["terminated = True, truncated = False", "terminated = False, truncated = True", "terminated = True, truncated = True", "Either: they mean the same thing"],
   "answer": 1,
   "explain": "<p>The time limit is not part of the task's dynamics, so the episode is truncated, not terminated. A learner that bootstraps values treats the two differently; mixing them up biases the value of states near the limit.</p>"},
  {"kind": "mcq", "q": "A behaviour-cloned policy has low validation loss but drifts away from the demonstrated states in closed loop and never recovers. What does DAgger change?",
   "options": ["It adds more layers to the policy", "It collects expert labels on the states the learner's own policy visits, and retrains on them", "It weights the loss by episode return", "It replaces the expert with a reward function"],
   "answer": 1,
   "explain": "<p>Behaviour cloning trains on the expert's state distribution and is tested on the learner's. DAgger queries the expert on the learner's states, which removes that mismatch (Ross, Gordon and Bagnell, see the Reading list).</p>"},
  {"kind": "numeric", "q": "You plan to report a success rate to within plus or minus 3 percentage points at 95% confidence, and you do not know the rate in advance. How many evaluation episodes do you need?",
   "answer": 1068, "tol": 1, "unit": "episodes",
   "explain": "<p>Worst case $p = 0.5$: $n = z^2 p(1-p)/w^2 = 1.96^2 \\times 0.25 / 0.03^2$ = 1067.1, rounded up to 1068 (Research mode).</p>"},
  {"kind": "numeric", "q": "A policy succeeds in 0 of 20 evaluation episodes. What is the upper end of the 95% Wilson interval for its true success rate, in percent?",
   "answer": 16.1, "tol": 0.1, "unit": "%",
   "explain": "<p>At zero successes the Wilson upper bound is $z^2/(n + z^2) = 3.84/23.84$ = 16.1%. Zero observed successes in 20 episodes is consistent with a true rate of 1 in 6.</p>"},
  {"kind": "numeric", "q": "Task A has 100 evaluation episodes at 90% success; task B has 20 episodes at 30%. What is the per-task mean success, in percent? (The per-episode mean is 80%.)",
   "answer": 60, "tol": 0.1, "unit": "%",
   "explain": "<p>Per task: $(90 + 30)/2$ = 60%. Per episode: $(90 + 6)/120$ = 80%. Twenty points apart from the same data, which is why a paper must say which one it reports.</p>"},
  {"kind": "mcq", "q": "Method X scores 33/50 and the baseline 31/50, one training seed each, different initial states. What can you conclude?",
   "options": ["X is better by 4 points", "X is better, but only slightly", "Nothing about which is better: the 95% intervals are about [52%, 78%] and [48%, 74%], and seed variance is unmeasured", "The baseline is better, because it has less variance"],
   "answer": 2,
   "explain": "<p>The Wilson intervals overlap almost completely, one seed says nothing about training variance, and unpaired initial states add noise a paired design would remove (Research mode).</p>"},
  {"kind": "open", "q": "A paper reports 95% success on LIBERO-Spatial and claims its method generalizes to novel object positions. What do you check before accepting the claim?",
   "reference": "<p>(1) Whether the evaluation states differ from the training states at all: LIBERO's standard evaluation uses a fixed set of initial states per task, drawn from the same placement distribution as the demonstrations, so high success there is in-distribution evidence, not evidence of generalization to new positions. Look for an evaluation with perturbed positions (for example LIBERO-PRO or LIBERO-Plus, Reading list). (2) Benchmark version and suite, success definition, number of evaluation episodes per task and seeds, and whether numbers are per task or per episode. (3) Whether baselines were run under the same protocol or copied from papers with a different one. Accept the generalization claim only for the axis the evaluation actually varied.</p>"},
  {"kind": "open", "q": "A grasping policy trained in MuJoCo succeeds 92% of the time in simulation and 40% on the real robot. List the measurements you would take, in order, to locate the gap.",
   "reference": "<p>(1) Replay the same open-loop action sequence in sim and on the robot from matched states and compare joint trajectories: separates actuation and latency from everything else. (2) Measure control latency and add it to the simulation (MuJoCo's actuator <code>delay</code>), then re-evaluate. (3) Identify friction, object mass and gripper force on the real setup and compare with the model (Level 18). (4) Compare observations: real camera images and depth against rendered ones at the same state; check calibration and frames. (5) Evaluate the policy in simulation under the measured parameters and under randomization around them, and see how much of the 52 points each change recovers. Change one thing at a time, and predict each effect before measuring it.</p>"}
]}
```

## Part B: practical tasks

Each task has acceptance criteria you measure yourself. Keep the code and the logs: Part C may use them.

**B1. Diagnose three unseen faults (3 hours, with a partner).** A partner takes three course models and introduces one fault into each, from the fault classes of the [Debugging clinic](#/page/debugging-clinic): units, joint axes, quaternion order, contact parameters, actuator gains, timestep and integrator, or observation indexing. You get the broken files and a one-line symptom for each, not the diff. *Accept when* for each fault you name the root cause, show the measurement that proves it (a printed field, a plot, a test), and fix it so that a test you wrote fails before your fix and passes after it.

**B2. Pass two project test suites with your own code (half a day).** Implement `starter.py` in Projects [1](#/project/p01_pendulum) and [2](#/project/p02_cartpole) without opening `solution.py`. *Accept when* `MJC_IMPL=starter pytest projects/p01_pendulum projects/p02_cartpole` passes.

**B3. A controller that meets a specification (1 day).** Meet every acceptance criterion of Project 4 (joint PD with gravity compensation on the 7-DOF arm), with the step-response plots and the steady-state error prediction checked against measurement.

**B4. A learned policy, reported properly (1 to 2 days).** Meet the acceptance criteria of Project 11 (PPO on reach) or Project 13 (behaviour cloning and DAgger), including the evaluation protocol: held-out initial states, several seeds, and intervals.

**B5. A transfer experiment with a prediction (half a day).** Run Project 18. *Accept when* your written prediction of the transfer gap, dated before you ran the perturbed model, is in the report next to the measured gap and an explanation of the difference.

## Part C: research judgement

**The task.** Choose one question about simulation or learning that you can answer in MuJoCo within a week and that the course does not already answer. Examples of the right size: how gripper closing force changes grasp success across object masses; whether `implicitfast` at 5 ms preserves the success of a fixed policy trained at 2 ms; how much of a behaviour-cloning failure is due to action chunk length. Design the experiment with the [Research mode](#/page/research-mode) checklist, run it, and write a report of at most four pages using its reporting template.

**The defence.** Another person who has finished the course reads the report and asks three questions, at least one about a result that could have a cause other than the one you claim. You answer from your data and logs.

**Rubric** (each line scored 1 to 4; pass with at least 3 on every line):

| | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Design | the variable is confounded with another | one confound remains and is not mentioned | confounds controlled or named | paired design, seeds and states fixed, a prediction recorded before running |
| Statistics | point estimates only | intervals, but too few episodes to separate the conditions | intervals with an episode count chosen in advance | intervals, paired differences, seed variance, and both aggregation levels where they differ |
| Claims | claims beyond the data | one claim exceeds the evidence | every claim matches the evidence | claims match, and the report states what the experiment cannot show |
| Reproducibility | results cannot be rerun | rerun needs the author | a script reproduces each number | one command reproduces every number and figure, with the MuJoCo version pinned and logged |
