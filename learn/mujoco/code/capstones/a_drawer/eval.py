import json
from pathlib import Path
import sys

_code_dir = str(Path(__file__).resolve().parents[2])
if _code_dir not in sys.path:
    sys.path.insert(0, _code_dir)

import numpy as np

from capstones.a_drawer.env import DrawerEnv
from capstones.a_drawer.policy import ScriptedDrawerPolicy

from mjcourse.experiment import Protocol, run_record, save
from mjcourse.paths import model_path
from mjcourse.stats import wilson_interval


def evaluate_policy(env: DrawerEnv, policy_fn, seeds: list[int]) -> tuple[int, int, float, tuple[float, float], list[dict]]:
    successes = 0
    episodes_log = []
    for seed in seeds:
        obs, info = env.reset(seed=seed)
        if hasattr(policy_fn, "reset"):
            policy_fn.reset()
        episode_success = False
        final_drawer_pos = 0.0
        for step in range(env.max_episode_steps):
            act = policy_fn(obs)
            obs, reward, terminated, truncated, info = env.step(act)
            final_drawer_pos = float(info.get("drawer_pos", 0.0))
            if info.get("success", False):
                episode_success = True
            if terminated or truncated:
                break
        if episode_success:
            successes += 1
        episodes_log.append({
            "seed": seed,
            "success": episode_success,
            "final_drawer_pos": final_drawer_pos,
        })
    n = len(seeds)
    rate = successes / n
    ci = wilson_interval(successes, n)
    return successes, n, rate, ci, episodes_log


def main() -> int:
    seeds = list(range(1000, 1200))
    env = DrawerEnv(action_mode="ee_delta", max_episode_steps=100)
    policy = ScriptedDrawerPolicy(ee_step=env.ee_step)

    print(f"Evaluating scripted policy on {len(seeds)} held-out seeds (1000..1199)...")
    s_succ, n_eval, s_rate, s_ci, s_log = evaluate_policy(env, policy, seeds)
    print(f"Scripted policy: {s_succ}/{n_eval} ({s_rate * 100:.1f}%), 95% Wilson CI: [{s_ci[0] * 100:.1f}%, {s_ci[1] * 100:.1f}%]")

    print("Evaluating baseline policies on the same 200 held-out seeds...")
    zero_fn = lambda obs: np.zeros(4, dtype=np.float32)
    z_succ, _, z_rate, z_ci, _ = evaluate_policy(env, zero_fn, seeds)
    print(f"Zero action:     {z_succ}/{n_eval} ({z_rate * 100:.1f}%), 95% Wilson CI: [{z_ci[0] * 100:.1f}%, {z_ci[1] * 100:.1f}%]")

    pull_fn = lambda obs: np.array([-1.0, 0.0, 0.0, -1.0], dtype=np.float32)
    p_succ, _, p_rate, p_ci, _ = evaluate_policy(env, pull_fn, seeds)
    print(f"Constant pull:   {p_succ}/{n_eval} ({p_rate * 100:.1f}%), 95% Wilson CI: [{p_ci[0] * 100:.1f}%, {p_ci[1] * 100:.1f}%]")

    push_fn = lambda obs: np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)
    u_succ, _, u_rate, u_ci, _ = evaluate_policy(env, push_fn, seeds)
    print(f"Constant push:   {u_succ}/{n_eval} ({u_rate * 100:.1f}%), 95% Wilson CI: [{u_ci[0] * 100:.1f}%, {u_ci[1] * 100:.1f}%]")

    protocol = Protocol(
        name="capstone_a_drawer",
        hypothesis="A coordinated finite-state policy achieves >= 90% success while constant action policies achieve 0%.",
        task="articulated.xml cabinet drawer opening to >= 0.10 m",
        initial_states="arm at pre-grasp with +/- 0.01 rad noise, drawer slide in [0, 0.015] m",
        success="drawer slide qpos >= 0.10 m within 100 steps",
        metric="task success rate with 95% Wilson score interval",
        eval_seeds=tuple(seeds),
        falsified_if="capstone checker failure, scripted success < 90%, or constant action success > 5%",
    )

    models_info = {
        "articulated": (env.model, model_path("articulated")),
    }

    results = {
        "scripted_policy": {
            "successes": s_succ,
            "total": n_eval,
            "rate": s_rate,
            "wilson_ci_95": list(s_ci),
        },
        "baselines": {
            "zero_action": {"successes": z_succ, "rate": z_rate, "wilson_ci_95": list(z_ci)},
            "constant_pull": {"successes": p_succ, "rate": p_rate, "wilson_ci_95": list(p_ci)},
            "constant_push": {"successes": u_succ, "rate": u_rate, "wilson_ci_95": list(u_ci)},
        },
    }

    record = run_record(
        protocol=protocol,
        models=models_info,
        config={"action_mode": "ee_delta", "max_episode_steps": 100, "ee_step": env.ee_step},
        results=results,
    )

    out_path = Path(__file__).resolve().parent / "run_record.json"
    save(record, out_path)
    print(f"Saved run record to {out_path}")

    assert s_rate >= 0.90, f"Scripted policy failed acceptance: {s_rate * 100:.1f}% < 90%"
    assert z_rate <= 0.05, f"Zero action baseline too high: {z_rate * 100:.1f}% > 5%"
    assert p_rate <= 0.05, f"Constant pull baseline too high: {p_rate * 100:.1f}% > 5%"
    print("All protocol acceptance criteria met successfully.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
