#pragma once

#include <string>
#include <vector>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "lefdef_fast_parser_bindings_shared.h"

PreparedCompactResult prepare_def_raster_compiled(
    const std::string& def_path,
    const std::string& tech_key,
    const std::vector<std::string>& channel_layers,
    const pybind11::dict& layer_widths_um,
    int target_size,
    pybind11::object pixel_resolution_obj,
    pybind11::object raster_bounds_obj,
    bool include_supply_nets,
    bool include_conductor_names
);
