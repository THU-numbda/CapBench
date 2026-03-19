from __future__ import annotations

import os

import torch


def ensure_torch_cuda_arch_list(device_index: int | None = None) -> str | None:
    current_value = os.environ.get("TORCH_CUDA_ARCH_LIST")
    if current_value:
        return current_value
    if not torch.cuda.is_available():
        return None

    resolved_index = 0 if device_index is None else int(device_index)
    major, minor = torch.cuda.get_device_capability(resolved_index)
    resolved_arch = f"{major}.{minor}"
    os.environ["TORCH_CUDA_ARCH_LIST"] = resolved_arch
    return resolved_arch
