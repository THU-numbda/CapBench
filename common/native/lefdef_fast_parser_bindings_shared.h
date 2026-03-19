#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>

enum RectSourceKindCode : std::uint8_t {
    RECT_SOURCE_ROUTE = 0,
    RECT_SOURCE_SPECIAL_ROUTE = 1,
    RECT_SOURCE_LEF_PIN = 2,
    RECT_SOURCE_LEF_OBS = 3,
};

struct RectD {
    double x0;
    double x1;
    double y0;
    double y1;
};

struct RectEntry {
    int conductor_id;
    int channel;
    int px_min;
    int px_max;
    int py_min;
    int py_max;
    std::uint8_t source_kind;
};

struct NamedRectEntry {
    std::string conductor_name;
    int channel;
    int px_min;
    int px_max;
    int py_min;
    int py_max;
    std::uint8_t source_kind;
};

struct PreparedCompactResult {
    std::vector<RectEntry> rect_entries;
    std::vector<std::string> conductor_names_sorted;
    std::vector<std::uint8_t> rect_source_kind_codes;
    std::array<double, 6> window_bounds{};
    double pixel_resolution = 0.0;
    double parse_ms = 0.0;
    double prepare_ms = 0.0;
    long long total_segments = 0;
    long long total_endpoint_extensions = 0;
    long long active_rectangles = 0;
    long long real_conductor_count = 0;
    long long conductor_count = 0;
    std::array<long long, 6> component_stats{{0, 0, 0, 0, 0, 0}};
};
