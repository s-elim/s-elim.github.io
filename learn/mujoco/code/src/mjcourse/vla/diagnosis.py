from __future__ import annotations

import numpy as np

from mjcourse import tabletop as tt
from mjcourse.vla import evaluation, language, train

STAGES = ("controller", "perception", "language grounding", "spatial reasoning", "action prediction", "contact")
CANONICAL = "push the {obj} puck to the {zone} zone"


def _layout(record: dict) -> tt.Layout:
    return tt.Layout(tuple(record["layout"]["pusher"]), tuple(tuple(p) for p in record["layout"]["pucks"]))


def _variation_camera(condition: str):
    variation = {"larger pucks": tt.Variation(puck_radius=0.036), "recoloured": tt.Variation(colours=evaluation.RECOLOURED),
                 "larger pusher": tt.Variation(pusher_radius=0.025), "slower pusher": tt.Variation(max_speed=0.15)}.get(condition)
    return variation, "top_shifted" if condition == "camera shifted" else "top"


def replay(model, record: dict, text: str | None = None, takeover: int | None = None) -> dict:
    variation, camera = _variation_camera(record["condition"])
    task = tuple(record["task"])
    scene = tt.Tabletop(variation)
    scene.reset(_layout(record))
    policy = train.VLAPolicy(model, language.default_tokenizer())
    policy.reset()
    words = text or record["text"]
    start = scene.state()
    for t in range(tt.EPISODE_STEPS):
        s = scene.state()
        a = tt.expert(s, task) if takeover is not None and t >= takeover else policy.act(t, scene.render(camera, 64), words, s)
        scene.step(a)
        if scene.success(task) and np.linalg.norm(scene.state()[4 + 4 * tt.OBJECTS.index(task[0]) + 2:][:2]) < 0.02:
            break
    final = scene.state()
    target = tt.OBJECTS.index(task[0])
    moved = [np.linalg.norm(final[4 + 4 * k:6 + 4 * k] - start[4 + 4 * k:6 + 4 * k]) for k in range(3)]
    moved_wrong = max(m for k, m in enumerate(moved) if k != target) > 0.02 and moved[target] < 0.02
    displacement = final[4 + 4 * target:6 + 4 * target] - start[4 + 4 * target:6 + 4 * target]
    to_zone = tt.ZONES[task[1]] - start[4 + 4 * target:6 + 4 * target]
    away = np.linalg.norm(displacement) > 0.02 and displacement @ to_zone < 0.5 * np.linalg.norm(displacement) * np.linalg.norm(to_zone)
    scene.close()
    return {"success": scene_success(final, task), "moved_wrong": bool(moved_wrong), "pushed_away": bool(away)}


def scene_success(state: np.ndarray, task) -> bool:
    i = 4 + 4 * tt.OBJECTS.index(task[0])
    return bool(np.linalg.norm(state[i:i + 2] - tt.ZONES[task[1]]) < tt.SUCCESS_RADIUS)


def diagnose(record: dict, model, oracle) -> dict:
    evidence = {}
    evidence["velocity_error"] = record["velocity_error"]
    if record["velocity_error"] > 0.03:
        return {"stage": "controller", "evidence": evidence}
    evidence["oracle"] = replay(oracle, record)["success"]
    if evidence["oracle"]:
        return {"stage": "perception", "evidence": evidence}
    obj, zone = record["task"]
    canonical = replay(model, record, text=CANONICAL.format(obj=obj, zone=zone))
    evidence["canonical_instruction"] = canonical["success"]
    if canonical["success"]:
        return {"stage": "language grounding", "evidence": evidence}
    if canonical["moved_wrong"] or canonical["pushed_away"]:
        evidence.update(moved_wrong=canonical["moved_wrong"], pushed_away=canonical["pushed_away"])
        return {"stage": "spatial reasoning", "evidence": evidence}
    takeover = replay(model, record, takeover=tt.EPISODE_STEPS // 2)
    evidence["expert_takeover"] = takeover["success"]
    if takeover["success"]:
        return {"stage": "action prediction", "evidence": evidence}
    return {"stage": "contact", "evidence": evidence}
