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

from typing import Any
import numpy as np
import pandas as pd

from .pc_normalize import pc_normalize

class PcCapTransform:
  """An abstract class of Transform"""
  
  def __init__(self, ann: pd.DataFrame = None) -> None:
    self.ann = ann

  def set_ann(self, ann: pd.DataFrame = None) -> None:
    """ann: point cloud annotations file"""
    self.ann = ann

  def get_ann(self) -> pd.DataFrame:
    if self.ann is  None:
      raise ValueError("Empty point cloud annotations file")
    return self.ann

  def __call__(self, data: np.ndarray, index: int) -> np.ndarray:
    raise NotImplementedError

class NormalizeTransform(PcCapTransform):
  def __init__(self, ann: pd.DataFrame = None) -> None:
    super().__init__(ann)

  def __call__(self, data: np.ndarray, index: int) -> np.ndarray:
    data[:, 0 : 3] = pc_normalize(data[:, 0 : 3])
    return data