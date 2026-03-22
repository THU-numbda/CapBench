#include <stdexcept>
#include <tuple>
#include <torch/extension.h>

torch::Tensor rasterize_idmaps_cuda(
    torch::Tensor packed_rects,
    int64_t num_layers,
    int64_t height,
    int64_t width);

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
    int64_t own_y1);

torch::Tensor rasterize_idmaps(
    torch::Tensor packed_rects,
    int64_t num_layers,
    int64_t height,
    int64_t width) {
    if (!packed_rects.is_cuda()) {
        throw std::runtime_error("rasterize_idmaps expects CUDA tensors");
    }
    return rasterize_idmaps_cuda(packed_rects, num_layers, height, width);
}

std::tuple<
    torch::Tensor,
    torch::Tensor,
    torch::Tensor,
    torch::Tensor,
    torch::Tensor,
    torch::Tensor,
    torch::Tensor,
    torch::Tensor> rasterize_idmaps_with_sparse(
    torch::Tensor packed_rects,
    int64_t num_layers,
    int64_t height,
    int64_t width,
    int64_t real_conductor_count,
    int64_t own_x0,
    int64_t own_x1,
    int64_t own_y0,
    int64_t own_y1) {
    if (!packed_rects.is_cuda()) {
        throw std::runtime_error("rasterize_idmaps_with_sparse expects CUDA tensors");
    }
    return rasterize_idmaps_with_sparse_cuda(
        packed_rects,
        num_layers,
        height,
        width,
        real_conductor_count,
        own_x0,
        own_x1,
        own_y0,
        own_y1
    );
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("rasterize_idmaps", &rasterize_idmaps, "Expand compact CAP3D tiles to dense ID maps (CUDA)");
    m.def(
        "rasterize_idmaps_with_sparse",
        &rasterize_idmaps_with_sparse,
        "Rasterize packed rects and build owned sparse aggregation metadata (CUDA)"
    );
}
