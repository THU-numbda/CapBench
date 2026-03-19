#include <torch/extension.h>
#include <pybind11/pybind11.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cctype>
#include <cstring>
#include <cstdlib>
#include <fstream>
#include <string>
#include <unordered_map>
#include <vector>

namespace py = pybind11;

struct BlockRec {
    int32_t layer_idx;
    int32_t conductor_idx;
    float x_min;
    float x_max;
    float y_min;
    float y_max;
};

static inline std::string trim_copy(const std::string& s) {
    size_t start = 0;
    while (start < s.size() && std::isspace(static_cast<unsigned char>(s[start]))) {
        ++start;
    }
    size_t end = s.size();
    while (end > start && std::isspace(static_cast<unsigned char>(s[end - 1]))) {
        --end;
    }
    return s.substr(start, end - start);
}

static inline bool starts_with(const std::string& s, const char* prefix) {
    const size_t n = std::strlen(prefix);
    if (s.size() < n) {
        return false;
    }
    return std::memcmp(s.data(), prefix, n) == 0;
}

static inline std::string after_prefix(const std::string& s, const char* prefix) {
    const size_t n = std::strlen(prefix);
    if (s.size() < n) {
        return std::string();
    }
    return trim_copy(s.substr(n));
}

static inline bool parse_triplet(const std::string& line, float out[3]) {
    const size_t open = line.find('(');
    if (open == std::string::npos) {
        return false;
    }
    const size_t close = line.find(')', open + 1);
    if (close == std::string::npos || close <= open + 1) {
        return false;
    }
    const std::string payload = line.substr(open + 1, close - open - 1);
    const char* cur = payload.c_str();
    char* end = nullptr;
    for (int i = 0; i < 3; ++i) {
        while (*cur == ',' || std::isspace(static_cast<unsigned char>(*cur))) {
            ++cur;
        }
        const float value = std::strtof(cur, &end);
        if (end == cur) {
            return false;
        }
        out[i] = value;
        cur = end;
    }
    return true;
}

static inline bool parse_int_like_value(const std::string& line, const char* prefix, int32_t* out) {
    if (!starts_with(line, prefix)) {
        return false;
    }
    const std::string raw = after_prefix(line, prefix);
    if (raw.empty()) {
        return false;
    }
    char* end = nullptr;
    const double value = std::strtod(raw.c_str(), &end);
    if (end == raw.c_str()) {
        return false;
    }
    *out = static_cast<int32_t>(value);
    return true;
}

static inline int32_t get_or_add_conductor(
    const std::string& name,
    std::unordered_map<std::string, int32_t>* conductor_to_idx,
    std::vector<std::string>* conductor_names
) {
    auto it = conductor_to_idx->find(name);
    if (it != conductor_to_idx->end()) {
        return it->second;
    }
    const int32_t idx = static_cast<int32_t>(conductor_names->size());
    conductor_names->push_back(name);
    conductor_to_idx->emplace(name, idx);
    return idx;
}

py::dict parse_cap3d_compact(const std::string& file_path) {
    auto t0 = std::chrono::high_resolution_clock::now();

    std::ifstream in(file_path);
    if (!in.good()) {
        throw std::runtime_error("Failed to open CAP3D file: " + file_path);
    }

    bool in_window = false;
    bool in_conductor = false;
    bool in_block = false;
    bool in_layer_decl = false;
    bool has_window = false;

    std::string current_conductor_name;
    std::string current_layer_name;
    std::string current_layer_type;
    int32_t current_block_layer = -1;
    float current_base[3] = {0.0f, 0.0f, 0.0f};
    float current_v1[3] = {0.0f, 0.0f, 0.0f};
    float current_v2[3] = {0.0f, 0.0f, 0.0f};
    bool have_base = false;
    bool have_v1 = false;
    bool have_v2 = false;

    float window_v1[3] = {0.0f, 0.0f, 0.0f};
    float window_v2[3] = {0.0f, 0.0f, 0.0f};

    std::vector<std::string> conductor_names;
    conductor_names.reserve(1024);
    std::unordered_map<std::string, int32_t> conductor_to_idx;
    conductor_to_idx.reserve(1024);

    std::vector<std::string> layer_names;
    std::vector<std::string> layer_types;
    layer_names.reserve(64);
    layer_types.reserve(64);

    std::vector<BlockRec> blocks;
    blocks.reserve(16384);

    std::string line;
    while (std::getline(in, line)) {
        line = trim_copy(line);
        if (line.empty() || starts_with(line, "<!--")) {
            continue;
        }

        if (line == "<window>") {
            in_window = true;
            continue;
        }
        if (line == "</window>") {
            in_window = false;
            continue;
        }
        if (in_window) {
            if (starts_with(line, "v1(")) {
                if (parse_triplet(line, window_v1)) {
                    has_window = true;
                }
            } else if (starts_with(line, "v2(")) {
                if (parse_triplet(line, window_v2)) {
                    has_window = true;
                }
            }
            continue;
        }

        if (line == "<layer>") {
            in_layer_decl = true;
            current_layer_name.clear();
            current_layer_type.clear();
            continue;
        }
        if (line == "</layer>") {
            if (in_layer_decl) {
                layer_names.push_back(current_layer_name);
                layer_types.push_back(current_layer_type);
            }
            in_layer_decl = false;
            continue;
        }
        if (in_layer_decl) {
            if (starts_with(line, "name ")) {
                current_layer_name = after_prefix(line, "name ");
            } else if (starts_with(line, "type ")) {
                current_layer_type = after_prefix(line, "type ");
            }
            continue;
        }

        if (line == "<conductor>") {
            in_conductor = true;
            current_conductor_name.clear();
            continue;
        }
        if (line == "</conductor>") {
            in_conductor = false;
            current_conductor_name.clear();
            continue;
        }
        if (!in_conductor) {
            continue;
        }

        if (line == "<block>") {
            in_block = true;
            current_block_layer = -1;
            have_base = false;
            have_v1 = false;
            have_v2 = false;
            continue;
        }
        if (line == "</block>") {
            if (in_block && have_base && have_v1 && have_v2 && current_block_layer >= 0) {
                const float x0 = current_base[0];
                const float x1 = current_base[0] + current_v1[0];
                const float x2 = current_base[0] + current_v2[0];
                const float x3 = current_base[0] + current_v1[0] + current_v2[0];
                const float y0 = current_base[1];
                const float y1 = current_base[1] + current_v1[1];
                const float y2 = current_base[1] + current_v2[1];
                const float y3 = current_base[1] + current_v1[1] + current_v2[1];

                int32_t conductor_idx = -1;
                if (!current_conductor_name.empty()) {
                    conductor_idx = get_or_add_conductor(
                        current_conductor_name,
                        &conductor_to_idx,
                        &conductor_names
                    );
                }

                BlockRec rec;
                rec.layer_idx = current_block_layer;
                rec.conductor_idx = conductor_idx;
                rec.x_min = std::min(std::min(x0, x1), std::min(x2, x3));
                rec.x_max = std::max(std::max(x0, x1), std::max(x2, x3));
                rec.y_min = std::min(std::min(y0, y1), std::min(y2, y3));
                rec.y_max = std::max(std::max(y0, y1), std::max(y2, y3));
                blocks.push_back(rec);
            }
            in_block = false;
            continue;
        }

        if (!in_block) {
            if (starts_with(line, "name ")) {
                current_conductor_name = after_prefix(line, "name ");
            }
            continue;
        }

        if (starts_with(line, "layer ")) {
            parse_int_like_value(line, "layer ", &current_block_layer);
            continue;
        }
        if (starts_with(line, "basepoint(")) {
            have_base = parse_triplet(line, current_base);
            continue;
        }
        if (starts_with(line, "v1(")) {
            have_v1 = parse_triplet(line, current_v1);
            continue;
        }
        if (starts_with(line, "v2(")) {
            have_v2 = parse_triplet(line, current_v2);
            continue;
        }
    }

    const auto block_count = static_cast<int64_t>(blocks.size());
    auto i32_opts = torch::TensorOptions().dtype(torch::kInt32).device(torch::kCPU);
    auto f32_opts = torch::TensorOptions().dtype(torch::kFloat32).device(torch::kCPU);

    auto block_layer_idx = torch::empty({block_count}, i32_opts);
    auto block_conductor_idx = torch::empty({block_count}, i32_opts);
    auto block_x_min = torch::empty({block_count}, f32_opts);
    auto block_x_max = torch::empty({block_count}, f32_opts);
    auto block_y_min = torch::empty({block_count}, f32_opts);
    auto block_y_max = torch::empty({block_count}, f32_opts);

    int32_t* layer_ptr = block_layer_idx.data_ptr<int32_t>();
    int32_t* cond_ptr = block_conductor_idx.data_ptr<int32_t>();
    float* x_min_ptr = block_x_min.data_ptr<float>();
    float* x_max_ptr = block_x_max.data_ptr<float>();
    float* y_min_ptr = block_y_min.data_ptr<float>();
    float* y_max_ptr = block_y_max.data_ptr<float>();

    for (int64_t i = 0; i < block_count; ++i) {
        const BlockRec& b = blocks[static_cast<size_t>(i)];
        layer_ptr[i] = b.layer_idx;
        cond_ptr[i] = b.conductor_idx;
        x_min_ptr[i] = b.x_min;
        x_max_ptr[i] = b.x_max;
        y_min_ptr[i] = b.y_min;
        y_max_ptr[i] = b.y_max;
    }

    auto window_v1_tensor = torch::zeros({3}, f32_opts);
    auto window_v2_tensor = torch::zeros({3}, f32_opts);
    float* w1_ptr = window_v1_tensor.data_ptr<float>();
    float* w2_ptr = window_v2_tensor.data_ptr<float>();
    for (int i = 0; i < 3; ++i) {
        w1_ptr[i] = window_v1[i];
        w2_ptr[i] = window_v2[i];
    }

    py::list conductor_name_list;
    for (const auto& name : conductor_names) {
        conductor_name_list.append(name);
    }
    py::list layer_name_list;
    for (const auto& name : layer_names) {
        layer_name_list.append(name);
    }
    py::list layer_type_list;
    for (const auto& type_name : layer_types) {
        layer_type_list.append(type_name);
    }

    auto t1 = std::chrono::high_resolution_clock::now();
    const double parse_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

    py::dict out;
    out["block_layer_idx"] = block_layer_idx;
    out["block_conductor_idx"] = block_conductor_idx;
    out["block_x_min"] = block_x_min;
    out["block_x_max"] = block_x_max;
    out["block_y_min"] = block_y_min;
    out["block_y_max"] = block_y_max;
    out["conductor_names"] = conductor_name_list;
    out["layer_names"] = layer_name_list;
    out["layer_types"] = layer_type_list;
    out["has_window"] = py::bool_(has_window);
    out["window_v1"] = window_v1_tensor;
    out["window_v2"] = window_v2_tensor;
    out["parse_ms"] = py::float_(parse_ms);
    return out;
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("parse_cap3d_compact", &parse_cap3d_compact, "Parse CAP3D into compact block metadata (CPU)");
}
