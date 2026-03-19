#include <torch/extension.h>
#include <ATen/cuda/CUDAContext.h>
#include <c10/cuda/CUDAGuard.h>
#include <c10/cuda/CUDAException.h>
#include <algorithm>
#include <cstdint>
#include <cuda.h>
#include <cuda_runtime.h>

constexpr int RECT_COL_LAYER = 0;
constexpr int RECT_COL_CONDUCTOR_ID = 1;
constexpr int RECT_COL_PX_MIN = 2;
constexpr int RECT_COL_PX_MAX = 3;
constexpr int RECT_COL_PY_MIN = 4;
constexpr int RECT_COL_PY_MAX = 5;
constexpr int RECT_COL_COUNT = 6;

__device__ __forceinline__ unsigned long long* as_ull_ptr(int64_t* ptr) {
    return reinterpret_cast<unsigned long long*>(ptr);
}

__global__ void paint_id_kernel(
    const int32_t* __restrict__ packed_rects,
    int16_t* __restrict__ out,
    int64_t block_count,
    int64_t num_layers,
    int64_t height,
    int64_t width) {
    int64_t idx = static_cast<int64_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (idx >= block_count) {
        return;
    }

    const int64_t row = idx * RECT_COL_COUNT;
    const int32_t layer = packed_rects[row + RECT_COL_LAYER];
    const int32_t cid = packed_rects[row + RECT_COL_CONDUCTOR_ID];
    if (layer < 0 || cid <= 0 || layer >= num_layers) {
        return;
    }

    const int32_t x0 = max(0, packed_rects[row + RECT_COL_PX_MIN]);
    const int32_t x1 = min(static_cast<int32_t>(width), packed_rects[row + RECT_COL_PX_MAX]);
    const int32_t y0 = max(0, packed_rects[row + RECT_COL_PY_MIN]);
    const int32_t y1 = min(static_cast<int32_t>(height), packed_rects[row + RECT_COL_PY_MAX]);
    if (x0 >= x1 || y0 >= y1) {
        return;
    }

    const int64_t layer_base = static_cast<int64_t>(layer) * height * width;
    for (int32_t y = y0; y < y1; ++y) {
        const int64_t row_base = layer_base + static_cast<int64_t>(y) * width;
        for (int32_t x = x0; x < x1; ++x) {
            out[row_base + x] = static_cast<int16_t>(cid);
        }
    }
}

__global__ void build_owned_sparse_metadata_kernel(
    int16_t* __restrict__ full_local_map,
    uint8_t* __restrict__ occupied,
    int16_t* __restrict__ owned_local_map,
    int64_t* __restrict__ owned_counts,
    int32_t* __restrict__ visible_flags,
    int64_t total_pixels,
    int64_t height,
    int64_t width,
    int64_t real_conductor_count,
    int64_t own_x0,
    int64_t own_x1,
    int64_t own_y0,
    int64_t own_y1) {
    const int64_t flat_idx = static_cast<int64_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (flat_idx >= total_pixels) {
        return;
    }

    int64_t cid = static_cast<int64_t>(full_local_map[flat_idx]);
    if (cid <= 0 || cid > real_conductor_count) {
        full_local_map[flat_idx] = static_cast<int16_t>(0);
        occupied[flat_idx] = static_cast<uint8_t>(0);
        owned_local_map[flat_idx] = static_cast<int16_t>(0);
        return;
    }

    occupied[flat_idx] = static_cast<uint8_t>(1);
    atomicExch(visible_flags + cid, 1);

    const int64_t x = flat_idx % width;
    const int64_t y = (flat_idx / width) % height;
    if (x >= own_x0 && x < own_x1 && y >= own_y0 && y < own_y1) {
        owned_local_map[flat_idx] = static_cast<int16_t>(cid);
        atomicAdd(as_ull_ptr(owned_counts + cid), 1ULL);
        return;
    }

    owned_local_map[flat_idx] = static_cast<int16_t>(0);
}

__global__ void scatter_owned_sparse_indices_kernel(
    const int16_t* __restrict__ owned_local_map,
    int64_t* __restrict__ sparse_indices,
    int64_t* __restrict__ write_offsets,
    int64_t total_pixels,
    int64_t max_sparse_points) {
    const int64_t flat_idx = static_cast<int64_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (flat_idx >= total_pixels) {
        return;
    }

    const int64_t cid = static_cast<int64_t>(owned_local_map[flat_idx]);
    if (cid <= 0) {
        return;
    }

    const int64_t position = static_cast<int64_t>(atomicAdd(as_ull_ptr(write_offsets + cid), 1ULL));
    if (position >= max_sparse_points) {
        return;
    }
    sparse_indices[cid * max_sparse_points + position] = flat_idx;
}

__global__ void paint_binary_masks_kernel(
    const int32_t* __restrict__ packed_rects,
    uint8_t* __restrict__ occupied,
    uint8_t* __restrict__ master_masks,
    int64_t block_count,
    int64_t num_layers,
    int64_t height,
    int64_t width,
    int64_t real_conductor_count) {
    int64_t idx = static_cast<int64_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (idx >= block_count) {
        return;
    }

    const int64_t row = idx * RECT_COL_COUNT;
    const int32_t layer = packed_rects[row + RECT_COL_LAYER];
    const int32_t cid = packed_rects[row + RECT_COL_CONDUCTOR_ID];
    if (layer < 0 || cid <= 0 || layer >= num_layers) {
        return;
    }

    const int32_t x0 = max(0, packed_rects[row + RECT_COL_PX_MIN]);
    const int32_t x1 = min(static_cast<int32_t>(width), packed_rects[row + RECT_COL_PX_MAX]);
    const int32_t y0 = max(0, packed_rects[row + RECT_COL_PY_MIN]);
    const int32_t y1 = min(static_cast<int32_t>(height), packed_rects[row + RECT_COL_PY_MAX]);
    if (x0 >= x1 || y0 >= y1) {
        return;
    }

    const int64_t layer_base = static_cast<int64_t>(layer) * height * width;
    const bool is_real_master = cid <= real_conductor_count;
    const int64_t master_base = is_real_master
        ? (static_cast<int64_t>(cid) - 1) * num_layers * height * width + layer_base
        : 0;
    for (int32_t y = y0; y < y1; ++y) {
        const int64_t occ_row_base = layer_base + static_cast<int64_t>(y) * width;
        const int64_t master_row_base = master_base + static_cast<int64_t>(y) * width;
        for (int32_t x = x0; x < x1; ++x) {
            occupied[occ_row_base + x] = static_cast<uint8_t>(1);
            if (is_real_master) {
                master_masks[master_row_base + x] = static_cast<uint8_t>(1);
            }
        }
    }
}

torch::Tensor rasterize_idmaps_cuda(
    torch::Tensor packed_rects,
    int64_t num_layers,
    int64_t height,
    int64_t width) {
    TORCH_CHECK(packed_rects.is_cuda(), "packed_rects must be CUDA");
    TORCH_CHECK(packed_rects.dim() == 2, "packed_rects must be 2D");
    TORCH_CHECK(packed_rects.size(1) == RECT_COL_COUNT, "packed_rects column mismatch");
    TORCH_CHECK(packed_rects.scalar_type() == torch::kInt32, "packed_rects must be int32");
    TORCH_CHECK(num_layers > 0, "num_layers must be positive");
    TORCH_CHECK(height > 0, "height must be positive");
    TORCH_CHECK(width > 0, "width must be positive");

    auto out = torch::zeros({num_layers, height, width}, packed_rects.options().dtype(torch::kInt16));
    const auto block_count = packed_rects.size(0);
    if (block_count == 0) {
        return out;
    }

    c10::cuda::CUDAGuard guard(packed_rects.device());
    cudaStream_t stream = at::cuda::getCurrentCUDAStream(packed_rects.get_device()).stream();

    const int threads = 128;
    const int blocks = static_cast<int>((block_count + threads - 1) / threads);
    paint_id_kernel<<<blocks, threads, 0, stream>>>(
        packed_rects.data_ptr<int32_t>(),
        out.data_ptr<int16_t>(),
        block_count,
        num_layers,
        height,
        width);
    C10_CUDA_KERNEL_LAUNCH_CHECK();

    return out;
}

std::tuple<torch::Tensor, torch::Tensor> rasterize_binary_masks_cuda(
    torch::Tensor packed_rects,
    int64_t num_layers,
    int64_t height,
    int64_t width,
    int64_t real_conductor_count) {
    TORCH_CHECK(packed_rects.is_cuda(), "packed_rects must be CUDA");
    TORCH_CHECK(packed_rects.dim() == 2, "packed_rects must be 2D");
    TORCH_CHECK(packed_rects.size(1) == RECT_COL_COUNT, "packed_rects column mismatch");
    TORCH_CHECK(packed_rects.scalar_type() == torch::kInt32, "packed_rects must be int32");
    TORCH_CHECK(num_layers > 0, "num_layers must be positive");
    TORCH_CHECK(height > 0, "height must be positive");
    TORCH_CHECK(width > 0, "width must be positive");
    TORCH_CHECK(real_conductor_count >= 0, "real_conductor_count must be non-negative");

    auto occupied = torch::zeros({num_layers, height, width}, packed_rects.options().dtype(torch::kUInt8));
    auto master_masks = torch::zeros(
        {real_conductor_count, num_layers, height, width},
        packed_rects.options().dtype(torch::kUInt8)
    );
    const auto block_count = packed_rects.size(0);
    if (block_count == 0) {
        return std::make_tuple(occupied, master_masks);
    }

    c10::cuda::CUDAGuard guard(packed_rects.device());
    cudaStream_t stream = at::cuda::getCurrentCUDAStream(packed_rects.get_device()).stream();

    const int threads = 128;
    const int blocks = static_cast<int>((block_count + threads - 1) / threads);
    paint_binary_masks_kernel<<<blocks, threads, 0, stream>>>(
        packed_rects.data_ptr<int32_t>(),
        occupied.data_ptr<uint8_t>(),
        master_masks.data_ptr<uint8_t>(),
        block_count,
        num_layers,
        height,
        width,
        real_conductor_count);
    C10_CUDA_KERNEL_LAUNCH_CHECK();

    return std::make_tuple(occupied, master_masks);
}

std::tuple<
    torch::Tensor,
    torch::Tensor,
    torch::Tensor,
    torch::Tensor,
    torch::Tensor,
    torch::Tensor,
    torch::Tensor,
    torch::Tensor> rasterize_idmaps_with_sparse_cuda(
    torch::Tensor packed_rects,
    int64_t num_layers,
    int64_t height,
    int64_t width,
    int64_t real_conductor_count,
    int64_t own_x0,
    int64_t own_x1,
    int64_t own_y0,
    int64_t own_y1) {
    TORCH_CHECK(packed_rects.is_cuda(), "packed_rects must be CUDA");
    TORCH_CHECK(packed_rects.dim() == 2, "packed_rects must be 2D");
    TORCH_CHECK(packed_rects.size(1) == RECT_COL_COUNT, "packed_rects column mismatch");
    TORCH_CHECK(packed_rects.scalar_type() == torch::kInt32, "packed_rects must be int32");
    TORCH_CHECK(num_layers > 0, "num_layers must be positive");
    TORCH_CHECK(height > 0, "height must be positive");
    TORCH_CHECK(width > 0, "width must be positive");
    TORCH_CHECK(real_conductor_count >= 0, "real_conductor_count must be non-negative");

    own_x0 = std::max<int64_t>(0, std::min<int64_t>(own_x0, width));
    own_x1 = std::max<int64_t>(own_x0, std::min<int64_t>(own_x1, width));
    own_y0 = std::max<int64_t>(0, std::min<int64_t>(own_y0, height));
    own_y1 = std::max<int64_t>(own_y0, std::min<int64_t>(own_y1, height));

    auto full_local_map = torch::zeros({num_layers, height, width}, packed_rects.options().dtype(torch::kInt16));
    auto occupied = torch::zeros({num_layers, height, width}, packed_rects.options().dtype(torch::kUInt8));
    auto owned_local_map = torch::zeros_like(full_local_map);
    auto owned_local_counts = torch::zeros({real_conductor_count + 1}, packed_rects.options().dtype(torch::kLong));
    auto visible_flags = torch::zeros({real_conductor_count + 1}, packed_rects.options().dtype(torch::kInt));

    const auto block_count = packed_rects.size(0);
    c10::cuda::CUDAGuard guard(packed_rects.device());
    cudaStream_t stream = at::cuda::getCurrentCUDAStream(packed_rects.get_device()).stream();

    const int threads = 128;
    if (block_count > 0) {
        const int blocks = static_cast<int>((block_count + threads - 1) / threads);
        paint_id_kernel<<<blocks, threads, 0, stream>>>(
            packed_rects.data_ptr<int32_t>(),
            full_local_map.data_ptr<int16_t>(),
            block_count,
            num_layers,
            height,
            width);
        C10_CUDA_KERNEL_LAUNCH_CHECK();
    }

    const int64_t total_pixels = num_layers * height * width;
    if (total_pixels > 0) {
        const int blocks = static_cast<int>((total_pixels + threads - 1) / threads);
        build_owned_sparse_metadata_kernel<<<blocks, threads, 0, stream>>>(
            full_local_map.data_ptr<int16_t>(),
            occupied.data_ptr<uint8_t>(),
            owned_local_map.data_ptr<int16_t>(),
            owned_local_counts.data_ptr<int64_t>(),
            visible_flags.data_ptr<int32_t>(),
            total_pixels,
            height,
            width,
            real_conductor_count,
            own_x0,
            own_x1,
            own_y0,
            own_y1);
        C10_CUDA_KERNEL_LAUNCH_CHECK();
    }

    auto owned_sparse_counts = owned_local_counts.clone();
    owned_sparse_counts.index_put_({0}, 0);
    const int64_t max_sparse_points = real_conductor_count > 0
        ? std::max<int64_t>(
            1,
            owned_local_counts.slice(0, 1, real_conductor_count + 1).max().item<int64_t>()
        )
        : 1;
    auto owned_sparse_indices = torch::zeros(
        {real_conductor_count + 1, max_sparse_points},
        packed_rects.options().dtype(torch::kLong)
    );

    if (total_pixels > 0 && real_conductor_count > 0) {
        auto write_offsets = torch::zeros({real_conductor_count + 1}, packed_rects.options().dtype(torch::kLong));
        const int blocks = static_cast<int>((total_pixels + threads - 1) / threads);
        scatter_owned_sparse_indices_kernel<<<blocks, threads, 0, stream>>>(
            owned_local_map.data_ptr<int16_t>(),
            owned_sparse_indices.data_ptr<int64_t>(),
            write_offsets.data_ptr<int64_t>(),
            total_pixels,
            max_sparse_points);
        C10_CUDA_KERNEL_LAUNCH_CHECK();
    }

    auto owned_query_local_ids = torch::nonzero(owned_local_counts.slice(0, 1, real_conductor_count + 1) > 0)
        .reshape({-1})
        .to(torch::kLong)
        + 1;
    auto visible_master_local_ids = torch::nonzero(visible_flags.slice(0, 1, real_conductor_count + 1) > 0)
        .reshape({-1})
        .to(torch::kLong)
        + 1;

    return std::make_tuple(
        occupied,
        full_local_map,
        owned_local_map,
        owned_local_counts,
        owned_sparse_indices,
        owned_sparse_counts,
        owned_query_local_ids.contiguous(),
        visible_master_local_ids.contiguous()
    );
}
