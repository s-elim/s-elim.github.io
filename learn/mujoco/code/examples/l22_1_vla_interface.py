import numpy as np
import torch

from mjcourse import tabletop as tt
from mjcourse.vla import language
from mjcourse.vla.model import MiniVLA, VLAConfig
from mjcourse.vla.train import STATE_SCALE


def part1_2() -> None:
    rng = np.random.default_rng(0)
    text, task = language.instructions("train")[0]
    scene = tt.Tabletop()
    scene.reset(tt.sample_layout(rng, task))
    image, state = scene.render("top", 64), scene.state()
    tokenizer = language.default_tokenizer()
    words = tokenizer(text)
    print("(1) one observation")
    print(f"  image        {image.shape} {image.dtype}, values {image.min()} to {image.max()}  (top camera, RGB)")
    print(f"  instruction  {text!r} -> token ids {words.tolist()}  (vocabulary of {len(tokenizer.vocab)} words)")
    print(f"  robot state  {np.round(state[:4], 3).tolist()}  (pusher x, y in m; vx, vy in m/s)")
    print(f"  not observed {state.size - 4} numbers: the pucks' positions and velocities, which the image must supply")
    torch.manual_seed(0)
    model = MiniVLA(VLAConfig(vocab=len(tokenizer.vocab), chunk=1)).eval()
    with torch.no_grad():
        action = model(torch.as_tensor(image).permute(2, 0, 1).float().unsqueeze(0) / 255.0,
                       torch.as_tensor(words).unsqueeze(0),
                       torch.as_tensor((state[:4] * STATE_SCALE)[None], dtype=torch.float32))
    print("(2) the policy's output")
    print(f"  action       {tuple(action.shape)} = (batch, chunk, 2): a pusher velocity in [-1, 1] x {tt.MAX_SPEED} m/s"
          f" (untrained: {[round(float(v), 3) for v in action[0, 0]]})")
    scene.close()


def part3() -> None:
    model = MiniVLA(VLAConfig(vocab=len(language.default_tokenizer().vocab), chunk=1))
    parts = {"vision encoder": model.vision, "word embeddings": model.words, "state encoder": model.state,
             "fusion transformer": model.fusion, "action head": model.head}
    print("(3) parameters")
    for name, module in parts.items():
        print(f"  {name:<20} {sum(p.numel() for p in module.parameters()):>8,d}")
    print(f"  {'total':<20} {sum(p.numel() for p in model.parameters()):>8,d}")


def part4() -> None:
    rows = [("vision-language model", "image(s) + text", "text"),
            ("vision-language-action policy", "image(s) + instruction (+ robot state)", "robot action (or a chunk of them)"),
            ("imitation-learning policy", "any observation", "robot action, learned from demonstrations"),
            ("multimodal policy", "two or more modalities, e.g. image + joint angles", "robot action"),
            ("robot foundation model", "varies; trained on large, diverse robot data", "robot action; meant to be adapted"),
            ("agentic policy", "observation + goal; may call models and keep memory",
             "robot action chosen by a loop of proposals, predictions and selection")]
    print("(4) interfaces")
    for name, inputs, outputs in rows:
        print(f"  {name:<31} in: {inputs:<53} out: {outputs}")


if __name__ == "__main__":
    part1_2()
    part3()
    part4()
