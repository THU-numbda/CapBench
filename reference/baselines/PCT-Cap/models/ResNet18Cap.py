import torch
from torch import nn
from torch.nn import functional as F

class Residual(nn.Module):
  def __init__(self,
    in_channels:  int,
    out_channels: int,
    use_1x1conv:  bool = False,
    strides:      int  = 1
  ) -> None:
    super().__init__()
    self.conv1 = nn.Conv1d(in_channels,  out_channels, kernel_size=3, padding=1, stride=strides) # (before -3 + 2 * 1) / strides + 1
    self.conv2 = nn.Conv1d(out_channels, out_channels, kernel_size=3, padding=1)                 # -3 + 2 * 1 + 1 = 0, keep shape
    self.conv3 = None
    
    if use_1x1conv:
      self.conv3 = nn.Conv1d(in_channels, out_channels, kernel_size=1, stride=strides)

    self.bn1 = nn.BatchNorm1d(out_channels)
    self.bn2 = nn.BatchNorm1d(out_channels)

  def forward(self, x: torch.Tensor):
    y = F.relu(self.bn1(self.conv1(x)))
    y = self.bn2(self.conv2(y))
    if self.conv3:
      x = self.conv3(x)
    y += x
    return F.relu(y)

class ResNetBlock(nn.Module):
  def __init__(self,
    in_channels:   int,
    out_channels:  int,
    num_residuals: int,
    first_block:   bool = False
  ) -> None:
    super().__init__()
    self.blk = nn.Sequential()
    for i in range(num_residuals):
      if i == 0 and not first_block:
        self.blk.append(Residual(in_channels, out_channels, use_1x1conv=True, strides=2))
      else:
        self.blk.append(Residual(out_channels, out_channels))
  
  def forward(self, x: torch.Tensor):
    for blk in self.blk:
      x = blk(x)
    return x

class ResNet18Cap(nn.Module):
  def __init__(self, in_channels: int) -> None:
    super().__init__()
    self.b1 = nn.Sequential(
      nn.Conv1d(in_channels, 64, kernel_size=7, stride=2, padding=3), # (N - 7 + 2 * 3) / 2 + 1
      nn.BatchNorm1d(64),
      nn.ReLU(),
      nn.MaxPool1d(kernel_size=3, stride=2, padding=1)                # (N - 3 + 2 * 1) / 2 + 1
    )                                                    # 1
    self.b2 = ResNetBlock(64, 64,   2, first_block=True) # 2 * 2
    self.b3 = ResNetBlock(64, 128,  2)                   # 2 * 2
    self.b4 = ResNetBlock(128, 256, 2)                   # 2 * 2
    self.b5 = ResNetBlock(256, 512, 2)                   # 2 * 2
    self.fl = nn.Flatten()
    self.fc = nn.Linear(512, 1)                          # 1
  
  def forward(self, x: torch.Tensor):
    """
    Input
      x: [B, N, C]
    Output
      x: [B, 1]
    """
    x = x.permute(0, 2, 1)          #   C, 1024
    x = self.b1(x)                  #  64, 256
    x = self.b2(x)                  #  64, 256
    x = self.b3(x)                  # 128, 128
    x = self.b4(x)                  # 256, 64
    x = self.b5(x)                  # 512, 32
    x = F.adaptive_avg_pool1d(x, 1) # 512, 1
    x = self.fl(x)                  # 512
    x = self.fc(x)                  # 1
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
    loss = F.mse_loss(pred.double(), target.view(B, -1))
    loss = torch.sqrt(loss)

    return loss