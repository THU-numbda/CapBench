import torch
import torch.nn as nn
import torch.nn.functional as F

from models.pct_utils import sample_and_group

class LocalOperation(nn.Module):
  def __init__(self, in_channels: int, out_channels: int) -> None:
    super().__init__()
    self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size=1, bias=False)
    self.bn1 = nn.BatchNorm1d(out_channels)
    self.conv2 = nn.Conv1d(out_channels, out_channels, kernel_size=1, bias=False)
    self.bn2 = nn.BatchNorm1d(out_channels)
  
  def forward(self, x: torch.Tensor):
    B, N, S, D = x.shape
    x = x.permute(0, 1, 3, 2) # B, N, D, S
    x = x.reshape(-1, D, S)   # B * N, D, S
    B_N, D, S = x.shape
    x = F.relu(self.bn1(self.conv1(x)))
    x = F.relu(self.bn2(self.conv2(x)))
    x = F.adaptive_avg_pool1d(x, 1)
    x = x.view(B_N, -1)
    x = x.reshape(B, N, -1).permute(0, 2, 1)
    return x

class SelfAttention(nn.Module):
  def __init__(self, channels: int) -> None:
    super().__init__()
    self.q_conv = nn.Conv1d(channels, channels // 4, kernel_size=1, bias=False)
    self.k_conv = nn.Conv1d(channels, channels // 4, kernel_size=1, bias=False)
    self.v_conv = nn.Conv1d(channels, channels, kernel_size=1, bias=False)
    self.softmax = nn.Softmax(dim=-1)
    
    self.z_conv = nn.Conv1d(channels, channels, 1)
    self.z_norm = nn.BatchNorm1d(channels)
    self.z_act = nn.ReLU()

  def forward(self, xyz: torch.Tensor, x: torch.Tensor):
    x = x + xyz # B, D, S
    x_q: torch.Tensor = self.q_conv(x) # B, d, S
    x_k: torch.Tensor = self.k_conv(x) # B, d, S
    x_v: torch.Tensor = self.v_conv(x) # B, D, S
    
    attention:torch.Tensor = self.softmax(torch.bmm(x_q.permute(0, 2, 1), x_k))
    attention = attention / (1e-9 + attention.sum(dim=1, keepdim=True))
    z: torch.Tensor = torch.bmm(x_v, attention) # B, D, S

    # offset attention
    z = self.z_act(self.z_norm(self.z_conv(x - z)))
    # skip connect
    x = x + z # B, D, S

    return x

class PointTransformer(nn.Module):
  def __init__(self, channels: int) -> None:
    super().__init__()
    self.conv1 = nn.Conv1d(channels, channels, kernel_size=1, bias=False)
    self.bn1 = nn.BatchNorm1d(channels)
    self.pos_xyz = nn.Conv1d(3, channels, kernel_size=1)
    
    self.sa1 = SelfAttention(channels)
    self.sa2 = SelfAttention(channels)
    self.sa3 = SelfAttention(channels)
    self.sa4 = SelfAttention(channels)

  def forward(self, xyz: torch.Tensor, x: torch.Tensor):
    """
    Input:
      xyz: input points position, [B, N, 3]
      x: input data, [B, S, D]
    """
    B, S, _ = xyz.shape
    xyz = xyz.permute(0, 2, 1)  # B, 3, S
    xyz = self.pos_xyz(xyz)     # B, D, S

    x = F.relu(self.bn1(self.conv1(x)))
    f1 = self.sa1(xyz, x)
    f2 = self.sa2(xyz, f1)
    f3 = self.sa3(xyz, f2)
    f4 = self.sa4(xyz, f3)
    x = torch.cat([f1, f2, f3, f4], dim=1) # B, 4 * D, S

    return x

class PCT(nn.Module):
  def __init__(self, d: int) -> None:
    """
    Input
      d: input dimension of features
    """
    super().__init__()
    self.conv1 = nn.Conv1d(d, 64, kernel_size=1, bias=False)
    self.bn1 = nn.BatchNorm1d(64)
    self.conv2 = nn.Conv1d(64, 64, kernel_size=1, bias=False)
    self.bn2 = nn.BatchNorm1d(64)
    self.gather_local_0 = LocalOperation(128, 128)
    self.gather_local_1 = LocalOperation(256, 256)
    self.transformer = PointTransformer(256)
    self.conv_fuse = nn.Sequential(
      nn.Conv1d(1280, 1024, kernel_size=1, bias=False),
      nn.BatchNorm1d(1024),
      nn.LeakyReLU(negative_slope=0.2))
    self.fc6 = nn.Linear(1024, 512)
    self.bn6 = nn.BatchNorm1d(512)
    self.do6 = nn.Dropout(0.5)
    self.fc7 = nn.Linear(512, 64)
    self.bn7 = nn.BatchNorm1d(64)
    self.do7 = nn.Dropout(0.5)
    self.fc8 = nn.Linear(64, 1)

  def forward(self, points: torch.Tensor):
    """
    Input:
      points: [B, N, C]
    """
    B, N, C = points.shape
    xyz = points[:, :, :3]

    # neighbour embedding for augmented local feature representation
    x: torch.Tensor = points.permute(0, 2, 1) # B, C, N
    x = F.relu(self.bn1(self.conv1(x)))
    x = F.relu(self.bn2(self.conv2(x)))
    x = x.permute(0, 2, 1)
    new_xyz, new_feature = sample_and_group(npoint=512, nsample=32, xyz=xyz, points=x) 
    feature0: torch.Tensor = self.gather_local_0(new_feature)
    feature0 = feature0.permute(0, 2, 1)
    new_xyz, new_feature = sample_and_group(npoint=256, nsample=32, xyz=new_xyz, points=feature0)
    feature1: torch.Tensor = self.gather_local_1(new_feature)

    # transformer
    x = self.transformer(new_xyz, feature1)
    x = torch.cat([x, feature1], dim=1)
    x = self.conv_fuse(x)
    x = F.adaptive_avg_pool1d(x, 1).view(B, -1)

    # predict
    x = self.do6(F.leaky_relu(self.bn6(self.fc6(x))))
    x = self.do7(F.leaky_relu(self.bn7(self.fc7(x))))
    x = self.fc8(x)

    return x

class CalLoss(nn.Module):
  def __init__(self) -> None:
    super().__init__()

  def forward(self, pred: torch.Tensor, target: torch.Tensor):
    """
    Input:
      pred:   [B, 1]
      target: [B, 1] 
    Output:
      loss:   [1]
    """
    B, _ = pred.shape
    loss = F.mse_loss(pred.double(), target.view(B, 1))
    print("loss: ", loss)
    return loss

  