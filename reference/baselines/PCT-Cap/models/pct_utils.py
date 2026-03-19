import torch

def farthest_point_sample(xyz: torch.Tensor, npoint: int):
    """
    Input:
        xyz: pointcloud data, [B, N, 3]
        npoint: number of samples
    Return:
        centroids: sampled pointcloud index, [B, npoint]
    """
    device = xyz.device
    B, N, C = xyz.shape
    centroids = torch.zeros(B, npoint, dtype=torch.long).to(device)
    distance = torch.ones(B, N).to(device) * 1e10
    farthest = torch.randint(0, N, (B,), dtype=torch.long).to(device)
    batch_indices = torch.arange(B, dtype=torch.long).to(device)
    for i in range(npoint):
        centroids[:, i] = farthest
        centroid = xyz[batch_indices, farthest, :].view(B, 1, 3)
        dist = torch.sum((xyz - centroid) ** 2, -1)
        mask = dist < distance
        distance[mask] = dist[mask]
        farthest = torch.max(distance, -1)[1]
    return centroids

def index_points(points: torch.Tensor, idx: torch.Tensor):
    """
    Input:
        points: input points data, [B, N, C]
        idx: sample index data, [B, S]
    Return:
        new_points:, indexed points data, [B, S, C]
    """
    device = points.device
    B = points.shape[0]
    view_shape = list(idx.shape)
    view_shape[1:] = [1] * (len(view_shape) - 1)
    repeat_shape = list(idx.shape)
    repeat_shape[0] = 1
    batch_indices = torch.arange(B, dtype=torch.long).to(device).view(view_shape).repeat(repeat_shape)
    new_points = points[batch_indices, idx, :]
    return new_points

def square_distance(src: torch.Tensor, dst: torch.Tensor):
    """
    Calculate Euclid distance between each two points.

    src^T * dst = xn * xm + yn * ym + zn * zm;
    sum(src^2, dim=-1) = xn*xn + yn*yn + zn*zn;
    sum(dst^2, dim=-1) = xm*xm + ym*ym + zm*zm;
    dist = (xn - xm)^2 + (yn - ym)^2 + (zn - zm)^2
         = sum(src**2,dim=-1)+sum(dst**2,dim=-1)-2*src^T*dst

    Input:
        src: source points, [B, N, C]
        dst: target points, [B, M, C]
    Output:
        dist: per-point square distance, [B, N, M]
    """
    B, N, _ = src.shape
    _, M, _ = dst.shape
    dist = -2 * torch.matmul(src, dst.permute(0, 2, 1))
    dist += torch.sum(src ** 2, -1).view(B, N, 1)
    dist += torch.sum(dst ** 2, -1).view(B, 1, M)
    return dist

def knn_point(nsample: int, xyz: torch.Tensor, new_xyz: torch.Tensor):
    """
    Input:
        nsample: max sample number in local region
        xyz: all points, [B, N, C]
        new_xyz: query points, [B, S, C]
    Return:
        group_idx: grouped points index, [B, S, nsample]
    """
    sqrdists = square_distance(new_xyz, xyz)
    _, group_idx = torch.topk(sqrdists, nsample, dim = -1, largest=False, sorted=False)
    return group_idx

def sample_and_group(npoint: int, nsample: int, xyz: torch.Tensor, points: torch.Tensor):
  """
  Input:
    npoint: number of key points
    nsample: number of samples in a key point group 
    xyz: input points position, [B, N, 3]
    points: input points data, [B, N, D]
  Return:
    new_xyz: sampled points position data, [B, S, 3]
    new_points: sampled points data, [B, S, K, 2 * D]
  """
  B, N, C = xyz.shape
  S = npoint

  fps_idx = farthest_point_sample(xyz, npoint)  # B, S
  new_xyz = index_points(xyz, fps_idx)          # B, S, 3
  new_points = index_points(points, fps_idx)    # B, S, D

  grouped_idx = knn_point(nsample, xyz, new_xyz) # B, S, K
  # grouped_xyz = index_points(xyz, grouped_idx)
  # grouped_xyz_norm = grouped_xyz - new_xyz.view(B, S, 1, C)
  grouped_points = index_points(points, grouped_idx) # B, S, K, D
  grouped_points_norm = grouped_points - new_points.view(B, S, 1, -1) # B, S, K, D

  # B, S, K, 2D
  new_points = torch.cat([grouped_points_norm,
                          new_points.view(B, S, 1, -1).repeat(1, 1, nsample, 1)
                        ], dim=-1)
  return new_xyz, new_points