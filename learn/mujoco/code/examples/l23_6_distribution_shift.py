import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor

import mujoco
import numpy as np
import torch

from mjcourse import stats
from mjcourse import tabletop as tt
from mjcourse.worldmodel import mpc, standard

FAST = os.environ.get("MJC_FAST") == "1"
N = 6 if FAST else 30
CONDITIONS = {"nominal": {}, "pucks near the rim": {"rim": True}, "friction 0.2": {"friction": 0.2},
              "friction 0.8": {"friction": 0.8}, "ice": {"friction": 0.05}, "puck mass 0.3 kg": {"puck_mass": 0.3},
              "larger pucks": {"puck_radius": 0.04}, "fast impacts": {"impacts": True}}


def variation(cond: dict) -> tt.Variation:
    return tt.Variation(**{k: v for k, v in cond.items() if k in ("friction", "puck_mass", "puck_radius")})


def layout_for(cond: dict, rng: np.random.Generator, task):
    if not cond.get("rim"):
        return tt.sample_layout(rng, task)
    while True:
        layout = tt.sample_layout(rng, task, low=-0.26, high=0.26, min_gap=0.09)
        if all(max(abs(x), abs(y)) > 0.2 for x, y in layout.pucks):
            return layout


def _at_puck(state: np.ndarray, target: int) -> np.ndarray:
    d = state[target:target + 2] - state[0:2]
    return d / (np.linalg.norm(d) + 1e-9)


def prediction(args) -> dict:
    name, i = args
    torch.set_num_threads(1)
    cond = CONDITIONS[name]
    rng = np.random.default_rng([6, i])
    task = (tt.OBJECTS[rng.integers(3)], list(tt.ZONES)[rng.integers(4)])
    scene, nominal = tt.Tabletop(variation(cond)), tt.Tabletop()
    scene.reset(layout_for(cond, rng, task))
    model = standard.model("one_step")
    spec = mujoco.mjtState.mjSTATE_INTEGRATION
    target = 4 + 4 * tt.OBJECTS.index(task[0])
    errors = {"learned": [], "nominal MuJoCo": []}
    for t in range(tt.EPISODE_STEPS - 10):
        if cond.get("impacts"):
            a = _at_puck(scene.state(), target)
        elif rng.random() < 0.2:
            a = rng.uniform(-1, 1, 2)
        else:
            a = np.clip(tt.expert(scene.state(), task) + rng.normal(0, 0.3, 2), -1, 1)
        if t % 10 == 0:
            if cond.get("impacts"):
                future = np.repeat(a[None], 10, axis=0)
            else:
                future = np.array([a] + [np.clip(tt.expert(scene.state(), task) + rng.normal(0, 0.3, 2), -1, 1)
                                         for _ in range(1, 10)])
            s0 = scene.state()
            full = np.zeros(mujoco.mj_stateSize(scene.model, spec))
            mujoco.mj_getState(scene.model, scene.data, full, spec)
            mujoco.mj_setState(nominal.model, nominal.data, full, spec)
            for b in future:
                nominal.step(b)
            pred_learned = model.rollout(s0[None], future[None].astype(np.float32))[0, -1]
            for b in future:
                scene.step(b)
            truth = scene.state()
            errors["learned"].append(np.linalg.norm(pred_learned[target:target + 2] - truth[target:target + 2]))
            errors["nominal MuJoCo"].append(np.linalg.norm(nominal.state()[target:target + 2] - truth[target:target + 2]))
            mujoco.mj_setState(scene.model, scene.data, full, spec)
            mujoco.mj_forward(scene.model, scene.data)
        scene.step(a)
    scene.close()
    nominal.close()
    return {"condition": name, **{k: float(np.mean(v)) for k, v in errors.items()}}


def control(args) -> dict:
    name, planner_kind, execute, i = args
    torch.set_num_threads(1)
    cond = CONDITIONS[name]
    rng = np.random.default_rng([7, i])
    task = (tt.OBJECTS[rng.integers(3)], list(tt.ZONES)[rng.integers(4)])
    layout = layout_for(cond, rng, task)
    if planner_kind == "learned":
        model = standard.model("one_step")
        factory = lambda scene: mpc.LearnedModel(model)
    elif planner_kind == "nominal MuJoCo":
        factory = lambda scene: mpc.MujocoModel(scene, plan_scene=tt.Tabletop())
    else:
        factory = lambda scene: mpc.MujocoModel(scene)
    r = mpc.run_episode(factory, task, layout, variation=variation(cond), execute=execute)
    return {"condition": name, "planner": planner_kind, "execute": execute, "success": bool(r["success"])}


if __name__ == "__main__":
    standard.model("one_step")
    workers = int(os.environ.get("SLURM_CPUS_PER_TASK", min(32, os.cpu_count() or 1)))
    with ProcessPoolExecutor(workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        preds = list(pool.map(prediction, [(c, i) for c in CONDITIONS for i in range(N)]))
        runs = list(pool.map(control, [(c, p, e, i) for e in (1, 10) for c in CONDITIONS if c != "fast impacts"
                                        for p in ("learned", "nominal MuJoCo", "true MuJoCo") for i in range(N)], chunksize=1))
    print(f"(1) prediction: error of the pushed puck 1 s ahead (mm), {N} episodes per condition, against the condition's truth")
    print(f"  {'condition':<22}{'learned model':>15}{'nominal MuJoCo':>16}")
    for c in CONDITIONS:
        rows = [p for p in preds if p["condition"] == c]
        print(f"  {c:<22}{1000 * np.mean([r['learned'] for r in rows]):>15.1f}{1000 * np.mean([r['nominal MuJoCo'] for r in rows]):>16.1f}")
    for part, execute, how in ((2, 1, "replanning every 0.1 s"), (3, 10, "each plan's first 1 s open loop")):
        print(f"({part}) control, {how}: MPC success, {N} tasks per cell [95% Wilson interval]")
        print(f"  {'condition':<22}" + "".join(f"{p:>22}" for p in ("learned", "nominal MuJoCo", "true MuJoCo")))
        for c in CONDITIONS:
            if c == "fast impacts":
                continue
            cells = []
            for p in ("learned", "nominal MuJoCo", "true MuJoCo"):
                k = sum(r["success"] for r in runs if r["condition"] == c and r["planner"] == p and r["execute"] == execute)
                lo, hi = stats.wilson_interval(k, N)
                cells.append(f"{k / N:.2f} [{lo:.2f}, {hi:.2f}]")
            print(f"  {c:<22}" + "".join(f"{x:>22}" for x in cells))
