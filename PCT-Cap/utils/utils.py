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

import datetime
import logging
import os
import random
import shutil
import torch

from pathlib import Path

'''global variables'''
logger: logging.Logger = None

def cur_time(fmt: str="%Y%m%d%H%M%S") -> str:
  now = datetime.datetime.now()
  return now.strftime(fmt)

def init_log(model_name: str=None) -> None:
  if model_name is None:
    model_name = "Log" + cur_time()
  global logger
  logger = logging.getLogger(model_name)
  logger.setLevel(logging.INFO)
  formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
  log_dir = Path(os.getcwd() + f'/log/{model_name}')
  log_dir.mkdir(parents=True, exist_ok=True)
  file_handler = logging.FileHandler('%s/log.txt' % (log_dir))
  file_handler.setLevel(logging.INFO)
  file_handler.setFormatter(formatter)
  logger.addHandler(file_handler)

def log_string(str: str) -> None:
  if logger:
    logger.info(str)
  print(str)

def set_seed(seed: int = 0) -> None:
  random.seed(seed)
  torch.manual_seed(seed)
  torch.cuda.manual_seed(seed)
  torch.cuda.manual_seed_all(seed)
  torch.backends.cudnn.deterministic = True

def back_up(files: list[str], dir: str) -> None:
  """
  back up files to the directory
  Input
    files: files to back up
    dir: destination directory  
  """
  dir_path = Path(dir)
  dir_path.mkdir(exist_ok=True, parents=True)
  for f in files:
    shutil.copy(f,  str(dir) + "/" + os.path.basename(f))

def try_gpu(index: int = 0) -> torch.device:
  if index < 0:
    return torch.device('cpu')
  elif torch.cuda.device_count() >= index + 1:
    return torch.device(f'cuda:{index}')
  return torch.device('cpu')