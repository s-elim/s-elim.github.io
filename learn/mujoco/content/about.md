This course takes a learner from no simulation background to research use of MuJoCo. It is built around one habit: **predict, then simulate, then explain the difference**. Every lesson has the same parts, in the same order: core concept, visual intuition, an interactive experiment, the mathematics, implementation, debugging, an exercise, a challenge, a research connection, a knowledge check, and a pointer to the next lesson. Each level ends with an expert checkpoint that asks you to build something without a template.

## Versions

| Component | Version | Notes |
|---|---|---|
| MuJoCo (Python) | 3.14.0 | released 22 September 2026; the companion package pins it exactly |
| MuJoCo (browser) | 3.14.0 | official `@mujoco/mujoco` WebAssembly build, single-threaded |
| Python | 3.10 to 3.15 | wheels exist for all of them; the course was run on 3.12 |
| NumPy, Gymnasium | 2.x, 1.3 | reference versions in `code/requirements.txt` |
| PyTorch | 2.x, CPU is enough | only from Level 13 on |
| three.js | 0.170.0 | draws the labs; MuJoCo's WebAssembly build has no renderer |

**Operating systems.** MuJoCo 3.14.0 ships wheels for Linux (x86-64 and ARM64, glibc 2.27 or newer), macOS on Apple silicon (11 or newer) and Windows x86-64. There is no wheel for Intel Macs.

**Hardware.** Every lesson runs on a laptop CPU. A GPU is never required; it helps for rendering large datasets (EGL) and for training vision policies. Rendering on a server without a GPU works with OSMesa (Lesson 0.2).

## The two runtimes

The labs in these pages run MuJoCo itself, compiled to WebAssembly, in your browser: same engine, same version, same numbers as Python for the same model and state. What differs is the drawing: the labs draw MuJoCo's geometry with three.js, so lighting and shading are the course's own, while every pose comes from MuJoCo. Anything that needs MuJoCo's renderer (camera images for datasets and vision policies), heavy computation (training, thousands of rollouts) or files on disk belongs in the Python companion package.

## Five kinds of claim

The course separates what it knows from what it argues. Boxes in the lessons carry one of these labels:

<div class="tier-legend">

> [!established]
> MuJoCo behaviour checked against the 3.14.0 documentation or source code, or measured by running it.

> [!derivation]
> Follows mathematically from stated assumptions; the assumptions are stated.

> [!implementation]
> How MuJoCo, its bindings, or this course's code does something. True for this version; may change.

> [!recommendation]
> A judgement call about practice, with its trade-off.

> [!research]
> An interpretation or argument about research practice. Disagree with it on evidence.

> [!unverified]
> Could not be checked against a primary source. Treat it as a hypothesis.

</div>

Two more labels appear: **version notes**, for behaviour that changed between MuJoCo releases, and **pitfalls**, for mistakes common enough to deserve a warning.

## What "complete", "draft" and "planned" mean

Every lesson in the course map has a status.

- **Complete**: written, every code block executed against MuJoCo 3.14.0, its labs tested in a browser, and reviewed for depth.
- **Draft**: written and executable, with every code block run and every lab tested, but not yet through a final review of exercises and depth.
- **Planned**: the syllabus (objectives, prerequisites, level) is fixed; the text is not written. The page says so and points to the nearest written material.

Nothing on this site describes a planned lesson as if it existed.

## Running everything locally

```bash
# the companion code (the site repository is large: fetch only this folder)
git clone --depth 1 --filter=blob:none --sparse https://github.com/s-elim/s-elim.github.io
cd s-elim.github.io && git sparse-checkout set learn/mujoco
cd learn/mujoco/code && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"            # add ".[learn]" for PyTorch
pytest                              # models compile, examples run, modules match MuJoCo
python examples/l0_1_free_fall.py   # any lesson script

# the course website itself, offline (labs still fetch MuJoCo and three.js from CDNs)
cd .. && python -m http.server 8000   # then open http://localhost:8000/
```

## How the course is built

| Path (under `learn/mujoco/`) | What it is |
|---|---|
| `index.html`, `css/`, `js/` | the website: router, lesson renderer, MuJoCo runtime, viewer, labs |
| `course.json` | the course map: levels, lessons, statuses, checkpoints, pages |
| `lessons/*.md`, `content/*.md` | lesson and page text, Markdown with math and lab blocks |
| `code/src/mjcourse/models/` | every MJCF model, shared by the browser and Python |
| `code/src/mjcourse/` | the Python package: spatial math, kinematics, control, environments, learning |
| `code/examples/` | one script per lesson; lessons embed these files verbatim |
| `code/projects/` | project specifications, starters, solutions, tests |
| `code/capstones/` | where capstone work goes; the specifications are in Lesson 22.1 and the acceptance checker is `mjcourse.capstone` (no reference solutions) |
| `code/tests/` | pytest suite |
| `tools/` | content checks, code sync, search index, browser checks |

Three tools keep the text honest: `tools/sync_code.py` rewrites every code block that names a file with that file's current contents; `tools/check_content.py` fails if a block drifts, a lab names a missing model, a quiz answer index is out of range, or the prose breaks the style rules; and `tools/browser_check.py` loads pages in a headless browser, starts the labs and fails on any console error.

## Author and licence

Written and built by [Md Selim Sarowar](/). Project: IITP, PI: Prof. Sungho Kim. The companion code is MIT-licensed; MuJoCo itself is Apache-2.0 (Google DeepMind). Corrections are welcome through the [repository](https://github.com/s-elim/s-elim.github.io) or the anonymous message form on the home page.
