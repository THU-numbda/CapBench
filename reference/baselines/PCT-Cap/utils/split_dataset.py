
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

import pandas as pd

TRAIN_RATIO = 0.8
ann_path = "path/to/pc_annotation.csv"
total_train_path = "path/to/pc_annotation_total_train.csv"
total_test_path = "path/to/pc_annotation_total_test.csv"
coupling_train_path = "path/to/pc_annotation_coupling_train.csv"
coupling_test_path = "path/to/pc_annotation_coupling_test.csv"
ann_csv = pd.read_csv(ann_path, skipinitialspace=True)

def query_cdt_num(src: pd.DataFrame, cdt_num: int) -> pd.Series:
  return src["conductor_num"] == cdt_num

def query_total(src: pd.DataFrame) -> pd.Series:
  return src["cap_type"] == "total"

ann_title_dict: dict[str, int] = {}
for i, title in enumerate(ann_csv):
  ann_title_dict[title] = i

cdt_num_max = ann_csv["conductor_num"].max()
total_train_csv = pd.DataFrame(columns=ann_csv.columns)
total_test_csv = pd.DataFrame(columns=ann_csv.columns)
coupling_train_csv = pd.DataFrame(columns=ann_csv.columns)
coupling_test_csv = pd.DataFrame(columns=ann_csv.columns)

for cdt_num in range(2, cdt_num_max + 1):
  class_data = ann_csv.loc[query_cdt_num(ann_csv, cdt_num)]
  total_df = class_data.loc[query_total]
  coupling_df = pd.concat([class_data, total_df]).drop_duplicates(keep=False)
  samples_num = total_df.shape[0] / cdt_num
  # print(cdt_num, total_df.shape[0], coupling_df.shape[0])
  
  total_train_csv    = pd.concat([total_train_csv, (total_df.sample(int(total_df.shape[0] * TRAIN_RATIO), random_state=42))])  
  coupling_train_csv = pd.concat([coupling_train_csv, coupling_df.sample(int(coupling_df.shape[0] * TRAIN_RATIO), random_state=42)])

total_df = ann_csv[query_total]
total_test_csv = pd.concat([total_df, total_train_csv]).drop_duplicates(keep=False)

coupling_df = pd.concat([ann_csv, total_df]).drop_duplicates(keep=False)
coupling_test_csv = pd.concat([coupling_df, coupling_train_csv]).drop_duplicates(keep=False)


total_train_csv.to_csv(total_train_path, index=False)
total_test_csv.to_csv(total_test_path, index=False)
coupling_train_csv.to_csv(coupling_train_path, index=False)
coupling_test_csv.to_csv(coupling_test_path, index=False)
print(f"total_train_dataset: size {total_train_csv.shape[0]}, saves at ", total_train_path)
print(f"total_test_dataset: szie {total_test_csv.shape[0]}, saves at ", total_test_path)
print(f"coupling_train_dataset: szie {coupling_train_csv.shape[0]}, saves at ", coupling_train_path)
print(f"coupling_test_dataset: szie {coupling_test_csv.shape[0]}, saves at ", coupling_test_path)