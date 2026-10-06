from __future__ import annotations

import itertools

import numpy as np

from mjcourse.tabletop import OBJECTS, ZONES

OBJECT_NAMES = {"red": ["red puck", "red disc"], "green": ["green puck", "green disc"], "blue": ["blue puck", "blue disc"]}
OBJECT_SYNONYMS = {"red": ["crimson puck", "scarlet disc"], "green": ["emerald puck", "lime disc"],
                   "blue": ["azure puck", "navy disc"]}
ZONE_NAMES = {"upper": ["upper zone", "top zone"], "lower": ["lower zone", "bottom zone"],
              "left": ["left zone", "left area"], "right": ["right zone", "right area"]}
ZONE_SYNONYMS = {"upper": ["upper region"], "lower": ["bottom region"], "left": ["left patch"], "right": ["right patch"]}
TRAIN_TEMPLATES = ["push the {obj} to the {zone}", "move the {obj} into the {zone}", "slide the {obj} to the {zone}",
                   "put the {obj} in the {zone}", "get the {obj} into the {zone}", "{obj} to the {zone}"]
HELD_OUT_TEMPLATES = ["shove the {obj} over to the {zone}", "nudge the {obj} until it is in the {zone}",
                      "the {zone} should receive the {obj}"]
ALL_PAIRS = list(itertools.product(OBJECTS, ZONES))
HELD_OUT_PAIRS = [("red", "left"), ("green", "upper"), ("blue", "right")]
TRAIN_PAIRS = [p for p in ALL_PAIRS if p not in HELD_OUT_PAIRS]
MAX_TOKENS = 12
PAD, UNK = "<pad>", "<unk>"


def instructions(split: str) -> list[tuple[str, tuple[str, str]]]:
    out = []
    if split == "train":
        for (obj, zone), t in itertools.product(TRAIN_PAIRS, TRAIN_TEMPLATES):
            out += [(t.format(obj=o, zone=z), (obj, zone)) for o in OBJECT_NAMES[obj] for z in ZONE_NAMES[zone]]
    elif split == "paraphrase":
        for (obj, zone), t in itertools.product(TRAIN_PAIRS, HELD_OUT_TEMPLATES):
            out += [(t.format(obj=o, zone=z), (obj, zone)) for o in OBJECT_NAMES[obj] for z in ZONE_NAMES[zone]]
    elif split == "synonym":
        for (obj, zone), t in itertools.product(TRAIN_PAIRS, TRAIN_TEMPLATES):
            out += [(t.format(obj=o, zone=z), (obj, zone)) for o in OBJECT_SYNONYMS[obj] for z in ZONE_SYNONYMS[zone]]
    elif split == "composition":
        for (obj, zone), t in itertools.product(HELD_OUT_PAIRS, TRAIN_TEMPLATES):
            out += [(t.format(obj=o, zone=z), (obj, zone)) for o in OBJECT_NAMES[obj] for z in ZONE_NAMES[zone]]
    else:
        raise ValueError(split)
    return out


class Tokenizer:
    def __init__(self, texts: list[str]):
        words = sorted({w for t in texts for w in t.lower().split()})
        self.vocab = [PAD, UNK] + words
        self.index = {w: i for i, w in enumerate(self.vocab)}

    def __call__(self, text: str) -> np.ndarray:
        ids = [self.index.get(w, 1) for w in text.lower().split()][:MAX_TOKENS]
        return np.array(ids + [0] * (MAX_TOKENS - len(ids)), dtype=np.int64)

    def unknown(self, text: str) -> list[str]:
        return [w for w in text.lower().split() if w not in self.index]


def default_tokenizer() -> Tokenizer:
    return Tokenizer([t for t, _ in instructions("train")])


SPLITS = ("train", "paraphrase", "synonym", "composition")
