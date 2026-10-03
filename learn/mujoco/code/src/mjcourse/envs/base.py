"""A Gymnasium environment written directly on MuJoCo (Lesson 12.1).

Nothing is hidden behind a library base class: the model is loaded, the episode is
reset from a keyframe, the task randomizes its initial state from the environment's
own generator (`self.np_random`, seeded by `reset(seed=...)`), each `step` holds one
action for `frame_skip` physics steps, and the episode is truncated by the
environment itself after `max_episode_steps`.

Subclasses implement `_reset_task`, `_apply_action`, `_get_obs`, `_reward` and
`_terminal`, and declare `observation_space` and `action_space`.
"""

from __future__ import annotations

import gymnasium as gym
import mujoco
import numpy as np

from mjcourse.paths import model_path


class MujocoEnv(gym.Env):
    metadata = {"render_modes": ["rgb_array"], "render_fps": 20}

    def __init__(self, model: str, frame_skip: int, max_episode_steps: int, keyframe: str = "home",
                 render_mode: str | None = None, camera: str | int = -1, width: int = 320, height: int = 240):
        self.model = mujoco.MjModel.from_xml_path(str(model_path(model)))
        self.data = mujoco.MjData(self.model)
        self.frame_skip, self.max_episode_steps = frame_skip, max_episode_steps
        self.dt = self.model.opt.timestep * frame_skip          # seconds per environment step
        self.metadata = {**self.metadata, "render_fps": round(1.0 / self.dt)}
        self.keyframe = self.model.key(keyframe).id
        if render_mode is not None and render_mode not in self.metadata["render_modes"]:
            raise ValueError(f"render_mode must be one of {self.metadata['render_modes']}")
        self.render_mode, self.camera, self.size = render_mode, camera, (width, height)
        self._renderer: mujoco.Renderer | None = None
        self._steps = 0

    # ------------------------------------------------------------- Gymnasium API

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)                                  # seeds self.np_random on the first call or when given
        mujoco.mj_resetDataKeyframe(self.model, self.data, self.keyframe)
        self._reset_task(options or {})
        mujoco.mj_forward(self.model, self.data)
        self._steps = 0
        return self._get_obs(), self._get_info()

    def step(self, action):
        action = np.asarray(action, dtype=np.float64)
        if action.shape != self.action_space.shape:
            raise ValueError(f"action shape {action.shape}, expected {self.action_space.shape}")
        action = np.clip(action, self.action_space.low, self.action_space.high)
        self._apply_action(action)                                # sets controller targets or ctrl
        for _ in range(self.frame_skip):
            self._control()                                       # inner controller at the physics rate
            mujoco.mj_step(self.model, self.data)
        mujoco.mj_forward(self.model, self.data)                  # positions after the last step, not before it
        self._steps += 1
        obs = self._get_obs()
        terminated = self._terminal()                             # the task decided: success or failure
        truncated = self._steps >= self.max_episode_steps and not terminated   # time ran out
        return obs, float(self._reward(action)), terminated, truncated, self._get_info()

    def render(self):
        if self.render_mode != "rgb_array":
            return None
        if self._renderer is None:
            self._renderer = mujoco.Renderer(self.model, self.size[1], self.size[0])
        self._renderer.update_scene(self.data, self.camera)
        return self._renderer.render()

    def close(self):
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None

    # ------------------------------------------------------------- for subclasses

    def _reset_task(self, options: dict) -> None:
        raise NotImplementedError

    def _apply_action(self, action: np.ndarray) -> None:
        raise NotImplementedError

    def _control(self) -> None:
        """Called before every physics step; the default leaves data.ctrl as it is."""

    def _get_obs(self) -> np.ndarray:
        raise NotImplementedError

    def _reward(self, action: np.ndarray) -> float:
        raise NotImplementedError

    def _terminal(self) -> bool:
        return False

    def _get_info(self) -> dict:
        return {}
