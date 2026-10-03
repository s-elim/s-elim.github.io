"""Lesson 11.1: the camera model: intrinsics, extrinsics, projection, checked against renders.

INPUT   pick_place.xml with 16 marker spheres (radius 5 mm) added by MjSpec at known positions
PROCESS (1) intrinsics of the scene's four cameras from fovy and the render size, extrinsics
            from cam_xpos and cam_xmat in the OpenCV convention (x right, y down, z forward);
        (2) project every marker and compare with the centroid of its segmentation mask
            rendered at 640 x 480: reprojection error per camera;
        (3) the same comparison under five common mistakes;
        (4) what the render's aspect ratio does to a fovy camera and to a camera defined by a
            sensor size: intrinsics fitted from renders at 640 x 480 and 480 x 480;
        (5) an OpenCV calibration matrix K turned into MuJoCo camera attributes, rendered,
            and K fitted back from the render, with the right and the wrong principal-point sign;
        (6) the lab's readout: each cube's projected centre against its mask centroid at 320 x 240
OUTPUT  printed tables

Run:  MUJOCO_GL=egl python examples/l11_1_camera_model.py     (or osmesa without a GPU)
"""
# requires: render

import math

import mujoco
import numpy as np

from mjcourse import model_path

W, H = 640, 480
FLIP = np.diag([1.0, -1.0, -1.0])        # MuJoCo camera axes (x right, y up, looking along -z) -> OpenCV
MARKER = 0.005                           # marker radius (m)


def scene_with_markers(seed: int = 0, extra_cameras=()) -> tuple[mujoco.MjModel, np.ndarray]:
    """pick_place plus 16 non-colliding spheres of radius 5 mm over the workspace."""
    spec = mujoco.MjSpec.from_file(str(model_path("pick_place")))
    rng = np.random.default_rng(seed)
    xs, ys = np.meshgrid(np.linspace(0.35, 0.65, 4), np.linspace(-0.18, 0.18, 4))
    points = np.c_[xs.ravel(), ys.ravel(), np.zeros(16)] + np.c_[rng.uniform(-0.02, 0.02, (16, 2)), rng.uniform(0.03, 0.2, 16)]
    for i, p in enumerate(points):
        spec.worldbody.add_geom(name=f"marker{i}", type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[MARKER, 0, 0], pos=p,
                                contype=0, conaffinity=0, rgba=[1, 1, 0, 1])
    for add in extra_cameras:
        add(spec)
    return spec.compile(), points


def intrinsics_fovy(model: mujoco.MjModel, cam: int, width: int, height: int) -> np.ndarray:
    """K for a camera defined by fovy: square pixels, principal point at the image centre."""
    f = 0.5 * height / math.tan(math.radians(model.cam_fovy[cam]) / 2)
    return np.array([[f, 0, width / 2], [0, f, height / 2], [0, 0, 1]])


def extrinsics(data: mujoco.MjData, cam: int) -> tuple[np.ndarray, np.ndarray]:
    """World-to-camera rotation and translation in the OpenCV convention: p_cam = R p_world + t."""
    r_wc = data.cam_xmat[cam].reshape(3, 3) @ FLIP          # columns: OpenCV camera axes in the world
    return r_wc.T, -r_wc.T @ data.cam_xpos[cam]


def project(k: np.ndarray, r: np.ndarray, t: np.ndarray, points: np.ndarray) -> np.ndarray:
    p = points @ r.T + t
    uv = p @ k.T
    return uv[:, :2] / uv[:, 2:3]


def masks(model, data, camera: str, n_markers: int, width: int = W, height: int = H, half: float = 0.5):
    """Centroid (u, v) of each marker's mask with pixel centres at index + half (NaN if not
    visible or touching the border), and the mask's pixel count."""
    renderer = mujoco.Renderer(model, height, width)
    renderer.enable_segmentation_rendering()
    renderer.update_scene(data, camera)
    seg = renderer.render()
    renderer.close()
    uv, counts = np.full((n_markers, 2), np.nan), np.zeros(n_markers)
    for i in range(n_markers):
        ys, xs = np.nonzero((seg[..., 0] == model.geom(f"marker{i}").id) & (seg[..., 1] == mujoco.mjtObj.mjOBJ_GEOM))
        counts[i] = len(xs)
        if len(xs) >= 6 and xs.min() > 0 and ys.min() > 0 and xs.max() < width - 1 and ys.max() < height - 1:
            uv[i] = xs.mean() + half, ys.mean() + half
    return uv, counts


def unoccluded(model, data, cam: int, points, uv, counts, height: int = H) -> np.ndarray:
    """Markers whose mask has at least 80% of the pixels an unoccluded sphere would cover."""
    r, t = extrinsics(data, cam)
    z = (points @ r.T + t)[:, 2]
    f = 0.5 * height / math.tan(math.radians(model.cam_fovy[cam]) / 2)
    return ~np.isnan(uv[:, 0]) & (counts >= 0.8 * math.pi * (f * MARKER / z) ** 2)


def errors(uv_model, uv_mask, ok) -> tuple[float, float]:
    e = np.linalg.norm(uv_model[ok] - uv_mask[ok], axis=1)
    return float(e.mean()), float(e.max())


def fit_k(points, r, t, uv) -> np.ndarray:
    """Least-squares fx, fy, cx, cy from known extrinsics and measured pixels."""
    p = points @ r.T + t
    a, b = p[:, 0] / p[:, 2], p[:, 1] / p[:, 2]
    ok = ~np.isnan(uv[:, 0])
    fx, cx = np.linalg.lstsq(np.c_[a, np.ones_like(a)][ok], uv[ok, 0], rcond=None)[0]
    fy, cy = np.linalg.lstsq(np.c_[b, np.ones_like(b)][ok], uv[ok, 1], rcond=None)[0]
    return np.array([fx, fy, cx, cy])


def part1_2(model, data, points) -> None:
    print(f"  {'camera':<14}{'fovy (deg)':>11}{'f (px)':>9}{'fov_x (deg)':>12}{'position (m)':>24}{'markers':>9}{'mean err (px)':>15}{'max err (px)':>14}")
    for cam in range(model.ncam):
        name = model.camera(cam).name
        k = intrinsics_fovy(model, cam, W, H)
        r, t = extrinsics(data, cam)
        uv_mask, counts = masks(model, data, name, len(points))
        ok = unoccluded(model, data, cam, points, uv_mask, counts)
        fov_x = 2 * math.degrees(math.atan(W / 2 / k[0, 0]))
        mean, mx = errors(project(k, r, t, points), uv_mask, ok) if ok.any() else (float("nan"), float("nan"))
        print(f"  {name:<14}{model.cam_fovy[cam]:>11.1f}{k[0, 0]:>9.1f}{fov_x:>12.1f}{np.array2string(data.cam_xpos[cam], precision=3):>24}"
              f"{ok.sum():>6d}/16{mean:>15.3f}{mx:>14.3f}")


def part3(model, data, points) -> None:
    cam = model.camera("front").id
    k, (r, t) = intrinsics_fovy(model, cam, W, H), extrinsics(data, cam)
    uv_mask, counts = masks(model, data, "front", len(points))
    ok = unoccluded(model, data, cam, points, uv_mask, counts)
    k_hfov = k.copy()
    k_hfov[0, 0] = k_hfov[1, 1] = 0.5 * W / math.tan(math.radians(model.cam_fovy[cam]) / 2)    # fovy read as horizontal
    r_mj = data.cam_xmat[cam].reshape(3, 3).T                                                    # MuJoCo axes, no flip
    cases = [("correct", project(k, r, t, points), uv_mask),
             ("fovy taken as the horizontal field of view", project(k_hfov, r, t, points), uv_mask),
             ("MuJoCo camera axes used as OpenCV axes", project(k, r_mj, -r_mj @ data.cam_xpos[cam], points), uv_mask),
             ("mask centroid without the half-pixel offset", project(k, r, t, points), masks(model, data, "front", len(points), half=0.0)[0]),
             ("cam_xmat used without transposing", project(k, r.T, -r.T @ data.cam_xpos[cam], points), uv_mask)]
    for label, uv, measured in cases:
        e = np.linalg.norm(uv[ok] - measured[ok], axis=1)
        e = np.where(np.isfinite(e), e, np.inf)
        print(f"  {label:<46} mean {np.mean(e):9.2f} px   max {np.max(e):9.2f} px")
    wrist = model.camera("gripper/wrist").id
    k_w, (r_w, t_w) = intrinsics_fovy(model, wrist, W, H), extrinsics(data, wrist)
    hand = model.cam_bodyid[wrist]
    uv_w, counts_w = masks(model, data, "gripper/wrist", len(points))
    ok_w = unoccluded(model, data, wrist, points, uv_w, counts_w)
    for label, (rr, tt) in (("wrist camera, its own pose", (r_w, t_w)),
                            ("wrist camera, the hand body's position instead", (r_w, -r_w @ data.xpos[hand]))):
        e = np.linalg.norm(project(k_w, rr, tt, points)[ok_w] - uv_w[ok_w], axis=1)
        print(f"  {label:<46} mean {np.mean(e):9.2f} px   max {np.max(e):9.2f} px  ({ok_w.sum()} markers)")


def sensor_camera(name: str, k: np.ndarray | None, sign: float = 1.0, pitch: float = 3e-6, principal=None):
    """A camera at the front camera's pose defined by focal and principal point in pixels.
    MuJoCo's principal-point offset (px, py) puts the image centre at (W/2 - px, H/2 - py)."""
    base = mujoco.MjModel.from_xml_path(str(model_path("pick_place")))
    front = base.camera("front").id                     # compiled pose: the XML gives it as xyaxes

    def add(spec: mujoco.MjSpec) -> None:
        cam = spec.worldbody.add_camera(name=name, pos=base.cam_pos[front], quat=base.cam_quat[front])
        fx, fy, cx, cy = (600.0, 600.0, W / 2, H / 2) if k is None else (k[0, 0], k[1, 1], k[0, 2], k[1, 2])
        cam.resolution = [W, H]
        cam.sensor_size = [W * pitch, H * pitch]
        cam.focal_pixel = [fx, fy]
        cam.principal_pixel = list(principal) if principal is not None else [sign * (W / 2 - cx), sign * (H / 2 - cy)]
    return add


def part4_5() -> None:
    k_cal = np.array([[615.3, 0, 326.4], [0, 614.8, 238.1], [0, 0, 1]])
    model, points = scene_with_markers(extra_cameras=(sensor_camera("sensor", None), sensor_camera("calibrated", k_cal),
                                                      sensor_camera("calibrated_wrong_sign", k_cal, sign=-1.0),
                                                      sensor_camera("offset_x", None, principal=(30, 0)),
                                                      sensor_camera("offset_y", None, principal=(0, 30))))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("home").id)
    mujoco.mj_forward(model, data)
    print("(4) intrinsics fitted from renders: fx, fy, cx, cy (px)")
    for name in ("front", "sensor"):
        cam = model.camera(name).id
        r, t = extrinsics(data, cam)
        for width, height in ((640, 480), (480, 480)):
            fitted = fit_k(points, r, t, masks(model, data, name, len(points), width, height)[0])
            fov_x = 2 * math.degrees(math.atan(width / 2 / fitted[0]))
            fov_y = 2 * math.degrees(math.atan(height / 2 / fitted[1]))
            kind = "fovy 45" if name == "front" else "sensor 4:3, focal 600 px"
            print(f"  {kind:<26} render {width} x {height}: {np.array2string(fitted, precision=2):<34} fov_x {fov_x:5.1f}, fov_y {fov_y:5.1f} deg")
    print("(5) the principal-point offset's sign: focal 600 px, principal_pixel set, cx and cy fitted from renders")
    for name, offset in (("sensor", (0, 0)), ("offset_x", (30, 0)), ("offset_y", (0, 30))):
        cam = model.camera(name).id
        r, t = extrinsics(data, cam)
        fitted = fit_k(points, r, t, masks(model, data, name, len(points))[0])
        print(f"  principal_pixel {str(offset):<9} fitted cx {fitted[2]:7.2f}, cy {fitted[3]:7.2f}")
    print("  an OpenCV K into MuJoCo: fx 615.3, fy 614.8, cx 326.4, cy 238.1 at 640 x 480")
    for name, label in (("calibrated", "principal_pixel = (W/2 - cx, H/2 - cy)"), ("calibrated_wrong_sign", "principal_pixel = (cx - W/2, cy - H/2)")):
        cam = model.camera(name).id
        r, t = extrinsics(data, cam)
        uv = masks(model, data, name, len(points))[0]
        fitted = fit_k(points, r, t, uv)
        ok = ~np.isnan(uv[:, 0])
        e = np.linalg.norm(project(k_cal, r, t, points)[ok] - uv[ok], axis=1)
        print(f"  {label:<40} fitted {np.array2string(fitted, precision=2):<34} reprojection with K: mean {e.mean():.2f}, max {e.max():.2f} px")


def part6() -> None:
    model = mujoco.MjModel.from_xml_path(str(model_path("pick_place")))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("home").id)
    mujoco.mj_forward(model, data)
    width, height = 320, 240
    renderer = mujoco.Renderer(model, height, width)
    renderer.enable_segmentation_rendering()
    for cam in range(model.ncam):
        renderer.update_scene(data, cam)
        seg = renderer.render()
        k, (r, t) = intrinsics_fovy(model, cam, width, height), extrinsics(data, cam)
        row = []
        for name in ("red_cube", "green_cube", "blue_cube"):
            ys, xs = np.nonzero((seg[..., 0] == model.geom(name).id) & (seg[..., 1] == mujoco.mjtObj.mjOBJ_GEOM))
            if len(xs) == 0:
                row.append(f"{name.split('_')[0]} not visible")
                continue
            uv = project(k, r, t, data.body(name).xpos[None])[0]
            row.append(f"{name.split('_')[0]} {np.hypot(uv[0] - xs.mean() - 0.5, uv[1] - ys.mean() - 0.5):.2f} ({len(xs)} px)")
        print(f"  {model.camera(cam).name:<14}" + ";  ".join(row))
    renderer.close()


if __name__ == "__main__":
    model, points = scene_with_markers()
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("home").id)
    mujoco.mj_forward(model, data)
    print(f"MuJoCo {mujoco.__version__}; renders {W} x {H}; 16 markers of radius {1000 * MARKER:.0f} mm")
    print("(1, 2) model cameras: intrinsics from fovy, extrinsics from cam_xpos/cam_xmat, reprojection against masks")
    part1_2(model, data, points)
    print("(3) common mistakes, front camera (wrist camera for the last two rows)")
    part3(model, data, points)
    part4_5()
    print("(6) cube centres projected against their mask centroids, 320 x 240, home state (px)")
    part6()
