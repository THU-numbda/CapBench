import torch
from torch import nn
from torch.nn import functional as F

class Residual(nn.Module):
  def __init__(self,
    in_channels:  int,
    out_channels: list[int],
    stride:       int  = 1
  ) -> None:
    super().__init__()
    f1, f2, f3 = out_channels
    self.stride = stride
    self.in_channels = in_channels
    self.out_channels = f3
    
    self.conv1 = nn.Conv1d(in_channels, f1, kernel_size=1, padding=0, stride=stride)
    self.conv2 = nn.Conv1d(f1, f2, kernel_size=3, padding=1, stride=1)
    self.conv3 = nn.Conv1d(f2, f3, kernel_size=1, padding=0, stride=1)

    self.bn1 = nn.BatchNorm1d(f1)
    self.bn2 = nn.BatchNorm1d(f2)
    self.bn3 = nn.BatchNorm1d(f3)

    self.downsample = nn.Sequential(
      nn.Conv1d(in_channels, f3, kernel_size=1, stride=stride),
      nn.BatchNorm1d(f3)
    )

  def forward(self, x: torch.Tensor):
    y = F.relu(self.bn1(self.conv1(x)))
    y = F.relu(self.bn2(self.conv2(y)))
    y = self.bn3(self.conv3(y))
    if self.stride != 1 or self.in_channels != self.out_channels:
      x = self.downsample(x)
    y += x
    return F.relu(y)

class ResNetBlock(nn.Module):
  def __init__(self,
    in_channels:   int,
    out_channels:  list[int],
    num_residuals: int,
    first_block:   bool = False
  ) -> None:
    super().__init__()
    self.blk = nn.Sequential()
    for i in range(num_residuals):
      if i == 0 and not first_block:
        self.blk.append(Residual(in_channels, out_channels, stride=2))
      else:
        self.blk.append(Residual(in_channels, out_channels))
      in_channels = out_channels[-1]

  def forward(self, x: torch.Tensor):
    for blk in self.blk:
      x = blk(x)
    return x

class ResNet101Cap(nn.Module):
  def __init__(self, in_channels: int) -> None:
    super().__init__()
    self.b1 = nn.Sequential(
      nn.Conv1d(in_channels, 64, kernel_size=7, stride=2, padding=3), # (N - 7 + 2 * 3) / 2 + 1
      nn.BatchNorm1d(64),
      nn.ReLU(),
      nn.MaxPool1d(kernel_size=3, stride=2, padding=1)                # (N - 3 + 2 * 1) / 2 + 1
    )                                                                  # 1
    self.b2 = ResNetBlock(  64, [ 64,  64,  256], 3, first_block=True) # 3 * 3
    self.b3 = ResNetBlock( 256, [128, 128,  512], 4)                   # 4 * 3
    self.b4 = ResNetBlock( 512, [256, 256, 1024], 23)                  #23 * 3
    self.b5 = ResNetBlock(1024, [512, 512, 2048], 3)                   # 3 * 3
    self.fl = nn.Flatten()
    self.fc = nn.Linear(2048, 1)                                       # 1
  
  def forward(self, x: torch.Tensor):
    """
    Input
      x: [B, N, C]
    Output
      x: [B, 1]
    """
    x = x.permute(0, 2, 1)          #    C, 1024
    x = self.b1(x)                  #   64, 256
    x = self.b2(x)                  #   64, 256
    x = self.b3(x)                  #  512, 128
    x = self.b4(x)                  # 1024, 64
    x = self.b5(x)                  # 2048, 32
    x = F.adaptive_avg_pool1d(x, 1) # 2048, 1
    x = self.fl(x)                  # 2048
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