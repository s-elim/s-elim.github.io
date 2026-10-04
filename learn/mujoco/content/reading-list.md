A reading track that runs alongside the levels. Every entry was checked against its arXiv record or its Crossref DOI record (on 2026-10-03; the manipulation section and later additions on 2026-10-04): title, first author and year below are as those records give them. Nothing here is cited from memory.

> [!recommendation] How to read a paper in this field
> Read the evaluation before the method. For each paper, write down three things before you summarize what it claims: the benchmark and its version, how success is defined and aggregated (per episode or per task, how many seeds and evaluation episodes), and which generalization axis the test actually varies. Then ask what the evaluation **cannot** support. A method tested only on its training distribution says nothing about generalization; a method tested on one seed says little about anything. Research mode has the tools for this check.

Each section lists papers in suggested reading order with the course level where they fit, and one question to answer while reading.

## Primary sources: MuJoCo itself

The documentation is the reference for everything this course states about MuJoCo's behaviour. Read the computation chapter after Level 1 and again after Level 20.

- [MuJoCo documentation](https://mujoco.readthedocs.io/en/stable/): [Computation](https://mujoco.readthedocs.io/en/stable/computation/index.html), [Modeling](https://mujoco.readthedocs.io/en/stable/modeling.html), [XML reference](https://mujoco.readthedocs.io/en/stable/XMLreference.html), [API reference](https://mujoco.readthedocs.io/en/stable/APIreference/index.html).
- [Changelog](https://mujoco.readthedocs.io/en/stable/changelog.html). Read it before upgrading. Several lessons cite it for when a feature appeared.
- [Source code](https://github.com/google-deepmind/mujoco) and [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie), the curated collection of robot models.
- E. Todorov, T. Erez, Y. Tassa. **MuJoCo: A physics engine for model-based control.** IROS 2012, pp. 5026-5033. [doi:10.1109/IROS.2012.6386109](https://doi.org/10.1109/IROS.2012.6386109). *Level 0.* The original design goals. Question: which of the 2012 design decisions does the current computation chapter still describe, and which changed?
- E. Todorov. **Convex and analytically-invertible dynamics with contacts and constraints: Theory and implementation in MuJoCo.** ICRA 2014, pp. 6054-6061. [doi:10.1109/ICRA.2014.6907751](https://doi.org/10.1109/ICRA.2014.6907751). *Levels 9 and 20.* The convex soft-contact formulation the solver still uses. Question: what does convexity buy, and what physical behaviour does it give up compared with a complementarity formulation?

## Mathematics and robotics foundations

- K. M. Lynch, F. C. Park. **Modern Robotics: Mechanics, Planning, and Control.** Cambridge University Press, 2017. [doi:10.1017/9781316661239](https://doi.org/10.1017/9781316661239). *Levels 4 to 8.* Screw theory, kinematics, dynamics and control in one notation. Question: map its spatial and body twists onto MuJoCo's `cvel` and free-joint `qvel`.
- R. Featherstone. **Rigid Body Dynamics Algorithms.** Springer, 2008. [doi:10.1007/978-1-4899-7560-7](https://doi.org/10.1007/978-1-4899-7560-7). *Levels 7 and 20.* The recursive Newton-Euler and composite rigid body algorithms behind `mj_rne` and `mj_crb`. Question: which quantities does MuJoCo cache in `mjData` that the book's algorithms recompute?
- J. Solà. **Quaternion kinematics for the error-state Kalman filter.** arXiv:1711.02508, 2017. [arXiv](https://arxiv.org/abs/1711.02508). *Level 4.* Read the section on conventions: quaternion libraries disagree on component order and on local versus global perturbations, and MuJoCo picks one of each.
- J. Solà, J. Deray, D. Atchuthan. **A micro Lie theory for state estimation in robotics.** arXiv:1812.01537, 2018. [arXiv](https://arxiv.org/abs/1812.01537). *Levels 4 and 6.* The cleanest short treatment of exponential maps and Jacobians on SO(3) and SE(3). Question: why does `mj_differentiatePos` return a vector of size `nv` rather than `nq`?
- O. Khatib. **A unified approach for motion and force control of robot manipulators: The operational space formulation.** IEEE Journal on Robotics and Automation 3(1), 1987, pp. 43-53. [doi:10.1109/JRA.1987.1087068](https://doi.org/10.1109/JRA.1987.1087068). *Level 8.* The source of operational-space control. Question: what does the controller assume about the model, and what happens when that model is wrong (Project 6 measures it)?

## Contact simulation

- D. E. Stewart, J. C. Trinkle. **An implicit time-stepping scheme for rigid body dynamics with inelastic collisions and Coulomb friction.** International Journal for Numerical Methods in Engineering 39(15), 1996, pp. 2673-2691. [doi:10.1002/(SICI)1097-0207(19960815)39:15<2673::AID-NME972>3.0.CO;2-I](https://doi.org/10.1002/%28SICI%291097-0207%2819960815%2939%3A15%3C2673%3A%3AAID-NME972%3E3.0.CO%3B2-I). *Level 9.* The velocity-level time-stepping idea that most robotics simulators share.
- M. Anitescu, F. A. Potra. **Formulating dynamic multi-rigid-body contact problems with friction as solvable linear complementarity problems.** Nonlinear Dynamics 14(3), 1997, pp. 231-247. [doi:10.1023/A:1008292328909](https://doi.org/10.1023/A:1008292328909). *Level 9.* Why polyhedral friction cones make the problem solvable, and what they cost (compare the pyramidal cone measurements in Lesson 0.3).
- E. Todorov. **A convex, smooth and invertible contact model for trajectory optimization.** ICRA 2011. [doi:10.1109/ICRA.2011.5979814](https://doi.org/10.1109/ICRA.2011.5979814). *Levels 9 and 21.* The precursor of MuJoCo's contact model, written for optimization rather than simulation. Question: why does trajectory optimization want contact forces that are smooth in the state?
- J. Horak, J. C. Trinkle. **On the similarities and differences among contact models in robot simulation.** IEEE Robotics and Automation Letters 4(2), 2019, pp. 493-499. [doi:10.1109/LRA.2019.2891085](https://doi.org/10.1109/LRA.2019.2891085). *Level 9.* A side-by-side reading of the formulations used by MuJoCo and other engines.
- T. Erez, Y. Tassa, E. Todorov. **Simulation tools for model-based robotics: Comparison of Bullet, Havok, MuJoCo, ODE and PhysX.** ICRA 2015, pp. 4397-4404. [doi:10.1109/ICRA.2015.7139807](https://doi.org/10.1109/ICRA.2015.7139807). *Level 0.* Read for the method of comparison (speed against accuracy as the timestep varies), not for the numbers: every engine compared has changed since 2015.
- T. A. Howell et al. **Dojo: A Differentiable Physics Engine for Robotics.** arXiv:2203.00806, 2022. [arXiv](https://arxiv.org/abs/2203.00806). *Level 20.* A hard-contact alternative designed for useful gradients. Question: what does it give up to get them?

## Manipulation and contact-rich control

- N. Hogan. **Impedance Control: An Approach to Manipulation: Part I, Theory.** Journal of Dynamic Systems, Measurement, and Control 107(1), 1985, pp. 1-7. [doi:10.1115/1.3140702](https://doi.org/10.1115/1.3140702). *Levels 8 and 10.* Why a manipulator in contact should control the relation between force and motion rather than either alone. Question: which of the paper's arguments depend on the environment being an admittance?
- D. E. Whitney. **Quasi-Static Assembly of Compliantly Supported Rigid Parts.** Journal of Dynamic Systems, Measurement, and Control 104(1), 1982, pp. 65-77. [doi:10.1115/1.3149634](https://doi.org/10.1115/1.3149634). *Level 10.* Jamming and wedging in peg-in-hole insertion and how support compliance decides between them. Question: where would the compliance centre of Lesson 10.3's impedance controller have to be to avoid the tilted jams it records?
- M. T. Mason. **Mechanics and Planning of Manipulator Pushing Operations.** The International Journal of Robotics Research 5(3), 1986, pp. 53-71. [doi:10.1177/027836498600500303](https://doi.org/10.1177/027836498600500303). *Level 10.* How a pushed object turns, from the contact geometry and friction alone. Question: what does the theory predict for Lesson 10.3's puck when the contact leaves the pusher's face?
- A. Jain, C. C. Kemp. **Pulling open novel doors and drawers with equilibrium point control.** IEEE-RAS Humanoids 2009, pp. 498-505. [doi:10.1109/ICHR.2009.5379532](https://doi.org/10.1109/ICHR.2009.5379532). *Level 10.* Opening mechanisms without a model by moving a compliant arm's equilibrium point along the measured motion.
- R. Martín-Martín et al. **Variable Impedance Control in End-Effector Space: An Action Space for Reinforcement Learning in Contact-Rich Tasks.** IROS 2019, pp. 1010-1017. [doi:10.1109/IROS40897.2019.8968201](https://doi.org/10.1109/IROS40897.2019.8968201). *Levels 10 and 13.* Letting the policy choose stiffness as well as the target. Question: which of its tasks would a fixed-stiffness controller fail, by the reasoning of Lesson 10.3?

## Reinforcement learning and its evaluation

- J. Schulman et al. **High-Dimensional Continuous Control Using Generalized Advantage Estimation.** arXiv:1506.02438, 2015. [arXiv](https://arxiv.org/abs/1506.02438). *Level 13.*
- J. Schulman et al. **Proximal Policy Optimization Algorithms.** arXiv:1707.06347, 2017. [arXiv](https://arxiv.org/abs/1707.06347). *Level 13.* Question: which of the details that make PPO work in practice are in the paper, and which are only in the code?
- L. Engstrom et al. **Implementation Matters in Deep Policy Gradients: A Case Study on PPO and TRPO.** arXiv:2005.12729, 2020. [arXiv](https://arxiv.org/abs/2005.12729). *Level 13.* The answer to the previous question, measured.
- T. P. Lillicrap et al. **Continuous control with deep reinforcement learning.** arXiv:1509.02971, 2015. [arXiv](https://arxiv.org/abs/1509.02971). *Level 13.* DDPG: a deterministic actor trained through a learned critic, the baseline TD3 and SAC modify.
- T. Haarnoja et al. **Soft Actor-Critic: Off-Policy Maximum Entropy Deep Reinforcement Learning with a Stochastic Actor.** arXiv:1801.01290, 2018. [arXiv](https://arxiv.org/abs/1801.01290). *Level 13.*
- T. Haarnoja et al. **Soft Actor-Critic Algorithms and Applications.** arXiv:1812.05905, 2018. [arXiv](https://arxiv.org/abs/1812.05905). *Level 13.* The version of SAC with the temperature tuned automatically toward a target entropy, as in `mjcourse.rl.offpolicy`. Question: what does the target entropy assume about the action space's scale?
- S. Fujimoto, H. van Hoof, D. Meger. **Addressing Function Approximation Error in Actor-Critic Methods.** arXiv:1802.09477, 2018. [arXiv](https://arxiv.org/abs/1802.09477). *Level 13.* TD3.
- P. Henderson et al. **Deep Reinforcement Learning that Matters.** arXiv:1709.06560, 2017. [arXiv](https://arxiv.org/abs/1709.06560). *Levels 13 and 21.* Seeds, implementations and hyperparameters change conclusions; the experiments use MuJoCo locomotion tasks.
- M. Andrychowicz et al. **What Matters In On-Policy Reinforcement Learning? A Large-Scale Empirical Study.** arXiv:2006.05990, 2020. [arXiv](https://arxiv.org/abs/2006.05990). *Level 13.* What it cannot support: its tasks are locomotion, so its recommendations are hypotheses, not results, for manipulation.
- T. Salimans, J. Ho, X. Chen, S. Sidor, I. Sutskever. **Evolution Strategies as a Scalable Alternative to Reinforcement Learning.** arXiv:1703.03864, 2017. [arXiv](https://arxiv.org/abs/1703.03864). *Level 13.* A return-only search scaled across many workers, evaluated on MuJoCo tasks.
- H. Mania, A. Guy, B. Recht. **Simple random search provides a competitive approach to reinforcement learning.** arXiv:1803.07055, 2018. [arXiv](https://arxiv.org/abs/1803.07055). *Level 13.* Linear policies found by random search on MuJoCo locomotion. Question: which of its tricks (observation normalization, top-direction selection) does Lesson 13.1's cross-entropy search share?
- F. Pardo, A. Tavakoli, V. Levdik, P. Kormushev. **Time Limits in Reinforcement Learning.** ICML 2018, PMLR 80, pp. 4042-4051; arXiv:1712.00378. [arXiv](https://arxiv.org/abs/1712.00378). *Levels 12 and 13.* Why `truncated` is not `terminated`, and what to do with each. Question: which case, (i) or (ii) in the paper's terms, is the reach task of Lesson 12.1?
- L. Pinto, M. Andrychowicz, P. Welinder, W. Zaremba, P. Abbeel. **Asymmetric Actor Critic for Image-Based Robot Learning.** arXiv:1710.06542, 2017. [arXiv](https://arxiv.org/abs/1710.06542). *Levels 12 and 13.* Privileged simulator state for the critic, realistic inputs for the actor. Question: which of Lesson 12.2's leaky observations would be legitimate inputs to such a critic?
- R. Agarwal et al. **Deep Reinforcement Learning at the Edge of the Statistical Precipice.** arXiv:2108.13264, 2021. [arXiv](https://arxiv.org/abs/2108.13264). *Level 21.* Interquartile means and bootstrap intervals over runs; Research mode uses both.
- Y. Tassa et al. **DeepMind Control Suite.** arXiv:1801.00690, 2018. [arXiv](https://arxiv.org/abs/1801.00690). *Level 12.* A benchmark built on MuJoCo; read how it fixes the reward scale and episode length across tasks.
- M. Towers et al. **Gymnasium: A Standard Interface for Reinforcement Learning Environments.** arXiv:2407.17032, 2024. [arXiv](https://arxiv.org/abs/2407.17032). *Level 12.* Why `terminated` and `truncated` are separate.

## Imitation learning

- S. Ross, G. J. Gordon, J. A. Bagnell. **A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning.** arXiv:1011.0686, 2010 (AISTATS 2011). [arXiv](https://arxiv.org/abs/1011.0686). *Level 14.* DAgger, and the compounding-error argument that motivates it.
- A. Mandlekar et al. **What Matters in Learning from Offline Human Demonstrations for Robot Manipulation.** arXiv:2108.03298, 2021. [arXiv](https://arxiv.org/abs/2108.03298). *Level 14.* Demonstration quality, observation choice and evaluation for behaviour cloning.
- C. Chi et al. **Diffusion Policy: Visuomotor Policy Learning via Action Diffusion.** arXiv:2303.04137, 2023. [arXiv](https://arxiv.org/abs/2303.04137). *Level 14.* Multimodal action distributions. Question: on which tasks does a unimodal Gaussian policy fail, and why?
- T. Z. Zhao et al. **Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware.** arXiv:2304.13705, 2023. [arXiv](https://arxiv.org/abs/2304.13705). *Level 14.* Action chunking (ACT).

## Vision, language and vision-language-action models

- M. Laskin et al. **Reinforcement Learning with Augmented Data.** arXiv:2004.14990, 2020. [arXiv](https://arxiv.org/abs/2004.14990). *Level 15.*
- I. Kostrikov, D. Yarats, R. Fergus. **Image Augmentation Is All You Need: Regularizing Deep Reinforcement Learning from Pixels.** arXiv:2004.13649, 2020. [arXiv](https://arxiv.org/abs/2004.13649). *Level 15.* Both papers evaluate on the DeepMind Control Suite; ask what their augmentations would do to a task where object position is the signal.
- A. Brohan et al. **RT-1: Robotics Transformer for Real-World Control at Scale.** arXiv:2212.06817, 2022. [arXiv](https://arxiv.org/abs/2212.06817). *Level 16.*
- A. Brohan et al. **RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control.** arXiv:2307.15818, 2023. [arXiv](https://arxiv.org/abs/2307.15818). *Level 16.* Where the term vision-language-action model comes from.
- Open X-Embodiment Collaboration. **Open X-Embodiment: Robotic Learning Datasets and RT-X Models.** arXiv:2310.08864, 2023. [arXiv](https://arxiv.org/abs/2310.08864). *Level 16.*
- Octo Model Team. **Octo: An Open-Source Generalist Robot Policy.** arXiv:2405.12213, 2024. [arXiv](https://arxiv.org/abs/2405.12213). *Level 16.*
- M. J. Kim et al. **OpenVLA: An Open-Source Vision-Language-Action Model.** arXiv:2406.09246, 2024. [arXiv](https://arxiv.org/abs/2406.09246). *Level 16.*
- K. Black et al. **π0: A Vision-Language-Action Flow Model for General Robot Control.** arXiv:2410.24164, 2024. [arXiv](https://arxiv.org/abs/2410.24164). *Level 16.* For each of these four, find which generalization axis (object, position, instruction, embodiment) each reported number tests.

## World models and planning

- Y. Tassa, T. Erez, E. Todorov. **Synthesis and stabilization of complex behaviors through online trajectory optimization.** IROS 2012, pp. 4906-4913. [doi:10.1109/IROS.2012.6386025](https://doi.org/10.1109/IROS.2012.6386025). *Level 21.* Model predictive control with MuJoCo as the model.
- G. Williams et al. **Information theoretic MPC for model-based reinforcement learning.** ICRA 2017, pp. 1714-1721. [doi:10.1109/ICRA.2017.7989202](https://doi.org/10.1109/ICRA.2017.7989202). *Level 21.* MPPI.
- T. Howell et al. **Predictive Sampling: Real-time Behaviour Synthesis with MuJoCo.** arXiv:2212.00541, 2022. [arXiv](https://arxiv.org/abs/2212.00541). *Level 21.* MuJoCo MPC, and the case for a very simple sampling planner.
- D. Ha, J. Schmidhuber. **World Models.** arXiv:1803.10122, 2018. [arXiv](https://arxiv.org/abs/1803.10122). *Level 21.*
- D. Hafner et al. **Learning Latent Dynamics for Planning from Pixels.** arXiv:1811.04551, 2018. [arXiv](https://arxiv.org/abs/1811.04551). *Level 21.* PlaNet.
- D. Hafner et al. **Mastering Diverse Domains through World Models.** arXiv:2301.04104, 2023. [arXiv](https://arxiv.org/abs/2301.04104). *Level 21.* DreamerV3.
- N. Hansen, X. Wang, H. Su. **Temporal Difference Learning for Model Predictive Control.** arXiv:2203.04955, 2022. [arXiv](https://arxiv.org/abs/2203.04955). *Level 21.* TD-MPC.
- N. Hansen, H. Su, X. Wang. **TD-MPC2: Scalable, Robust World Models for Continuous Control.** arXiv:2310.16828, 2023. [arXiv](https://arxiv.org/abs/2310.16828). *Level 21.*
- M. Assran et al. **V-JEPA 2: Self-Supervised Video Models Enable Understanding, Prediction and Planning.** arXiv:2506.09985, 2025. [arXiv](https://arxiv.org/abs/2506.09985). *Level 21.* For each world-model paper, separate three claims the course keeps apart: prediction accuracy, controllability, and the success of the policy or planner that uses the model.

## Domain randomization, system identification and sim-to-real

- J. Tobin et al. **Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real World.** arXiv:1703.06907, 2017. [arXiv](https://arxiv.org/abs/1703.06907). *Level 17.* Visual randomization.
- X. B. Peng et al. **Sim-to-Real Transfer of Robotic Control with Dynamics Randomization.** arXiv:1710.06537, 2017. [arXiv](https://arxiv.org/abs/1710.06537). *Level 17.* Dynamics randomization.
- J. Tan et al. **Sim-to-Real: Learning Agile Locomotion For Quadruped Robots.** arXiv:1804.10332, 2018. [arXiv](https://arxiv.org/abs/1804.10332). *Levels 17 and 18.* System identification and randomization used together, with an actuator model.
- J. Hwangbo et al. **Learning agile and dynamic motor skills for legged robots.** Science Robotics 4(26), 2019, eaau5872. [arXiv:1901.08652](https://arxiv.org/abs/1901.08652). *Level 19.* A learned actuator model closes the gap that rigid-body identification left.
- OpenAI et al. **Solving Rubik's Cube with a Robot Hand.** arXiv:1910.07113, 2019. [arXiv](https://arxiv.org/abs/1910.07113). *Level 17.* Automatic domain randomization at large compute cost.
- A. Kumar et al. **RMA: Rapid Motor Adaptation for Legged Robots.** arXiv:2107.04034, 2021. [arXiv](https://arxiv.org/abs/2107.04034). *Level 19.* Adapting to the dynamics online instead of being robust to all of them.
- W. Zhao, J. P. Queralta, T. Westerlund. **Sim-to-Real Transfer in Deep Reinforcement Learning for Robotics: a Survey.** IEEE SSCI 2020, pp. 737-744. [arXiv:2009.13303](https://arxiv.org/abs/2009.13303). *Level 19.*
- F. Muratore et al. **Robot Learning from Randomized Simulations: A Review.** arXiv:2111.00956, 2021. [arXiv](https://arxiv.org/abs/2111.00956). *Level 17.*

## Benchmarks and batched simulation

Read these for their protocols (Level 21): task set, splits, initial states, success definition, aggregation, and simulator version.

- T. Yu et al. **Meta-World: A Benchmark and Evaluation for Multi-Task and Meta Reinforcement Learning.** arXiv:1910.10897, 2019. [arXiv](https://arxiv.org/abs/1910.10897). Built on MuJoCo. Its task definitions changed between releases: always report the version.
- Y. Zhu et al. **robosuite: A Modular Simulation Framework and Benchmark for Robot Learning.** arXiv:2009.12293, 2020. [arXiv](https://arxiv.org/abs/2009.12293). Built on MuJoCo.
- B. Liu et al. **LIBERO: Benchmarking Knowledge Transfer for Lifelong Robot Learning.** arXiv:2306.03310, 2023. [arXiv](https://arxiv.org/abs/2306.03310). Built on robosuite.
- X. Zhou et al. **LIBERO-PRO: Towards Robust and Fair Evaluation of Vision-Language-Action Models Beyond Memorization.** arXiv:2510.03827, 2025. [arXiv](https://arxiv.org/abs/2510.03827), and S. Fei et al. **LIBERO-Plus: In-depth Robustness Analysis of Vision-Language-Action Models.** arXiv:2510.13626, 2025. [arXiv](https://arxiv.org/abs/2510.13626). Both perturb LIBERO's evaluation conditions; read them together with LIBERO to see how much of a reported success rate survives a change of initial state or instruction.
- O. Mees et al. **CALVIN: A Benchmark for Language-Conditioned Policy Learning for Long-Horizon Robot Manipulation Tasks.** arXiv:2112.03227, 2021. [arXiv](https://arxiv.org/abs/2112.03227). Built on PyBullet. Its splits (for example ABC to D versus ABCD to D) are not interchangeable.
- S. James et al. **RLBench: The Robot Learning Benchmark & Learning Environment.** arXiv:1909.12271, 2019. [arXiv](https://arxiv.org/abs/1909.12271). Built on CoppeliaSim.
- X. Li et al. **Evaluating Real-World Robot Manipulation Policies in Simulation.** arXiv:2405.05941, 2024. [arXiv](https://arxiv.org/abs/2405.05941). SimplerEnv: how well simulated success predicts real success, and how to measure that.
- S. Tao et al. **ManiSkill3: GPU Parallelized Robotics Simulation and Rendering for Generalizable Embodied AI.** arXiv:2410.00425, 2024. [arXiv](https://arxiv.org/abs/2410.00425). Built on SAPIEN.
- C. D. Freeman et al. **Brax: A Differentiable Physics Engine for Large Scale Rigid Body Simulation.** arXiv:2106.13281, 2021. [arXiv](https://arxiv.org/abs/2106.13281). Accelerator-batched simulation in JAX, the setting MJX later brought to MuJoCo's own pipeline.
- K. Zakka et al. **MuJoCo Playground.** arXiv:2502.08844, 2025. [arXiv](https://arxiv.org/abs/2502.08844). Environments and training on MJX. Read with the Performance lab: which of its throughput numbers depend on the accelerator, and which on the batch size?
