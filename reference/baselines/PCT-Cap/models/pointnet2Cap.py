import torch
import torch.nn as nn
import torch.nn.functional as F
from models.pointnet2_utils import PointNetSetAbstractionMsg, PointNetSetAbstraction

class PointNet2Cap(nn.Module):
  def __init__(self) -> None:
    super().__init__()
    self.sa1 = PointNetSetAbstractionMsg(512, [0.1, 0.2, 0.4], [16, 32, 128], 8,[[32, 32, 64], [64, 64, 128], [64, 96, 128]])
    self.sa2 = PointNetSetAbstractionMsg(128, [0.2, 0.4, 0.8], [32, 64, 128], 320,[[64, 64, 128], [128, 128, 256], [128, 128, 256]])
    self.sa3 = PointNetSetAbstraction(None, None, None, 640 + 3, [256, 512, 1024], True)
    self.fc1 = nn.Linear(1024, 512)
    self.bn1 = nn.BatchNorm1d(512)
    self.drop1 = nn.Dropout(0.4)
    self.fc2 = nn.Linear(512, 256)
    self.bn2 = nn.BatchNorm1d(256)
    self.drop2 = nn.Dropout(0.5)
    self.fc3 = nn.Linear(256, 64)
    self.bn3 = nn.BatchNorm1d(64)
    self.drop3 = nn.Dropout(0.5)
    self.fc4 = nn.Linear(64, 1)

  def forward(self, points: torch.Tensor):
    """
    Input
      points: input points data, [B, N, C]
    """
    points = points.permute(0, 2, 1) # [B, C, N]
    xyz = points[:, : 3, :]
    B, _, _ = points.shape
    l1_xyz, l1_points = self.sa1(xyz, points)
    l2_xyz, l2_points = self.sa2(l1_xyz, l1_points)
    l3_xyz, l3_points = self.sa3(l2_xyz, l2_points)
    x = l3_points.view(B, 1024)
    x = self.drop1(F.relu(self.bn1(self.fc1(x))))
    x = self.drop2(F.relu(self.bn2(self.fc2(x))))
    x = self.drop3(F.relu(self.bn3(self.fc3(x))))
    x = self.fc4(x)
    
    return x

class CalLoss(nn.Module):
  def __init__(self, target_transform = None) -> None:
    self.tar_trans = target_transform
    super().__init__()

  def forward(self, pred: torch.Tensor, target: torch.Tensor, trans_feat: torch.Tensor = None):
    """
    Input
      pred: prediction, [B, 1]
      target: [B]
    """

    if (self.tar_trans):
      target = self.tar_trans(target)

    B, _ = pred.shape
    loss = F.mse_loss(pred, target.float().view(B, 1))
    print("loss: ", loss)
    return loss