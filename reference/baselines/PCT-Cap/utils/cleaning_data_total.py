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

total_train_path = "/path/to/PC_Cap_3D_Dataset/pc_annotation_total_train.csv"
total_test_path = "/path/to/PC_Cap_3D_Dataset/pc_annotation_total_test.csv"
total_train_clean_path = "/path/to/PC_Cap_3D_Dataset/pc_annotation_total_train_clean.csv"
total_test_clean_path = "/path/to/PC_Cap_3D_Dataset/pc_annotation_total_test_clean.csv"

total_train_csv = pd.read_csv(total_train_path, skipinitialspace=True)
total_test_csv = pd.read_csv(total_test_path, skipinitialspace=True)

def query_my_data(src: pd.DataFrame) -> pd.Series:
  return (src["cap_type"] == "total") & (1e-17 <= src["cap"])

total_train_clean_csv = total_train_csv.loc[query_my_data]
total_train_clean_csv.to_csv(total_train_clean_path, index=False)
print("total_train_clean_csv saves: ", total_train_clean_path, " , size: ", total_train_clean_csv.shape[0])

total_test_clean_csv = total_test_csv.loc[query_my_data]
total_test_clean_csv.to_csv(total_test_clean_path, index=False)
print("total_test_clean_csv saves: ", total_test_clean_path, " , size: ", total_test_clean_csv.shape[0])