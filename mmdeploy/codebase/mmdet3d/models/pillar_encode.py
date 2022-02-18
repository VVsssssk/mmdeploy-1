import torch

from mmdeploy.core import FUNCTION_REWRITER


def get_paddings_indicator(actual_num, max_num, axis=0):
    actual_num = torch.unsqueeze(actual_num, axis + 1)
    # tiled_actual_num: [N, M, 1]
    max_num_shape = [1] * len(actual_num.shape)
    max_num_shape[axis + 1] = -1
    max_num = torch.arange(
        max_num, dtype=torch.int, device=actual_num.device).view(max_num_shape)
    # tiled_actual_num: [[3,3,3,3,3], [4,4,4,4,4], [2,2,2,2,2]]
    # tiled_max_num: [[0,1,2,3,4], [0,1,2,3,4], [0,1,2,3,4]]
    paddings_indicator = actual_num.int() > max_num
    # paddings_indicator shape: [batch_size, max_num]
    return paddings_indicator


@FUNCTION_REWRITER.register_rewriter(
    'mmdet3d.models.voxel_encoders.pillar_encoder.PillarFeatureNet.forward')
def forward(ctx, self, features, num_points, coors):
    """Forward function.

    Args:
        features (torch.Tensor): Point features or raw points in shape
            (N, M, C).
        num_points (torch.Tensor): Number of points in each pillar.
        coors (torch.Tensor): Coordinates of each voxel.

    Returns:
        torch.Tensor: Features of pillars.
    """
    features_ls = [features]
    # Find distance of x, y, and z from cluster center
    if self._with_cluster_center:
        points_mean = features[:, :, :3].sum(
            dim=1, keepdim=True) / num_points.type_as(features).view(-1, 1, 1)
        f_cluster = features[:, :, :3] - points_mean
        features_ls.append(f_cluster)

    # Find distance of x, y, and z from pillar center
    if self._with_voxel_center:
        if not self.legacy:
            f_center = features[..., :2] - (
                coors * torch.tensor([1, 1, self.vy, self.vx]).cuda() +
                torch.tensor([1, 1, self.y_offset, self.x_offset
                              ]).cuda()).unsqueeze(1).flip(2)[..., :2]
        else:
            f_center = features[..., :2] - (
                coors * torch.tensor([1, 1, self.vy, self.vx]).cuda() +
                torch.tensor([1, 1, self.y_offset, self.x_offset
                              ]).cuda()).unsqueeze(1).flip(2)[..., :2]
            features_ls[0] = torch.cat((f_center, features[..., 2:]), dim=-1)
        features_ls.append(f_center)

    if self._with_distance:
        points_dist = torch.norm(features[:, :, :3], 2, 2, keepdim=True)
        features_ls.append(points_dist)

    # Combine together feature decorations
    features = torch.cat(features_ls, dim=-1)
    # The feature decorations were calculated without regard to whether
    # pillar was empty. Need to ensure that
    # empty pillars remain set to zeros.
    voxel_count = features.shape[1]
    mask = get_paddings_indicator(num_points, voxel_count, axis=0)
    mask = torch.unsqueeze(mask, -1).type_as(features)
    features *= mask
    for pfn in self.pfn_layers:
        features = pfn(features, num_points)

    return features.squeeze(1)
