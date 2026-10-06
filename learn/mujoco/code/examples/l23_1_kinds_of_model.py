import mujoco
import numpy as np

from mjcourse import tabletop as tt
from mjcourse.worldmodel import data, standard

H = 10


def segment(seed: int, rng: np.random.Generator):
    task = (tt.OBJECTS[rng.integers(3)], list(tt.ZONES)[rng.integers(4)])
    scene = tt.Tabletop()
    scene.reset(tt.sample_layout(rng, task))
    policy = lambda s: rng.uniform(-1, 1, 2) if rng.random() < 0.2 else np.clip(tt.expert(s, task) + rng.normal(0, 0.3, 2), -1, 1)
    for _ in range(int(rng.integers(0, 100))):
        scene.step(policy(scene.state()))
    full = np.zeros(mujoco.mj_stateSize(scene.model, mujoco.mjtState.mjSTATE_INTEGRATION))
    mujoco.mj_getState(scene.model, scene.data, full, mujoco.mjtState.mjSTATE_INTEGRATION)
    s0, actions, path = scene.state(), [], [scene.state()]
    for _ in range(H):
        actions.append(policy(path[-1]))
        scene.step(actions[-1])
        path.append(scene.state())
    scene.close()
    touched = data.contact_share([{"states": np.array(path)}]) > 0
    return s0, full, np.array(actions), path[-1], task, touched


def mujoco_prediction(full: np.ndarray, actions: np.ndarray, friction: float = 0.4) -> np.ndarray:
    scene = tt.Tabletop(tt.Variation(friction=friction))
    mujoco.mj_setState(scene.model, scene.data, full, mujoco.mjtState.mjSTATE_INTEGRATION)
    mujoco.mj_forward(scene.model, scene.data)
    for a in actions:
        scene.step(a)
    out = scene.state()
    scene.close()
    return out


def hand_written(s0: np.ndarray, actions: np.ndarray) -> np.ndarray:
    s = s0.copy()
    tau, dt = 0.5 / 40.0, tt.CONTROL_DT
    for a in actions:
        v_cmd = np.clip(a, -1, 1) * tt.MAX_SPEED
        v0 = s[2:4].copy()
        decay = np.exp(-dt / tau)
        s[2:4] = v_cmd + (v0 - v_cmd) * decay
        s[0:2] += v_cmd * dt + (v0 - v_cmd) * tau * (1 - decay)
        s[4:] = np.r_[[s[4 + 4 * i:6 + 4 * i].tolist() + [0.0, 0.0] for i in range(3)]].ravel()
    return s


def main() -> None:
    mlp = standard.model("one_step")
    rng = np.random.default_rng(23)
    rows = {name: {"contact": [], "free": []} for name in ("MuJoCo", "MuJoCo, wrong friction", "hand-written", "learned",
                                                           "nothing moves")}
    for _ in range(200):
        s0, full, a, true, task, touched = segment(23, rng)
        target = 4 + 4 * tt.OBJECTS.index(task[0])
        predictions = {"MuJoCo": mujoco_prediction(full, a), "MuJoCo, wrong friction": mujoco_prediction(full, a, 0.3),
                       "hand-written": hand_written(s0, a), "learned": mlp.rollout(s0[None], a[None].astype(np.float32))[0, -1],
                       "nothing moves": s0}
        for name, p in predictions.items():
            rows[name]["contact" if touched else "free"].append(
                (np.linalg.norm(p[:2] - true[:2]), np.linalg.norm(p[target:target + 2] - true[target:target + 2])))
    n_contact = len(rows["MuJoCo"]["contact"])
    print(f"200 test segments of 1 s; the pusher touched a puck in {n_contact} of them")
    print(f"  {'model':<24}{'pusher, no contact':>20}{'puck, no contact':>18}{'pusher, contact':>18}{'puck, contact':>16}"
          "   (mean error, mm)")
    for name, r in rows.items():
        free, contact = np.array(r["free"]) * 1000, np.array(r["contact"]) * 1000
        print(f"  {name:<24}{free[:, 0].mean():>20.2f}{free[:, 1].mean():>18.2f}{contact[:, 0].mean():>18.2f}"
              f"{contact[:, 1].mean():>16.2f}")


if __name__ == "__main__":
    main()
