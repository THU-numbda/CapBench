# ***************************************************************************************
# Copyright (c) 2023-2025 Peng Cheng Laboratory
# Copyright (c) 2023-2025 Institute of Computing Technology, Chinese Academy of Sciences
# Copyright (c) 2023-2025 Beijing Institute of Open Source Chip
#
# iEDA is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
# http://license.coscl.org.cn/MulanPSL2
#
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
#
# See the Mulan PSL v2 for more details.
# ***************************************************************************************

import torch
import torch.nn as nn
import torch.nn.functional as F

class SelfAttention(nn.Module):
  def __init__(self, de: int, da: int) -> None:
    """
    Input
      de: dimension of embedding
      da: dimension of attention (dimension of q and k vectors)
    """
    super().__init__()
    self.q_conv = nn.Conv1d(de, da, kernel_size=1, bias=False)
    self.k_conv = nn.Conv1d(de, da, kernel_size=1, bias=False)
    self.v_conv = nn.Conv1d(de, de, kernel_size=1, bias=False)
    self.softmax = nn.Softmax(dim=-1)

  def forward(self, x: torch.Tensor):
    """
    Input
      x: (de, N). de: dimension of embedding; N point acount
    """
    x_q: torch.Tensor = self.q_conv(x) # B, da, N
    x_k: torch.Tensor = self.k_conv(x) # B, da, N
    x_v: torch.Tensor = self.v_conv(x) # B, de, N
    
    attention:torch.Tensor = self.softmax(torch.bmm(x_q.permute(0, 2, 1), x_k)) # B, N, N
    attention = attention / (1e-9 + attention.sum(dim=1, keepdim=True))
    z: torch.Tensor = torch.bmm(x_v, attention) # B, de, N

    # skip connect
    x = x + z # B, de, N

    return x

class PCT_Cap(nn.Module):
  def __init__(self, channels: int, num_sa: int, npoints: int) -> None:
    super().__init__()
    assert npoints > 0, "npoints should be positive"

    self.npoints = npoints
    self.conv1 = nn.Conv1d(channels, 64, 1)
    self.bn1 = nn.BatchNorm1d(64)
    self.conv2 = nn.Conv1d(64, 256, 1)
    self.bn2 = nn.BatchNorm1d(256)
    
    self.sa_list = nn.Sequential()
    for i in range(num_sa):
      self.sa_list.append(SelfAttention(256, 256))
    self.fc1 = nn.Linear(npoints, npoints)
    self.fc2= nn.Linear(npoints, 1)

  def forward(self, x: torch.Tensor) -> torch.Tensor:
    """
    Input
      x: [B, N, C]
    Output
      x: [B, 1]
    """
    x = x.permute(0, 2, 1)
    x = F.relu(self.bn1(self.conv1(x)))
    x = F.relu(self.bn2(self.conv2(x)))
    for sa in self.sa_list:
      x = sa(x)
    x = x.permute(0, 2, 1)
    x = F.adaptive_avg_pool1d(x, 1).view(-1, self.npoints)
    x = F.relu(self.fc1(x))
    x = self.fc2(x)

    return x
  
class CalLoss(nn.Module):
  def  __init__(self) -> None:
    super().__init__()

  def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """
    Input
      pred:   [B, 1]
      target: [B, 1]
    Output
      loss:   [1, 1]
    """
    B, _ = pred.shape
    # rmse
    pred = pred.view(B, -1).contiguous()
    target = target.view(B, -1).contiguous()
    loss = F.mse_loss(pred, target)
    loss = torch.sqrt(loss + 1e-12)

    return loss
