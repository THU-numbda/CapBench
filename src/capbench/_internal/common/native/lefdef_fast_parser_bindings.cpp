#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cctype>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include <torch/extension.h>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "lefdef_fast_parser.h"
#include "lefdef_fast_parser_bindings_shared.h"
#include "lefdef_fast_parser_compiled.h"
#include "lefdef_compiled_cell_recipes.h"

namespace py = pybind11;

namespace {

constexpr int RECT_COL_LAYER = 0;
constexpr int RECT_COL_CONDUCTOR_ID = 1;
constexpr int RECT_COL_PX_MIN = 2;
constexpr int RECT_COL_PX_MAX = 3;
constexpr int RECT_COL_PY_MIN = 4;
constexpr int RECT_COL_PY_MAX = 5;
constexpr int RECT_COL_COUNT = 6;
constexpr double kEps = 1e-9;

struct RouteTouchRect {
    RectD rect;
    std::string net_name;
};

struct PrimitiveRect {
    RectD rect;
    std::string attached_net;
    bool has_attached_net;
    bool is_obs;
    std::string pin_name;
    std::string pin_use;
};

struct TemplatePrimitive {
    std::string normalized_layer;
    RectD local_rect;
    bool is_obs;
    std::string pin_name;
    std::string pin_use;
};

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

struct CompiledLocalRect {
    std::string normalized_layer;
    RectD local_rect;
    bool is_obs = false;
};

struct CompiledGroupTemplate {
    CompiledBindingKind binding_kind;
    int binding_slot = -1;
    std::string binding_name;
    std::vector<CompiledLocalRect> rects;
};

struct CompiledBaseGroup {
    CompiledBindingKind binding_kind;
    int binding_slot = -1;
    std::string binding_name;
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

struct UnionFind {
    explicit UnionFind(std::size_t size) : parent(size), rank(size, 0) {
        for (std::size_t i = 0; i < size; ++i) {
            parent[i] = static_cast<int>(i);
        }
    }

    int find(int x) {
        int root = x;
        while (parent[root] != root) {
            root = parent[root];
        }
        while (parent[x] != x) {
            const int next = parent[x];
            parent[x] = root;
            x = next;
        }
        return root;
    }

    void unite(int a, int b) {
        int ra = find(a);
        int rb = find(b);
        if (ra == rb) {
            return;
        }
        if (rank[ra] < rank[rb]) {
            std::swap(ra, rb);
        }
        parent[rb] = ra;
        if (rank[ra] == rank[rb]) {
            ++rank[ra];
        }
    }

    std::vector<int> parent;
    std::vector<int> rank;
};

struct LayerRouteIndex {
    std::vector<RouteTouchRect> rects;
    std::unordered_map<long long, std::vector<int>> buckets;
    std::vector<unsigned int> marks;
    unsigned int epoch = 1;
    double cell_size = 1.0;
    double origin_x = 0.0;
    double origin_y = 0.0;
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

struct LefResultGuard {
    ~LefResultGuard() {
        if (loaded) {
            lfd_free_lef_parse_result(&result);
        }
    }
    LfdLefParseResult result{};
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
    std::transform(out.begin(), out.end(), out.begin(), [](unsigned char ch) {
        return static_cast<char>(std::toupper(ch));
    });
    return out;
}

bool string_case_equals(const std::string& lhs, const char* rhs) {
    return uppercase_copy(lhs) == uppercase_copy(rhs != nullptr ? rhs : "");
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

std::string component_pin_key(const std::string& component_name, const std::string& pin_name) {
    return component_name + '\x1f' + pin_name;
}

long long cell_key(int ix, int iy) {
    return (static_cast<long long>(ix) << 32) ^ static_cast<unsigned int>(iy);
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
    if (orient == "R0") {
        return "N";
    }
    if (orient == "R90") {
        return "E";
    }
    if (orient == "R180") {
        return "S";
    }
    if (orient == "R270") {
        return "W";
    }
    if (orient == "MX") {
        return "FS";
    }
    if (orient == "MY") {
        return "FN";
    }
    if (orient == "MYR90") {
        return "FE";
    }
    if (orient == "MXR90") {
        return "FW";
    }
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
    out->x0 = std::max(bounds[0], rect.x0);
    out->x1 = std::min(bounds[2], rect.x1);
    out->y0 = std::max(bounds[1], rect.y0);
    out->y1 = std::min(bounds[3], rect.y1);
    return out->x0 < out->x1 && out->y0 < out->y1;
}

bool touches_or_overlaps(const RectD& a, const RectD& b) {
    return !(a.x1 < b.x0 - kEps || b.x1 < a.x0 - kEps || a.y1 < b.y0 - kEps || b.y1 < a.y0 - kEps);
}

RectD union_rect(const RectD& a, const RectD& b) {
    return {
        std::min(a.x0, b.x0),
        std::max(a.x1, b.x1),
        std::min(a.y0, b.y0),
        std::max(a.y1, b.y1),
    };
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

std::string join_sorted_strings(const std::unordered_set<std::string>& values) {
    std::vector<std::string> ordered(values.begin(), values.end());
    std::sort(ordered.begin(), ordered.end());
    std::ostringstream out;
    for (std::size_t idx = 0; idx < ordered.size(); ++idx) {
        if (idx > 0) {
            out << ", ";
        }
        out << ordered[idx];
    }
    return out.str();
}

std::string format_missing_macro_error(
    const std::string& def_path,
    const std::string& lef_path,
    const std::unordered_map<std::string, std::vector<std::string>>& missing_by_macro
) {
    std::ostringstream out;
    std::size_t total_missing = 0;
    for (const auto& item : missing_by_macro) {
        total_missing += item.second.size();
    }
    out << "Missing LEF macro definitions for DEF components in " << def_path << "\n";
    out << "  def_path=" << def_path << "\n";
    out << "  lef_path=" << lef_path << "\n";
    out << "  missing_macro_types=" << missing_by_macro.size() << " missing_instances=" << total_missing;
    std::vector<std::string> macro_names;
    macro_names.reserve(missing_by_macro.size());
    for (const auto& item : missing_by_macro) {
        macro_names.push_back(item.first);
    }
    std::sort(macro_names.begin(), macro_names.end());
    for (const std::string& macro_name : macro_names) {
        auto it = missing_by_macro.find(macro_name);
        if (it == missing_by_macro.end()) {
            continue;
        }
        std::vector<std::string> instances = it->second;
        std::sort(instances.begin(), instances.end());
        out << "\n  " << macro_name << ": ";
        for (std::size_t idx = 0; idx < instances.size() && idx < 5; ++idx) {
            if (idx > 0) {
                out << ", ";
            }
            out << instances[idx];
        }
        if (instances.size() > 5) {
            out << ", ...";
        }
        out << " (instances=" << instances.size() << ")";
    }
    return out.str();
}

int compiled_supply_slot_for_name(const std::string& name) {
    if (name == "POWER") {
        return static_cast<int>(CompiledSupplySlot::kPower);
    }
    if (name == "GROUND") {
        return static_cast<int>(CompiledSupplySlot::kGround);
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
    if (orient == "N") {
        return 0;
    }
    if (orient == "FN") {
        return 1;
    }
    if (orient == "FS") {
        return 2;
    }
    if (orient == "S") {
        return 3;
    }
    return -1;
}

const char* row_orient_name(int orient_index) {
    static constexpr const char* kNames[4] = {"N", "FN", "FS", "S"};
    return kNames[orient_index];
}

CompiledBaseMacroRecipe build_compiled_recipe(const capbench_compiled_recipes::MacroSpec& macro) {
    CompiledBaseMacroRecipe recipe;
    recipe.macro_name = macro.macro_name != nullptr ? macro.macro_name : "";
    recipe.size_x = macro.size_x;
    recipe.size_y = macro.size_y;
    std::unordered_map<std::string, int> signal_slots;
    recipe.groups.reserve(macro.group_count);
    for (std::size_t group_idx = 0; group_idx < macro.group_count; ++group_idx) {
        const capbench_compiled_recipes::GroupSpec& group = macro.groups[group_idx];
        CompiledBaseGroup compiled_group;
        compiled_group.binding_kind = static_cast<CompiledBindingKind>(group.binding_kind);
        compiled_group.binding_name = group.binding_name != nullptr ? group.binding_name : "";
        if (compiled_group.binding_kind == CompiledBindingKind::kPinNet) {
            const auto [slot_it, inserted] =
                signal_slots.emplace(compiled_group.binding_name, static_cast<int>(recipe.signal_pin_names.size()));
            if (inserted) {
                recipe.signal_pin_names.push_back(compiled_group.binding_name);
            }
            compiled_group.binding_slot = slot_it->second;
        } else if (compiled_group.binding_kind == CompiledBindingKind::kSupplyNet) {
            compiled_group.binding_slot = compiled_supply_slot_for_name(compiled_group.binding_name);
        } else {
            compiled_group.binding_slot = -1;
        }
        if (compiled_group.binding_kind != CompiledBindingKind::kSyntheticNet && compiled_group.binding_slot < 0) {
            throw std::runtime_error(
                "Unsupported compiled recipe binding '" + compiled_group.binding_name +
                "' for macro '" + recipe.macro_name + "'"
            );
        }
        compiled_group.rects.reserve(group.rect_count);
        for (std::size_t rect_idx = 0; rect_idx < group.rect_count; ++rect_idx) {
            const capbench_compiled_recipes::RectSpec& rect = group.rects[rect_idx];
            compiled_group.rects.push_back({
                normalize_layer_name(rect.layer),
                {rect.x0, rect.x1, rect.y0, rect.y1},
                rect.is_obs,
            });
        }
        recipe.groups.push_back(std::move(compiled_group));
    }
    return recipe;
}

std::vector<CompiledGroupTemplate> build_compiled_group_templates(
    const CompiledBaseMacroRecipe& recipe,
    const std::string& orient
);

CompiledRecipeCacheEntry build_compiled_recipe_cache_entry(const capbench_compiled_recipes::MacroSpec& macro) {
    CompiledRecipeCacheEntry entry;
    entry.recipe = build_compiled_recipe(macro);
    for (int orient_index = 0; orient_index < 4; ++orient_index) {
        entry.templates[static_cast<std::size_t>(orient_index)] =
            build_compiled_group_templates(entry.recipe, row_orient_name(orient_index));
    }
    return entry;
}

const std::vector<CompiledRecipeCacheEntry>& compiled_recipe_cache() {
    static const std::vector<CompiledRecipeCacheEntry> kCache = [] {
        std::vector<CompiledRecipeCacheEntry> cache;
        cache.reserve(std::size(capbench_compiled_recipes::kSupportedMacros));
        for (const capbench_compiled_recipes::MacroSpec& macro : capbench_compiled_recipes::kSupportedMacros) {
            cache.push_back(build_compiled_recipe_cache_entry(macro));
        }
        return cache;
    }();
    return kCache;
}

const CompiledRecipeCacheEntry* find_compiled_recipe_cache_entry(const std::string& macro_name) {
    for (const CompiledRecipeCacheEntry& entry : compiled_recipe_cache()) {
        if (entry.recipe.macro_name == macro_name) {
            return &entry;
        }
    }
    return nullptr;
}

std::vector<CompiledGroupTemplate> build_compiled_group_templates(
    const CompiledBaseMacroRecipe& recipe,
    const std::string& orient
) {
    std::vector<CompiledGroupTemplate> out;
    out.reserve(recipe.groups.size());
    for (const CompiledBaseGroup& group : recipe.groups) {
        CompiledGroupTemplate templ;
        templ.binding_kind = group.binding_kind;
        templ.binding_slot = group.binding_slot;
        templ.binding_name = group.binding_name;
        templ.rects.reserve(group.rects.size());
        for (const CompiledLocalRect& rect : group.rects) {
            templ.rects.push_back({
                rect.normalized_layer,
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

LayerRouteIndex build_route_index(
    const std::vector<RouteTouchRect>& rects,
    const std::array<double, 4>& bounds,
    double pixel_resolution
) {
    LayerRouteIndex index;
    index.rects = rects;
    index.origin_x = bounds[0];
    index.origin_y = bounds[1];
    index.cell_size = std::max(pixel_resolution * 8.0, 1e-6);
    index.marks.assign(rects.size(), 0U);

    for (std::size_t rect_idx = 0; rect_idx < rects.size(); ++rect_idx) {
        const RectD& rect = rects[rect_idx].rect;
        const int ix0 = static_cast<int>(std::floor((rect.x0 - index.origin_x) / index.cell_size));
        const int ix1 = static_cast<int>(std::floor((rect.x1 - index.origin_x) / index.cell_size));
        const int iy0 = static_cast<int>(std::floor((rect.y0 - index.origin_y) / index.cell_size));
        const int iy1 = static_cast<int>(std::floor((rect.y1 - index.origin_y) / index.cell_size));
        for (int ix = ix0; ix <= ix1; ++ix) {
            for (int iy = iy0; iy <= iy1; ++iy) {
                index.buckets[cell_key(ix, iy)].push_back(static_cast<int>(rect_idx));
            }
        }
    }
    return index;
}

std::vector<int> query_route_candidates(LayerRouteIndex* index, const RectD& bbox) {
    std::vector<int> out;
    if (index == nullptr || index->rects.empty()) {
        return out;
    }
    if (index->epoch == std::numeric_limits<unsigned int>::max()) {
        std::fill(index->marks.begin(), index->marks.end(), 0U);
        index->epoch = 1;
    } else {
        ++index->epoch;
    }

    const int ix0 = static_cast<int>(std::floor((bbox.x0 - index->origin_x) / index->cell_size));
    const int ix1 = static_cast<int>(std::floor((bbox.x1 - index->origin_x) / index->cell_size));
    const int iy0 = static_cast<int>(std::floor((bbox.y0 - index->origin_y) / index->cell_size));
    const int iy1 = static_cast<int>(std::floor((bbox.y1 - index->origin_y) / index->cell_size));
    for (int ix = ix0; ix <= ix1; ++ix) {
        for (int iy = iy0; iy <= iy1; ++iy) {
            auto bucket_it = index->buckets.find(cell_key(ix, iy));
            if (bucket_it == index->buckets.end()) {
                continue;
            }
            for (int rect_idx : bucket_it->second) {
                if (index->marks[static_cast<std::size_t>(rect_idx)] == index->epoch) {
                    continue;
                }
                index->marks[static_cast<std::size_t>(rect_idx)] = index->epoch;
                out.push_back(rect_idx);
            }
        }
    }
    return out;
}

std::vector<TemplatePrimitive> build_oriented_templates(
    const LfdMacro& macro,
    const std::string& orient,
    const std::unordered_map<std::string, int>& layer_name_to_channel
) {
    std::vector<TemplatePrimitive> out;
    out.reserve(macro.pin_rect_count + macro.obs_rect_count);

    for (std::size_t idx = 0; idx < macro.pin_rect_count; ++idx) {
        const LfdPinRect& rect = macro.pin_rects[idx];
        const std::string normalized_layer = normalize_layer_name(rect.layer);
        if (layer_name_to_channel.find(normalized_layer) == layer_name_to_channel.end()) {
            continue;
        }
        out.push_back({
            normalized_layer,
            transform_local_rect(rect.x0, rect.y0, rect.x1, rect.y1, macro.size_x, macro.size_y, orient),
            false,
            normalize_net_name(rect.pin_name),
            uppercase_copy(rect.pin_use != nullptr ? rect.pin_use : ""),
        });
    }

    for (std::size_t idx = 0; idx < macro.obs_rect_count; ++idx) {
        const LfdObsRect& rect = macro.obs_rects[idx];
        const std::string normalized_layer = normalize_layer_name(rect.layer);
        if (layer_name_to_channel.find(normalized_layer) == layer_name_to_channel.end()) {
            continue;
        }
        out.push_back({
            normalized_layer,
            transform_local_rect(rect.x0, rect.y0, rect.x1, rect.y1, macro.size_x, macro.size_y, orient),
            true,
            "",
            "",
        });
    }

    return out;
}

void append_component_primitives(
    const LfdComponent& component,
    const LfdMacro& macro,
    const std::unordered_map<std::string, int>& layer_name_to_channel,
    const std::unordered_map<std::string, std::string>& instance_pin_to_net,
    const std::unordered_map<std::string, std::string>& supply_use_to_net,
    const std::array<double, 4>& bounds,
    std::unordered_map<std::string, std::vector<PrimitiveRect>>* out,
    std::unordered_map<std::string, std::vector<TemplatePrimitive>>* template_cache
) {
    const std::string orient = canonical_orient(component.orient != nullptr ? component.orient : "N");
    const std::string macro_name = macro.name != nullptr ? macro.name : "";
    const std::string cache_key = macro_name + '\x1f' + orient;
    auto cache_it = template_cache->find(cache_key);
    if (cache_it == template_cache->end()) {
        cache_it = template_cache->emplace(cache_key, build_oriented_templates(macro, orient, layer_name_to_channel)).first;
    }

    const std::string instance_name = normalize_net_name(component.name);
    for (const TemplatePrimitive& templ : cache_it->second) {
        RectD world_rect = {
            component.x + templ.local_rect.x0,
            component.x + templ.local_rect.x1,
            component.y + templ.local_rect.y0,
            component.y + templ.local_rect.y1,
        };
        RectD clipped{};
        if (!clip_rect(world_rect, bounds, &clipped)) {
            continue;
        }

        PrimitiveRect primitive{};
        primitive.rect = clipped;
        primitive.is_obs = templ.is_obs;
        primitive.pin_name = templ.pin_name;
        primitive.pin_use = templ.pin_use;
        primitive.has_attached_net = false;
        if (!templ.is_obs && !templ.pin_name.empty()) {
            auto net_it = instance_pin_to_net.find(component_pin_key(instance_name, templ.pin_name));
            if (net_it != instance_pin_to_net.end()) {
                primitive.attached_net = net_it->second;
                primitive.has_attached_net = true;
            } else if (templ.pin_use == "POWER" || templ.pin_use == "GROUND") {
                auto supply_it = supply_use_to_net.find(templ.pin_use);
                if (supply_it != supply_use_to_net.end()) {
                    primitive.attached_net = supply_it->second;
                    primitive.has_attached_net = true;
                }
            }
        }
        (*out)[templ.normalized_layer].push_back(std::move(primitive));
    }
}

PreparedCompactResult prepare_def_raster_compact(
    const std::string& def_path,
    const std::string& lef_path,
    const std::vector<std::string>& channel_layers,
    const py::dict& layer_widths_um,
    int target_size,
    py::object pixel_resolution_obj,
    py::object raster_bounds_obj,
    bool include_supply_nets
) {
    if (target_size <= 0) {
        throw std::runtime_error("target_size must be positive");
    }

    const auto parse_start = std::chrono::steady_clock::now();

    DefResultGuard def_guard;
    LefResultGuard lef_guard;
    char* error_message = nullptr;
    if (!lfd_parse_def_compact(def_path.c_str(), &def_guard.result, &error_message)) {
        const std::string message = error_message != nullptr ? error_message : "unknown DEF parse failure";
        lfd_free_error_message(error_message);
        throw std::runtime_error(message);
    }
    def_guard.loaded = true;

    error_message = nullptr;
    if (!lfd_parse_lef_abstracts(lef_path.c_str(), &lef_guard.result, &error_message)) {
        const std::string message = error_message != nullptr ? error_message : "unknown LEF parse failure";
        lfd_free_error_message(error_message);
        throw std::runtime_error(message);
    }
    lef_guard.loaded = true;

    std::unordered_map<std::string, const LfdMacro*> macro_by_name;
    macro_by_name.reserve(lef_guard.result.macro_count);
    for (std::size_t idx = 0; idx < lef_guard.result.macro_count; ++idx) {
        const LfdMacro& macro = lef_guard.result.macros[idx];
        macro_by_name[macro.name != nullptr ? macro.name : ""] = &macro;
    }

    std::unordered_map<std::string, std::vector<std::string>> missing_by_macro;
    for (std::size_t idx = 0; idx < def_guard.result.component_count; ++idx) {
        const LfdComponent& component = def_guard.result.components[idx];
        const std::string cell_type = component.cell_type != nullptr ? component.cell_type : "";
        if (macro_by_name.find(cell_type) == macro_by_name.end()) {
            missing_by_macro[cell_type].push_back(component.name != nullptr ? component.name : "");
        }
    }
    if (!missing_by_macro.empty()) {
        throw std::runtime_error(format_missing_macro_error(def_path, lef_path, missing_by_macro));
    }

    const auto parse_end = std::chrono::steady_clock::now();
    const auto prep_start = std::chrono::steady_clock::now();

    std::unordered_map<std::string, int> layer_name_to_channel;
    layer_name_to_channel.reserve(channel_layers.size());
    for (std::size_t idx = 0; idx < channel_layers.size(); ++idx) {
        layer_name_to_channel[normalize_layer_name(channel_layers[idx])] = static_cast<int>(idx);
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

    std::unordered_map<std::string, std::string> instance_pin_to_net;
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
                instance_pin_to_net[component_pin_key(component_name, pin_name)] = net_name;
            }
        }
    };
    add_instance_pin_maps(def_guard.result.nets, def_guard.result.net_count);
    add_instance_pin_maps(def_guard.result.specialnets, def_guard.result.specialnet_count);

    std::unordered_map<std::string, std::string> supply_use_to_net;
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
            if (!supply_use.empty() && supply_use_to_net.find(supply_use) == supply_use_to_net.end()) {
                supply_use_to_net[supply_use] = net_name;
            }
        }
    }

    PreparedCompactResult prepared;
    prepared.window_bounds = {bounds[0], bounds[1], 0.0, bounds[2], bounds[3], 0.0};
    prepared.pixel_resolution = pixel_resolution;

    std::vector<NamedRectEntry> rect_entries;
    std::unordered_set<std::string> real_net_names;
    std::unordered_map<std::string, std::vector<RouteTouchRect>> route_rects_by_layer;

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
                auto layer_it = layer_name_to_channel.find(normalized_layer);
                if (layer_it == layer_name_to_channel.end()) {
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
                const int channel = layer_it->second;
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
                const std::string normalized_channel_layer = normalize_layer_name(channel_layers[channel_idx]);
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
                        route_rects_by_layer[normalized_channel_layer].push_back({clipped, net_name});
                        append_named_rect_entry(
                            &rect_entries,
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

    std::unordered_map<std::string, LayerRouteIndex> route_index_by_layer;
    route_index_by_layer.reserve(route_rects_by_layer.size());
    for (const auto& item : route_rects_by_layer) {
        route_index_by_layer.emplace(item.first, build_route_index(item.second, bounds, pixel_resolution));
    }

    std::unordered_map<std::string, std::vector<TemplatePrimitive>> template_cache;
    template_cache.reserve(macro_by_name.size() * 4U);

    for (std::size_t comp_idx = 0; comp_idx < def_guard.result.component_count; ++comp_idx) {
        const LfdComponent& component = def_guard.result.components[comp_idx];
        const std::string macro_name = component.cell_type != nullptr ? component.cell_type : "";
        const LfdMacro& macro = *macro_by_name.at(macro_name);

        std::unordered_map<std::string, std::vector<PrimitiveRect>> per_layer;
        append_component_primitives(
            component,
            macro,
            layer_name_to_channel,
            instance_pin_to_net,
            supply_use_to_net,
            bounds,
            &per_layer,
            &template_cache
        );

        const std::string instance_name = normalize_net_name(component.name);
        for (auto& layer_item : per_layer) {
            const std::string& normalized_layer = layer_item.first;
            std::vector<PrimitiveRect>& primitives = layer_item.second;
            if (primitives.empty()) {
                continue;
            }

            UnionFind uf(primitives.size());
            std::unordered_map<std::string, int> first_by_pin;
            for (std::size_t idx = 0; idx < primitives.size(); ++idx) {
                const std::string& pin_name = primitives[idx].pin_name;
                if (pin_name.empty()) {
                    continue;
                }
                auto it = first_by_pin.find(pin_name);
                if (it == first_by_pin.end()) {
                    first_by_pin[pin_name] = static_cast<int>(idx);
                } else {
                    uf.unite(it->second, static_cast<int>(idx));
                }
            }

            std::vector<int> order(primitives.size());
            for (std::size_t idx = 0; idx < primitives.size(); ++idx) {
                order[idx] = static_cast<int>(idx);
            }
            std::sort(order.begin(), order.end(), [&](int lhs, int rhs) {
                if (!approx_equal(primitives[lhs].rect.x0, primitives[rhs].rect.x0)) {
                    return primitives[lhs].rect.x0 < primitives[rhs].rect.x0;
                }
                if (!approx_equal(primitives[lhs].rect.x1, primitives[rhs].rect.x1)) {
                    return primitives[lhs].rect.x1 < primitives[rhs].rect.x1;
                }
                return lhs < rhs;
            });

            std::vector<int> active;
            active.reserve(primitives.size());
            for (int idx : order) {
                std::vector<int> next_active;
                next_active.reserve(active.size() + 1U);
                for (int active_idx : active) {
                    if (primitives[active_idx].rect.x1 >= primitives[idx].rect.x0 - kEps) {
                        next_active.push_back(active_idx);
                    }
                }
                active.swap(next_active);

                for (int active_idx : active) {
                    if (touches_or_overlaps(primitives[idx].rect, primitives[active_idx].rect)) {
                        uf.unite(idx, active_idx);
                    }
                }
                active.push_back(idx);
            }

            std::unordered_map<int, std::vector<int>> groups;
            for (std::size_t idx = 0; idx < primitives.size(); ++idx) {
                groups[uf.find(static_cast<int>(idx))].push_back(static_cast<int>(idx));
            }
            std::vector<std::vector<int>> ordered_groups;
            ordered_groups.reserve(groups.size());
            for (auto& group_item : groups) {
                ordered_groups.push_back(std::move(group_item.second));
            }
            std::sort(ordered_groups.begin(), ordered_groups.end(), [](const std::vector<int>& lhs, const std::vector<int>& rhs) {
                return *std::min_element(lhs.begin(), lhs.end()) < *std::min_element(rhs.begin(), rhs.end());
            });

            for (const std::vector<int>& member_indices : ordered_groups) {
                std::unordered_set<std::string> pin_nets;
                bool explicit_pin_match = false;
                bool supply_fallback_match = false;
                RectD group_bbox = primitives[static_cast<std::size_t>(member_indices.front())].rect;
                for (int member_idx : member_indices) {
                    const PrimitiveRect& primitive = primitives[static_cast<std::size_t>(member_idx)];
                    group_bbox = union_rect(group_bbox, primitive.rect);
                    if (primitive.has_attached_net) {
                        pin_nets.insert(primitive.attached_net);
                        if (!primitive.pin_name.empty() &&
                            instance_pin_to_net.find(component_pin_key(instance_name, primitive.pin_name)) != instance_pin_to_net.end()) {
                            explicit_pin_match = true;
                        } else if (primitive.pin_use == "POWER" || primitive.pin_use == "GROUND") {
                            supply_fallback_match = true;
                        }
                    }
                }

                std::unordered_set<std::string> geom_nets;
                auto route_index_it = route_index_by_layer.find(normalized_layer);
                if (route_index_it != route_index_by_layer.end()) {
                    const std::vector<int> candidate_ids = query_route_candidates(&route_index_it->second, group_bbox);
                    for (int candidate_id : candidate_ids) {
                        const RouteTouchRect& candidate = route_index_it->second.rects[static_cast<std::size_t>(candidate_id)];
                        bool touches_member = false;
                        for (int member_idx : member_indices) {
                            if (touches_or_overlaps(candidate.rect, primitives[static_cast<std::size_t>(member_idx)].rect)) {
                                touches_member = true;
                                break;
                            }
                        }
                        if (touches_member) {
                            geom_nets.insert(candidate.net_name);
                        }
                    }
                }

                std::unordered_set<std::string> touched_nets = pin_nets;
                touched_nets.insert(geom_nets.begin(), geom_nets.end());
                if (touched_nets.size() != 1U) {
                    std::ostringstream error;
                    error
                        << "Component conductor resolution failed for " << instance_name
                        << " layer=" << normalized_layer
                        << " nets=[" << join_sorted_strings(touched_nets) << "]";
                    throw std::runtime_error(error.str());
                }

                const std::string conductor_name = *touched_nets.begin();
                if (!pin_nets.empty() && !geom_nets.empty()) {
                    ++prepared.component_stats[3];
                } else if (explicit_pin_match) {
                    ++prepared.component_stats[0];
                } else if (supply_fallback_match) {
                    ++prepared.component_stats[1];
                } else {
                    ++prepared.component_stats[2];
                }

                const int channel = layer_name_to_channel.at(normalized_layer);
                for (int member_idx : member_indices) {
                    const PrimitiveRect& primitive = primitives[static_cast<std::size_t>(member_idx)];
                    append_named_rect_entry(
                        &rect_entries,
                        conductor_name,
                        channel,
                        primitive.rect,
                        bounds[0],
                        bounds[1],
                        pixel_resolution,
                        target_size,
                        primitive.is_obs ? RECT_SOURCE_LEF_OBS : RECT_SOURCE_LEF_PIN
                    );
                    real_net_names.insert(conductor_name);
                }
            }
        }
    }

    std::vector<std::string> conductor_names_sorted(real_net_names.begin(), real_net_names.end());
    std::sort(conductor_names_sorted.begin(), conductor_names_sorted.end());
    if (conductor_names_sorted.size() > static_cast<std::size_t>(std::numeric_limits<std::int16_t>::max())) {
        throw std::runtime_error(
            "Prepared LEF+DEF conductors exceed int16 limit for " + def_path + ": " +
            std::to_string(conductor_names_sorted.size())
        );
    }

    std::unordered_map<std::string, int> conductor_id_map;
    conductor_id_map.reserve(conductor_names_sorted.size());
    for (std::size_t idx = 0; idx < conductor_names_sorted.size(); ++idx) {
        conductor_id_map[conductor_names_sorted[idx]] = static_cast<int>(idx) + 1;
    }

    prepared.rect_source_kind_codes.reserve(rect_entries.size());
    prepared.rect_entries.reserve(rect_entries.size());
    for (const NamedRectEntry& rect_entry : rect_entries) {
        prepared.rect_entries.push_back({
            conductor_id_map.at(rect_entry.conductor_name),
            rect_entry.channel,
            rect_entry.px_min,
            rect_entry.px_max,
            rect_entry.py_min,
            rect_entry.py_max,
            rect_entry.source_kind,
        });
        prepared.rect_source_kind_codes.push_back(rect_entry.source_kind);
    }
    prepared.conductor_names_sorted = std::move(conductor_names_sorted);
    prepared.conductor_count = static_cast<long long>(prepared.conductor_names_sorted.size());
    prepared.active_rectangles = static_cast<long long>(prepared.rect_entries.size());

    const auto prep_end = std::chrono::steady_clock::now();
    prepared.parse_ms = std::chrono::duration<double, std::milli>(parse_end - parse_start).count();
    prepared.prepare_ms = std::chrono::duration<double, std::milli>(prep_end - prep_start).count();
    return prepared;
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

py::dict prepare_def_raster_compact_py(
    const std::string& def_path,
    const std::string& lef_path,
    const std::vector<std::string>& channel_layers,
    const py::dict& layer_widths_um,
    int target_size,
    py::object pixel_resolution_obj,
    py::object raster_bounds_obj,
    bool include_supply_nets,
    bool include_conductor_names
) {
    return prepared_compact_result_to_py(
        prepare_def_raster_compact(
            def_path,
            lef_path,
            channel_layers,
            layer_widths_um,
            target_size,
            pixel_resolution_obj,
            raster_bounds_obj,
            include_supply_nets
        ),
        include_conductor_names
    );
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

py::dict parse_lef_abstracts_file(const std::string& file_path) {
    LefResultGuard lef_guard;
    char* error_message = nullptr;
    if (!lfd_parse_lef_abstracts(file_path.c_str(), &lef_guard.result, &error_message)) {
        const std::string message = error_message != nullptr ? error_message : "unknown LEF parse failure";
        lfd_free_error_message(error_message);
        throw std::runtime_error(message);
    }
    lef_guard.loaded = true;

    py::dict macro_dict;
    for (std::size_t macro_idx = 0; macro_idx < lef_guard.result.macro_count; ++macro_idx) {
        const LfdMacro& macro = lef_guard.result.macros[macro_idx];
        py::list pin_rects;
        py::list obs_rects;
        for (std::size_t rect_idx = 0; rect_idx < macro.pin_rect_count; ++rect_idx) {
            const LfdPinRect& rect = macro.pin_rects[rect_idx];
            pin_rects.append(py::make_tuple(
                rect.pin_name != nullptr ? rect.pin_name : "",
                rect.pin_use != nullptr ? rect.pin_use : "",
                rect.layer != nullptr ? rect.layer : "",
                rect.x0,
                rect.y0,
                rect.x1,
                rect.y1
            ));
        }
        for (std::size_t rect_idx = 0; rect_idx < macro.obs_rect_count; ++rect_idx) {
            const LfdObsRect& rect = macro.obs_rects[rect_idx];
            obs_rects.append(py::make_tuple(
                rect.layer != nullptr ? rect.layer : "",
                rect.x0,
                rect.y0,
                rect.x1,
                rect.y1
            ));
        }
        py::dict item;
        item["size_x"] = macro.size_x;
        item["size_y"] = macro.size_y;
        item["pin_rects"] = pin_rects;
        item["obs_rects"] = obs_rects;
        macro_dict[py::str(macro.name != nullptr ? macro.name : "")] = item;
    }

    py::dict out;
    out["macros"] = macro_dict;
    out["macro_count"] = py::int_(static_cast<long long>(lef_guard.result.macro_count));
    return out;
}

py::dict parse_def_compact(const std::string& file_path) {
    DefResultGuard def_guard;
    char* error_message = nullptr;
    if (!lfd_parse_def_compact(file_path.c_str(), &def_guard.result, &error_message)) {
        const std::string message = error_message != nullptr ? error_message : "unknown DEF parse failure";
        lfd_free_error_message(error_message);
        throw std::runtime_error(message);
    }
    def_guard.loaded = true;

    py::list components;
    py::list nets;
    py::list specialnets;

    for (std::size_t component_idx = 0; component_idx < def_guard.result.component_count; ++component_idx) {
        const LfdComponent& component = def_guard.result.components[component_idx];
        components.append(py::make_tuple(
            component.name != nullptr ? component.name : "",
            component.cell_type != nullptr ? component.cell_type : "",
            component.x,
            component.y,
            component.orient != nullptr ? component.orient : "N",
            component.status != nullptr ? component.status : "PLACED"
        ));
    }

    auto append_nets = [](py::list* dst, const LfdNet* src, std::size_t count) {
        for (std::size_t net_idx = 0; net_idx < count; ++net_idx) {
            const LfdNet& net = src[net_idx];
            py::list connections;
            py::list routing;
            for (std::size_t conn_idx = 0; conn_idx < net.connection_count; ++conn_idx) {
                const LfdConnection& conn = net.connections[conn_idx];
                connections.append(py::make_tuple(
                    conn.component != nullptr ? conn.component : "",
                    conn.pin != nullptr ? conn.pin : ""
                ));
            }
            for (std::size_t route_idx = 0; route_idx < net.routing_count; ++route_idx) {
                const LfdRoutingSegment& segment = net.routing[route_idx];
                py::list points;
                for (std::size_t point_idx = 0; point_idx < segment.point_count; ++point_idx) {
                    points.append(py::make_tuple(
                        segment.points_xy[point_idx * 2],
                        segment.points_xy[point_idx * 2 + 1]
                    ));
                }
                py::dict route_item;
                route_item["layer"] = py::str(segment.layer != nullptr ? segment.layer : "");
                route_item["points"] = points;
                route_item["has_width"] = py::bool_(segment.has_width != 0);
                route_item["width"] = segment.width;
                routing.append(route_item);
            }
            py::dict net_item;
            net_item["name"] = py::str(net.name != nullptr ? net.name : "");
            net_item["connections"] = connections;
            net_item["routing"] = routing;
            net_item["use"] = py::str(net.use != nullptr ? net.use : "SIGNAL");
            net_item["is_special"] = py::bool_(net.is_special != 0);
            dst->append(net_item);
        }
    };

    append_nets(&nets, def_guard.result.nets, def_guard.result.net_count);
    append_nets(&specialnets, def_guard.result.specialnets, def_guard.result.specialnet_count);

    py::dict out;
    out["design_name"] = py::str(def_guard.result.design_name != nullptr ? def_guard.result.design_name : "");
    out["tech"] = py::str(def_guard.result.tech_name != nullptr ? def_guard.result.tech_name : "");
    out["units"] = py::int_(def_guard.result.units);
    out["diearea"] = py::make_tuple(
        def_guard.result.diearea[0],
        def_guard.result.diearea[1],
        def_guard.result.diearea[2],
        def_guard.result.diearea[3]
    );
    out["components"] = components;
    out["nets"] = nets;
    out["specialnets"] = specialnets;
    return out;
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
    m.def("parse_lef_abstracts_file", &parse_lef_abstracts_file, "Parse LEF macro abstracts from a file");
    m.def("parse_def_compact", &parse_def_compact, "Parse the DEF subset needed by the fast LEF+DEF path");
    m.def(
        "prepare_def_raster_compact",
        &prepare_def_raster_compact_py,
        py::arg("def_path"),
        py::arg("lef_path"),
        py::arg("channel_layers"),
        py::arg("layer_widths_um"),
        py::arg("target_size"),
        py::arg("pixel_resolution") = py::none(),
        py::arg("raster_bounds") = py::none(),
        py::arg("include_supply_nets") = true,
        py::arg("include_conductor_names") = true,
        "Prepare compact LEF+DEF raster inputs"
    );
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
        "Prepare compact LEF+DEF raster inputs using compiled cell recipes"
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
