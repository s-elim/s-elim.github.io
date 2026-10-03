"""Lesson 16.1: language-conditioned pick-and-place, and the two ways instructions generalize.

INPUT   pick_place.xml (three cubes, a tray, a left and a right zone); Lesson 10.2's pipeline
PROCESS (1) 30 instruction templates over 3 objects and 3 destinations: 18 for training,
            12 held-out paraphrases (new wording and synonyms); 3 of the 9 object-destination
            combinations held out. Splits: training (training templates, training
            combinations), held-out paraphrases, held-out combinations;
        (2) three instruction-to-goal baselines evaluated on each split: a scripted keyword
            parser, a bag-of-words classifier over joint (object, destination) labels, and
            the same classifier factorized into an object head and a destination head;
        (3) the keyword parser driving the scripted pick-and-place on 15 instructions per
            split, with all three cubes on the table: parse and task success
OUTPUT  printed tables

Run:  python examples/l16_1_language.py
"""

import itertools
import math
import os
import sys
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import l10_2_pick_place as pp  # noqa: E402  (the pipeline of Lesson 10.2)

FAST = os.environ.get("MJC_FAST") == "1"
OBJECTS = {"red_cube": ("red cube", "red block"), "green_cube": ("green cube", "green block"),
           "blue_cube": ("blue cube", "blue block")}
SYNONYMS = {"red_cube": "crimson block", "green_cube": "emerald cube", "blue_cube": "azure block"}
GOALS = {"tray": ("tray", "tray"), "left_zone": ("left zone", "zone on the left"),
         "right_zone": ("right zone", "zone on the right")}
GOAL_SYNONYMS = {"tray": "bin", "left_zone": "left pad", "right_zone": "right pad"}
TRAIN_TEMPLATES = [
    "put the {o} in the {g}", "place the {o} in the {g}", "move the {o} to the {g}", "put the {o} on the {g}",
    "pick up the {o} and put it in the {g}", "pick up the {o} and place it on the {g}", "take the {o} to the {g}",
    "bring the {o} to the {g}", "the {o} goes in the {g}", "carry the {o} to the {g}", "set the {o} on the {g}",
    "drop the {o} in the {g}", "move the {o} onto the {g}", "place the {o} into the {g}", "please put the {o} in the {g}",
    "grab the {o} and move it to the {g}", "the {g} is where the {o} goes", "lift the {o} and put it on the {g}"]
PARAPHRASE_TEMPLATES = [
    "could you transfer the {o} over to the {g}", "relocate the {o} to the {g}", "i would like the {o} in the {g}",
    "deposit the {o} into the {g}", "the {o} belongs on the {g}", "shift the {o} across to the {g}",
    "put the {O} in the {G}", "move the {O} to the {G}", "place the {O} on the {G}", "the {O} goes in the {g}",
    "take the {o} to the {G}", "kindly deposit the {O} in the {G}"]
HELD_OUT_PAIRS = {("blue_cube", "tray"), ("red_cube", "left_zone"), ("green_cube", "right_zone")}
PAIRS = list(itertools.product(OBJECTS, GOALS))
TRAIN_PAIRS = [p for p in PAIRS if p not in HELD_OUT_PAIRS]


def instructions(templates, pairs, rng) -> list[tuple[str, tuple[str, str]]]:
    out = []
    for t in templates:
        for obj, goal in pairs:
            text = t.format(o=OBJECTS[obj][rng.integers(2)], g=GOALS[goal][rng.integers(2)],
                            O=SYNONYMS[obj], G=GOAL_SYNONYMS[goal])
            out.append((text, (obj, goal)))
    return out


def splits() -> dict:
    rng = np.random.default_rng(0)
    return {"training": instructions(TRAIN_TEMPLATES, TRAIN_PAIRS, rng),
            "held-out paraphrases": instructions(PARAPHRASE_TEMPLATES, TRAIN_PAIRS, rng),
            "held-out combinations": instructions(TRAIN_TEMPLATES, sorted(HELD_OUT_PAIRS), rng)}


# ---------------------------------------------------------------- baselines

def keyword_parser(text: str):
    """Scripted: colour words name the object, destination words the goal; None if either is missing."""
    words = text.split()
    obj = next((o for o, c in (("red_cube", "red"), ("green_cube", "green"), ("blue_cube", "blue")) if c in words), None)
    if "tray" in words:
        goal = "tray"
    elif "zone" in words and ("left" in words or "right" in words):
        goal = "left_zone" if "left" in words else "right_zone"
    else:
        goal = None
    return (obj, goal) if obj and goal else None


class NaiveBayes:
    """Multinomial naive Bayes over word counts with add-one smoothing."""

    def fit(self, texts, labels):
        self.vocab = sorted({w for t in texts for w in t.split()})
        self.index = {w: i for i, w in enumerate(self.vocab)}
        self.classes = sorted(set(labels))
        counts = np.ones((len(self.classes), len(self.vocab)))
        prior = np.zeros(len(self.classes))
        for t, y in zip(texts, labels):
            c = self.classes.index(y)
            prior[c] += 1
            for w in t.split():
                counts[c, self.index[w]] += 1
        self.log_prior = np.log(prior / prior.sum())
        self.log_like = np.log(counts / counts.sum(axis=1, keepdims=True))
        return self

    def predict(self, text):
        known = [self.index[w] for w in text.split() if w in self.index]
        return self.classes[int(np.argmax(self.log_prior + self.log_like[:, known].sum(axis=1)))]


def part1_2(data: dict) -> None:
    print(f"  templates: {len(TRAIN_TEMPLATES)} training, {len(PARAPHRASE_TEMPLATES)} held-out paraphrases; "
          f"combinations: {len(TRAIN_PAIRS)} training, {len(HELD_OUT_PAIRS)} held out {sorted(HELD_OUT_PAIRS)}")
    for name, items in data.items():
        print(f"  {name:<22} {len(items):>4} instructions, e.g. \"{items[1][0]}\"")
    train_texts, train_labels = zip(*data["training"])
    joint = NaiveBayes().fit(train_texts, train_labels)
    obj_head = NaiveBayes().fit(train_texts, [y[0] for y in train_labels])
    goal_head = NaiveBayes().fit(train_texts, [y[1] for y in train_labels])
    baselines = {"keyword parser (scripted)": keyword_parser,
                 "bag of words, joint labels": joint.predict,
                 "bag of words, object and goal heads": lambda t: (obj_head.predict(t), goal_head.predict(t))}
    print(f"\n(2) accuracy of the (object, destination) each baseline returns")
    print(f"  {'baseline':<38}" + "".join(f"{n:>24}" for n in data))
    for name, fn in baselines.items():
        accuracies = [np.mean([fn(t) == y for t, y in items]) for items in data.values()]
        print(f"  {name:<38}" + "".join(f"{a:>24.2f}" for a in accuracies))
    vocab = set(joint.vocab)
    unseen = sorted({w for t, _ in data["held-out paraphrases"] for w in t.split() if w not in vocab})
    print(f"  words in held-out paraphrases never seen in training: {', '.join(unseen)}")


# ---------------------------------------------------------------- executing instructions

class SceneEpisode(pp.Episode):
    """Lesson 10.2's episode with all three cubes placed on the table and any one as the target."""

    def __init__(self, layout: dict[str, tuple[float, float, float]], target: str):
        red = layout["red_cube"]
        super().__init__(np.array(red[:2]), red[2])
        m, d = self.model, self.data
        for name in ("green_cube", "blue_cube"):
            x, y, yaw = layout[name]
            adr = m.jnt_qposadr[m.joint(name).id]
            d.qpos[adr:adr + 7] = [x, y, 0.02, math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]
        mujoco.mj_forward(m, d)
        self.cube, self.cube_geom = m.body(target).id, m.geom(target).id


def layout(rng) -> dict:
    """Three cubes at least 8 cm apart in the 10.2 area."""
    while True:
        xy = np.c_[rng.uniform(*pp.AREA[0], 3), rng.uniform(*pp.AREA[1], 3)]
        if min(np.linalg.norm(a - b) for a, b in itertools.combinations(xy, 2)) > 0.08:
            return {n: (*p, rng.uniform(-math.pi / 4, math.pi / 4)) for n, p in zip(OBJECTS, xy)}


def execute(scene: dict, obj: str, goal: str) -> bool:
    ep = SceneEpisode(scene, obj)
    dest = ep.data.site("tray_center" if goal == "tray" else goal).xpos[:2].copy()
    half, release = (0.07, 0.07) if goal == "tray" else (0.06, 0.05)
    yaw = (scene[obj][2] + math.pi / 4) % (math.pi / 2) - math.pi / 4
    cube = ep.cube_pos()[:2]
    steps = [(np.r_[cube, 0.15], yaw, 1.5), (np.r_[cube, 0.022], yaw, 1.0)]
    if not all(ep.move_to(p, y, t) for p, y, t in steps):
        return False
    ep.grip(pp.CLOSED)
    for p, y, t in ((np.r_[cube, 0.15], yaw, 1.0), (np.r_[dest, 0.15], 0.0, 1.5), (np.r_[dest, release], 0.0, 0.8)):
        if not ep.move_to(p, y, t):
            return False
    ep.grip(pp.OPEN, 0.5)
    ep.move_to(np.r_[dest, 0.15], 0.0, 0.8)
    ep.step(round(0.5 / pp.H))
    p = ep.cube_pos()
    return bool(abs(p[0] - dest[0]) < half and abs(p[1] - dest[1]) < half and p[2] < 0.06)


def part3(data: dict) -> None:
    n = 4 if FAST else 15
    rng = np.random.default_rng(16)
    print(f"  {'split':<24}{'parsed correctly':>18}{'task success':>15}   (keyword parser, {n} instructions each)")
    for name, items in data.items():
        picks = [items[i] for i in rng.choice(len(items), n, replace=False)]
        parsed = executed = 0
        for text, truth in picks:
            guess = keyword_parser(text)
            if guess == truth:
                parsed += 1
                executed += execute(layout(rng), *guess)
        print(f"  {name:<24}{parsed:>15d}/{n}{executed:>12d}/{n}")
    print("  task success counts the target cube inside its destination after release")


if __name__ == "__main__":
    data = splits()
    print(f"MuJoCo {mujoco.__version__}")
    print("(1) instruction splits")
    part1_2(data)
    print("(3) instructions executed by the scripted pick-and-place")
    part3(data)
