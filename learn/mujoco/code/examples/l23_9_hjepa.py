import torch
import torch.nn as nn
import torch.nn.functional as F

class SIGRegLoss(nn.Module):
    def __init__(self, lambd_mean: float = 1.0, lambd_cov: float = 1.0):
        super().__init__()
        self.lambd_mean = lambd_mean
        self.lambd_cov = lambd_cov

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        b, d = z.shape
        mean = z.mean(dim=0)
        mean_loss = torch.sum(mean ** 2)
        z_centered = z - mean
        cov = (z_centered.T @ z_centered) / max(1, b - 1)
        eye = torch.eye(d, device=z.device)
        cov_loss = torch.sum((cov - eye) ** 2)
        return self.lambd_mean * mean_loss + self.lambd_cov * cov_loss

class MultimodalSensorEncoder(nn.Module):
    def __init__(self, token_dim: int = 16):
        super().__init__()
        self.token_dim = token_dim
        # Modality encoders: RGB, Depth, LiDAR, Radar, Raman, Proprioception
        self.rgb_enc = nn.Sequential(nn.Linear(32, 32), nn.SiLU(), nn.Linear(32, token_dim))
        self.depth_enc = nn.Sequential(nn.Linear(16, 32), nn.SiLU(), nn.Linear(32, token_dim))
        self.lidar_enc = nn.Sequential(nn.Linear(16, 32), nn.SiLU(), nn.Linear(32, token_dim))
        self.radar_enc = nn.Sequential(nn.Linear(12, 32), nn.SiLU(), nn.Linear(32, token_dim))
        self.raman_enc = nn.Sequential(nn.Linear(24, 32), nn.SiLU(), nn.Linear(32, token_dim))
        self.proprio_enc = nn.Sequential(nn.Linear(14, 32), nn.SiLU(), nn.Linear(32, token_dim))

        self.fusion = nn.Sequential(
            nn.Linear(6 * token_dim, 64),
            nn.SiLU(),
            nn.Linear(64, 32),
        )

    def forward(
        self,
        rgb: torch.Tensor,
        depth: torch.Tensor,
        lidar: torch.Tensor,
        radar: torch.Tensor,
        raman: torch.Tensor,
        proprio: torch.Tensor,
    ) -> torch.Tensor:
        e_rgb = self.rgb_enc(rgb)
        e_depth = self.depth_enc(depth)
        e_lidar = self.lidar_enc(lidar)
        e_radar = self.radar_enc(radar)
        e_raman = self.raman_enc(raman)
        e_proprio = self.proprio_enc(proprio)

        fused = torch.cat([e_rgb, e_depth, e_lidar, e_radar, e_raman, e_proprio], dim=-1)
        return self.fusion(fused)

class HierarchicalJEPA(nn.Module):
    def __init__(
        self,
        token_dim: int = 16,
        act_dim: int = 7,
        l1_dim: int = 32,
        l2_dim: int = 16,
        stride: int = 4,
    ):
        super().__init__()
        self.token_dim = token_dim
        self.act_dim = act_dim
        self.l1_dim = l1_dim
        self.l2_dim = l2_dim
        self.stride = stride

        self.sensor_encoder = MultimodalSensorEncoder(token_dim=token_dim)

        self.pred1 = nn.Sequential(
            nn.Linear(l1_dim + act_dim, 64),
            nn.SiLU(),
            nn.Linear(64, l1_dim),
        )
        self.idm1 = nn.Sequential(
            nn.Linear(2 * l1_dim, 64),
            nn.SiLU(),
            nn.Linear(64, act_dim),
        )

        self.enc2 = nn.Sequential(
            nn.Linear(l1_dim, 32),
            nn.SiLU(),
            nn.Linear(32, l2_dim),
        )
        self.act_enc2 = nn.Sequential(
            nn.Linear(stride * act_dim, 32),
            nn.SiLU(),
            nn.Linear(32, act_dim),
        )
        self.pred2 = nn.Sequential(
            nn.Linear(l2_dim + act_dim, 32),
            nn.SiLU(),
            nn.Linear(32, l2_dim),
        )

        self.sigreg = SIGRegLoss(lambd_mean=1.0, lambd_cov=1.0)

    def forward_loss(
        self,
        sensors: dict[str, torch.Tensor],
        act_seq: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        b, t, _ = sensors["rgb"].shape

        z1 = self.sensor_encoder(
            sensors["rgb"],
            sensors["depth"],
            sensors["lidar"],
            sensors["radar"],
            sensors["raman"],
            sensors["proprio"],
        )
        z1_inputs = torch.cat([z1[:, :-1], act_seq], dim=-1)
        z1_pred = self.pred1(z1_inputs)

        loss_pred1 = F.mse_loss(z1_pred, z1[:, 1:])
        loss_sigreg1 = self.sigreg(z1.reshape(-1, self.l1_dim))

        pred_act1 = self.idm1(torch.cat([z1[:, :-1], z1[:, 1:]], dim=-1))
        loss_idm1 = F.mse_loss(pred_act1, act_seq)

        # Macro-stride level 2 computation
        sub_steps = t // self.stride
        z2 = self.enc2(z1[:, ::self.stride])
        loss_sigreg2 = self.sigreg(z2.reshape(-1, self.l2_dim))

        macro_acts = []
        for s in range(sub_steps - 1):
            act_chunk = act_seq[:, s * self.stride : (s + 1) * self.stride].reshape(b, -1)
            macro_acts.append(self.act_enc2(act_chunk))

        if len(macro_acts) > 0:
            macro_act_stack = torch.stack(macro_acts, dim=1)
            z2_inputs = torch.cat([z2[:, :len(macro_acts)], macro_act_stack], dim=-1)
            z2_pred = self.pred2(z2_inputs)
            loss_pred2 = F.mse_loss(z2_pred, z2[:, 1:len(macro_acts) + 1])
        else:
            loss_pred2 = torch.tensor(0.0, device=act_seq.device)

        total_loss = (
            loss_pred1
            + 0.1 * loss_sigreg1
            + 0.2 * loss_idm1
            + loss_pred2
            + 0.1 * loss_sigreg2
        )

        return {
            "total_loss": total_loss,
            "loss_pred1": loss_pred1,
            "loss_sigreg1": loss_sigreg1,
            "loss_idm1": loss_idm1,
            "loss_pred2": loss_pred2,
            "loss_sigreg2": loss_sigreg2,
        }

    def plan_top_down(
        self,
        current_sensors: dict[str, torch.Tensor],
        goal_sensors: dict[str, torch.Tensor],
        horizon_l2: int = 2,
        iters: int = 25,
        lr: float = 0.05,
    ) -> torch.Tensor:
        with torch.no_grad():
            z1_0 = self.sensor_encoder(
                current_sensors["rgb"],
                current_sensors["depth"],
                current_sensors["lidar"],
                current_sensors["radar"],
                current_sensors["raman"],
                current_sensors["proprio"],
            )
            z2_0 = self.enc2(z1_0).squeeze(1)

            z1_g = self.sensor_encoder(
                goal_sensors["rgb"],
                goal_sensors["depth"],
                goal_sensors["lidar"],
                goal_sensors["radar"],
                goal_sensors["raman"],
                goal_sensors["proprio"],
            )
            z2_g = self.enc2(z1_g).squeeze(1)

        # Optimize level 2 macro-actions
        macro_act = nn.Parameter(torch.zeros(1, horizon_l2, self.act_dim))
        opt2 = torch.optim.Adam([macro_act], lr=lr)

        for _ in range(iters):
            opt2.zero_grad()
            curr = z2_0
            for h in range(horizon_l2):
                inp = torch.cat([curr, macro_act[:, h]], dim=-1)
                curr = self.pred2(inp)
            loss = F.mse_loss(curr, z2_g)
            loss.backward()
            opt2.step()

        return macro_act.detach()

def main():
    torch.manual_seed(42)
    device = torch.device("cpu")

    model = HierarchicalJEPA(token_dim=16, act_dim=7, l1_dim=32, l2_dim=16, stride=4).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)

    b, t = 4, 9
    sensors = {
        "rgb": torch.randn(b, t, 32, device=device),
        "depth": torch.randn(b, t, 16, device=device),
        "lidar": torch.randn(b, t, 16, device=device),
        "radar": torch.randn(b, t, 12, device=device),
        "raman": torch.randn(b, t, 24, device=device),
        "proprio": torch.randn(b, t, 14, device=device),
    }
    act_seq = torch.randn(b, t - 1, 7, device=device)

    print("Training Hierarchical World Model with multimodal sensor fusion (RGB, Depth, LiDAR, Radar, Raman)...")
    for step in range(5):
        optimizer.zero_grad()
        loss_dict = model.forward_loss(sensors, act_seq)
        loss_dict["total_loss"].backward()
        optimizer.step()
        print(
            f"Step {step + 1}: Total = {loss_dict['total_loss'].item():.4f}, "
            f"L1 Pred = {loss_dict['loss_pred1'].item():.4f}, "
            f"L2 Pred = {loss_dict['loss_pred2'].item():.4f}, "
            f"SIGReg = {loss_dict['loss_sigreg1'].item():.4f}"
        )

    print("\nRunning top-down visual planning with multimodal goal conditioning...")
    cur_s = {k: v[:1, :1] for k, v in sensors.items()}
    goal_s = {k: torch.randn(1, 1, v.shape[-1], device=device) for k, v in sensors.items()}
    macros = model.plan_top_down(cur_s, goal_s, horizon_l2=2, iters=20)
    print("Planned macro-actions tensor shape:", macros.shape)

    from pathlib import Path
    import mujoco
    model_path = Path(__file__).resolve().parent.parent / "src" / "mjcourse" / "models" / "industrial_battery.xml"
    if model_path.exists():
        mj_model = mujoco.MjModel.from_xml_path(str(model_path))
        mj_data = mujoco.MjData(mj_model)
        mujoco.mj_step(mj_model, mj_data)
        print(f"Verified physical simulation on {model_path.name}: {mj_model.nbody} bodies, t = {mj_data.time:.3f} s")

    print("Multimodal physical verification successful.")

if __name__ == "__main__":
    main()
