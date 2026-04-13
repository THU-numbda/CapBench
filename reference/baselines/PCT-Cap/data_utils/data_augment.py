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


import numpy as np
import pandas as pd
import random

from .transform import PcCapTransform
from .pc_normalize import pc_normalize

def x_symmetry(x0: float, xyz: np.ndarray) -> np.ndarray:
  """
  Input
    x0: plane x = x0
    xyz: [x, y, z] perhaps appending with [nx, ny, nz]
  Output:
    xyz: symmetric about plane x = x0
  """
  xyz[:, 0] = 2 * x0 - xyz[:, 0]
  if xyz.shape[1] >= 4:
    xyz[:, 3] = -xyz[:, 3]
  return xyz

def y_symmetry(y0: float, xyz: np.ndarray) -> np.ndarray:
  """
  Input
    y0: plane y = y0
    xyz: [x, y, z] perhaps appending with [nx, ny, nz]
  Output:
    xyz: symmetric about plane y = y0
  """
  xyz[:, 1] = 2 * y0 - xyz[:, 1]
  if xyz.shape[1] >= 5:
    xyz[:, 4] = -xyz[:, 4]
  return xyz

def z_symmetry(z0: float, xyz: np.ndarray) -> np.ndarray:
  """
  Input
    z0: plane z = z0
    xyz: [x, y, z] perhaps appending with [nx, ny, nz]
  Output:
    xyz: symmetric about plane z = z0
  """
  xyz[:, 2] = 2 * z0 - xyz[:, 2]
  if xyz.shape[1] >= 6:
    xyz[:, 5] = -xyz[:, 5]
  return xyz  

class SymmetricTransform(PcCapTransform):
  def __init__(self, ann: pd.DataFrame = None) -> None:
    super().__init__(ann)
    self.sym_func = {
      0 : self.x_symmetry_api,
      1 : self.y_symmetry_api,
      2 : self.z_symmetry_api,
    }

  def x_symmetry_api(self, data: np.ndarray, index: int) -> np.ndarray:
    ann = self.get_ann()
    v1_x = ann.loc[index, "v1_x"]
    dx = ann.loc[index, "dx"]
    data = x_symmetry(v1_x + 0.5 * dx, data)
    return data
  
  def y_symmetry_api(self, data: np.ndarray, index: int) -> np.ndarray:
    ann = self.get_ann()
    v1_y = ann.loc[index, "v1_y"]
    dy = ann.loc[index, "dy"]
    data = y_symmetry(v1_y + 0.5 * dy, data)
    return data

  def z_symmetry_api(self, data: np.ndarray, index: int) -> np.ndarray:
    ann = self.get_ann()
    v1_z = ann.loc[index, "v1_z"]
    dz = ann.loc[index, "dz"]
    data = z_symmetry(v1_z + 0.5 * dz, data)
    return data

  def __call__(self, data: np.ndarray, index: int) -> np.ndarray:
    """
    Input:
      dataset: PcCapDataset
      data: 
      index: index of __getitem__()
    """
    func_id = random.randint(0, len(self.sym_func))
    if func_id < len(self.sym_func):
      data = self.sym_func[func_id](data, index)
    data[:, 0 : 3] = pc_normalize(data[:, 0 : 3])
    return data
    
