"""Lesson 3.2: offscreen rendering with mujoco.Renderer: RGB, depth, segmentation.

INPUT   pick_place.xml at its home keyframe; needs an OpenGL backend (set
        MUJOCO_GL=egl or osmesa on a machine without a display)
PROCESS render the front, side, top and wrist cameras plus one free camera, in
        RGB, metric depth and segmentation; summarize each image
OUTPUT  runs/l3_2/cameras.png (a figure of all images) and printed statistics

Run:  MUJOCO_GL=egl python examples/l3_2_render.py
"""
# requires: render

import sys
from pathlib import Path

import matplotlib
import mujoco
import numpy as np

from mjcourse import model_path

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "runs" / "l3_2"
H, W = 240, 320


def free_camera(model: mujoco.MjModel) -> mujoco.MjvCamera:
    cam = mujoco.MjvCamera()
    mujoco.mjv_defaultFreeCamera(model, cam)
    cam.lookat[:] = [0.45, 0.0, 0.1]          # point the camera orbits around (m)
    cam.distance, cam.azimuth, cam.elevation = 1.3, 150.0, -30.0   # m, degrees, degrees
    return cam


def main() -> int:
    model = mujoco.MjModel.from_xml_path(str(model_path("pick_place")))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 1)
    mujoco.mj_forward(model, data)
    try:
        renderer = mujoco.Renderer(model, height=H, width=W)
    except Exception as err:  # noqa: BLE001
        print(f"rendering unavailable: {err}\nset MUJOCO_GL=egl or osmesa (Lesson 0.2)")
        return 2

    cameras = {"front": "front", "side": "side", "top": "top", "wrist": "gripper/wrist", "free": free_camera(model)}
    images = {}
    for label, cam in cameras.items():
        renderer.disable_depth_rendering()
        renderer.disable_segmentation_rendering()
        renderer.update_scene(data, camera=cam)
        rgb = renderer.render().copy()
        renderer.enable_depth_rendering()
        renderer.update_scene(data, camera=cam)
        depth = renderer.render().copy()
        renderer.enable_segmentation_rendering()
        renderer.update_scene(data, camera=cam)
        seg = renderer.render().copy()           # (H, W, 2): object id, object type; background -1
        images[label] = (rgb, depth, seg)
        geom_ids = np.unique(seg[..., 0][seg[..., 1] == mujoco.mjtObj.mjOBJ_GEOM])
        cube_pixels = {n: int(np.sum((seg[..., 1] == mujoco.mjtObj.mjOBJ_GEOM) & (seg[..., 0] == model.geom(n).id)))
                       for n in ("red_cube", "green_cube", "blue_cube")}
        print(f"{label:>6}: rgb {rgb.shape} {rgb.dtype}; depth {depth.dtype} {depth.min():.3f} to {depth.max():.3f} m; "
              f"{len(geom_ids)} geoms visible; cube pixels {cube_pixels}")
    renderer.close()

    OUT.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(3, len(images), figsize=(3.2 * len(images), 7.2))
    for col, (label, (rgb, depth, seg)) in enumerate(images.items()):
        axes[0, col].imshow(rgb)
        axes[0, col].set_title(label)
        d = axes[1, col].imshow(depth, cmap="viridis")
        fig.colorbar(d, ax=axes[1, col], fraction=0.046, label="depth (m)")
        is_geom = seg[..., 1] == mujoco.mjtObj.mjOBJ_GEOM
        geom_id = np.ma.masked_where(~is_geom, seg[..., 0])        # background and sites masked out
        cmap = matplotlib.colormaps["tab20"].with_extremes(bad="black")
        axes[2, col].imshow(geom_id, cmap=cmap, vmin=0, vmax=model.ngeom, interpolation="nearest")
        for row in range(3):
            axes[row, col].set_xticks([])
            axes[row, col].set_yticks([])
    axes[0, 0].set_ylabel("RGB")
    axes[1, 0].set_ylabel("depth")
    axes[2, 0].set_ylabel("segmentation (geom id)")
    fig.tight_layout()
    fig.savefig(OUT / "cameras.png", dpi=110)
    print(f"saved {OUT / 'cameras.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
