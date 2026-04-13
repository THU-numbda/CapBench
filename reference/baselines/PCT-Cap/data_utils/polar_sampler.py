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
from enum import Enum


from .sampler import PcCapSampler, supplement

class PolarCenter(Enum):
  Sample = 1
  MainConductor = 2

class PolarSampler(PcCapSampler):
  """
  PolarSampler contains transform and sampler, it is recommended to set 
    PcCapDataset(... sampler=PolarSampler(), transform=None, ...)
  for functional correctness.
  
  ------------------------------------
        z+
        |  * (r, theta, phi)
  theta |-/|    
        |/_|_________ y+
   phi /_\ |
      /   \|
    x+  
    
    when Pole(0,0,0)
    
    r = sqrt(x^2 + y^2 + z^2)
    theta = arctan( sqrt(x^2 + y^2) / z ) = arccos( z/ sqrt(x^2 + y^2 + z^2) )
    phi = arctan(y/x)
    ----------------------------
    x = r*sin(theta)cos(phi) 
    y = r*sin(theta)sin(phi) 
    z = r*cos(theta)
  """

  def __init__(self, ann: pd.DataFrame = None, center: PolarCenter = PolarCenter.Sample) -> None:
    super().__init__(ann)
    self.center = center
    self.centralize_fun = {
      PolarCenter.Sample        : self.SampleCentralize,
      PolarCenter.MainConductor : self.MainConductorCentralize
    }
  
  def set_center(self, center: PolarCenter)->None:
    self.center = center

  def __call__(self, data: np.ndarray, index: int, npoints: int) -> np.ndarray:
    """
    Input
      data: [N, C], point cloud, feature(channel): [x, y, z, nx, ny, nz, diel, flux]
    Output
    """
    data = supplement(data, npoints)

    # ---transform---
    data = self.centralize_fun[self.center](data, index)
    polar_coord = np.zeros((data.shape[0], 3))
    # r = sqrt(x^2 + y^2 + z^2)
    polar_coord[:, 0] = np.sqrt(np.sum(data[:, : 3]**2, axis=1))
    # theta = arctan( sqrt(x^2 + y^2) / z )
    polar_coord[:, 1] = np.arctan( np.sqrt(np.sum(data[:, :2]**2, axis=1)) / (data[:, 2] + 1e-15) )
    # phi = arctan(y/x)
    polar_coord[:, 2] = np.arctan( data[:, 1] / (data[:, 0] + 1e-15) )
    data[:, :3] = polar_coord

    # ---sample---
    target = np.zeros((data.shape[0], 2))
    # id
    target[:, 0] = np.arange(0, data.shape[0])
    # sampling strategy
    target[:, 1] = data[:, 0] * np.random.rand(data.shape[0])
    output_index = np.argsort(target[:, 1])[::-1]
    
    data = data[output_index[: npoints]]
    return data

  def SampleCentralize(self, data: np.ndarray, index: int) -> np.ndarray:
    ann = self.get_ann()
    v1_x = ann.loc[index, "v1_x"]
    v1_y = ann.loc[index, "v1_y"]
    v1_z = ann.loc[index, "v1_z"]
    dx = ann.loc[index, "dx"]
    dy = ann.loc[index, "dy"]
    dz = ann.loc[index, "dz"]
    cx = v1_x + 0.5 * dx
    cy = v1_y + 0.5 * dy
    cz = v1_z + 0.5 * dz
    data[:, 0] = data[:, 0] - cx
    data[:, 1] = data[:, 1] - cy
    data[:, 2] = data[:, 2] - cz
    return data
    
  def MainConductorCentralize(self, data: np.ndarray, index: int) -> np.ndarray: 
    mask_main = data[:, 7] == 1
    centroid = np.mean(data[:, :3][mask_main], axis=0)
    data[:, 0] = data[:, 0] - centroid[0]
    data[:, 1] = data[:, 1] - centroid[1]
    data[:, 2] = data[:, 2] - centroid[2]
    return data
    
