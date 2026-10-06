from __future__ import annotations

import os
import numpy as np

from mjcourse.vla.franka import FrankaVLA, franka_expert_action


FAST = os.environ.get("MJC_FAST") == "1"
STEPS = 20 if FAST else 120


def main() -> None:
    print("Initializing 7-DOF Franka Emika Panda VLA simulator in MuJoCo...")
    env = FrankaVLA()

    # (1) Topology
    nq, nv, nu = env.model.nq, env.model.nv, env.model.nu
    print(f"Topology: nq = {nq}, nv = {nv}, nu = {nu} actuators (7 arm torques + 1 gripper)")

    # (2) Observations
    pos, quat = env.tcp_pose()
    state_no_vel = env.state(include_velocity=False)
    state_with_vel = env.state(include_velocity=True)
    print(f"TCP Pose: position = {np.round(pos, 3)}, quaternion = {np.round(quat, 3)}")
    print(f"Proprioception: {len(state_no_vel)} dims (position-only) vs {len(state_with_vel)} dims (with velocity)")

    # (3) Dual-camera rendering
    img_top = env.render("top", width=64, height=64)
    img_wrist = env.render("gripper/wrist", width=64, height=64)
    print(f"Rendered views: top = {img_top.shape}, wrist = {img_wrist.shape}")

    # (4) Rollout
    task = ("red_cube", "tray")
    env.reset(seed=42, task=task)
    print(f"Task: move {task[0]} to {task[1]}")

    success = False
    for t in range(STEPS):
        action = franka_expert_action(env)
        step_result = env.step(action)
        if step_result["success"]:
            success = True
            print(f"Goal achieved at step {t} (distance to tray = {step_result['dist_to_target'] * 1000:.1f} mm)")
            break

    if not success:
        print(f"Rollout finished: final distance to target = {step_result['dist_to_target'] * 1000:.1f} mm")

    env.close()
    print("7-DOF Franka VLA simulation interface verified.")


if __name__ == "__main__":
    main()
