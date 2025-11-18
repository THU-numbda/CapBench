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

cp_train_path = "/path/to/PC_Cap_3D_Dataset/pc_annotation_coupling_train.csv"
cp_test_path = "/path/to/PC_Cap_3D_Dataset/pc_annotation_coupling_test.csv"
cp_train_clean_path = "/path/to/PC_Cap_3D_Dataset/pc_annotation_coupling_train_clean.csv"
cp_test_clean_path = "/path/to/PC_Cap_3D_Dataset/pc_annotation_coupling_test_clean.csv"

cp_train_csv = pd.read_csv(cp_train_path, skipinitialspace=True)
cp_test_csv = pd.read_csv(cp_test_path, skipinitialspace=True)

def query_my_data(src: pd.DataFrame) -> pd.Series:
  return (src["cap_type"] == "coupling") \
    & ( 1e-17 <= src["cap"] ) \
    & ( (src["electrode1_point_num"] + src["electrode2_point_num"]) / src["point_num"] > 0.4)
cp_train_clean_csv = cp_train_csv.loc[query_my_data]
cp_train_clean_csv.to_csv(cp_train_clean_path, index=False)
print("cp_train_clean_ann saves: ", cp_train_clean_path, " , size: ", cp_train_clean_csv.shape[0])

cp_test_clean_csv = cp_test_csv.loc[query_my_data]
cp_test_clean_csv.to_csv(cp_test_clean_path, index=False)
print("cp_test_clean_ann saves: ", cp_test_clean_path, " , size: ", cp_test_clean_csv.shape[0])