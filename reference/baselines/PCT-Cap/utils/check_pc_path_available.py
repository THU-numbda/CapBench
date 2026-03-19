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

import argparse
import os
import pandas as pd
from pathlib import Path

parser = argparse.ArgumentParser(description="check the path of point cloud dataset")
parser.add_argument('--ann', metavar='path', help='the path to pc_annotation.csv', required=True)
args = parser.parse_args()

ann_path = args.ann
ann_csv = pd.read_csv(ann_path)
ann_title_dict: dict[str, int] = {}
for i, title in enumerate(ann_csv):
  ann_title_dict[title] = i
pc_dir =  str(Path(ann_path).parent) + "/"

print(f'checking path in terms of {ann_path}')
mis_match_num = 0
for row_index in range(ann_csv.shape[0]):
  pc_path = pc_dir + ann_csv.iloc[row_index, ann_title_dict["point_cloud_path"]]
  if not os.path.exists(pc_path):
    print(f"path mismatch: {pc_path}")
    mis_match_num += 1
print(f"check path num: {ann_csv.shape[0]}")
print(f"path mismatch num: {mis_match_num}, please check")