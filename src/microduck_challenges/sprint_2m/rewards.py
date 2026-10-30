"""The sprint's own reward terms.

track_lane_velocity: velocity tracking in the LANE's frame instead of the trunk's.

The Arena scores progress down a lane the policy is never told about, and the reference loses
its time at speed by crab-walking (yaw about -3 deg, sideways drift) into the right wall. The
stock tracking term reads the velocity in the trunk's own yaw frame: a duck that walks "forward"
while turned off the lane, or that drifts sideways in world, keeps most of it. Here the frame is
the spawn heading (the lane's axis on the Arena): the reward is
    exp(-((v_par - vx_cmd)^2 + v_perp^2) / std^2)
with v_par and v_perp the trunk's horizontal world velocity along and across the spawn heading.

Unlike the refuted lane_hold (a POSITION reward, which standing still kept earning), this pays
only for moving down the lane at the commanded speed: walking less loses it.
"""

from __future__ import annotations

import torch
from mjlab.envs import ManagerBasedRlEnv
from mjlab.managers.scene_entity_config import SceneEntityCfg

_ROBOT = SceneEntityCfg("robot")


def _yaw(quat: torch.Tensor) -> torch.Tensor:
    w, x, y, z = quat[:, 0], quat[:, 1], quat[:, 2], quat[:, 3]
    return torch.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def track_lane_velocity(
    env: ManagerBasedRlEnv,
    std: float,
    command_name: str = "twist",
    asset_cfg: SceneEntityCfg = _ROBOT,
) -> torch.Tensor:
    asset = env.scene[asset_cfg.name]
    yaw = _yaw(asset.data.root_link_quat_w)
    if not hasattr(env, "_lane_heading") or env._lane_heading.shape[0] != env.num_envs:
        env._lane_heading = yaw.clone()
    env._lane_heading = torch.where(env.episode_length_buf <= 1, yaw, env._lane_heading)
    c, s = torch.cos(env._lane_heading), torch.sin(env._lane_heading)
    v = asset.data.root_link_lin_vel_w
    v_par = v[:, 0] * c + v[:, 1] * s
    v_perp = -v[:, 0] * s + v[:, 1] * c
    vx_cmd = env.command_manager.get_command(command_name)[:, 0]
    err = (v_par - vx_cmd) ** 2 + v_perp**2
    return torch.exp(-err / std**2)
