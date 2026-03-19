#include "lefdef_fast_parser_compiled.h"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cctype>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "lefdef_compiled_cell_recipes.h"
#include "lefdef_compiled_cell_recipes_sky130hd.h"
#include "lefdef_fast_parser.h"

namespace py = pybind11;

namespace {

constexpr double kEps = 1e-9;

enum class CompiledBindingKind : std::uint8_t {
    kPinNet = 0,
    kSupplyNet = 1,
    kSyntheticNet = 2,
};

enum class CompiledSupplySlot : std::uint8_t {
    kPower = 0,
    kGround = 1,
    kCount = 2,
};

struct CompiledTechSpec {
    std::string tech_key;
    std::vector<std::string> normalized_layer_names;
    const capbench_compiled_recipes::MacroSpec* macro_specs = nullptr;
    std::size_t macro_count = 0;
};

struct CompiledLocalRect {
    std::uint8_t layer_slot = 0;
    RectD local_rect{};
    bool is_obs = false;
};

struct CompiledGroupTemplate {
    CompiledBindingKind binding_kind = CompiledBindingKind::kPinNet;
    int binding_slot = -1;
    int synthetic_group_index = -1;
    std::vector<CompiledLocalRect> rects;
};

struct CompiledBaseGroup {
    CompiledBindingKind binding_kind = CompiledBindingKind::kPinNet;
    int binding_slot = -1;
    int synthetic_group_index = -1;
    std::vector<CompiledLocalRect> rects;
};

struct CompiledBaseMacroRecipe {
    std::string macro_name;
    double size_x = 0.0;
    double size_y = 0.0;
    std::vector<std::string> signal_pin_names;
    std::vector<CompiledBaseGroup> groups;
};

using CompiledOrientedTemplates = std::array<std::vector<CompiledGroupTemplate>, 4>;

struct CompiledRecipeCacheEntry {
    CompiledBaseMacroRecipe recipe;
    CompiledOrientedTemplates templates;
};

struct CompiledComponentBindingState {
    const CompiledRecipeCacheEntry* entry = nullptr;
    std::vector<std::string> signal_nets;
};

struct DefResultGuard {
    ~DefResultGuard() {
        if (loaded) {
            lfd_free_def_parse_result(&result);
        }
    }
    LfdDefParseResult result{};
    bool loaded = false;
};

bool approx_equal(double a, double b) {
    return std::fabs(a - b) <= kEps;
}

std::string trim_copy(const std::string& value) {
    std::size_t start = 0;
    while (start < value.size() && std::isspace(static_cast<unsigned char>(value[start])) != 0) {
        ++start;
    }
    std::size_t end = value.size();
    while (end > start && std::isspace(static_cast<unsigned char>(value[end - 1])) != 0) {
        --end;
    }
    return value.substr(start, end - start);
}

std::string normalize_net_name(const char* value) {
    return trim_copy(value != nullptr ? value : "");
}

std::string normalize_net_name(const std::string& value) {
    return trim_copy(value);
}

std::string normalize_layer_name(const char* value) {
    std::string out;
    const char* cur = value != nullptr ? value : "";
    while (*cur != '\0') {
        const unsigned char ch = static_cast<unsigned char>(*cur++);
        if (std::isalnum(ch) != 0) {
            out.push_back(static_cast<char>(std::tolower(ch)));
        }
    }
    return out;
}

std::string normalize_layer_name(const std::string& value) {
    return normalize_layer_name(value.c_str());
}

std::string uppercase_copy(const std::string& value) {
    std::string out = value;
    for (char& ch : out) {
        ch = static_cast<char>(std::toupper(static_cast<unsigned char>(ch)));
    }
    return out;
}

bool include_net(const LfdNet& net, bool include_supply_nets) {
    const std::string net_name = normalize_net_name(net.name);
    if (net_name.empty()) {
        return false;
    }
    if (include_supply_nets) {
        return true;
    }
    return uppercase_copy(net_name) != "GROUND";
}

std::string classify_supply_net(const std::string& net_name) {
    const std::string upper = uppercase_copy(net_name);
    if (upper == "VDD" || upper == "VDDPE" || upper == "VPWR" || upper == "POWER") {
        return "POWER";
    }
    if (upper == "VSS" || upper == "VSSPE" || upper == "VGND" || upper == "GND" || upper == "GROUND") {
        return "GROUND";
    }
    return "";
}

std::pair<double, double> apply_orientation(double x, double y, const std::string& orient_raw) {
    std::string orient = uppercase_copy(orient_raw);
    if (orient == "R0") {
        orient = "N";
    } else if (orient == "R90") {
        orient = "E";
    } else if (orient == "R180") {
        orient = "S";
    } else if (orient == "R270") {
        orient = "W";
    } else if (orient == "MX") {
        orient = "FS";
    } else if (orient == "MY") {
        orient = "FN";
    } else if (orient == "MYR90") {
        orient = "FE";
    } else if (orient == "MXR90") {
        orient = "FW";
    }
    if (!orient.empty() && orient[0] == 'F') {
        x = -x;
        orient = orient.substr(1);
    }
    if (orient == "N") {
        return {x, y};
    }
    if (orient == "S") {
        return {-x, -y};
    }
    if (orient == "E") {
        return {y, -x};
    }
    if (orient == "W") {
        return {-y, x};
    }
    throw std::runtime_error("Unsupported DEF orientation: " + orient_raw);
}

std::string canonical_orient(const std::string& orient_raw) {
    std::string orient = uppercase_copy(orient_raw);
    if (orient == "R0") return "N";
    if (orient == "R90") return "E";
    if (orient == "R180") return "S";
    if (orient == "R270") return "W";
    if (orient == "MX") return "FS";
    if (orient == "MY") return "FN";
    if (orient == "MYR90") return "FE";
    if (orient == "MXR90") return "FW";
    return orient;
}

RectD transform_local_rect(
    double rect_x0,
    double rect_y0,
    double rect_x1,
    double rect_y1,
    double macro_size_x,
    double macro_size_y,
    const std::string& orient
) {
    const auto c0 = apply_orientation(0.0, 0.0, orient);
    const auto c1 = apply_orientation(macro_size_x, 0.0, orient);
    const auto c2 = apply_orientation(0.0, macro_size_y, orient);
    const auto c3 = apply_orientation(macro_size_x, macro_size_y, orient);
    const double bbox_min_x = std::min(std::min(c0.first, c1.first), std::min(c2.first, c3.first));
    const double bbox_min_y = std::min(std::min(c0.second, c1.second), std::min(c2.second, c3.second));

    const auto r0 = apply_orientation(rect_x0, rect_y0, orient);
    const auto r1 = apply_orientation(rect_x1, rect_y0, orient);
    const auto r2 = apply_orientation(rect_x0, rect_y1, orient);
    const auto r3 = apply_orientation(rect_x1, rect_y1, orient);

    const double xs[4] = {
        r0.first - bbox_min_x,
        r1.first - bbox_min_x,
        r2.first - bbox_min_x,
        r3.first - bbox_min_x,
    };
    const double ys[4] = {
        r0.second - bbox_min_y,
        r1.second - bbox_min_y,
        r2.second - bbox_min_y,
        r3.second - bbox_min_y,
    };

    return {
        std::min(std::min(xs[0], xs[1]), std::min(xs[2], xs[3])),
        std::max(std::max(xs[0], xs[1]), std::max(xs[2], xs[3])),
        std::min(std::min(ys[0], ys[1]), std::min(ys[2], ys[3])),
        std::max(std::max(ys[0], ys[1]), std::max(ys[2], ys[3])),
    };
}

bool clip_rect(const RectD& rect, const std::array<double, 4>& bounds, RectD* out) {
    RectD clipped = rect;
    clipped.x0 = std::max(clipped.x0, bounds[0]);
    clipped.x1 = std::min(clipped.x1, bounds[2]);
    clipped.y0 = std::max(clipped.y0, bounds[1]);
    clipped.y1 = std::min(clipped.y1, bounds[3]);
    if (clipped.x0 >= clipped.x1 || clipped.y0 >= clipped.y1) {
        return false;
    }
    *out = clipped;
    return true;
}

bool world_rect_to_pixels(
    const RectD& rect,
    double x_min,
    double y_min,
    double pixel_resolution,
    int target_size,
    int* px_min,
    int* px_max,
    int* py_min,
    int* py_max
) {
    *px_min = static_cast<int>(std::floor((rect.x0 - x_min) / pixel_resolution));
    *px_max = static_cast<int>(std::ceil((rect.x1 - x_min) / pixel_resolution));
    *py_min = static_cast<int>(std::floor((rect.y0 - y_min) / pixel_resolution));
    *py_max = static_cast<int>(std::ceil((rect.y1 - y_min) / pixel_resolution));
    *px_min = std::max(0, std::min(target_size, *px_min));
    *px_max = std::max(0, std::min(target_size, *px_max));
    *py_min = std::max(0, std::min(target_size, *py_min));
    *py_max = std::max(0, std::min(target_size, *py_max));
    return *px_min < *px_max && *py_min < *py_max;
}

void append_rect_entry(
    std::vector<RectEntry>* rect_entries,
    int conductor_id,
    int channel,
    const RectD& rect,
    double x_min,
    double y_min,
    double pixel_resolution,
    int target_size,
    std::uint8_t source_kind
) {
    int px_min = 0;
    int px_max = 0;
    int py_min = 0;
    int py_max = 0;
    if (!world_rect_to_pixels(rect, x_min, y_min, pixel_resolution, target_size, &px_min, &px_max, &py_min, &py_max)) {
        return;
    }
    rect_entries->push_back({conductor_id, channel, px_min, px_max, py_min, py_max, source_kind});
}

void append_named_rect_entry(
    std::vector<NamedRectEntry>* rect_entries,
    const std::string& conductor_name,
    int channel,
    const RectD& rect,
    double x_min,
    double y_min,
    double pixel_resolution,
    int target_size,
    std::uint8_t source_kind
) {
    int px_min = 0;
    int px_max = 0;
    int py_min = 0;
    int py_max = 0;
    if (!world_rect_to_pixels(rect, x_min, y_min, pixel_resolution, target_size, &px_min, &px_max, &py_min, &py_max)) {
        return;
    }
    rect_entries->push_back({conductor_name, channel, px_min, px_max, py_min, py_max, source_kind});
}

int compiled_supply_slot_for_name(const std::string& name) {
    const std::string upper = uppercase_copy(name);
    if (upper == "POWER") return static_cast<int>(CompiledSupplySlot::kPower);
    if (upper == "GROUND") return static_cast<int>(CompiledSupplySlot::kGround);
    return -1;
}

const char* compiled_supply_name_for_slot(int slot) {
    return slot == static_cast<int>(CompiledSupplySlot::kPower) ? "POWER" : "GROUND";
}

const CompiledTechSpec& compiled_tech_spec_for_key(const std::string& raw_tech_key) {
    static const CompiledTechSpec kNangate45 = {
        "nangate45",
        {
            "metal1", "metal2", "metal3", "metal4", "metal5", "metal6",
            "metal7", "metal8", "metal9", "metal10", "metal11", "metal12",
        },
        capbench_compiled_recipes::kSupportedMacros,
        std::size(capbench_compiled_recipes::kSupportedMacros),
    };
    static const CompiledTechSpec kSky130hd = {
        "sky130hd",
        {"li1", "met1", "met2", "met3", "met4", "met5"},
        capbench_compiled_recipes::kSupportedMacrosSky130hd,
        std::size(capbench_compiled_recipes::kSupportedMacrosSky130hd),
    };

    const std::string tech_key = normalize_layer_name(raw_tech_key);
    if (tech_key == kNangate45.tech_key) {
        return kNangate45;
    }
    if (tech_key == kSky130hd.tech_key) {
        return kSky130hd;
    }
    throw std::runtime_error("Unsupported compiled recipe tech: " + raw_tech_key);
}

int compiled_layer_slot_for_name(const CompiledTechSpec& tech_spec, const std::string& name) {
    const std::string normalized = normalize_layer_name(name);
    for (std::size_t idx = 0; idx < tech_spec.normalized_layer_names.size(); ++idx) {
        if (tech_spec.normalized_layer_names[idx] == normalized) {
            return static_cast<int>(idx);
        }
    }
    return -1;
}

int compiled_signal_slot_for_name(const CompiledBaseMacroRecipe& recipe, const std::string& name) {
    for (std::size_t slot_idx = 0; slot_idx < recipe.signal_pin_names.size(); ++slot_idx) {
        if (recipe.signal_pin_names[slot_idx] == name) {
            return static_cast<int>(slot_idx);
        }
    }
    return -1;
}

int row_orient_index(const std::string& orient) {
    if (orient == "N") return 0;
    if (orient == "FN") return 1;
    if (orient == "FS") return 2;
    if (orient == "S") return 3;
    return -1;
}

const char* row_orient_name(int orient_index) {
    static constexpr const char* kNames[4] = {"N", "FN", "FS", "S"};
    return kNames[orient_index];
}

CompiledBaseMacroRecipe build_compiled_recipe(
    const capbench_compiled_recipes::MacroSpec& macro,
    const CompiledTechSpec& tech_spec
) {
    CompiledBaseMacroRecipe recipe;
    recipe.macro_name = macro.macro_name != nullptr ? macro.macro_name : "";
    recipe.size_x = macro.size_x;
    recipe.size_y = macro.size_y;
    std::unordered_map<std::string, int> signal_slots;
    int next_synthetic_group_index = 0;
    recipe.groups.reserve(macro.group_count);
    for (std::size_t group_idx = 0; group_idx < macro.group_count; ++group_idx) {
        const capbench_compiled_recipes::GroupSpec& group = macro.groups[group_idx];
        CompiledBaseGroup compiled_group;
        compiled_group.binding_kind = static_cast<CompiledBindingKind>(group.binding_kind);
        if (compiled_group.binding_kind == CompiledBindingKind::kPinNet) {
            const std::string binding_name = group.binding_name != nullptr ? group.binding_name : "";
            const auto [slot_it, inserted] =
                signal_slots.emplace(binding_name, static_cast<int>(recipe.signal_pin_names.size()));
            if (inserted) {
                recipe.signal_pin_names.push_back(binding_name);
            }
            compiled_group.binding_slot = slot_it->second;
        } else if (compiled_group.binding_kind == CompiledBindingKind::kSupplyNet) {
            compiled_group.binding_slot = compiled_supply_slot_for_name(group.binding_name != nullptr ? group.binding_name : "");
        } else {
            compiled_group.synthetic_group_index = next_synthetic_group_index++;
        }
        if (compiled_group.binding_kind != CompiledBindingKind::kSyntheticNet && compiled_group.binding_slot < 0) {
            throw std::runtime_error("Unsupported compiled recipe binding for macro '" + recipe.macro_name + "'");
        }
        compiled_group.rects.reserve(group.rect_count);
        for (std::size_t rect_idx = 0; rect_idx < group.rect_count; ++rect_idx) {
            const capbench_compiled_recipes::RectSpec& rect = group.rects[rect_idx];
            const int layer_slot = compiled_layer_slot_for_name(tech_spec, rect.layer != nullptr ? rect.layer : "");
            if (layer_slot < 0) {
                throw std::runtime_error(
                    "Unsupported compiled recipe layer for macro '" + recipe.macro_name +
                    "' on tech '" + tech_spec.tech_key + "'"
                );
            }
            compiled_group.rects.push_back({
                static_cast<std::uint8_t>(layer_slot),
                {rect.x0, rect.x1, rect.y0, rect.y1},
                rect.is_obs,
            });
        }
        recipe.groups.push_back(std::move(compiled_group));
    }
    return recipe;
}

std::vector<CompiledGroupTemplate> build_compiled_group_templates(const CompiledBaseMacroRecipe& recipe, const std::string& orient) {
    std::vector<CompiledGroupTemplate> out;
    out.reserve(recipe.groups.size());
    for (const CompiledBaseGroup& group : recipe.groups) {
        CompiledGroupTemplate templ;
        templ.binding_kind = group.binding_kind;
        templ.binding_slot = group.binding_slot;
        templ.synthetic_group_index = group.synthetic_group_index;
        templ.rects.reserve(group.rects.size());
        for (const CompiledLocalRect& rect : group.rects) {
            templ.rects.push_back({
                rect.layer_slot,
                transform_local_rect(
                    rect.local_rect.x0,
                    rect.local_rect.y0,
                    rect.local_rect.x1,
                    rect.local_rect.y1,
                    recipe.size_x,
                    recipe.size_y,
                    orient
                ),
                rect.is_obs,
            });
        }
        out.push_back(std::move(templ));
    }
    return out;
}

CompiledRecipeCacheEntry build_compiled_recipe_cache_entry(
    const capbench_compiled_recipes::MacroSpec& macro,
    const CompiledTechSpec& tech_spec
) {
    CompiledRecipeCacheEntry entry;
    entry.recipe = build_compiled_recipe(macro, tech_spec);
    for (int orient_index = 0; orient_index < 4; ++orient_index) {
        entry.templates[static_cast<std::size_t>(orient_index)] =
            build_compiled_group_templates(entry.recipe, row_orient_name(orient_index));
    }
    return entry;
}

std::vector<CompiledRecipeCacheEntry> build_compiled_recipe_cache(const CompiledTechSpec& tech_spec) {
    std::vector<CompiledRecipeCacheEntry> cache;
    cache.reserve(tech_spec.macro_count);
    for (std::size_t idx = 0; idx < tech_spec.macro_count; ++idx) {
        cache.push_back(build_compiled_recipe_cache_entry(tech_spec.macro_specs[idx], tech_spec));
    }
    return cache;
}

const std::vector<CompiledRecipeCacheEntry>& compiled_recipe_cache(const CompiledTechSpec& tech_spec) {
    static const std::vector<CompiledRecipeCacheEntry> kNangateCache =
        build_compiled_recipe_cache(compiled_tech_spec_for_key("nangate45"));
    static const std::vector<CompiledRecipeCacheEntry> kSky130hdCache =
        build_compiled_recipe_cache(compiled_tech_spec_for_key("sky130hd"));
    return tech_spec.tech_key == "nangate45" ? kNangateCache : kSky130hdCache;
}

const CompiledRecipeCacheEntry* find_compiled_recipe_cache_entry(
    const CompiledTechSpec& tech_spec,
    const std::string& macro_name
) {
    for (const CompiledRecipeCacheEntry& entry : compiled_recipe_cache(tech_spec)) {
        if (entry.recipe.macro_name == macro_name) {
            return &entry;
        }
    }
    return nullptr;
}

}  // namespace

PreparedCompactResult prepare_def_raster_compiled(
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
    if (target_size <= 0) {
        throw std::runtime_error("target_size must be positive");
    }
    const CompiledTechSpec& tech_spec = compiled_tech_spec_for_key(tech_key);
    const auto parse_start = std::chrono::steady_clock::now();

    DefResultGuard def_guard;
    char* error_message = nullptr;
    if (!lfd_parse_def_compact(def_path.c_str(), &def_guard.result, &error_message)) {
        const std::string message = error_message != nullptr ? error_message : "unknown DEF parse failure";
        lfd_free_error_message(error_message);
        throw std::runtime_error(message);
    }
    def_guard.loaded = true;

    const auto parse_end = std::chrono::steady_clock::now();
    const auto prep_start = std::chrono::steady_clock::now();

    std::vector<int> channel_by_layer_slot(tech_spec.normalized_layer_names.size(), -1);
    for (std::size_t idx = 0; idx < channel_layers.size(); ++idx) {
        const int layer_slot = compiled_layer_slot_for_name(tech_spec, channel_layers[idx]);
        if (layer_slot >= 0) {
            channel_by_layer_slot[static_cast<std::size_t>(layer_slot)] = static_cast<int>(idx);
        }
    }

    std::unordered_map<std::string, double> default_widths_um;
    default_widths_um.reserve(layer_widths_um.size());
    for (auto item : layer_widths_um) {
        default_widths_um[normalize_layer_name(py::cast<std::string>(item.first))] = py::cast<double>(item.second);
    }

    const std::array<double, 4> diearea_bounds = {
        def_guard.result.diearea[0],
        def_guard.result.diearea[1],
        def_guard.result.diearea[2],
        def_guard.result.diearea[3],
    };
    std::array<double, 4> bounds = diearea_bounds;
    if (!raster_bounds_obj.is_none()) {
        const std::vector<double> raster_bounds = py::cast<std::vector<double>>(raster_bounds_obj);
        if (raster_bounds.size() != 4U) {
            throw std::runtime_error("raster_bounds must contain 4 values");
        }
        bounds = {raster_bounds[0], raster_bounds[1], raster_bounds[2], raster_bounds[3]};
    }
    if (!(std::isfinite(bounds[0]) && std::isfinite(bounds[1]) && std::isfinite(bounds[2]) && std::isfinite(bounds[3])) ||
        bounds[2] <= bounds[0] || bounds[3] <= bounds[1]) {
        throw std::runtime_error("Invalid raster bounds");
    }

    double pixel_resolution = 0.0;
    if (pixel_resolution_obj.is_none()) {
        pixel_resolution = std::max(bounds[2] - bounds[0], bounds[3] - bounds[1]) / static_cast<double>(target_size);
    } else {
        pixel_resolution = py::cast<double>(pixel_resolution_obj);
    }
    if (!std::isfinite(pixel_resolution) || pixel_resolution <= 0.0) {
        throw std::runtime_error("Invalid pixel resolution");
    }

    std::unordered_map<std::string, std::size_t> component_index_by_name;
    component_index_by_name.reserve(def_guard.result.component_count);
    std::vector<CompiledComponentBindingState> component_binding_states(def_guard.result.component_count);
    for (std::size_t comp_idx = 0; comp_idx < def_guard.result.component_count; ++comp_idx) {
        const LfdComponent& component = def_guard.result.components[comp_idx];
        component_index_by_name[normalize_net_name(component.name)] = comp_idx;
        const CompiledRecipeCacheEntry* recipe_entry =
            find_compiled_recipe_cache_entry(tech_spec, component.cell_type != nullptr ? component.cell_type : "");
        component_binding_states[comp_idx].entry = recipe_entry;
        if (recipe_entry != nullptr) {
            component_binding_states[comp_idx].signal_nets.assign(recipe_entry->recipe.signal_pin_names.size(), "");
        }
    }

    auto add_instance_pin_maps = [&](const LfdNet* nets, std::size_t count) {
        for (std::size_t net_idx = 0; net_idx < count; ++net_idx) {
            const LfdNet& net = nets[net_idx];
            if (!include_net(net, include_supply_nets)) {
                continue;
            }
            const std::string net_name = normalize_net_name(net.name);
            for (std::size_t conn_idx = 0; conn_idx < net.connection_count; ++conn_idx) {
                const LfdConnection& conn = net.connections[conn_idx];
                const std::string component_name = normalize_net_name(conn.component);
                const std::string pin_name = normalize_net_name(conn.pin);
                if (component_name.empty() || pin_name.empty() || uppercase_copy(component_name) == "PIN") {
                    continue;
                }
                auto component_it = component_index_by_name.find(component_name);
                if (component_it == component_index_by_name.end()) {
                    continue;
                }
                CompiledComponentBindingState& binding_state = component_binding_states[component_it->second];
                if (binding_state.entry == nullptr) {
                    continue;
                }
                const int signal_slot = compiled_signal_slot_for_name(binding_state.entry->recipe, pin_name);
                if (signal_slot >= 0) {
                    binding_state.signal_nets[static_cast<std::size_t>(signal_slot)] = net_name;
                }
            }
        }
    };
    add_instance_pin_maps(def_guard.result.nets, def_guard.result.net_count);
    add_instance_pin_maps(def_guard.result.specialnets, def_guard.result.specialnet_count);

    std::array<std::string, static_cast<std::size_t>(CompiledSupplySlot::kCount)> supply_nets{};
    if (include_supply_nets) {
        for (std::size_t net_idx = 0; net_idx < def_guard.result.specialnet_count; ++net_idx) {
            const LfdNet& net = def_guard.result.specialnets[net_idx];
            const std::string net_name = normalize_net_name(net.name);
            if (net_name.empty()) {
                continue;
            }
            std::string supply_use = classify_supply_net(net_name);
            if (supply_use.empty()) {
                const std::string use_value = uppercase_copy(net.use != nullptr ? net.use : "");
                if (use_value == "POWER" || use_value == "GROUND") {
                    supply_use = use_value;
                }
            }
            if (!supply_use.empty()) {
                const int supply_slot = compiled_supply_slot_for_name(supply_use);
                if (supply_slot >= 0 && supply_nets[static_cast<std::size_t>(supply_slot)].empty()) {
                    supply_nets[static_cast<std::size_t>(supply_slot)] = net_name;
                }
            }
        }
    }

    PreparedCompactResult prepared;
    prepared.window_bounds = {bounds[0], bounds[1], 0.0, bounds[2], bounds[3], 0.0};
    prepared.pixel_resolution = pixel_resolution;

    std::vector<NamedRectEntry> route_rect_entries;
    std::unordered_set<std::string> real_net_names;

    auto process_net_set = [&](const LfdNet* nets, std::size_t count, bool is_special_net_set) {
        for (std::size_t net_idx = 0; net_idx < count; ++net_idx) {
            const LfdNet& net = nets[net_idx];
            const std::string net_name = normalize_net_name(net.name);
            if (!include_net(net, include_supply_nets) || net_name.empty() || net.routing_count == 0) {
                continue;
            }

            std::vector<double> widths_by_channel(channel_layers.size(), -1.0);
            std::vector<std::vector<const LfdRoutingSegment*>> segments_by_channel(channel_layers.size());
            for (std::size_t route_idx = 0; route_idx < net.routing_count; ++route_idx) {
                const LfdRoutingSegment& segment = net.routing[route_idx];
                const std::string normalized_layer = normalize_layer_name(segment.layer);
                prepared.total_segments += std::max<long long>(0, static_cast<long long>(segment.point_count) - 1);
                const int layer_slot = compiled_layer_slot_for_name(tech_spec, normalized_layer);
                if (layer_slot < 0) {
                    continue;
                }
                const int channel = channel_by_layer_slot[static_cast<std::size_t>(layer_slot)];
                if (channel < 0) {
                    continue;
                }
                double width_um = 0.0;
                if (segment.has_width != 0) {
                    width_um = segment.width;
                } else {
                    auto width_it = default_widths_um.find(normalized_layer);
                    if (width_it == default_widths_um.end()) {
                        throw std::runtime_error(
                            "DEF route width missing for layer '" + std::string(segment.layer != nullptr ? segment.layer : "") +
                            "' in " + def_path
                        );
                    }
                    width_um = width_it->second;
                }
                if (widths_by_channel[static_cast<std::size_t>(channel)] < 0.0) {
                    widths_by_channel[static_cast<std::size_t>(channel)] = width_um;
                } else if (!approx_equal(widths_by_channel[static_cast<std::size_t>(channel)], width_um)) {
                    throw std::runtime_error(
                        "Mixed route widths on net '" + net_name + "' layer '" +
                        std::string(segment.layer != nullptr ? segment.layer : "") + "' are not supported"
                    );
                }
                segments_by_channel[static_cast<std::size_t>(channel)].push_back(&segment);
            }

            for (std::size_t channel_idx = 0; channel_idx < segments_by_channel.size(); ++channel_idx) {
                const std::vector<const LfdRoutingSegment*>& channel_segments = segments_by_channel[channel_idx];
                if (channel_segments.empty()) {
                    continue;
                }
                const int channel = static_cast<int>(channel_idx);
                const double width_um = widths_by_channel[channel_idx];
                const double half = 0.5 * width_um;
                const std::uint8_t source_kind = is_special_net_set ? RECT_SOURCE_SPECIAL_ROUTE : RECT_SOURCE_ROUTE;

                for (const LfdRoutingSegment* segment : channel_segments) {
                    for (std::size_t point_idx = 0; point_idx + 1 < segment->point_count; ++point_idx) {
                        const double x0 = segment->points_xy[point_idx * 2];
                        const double y0 = segment->points_xy[point_idx * 2 + 1];
                        const double x1 = segment->points_xy[(point_idx + 1) * 2];
                        const double y1 = segment->points_xy[(point_idx + 1) * 2 + 1];
                        if (approx_equal(x0, x1) && approx_equal(y0, y1)) {
                            continue;
                        }

                        RectD rect{};
                        if (approx_equal(y0, y1) && !approx_equal(x0, x1)) {
                            rect = {std::min(x0, x1) - half, std::max(x0, x1) + half, y0 - half, y0 + half};
                        } else if (approx_equal(x0, x1) && !approx_equal(y0, y1)) {
                            rect = {x0 - half, x0 + half, std::min(y0, y1) - half, std::max(y0, y1) + half};
                        } else {
                            throw std::runtime_error(
                                "Non-Manhattan DEF segment edge in " + def_path + " on net '" + net_name + "'"
                            );
                        }
                        prepared.total_endpoint_extensions += 2;

                        RectD clipped{};
                        if (!clip_rect(rect, bounds, &clipped)) {
                            continue;
                        }
                        append_named_rect_entry(
                            &route_rect_entries,
                            net_name,
                            channel,
                            clipped,
                            bounds[0],
                            bounds[1],
                            pixel_resolution,
                            target_size,
                            source_kind
                        );
                        real_net_names.insert(net_name);
                    }
                }
            }
        }
    };
    process_net_set(def_guard.result.nets, def_guard.result.net_count, false);
    process_net_set(def_guard.result.specialnets, def_guard.result.specialnet_count, true);

    struct PendingCompiledRect {
        int channel = -1;
        RectD rect{};
        bool is_obs = false;
    };
    struct PendingCompiledGroup {
        CompiledBindingKind binding_kind = CompiledBindingKind::kPinNet;
        std::string conductor_name;
        std::string instance_name;
        std::string synthetic_label;
        std::vector<PendingCompiledRect> rects;
    };
    std::vector<PendingCompiledGroup> pending_groups;
    std::size_t pending_group_rect_count = 0;

    for (std::size_t comp_idx = 0; comp_idx < def_guard.result.component_count; ++comp_idx) {
        const LfdComponent& component = def_guard.result.components[comp_idx];
        const std::string macro_name = component.cell_type != nullptr ? component.cell_type : "";
        const CompiledComponentBindingState& binding_state = component_binding_states[comp_idx];
        const CompiledRecipeCacheEntry* recipe_entry = binding_state.entry;
        if (recipe_entry == nullptr) {
            throw std::runtime_error(
                "Compiled prepare does not support macro '" + macro_name +
                "' on tech '" + tech_spec.tech_key +
                "' for instance '" + normalize_net_name(component.name != nullptr ? component.name : "") + "'"
            );
        }

        const std::string orient = canonical_orient(component.orient != nullptr ? component.orient : "N");
        const int orient_index = row_orient_index(orient);
        if (orient_index < 0) {
            throw std::runtime_error(
                "Compiled prepare only supports row-valid orientations (N/FN/FS/S) for " +
                normalize_net_name(component.name != nullptr ? component.name : "") + ": got '" + orient + "'"
            );
        }

        const std::string instance_name = normalize_net_name(component.name);
        for (const CompiledGroupTemplate& group : recipe_entry->templates[static_cast<std::size_t>(orient_index)]) {
            std::vector<PendingCompiledRect> active_rects;
            active_rects.reserve(group.rects.size());
            for (const CompiledLocalRect& local_rect : group.rects) {
                const int channel = channel_by_layer_slot[static_cast<std::size_t>(local_rect.layer_slot)];
                if (channel < 0) {
                    continue;
                }
                RectD world_rect = {
                    component.x + local_rect.local_rect.x0,
                    component.x + local_rect.local_rect.x1,
                    component.y + local_rect.local_rect.y0,
                    component.y + local_rect.local_rect.y1,
                };
                RectD clipped{};
                if (!clip_rect(world_rect, bounds, &clipped)) {
                    continue;
                }
                active_rects.push_back({channel, clipped, local_rect.is_obs});
            }
            if (active_rects.empty()) {
                continue;
            }

            std::string conductor_name;
            std::string synthetic_label;
            CompiledBindingKind resolved_binding_kind = group.binding_kind;
            if (group.binding_kind == CompiledBindingKind::kPinNet) {
                if (group.binding_slot < 0 || static_cast<std::size_t>(group.binding_slot) >= binding_state.signal_nets.size()) {
                    throw std::runtime_error("Internal error: invalid compiled signal binding slot");
                }
                conductor_name = binding_state.signal_nets[static_cast<std::size_t>(group.binding_slot)];
                if (conductor_name.empty()) {
                    resolved_binding_kind = CompiledBindingKind::kSyntheticNet;
                    synthetic_label = "PIN_" + recipe_entry->recipe.signal_pin_names[static_cast<std::size_t>(group.binding_slot)];
                    ++prepared.component_stats[5];
                } else {
                    real_net_names.insert(conductor_name);
                    ++prepared.component_stats[0];
                }
            } else if (group.binding_kind == CompiledBindingKind::kSupplyNet) {
                conductor_name = supply_nets[static_cast<std::size_t>(group.binding_slot)];
                if (conductor_name.empty()) {
                    throw std::runtime_error(
                        "Compiled recipe could not resolve required supply '" +
                        std::string(compiled_supply_name_for_slot(group.binding_slot)) +
                        "' for instance '" + instance_name + "'"
                    );
                }
                real_net_names.insert(conductor_name);
                ++prepared.component_stats[1];
            } else {
                synthetic_label = "OBS" + std::to_string(group.synthetic_group_index);
                ++prepared.component_stats[5];
            }

            pending_group_rect_count += active_rects.size();
            pending_groups.push_back({
                resolved_binding_kind,
                std::move(conductor_name),
                instance_name,
                std::move(synthetic_label),
                std::move(active_rects),
            });
        }
    }

    std::vector<std::string> real_conductor_names_sorted(real_net_names.begin(), real_net_names.end());
    std::sort(real_conductor_names_sorted.begin(), real_conductor_names_sorted.end());
    prepared.real_conductor_count = static_cast<long long>(real_conductor_names_sorted.size());
    std::unordered_map<std::string, int> real_conductor_id_map;
    real_conductor_id_map.reserve(real_conductor_names_sorted.size());
    for (std::size_t idx = 0; idx < real_conductor_names_sorted.size(); ++idx) {
        real_conductor_id_map[real_conductor_names_sorted[idx]] = static_cast<int>(idx) + 1;
    }

    std::vector<RectEntry> rect_entries;
    rect_entries.reserve(route_rect_entries.size() + pending_group_rect_count);
    for (const NamedRectEntry& rect_entry : route_rect_entries) {
        rect_entries.push_back({
            real_conductor_id_map.at(rect_entry.conductor_name),
            rect_entry.channel,
            rect_entry.px_min,
            rect_entry.px_max,
            rect_entry.py_min,
            rect_entry.py_max,
            rect_entry.source_kind,
        });
    }

    std::vector<std::string> synthetic_conductor_names;
    if (include_conductor_names) {
        synthetic_conductor_names.reserve(pending_groups.size());
    }
    int next_synthetic_conductor_id = static_cast<int>(prepared.real_conductor_count) + 1;
    for (const PendingCompiledGroup& group : pending_groups) {
        int conductor_id = -1;
        if (group.binding_kind == CompiledBindingKind::kSyntheticNet) {
            conductor_id = next_synthetic_conductor_id++;
            if (include_conductor_names) {
                synthetic_conductor_names.push_back("__lef__/" + group.instance_name + "/" + group.synthetic_label);
            }
        } else {
            conductor_id = real_conductor_id_map.at(group.conductor_name);
        }
        for (const PendingCompiledRect& rect : group.rects) {
            append_rect_entry(
                &rect_entries,
                conductor_id,
                rect.channel,
                rect.rect,
                bounds[0],
                bounds[1],
                pixel_resolution,
                target_size,
                rect.is_obs ? RECT_SOURCE_LEF_OBS : RECT_SOURCE_LEF_PIN
            );
        }
    }

    const std::size_t conductor_count = static_cast<std::size_t>(next_synthetic_conductor_id - 1);
    if (conductor_count > static_cast<std::size_t>(std::numeric_limits<std::int16_t>::max())) {
        throw std::runtime_error(
            "Prepared LEF+DEF conductors exceed int16 limit for " + def_path + ": " + std::to_string(conductor_count)
        );
    }

    prepared.rect_source_kind_codes.reserve(rect_entries.size());
    prepared.rect_entries = std::move(rect_entries);
    for (const RectEntry& rect_entry : prepared.rect_entries) {
        prepared.rect_source_kind_codes.push_back(rect_entry.source_kind);
    }
    if (include_conductor_names) {
        prepared.conductor_names_sorted = std::move(real_conductor_names_sorted);
        prepared.conductor_names_sorted.insert(
            prepared.conductor_names_sorted.end(),
            synthetic_conductor_names.begin(),
            synthetic_conductor_names.end()
        );
    }
    prepared.conductor_count = static_cast<long long>(conductor_count);
    prepared.active_rectangles = static_cast<long long>(prepared.rect_entries.size());

    const auto prep_end = std::chrono::steady_clock::now();
    prepared.parse_ms = std::chrono::duration<double, std::milli>(parse_end - parse_start).count();
    prepared.prepare_ms = std::chrono::duration<double, std::milli>(prep_end - prep_start).count();
    return prepared;
}
