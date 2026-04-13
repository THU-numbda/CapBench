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

import math
import numpy as np
import pandas as pd
import random

from .sampler import PcCapSampler, supplement

class GridSampler(PcCapSampler):
  def __init__(self,
    size: object,
    ann: pd.DataFrame = None,
    init_density: float = 0.9,
    decay: float = 0.9
  ) -> None:
    super().__init__(ann)
    self.size = None
    self.set_init_density(init_density)
    self.set_decay(decay)
    self.set_size(size)
  
  def set_size(self, size: object) -> None:
    check = np.array(size) > 0
    if len(size) == 3 and sum(check) == 3:
      self.size: tuple = size
    else: raise ValueError("3 positive numbers are required to describe spatial grid shape in x, y, z dimension")

  def set_init_density(self, density: float) -> None:
    assert density > 0 and density <= 1, "invalid value of init_density"
    self.init_density = density

  def set_decay(self, decay: float) -> None:
    assert decay > 0 and decay <= 1, "invalid value of decay"
    self.decay = decay
  
  def binary_search(self, arr: list, e: object) -> int:
    """
    Input
      arr: an ascending sequence
      e: element to search
    """
    left = 0
    right = len(arr) - 1
    if left >= right or e < arr[0] or e > arr[right]: return -1  

    max_depth = math.ceil(math.log2(len(arr)))
    for depth in range(max_depth):
      if left + 1 == right: break

      mid = math.floor(0.5 * (left + right))
      if e == arr[mid]:
        left = right = mid
        break
      elif e < arr[mid]:
        right = mid
      else:
        left = mid
    
    return left

  def density_strategy(self,
    grid_d3: np.ndarray,
    init_density: float,
    decay: float
  ) -> np.ndarray:
    """
    Input:
      grid_d3: [nx, ny, nz, 3]. 3D index. 3 = (main, target env, non-target env)
    """
    visited = np.zeros(self.size, dtype=bool)
    density_grid = np.zeros(self.size)

    # source queue
    queue: list[tuple[int, int, int]] = []
    for i in range(self.size[0]):
      for j in range(self.size[1]):
        for k in range(self.size[2]):
          if grid_d3[i, j, k, 0] != 0 or grid_d3[i, j, k, 1] != 0:
            # main conductors enqueue or target environment conductors enqueue
            queue.append((i, j, k))
            visited[i, j, k] = 1
            density_grid[i, j, k] = init_density
    
    directions = [(-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)]
    while len(queue) > 0:
      round_visited = np.zeros(self.size, dtype=bool)
      for n in range(len(queue)):
        # current grid
        i,j,k = queue.pop(0) 
        for d in directions:
          # next grid
          next_i, next_j, next_k = d[0] + i, d[1] + j, d[2] + k
          if self.grid_boundary_check(next_i, next_j, next_k) and \
             (visited[next_i, next_j, next_k] == False and round_visited[next_i, next_j, next_k] == False):
            queue.append((next_i, next_j, next_k))
            round_visited[next_i, next_j, next_k] = True
            # density strategy of next grid
            density = 1
            from_conductor = False
            for di, dj, dk in directions:
              source_i, source_j, source_k = next_i + di, next_j + dj, next_k + dk
              if self.grid_boundary_check(source_i, source_j, source_k) and \
                 visited[source_i, source_j, source_k] == True:
                density = min(density, density_grid[source_i, source_j, source_k])
                from_conductor |= sum(grid_d3[source_i, source_j, source_k]) > 0
            if from_conductor:
              # strategy 1: density decay when going through conductor
              density_grid[next_i, next_j, next_k] = density * decay
            else:
              # strategy 2: density stay when going through dielectric
              density_grid[next_i, next_j, next_k] = density

      # update visited before next round
      visited = visited | round_visited
      
    return density_grid

  def grid_boundary_check(self, i:int, j:int, k:int) -> bool:
    if i >= 0 and i < self.size[0] and \
       j >= 0 and j < self.size[1] and \
       k >= 0 and k < self.size[2]:
      return True
    else:
      return False
  
  def pack_grid_id(self, x_idx: int, y_idx: int, z_idx: int) -> int:
    return x_idx + y_idx * self.size[0] + z_idx * self.size[0] * self.size[1]

  def unpack_grid_id(self, idx: int) -> tuple[int, int, int]:
    z_idx = math.floor( idx / (self.size[0] * self.size[1]) ) 
    y_idx = math.floor((idx - z_idx * (self.size[0] * self.size[1])) / self.size[0])
    x_idx = int( idx - y_idx * self.size[0] - z_idx * self.size[0] * self.size[1] )
    return x_idx, y_idx, z_idx

  def __call__(self, data: np.ndarray, index: int, npoints: int) -> np.ndarray:
    """
    Input
      data: [N, C], point cloud data, [x, y, z, nx, ny, nz, diel, flux]
      index: 
      npoints: 
    """
    assert npoints > 0
    data = supplement(data, npoints)
    
    extend_info = self.get_ann().loc[index]
    x_interval = np.linspace(extend_info["v1_x"], extend_info["v1_x"] + extend_info["dx"], self.size[0])
    y_interval = np.linspace(extend_info["v1_y"], extend_info["v1_y"] + extend_info["dy"], self.size[1])
    z_interval = np.linspace(extend_info["v1_z"], extend_info["v1_z"] + extend_info["dz"], self.size[2])

    point_num = data.shape[0]
    sampling_target = np.zeros((len(data), 4))
    grid_d3 = np.zeros(self.size +(3,))
    for point_id in range(point_num):
      p = data[point_id]
      x_idx = self.binary_search(x_interval, p[0])
      y_idx = self.binary_search(y_interval, p[1])
      z_idx = self.binary_search(z_interval, p[2])
      sampling_target[point_id, :3] = (point_id, self.pack_grid_id(x_idx, y_idx, z_idx), random.random())
      if p[7] > 0:
        grid_d3[x_idx, y_idx, z_idx, 0] += 1 # main conductor
      elif p[7] < 0:
        grid_d3[x_idx, y_idx, z_idx, 1] += 1 # target environment conductor
      else:
        grid_d3[x_idx, y_idx, z_idx, 2] += 1 # non-target environment conductor
    
    density_grid = self.density_strategy(grid_d3, self.init_density, self.decay)

    for point_id in range(point_num):
      x_idx, y_idx, z_idx = self.unpack_grid_id(sampling_target[point_id, 1])
      sampling_target[point_id, 3] = sampling_target[point_id, 2] * density_grid[x_idx, y_idx, z_idx]
    sampling_target = sampling_target[np.argsort(sampling_target[:, 3])[::-1]]
    output_index = sampling_target[:, 0].astype(int)

    data = data[output_index[: npoints]]
  
    return data
