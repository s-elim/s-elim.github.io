"""mjcourse.capstone: the course's push task passes, a leaking variant fails."""

from mjcourse import capstone
from mjcourse.envs import PushEnv


def test_push_env_passes():
    results = capstone.check(lambda: PushEnv(action_mode="ee_delta", max_episode_steps=20), object_body="puck")
    assert all(ok for ok, _ in results.values()), results


def test_a_leak_fails():
    results = capstone.check(lambda: PushEnv(action_mode="ee_delta", max_episode_steps=20,
                                             extra_observations=("puck_velocity",)), object_body="puck")
    assert not results["observation sources are sensors"][0]
    assert not results["no privileged quantity leaks"][0]


def test_command_line_exit_codes(capsys):
    assert capstone.main(["mjcourse.envs.push:PushEnv", "--kwargs", '{"action_mode": "ee_delta", "max_episode_steps": 20}',
                          "--object", "puck"]) == 0
    assert "PASS  gymnasium check_env" in capsys.readouterr().out
    assert capstone.main(["mjcourse.envs.push:PushEnv", "--kwargs",
                          '{"action_mode": "ee_delta", "max_episode_steps": 20, "extra_observations": ["puck_velocity"]}',
                          "--object", "puck"]) == 1
