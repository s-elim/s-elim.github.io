"""Lesson 11.2: depth, segmentation and point clouds: what the images measure.

INPUT   pick_place.xml; a test scene (a large plane under a downward camera at a chosen height)
PROCESS (1) what depth is: the top camera's depth at floor pixels in the centre and the corners
            of the image, against the camera height and the length of each pixel's ray;
        (2) depth accuracy against distance: the plane seen from 0.1 to 30 m, with the default
            near clipping plane and one ten times farther;
        (3) segmentation: what the front camera's labels contain (geoms, sites, background),
            and the same with sites hidden through the scene options;
        (4) point clouds: depth back-projected to the world from three cameras; floor flatness;
            the red cube's points against its true centre, per camera and fused;
        (5) the top camera as the cube-position sensor of Lesson 10.2: the xy centre of the
            red cube's top face over 100 random cube poses, against the truth
OUTPUT  printed tables

Run:  MUJOCO_GL=egl python examples/l11_2_depth_pointclouds.py     (or osmesa without a GPU)
"""
# requires: render

import math
import os

import mujoco
import numpy as np

from mjcourse import model_path

W, H = 640, 480
FLIP = np.diag([1.0, -1.0, -1.0])                 # MuJoCo camera axes -> OpenCV (x right, y down, z forward)
STATES = 20 if os.environ.get("MJC_FAST") == "1" else 100


def k_matrix(model, cam: int, width: int = W, height: int = H) -> np.ndarray:
    f = 0.5 * height / math.tan(math.radians(model.cam_fovy[cam]) / 2)
    return np.array([[f, 0, width / 2], [0, f, height / 2], [0, 0, 1]])


def back_project(model, data, cam: int, depth: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """World points (N, 3) of the pixels in `mask`, from metric depth along the optical axis."""
    k = k_matrix(model, cam, depth.shape[1], depth.shape[0])
    v, u = np.nonzero(mask)
    z = depth[v, u]
    p_cv = np.c_[(u + 0.5 - k[0, 2]) * z / k[0, 0], (v + 0.5 - k[1, 2]) * z / k[1, 1], z]
    r_wc = data.cam_xmat[cam].reshape(3, 3) @ FLIP
    return p_cv @ r_wc.T + data.cam_xpos[cam]


def render(renderer, data, camera, kind: str) -> np.ndarray:
    renderer.disable_depth_rendering()
    renderer.disable_segmentation_rendering()
    if kind == "depth":
        renderer.enable_depth_rendering()
    elif kind == "seg":
        renderer.enable_segmentation_rendering()
    renderer.update_scene(data, camera)
    return renderer.render().copy()


def home():
    model = mujoco.MjModel.from_xml_path(str(model_path("pick_place")))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("home").id)
    mujoco.mj_forward(model, data)
    return model, data


def part1() -> None:
    model, data = home()
    renderer = mujoco.Renderer(model, H, W)
    cam = model.camera("top").id
    depth, seg = render(renderer, data, "top", "depth"), render(renderer, data, "top", "seg")
    floor = (seg[..., 0] == model.geom("floor").id) & (seg[..., 1] == mujoco.mjtObj.mjOBJ_GEOM)
    k, height = k_matrix(model, cam), data.cam_xpos[cam][2]
    print(f"  camera height {height:.3f} m; fovy {model.cam_fovy[cam]:.0f} deg")
    print(f"  {'pixel (u, v)':<16}{'sees':>7}{'depth (m)':>11}{'ray length (m)':>16}")
    for u, v in ((W // 2, H // 2), (40, 40), (W - 40, 40), (40, H - 40), (W - 40, H - 40)):
        ray = height * math.hypot(1, (u + 0.5 - k[0, 2]) / k[0, 0], (v + 0.5 - k[1, 2]) / k[1, 1])
        print(f"  {str((u, v)):<16}{'floor' if floor[v, u] else 'other':>7}{depth[v, u]:>11.4f}{ray:>16.4f}")
    renderer.close()


def plane_scene(height: float, znear: float) -> mujoco.MjModel:
    return mujoco.MjModel.from_xml_string(f"""
<mujoco>
  <statistic extent="1" center="0 0 0"/>
  <visual><map znear="{znear}" zfar="100"/></visual>
  <worldbody>
    <light pos="0 0 50" dir="0 0 -1"/>
    <geom type="plane" size="500 500 0.1"/>
    <camera name="down" pos="0 0 {height}" fovy="45"/>
  </worldbody>
</mujoco>""")


def part2() -> None:
    print(f"  {'height (m)':>10}{'max |error|, znear 0.01 m (um)':>33}{'znear 0.1 m (um)':>19}{'float32 spacing at z (um)':>28}")
    for height in (0.3, 1.0, 3.0, 10.0, 30.0):
        errors = []
        for znear in (0.01, 0.1):
            model = plane_scene(height, znear)
            data = mujoco.MjData(model)
            mujoco.mj_forward(model, data)
            renderer = mujoco.Renderer(model, H, W)
            errors.append(1e6 * np.abs(render(renderer, data, "down", "depth") - height).max())
            renderer.close()
        print(f"  {height:>10.1f}{errors[0]:>33.2f}{errors[1]:>19.2f}{1e6 * np.spacing(np.float32(height)):>28.2f}")


def part3() -> None:
    model, data = home()
    renderer = mujoco.Renderer(model, H, W)
    for label, hide_sites in (("default scene options", False), ("sites hidden", True)):
        option = mujoco.MjvOption()
        if hide_sites:
            option.sitegroup[:] = 0
        renderer.enable_segmentation_rendering()
        renderer.update_scene(data, "front", scene_option=option)
        seg = renderer.render()
        renderer.disable_segmentation_rendering()
        types = {int(t): int(np.count_nonzero(seg[..., 1] == t)) for t in np.unique(seg[..., 1])}
        named = {mujoco.mjtObj(t).name if t >= 0 else "background": n for t, n in types.items()}
        sites = {model.site(int(i)).name: int(np.count_nonzero((seg[..., 1] == mujoco.mjtObj.mjOBJ_SITE) & (seg[..., 0] == i)))
                 for i in np.unique(seg[..., 0][seg[..., 1] == mujoco.mjtObj.mjOBJ_SITE])}
        print(f"  {label:<24} pixels by type {named}; sites {sites}")
    seg = render(renderer, data, "front", "seg")
    geoms = seg[..., 0][seg[..., 1] == mujoco.mjtObj.mjOBJ_GEOM]
    tray_geoms = {i for i in np.unique(geoms) if model.geom_bodyid[i] == model.body("tray").id}
    print(f"  the tray is {len(tray_geoms)} visible geoms of one body; body-level mask: "
          f"{int(np.isin(seg[..., 0], list(tray_geoms)).sum() if tray_geoms else 0)} pixels")
    renderer.close()


def part4(width: int, height: int) -> None:
    model, data = home()
    renderer = mujoco.Renderer(model, height, width)
    cube, centre = model.geom("red_cube").id, data.body("red_cube").xpos.copy()
    clouds = []
    print(f"  {width} x {height}: red cube centre {np.round(centre, 3)} m, half-size 20 mm")
    print(f"  {'camera':<10}{'floor points':>13}{'floor z max |err| (mm)':>24}{'cube points':>13}{'cube centroid minus centre (mm)':>34}")
    for name in ("front", "side", "top"):
        cam = model.camera(name).id
        depth, seg = render(renderer, data, name, "depth"), render(renderer, data, name, "seg")
        is_geom = seg[..., 1] == mujoco.mjtObj.mjOBJ_GEOM
        floor = back_project(model, data, cam, depth, is_geom & (seg[..., 0] == model.geom("floor").id))
        points = back_project(model, data, cam, depth, is_geom & (seg[..., 0] == cube))
        clouds.append(points)
        print(f"  {name:<10}{len(floor):>13d}{1000 * np.abs(floor[:, 2]).max():>24.3f}{len(points):>13d}"
              f"{np.array2string(1000 * (points.mean(axis=0) - centre), precision=1):>34}")
    fused = np.vstack(clouds)
    print(f"  {'fused':<10}{'':>13}{'':>24}{len(fused):>13d}{np.array2string(1000 * (fused.mean(axis=0) - centre), precision=1):>34}")
    box = (fused.min(axis=0) + fused.max(axis=0)) / 2
    print(f"  {'fused, centre of the bounding box':<60}{np.array2string(1000 * (box - centre), precision=1):>34}")
    renderer.close()


def part5(arm_aside: bool) -> None:
    model, data = home()
    renderer = mujoco.Renderer(model, H, W)
    cam, cube = model.camera("top").id, model.geom("red_cube").id
    adr = model.jnt_qposadr[model.joint("red_cube").id]
    rng = np.random.default_rng(10)
    xy = np.c_[rng.uniform(0.40, 0.60, STATES), rng.uniform(-0.20, 0.00, STATES)]
    yaw = rng.uniform(-math.pi / 4, math.pi / 4, STATES)
    errors, hidden = [], 0
    for (x, y), a in zip(xy, yaw):
        mujoco.mj_resetDataKeyframe(model, data, model.key("home").id)
        if arm_aside:
            data.qpos[0] = 1.6                                     # base joint: swing the arm to the robot's left
        for name, other in (("green_cube", (-0.6, 0.6)), ("blue_cube", (-0.6, -0.6))):   # set aside, as in 10.2
            o = model.jnt_qposadr[model.joint(name).id]
            data.qpos[o:o + 3] = [*other, 0.02]
        data.qpos[adr:adr + 7] = [x, y, 0.02, math.cos(a / 2), 0, 0, math.sin(a / 2)]
        mujoco.mj_forward(model, data)
        depth, seg = render(renderer, data, "top", "depth"), render(renderer, data, "top", "seg")
        points = back_project(model, data, cam, depth, (seg[..., 1] == mujoco.mjtObj.mjOBJ_GEOM) & (seg[..., 0] == cube))
        top_face = points[points[:, 2] > 0.039]                   # the top face is at z = 0.04
        if len(top_face) < 0.8 * 0.04**2 / (1.36 / k_matrix(model, cam)[0, 0]) ** 2:
            hidden += 1                                            # less than 80% of the face visible
            continue
        errors.append(1000 * np.linalg.norm(top_face[:, :2].mean(axis=0) - [x, y]))
    errors = np.array(errors)
    print(f"  arm {'swung aside (joint 1 at 1.6 rad)' if arm_aside else 'at home':<34} top face less than 80% visible: {hidden:3d}/{STATES};"
          f" xy error (mm): mean {errors.mean():.2f}, 95th percentile {np.percentile(errors, 95):.2f}, max {errors.max():.2f}")
    renderer.close()


if __name__ == "__main__":
    print(f"MuJoCo {mujoco.__version__}; renders {W} x {H}")
    print("(1) depth at floor pixels of the top camera, home state")
    part1()
    print("(2) depth error against distance (plane, camera looking straight down, extent 1 m)")
    part2()
    print("(3) segmentation of the front camera")
    part3()
    print("(4) point clouds from depth, home state")
    part4(W, H)
    part4(320, 240)
    print(f"(5) the top camera as a cube-position sensor: {STATES} cube poses (seed 10, Lesson 10.2's distribution),")
    print(f"    xy centre of the top face's points; pixel footprint on the face {1000 * 1.36 * 2 * math.tan(math.radians(22.5)) / H:.2f} mm")
    part5(arm_aside=False)
    part5(arm_aside=True)
