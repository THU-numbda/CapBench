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

def supplement(data: np.ndarray , npoints: int) -> np.ndarray:
  while data.shape[0] < npoints:
      indexs: list = random.sample(range(0, data.shape[0]), (npoints - data.shape[0]) % data.shape[0])
      data_repeat: np.ndarray = data[indexs]
      data = np.append(data, data_repeat, axis = 0)

  return data

class PcCapSampler:
  """An abstract class of Sampler"""
  
  def __init__(self, ann: pd.DataFrame = None) -> None:
    self.ann = ann
  
  def set_ann(self, ann: pd.DataFrame = None) -> None:
    """ann: point cloud annotations file"""
    self.ann = ann

  def get_ann(self) -> pd.DataFrame:
    if self.ann is  None:
      raise ValueError("Empty point cloud annotations file")
    return self.ann
  
  def __call__(self, data: np.ndarray, index: int, npoints: int) -> np.ndarray:
    """
    Input
      data: [N, C], point cloud data,
        N is the original number of points,
        C = [x, y, z, nx, ny, nz, diel, flux]
      index: index in annotation
      npoints: number of sampling point
    """
    raise NotImplementedError

class RandomSampler(PcCapSampler):
  def __init__(self, ann: pd.DataFrame = None) -> None:
    super().__init__(ann)

  def __call__(self, data: np.ndarray, index: int, npoints: int) -> np.ndarray:
    """
    Output
      data: [min(N, npoints), C] 
    """
    data = supplement(data, npoints)

    indexs: list = random.sample(range(0, data.shape[0]), min(npoints, data.shape[0]))
    data = data[indexs]

    return data
