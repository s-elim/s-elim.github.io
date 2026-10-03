"""Lesson 6.3: inverse kinematics by damped least squares, under test.

INPUT   arm7.xml; targets made by forward kinematics of random joint vectors inside
        the ranges, so "reachable" never depends on the solver being tested
PROCESS (1) solve 6-D IK from the home pose: success, iterations, time, errors;
        (2) sweep the damping;
        (3) analyse every failure and retry it from random starts;
        (4) add a null-space posture term with the damped and the exact projector;
        (5) near the singular straight-up pose and beyond the workspace: what the
            solver does, and what it reports
OUTPUT  printed tables

Run:  python examples/l6_3_inverse_kinematics.py
"""

import os
import time

import mujoco
import numpy as np

from mjcourse import kinematics, model_path, spatial, stats

N = 40 if os.environ.get("MJC_FAST") == "1" else 100


def reachable_targets(model, n: int, seed: int) -> list[tuple[np.ndarray, np.ndarray]]:
    data = mujoco.MjData(model)
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        data.qpos[:] = rng.uniform(model.jnt_range[:, 0], model.jnt_range[:, 1])
        mujoco.mj_kinematics(model, data)
        out.append((data.site("ee").xpos.copy(), spatial.mat_to_quat(data.site("ee").xmat.reshape(3, 3))))
    return out


def at_limit(model, q: np.ndarray) -> int:
    lo, hi = model.jnt_range[:, 0], model.jnt_range[:, 1]
    return int(np.sum((q - lo < 1e-9) | (hi - q < 1e-9)))


def benchmark(model, targets, home) -> list[int]:
    results, t0 = [], time.perf_counter()
    for pos, quat in targets:
        results.append(kinematics.solve_ik(model, "ee", pos, quat, q_init=home))
    elapsed = (time.perf_counter() - t0) / len(targets)
    ok = [r for r in results if r.success]
    lo, hi = stats.wilson_interval(len(ok), len(results))
    its = np.array([r.iterations for r in ok])
    print(f"  success {len(ok)}/{len(results)} (95% Wilson [{lo:.2f}, {hi:.2f}]), iterations among successes: "
          f"median {np.median(its):.0f}, 95th percentile {np.percentile(its, 95):.0f}; {1000 * elapsed:.2f} ms per solve")
    print(f"  worst error among successes: {1000 * max(r.pos_error for r in ok):.3f} mm, "
          f"{np.degrees(max(r.rot_error for r in ok)):.3f} deg; joints outside their ranges: "
          f"{sum(int(np.any(r.qpos < model.jnt_range[:, 0] - 1e-12) | np.any(r.qpos > model.jnt_range[:, 1] + 1e-12)) for r in results)}")
    return [i for i, r in enumerate(results) if not r.success]


def damping_sweep(model, targets, home) -> None:
    for lam in (1e-4, 1e-3, 1e-2, 3e-2, 1e-1, 3e-1):
        res = [kinematics.solve_ik(model, "ee", p, q, q_init=home, damping=lam) for p, q in targets]
        its = [r.iterations for r in res if r.success]
        print(f"  damping {lam:<7g} success {sum(r.success for r in res):3d}/{len(res)}, median iterations {np.median(its):.0f}")


def failures(model, targets, home, failed: list[int]) -> None:
    used = []
    for i in failed:
        pos, quat = targets[i]
        r = kinematics.solve_ik(model, "ee", pos, quat, q_init=home)
        retry, n = kinematics.solve_ik_restarts(model, "ee", pos, quat, q_init=home, restarts=10, seed=i)
        used.append(n if retry.success else None)
        print(f"  target {i:2d}: stopped at {1000 * r.pos_error:6.1f} mm, {np.degrees(r.rot_error):6.1f} deg with "
              f"{at_limit(model, r.qpos)} joint(s) at a limit; random restarts: "
              f"{'solved after ' + str(n) if retry.success else 'not solved in 10'}")
    print(f"  every failure ended with a joint at a limit: {all(at_limit(model, kinematics.solve_ik(model, 'ee', *targets[i], q_init=home).qpos) > 0 for i in failed)}; "
          f"solved by restarts: {sum(u is not None for u in used)}/{len(failed)}")


def nullspace(model, targets, home) -> None:
    mid = model.jnt_range.mean(axis=1)
    for label, gain, proj in (("no posture term", 0.0, "exact"), ("posture term, damped projector", 0.1, "damped"),
                              ("posture term, exact projector", 0.1, "exact")):
        res = [kinematics.solve_ik(model, "ee", p, q, q_init=home, max_iters=300, nullspace_gain=gain,
                                   q_rest=mid, projector=proj) for p, q in targets]
        ok = [r for r in res if r.success]
        spread = np.mean([np.linalg.norm(r.qpos - mid) for r in ok])
        print(f"  {label:<32} success {len(ok):3d}/{len(res)}, mean |q - q_mid| over successes {spread:.2f} rad")


def edge_cases(model, home) -> None:
    data = mujoco.MjData(model)
    data.qpos[:] = [0.0, 0.001, 0.0, 0.001, 0.0, 0.001, 0.0]         # 1 mrad from straight up
    mujoco.mj_kinematics(model, data)
    pos = data.site("ee").xpos.copy() + [0.0, 0.0, -0.03]           # 3 cm down: reachable
    for lam in (1e-6, 1e-3, 1e-2, 1e-1):
        r = kinematics.solve_ik(model, "ee", pos, q_init=data.qpos.copy(), damping=lam, max_iters=300)
        print(f"  from 1 mrad short of straight up, 3 cm down, damping {lam:<6g}: success {r.success}, "
              f"{r.iterations:2d} iterations, largest unclipped step {r.max_step:7.3g} rad")
    far = np.array([1.6, 0.0, 0.5])
    r = kinematics.solve_ik(model, "ee", far, q_init=home, max_iters=300)
    data.qpos[:] = r.qpos
    mujoco.mj_kinematics(model, data)
    reach = np.linalg.norm(data.site("ee").xpos - data.xpos[model.body("link2").id])
    print(f"  target 1.6 m from the base: success {r.success}, final position error {1000 * r.pos_error:.0f} mm, "
          f"shoulder-to-tool distance at the end {reach:.3f} m (arm fully stretched towards the target)")


if __name__ == "__main__":
    model = mujoco.MjModel.from_xml_path(str(model_path("arm7")))
    home = model.key_qpos[model.key("home").id].copy()
    targets = reachable_targets(model, N, seed=0)
    print(f"(1) {N} reachable 6-D targets, one start (home), damping 0.01, tolerances 0.1 mm and 0.057 deg")
    failed = benchmark(model, targets, home)
    print("(2) damping sweep")
    damping_sweep(model, targets, home)
    print("(3) the failures, one by one")
    failures(model, targets, home, failed)
    print("(4) a null-space term pulling towards the middle of the joint ranges (gain 0.1, up to 300 iterations)")
    nullspace(model, targets, home)
    print("(5) near a singularity, and out of reach")
    edge_cases(model, home)
