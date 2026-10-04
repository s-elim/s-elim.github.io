"""mjcourse.experiment: fingerprints catch model edits, records serialize."""

import dataclasses
import json

import mujoco
import pytest

from mjcourse import experiment, model_path


def load():
    return mujoco.MjModel.from_xml_path(str(model_path("point_mass")))


def test_fingerprint_is_stable_across_loads():
    assert experiment.model_fingerprint(load()) == experiment.model_fingerprint(load())


def test_fingerprint_changes_with_an_edit_in_code():
    model = load()
    before = experiment.model_fingerprint(model)
    model.dof_damping[0] *= 2
    assert experiment.model_fingerprint(model) != before


def test_fingerprint_changes_with_an_option():
    model = load()
    before = experiment.model_fingerprint(model)
    model.opt.timestep *= 0.5
    assert experiment.model_fingerprint(model) != before


def test_record_serializes(tmp_path):
    protocol = experiment.Protocol(name="t", hypothesis="h", task="reach", initial_states="uniform", success="s",
                                   metric="m", eval_seeds=(1, 2))
    record = experiment.run_record(protocol, {"pm": (load(), model_path("point_mass"))}, {"k": 1}, {"success": 0.5})
    path = experiment.save(record, tmp_path / "run.json")
    loaded = json.loads(path.read_text())
    assert loaded["protocol"]["eval_seeds"] == [1, 2]
    assert loaded["software"]["mujoco"] == mujoco.__version__
    assert len(loaded["models"]["pm"]["fingerprint"]) == 64


def test_protocol_is_frozen():
    protocol = experiment.Protocol(name="t", hypothesis="h", task="t", initial_states="i", success="s", metric="m")
    with pytest.raises(dataclasses.FrozenInstanceError):
        protocol.name = "other"
