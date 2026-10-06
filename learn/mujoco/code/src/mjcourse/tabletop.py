"""The tabletop pushing scene shared by the VLA and world-model tracks (Levels 22 and 23).

A task is (object, zone): push the named puck into the named zone. A layout places the pusher and
the three pucks. The pusher is commanded by a planar velocity; one action is held for CONTROL_DT
(20 physics steps of 5 ms), and actions are in [-1, 1] times MAX_SPEED.

    scene = Tabletop()
    scene.reset(layout)                      # a Layout from sample_layout
    rgb = scene.render("top", 64)            # (64, 64, 3) uint8
    scene.step(expert(scene.state(), task))  # state: the 14-vector of planar positions and velocities
    scene.success(task)

The state vector (STATE_NAMES) is planar: pusher x, y, vx, vy, then x, y, vx, vy for each puck in
OBJECTS order. Puck heights, tilts and spins are left out: the table holds the pucks flat and the
pucks are round. Variations for the evaluation axes of Lesson 22.5 are applied by `Variation`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import mujoco
import numpy as np

from mjcourse.paths import model_path

OBJECTS = ("red", "green", "blue")
ZONES = {"upper": np.array([0.21, 0.0]), "lower": np.array([-0.21, 0.0]),
         "left": np.array([0.0, 0.21]), "right": np.array([0.0, -0.21])}
CONTROL_DT = 0.1            # s per action
MAX_SPEED = 0.2             # m/s at action 1
SUCCESS_RADIUS = 0.05       # m, puck centre to zone centre
EPISODE_STEPS = 120         # 12 s
PUCK_RADIUS, PUSHER_RADIUS = 0.03, 0.015
STATE_NAMES = tuple(["pusher_x", "pusher_y", "pusher_vx", "pusher_vy"]
                    + [f"{o}_{q}" for o in OBJECTS for q in ("x", "y", "vx", "vy")])


@dataclass(frozen=True)
class Layout:
    pusher: tuple[float, float]
    pucks: tuple[tuple[float, float], ...]          # one (x, y) per object, in OBJECTS order


@dataclass(frozen=True)
class Variation:
    """Changes for evaluation axes; the default is the training distribution."""
    puck_radius: float = PUCK_RADIUS
    puck_mass: float = 0.1
    friction: float = 0.4
    pusher_radius: float = PUSHER_RADIUS
    max_speed: float = MAX_SPEED
    colours: dict = field(default_factory=dict)       # e.g. {"red": (0.9, 0.5, 0.1)}: a recoloured object


def sample_layout(rng: np.random.Generator, task: tuple[str, str] | None = None, low: float = -0.2, high: float = 0.2,
                  min_gap: float = 0.1) -> Layout:
    """Pucks at least `min_gap` apart and away from the zones' centres; with `task`, the target puck at least
    0.12 m from its zone. The pusher starts at least 0.08 m from every puck."""
    centres = np.array(list(ZONES.values()))
    while True:
        pucks = rng.uniform(low, high, (3, 2))
        if min(np.linalg.norm(pucks[a] - pucks[b]) for a, b in ((0, 1), (0, 2), (1, 2))) < min_gap:
            continue
        if np.min(np.linalg.norm(pucks[:, None] - centres[None], axis=2)) < SUCCESS_RADIUS + 0.02:
            continue
        if task is not None and np.linalg.norm(pucks[OBJECTS.index(task[0])] - ZONES[task[1]]) < 0.12:
            continue
        pusher = rng.uniform(-0.25, 0.25, 2)
        if np.min(np.linalg.norm(pucks - pusher, axis=1)) < 0.08:
            continue
        return Layout(tuple(pusher), tuple(map(tuple, pucks)))


class Tabletop:
    def __init__(self, variation: Variation | None = None):
        self.variation = variation or Variation()
        self.model = self._build(self.variation)
        self.data = mujoco.MjData(self.model)
        self.frame_skip = round(CONTROL_DT / self.model.opt.timestep)
        self._renderers: dict[int, mujoco.Renderer] = {}
        self._adr = [self.model.jnt_qposadr[self.model.joint(f"{o}_puck").id] for o in OBJECTS]
        self._dof = [self.model.jnt_dofadr[self.model.joint(f"{o}_puck").id] for o in OBJECTS]

    @staticmethod
    def _build(v: Variation) -> mujoco.MjModel:
        spec = mujoco.MjSpec.from_file(str(model_path("tabletop")))
        for o in OBJECTS:
            geom = spec.geom(f"{o}_puck")
            geom.size = [v.puck_radius, 0.01, 0]
            geom.mass = v.puck_mass
            geom.friction = [v.friction, 0.005, 0.0001]
            if o in v.colours:
                geom.rgba = [*v.colours[o], 1]
        spec.geom("table").friction = [v.friction, 0.005, 0.0001]
        spec.geom("pusher").size = [v.pusher_radius, 0.01, 0]
        for name in ("pusher_vx", "pusher_vy"):
            spec.actuator(name).ctrlrange = [-v.max_speed, v.max_speed]
        return spec.compile()

    def reset(self, layout: Layout) -> None:
        m, d = self.model, self.data
        mujoco.mj_resetData(m, d)
        d.qpos[0:2] = layout.pusher
        for adr, (x, y) in zip(self._adr, layout.pucks):
            d.qpos[adr:adr + 7] = [x, y, 0.01, 1, 0, 0, 0]
        mujoco.mj_forward(m, d)

    def step(self, action: np.ndarray) -> None:
        a = np.clip(np.asarray(action, dtype=float), -1.0, 1.0)
        self.data.ctrl[:] = a * self.variation.max_speed
        for _ in range(self.frame_skip):
            mujoco.mj_step(self.model, self.data)

    def state(self) -> np.ndarray:
        d = self.data
        parts = [d.qpos[0:2], d.qvel[0:2]]
        for adr, dof in zip(self._adr, self._dof):
            parts += [d.qpos[adr:adr + 2], d.qvel[dof:dof + 2]]
        return np.concatenate(parts).copy()

    def puck(self, obj: str) -> np.ndarray:
        adr = self._adr[OBJECTS.index(obj)]
        return self.data.qpos[adr:adr + 2].copy()

    def success(self, task: tuple[str, str]) -> bool:
        return bool(np.linalg.norm(self.puck(task[0]) - ZONES[task[1]]) < SUCCESS_RADIUS)

    def render(self, camera: str = "top", size: int = 64, depth: bool = False) -> np.ndarray:
        if size not in self._renderers:
            self._renderers[size] = mujoco.Renderer(self.model, size, size)
        r = self._renderers[size]
        mujoco.mj_forward(self.model, self.data)
        if depth:
            r.enable_depth_rendering()
        r.update_scene(self.data, camera)
        image = r.render().copy()
        if depth:
            r.disable_depth_rendering()
        return image

    def close(self) -> None:
        for r in self._renderers.values():
            r.close()
        self._renderers.clear()


def _toward(u: np.ndarray, target: np.ndarray, gain: float) -> np.ndarray:
    """Velocity (in action units) toward a point: full speed when far, proportional when near."""
    delta = target - u
    speed = min(1.0, gain * np.linalg.norm(delta))
    return speed * delta / (np.linalg.norm(delta) + 1e-9)


def switching_expert(state: np.ndarray, task: tuple[str, str], push_speed: float = 0.6, lateral_gain: float = 40.0) -> np.ndarray:
    """The first demonstrator: a controller that switches between going around and pushing (Lesson 22.4
    measures why a policy cannot clone it). Uses the true state.

    A puck pushed by a round pusher moves along the line of centres. The controller keeps the pusher on
    the line from the goal through the puck, behind it, and pushes along that line, slowing down while
    it corrects any sideways offset. Outside a narrow cone behind the puck it first drives, at full
    speed, to a point behind the puck, through a point beside it if the puck is in the way.
    """
    u = state[0:2]
    i = 4 + 4 * OBJECTS.index(task[0])
    p, g = state[i:i + 2], ZONES[task[1]]
    dist = np.linalg.norm(g - p)
    if dist < 0.01:
        return np.zeros(2)
    d = (g - p) / dist
    n = np.array([-d[1], d[0]])
    r = PUCK_RADIUS + PUSHER_RADIUS
    along, lateral = (u - p) @ d, (u - p) @ n
    if -1.6 * r < along < -0.5 * r and abs(lateral) < 0.45 * r:          # in the cone: push
        slow = max(0.0, 1.0 - abs(lateral) / (0.45 * r))
        v = push_speed * slow * min(1.0, dist / 0.04 + 0.25) * d
        v += -lateral_gain * lateral * n                                 # back onto the line
        v += 10.0 * (-(r - 0.003) - along) * d                           # keep in contact
        return np.clip(v, -1.0, 1.0)
    behind = p - d * (r + 0.015)
    if along > -0.5 * r and abs(lateral) < r + 0.012:                    # in the way: step out sideways
        side = 1.0 if lateral >= 0 else -1.0
        return _toward(u, p + n * side * (r + 0.025) - d * 0.5 * r, 15.0)
    return _toward(u, behind, 15.0)                                       # clear of the puck: go behind it


def _smoothstep(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def expert(state: np.ndarray, task: tuple[str, str], push_speed: float = 0.6, lateral_gain: float = 30.0,
           side_width: float = 0.006) -> np.ndarray:
    """The demonstrator: one continuous velocity field that uses the true state (privileged).

    Three fields are blended with smooth weights instead of switched: go to the point behind the puck on
    the line to the zone; while ahead of or beside the puck, also circle around it (the side follows a
    steep tanh of the sideways offset, not its sign) and keep clear of it; once behind it and on the
    line, push along the line while correcting the sideways offset. A policy has to approximate this
    function from examples, and a continuous function is far easier to fit than a switching one.
    """
    u = state[0:2]
    i = 4 + 4 * OBJECTS.index(task[0])
    p, g = state[i:i + 2], ZONES[task[1]]
    dist = np.linalg.norm(g - p)
    d = (g - p) / (dist + 1e-9)
    n = np.array([-d[1], d[0]])
    r = PUCK_RADIUS + PUSHER_RADIUS
    rel = u - p
    along, lateral, gap = rel @ d, rel @ n, np.linalg.norm(rel)
    finish = min(1.0, dist / 0.03)                                       # slow to a stop at the zone centre
    push = push_speed * finish * d - lateral_gain * lateral * n + 10.0 * (-(r - 0.003) - along) * d
    behind = p - d * (r + 0.02)
    approach = _toward(u, behind, 15.0)
    front = _smoothstep((along + 0.6 * r) / (0.6 * r))                 # 0 behind the puck, 1 beside or ahead
    near = np.exp(-((gap - r) / 0.03) ** 2) if gap > r else 1.0
    circle = np.tanh(lateral / side_width) * n * front * near
    clear = rel / (gap + 1e-9) * max(0.0, (r + 0.015 - gap) / 0.015) * front
    w = _smoothstep((-along - 0.45 * r) / (0.35 * r)) * np.exp(-(lateral / (0.45 * r)) ** 2)
    v = w * push + (1 - w) * (approach + circle + clear)
    return np.clip(v, -1.0, 1.0)
