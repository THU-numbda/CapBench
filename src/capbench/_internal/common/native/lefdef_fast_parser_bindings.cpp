#include <algorithm>
#include <cctype>
#include <cstdint>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <string>
#include <vector>

#include <torch/extension.h>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "lefdef_fast_parser_bindings_shared.h"
#include "lefdef_fast_parser_compiled.h"

namespace py = pybind11;

namespace {

constexpr int RECT_COL_LAYER = 0;
constexpr int RECT_COL_CONDUCTOR_ID = 1;
constexpr int RECT_COL_PX_MIN = 2;
constexpr int RECT_COL_PX_MAX = 3;
constexpr int RECT_COL_PY_MIN = 4;
constexpr int RECT_COL_PY_MAX = 5;
constexpr int RECT_COL_COUNT = 6;

std::string uppercase_copy(const std::string& value) {
    std::string out = value;
    std::transform(out.begin(), out.end(), out.begin(), [](unsigned char ch) {
        return static_cast<char>(std::toupper(ch));
    });
    return out;
}

py::dict prepared_compact_result_to_py(const PreparedCompactResult& prepared, bool include_conductor_names) {
    auto packed_rects = torch::empty(
        {
            static_cast<long long>(prepared.rect_entries.size()),
            static_cast<long long>(RECT_COL_COUNT),
        },
        torch::TensorOptions().dtype(torch::kInt32).device(torch::kCPU)
    );
    auto packed = packed_rects.accessor<std::int32_t, 2>();
    for (long long row = 0; row < packed_rects.size(0); ++row) {
        const RectEntry& entry = prepared.rect_entries[static_cast<std::size_t>(row)];
        packed[row][RECT_COL_LAYER] = entry.channel;
        packed[row][RECT_COL_CONDUCTOR_ID] = entry.conductor_id;
        packed[row][RECT_COL_PX_MIN] = entry.px_min;
        packed[row][RECT_COL_PX_MAX] = entry.px_max;
        packed[row][RECT_COL_PY_MIN] = entry.py_min;
        packed[row][RECT_COL_PY_MAX] = entry.py_max;
    }

    py::array_t<std::uint8_t> rect_source_kind_codes(static_cast<py::ssize_t>(prepared.rect_source_kind_codes.size()));
    auto codes = rect_source_kind_codes.mutable_unchecked<1>();
    for (py::ssize_t idx = 0; idx < codes.shape(0); ++idx) {
        codes(idx) = prepared.rect_source_kind_codes[static_cast<std::size_t>(idx)];
    }

    py::dict stats;
    stats["explicit_pin"] = py::int_(prepared.component_stats[0]);
    stats["supply_fallback"] = py::int_(prepared.component_stats[1]);
    stats["routed_touch"] = py::int_(prepared.component_stats[2]);
    stats["pin_and_geom"] = py::int_(prepared.component_stats[3]);
    stats["ambiguous"] = py::int_(prepared.component_stats[4]);
    stats["no_net"] = py::int_(prepared.component_stats[5]);

    py::dict out;
    out["packed_rects"] = packed_rects;
    if (include_conductor_names) {
        out["conductor_names_sorted"] = py::cast(prepared.conductor_names_sorted);
    }
    out["real_conductor_count"] = py::int_(prepared.real_conductor_count);
    out["conductor_count"] = py::int_(prepared.conductor_count);
    out["rect_source_kind_codes"] = rect_source_kind_codes;
    out["total_segments"] = py::int_(prepared.total_segments);
    out["total_endpoint_extensions"] = py::int_(prepared.total_endpoint_extensions);
    out["active_rectangles"] = py::int_(prepared.active_rectangles);
    out["component_resolution_stats"] = stats;
    out["parse_ms"] = py::float_(prepared.parse_ms);
    out["prepare_ms"] = py::float_(prepared.prepare_ms);
    out["window_bounds"] = py::make_tuple(
        prepared.window_bounds[0],
        prepared.window_bounds[1],
        prepared.window_bounds[2],
        prepared.window_bounds[3],
        prepared.window_bounds[4],
        prepared.window_bounds[5]
    );
    out["pixel_resolution"] = py::float_(prepared.pixel_resolution);
    return out;
}

py::dict prepared_compact_runtime_result_to_py(const PreparedCompactResult& prepared) {
    auto packed_rects = torch::empty(
        {
            static_cast<long long>(prepared.rect_entries.size()),
            static_cast<long long>(RECT_COL_COUNT),
        },
        torch::TensorOptions().dtype(torch::kInt32).device(torch::kCPU)
    );
    auto packed = packed_rects.accessor<std::int32_t, 2>();
    for (long long row = 0; row < packed_rects.size(0); ++row) {
        const RectEntry& entry = prepared.rect_entries[static_cast<std::size_t>(row)];
        packed[row][RECT_COL_LAYER] = entry.channel;
        packed[row][RECT_COL_CONDUCTOR_ID] = entry.conductor_id;
        packed[row][RECT_COL_PX_MIN] = entry.px_min;
        packed[row][RECT_COL_PX_MAX] = entry.px_max;
        packed[row][RECT_COL_PY_MIN] = entry.py_min;
        packed[row][RECT_COL_PY_MAX] = entry.py_max;
    }

    auto conductor_ids = torch::empty(
        {static_cast<long long>(prepared.real_conductor_count)},
        torch::TensorOptions().dtype(torch::kInt16).device(torch::kCPU)
    );
    auto conductor_ids_acc = conductor_ids.accessor<std::int16_t, 1>();
    for (long long idx = 0; idx < conductor_ids.size(0); ++idx) {
        conductor_ids_acc[idx] = static_cast<std::int16_t>(idx + 1);
    }

    py::dict out;
    out["packed_rects"] = packed_rects;
    out["conductor_ids"] = conductor_ids;
    out["active_rectangles"] = py::int_(prepared.active_rectangles);
    out["parse_ms"] = py::float_(prepared.parse_ms);
    out["prepare_ms"] = py::float_(prepared.prepare_ms);
    out["pixel_resolution"] = py::float_(prepared.pixel_resolution);
    return out;
}

py::dict prepare_def_raster_compiled_runtime_py(
    const std::string& def_path,
    const std::string& tech_key,
    const std::vector<std::string>& channel_layers,
    const py::dict& layer_widths_um,
    int target_size,
    py::object pixel_resolution_obj,
    py::object raster_bounds_obj,
    bool include_supply_nets
) {
    return prepared_compact_runtime_result_to_py(
        prepare_def_raster_compiled(
            def_path,
            tech_key,
            channel_layers,
            layer_widths_um,
            target_size,
            std::move(pixel_resolution_obj),
            std::move(raster_bounds_obj),
            include_supply_nets,
            false
        )
    );
}

py::dict prepare_def_raster_compiled_py(
    const std::string& def_path,
    const std::string& tech_key,
    const std::vector<std::string>& channel_layers,
    const py::dict& layer_widths_um,
    int target_size,
    py::object pixel_resolution_obj,
    py::object raster_bounds_obj,
    bool include_supply_nets,
    bool include_conductor_names
) {
    return prepared_compact_result_to_py(
        prepare_def_raster_compiled(
            def_path,
            tech_key,
            channel_layers,
            layer_widths_um,
            target_size,
            pixel_resolution_obj,
            raster_bounds_obj,
            include_supply_nets,
            include_conductor_names
        ),
        include_conductor_names
    );
}

double simple_spef_unit_to_farads(const std::string& unit) {
    const std::string upper = uppercase_copy(unit);
    if (upper == "F" || upper == "FARAD") {
        return 1.0;
    }
    if (upper == "PF") {
        return 1e-12;
    }
    if (upper == "NF") {
        return 1e-9;
    }
    if (upper == "UF") {
        return 1e-6;
    }
    if (upper == "MF") {
        return 1e-3;
    }
    if (upper == "KF") {
        return 1e3;
    }
    if (upper == "FF") {
        return 1e-15;
    }
    return 1.0;
}

std::string current_spef_timestamp() {
    std::time_t now = std::time(nullptr);
    std::tm local_tm{};
#if defined(_WIN32)
    localtime_s(&local_tm, &now);
#else
    localtime_r(&now, &local_tm);
#endif
    char buffer[128];
    if (std::strftime(buffer, sizeof(buffer), "%H:%M:%S %A %B %d, %Y", &local_tm) == 0) {
        return "";
    }
    return std::string(buffer);
}

void write_simple_spef_file_impl(
    const std::string& out_path,
    const std::string& design,
    const std::vector<std::string>& nets,
    const std::vector<double>& total_cap_f,
    const std::vector<std::int64_t>& coupling_left_indices,
    const std::vector<std::int64_t>& coupling_right_indices,
    const std::vector<double>& coupling_values_f,
    const std::string& c_unit,
    bool include_conn
) {
    if (nets.size() != total_cap_f.size()) {
        throw std::runtime_error(
            "nets and total_cap_f must have the same length, got "
            + std::to_string(nets.size()) + " vs " + std::to_string(total_cap_f.size())
        );
    }
    if (coupling_left_indices.size() != coupling_right_indices.size()
        || coupling_left_indices.size() != coupling_values_f.size()) {
        throw std::runtime_error("Coupling index and value arrays must have the same length.");
    }

    const double target_factor = simple_spef_unit_to_farads(c_unit);
    std::vector<std::vector<std::pair<std::int64_t, double>>> adjacency(nets.size());

    for (std::size_t idx = 0; idx < coupling_values_f.size(); ++idx) {
        const std::int64_t left = coupling_left_indices[idx];
        const std::int64_t right = coupling_right_indices[idx];
        if (left < 0 || right < 0
            || left >= static_cast<std::int64_t>(nets.size())
            || right >= static_cast<std::int64_t>(nets.size())) {
            throw std::runtime_error("Coupling indices are out of bounds for the provided net list.");
        }
        if (left == right) {
            continue;
        }
        const double value = coupling_values_f[idx];
        const std::int64_t low = std::min(left, right);
        const std::int64_t high = std::max(left, right);
        adjacency[static_cast<std::size_t>(low)].push_back({high, value});
    }

    std::ofstream out(out_path, std::ios::out | std::ios::trunc);
    if (!out.is_open()) {
        throw std::runtime_error("Failed to open SPEF output for writing: " + out_path);
    }
    out << std::setprecision(12);

    out << "*SPEF \"ieee 1481-1999\"\n";
    out << "*DESIGN \"" << design << "\"\n";
    out << "*DATE \"" << current_spef_timestamp() << "\"\n";
    out << "*VENDOR \"simple-spef\"\n";
    out << "*PROGRAM \"spef_to_simple\"\n";
    out << "*VERSION \"0.3\"\n";
    out << "*COMMENT \"D_NET totals are direct model predictions; ground CAP entries omitted.\"\n";
    out << "*DESIGN_FLOW \"NAME_SCOPE LOCAL\" \"PIN_CAP NONE\"\n";
    out << "*DIVIDER /\n";
    out << "*DELIMITER :\n";
    out << "*BUS_DELIMITER []\n";
    out << "*T_UNIT 1 NS\n";
    out << "*C_UNIT 1 " << uppercase_copy(c_unit) << "\n";
    out << "*R_UNIT 1 OHM\n";
    out << "*L_UNIT 1 HENRY\n\n";

    out << "*NAME_MAP\n";
    for (std::size_t idx = 0; idx < nets.size(); ++idx) {
        out << "*" << (idx + 1) << " " << nets[idx] << "\n";
    }
    out << "\n";

    for (std::size_t idx = 0; idx < nets.size(); ++idx) {
        const double total_out = target_factor != 0.0 ? total_cap_f[idx] / target_factor : total_cap_f[idx];
        out << "*D_NET *" << (idx + 1) << " " << total_out << "\n";
        out << "*CONN\n";
        if (include_conn) {
            out << "*P " << nets[idx] << " B\n";
        }
        out << "*CAP\n";
        int cap_index = 1;
        for (const auto& edge : adjacency[idx]) {
            const double coupling_out = target_factor != 0.0 ? edge.second / target_factor : edge.second;
            out << cap_index << " " << nets[idx] << " " << nets[static_cast<std::size_t>(edge.first)] << " " << coupling_out << "\n";
            ++cap_index;
        }
        out << "*RES\n";
        out << "*END\n\n";
    }
}

void write_simple_spef_file_py(
    const std::string& out_path,
    const std::string& design,
    const std::vector<std::string>& nets,
    const std::vector<double>& total_cap_f,
    const std::vector<std::int64_t>& coupling_left_indices,
    const std::vector<std::int64_t>& coupling_right_indices,
    const std::vector<double>& coupling_values_f,
    const std::string& c_unit,
    bool include_conn
) {
    write_simple_spef_file_impl(
        out_path,
        design,
        nets,
        total_cap_f,
        coupling_left_indices,
        coupling_right_indices,
        coupling_values_f,
        c_unit,
        include_conn
    );
}

}  // namespace

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def(
        "prepare_def_raster_compiled",
        &prepare_def_raster_compiled_py,
        py::arg("def_path"),
        py::arg("tech_key"),
        py::arg("channel_layers"),
        py::arg("layer_widths_um"),
        py::arg("target_size"),
        py::arg("pixel_resolution") = py::none(),
        py::arg("raster_bounds") = py::none(),
        py::arg("include_supply_nets") = true,
        py::arg("include_conductor_names") = false,
        "Prepare compiled LEF+DEF raster inputs using static cell recipes"
    );
    m.def(
        "prepare_def_raster_compiled_runtime",
        &prepare_def_raster_compiled_runtime_py,
        py::arg("def_path"),
        py::arg("tech_key"),
        py::arg("channel_layers"),
        py::arg("layer_widths_um"),
        py::arg("target_size"),
        py::arg("pixel_resolution") = py::none(),
        py::arg("raster_bounds") = py::none(),
        py::arg("include_supply_nets") = true,
        "Prepare runtime LEF+DEF tensors using compiled cell recipes"
    );
    m.def(
        "write_simple_spef_file",
        &write_simple_spef_file_py,
        py::arg("out_path"),
        py::arg("design"),
        py::arg("nets"),
        py::arg("total_cap_f"),
        py::arg("coupling_left_indices"),
        py::arg("coupling_right_indices"),
        py::arg("coupling_values_f"),
        py::arg("c_unit") = "PF",
        py::arg("include_conn") = true,
        "Write a simplified SPEF file from total and coupling capacitance values"
    );
}
