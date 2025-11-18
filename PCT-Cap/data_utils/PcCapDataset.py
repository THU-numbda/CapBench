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
import torch
from pathlib import Path
from torch.utils.data import Dataset

from .sampler import PcCapSampler, RandomSampler
from .transform import PcCapTransform, NormalizeTransform

class PcCapDataset(Dataset):
  def __init__(self,
    annotations_file: str,
    npoints: int = 1024,
    sampler: object = RandomSampler(),
    transform: object = NormalizeTransform(),
    target_transform: callable = None,
  ):
    """
    Input:
      annotations_file: point cloud annotation file
      npoints: output point cloud scale 
      sampler: point sampler
      transform: point cloud data transformation
      target_transform: label data transformation
    """
    self.npoints = npoints
    self.ann = pd.DataFrame()
    self.pc_dir: str = ""
    self.sampler: PcCapSampler = sampler
    self.transform: PcCapTransform = transform
    self.target_transform = target_transform
    self.title_dict: dict[str, int] = {}

    self.read_annotations(annotations_file)
    
  def read_annotations(self, annotations_file: str) -> None:
    self.ann = pd.read_csv(annotations_file)
    if self.sampler: self.sampler.set_ann(self.ann)
    if self.transform: self.transform.set_ann(self.ann)

    self.pc_dir = str(Path(annotations_file).parent) + "/"
    for i, title in enumerate(self.ann):
      self.title_dict[title] = i

  def __getitem__(self, index) -> tuple[torch.Tensor, np.float32]:
    """
    Output
      original data: [N, C], point cloud, feature(channel): [x, y, z, nx, ny, nz, diel, flux]
      label: capacitance value
    """
    data_path: str = self.pc_dir + self.ann.iloc[index, self.title_dict["point_cloud_path"]]
    data: np.ndarray = np.loadtxt(data_path, delimiter=',').astype(np.float32)
    if data.shape[1] == 9:
      data = np.delete(data, 7, axis=1)
    label: np.float32 = self.ann.iloc[index, self.title_dict["cap"]]

    if self.sampler:
      data = self.sampler(data, index, self.npoints)
    
    if self.transform:
      data = self.transform(data, index)
    
    if self.target_transform:
      label = self.target_transform(label)

    return data, label
    
  def __len__(self) -> int:
    return len(self.ann)
