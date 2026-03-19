#pragma once

#include <cstddef>
#include <cstdint>
#include <iterator>

namespace capbench_compiled_recipes {

enum class BindingKind : std::uint8_t {
    kPinNet = 0,
    kSupplyNet = 1,
    kSyntheticNet = 2,
};

struct RectSpec {
    const char* layer;
    double x0;
    double y0;
    double x1;
    double y1;
    bool is_obs = false;
};

struct GroupSpec {
    BindingKind binding_kind;
    const char* binding_name;
    const RectSpec* rects;
    std::size_t rect_count;
};

struct MacroSpec {
    const char* macro_name;
    double size_x;
    double size_y;
    const GroupSpec* groups;
    std::size_t group_count;
};

// Generated from tech/nangate45.lef.

inline constexpr RectSpec kNangateAND2X1PinA1[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateAND2X1PinA2[] = {
    {"metal1", 0.25, 0.525, 0.38, 0.7},
};

inline constexpr RectSpec kNangateAND2X1PinZN[] = {
    {"metal1", 0.61, 0.19, 0.7, 1.25},
};

inline constexpr RectSpec kNangateAND2X1Power[] = {
    {"metal1", 0.0, 1.315, 0.76, 1.485},
    {"metal1", 0.415, 0.975, 0.485, 1.485},
    {"metal1", 0.04, 0.975, 0.11, 1.485},
};

inline constexpr RectSpec kNangateAND2X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.76, 0.085},
    {"metal1", 0.415, -0.085, 0.485, 0.325},
};

inline constexpr RectSpec kNangateAND2X1ObsGroup0[] = {
    {"metal1", 0.235, 0.84, 0.305, 1.25, true},
    {"metal1", 0.235, 0.84, 0.54, 0.91, true},
    {"metal1", 0.47, 0.39, 0.54, 0.91, true},
    {"metal1", 0.045, 0.39, 0.54, 0.46, true},
    {"metal1", 0.045, 0.19, 0.115, 0.46, true},
};

inline constexpr GroupSpec kNangateAND2X1Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateAND2X1PinA1, std::size(kNangateAND2X1PinA1)},
    {BindingKind::kPinNet, "A2", kNangateAND2X1PinA2, std::size(kNangateAND2X1PinA2)},
    {BindingKind::kPinNet, "ZN", kNangateAND2X1PinZN, std::size(kNangateAND2X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAND2X1Power, std::size(kNangateAND2X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAND2X1Ground, std::size(kNangateAND2X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAND2X1ObsGroup0, std::size(kNangateAND2X1ObsGroup0)},
};

inline constexpr RectSpec kNangateAND2X2PinA1[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateAND2X2PinA2[] = {
    {"metal1", 0.25, 0.525, 0.38, 0.7},
};

inline constexpr RectSpec kNangateAND2X2PinZN[] = {
    {"metal1", 0.615, 0.15, 0.7, 1.25},
};

inline constexpr RectSpec kNangateAND2X2Power[] = {
    {"metal1", 0.0, 1.315, 0.95, 1.485},
    {"metal1", 0.795, 0.975, 0.865, 1.485},
    {"metal1", 0.415, 0.975, 0.485, 1.485},
    {"metal1", 0.04, 0.975, 0.11, 1.485},
};

inline constexpr RectSpec kNangateAND2X2Ground[] = {
    {"metal1", 0.0, -0.085, 0.95, 0.085},
    {"metal1", 0.795, -0.085, 0.865, 0.425},
    {"metal1", 0.415, -0.085, 0.485, 0.285},
};

inline constexpr RectSpec kNangateAND2X2ObsGroup0[] = {
    {"metal1", 0.235, 0.84, 0.305, 1.25, true},
    {"metal1", 0.235, 0.84, 0.545, 0.91, true},
    {"metal1", 0.475, 0.39, 0.545, 0.91, true},
    {"metal1", 0.045, 0.39, 0.545, 0.46, true},
    {"metal1", 0.045, 0.15, 0.115, 0.46, true},
};

inline constexpr GroupSpec kNangateAND2X2Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateAND2X2PinA1, std::size(kNangateAND2X2PinA1)},
    {BindingKind::kPinNet, "A2", kNangateAND2X2PinA2, std::size(kNangateAND2X2PinA2)},
    {BindingKind::kPinNet, "ZN", kNangateAND2X2PinZN, std::size(kNangateAND2X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAND2X2Power, std::size(kNangateAND2X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAND2X2Ground, std::size(kNangateAND2X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAND2X2ObsGroup0, std::size(kNangateAND2X2ObsGroup0)},
};

inline constexpr RectSpec kNangateAND2X4PinA1[] = {
    {"metal1", 0.25, 0.42, 0.38, 0.66},
};

inline constexpr RectSpec kNangateAND2X4PinA2[] = {
    {"metal1", 0.06, 0.725, 0.76, 0.795},
    {"metal1", 0.69, 0.525, 0.76, 0.795},
    {"metal1", 0.06, 0.42, 0.185, 0.795},
};

inline constexpr RectSpec kNangateAND2X4PinZN[] = {
    {"metal1", 1.365, 0.15, 1.435, 1.25},
    {"metal1", 0.995, 0.68, 1.435, 0.75},
    {"metal1", 0.995, 0.15, 1.08, 1.25},
};

inline constexpr RectSpec kNangateAND2X4Power[] = {
    {"metal1", 0.0, 1.315, 1.71, 1.485},
    {"metal1", 1.555, 0.995, 1.625, 1.485},
    {"metal1", 1.175, 0.995, 1.245, 1.485},
    {"metal1", 0.795, 0.995, 0.865, 1.485},
    {"metal1", 0.415, 0.995, 0.485, 1.485},
    {"metal1", 0.04, 0.995, 0.11, 1.485},
};

inline constexpr RectSpec kNangateAND2X4Ground[] = {
    {"metal1", 0.0, -0.085, 1.71, 0.085},
    {"metal1", 1.555, -0.085, 1.625, 0.355},
    {"metal1", 1.175, -0.085, 1.245, 0.355},
    {"metal1", 0.795, -0.085, 0.865, 0.215},
    {"metal1", 0.04, -0.085, 0.11, 0.355},
};

inline constexpr RectSpec kNangateAND2X4ObsGroup0[] = {
    {"metal1", 0.605, 0.86, 0.675, 1.25, true},
    {"metal1", 0.235, 0.86, 0.305, 1.25, true},
    {"metal1", 0.235, 0.86, 0.92, 0.93, true},
    {"metal1", 0.85, 0.285, 0.92, 0.93, true},
    {"metal1", 0.425, 0.285, 0.92, 0.355, true},
    {"metal1", 0.425, 0.22, 0.495, 0.355, true},
};

inline constexpr GroupSpec kNangateAND2X4Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateAND2X4PinA1, std::size(kNangateAND2X4PinA1)},
    {BindingKind::kPinNet, "A2", kNangateAND2X4PinA2, std::size(kNangateAND2X4PinA2)},
    {BindingKind::kPinNet, "ZN", kNangateAND2X4PinZN, std::size(kNangateAND2X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAND2X4Power, std::size(kNangateAND2X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAND2X4Ground, std::size(kNangateAND2X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAND2X4ObsGroup0, std::size(kNangateAND2X4ObsGroup0)},
};

inline constexpr RectSpec kNangateAND3X1PinA1[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateAND3X1PinA2[] = {
    {"metal1", 0.25, 0.525, 0.375, 0.7},
};

inline constexpr RectSpec kNangateAND3X1PinA3[] = {
    {"metal1", 0.44, 0.525, 0.57, 0.7},
};

inline constexpr RectSpec kNangateAND3X1PinZN[] = {
    {"metal1", 0.8, 0.975, 0.89, 1.25},
    {"metal1", 0.82, 0.15, 0.89, 1.25},
    {"metal1", 0.8, 0.15, 0.89, 0.425},
};

inline constexpr RectSpec kNangateAND3X1Power[] = {
    {"metal1", 0.0, 1.315, 0.95, 1.485},
    {"metal1", 0.605, 1.0, 0.675, 1.485},
    {"metal1", 0.225, 1.04, 0.295, 1.485},
};

inline constexpr RectSpec kNangateAND3X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.95, 0.085},
    {"metal1", 0.605, -0.085, 0.675, 0.285},
};

inline constexpr RectSpec kNangateAND3X1ObsGroup0[] = {
    {"metal1", 0.415, 0.865, 0.485, 1.25, true},
    {"metal1", 0.045, 0.865, 0.115, 1.25, true},
    {"metal1", 0.045, 0.865, 0.705, 0.935, true},
    {"metal1", 0.635, 0.35, 0.705, 0.935, true},
    {"metal1", 0.635, 0.525, 0.755, 0.66, true},
    {"metal1", 0.045, 0.35, 0.705, 0.42, true},
    {"metal1", 0.045, 0.15, 0.115, 0.42, true},
};

inline constexpr GroupSpec kNangateAND3X1Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateAND3X1PinA1, std::size(kNangateAND3X1PinA1)},
    {BindingKind::kPinNet, "A2", kNangateAND3X1PinA2, std::size(kNangateAND3X1PinA2)},
    {BindingKind::kPinNet, "A3", kNangateAND3X1PinA3, std::size(kNangateAND3X1PinA3)},
    {BindingKind::kPinNet, "ZN", kNangateAND3X1PinZN, std::size(kNangateAND3X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAND3X1Power, std::size(kNangateAND3X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAND3X1Ground, std::size(kNangateAND3X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAND3X1ObsGroup0, std::size(kNangateAND3X1ObsGroup0)},
};

inline constexpr RectSpec kNangateAND3X2PinA1[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateAND3X2PinA2[] = {
    {"metal1", 0.25, 0.525, 0.375, 0.7},
};

inline constexpr RectSpec kNangateAND3X2PinA3[] = {
    {"metal1", 0.44, 0.525, 0.57, 0.7},
};

inline constexpr RectSpec kNangateAND3X2PinZN[] = {
    {"metal1", 0.805, 0.15, 0.89, 1.25},
};

inline constexpr RectSpec kNangateAND3X2Power[] = {
    {"metal1", 0.0, 1.315, 1.14, 1.485},
    {"metal1", 0.99, 0.975, 1.06, 1.485},
    {"metal1", 0.605, 0.975, 0.675, 1.485},
    {"metal1", 0.225, 0.975, 0.295, 1.485},
};

inline constexpr RectSpec kNangateAND3X2Ground[] = {
    {"metal1", 0.0, -0.085, 1.14, 0.085},
    {"metal1", 0.99, -0.085, 1.06, 0.425},
    {"metal1", 0.605, -0.085, 0.675, 0.285},
};

inline constexpr RectSpec kNangateAND3X2ObsGroup0[] = {
    {"metal1", 0.415, 0.8, 0.485, 1.25, true},
    {"metal1", 0.045, 0.8, 0.115, 1.25, true},
    {"metal1", 0.045, 0.8, 0.735, 0.87, true},
    {"metal1", 0.665, 0.355, 0.735, 0.87, true},
    {"metal1", 0.045, 0.355, 0.735, 0.425, true},
    {"metal1", 0.045, 0.15, 0.115, 0.425, true},
};

inline constexpr GroupSpec kNangateAND3X2Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateAND3X2PinA1, std::size(kNangateAND3X2PinA1)},
    {BindingKind::kPinNet, "A2", kNangateAND3X2PinA2, std::size(kNangateAND3X2PinA2)},
    {BindingKind::kPinNet, "A3", kNangateAND3X2PinA3, std::size(kNangateAND3X2PinA3)},
    {BindingKind::kPinNet, "ZN", kNangateAND3X2PinZN, std::size(kNangateAND3X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAND3X2Power, std::size(kNangateAND3X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAND3X2Ground, std::size(kNangateAND3X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAND3X2ObsGroup0, std::size(kNangateAND3X2ObsGroup0)},
};

inline constexpr RectSpec kNangateAND3X4PinA1[] = {
    {"metal1", 0.595, 0.555, 0.73, 0.7},
};

inline constexpr RectSpec kNangateAND3X4PinA2[] = {
    {"metal1", 0.82, 0.42, 0.95, 0.7},
    {"metal1", 0.34, 0.42, 0.95, 0.49},
    {"metal1", 0.34, 0.42, 0.41, 0.66},
};

inline constexpr RectSpec kNangateAND3X4PinA3[] = {
    {"metal1", 0.12, 0.765, 1.14, 0.835},
    {"metal1", 1.07, 0.525, 1.14, 0.835},
    {"metal1", 0.12, 0.525, 0.19, 0.835},
    {"metal1", 0.06, 0.525, 0.19, 0.7},
};

inline constexpr RectSpec kNangateAND3X4PinZN[] = {
    {"metal1", 1.745, 0.15, 1.815, 1.25},
    {"metal1", 1.375, 0.56, 1.815, 0.7},
    {"metal1", 1.375, 0.15, 1.445, 1.25},
};

inline constexpr RectSpec kNangateAND3X4Power[] = {
    {"metal1", 0.0, 1.315, 2.09, 1.485},
    {"metal1", 1.935, 1.035, 2.005, 1.485},
    {"metal1", 1.555, 1.035, 1.625, 1.485},
    {"metal1", 1.175, 1.035, 1.245, 1.485},
    {"metal1", 0.795, 1.035, 0.865, 1.485},
    {"metal1", 0.415, 1.035, 0.485, 1.485},
    {"metal1", 0.04, 1.035, 0.11, 1.485},
};

inline constexpr RectSpec kNangateAND3X4Ground[] = {
    {"metal1", 0.0, -0.085, 2.09, 0.085},
    {"metal1", 1.935, -0.085, 2.005, 0.425},
    {"metal1", 1.555, -0.085, 1.625, 0.425},
    {"metal1", 1.175, -0.085, 1.245, 0.195},
    {"metal1", 0.04, -0.085, 0.11, 0.425},
};

inline constexpr RectSpec kNangateAND3X4ObsGroup0[] = {
    {"metal1", 0.985, 0.9, 1.055, 1.25, true},
    {"metal1", 0.605, 0.9, 0.675, 1.25, true},
    {"metal1", 0.235, 0.9, 0.305, 1.25, true},
    {"metal1", 0.235, 0.9, 1.305, 0.97, true},
    {"metal1", 1.235, 0.26, 1.305, 0.97, true},
    {"metal1", 0.615, 0.26, 1.305, 0.33, true},
    {"metal1", 0.615, 0.15, 0.685, 0.33, true},
};

inline constexpr GroupSpec kNangateAND3X4Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateAND3X4PinA1, std::size(kNangateAND3X4PinA1)},
    {BindingKind::kPinNet, "A2", kNangateAND3X4PinA2, std::size(kNangateAND3X4PinA2)},
    {BindingKind::kPinNet, "A3", kNangateAND3X4PinA3, std::size(kNangateAND3X4PinA3)},
    {BindingKind::kPinNet, "ZN", kNangateAND3X4PinZN, std::size(kNangateAND3X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAND3X4Power, std::size(kNangateAND3X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAND3X4Ground, std::size(kNangateAND3X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAND3X4ObsGroup0, std::size(kNangateAND3X4ObsGroup0)},
};

inline constexpr RectSpec kNangateAND4X1PinA1[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateAND4X1PinA2[] = {
    {"metal1", 0.25, 0.525, 0.375, 0.7},
};

inline constexpr RectSpec kNangateAND4X1PinA3[] = {
    {"metal1", 0.44, 0.525, 0.565, 0.7},
};

inline constexpr RectSpec kNangateAND4X1PinA4[] = {
    {"metal1", 0.63, 0.525, 0.76, 0.7},
};

inline constexpr RectSpec kNangateAND4X1PinZN[] = {
    {"metal1", 0.99, 0.15, 1.08, 1.25},
};

inline constexpr RectSpec kNangateAND4X1Power[] = {
    {"metal1", 0.0, 1.315, 1.14, 1.485},
    {"metal1", 0.795, 0.975, 0.865, 1.485},
    {"metal1", 0.415, 0.975, 0.485, 1.485},
    {"metal1", 0.04, 0.975, 0.11, 1.485},
};

inline constexpr RectSpec kNangateAND4X1Ground[] = {
    {"metal1", 0.0, -0.085, 1.14, 0.085},
    {"metal1", 0.795, -0.085, 0.865, 0.285},
};

inline constexpr RectSpec kNangateAND4X1ObsGroup0[] = {
    {"metal1", 0.605, 0.84, 0.675, 1.25, true},
    {"metal1", 0.235, 0.84, 0.305, 1.25, true},
    {"metal1", 0.235, 0.84, 0.925, 0.91, true},
    {"metal1", 0.855, 0.35, 0.925, 0.91, true},
    {"metal1", 0.045, 0.35, 0.925, 0.42, true},
    {"metal1", 0.045, 0.15, 0.115, 0.42, true},
};

inline constexpr GroupSpec kNangateAND4X1Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateAND4X1PinA1, std::size(kNangateAND4X1PinA1)},
    {BindingKind::kPinNet, "A2", kNangateAND4X1PinA2, std::size(kNangateAND4X1PinA2)},
    {BindingKind::kPinNet, "A3", kNangateAND4X1PinA3, std::size(kNangateAND4X1PinA3)},
    {BindingKind::kPinNet, "A4", kNangateAND4X1PinA4, std::size(kNangateAND4X1PinA4)},
    {BindingKind::kPinNet, "ZN", kNangateAND4X1PinZN, std::size(kNangateAND4X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAND4X1Power, std::size(kNangateAND4X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAND4X1Ground, std::size(kNangateAND4X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAND4X1ObsGroup0, std::size(kNangateAND4X1ObsGroup0)},
};

inline constexpr RectSpec kNangateAND4X2PinA1[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateAND4X2PinA2[] = {
    {"metal1", 0.25, 0.525, 0.375, 0.7},
};

inline constexpr RectSpec kNangateAND4X2PinA3[] = {
    {"metal1", 0.44, 0.525, 0.565, 0.7},
};

inline constexpr RectSpec kNangateAND4X2PinA4[] = {
    {"metal1", 0.63, 0.525, 0.76, 0.7},
};

inline constexpr RectSpec kNangateAND4X2PinZN[] = {
    {"metal1", 0.995, 0.15, 1.08, 1.25},
};

inline constexpr RectSpec kNangateAND4X2Power[] = {
    {"metal1", 0.0, 1.315, 1.33, 1.485},
    {"metal1", 1.18, 0.975, 1.25, 1.485},
    {"metal1", 0.795, 0.975, 0.865, 1.485},
    {"metal1", 0.415, 0.975, 0.485, 1.485},
    {"metal1", 0.04, 0.975, 0.11, 1.485},
};

inline constexpr RectSpec kNangateAND4X2Ground[] = {
    {"metal1", 0.0, -0.085, 1.33, 0.085},
    {"metal1", 1.18, -0.085, 1.25, 0.425},
    {"metal1", 0.795, -0.085, 0.865, 0.27},
};

inline constexpr RectSpec kNangateAND4X2ObsGroup0[] = {
    {"metal1", 0.605, 0.8, 0.675, 1.25, true},
    {"metal1", 0.235, 0.8, 0.305, 1.25, true},
    {"metal1", 0.235, 0.8, 0.925, 0.87, true},
    {"metal1", 0.855, 0.355, 0.925, 0.87, true},
    {"metal1", 0.045, 0.355, 0.925, 0.425, true},
    {"metal1", 0.045, 0.15, 0.115, 0.425, true},
};

inline constexpr GroupSpec kNangateAND4X2Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateAND4X2PinA1, std::size(kNangateAND4X2PinA1)},
    {BindingKind::kPinNet, "A2", kNangateAND4X2PinA2, std::size(kNangateAND4X2PinA2)},
    {BindingKind::kPinNet, "A3", kNangateAND4X2PinA3, std::size(kNangateAND4X2PinA3)},
    {BindingKind::kPinNet, "A4", kNangateAND4X2PinA4, std::size(kNangateAND4X2PinA4)},
    {BindingKind::kPinNet, "ZN", kNangateAND4X2PinZN, std::size(kNangateAND4X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAND4X2Power, std::size(kNangateAND4X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAND4X2Ground, std::size(kNangateAND4X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAND4X2ObsGroup0, std::size(kNangateAND4X2ObsGroup0)},
};

inline constexpr RectSpec kNangateAND4X4PinA1[] = {
    {"metal1", 0.8, 0.56, 0.935, 0.7},
};

inline constexpr RectSpec kNangateAND4X4PinA2[] = {
    {"metal1", 1.065, 0.425, 1.135, 0.66},
    {"metal1", 0.565, 0.425, 1.135, 0.495},
    {"metal1", 0.565, 0.425, 0.7, 0.7},
};

inline constexpr RectSpec kNangateAND4X4PinA3[] = {
    {"metal1", 0.355, 0.77, 1.345, 0.84},
    {"metal1", 1.2, 0.525, 1.345, 0.84},
    {"metal1", 0.355, 0.525, 0.425, 0.84},
};

inline constexpr RectSpec kNangateAND4X4PinA4[] = {
    {"metal1", 0.135, 0.905, 1.535, 0.975},
    {"metal1", 1.465, 0.525, 1.535, 0.975},
    {"metal1", 0.135, 0.525, 0.205, 0.975},
    {"metal1", 0.06, 0.525, 0.205, 0.7},
};

inline constexpr RectSpec kNangateAND4X4PinZN[] = {
    {"metal1", 2.14, 0.15, 2.21, 0.925},
    {"metal1", 1.77, 0.56, 2.21, 0.7},
    {"metal1", 1.77, 0.15, 1.84, 0.925},
};

inline constexpr RectSpec kNangateAND4X4Power[] = {
    {"metal1", 0.0, 1.315, 2.47, 1.485},
    {"metal1", 2.33, 1.065, 2.4, 1.485},
    {"metal1", 1.95, 1.065, 2.02, 1.485},
    {"metal1", 1.57, 1.175, 1.64, 1.485},
    {"metal1", 1.19, 1.175, 1.26, 1.485},
    {"metal1", 0.81, 1.175, 0.88, 1.485},
    {"metal1", 0.43, 1.175, 0.5, 1.485},
    {"metal1", 0.055, 1.065, 0.125, 1.485},
};

inline constexpr RectSpec kNangateAND4X4Ground[] = {
    {"metal1", 0.0, -0.085, 2.47, 0.085},
    {"metal1", 2.33, -0.085, 2.4, 0.425},
    {"metal1", 1.95, -0.085, 2.02, 0.425},
    {"metal1", 1.57, -0.085, 1.64, 0.195},
    {"metal1", 0.055, -0.085, 0.125, 0.425},
};

inline constexpr RectSpec kNangateAND4X4ObsGroup0[] = {
    {"metal1", 0.215, 1.04, 1.705, 1.11, true},
    {"metal1", 1.635, 0.29, 1.705, 1.11, true},
    {"metal1", 0.785, 0.29, 1.705, 0.36, true},
};

inline constexpr GroupSpec kNangateAND4X4Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateAND4X4PinA1, std::size(kNangateAND4X4PinA1)},
    {BindingKind::kPinNet, "A2", kNangateAND4X4PinA2, std::size(kNangateAND4X4PinA2)},
    {BindingKind::kPinNet, "A3", kNangateAND4X4PinA3, std::size(kNangateAND4X4PinA3)},
    {BindingKind::kPinNet, "A4", kNangateAND4X4PinA4, std::size(kNangateAND4X4PinA4)},
    {BindingKind::kPinNet, "ZN", kNangateAND4X4PinZN, std::size(kNangateAND4X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAND4X4Power, std::size(kNangateAND4X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAND4X4Ground, std::size(kNangateAND4X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAND4X4ObsGroup0, std::size(kNangateAND4X4ObsGroup0)},
};

inline constexpr RectSpec kNangateANTENNAX1PinA[] = {
    {"metal1", 0.06, 0.42, 0.13, 0.75},
};

inline constexpr RectSpec kNangateANTENNAX1Power[] = {
    {"metal1", 0.0, 1.315, 0.19, 1.485},
};

inline constexpr RectSpec kNangateANTENNAX1Ground[] = {
    {"metal1", 0.0, -0.085, 0.19, 0.085},
};

inline constexpr GroupSpec kNangateANTENNAX1Groups[] = {
    {BindingKind::kPinNet, "A", kNangateANTENNAX1PinA, std::size(kNangateANTENNAX1PinA)},
    {BindingKind::kSupplyNet, "POWER", kNangateANTENNAX1Power, std::size(kNangateANTENNAX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateANTENNAX1Ground, std::size(kNangateANTENNAX1Ground)},
};

inline constexpr RectSpec kNangateAOI211X1PinA[] = {
    {"metal1", 0.765, 0.525, 0.89, 0.7},
};

inline constexpr RectSpec kNangateAOI211X1PinB[] = {
    {"metal1", 0.575, 0.525, 0.7, 0.7},
};

inline constexpr RectSpec kNangateAOI211X1PinC1[] = {
    {"metal1", 0.41, 0.525, 0.51, 0.7},
};

inline constexpr RectSpec kNangateAOI211X1PinC2[] = {
    {"metal1", 0.06, 0.525, 0.21, 0.7},
};

inline constexpr RectSpec kNangateAOI211X1PinZN[] = {
    {"metal1", 0.275, 0.355, 0.905, 0.425},
    {"metal1", 0.835, 0.15, 0.905, 0.425},
    {"metal1", 0.44, 0.15, 0.525, 0.425},
    {"metal1", 0.275, 0.355, 0.345, 1.115},
};

inline constexpr RectSpec kNangateAOI211X1Power[] = {
    {"metal1", 0.0, 1.315, 0.95, 1.485},
    {"metal1", 0.835, 0.905, 0.905, 1.485},
};

inline constexpr RectSpec kNangateAOI211X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.95, 0.085},
    {"metal1", 0.645, -0.085, 0.715, 0.285},
    {"metal1", 0.08, -0.085, 0.15, 0.425},
};

inline constexpr RectSpec kNangateAOI211X1ObsGroup0[] = {
    {"metal1", 0.085, 1.18, 0.525, 1.25, true},
    {"metal1", 0.455, 0.905, 0.525, 1.25, true},
    {"metal1", 0.085, 0.905, 0.155, 1.25, true},
};

inline constexpr GroupSpec kNangateAOI211X1Groups[] = {
    {BindingKind::kPinNet, "A", kNangateAOI211X1PinA, std::size(kNangateAOI211X1PinA)},
    {BindingKind::kPinNet, "B", kNangateAOI211X1PinB, std::size(kNangateAOI211X1PinB)},
    {BindingKind::kPinNet, "C1", kNangateAOI211X1PinC1, std::size(kNangateAOI211X1PinC1)},
    {BindingKind::kPinNet, "C2", kNangateAOI211X1PinC2, std::size(kNangateAOI211X1PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateAOI211X1PinZN, std::size(kNangateAOI211X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAOI211X1Power, std::size(kNangateAOI211X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAOI211X1Ground, std::size(kNangateAOI211X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAOI211X1ObsGroup0, std::size(kNangateAOI211X1ObsGroup0)},
};

inline constexpr RectSpec kNangateAOI211X2PinA[] = {
    {"metal1", 0.39, 0.56, 0.525, 0.7},
};

inline constexpr RectSpec kNangateAOI211X2PinB[] = {
    {"metal1", 0.06, 0.765, 0.75, 0.835},
    {"metal1", 0.68, 0.525, 0.75, 0.835},
    {"metal1", 0.06, 0.525, 0.185, 0.835},
};

inline constexpr RectSpec kNangateAOI211X2PinC1[] = {
    {"metal1", 1.19, 0.56, 1.325, 0.7},
};

inline constexpr RectSpec kNangateAOI211X2PinC2[] = {
    {"metal1", 1.54, 0.425, 1.65, 0.7},
    {"metal1", 0.965, 0.425, 1.65, 0.495},
    {"metal1", 0.965, 0.425, 1.035, 0.66},
};

inline constexpr RectSpec kNangateAOI211X2PinZN[] = {
    {"metal1", 1.405, 0.765, 1.475, 1.055},
    {"metal1", 0.82, 0.765, 1.475, 0.835},
    {"metal1", 0.2, 0.285, 1.32, 0.355},
    {"metal1", 1.185, 0.15, 1.32, 0.355},
    {"metal1", 1.025, 0.765, 1.095, 1.055},
    {"metal1", 0.82, 0.285, 0.89, 0.835},
    {"metal1", 0.2, 0.15, 0.335, 0.355},
};

inline constexpr RectSpec kNangateAOI211X2Power[] = {
    {"metal1", 0.0, 1.315, 1.71, 1.485},
    {"metal1", 0.42, 1.035, 0.49, 1.485},
};

inline constexpr RectSpec kNangateAOI211X2Ground[] = {
    {"metal1", 0.0, -0.085, 1.71, 0.085},
    {"metal1", 1.595, -0.085, 1.665, 0.355},
    {"metal1", 0.825, -0.085, 0.895, 0.215},
    {"metal1", 0.43, -0.085, 0.5, 0.215},
    {"metal1", 0.045, -0.085, 0.115, 0.355},
};

inline constexpr RectSpec kNangateAOI211X2ObsGroup0[] = {
    {"metal1", 0.815, 1.18, 1.665, 1.25, true},
    {"metal1", 1.595, 0.975, 1.665, 1.25, true},
    {"metal1", 0.05, 0.9, 0.12, 1.25, true},
    {"metal1", 1.22, 0.975, 1.29, 1.25, true},
    {"metal1", 0.815, 0.9, 0.885, 1.25, true},
    {"metal1", 0.05, 0.9, 0.885, 0.97, true},
};

inline constexpr GroupSpec kNangateAOI211X2Groups[] = {
    {BindingKind::kPinNet, "A", kNangateAOI211X2PinA, std::size(kNangateAOI211X2PinA)},
    {BindingKind::kPinNet, "B", kNangateAOI211X2PinB, std::size(kNangateAOI211X2PinB)},
    {BindingKind::kPinNet, "C1", kNangateAOI211X2PinC1, std::size(kNangateAOI211X2PinC1)},
    {BindingKind::kPinNet, "C2", kNangateAOI211X2PinC2, std::size(kNangateAOI211X2PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateAOI211X2PinZN, std::size(kNangateAOI211X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAOI211X2Power, std::size(kNangateAOI211X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAOI211X2Ground, std::size(kNangateAOI211X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAOI211X2ObsGroup0, std::size(kNangateAOI211X2ObsGroup0)},
};

inline constexpr RectSpec kNangateAOI211X4PinA[] = {
    {"metal1", 0.63, 0.525, 0.76, 0.7},
};

inline constexpr RectSpec kNangateAOI211X4PinB[] = {
    {"metal1", 0.44, 0.525, 0.565, 0.7},
};

inline constexpr RectSpec kNangateAOI211X4PinC1[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateAOI211X4PinC2[] = {
    {"metal1", 0.25, 0.525, 0.375, 0.7},
};

inline constexpr RectSpec kNangateAOI211X4PinZN[] = {
    {"metal1", 1.75, 0.15, 1.82, 1.175},
    {"metal1", 1.375, 0.56, 1.82, 0.7},
    {"metal1", 1.375, 0.15, 1.445, 1.175},
};

inline constexpr RectSpec kNangateAOI211X4Power[] = {
    {"metal1", 0.0, 1.315, 2.09, 1.485},
    {"metal1", 1.935, 0.9, 2.005, 1.485},
    {"metal1", 1.555, 0.9, 1.625, 1.485},
    {"metal1", 1.175, 0.9, 1.245, 1.485},
    {"metal1", 0.795, 0.9, 0.865, 1.485},
};

inline constexpr RectSpec kNangateAOI211X4Ground[] = {
    {"metal1", 0.0, -0.085, 2.09, 0.085},
    {"metal1", 1.935, -0.085, 2.005, 0.425},
    {"metal1", 1.555, -0.085, 1.625, 0.425},
    {"metal1", 1.175, -0.085, 1.245, 0.425},
    {"metal1", 0.795, -0.085, 0.865, 0.285},
    {"metal1", 0.415, -0.085, 0.485, 0.285},
};

inline constexpr RectSpec kNangateAOI211X4ObsGroup0[] = {
    {"metal1", 0.995, 0.15, 1.065, 1.175, true},
    {"metal1", 0.995, 0.525, 1.31, 0.66, true},
};

inline constexpr RectSpec kNangateAOI211X4ObsGroup1[] = {
    {"metal1", 0.235, 0.765, 0.305, 1.115, true},
    {"metal1", 0.235, 0.765, 0.93, 0.835, true},
    {"metal1", 0.86, 0.39, 0.93, 0.835, true},
    {"metal1", 0.045, 0.39, 0.93, 0.46, true},
    {"metal1", 0.605, 0.15, 0.675, 0.46, true},
    {"metal1", 0.045, 0.15, 0.115, 0.46, true},
};

inline constexpr RectSpec kNangateAOI211X4ObsGroup2[] = {
    {"metal1", 0.045, 1.18, 0.485, 1.25, true},
    {"metal1", 0.415, 0.9, 0.485, 1.25, true},
    {"metal1", 0.045, 0.9, 0.115, 1.25, true},
};

inline constexpr GroupSpec kNangateAOI211X4Groups[] = {
    {BindingKind::kPinNet, "A", kNangateAOI211X4PinA, std::size(kNangateAOI211X4PinA)},
    {BindingKind::kPinNet, "B", kNangateAOI211X4PinB, std::size(kNangateAOI211X4PinB)},
    {BindingKind::kPinNet, "C1", kNangateAOI211X4PinC1, std::size(kNangateAOI211X4PinC1)},
    {BindingKind::kPinNet, "C2", kNangateAOI211X4PinC2, std::size(kNangateAOI211X4PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateAOI211X4PinZN, std::size(kNangateAOI211X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAOI211X4Power, std::size(kNangateAOI211X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAOI211X4Ground, std::size(kNangateAOI211X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAOI211X4ObsGroup0, std::size(kNangateAOI211X4ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateAOI211X4ObsGroup1, std::size(kNangateAOI211X4ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateAOI211X4ObsGroup2, std::size(kNangateAOI211X4ObsGroup2)},
};

inline constexpr RectSpec kNangateAOI21X1PinA[] = {
    {"metal1", 0.575, 0.525, 0.7, 0.7},
};

inline constexpr RectSpec kNangateAOI21X1PinB1[] = {
    {"metal1", 0.4, 0.525, 0.51, 0.7},
};

inline constexpr RectSpec kNangateAOI21X1PinB2[] = {
    {"metal1", 0.06, 0.525, 0.2, 0.7},
};

inline constexpr RectSpec kNangateAOI21X1PinZN[] = {
    {"metal1", 0.265, 0.355, 0.525, 0.425},
    {"metal1", 0.44, 0.15, 0.525, 0.425},
    {"metal1", 0.265, 0.355, 0.335, 1.115},
};

inline constexpr RectSpec kNangateAOI21X1Power[] = {
    {"metal1", 0.0, 1.315, 0.76, 1.485},
    {"metal1", 0.645, 0.905, 0.715, 1.485},
};

inline constexpr RectSpec kNangateAOI21X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.76, 0.085},
    {"metal1", 0.645, -0.085, 0.715, 0.355},
    {"metal1", 0.08, -0.085, 0.15, 0.425},
};

inline constexpr RectSpec kNangateAOI21X1ObsGroup0[] = {
    {"metal1", 0.085, 1.18, 0.525, 1.25, true},
    {"metal1", 0.455, 0.905, 0.525, 1.25, true},
    {"metal1", 0.085, 0.905, 0.155, 1.25, true},
};

inline constexpr GroupSpec kNangateAOI21X1Groups[] = {
    {BindingKind::kPinNet, "A", kNangateAOI21X1PinA, std::size(kNangateAOI21X1PinA)},
    {BindingKind::kPinNet, "B1", kNangateAOI21X1PinB1, std::size(kNangateAOI21X1PinB1)},
    {BindingKind::kPinNet, "B2", kNangateAOI21X1PinB2, std::size(kNangateAOI21X1PinB2)},
    {BindingKind::kPinNet, "ZN", kNangateAOI21X1PinZN, std::size(kNangateAOI21X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAOI21X1Power, std::size(kNangateAOI21X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAOI21X1Ground, std::size(kNangateAOI21X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAOI21X1ObsGroup0, std::size(kNangateAOI21X1ObsGroup0)},
};

inline constexpr RectSpec kNangateAOI21X2PinA[] = {
    {"metal1", 0.215, 0.56, 0.35, 0.7},
};

inline constexpr RectSpec kNangateAOI21X2PinB1[] = {
    {"metal1", 0.765, 0.56, 0.9, 0.7},
};

inline constexpr RectSpec kNangateAOI21X2PinB2[] = {
    {"metal1", 0.63, 0.77, 1.18, 0.84},
    {"metal1", 1.11, 0.525, 1.18, 0.84},
    {"metal1", 0.63, 0.525, 0.7, 0.84},
    {"metal1", 0.57, 0.525, 0.7, 0.7},
};

inline constexpr RectSpec kNangateAOI21X2PinZN[] = {
    {"metal1", 0.435, 0.905, 1.13, 0.975},
    {"metal1", 0.25, 0.355, 0.905, 0.425},
    {"metal1", 0.835, 0.15, 0.905, 0.425},
    {"metal1", 0.435, 0.355, 0.505, 0.975},
    {"metal1", 0.25, 0.15, 0.335, 0.425},
};

inline constexpr RectSpec kNangateAOI21X2Power[] = {
    {"metal1", 0.0, 1.315, 1.33, 1.485},
    {"metal1", 0.265, 1.205, 0.335, 1.485},
};

inline constexpr RectSpec kNangateAOI21X2Ground[] = {
    {"metal1", 0.0, -0.085, 1.33, 0.085},
    {"metal1", 1.215, -0.085, 1.285, 0.425},
    {"metal1", 0.455, -0.085, 0.525, 0.285},
    {"metal1", 0.08, -0.085, 0.15, 0.425},
};

inline constexpr RectSpec kNangateAOI21X2ObsGroup0[] = {
    {"metal1", 1.215, 0.975, 1.285, 1.25, true},
    {"metal1", 0.085, 0.975, 0.155, 1.25, true},
    {"metal1", 0.085, 1.07, 1.285, 1.14, true},
};

inline constexpr GroupSpec kNangateAOI21X2Groups[] = {
    {BindingKind::kPinNet, "A", kNangateAOI21X2PinA, std::size(kNangateAOI21X2PinA)},
    {BindingKind::kPinNet, "B1", kNangateAOI21X2PinB1, std::size(kNangateAOI21X2PinB1)},
    {BindingKind::kPinNet, "B2", kNangateAOI21X2PinB2, std::size(kNangateAOI21X2PinB2)},
    {BindingKind::kPinNet, "ZN", kNangateAOI21X2PinZN, std::size(kNangateAOI21X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAOI21X2Power, std::size(kNangateAOI21X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAOI21X2Ground, std::size(kNangateAOI21X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAOI21X2ObsGroup0, std::size(kNangateAOI21X2ObsGroup0)},
};

inline constexpr RectSpec kNangateAOI21X4PinA[] = {
    {"metal1", 0.4, 0.525, 0.535, 0.7},
};

inline constexpr RectSpec kNangateAOI21X4PinB1[] = {
    {"metal1", 1.165, 0.69, 2.06, 0.76},
    {"metal1", 1.925, 0.56, 2.06, 0.76},
    {"metal1", 1.165, 0.56, 1.3, 0.76},
};

inline constexpr RectSpec kNangateAOI21X4PinB2[] = {
    {"metal1", 2.25, 0.42, 2.32, 0.66},
    {"metal1", 0.925, 0.42, 2.32, 0.49},
    {"metal1", 1.525, 0.42, 1.66, 0.625},
    {"metal1", 0.925, 0.42, 0.995, 0.66},
};

inline constexpr RectSpec kNangateAOI21X4PinZN[] = {
    {"metal1", 2.14, 0.825, 2.21, 1.115},
    {"metal1", 0.63, 0.825, 2.21, 0.895},
    {"metal1", 0.63, 0.26, 2.055, 0.33},
    {"metal1", 1.76, 0.825, 1.83, 1.115},
    {"metal1", 1.38, 0.825, 1.45, 1.115},
    {"metal1", 1.0, 0.825, 1.07, 1.115},
    {"metal1", 0.63, 0.15, 0.7, 0.895},
    {"metal1", 0.25, 0.355, 0.7, 0.425},
    {"metal1", 0.25, 0.15, 0.32, 0.425},
};

inline constexpr RectSpec kNangateAOI21X4Power[] = {
    {"metal1", 0.0, 1.315, 2.47, 1.485},
    {"metal1", 0.62, 1.205, 0.69, 1.485},
    {"metal1", 0.24, 1.205, 0.31, 1.485},
};

inline constexpr RectSpec kNangateAOI21X4Ground[] = {
    {"metal1", 0.0, -0.085, 2.47, 0.085},
    {"metal1", 2.33, -0.085, 2.4, 0.35},
    {"metal1", 1.57, -0.085, 1.64, 0.195},
    {"metal1", 0.81, -0.085, 0.88, 0.195},
    {"metal1", 0.43, -0.085, 0.5, 0.195},
    {"metal1", 0.055, -0.085, 0.125, 0.425},
};

inline constexpr RectSpec kNangateAOI21X4ObsGroup0[] = {
    {"metal1", 0.81, 1.18, 2.4, 1.25, true},
    {"metal1", 2.33, 0.84, 2.4, 1.25, true},
    {"metal1", 0.43, 0.965, 0.5, 1.24, true},
    {"metal1", 0.06, 0.965, 0.13, 1.24, true},
    {"metal1", 1.95, 0.96, 2.02, 1.25, true},
    {"metal1", 1.57, 0.96, 1.64, 1.25, true},
    {"metal1", 1.19, 0.96, 1.26, 1.25, true},
    {"metal1", 0.81, 0.965, 0.88, 1.25, true},
    {"metal1", 0.06, 0.965, 0.88, 1.035, true},
};

inline constexpr GroupSpec kNangateAOI21X4Groups[] = {
    {BindingKind::kPinNet, "A", kNangateAOI21X4PinA, std::size(kNangateAOI21X4PinA)},
    {BindingKind::kPinNet, "B1", kNangateAOI21X4PinB1, std::size(kNangateAOI21X4PinB1)},
    {BindingKind::kPinNet, "B2", kNangateAOI21X4PinB2, std::size(kNangateAOI21X4PinB2)},
    {BindingKind::kPinNet, "ZN", kNangateAOI21X4PinZN, std::size(kNangateAOI21X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAOI21X4Power, std::size(kNangateAOI21X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAOI21X4Ground, std::size(kNangateAOI21X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAOI21X4ObsGroup0, std::size(kNangateAOI21X4ObsGroup0)},
};

inline constexpr RectSpec kNangateAOI221X1PinA[] = {
    {"metal1", 0.44, 0.525, 0.565, 0.7},
};

inline constexpr RectSpec kNangateAOI221X1PinB1[] = {
    {"metal1", 0.25, 0.525, 0.375, 0.7},
};

inline constexpr RectSpec kNangateAOI221X1PinB2[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateAOI221X1PinC1[] = {
    {"metal1", 0.955, 0.525, 1.08, 0.7},
};

inline constexpr RectSpec kNangateAOI221X1PinC2[] = {
    {"metal1", 0.63, 0.525, 0.74, 0.7},
};

inline constexpr RectSpec kNangateAOI221X1PinZN[] = {
    {"metal1", 0.425, 0.355, 1.055, 0.425},
    {"metal1", 0.985, 0.15, 1.055, 0.425},
    {"metal1", 0.805, 0.355, 0.89, 1.115},
    {"metal1", 0.425, 0.15, 0.495, 0.425},
};

inline constexpr RectSpec kNangateAOI221X1Power[] = {
    {"metal1", 0.0, 1.315, 1.14, 1.485},
    {"metal1", 0.225, 0.905, 0.295, 1.485},
};

inline constexpr RectSpec kNangateAOI221X1Ground[] = {
    {"metal1", 0.0, -0.085, 1.14, 0.085},
    {"metal1", 0.605, -0.085, 0.675, 0.215},
    {"metal1", 0.04, -0.085, 0.11, 0.355},
};

inline constexpr RectSpec kNangateAOI221X1ObsGroup0[] = {
    {"metal1", 0.615, 1.18, 1.055, 1.25, true},
    {"metal1", 0.985, 0.905, 1.055, 1.25, true},
    {"metal1", 0.615, 0.905, 0.685, 1.25, true},
};

inline constexpr RectSpec kNangateAOI221X1ObsGroup1[] = {
    {"metal1", 0.415, 0.77, 0.485, 1.18, true},
    {"metal1", 0.045, 0.77, 0.115, 1.18, true},
    {"metal1", 0.045, 0.77, 0.485, 0.84, true},
};

inline constexpr GroupSpec kNangateAOI221X1Groups[] = {
    {BindingKind::kPinNet, "A", kNangateAOI221X1PinA, std::size(kNangateAOI221X1PinA)},
    {BindingKind::kPinNet, "B1", kNangateAOI221X1PinB1, std::size(kNangateAOI221X1PinB1)},
    {BindingKind::kPinNet, "B2", kNangateAOI221X1PinB2, std::size(kNangateAOI221X1PinB2)},
    {BindingKind::kPinNet, "C1", kNangateAOI221X1PinC1, std::size(kNangateAOI221X1PinC1)},
    {BindingKind::kPinNet, "C2", kNangateAOI221X1PinC2, std::size(kNangateAOI221X1PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateAOI221X1PinZN, std::size(kNangateAOI221X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAOI221X1Power, std::size(kNangateAOI221X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAOI221X1Ground, std::size(kNangateAOI221X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAOI221X1ObsGroup0, std::size(kNangateAOI221X1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateAOI221X1ObsGroup1, std::size(kNangateAOI221X1ObsGroup1)},
};

inline constexpr RectSpec kNangateAOI221X2PinA[] = {
    {"metal1", 0.18, 0.79, 1.13, 0.86},
    {"metal1", 1.06, 0.525, 1.13, 0.86},
    {"metal1", 0.18, 0.56, 0.25, 0.86},
    {"metal1", 0.06, 0.56, 0.25, 0.7},
};

inline constexpr RectSpec kNangateAOI221X2PinB1[] = {
    {"metal1", 0.82, 0.42, 0.945, 0.7},
    {"metal1", 0.34, 0.42, 0.945, 0.49},
    {"metal1", 0.34, 0.42, 0.41, 0.66},
};

inline constexpr RectSpec kNangateAOI221X2PinB2[] = {
    {"metal1", 0.585, 0.56, 0.725, 0.7},
};

inline constexpr RectSpec kNangateAOI221X2PinC1[] = {
    {"metal1", 1.57, 0.525, 1.66, 0.7},
};

inline constexpr RectSpec kNangateAOI221X2PinC2[] = {
    {"metal1", 1.77, 0.525, 1.91, 0.7},
    {"metal1", 1.34, 0.765, 1.84, 0.835},
    {"metal1", 1.77, 0.525, 1.84, 0.835},
    {"metal1", 1.34, 0.525, 1.41, 0.835},
};

inline constexpr RectSpec kNangateAOI221X2PinZN[] = {
    {"metal1", 1.195, 0.9, 1.86, 0.97},
    {"metal1", 0.2, 0.28, 1.675, 0.35},
    {"metal1", 1.195, 0.28, 1.275, 0.97},
};

inline constexpr RectSpec kNangateAOI221X2Power[] = {
    {"metal1", 0.0, 1.315, 2.09, 1.485},
    {"metal1", 0.795, 1.205, 0.865, 1.485},
    {"metal1", 0.415, 1.205, 0.485, 1.485},
};

inline constexpr RectSpec kNangateAOI221X2Ground[] = {
    {"metal1", 0.0, -0.085, 2.09, 0.085},
    {"metal1", 1.945, -0.085, 2.015, 0.425},
    {"metal1", 1.175, -0.085, 1.245, 0.195},
    {"metal1", 0.605, -0.085, 0.675, 0.195},
    {"metal1", 0.04, -0.085, 0.11, 0.425},
};

inline constexpr RectSpec kNangateAOI221X2ObsGroup0[] = {
    {"metal1", 0.045, 1.07, 2.015, 1.14, true},
    {"metal1", 1.945, 0.865, 2.015, 1.14, true},
    {"metal1", 0.045, 0.865, 0.115, 1.14, true},
};

inline constexpr RectSpec kNangateAOI221X2ObsGroup1[] = {
    {"metal1", 0.2, 0.93, 1.09, 1.0, true},
};

inline constexpr GroupSpec kNangateAOI221X2Groups[] = {
    {BindingKind::kPinNet, "A", kNangateAOI221X2PinA, std::size(kNangateAOI221X2PinA)},
    {BindingKind::kPinNet, "B1", kNangateAOI221X2PinB1, std::size(kNangateAOI221X2PinB1)},
    {BindingKind::kPinNet, "B2", kNangateAOI221X2PinB2, std::size(kNangateAOI221X2PinB2)},
    {BindingKind::kPinNet, "C1", kNangateAOI221X2PinC1, std::size(kNangateAOI221X2PinC1)},
    {BindingKind::kPinNet, "C2", kNangateAOI221X2PinC2, std::size(kNangateAOI221X2PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateAOI221X2PinZN, std::size(kNangateAOI221X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAOI221X2Power, std::size(kNangateAOI221X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAOI221X2Ground, std::size(kNangateAOI221X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAOI221X2ObsGroup0, std::size(kNangateAOI221X2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateAOI221X2ObsGroup1, std::size(kNangateAOI221X2ObsGroup1)},
};

inline constexpr RectSpec kNangateAOI221X4PinA[] = {
    {"metal1", 0.61, 0.525, 0.7, 0.7},
};

inline constexpr RectSpec kNangateAOI221X4PinB1[] = {
    {"metal1", 0.8, 0.525, 0.89, 0.7},
};

inline constexpr RectSpec kNangateAOI221X4PinB2[] = {
    {"metal1", 1.01, 0.525, 1.18, 0.7},
};

inline constexpr RectSpec kNangateAOI221X4PinC1[] = {
    {"metal1", 0.06, 0.525, 0.27, 0.7},
};

inline constexpr RectSpec kNangateAOI221X4PinC2[] = {
    {"metal1", 0.42, 0.525, 0.51, 0.7},
};

inline constexpr RectSpec kNangateAOI221X4PinZN[] = {
    {"metal1", 2.17, 0.15, 2.24, 1.25},
    {"metal1", 1.795, 0.56, 2.24, 0.7},
    {"metal1", 1.795, 0.15, 1.885, 0.7},
    {"metal1", 1.795, 0.15, 1.865, 1.25},
};

inline constexpr RectSpec kNangateAOI221X4Power[] = {
    {"metal1", 0.0, 1.315, 2.47, 1.485},
    {"metal1", 2.355, 0.975, 2.425, 1.485},
    {"metal1", 1.975, 0.975, 2.045, 1.485},
    {"metal1", 1.6, 1.005, 1.67, 1.485},
    {"metal1", 1.215, 0.975, 1.285, 1.485},
    {"metal1", 0.875, 1.035, 0.945, 1.485},
};

inline constexpr RectSpec kNangateAOI221X4Ground[] = {
    {"metal1", 0.0, -0.085, 2.47, 0.085},
    {"metal1", 2.355, -0.085, 2.425, 0.425},
    {"metal1", 1.975, -0.085, 2.045, 0.425},
    {"metal1", 1.605, -0.085, 1.675, 0.425},
    {"metal1", 1.215, -0.085, 1.285, 0.285},
    {"metal1", 0.495, -0.085, 0.565, 0.285},
};

inline constexpr RectSpec kNangateAOI221X4ObsGroup0[] = {
    {"metal1", 1.415, 0.15, 1.485, 1.25, true},
    {"metal1", 1.415, 0.525, 1.73, 0.66, true},
};

inline constexpr RectSpec kNangateAOI221X4ObsGroup1[] = {
    {"metal1", 0.315, 0.765, 0.385, 1.04, true},
    {"metal1", 0.315, 0.765, 1.35, 0.835, true},
    {"metal1", 1.28, 0.355, 1.35, 0.835, true},
    {"metal1", 0.125, 0.355, 1.35, 0.425, true},
    {"metal1", 0.71, 0.15, 0.78, 0.425, true},
    {"metal1", 0.125, 0.15, 0.195, 0.425, true},
};

inline constexpr RectSpec kNangateAOI221X4ObsGroup2[] = {
    {"metal1", 1.03, 0.9, 1.1, 1.25, true},
    {"metal1", 0.695, 0.9, 0.765, 1.25, true},
    {"metal1", 0.695, 0.9, 1.1, 0.97, true},
};

inline constexpr RectSpec kNangateAOI221X4ObsGroup3[] = {
    {"metal1", 0.495, 0.975, 0.565, 1.25, true},
    {"metal1", 0.125, 0.975, 0.195, 1.25, true},
    {"metal1", 0.125, 1.105, 0.565, 1.175, true},
};

inline constexpr GroupSpec kNangateAOI221X4Groups[] = {
    {BindingKind::kPinNet, "A", kNangateAOI221X4PinA, std::size(kNangateAOI221X4PinA)},
    {BindingKind::kPinNet, "B1", kNangateAOI221X4PinB1, std::size(kNangateAOI221X4PinB1)},
    {BindingKind::kPinNet, "B2", kNangateAOI221X4PinB2, std::size(kNangateAOI221X4PinB2)},
    {BindingKind::kPinNet, "C1", kNangateAOI221X4PinC1, std::size(kNangateAOI221X4PinC1)},
    {BindingKind::kPinNet, "C2", kNangateAOI221X4PinC2, std::size(kNangateAOI221X4PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateAOI221X4PinZN, std::size(kNangateAOI221X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAOI221X4Power, std::size(kNangateAOI221X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAOI221X4Ground, std::size(kNangateAOI221X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAOI221X4ObsGroup0, std::size(kNangateAOI221X4ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateAOI221X4ObsGroup1, std::size(kNangateAOI221X4ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateAOI221X4ObsGroup2, std::size(kNangateAOI221X4ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateAOI221X4ObsGroup3, std::size(kNangateAOI221X4ObsGroup3)},
};

inline constexpr RectSpec kNangateAOI222X1PinA1[] = {
    {"metal1", 1.315, 0.525, 1.46, 0.7},
};

inline constexpr RectSpec kNangateAOI222X1PinA2[] = {
    {"metal1", 0.995, 0.525, 1.08, 0.7},
};

inline constexpr RectSpec kNangateAOI222X1PinB1[] = {
    {"metal1", 0.62, 0.525, 0.72, 0.7},
};

inline constexpr RectSpec kNangateAOI222X1PinB2[] = {
    {"metal1", 0.82, 0.525, 0.91, 0.7},
};

inline constexpr RectSpec kNangateAOI222X1PinC1[] = {
    {"metal1", 0.385, 0.525, 0.51, 0.7},
};

inline constexpr RectSpec kNangateAOI222X1PinC2[] = {
    {"metal1", 0.06, 0.525, 0.215, 0.7},
};

inline constexpr RectSpec kNangateAOI222X1PinZN[] = {
    {"metal1", 0.5, 0.375, 1.46, 0.45},
    {"metal1", 1.325, 0.175, 1.46, 0.45},
    {"metal1", 1.145, 0.375, 1.215, 1.115},
    {"metal1", 0.5, 0.175, 0.57, 0.45},
};

inline constexpr RectSpec kNangateAOI222X1Power[] = {
    {"metal1", 0.0, 1.315, 1.52, 1.485},
    {"metal1", 0.415, 0.905, 0.485, 1.485},
    {"metal1", 0.04, 0.905, 0.11, 1.485},
};

inline constexpr RectSpec kNangateAOI222X1Ground[] = {
    {"metal1", 0.0, -0.085, 1.52, 0.085},
    {"metal1", 0.945, -0.085, 1.015, 0.31},
    {"metal1", 0.04, -0.085, 0.11, 0.45},
};

inline constexpr RectSpec kNangateAOI222X1ObsGroup0[] = {
    {"metal1", 0.575, 1.18, 1.395, 1.25, true},
    {"metal1", 1.325, 0.905, 1.395, 1.25, true},
    {"metal1", 0.945, 0.905, 1.015, 1.25, true},
    {"metal1", 0.575, 0.905, 0.645, 1.25, true},
};

inline constexpr RectSpec kNangateAOI222X1ObsGroup1[] = {
    {"metal1", 0.235, 0.77, 0.305, 1.18, true},
    {"metal1", 0.755, 0.77, 0.825, 1.115, true},
    {"metal1", 0.235, 0.77, 0.825, 0.84, true},
};

inline constexpr GroupSpec kNangateAOI222X1Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateAOI222X1PinA1, std::size(kNangateAOI222X1PinA1)},
    {BindingKind::kPinNet, "A2", kNangateAOI222X1PinA2, std::size(kNangateAOI222X1PinA2)},
    {BindingKind::kPinNet, "B1", kNangateAOI222X1PinB1, std::size(kNangateAOI222X1PinB1)},
    {BindingKind::kPinNet, "B2", kNangateAOI222X1PinB2, std::size(kNangateAOI222X1PinB2)},
    {BindingKind::kPinNet, "C1", kNangateAOI222X1PinC1, std::size(kNangateAOI222X1PinC1)},
    {BindingKind::kPinNet, "C2", kNangateAOI222X1PinC2, std::size(kNangateAOI222X1PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateAOI222X1PinZN, std::size(kNangateAOI222X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAOI222X1Power, std::size(kNangateAOI222X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAOI222X1Ground, std::size(kNangateAOI222X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAOI222X1ObsGroup0, std::size(kNangateAOI222X1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateAOI222X1ObsGroup1, std::size(kNangateAOI222X1ObsGroup1)},
};

inline constexpr RectSpec kNangateAOI222X2PinA1[] = {
    {"metal1", 1.91, 0.56, 2.045, 0.7},
};

inline constexpr RectSpec kNangateAOI222X2PinA2[] = {
    {"metal1", 2.285, 0.56, 2.42, 0.7},
};

inline constexpr RectSpec kNangateAOI222X2PinB1[] = {
    {"metal1", 1.145, 0.56, 1.28, 0.7},
};

inline constexpr RectSpec kNangateAOI222X2PinB2[] = {
    {"metal1", 1.475, 0.42, 1.545, 0.66},
    {"metal1", 0.91, 0.42, 1.545, 0.49},
    {"metal1", 0.91, 0.42, 1.08, 0.66},
};

inline constexpr RectSpec kNangateAOI222X2PinC1[] = {
    {"metal1", 0.385, 0.56, 0.52, 0.7},
};

inline constexpr RectSpec kNangateAOI222X2PinC2[] = {
    {"metal1", 0.69, 0.425, 0.76, 0.66},
    {"metal1", 0.06, 0.425, 0.76, 0.495},
    {"metal1", 0.06, 0.425, 0.19, 0.7},
};

inline constexpr RectSpec kNangateAOI222X2PinZN[] = {
    {"metal1", 2.31, 0.77, 2.38, 1.115},
    {"metal1", 1.77, 0.77, 2.38, 0.84},
    {"metal1", 0.39, 0.285, 2.035, 0.355},
    {"metal1", 1.94, 0.77, 2.01, 1.115},
    {"metal1", 1.77, 0.285, 1.84, 0.84},
    {"metal1", 1.145, 0.15, 1.28, 0.355},
    {"metal1", 0.39, 0.15, 0.525, 0.355},
};

inline constexpr RectSpec kNangateAOI222X2Power[] = {
    {"metal1", 0.0, 1.315, 2.66, 1.485},
    {"metal1", 0.605, 0.905, 0.675, 1.485},
    {"metal1", 0.225, 0.905, 0.295, 1.485},
};

inline constexpr RectSpec kNangateAOI222X2Ground[] = {
    {"metal1", 0.0, -0.085, 2.66, 0.085},
    {"metal1", 2.31, -0.085, 2.38, 0.25},
    {"metal1", 1.555, -0.085, 1.625, 0.195},
    {"metal1", 0.765, -0.085, 0.9, 0.215},
    {"metal1", 0.04, -0.085, 0.11, 0.25},
};

inline constexpr RectSpec kNangateAOI222X2ObsGroup0[] = {
    {"metal1", 2.1, 0.355, 2.57, 0.425, true},
    {"metal1", 2.5, 0.15, 2.57, 0.425, true},
    {"metal1", 2.1, 0.15, 2.17, 0.425, true},
    {"metal1", 1.715, 0.15, 2.17, 0.22, true},
};

inline constexpr RectSpec kNangateAOI222X2ObsGroup1[] = {
    {"metal1", 0.995, 1.18, 2.57, 1.25, true},
    {"metal1", 2.5, 0.905, 2.57, 1.25, true},
    {"metal1", 2.12, 0.905, 2.19, 1.25, true},
    {"metal1", 1.745, 0.905, 1.815, 1.25, true},
    {"metal1", 1.365, 0.905, 1.435, 1.25, true},
    {"metal1", 0.995, 0.905, 1.065, 1.25, true},
};

inline constexpr RectSpec kNangateAOI222X2ObsGroup2[] = {
    {"metal1", 0.795, 0.77, 0.865, 1.18, true},
    {"metal1", 0.415, 0.77, 0.485, 1.18, true},
    {"metal1", 0.045, 0.77, 0.115, 1.18, true},
    {"metal1", 1.555, 0.77, 1.625, 1.115, true},
    {"metal1", 1.175, 0.77, 1.245, 1.115, true},
    {"metal1", 0.045, 0.77, 1.625, 0.84, true},
};

inline constexpr GroupSpec kNangateAOI222X2Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateAOI222X2PinA1, std::size(kNangateAOI222X2PinA1)},
    {BindingKind::kPinNet, "A2", kNangateAOI222X2PinA2, std::size(kNangateAOI222X2PinA2)},
    {BindingKind::kPinNet, "B1", kNangateAOI222X2PinB1, std::size(kNangateAOI222X2PinB1)},
    {BindingKind::kPinNet, "B2", kNangateAOI222X2PinB2, std::size(kNangateAOI222X2PinB2)},
    {BindingKind::kPinNet, "C1", kNangateAOI222X2PinC1, std::size(kNangateAOI222X2PinC1)},
    {BindingKind::kPinNet, "C2", kNangateAOI222X2PinC2, std::size(kNangateAOI222X2PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateAOI222X2PinZN, std::size(kNangateAOI222X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAOI222X2Power, std::size(kNangateAOI222X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAOI222X2Ground, std::size(kNangateAOI222X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAOI222X2ObsGroup0, std::size(kNangateAOI222X2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateAOI222X2ObsGroup1, std::size(kNangateAOI222X2ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateAOI222X2ObsGroup2, std::size(kNangateAOI222X2ObsGroup2)},
};

inline constexpr RectSpec kNangateAOI222X4PinA1[] = {
    {"metal1", 0.06, 0.525, 0.235, 0.7},
};

inline constexpr RectSpec kNangateAOI222X4PinA2[] = {
    {"metal1", 0.385, 0.525, 0.51, 0.7},
};

inline constexpr RectSpec kNangateAOI222X4PinB1[] = {
    {"metal1", 0.765, 0.525, 0.89, 0.7},
};

inline constexpr RectSpec kNangateAOI222X4PinB2[] = {
    {"metal1", 0.575, 0.525, 0.7, 0.7},
};

inline constexpr RectSpec kNangateAOI222X4PinC1[] = {
    {"metal1", 1.01, 0.525, 1.135, 0.7},
};

inline constexpr RectSpec kNangateAOI222X4PinC2[] = {
    {"metal1", 1.2, 0.525, 1.335, 0.7},
};

inline constexpr RectSpec kNangateAOI222X4PinZN[] = {
    {"metal1", 2.33, 0.15, 2.41, 1.205},
    {"metal1", 1.95, 0.56, 2.41, 0.7},
    {"metal1", 2.325, 0.15, 2.41, 0.7},
    {"metal1", 1.95, 0.15, 2.02, 1.205},
};

inline constexpr RectSpec kNangateAOI222X4Power[] = {
    {"metal1", 0.0, 1.315, 2.66, 1.485},
    {"metal1", 2.51, 0.93, 2.58, 1.485},
    {"metal1", 2.13, 0.93, 2.2, 1.485},
    {"metal1", 1.75, 0.93, 1.82, 1.485},
    {"metal1", 1.37, 0.93, 1.44, 1.485},
    {"metal1", 0.995, 1.065, 1.065, 1.485},
};

inline constexpr RectSpec kNangateAOI222X4Ground[] = {
    {"metal1", 0.0, -0.085, 2.66, 0.085},
    {"metal1", 2.51, -0.085, 2.58, 0.425},
    {"metal1", 2.14, -0.085, 2.21, 0.425},
    {"metal1", 1.75, -0.085, 1.82, 0.425},
    {"metal1", 1.37, -0.085, 1.44, 0.285},
    {"metal1", 0.46, -0.085, 0.53, 0.285},
};

inline constexpr RectSpec kNangateAOI222X4ObsGroup0[] = {
    {"metal1", 1.57, 0.15, 1.64, 1.205, true},
    {"metal1", 1.57, 0.525, 1.885, 0.66, true},
};

inline constexpr RectSpec kNangateAOI222X4ObsGroup1[] = {
    {"metal1", 0.28, 0.765, 0.35, 1.04, true},
    {"metal1", 0.28, 0.765, 1.505, 0.835, true},
    {"metal1", 1.435, 0.355, 1.505, 0.835, true},
    {"metal1", 0.09, 0.355, 1.505, 0.425, true},
    {"metal1", 0.84, 0.15, 0.91, 0.425, true},
    {"metal1", 0.09, 0.15, 0.16, 0.425, true},
};

inline constexpr RectSpec kNangateAOI222X4ObsGroup2[] = {
    {"metal1", 1.18, 0.93, 1.25, 1.205, true},
    {"metal1", 0.66, 0.93, 0.73, 1.065, true},
    {"metal1", 0.66, 0.93, 1.25, 1.0, true},
};

inline constexpr RectSpec kNangateAOI222X4ObsGroup3[] = {
    {"metal1", 0.09, 1.135, 0.91, 1.205, true},
    {"metal1", 0.84, 1.07, 0.91, 1.205, true},
    {"metal1", 0.46, 0.93, 0.53, 1.205, true},
    {"metal1", 0.09, 0.93, 0.16, 1.205, true},
};

inline constexpr GroupSpec kNangateAOI222X4Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateAOI222X4PinA1, std::size(kNangateAOI222X4PinA1)},
    {BindingKind::kPinNet, "A2", kNangateAOI222X4PinA2, std::size(kNangateAOI222X4PinA2)},
    {BindingKind::kPinNet, "B1", kNangateAOI222X4PinB1, std::size(kNangateAOI222X4PinB1)},
    {BindingKind::kPinNet, "B2", kNangateAOI222X4PinB2, std::size(kNangateAOI222X4PinB2)},
    {BindingKind::kPinNet, "C1", kNangateAOI222X4PinC1, std::size(kNangateAOI222X4PinC1)},
    {BindingKind::kPinNet, "C2", kNangateAOI222X4PinC2, std::size(kNangateAOI222X4PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateAOI222X4PinZN, std::size(kNangateAOI222X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAOI222X4Power, std::size(kNangateAOI222X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAOI222X4Ground, std::size(kNangateAOI222X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAOI222X4ObsGroup0, std::size(kNangateAOI222X4ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateAOI222X4ObsGroup1, std::size(kNangateAOI222X4ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateAOI222X4ObsGroup2, std::size(kNangateAOI222X4ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateAOI222X4ObsGroup3, std::size(kNangateAOI222X4ObsGroup3)},
};

inline constexpr RectSpec kNangateAOI22X1PinA1[] = {
    {"metal1", 0.575, 0.42, 0.7, 0.66},
};

inline constexpr RectSpec kNangateAOI22X1PinA2[] = {
    {"metal1", 0.765, 0.42, 0.89, 0.66},
};

inline constexpr RectSpec kNangateAOI22X1PinB1[] = {
    {"metal1", 0.25, 0.525, 0.375, 0.7},
};

inline constexpr RectSpec kNangateAOI22X1PinB2[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateAOI22X1PinZN[] = {
    {"metal1", 0.62, 0.725, 0.69, 1.005},
    {"metal1", 0.44, 0.725, 0.69, 0.795},
    {"metal1", 0.44, 0.15, 0.51, 0.795},
};

inline constexpr RectSpec kNangateAOI22X1Power[] = {
    {"metal1", 0.0, 1.315, 0.95, 1.485},
    {"metal1", 0.24, 1.205, 0.31, 1.485},
};

inline constexpr RectSpec kNangateAOI22X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.95, 0.085},
    {"metal1", 0.81, -0.085, 0.88, 0.355},
    {"metal1", 0.055, -0.085, 0.125, 0.355},
};

inline constexpr RectSpec kNangateAOI22X1ObsGroup0[] = {
    {"metal1", 0.06, 1.07, 0.88, 1.14, true},
    {"metal1", 0.81, 0.865, 0.88, 1.14, true},
    {"metal1", 0.435, 0.865, 0.505, 1.14, true},
    {"metal1", 0.06, 0.865, 0.13, 1.14, true},
};

inline constexpr GroupSpec kNangateAOI22X1Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateAOI22X1PinA1, std::size(kNangateAOI22X1PinA1)},
    {BindingKind::kPinNet, "A2", kNangateAOI22X1PinA2, std::size(kNangateAOI22X1PinA2)},
    {BindingKind::kPinNet, "B1", kNangateAOI22X1PinB1, std::size(kNangateAOI22X1PinB1)},
    {BindingKind::kPinNet, "B2", kNangateAOI22X1PinB2, std::size(kNangateAOI22X1PinB2)},
    {BindingKind::kPinNet, "ZN", kNangateAOI22X1PinZN, std::size(kNangateAOI22X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAOI22X1Power, std::size(kNangateAOI22X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAOI22X1Ground, std::size(kNangateAOI22X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAOI22X1ObsGroup0, std::size(kNangateAOI22X1ObsGroup0)},
};

inline constexpr RectSpec kNangateAOI22X2PinA1[] = {
    {"metal1", 1.155, 0.56, 1.29, 0.7},
};

inline constexpr RectSpec kNangateAOI22X2PinA2[] = {
    {"metal1", 1.48, 0.425, 1.55, 0.66},
    {"metal1", 0.955, 0.425, 1.55, 0.495},
    {"metal1", 0.955, 0.425, 1.08, 0.7},
};

inline constexpr RectSpec kNangateAOI22X2PinB1[] = {
    {"metal1", 0.395, 0.56, 0.53, 0.7},
};

inline constexpr RectSpec kNangateAOI22X2PinB2[] = {
    {"metal1", 0.06, 0.765, 0.755, 0.835},
    {"metal1", 0.685, 0.525, 0.755, 0.835},
    {"metal1", 0.06, 0.525, 0.195, 0.835},
};

inline constexpr RectSpec kNangateAOI22X2PinZN[] = {
    {"metal1", 1.375, 0.765, 1.445, 1.065},
    {"metal1", 0.82, 0.765, 1.445, 0.835},
    {"metal1", 0.395, 0.28, 1.285, 0.355},
    {"metal1", 1.15, 0.15, 1.285, 0.355},
    {"metal1", 0.99, 0.765, 1.06, 1.065},
    {"metal1", 0.82, 0.28, 0.89, 0.835},
    {"metal1", 0.395, 0.15, 0.53, 0.355},
};

inline constexpr RectSpec kNangateAOI22X2Power[] = {
    {"metal1", 0.0, 1.315, 1.71, 1.485},
    {"metal1", 0.61, 1.035, 0.68, 1.485},
    {"metal1", 0.23, 1.035, 0.3, 1.485},
};

inline constexpr RectSpec kNangateAOI22X2Ground[] = {
    {"metal1", 0.0, -0.085, 1.71, 0.085},
    {"metal1", 1.56, -0.085, 1.63, 0.36},
    {"metal1", 0.77, -0.085, 0.905, 0.205},
    {"metal1", 0.045, -0.085, 0.115, 0.39},
};

inline constexpr RectSpec kNangateAOI22X2ObsGroup0[] = {
    {"metal1", 0.8, 1.18, 1.63, 1.25, true},
    {"metal1", 1.56, 0.975, 1.63, 1.25, true},
    {"metal1", 0.42, 0.9, 0.49, 1.25, true},
    {"metal1", 0.05, 0.9, 0.12, 1.25, true},
    {"metal1", 1.18, 0.975, 1.25, 1.25, true},
    {"metal1", 0.8, 0.9, 0.87, 1.25, true},
    {"metal1", 0.05, 0.9, 0.87, 0.97, true},
};

inline constexpr GroupSpec kNangateAOI22X2Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateAOI22X2PinA1, std::size(kNangateAOI22X2PinA1)},
    {BindingKind::kPinNet, "A2", kNangateAOI22X2PinA2, std::size(kNangateAOI22X2PinA2)},
    {BindingKind::kPinNet, "B1", kNangateAOI22X2PinB1, std::size(kNangateAOI22X2PinB1)},
    {BindingKind::kPinNet, "B2", kNangateAOI22X2PinB2, std::size(kNangateAOI22X2PinB2)},
    {BindingKind::kPinNet, "ZN", kNangateAOI22X2PinZN, std::size(kNangateAOI22X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAOI22X2Power, std::size(kNangateAOI22X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAOI22X2Ground, std::size(kNangateAOI22X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAOI22X2ObsGroup0, std::size(kNangateAOI22X2ObsGroup0)},
};

inline constexpr RectSpec kNangateAOI22X4PinA1[] = {
    {"metal1", 1.915, 0.69, 2.79, 0.76},
    {"metal1", 2.655, 0.56, 2.79, 0.76},
    {"metal1", 1.915, 0.56, 2.05, 0.76},
};

inline constexpr RectSpec kNangateAOI22X4PinA2[] = {
    {"metal1", 2.91, 0.42, 3.045, 0.66},
    {"metal1", 1.715, 0.42, 3.045, 0.49},
    {"metal1", 2.295, 0.42, 2.43, 0.625},
    {"metal1", 1.715, 0.42, 1.785, 0.66},
};

inline constexpr RectSpec kNangateAOI22X4PinB1[] = {
    {"metal1", 0.395, 0.69, 1.29, 0.76},
    {"metal1", 1.155, 0.56, 1.29, 0.76},
    {"metal1", 0.395, 0.56, 0.53, 0.76},
};

inline constexpr RectSpec kNangateAOI22X4PinB2[] = {
    {"metal1", 1.445, 0.42, 1.515, 0.66},
    {"metal1", 0.125, 0.42, 1.515, 0.49},
    {"metal1", 0.755, 0.42, 0.89, 0.625},
    {"metal1", 0.125, 0.42, 0.195, 0.66},
};

inline constexpr RectSpec kNangateAOI22X4PinZN[] = {
    {"metal1", 2.89, 0.825, 2.96, 1.115},
    {"metal1", 1.75, 0.825, 2.96, 0.895},
    {"metal1", 0.395, 0.26, 2.805, 0.33},
    {"metal1", 2.51, 0.825, 2.58, 1.115},
    {"metal1", 2.13, 0.825, 2.2, 1.115},
    {"metal1", 1.75, 0.725, 1.82, 1.115},
    {"metal1", 1.58, 0.725, 1.82, 0.795},
    {"metal1", 1.58, 0.26, 1.65, 0.795},
};

inline constexpr RectSpec kNangateAOI22X4Power[] = {
    {"metal1", 0.0, 1.315, 3.23, 1.485},
    {"metal1", 1.37, 1.065, 1.44, 1.485},
    {"metal1", 0.99, 1.065, 1.06, 1.485},
    {"metal1", 0.61, 1.065, 0.68, 1.485},
    {"metal1", 0.23, 1.065, 0.3, 1.485},
};

inline constexpr RectSpec kNangateAOI22X4Ground[] = {
    {"metal1", 0.0, -0.085, 3.23, 0.085},
    {"metal1", 3.08, -0.085, 3.15, 0.335},
    {"metal1", 2.29, -0.085, 2.425, 0.16},
    {"metal1", 1.53, -0.085, 1.665, 0.16},
    {"metal1", 0.77, -0.085, 0.905, 0.16},
    {"metal1", 0.045, -0.085, 0.115, 0.335},
};

inline constexpr RectSpec kNangateAOI22X4ObsGroup0[] = {
    {"metal1", 1.56, 1.18, 3.15, 1.25, true},
    {"metal1", 3.08, 0.84, 3.15, 1.25, true},
    {"metal1", 2.7, 0.96, 2.77, 1.25, true},
    {"metal1", 2.32, 0.96, 2.39, 1.25, true},
    {"metal1", 1.94, 0.96, 2.01, 1.25, true},
    {"metal1", 1.56, 0.87, 1.63, 1.25, true},
    {"metal1", 1.18, 0.87, 1.25, 1.16, true},
    {"metal1", 0.8, 0.87, 0.87, 1.16, true},
    {"metal1", 0.42, 0.87, 0.49, 1.16, true},
    {"metal1", 0.05, 0.87, 0.12, 1.16, true},
    {"metal1", 0.05, 0.87, 1.63, 0.94, true},
};

inline constexpr GroupSpec kNangateAOI22X4Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateAOI22X4PinA1, std::size(kNangateAOI22X4PinA1)},
    {BindingKind::kPinNet, "A2", kNangateAOI22X4PinA2, std::size(kNangateAOI22X4PinA2)},
    {BindingKind::kPinNet, "B1", kNangateAOI22X4PinB1, std::size(kNangateAOI22X4PinB1)},
    {BindingKind::kPinNet, "B2", kNangateAOI22X4PinB2, std::size(kNangateAOI22X4PinB2)},
    {BindingKind::kPinNet, "ZN", kNangateAOI22X4PinZN, std::size(kNangateAOI22X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateAOI22X4Power, std::size(kNangateAOI22X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateAOI22X4Ground, std::size(kNangateAOI22X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateAOI22X4ObsGroup0, std::size(kNangateAOI22X4ObsGroup0)},
};

inline constexpr RectSpec kNangateBUFX1PinA[] = {
    {"metal1", 0.06, 0.525, 0.19, 0.7},
};

inline constexpr RectSpec kNangateBUFX1PinZ[] = {
    {"metal1", 0.42, 0.19, 0.51, 1.24},
};

inline constexpr RectSpec kNangateBUFX1Power[] = {
    {"metal1", 0.0, 1.315, 0.57, 1.485},
    {"metal1", 0.225, 0.965, 0.295, 1.485},
};

inline constexpr RectSpec kNangateBUFX1Ground[] = {
    {"metal1", 0.0, -0.085, 0.57, 0.085},
    {"metal1", 0.225, -0.085, 0.295, 0.325},
};

inline constexpr RectSpec kNangateBUFX1ObsGroup0[] = {
    {"metal1", 0.045, 0.83, 0.115, 1.24, true},
    {"metal1", 0.045, 0.83, 0.355, 0.9, true},
    {"metal1", 0.285, 0.39, 0.355, 0.9, true},
    {"metal1", 0.045, 0.39, 0.355, 0.46, true},
    {"metal1", 0.045, 0.19, 0.115, 0.46, true},
};

inline constexpr GroupSpec kNangateBUFX1Groups[] = {
    {BindingKind::kPinNet, "A", kNangateBUFX1PinA, std::size(kNangateBUFX1PinA)},
    {BindingKind::kPinNet, "Z", kNangateBUFX1PinZ, std::size(kNangateBUFX1PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateBUFX1Power, std::size(kNangateBUFX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateBUFX1Ground, std::size(kNangateBUFX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateBUFX1ObsGroup0, std::size(kNangateBUFX1ObsGroup0)},
};

inline constexpr RectSpec kNangateBUFX16PinA[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.715},
};

inline constexpr RectSpec kNangateBUFX16PinZ[] = {
    {"metal1", 4.42, 0.15, 4.49, 0.925},
    {"metal1", 1.77, 0.28, 4.49, 0.42},
    {"metal1", 4.05, 0.28, 4.12, 0.925},
    {"metal1", 4.04, 0.15, 4.11, 0.42},
    {"metal1", 3.66, 0.15, 3.73, 0.925},
    {"metal1", 3.28, 0.15, 3.35, 0.925},
    {"metal1", 2.9, 0.15, 2.97, 0.925},
    {"metal1", 2.52, 0.15, 2.59, 0.925},
    {"metal1", 2.14, 0.15, 2.21, 0.925},
    {"metal1", 1.77, 0.15, 1.84, 0.925},
};

inline constexpr RectSpec kNangateBUFX16Power[] = {
    {"metal1", 0.0, 1.315, 4.75, 1.485},
    {"metal1", 4.61, 1.205, 4.68, 1.485},
    {"metal1", 4.23, 1.205, 4.3, 1.485},
    {"metal1", 3.85, 1.205, 3.92, 1.485},
    {"metal1", 3.47, 1.205, 3.54, 1.485},
    {"metal1", 3.09, 1.205, 3.16, 1.485},
    {"metal1", 2.71, 1.205, 2.78, 1.485},
    {"metal1", 2.33, 1.205, 2.4, 1.485},
    {"metal1", 1.95, 1.205, 2.02, 1.485},
    {"metal1", 1.57, 1.205, 1.64, 1.485},
    {"metal1", 1.19, 0.975, 1.26, 1.485},
    {"metal1", 0.81, 0.975, 0.88, 1.485},
    {"metal1", 0.43, 0.975, 0.5, 1.485},
    {"metal1", 0.055, 0.975, 0.125, 1.485},
};

inline constexpr RectSpec kNangateBUFX16Ground[] = {
    {"metal1", 0.0, -0.085, 4.75, 0.085},
    {"metal1", 4.61, -0.085, 4.68, 0.2},
    {"metal1", 4.23, -0.085, 4.3, 0.2},
    {"metal1", 3.85, -0.085, 3.92, 0.2},
    {"metal1", 3.47, -0.085, 3.54, 0.2},
    {"metal1", 3.09, -0.085, 3.16, 0.2},
    {"metal1", 2.71, -0.085, 2.78, 0.2},
    {"metal1", 2.33, -0.085, 2.4, 0.2},
    {"metal1", 1.95, -0.085, 2.02, 0.2},
    {"metal1", 1.57, -0.085, 1.64, 0.34},
    {"metal1", 1.19, -0.085, 1.26, 0.34},
    {"metal1", 0.81, -0.085, 0.88, 0.34},
    {"metal1", 0.43, -0.085, 0.5, 0.34},
    {"metal1", 0.055, -0.085, 0.125, 0.34},
};

inline constexpr RectSpec kNangateBUFX16ObsGroup0[] = {
    {"metal1", 1.38, 0.15, 1.45, 1.25, true},
    {"metal1", 1.0, 0.15, 1.07, 1.25, true},
    {"metal1", 0.62, 0.15, 0.69, 1.25, true},
    {"metal1", 0.25, 0.15, 0.32, 1.25, true},
    {"metal1", 1.635, 1.05, 4.63, 1.12, true},
    {"metal1", 4.56, 0.525, 4.63, 1.12, true},
    {"metal1", 3.45, 0.525, 3.52, 1.12, true},
    {"metal1", 2.69, 0.525, 2.76, 1.12, true},
    {"metal1", 1.635, 0.525, 1.705, 1.12, true},
    {"metal1", 0.25, 0.525, 1.705, 0.66, true},
};

inline constexpr GroupSpec kNangateBUFX16Groups[] = {
    {BindingKind::kPinNet, "A", kNangateBUFX16PinA, std::size(kNangateBUFX16PinA)},
    {BindingKind::kPinNet, "Z", kNangateBUFX16PinZ, std::size(kNangateBUFX16PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateBUFX16Power, std::size(kNangateBUFX16Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateBUFX16Ground, std::size(kNangateBUFX16Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateBUFX16ObsGroup0, std::size(kNangateBUFX16ObsGroup0)},
};

inline constexpr RectSpec kNangateBUFX2PinA[] = {
    {"metal1", 0.06, 0.525, 0.23, 0.7},
};

inline constexpr RectSpec kNangateBUFX2PinZ[] = {
    {"metal1", 0.465, 0.56, 0.7, 0.7},
    {"metal1", 0.465, 0.15, 0.535, 1.25},
};

inline constexpr RectSpec kNangateBUFX2Power[] = {
    {"metal1", 0.0, 1.315, 0.76, 1.485},
    {"metal1", 0.645, 0.975, 0.715, 1.485},
    {"metal1", 0.265, 1.04, 0.335, 1.485},
};

inline constexpr RectSpec kNangateBUFX2Ground[] = {
    {"metal1", 0.0, -0.085, 0.76, 0.085},
    {"metal1", 0.645, -0.085, 0.715, 0.425},
    {"metal1", 0.265, -0.085, 0.335, 0.285},
};

inline constexpr RectSpec kNangateBUFX2ObsGroup0[] = {
    {"metal1", 0.085, 0.82, 0.155, 1.25, true},
    {"metal1", 0.085, 0.82, 0.395, 0.89, true},
    {"metal1", 0.325, 0.39, 0.395, 0.89, true},
    {"metal1", 0.085, 0.39, 0.395, 0.46, true},
    {"metal1", 0.085, 0.15, 0.155, 0.46, true},
};

inline constexpr GroupSpec kNangateBUFX2Groups[] = {
    {BindingKind::kPinNet, "A", kNangateBUFX2PinA, std::size(kNangateBUFX2PinA)},
    {BindingKind::kPinNet, "Z", kNangateBUFX2PinZ, std::size(kNangateBUFX2PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateBUFX2Power, std::size(kNangateBUFX2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateBUFX2Ground, std::size(kNangateBUFX2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateBUFX2ObsGroup0, std::size(kNangateBUFX2ObsGroup0)},
};

inline constexpr RectSpec kNangateBUFX32PinA[] = {
    {"metal1", 0.1, 0.93, 2.8, 1.0},
    {"metal1", 2.665, 0.56, 2.8, 1.0},
    {"metal1", 1.905, 0.56, 2.04, 1.0},
    {"metal1", 1.12, 0.56, 1.255, 1.0},
    {"metal1", 0.1, 0.525, 0.17, 1.0},
};

inline constexpr RectSpec kNangateBUFX32PinZ[] = {
    {"metal1", 8.99, 0.15, 9.06, 1.25},
    {"metal1", 3.3, 0.28, 9.06, 0.42},
    {"metal1", 8.61, 0.15, 8.68, 0.785},
    {"metal1", 8.23, 0.15, 8.3, 0.785},
    {"metal1", 7.85, 0.15, 7.92, 0.785},
    {"metal1", 7.47, 0.15, 7.54, 0.785},
    {"metal1", 7.09, 0.15, 7.16, 0.785},
    {"metal1", 6.71, 0.15, 6.78, 0.785},
    {"metal1", 6.33, 0.15, 6.4, 0.785},
    {"metal1", 5.95, 0.15, 6.02, 0.785},
    {"metal1", 5.57, 0.15, 5.64, 0.785},
    {"metal1", 5.19, 0.15, 5.26, 0.785},
    {"metal1", 4.81, 0.15, 4.88, 0.785},
    {"metal1", 4.43, 0.15, 4.5, 0.785},
    {"metal1", 4.05, 0.15, 4.12, 0.785},
    {"metal1", 3.67, 0.15, 3.74, 0.785},
    {"metal1", 3.3, 0.15, 3.37, 0.785},
};

inline constexpr RectSpec kNangateBUFX32Power[] = {
    {"metal1", 0.0, 1.315, 9.31, 1.485},
    {"metal1", 9.18, 1.065, 9.25, 1.485},
    {"metal1", 8.8, 1.065, 8.87, 1.485},
    {"metal1", 8.42, 1.065, 8.49, 1.485},
    {"metal1", 8.04, 1.065, 8.11, 1.485},
    {"metal1", 7.66, 1.065, 7.73, 1.485},
    {"metal1", 7.28, 1.065, 7.35, 1.485},
    {"metal1", 6.9, 1.065, 6.97, 1.485},
    {"metal1", 6.52, 1.065, 6.59, 1.485},
    {"metal1", 6.14, 1.065, 6.21, 1.485},
    {"metal1", 5.76, 1.065, 5.83, 1.485},
    {"metal1", 5.38, 1.065, 5.45, 1.485},
    {"metal1", 5.0, 1.065, 5.07, 1.485},
    {"metal1", 4.62, 1.065, 4.69, 1.485},
    {"metal1", 4.24, 1.065, 4.31, 1.485},
    {"metal1", 3.86, 1.065, 3.93, 1.485},
    {"metal1", 3.48, 1.065, 3.55, 1.485},
    {"metal1", 3.08, 1.065, 3.15, 1.485},
    {"metal1", 2.695, 1.065, 2.765, 1.485},
    {"metal1", 2.315, 1.065, 2.385, 1.485},
    {"metal1", 1.935, 1.065, 2.005, 1.485},
    {"metal1", 1.555, 1.065, 1.625, 1.485},
    {"metal1", 1.175, 1.065, 1.245, 1.485},
    {"metal1", 0.795, 1.065, 0.865, 1.485},
    {"metal1", 0.415, 1.065, 0.485, 1.485},
    {"metal1", 0.04, 1.065, 0.11, 1.485},
};

inline constexpr RectSpec kNangateBUFX32Ground[] = {
    {"metal1", 0.0, -0.085, 9.31, 0.085},
    {"metal1", 9.18, -0.085, 9.25, 0.2},
    {"metal1", 8.8, -0.085, 8.87, 0.2},
    {"metal1", 8.42, -0.085, 8.49, 0.2},
    {"metal1", 8.04, -0.085, 8.11, 0.2},
    {"metal1", 7.66, -0.085, 7.73, 0.2},
    {"metal1", 7.28, -0.085, 7.35, 0.2},
    {"metal1", 6.9, -0.085, 6.97, 0.2},
    {"metal1", 6.52, -0.085, 6.59, 0.2},
    {"metal1", 6.14, -0.085, 6.21, 0.2},
    {"metal1", 5.76, -0.085, 5.83, 0.2},
    {"metal1", 5.38, -0.085, 5.45, 0.2},
    {"metal1", 5.0, -0.085, 5.07, 0.2},
    {"metal1", 4.62, -0.085, 4.69, 0.2},
    {"metal1", 4.24, -0.085, 4.31, 0.2},
    {"metal1", 3.86, -0.085, 3.93, 0.2},
    {"metal1", 3.48, -0.085, 3.55, 0.2},
    {"metal1", 3.08, -0.085, 3.15, 0.22},
    {"metal1", 2.695, -0.085, 2.765, 0.34},
    {"metal1", 2.315, -0.085, 2.385, 0.34},
    {"metal1", 1.935, -0.085, 2.005, 0.34},
    {"metal1", 1.555, -0.085, 1.625, 0.34},
    {"metal1", 1.175, -0.085, 1.245, 0.34},
    {"metal1", 0.795, -0.085, 0.865, 0.34},
    {"metal1", 0.415, -0.085, 0.485, 0.34},
    {"metal1", 0.04, -0.085, 0.11, 0.36},
};

inline constexpr RectSpec kNangateBUFX32ObsGroup0[] = {
    {"metal1", 3.165, 0.85, 8.88, 0.92, true},
    {"metal1", 8.745, 0.56, 8.88, 0.92, true},
    {"metal1", 2.885, 0.405, 2.955, 0.865, true},
    {"metal1", 2.505, 0.15, 2.575, 0.865, true},
    {"metal1", 2.13, 0.15, 2.2, 0.865, true},
    {"metal1", 1.745, 0.405, 1.815, 0.865, true},
    {"metal1", 1.365, 0.15, 1.435, 0.865, true},
    {"metal1", 0.985, 0.15, 1.055, 0.865, true},
    {"metal1", 0.615, 0.405, 0.685, 0.865, true},
    {"metal1", 0.235, 0.15, 0.305, 0.865, true},
    {"metal1", 7.605, 0.56, 7.74, 0.92, true},
    {"metal1", 6.465, 0.56, 6.6, 0.92, true},
    {"metal1", 5.325, 0.56, 5.46, 0.92, true},
    {"metal1", 4.185, 0.56, 4.32, 0.92, true},
    {"metal1", 3.165, 0.405, 3.235, 0.92, true},
    {"metal1", 0.235, 0.405, 3.235, 0.495, true},
    {"metal1", 2.89, 0.15, 2.96, 0.495, true},
    {"metal1", 1.75, 0.15, 1.82, 0.495, true},
    {"metal1", 0.605, 0.15, 0.675, 0.495, true},
};

inline constexpr GroupSpec kNangateBUFX32Groups[] = {
    {BindingKind::kPinNet, "A", kNangateBUFX32PinA, std::size(kNangateBUFX32PinA)},
    {BindingKind::kPinNet, "Z", kNangateBUFX32PinZ, std::size(kNangateBUFX32PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateBUFX32Power, std::size(kNangateBUFX32Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateBUFX32Ground, std::size(kNangateBUFX32Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateBUFX32ObsGroup0, std::size(kNangateBUFX32ObsGroup0)},
};

inline constexpr RectSpec kNangateBUFX4PinA[] = {
    {"metal1", 0.06, 0.525, 0.17, 0.7},
};

inline constexpr RectSpec kNangateBUFX4PinZ[] = {
    {"metal1", 0.995, 0.15, 1.065, 1.25},
    {"metal1", 0.615, 0.56, 1.065, 0.7},
    {"metal1", 0.615, 0.15, 0.685, 1.25},
};

inline constexpr RectSpec kNangateBUFX4Power[] = {
    {"metal1", 0.0, 1.315, 1.33, 1.485},
    {"metal1", 1.175, 0.975, 1.245, 1.485},
    {"metal1", 0.795, 0.975, 0.865, 1.485},
    {"metal1", 0.415, 0.975, 0.485, 1.485},
    {"metal1", 0.04, 0.975, 0.11, 1.485},
};

inline constexpr RectSpec kNangateBUFX4Ground[] = {
    {"metal1", 0.0, -0.085, 1.33, 0.085},
    {"metal1", 1.175, -0.085, 1.245, 0.37},
    {"metal1", 0.795, -0.085, 0.865, 0.37},
    {"metal1", 0.415, -0.085, 0.485, 0.37},
    {"metal1", 0.04, -0.085, 0.11, 0.37},
};

inline constexpr RectSpec kNangateBUFX4ObsGroup0[] = {
    {"metal1", 0.235, 0.15, 0.305, 1.25, true},
    {"metal1", 0.235, 0.525, 0.55, 0.66, true},
};

inline constexpr GroupSpec kNangateBUFX4Groups[] = {
    {BindingKind::kPinNet, "A", kNangateBUFX4PinA, std::size(kNangateBUFX4PinA)},
    {BindingKind::kPinNet, "Z", kNangateBUFX4PinZ, std::size(kNangateBUFX4PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateBUFX4Power, std::size(kNangateBUFX4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateBUFX4Ground, std::size(kNangateBUFX4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateBUFX4ObsGroup0, std::size(kNangateBUFX4ObsGroup0)},
};

inline constexpr RectSpec kNangateBUFX8PinA[] = {
    {"metal1", 0.06, 0.525, 0.17, 0.7},
};

inline constexpr RectSpec kNangateBUFX8PinZ[] = {
    {"metal1", 2.125, 0.15, 2.195, 1.25},
    {"metal1", 0.995, 0.56, 2.195, 0.7},
    {"metal1", 1.755, 0.56, 1.825, 1.25},
    {"metal1", 1.745, 0.15, 1.815, 0.7},
    {"metal1", 1.365, 0.15, 1.435, 1.25},
    {"metal1", 0.995, 0.15, 1.065, 1.25},
};

inline constexpr RectSpec kNangateBUFX8Power[] = {
    {"metal1", 0.0, 1.315, 2.47, 1.485},
    {"metal1", 2.315, 0.975, 2.385, 1.485},
    {"metal1", 1.935, 0.975, 2.005, 1.485},
    {"metal1", 1.555, 0.975, 1.625, 1.485},
    {"metal1", 1.175, 0.975, 1.245, 1.485},
    {"metal1", 0.795, 0.975, 0.865, 1.485},
    {"metal1", 0.415, 0.975, 0.485, 1.485},
    {"metal1", 0.04, 0.975, 0.11, 1.485},
};

inline constexpr RectSpec kNangateBUFX8Ground[] = {
    {"metal1", 0.0, -0.085, 2.47, 0.085},
    {"metal1", 2.315, -0.085, 2.385, 0.425},
    {"metal1", 1.935, -0.085, 2.005, 0.425},
    {"metal1", 1.555, -0.085, 1.625, 0.425},
    {"metal1", 1.185, -0.085, 1.255, 0.425},
    {"metal1", 0.795, -0.085, 0.865, 0.425},
    {"metal1", 0.415, -0.085, 0.485, 0.425},
    {"metal1", 0.04, -0.085, 0.11, 0.425},
};

inline constexpr RectSpec kNangateBUFX8ObsGroup0[] = {
    {"metal1", 0.605, 0.15, 0.675, 1.25, true},
    {"metal1", 0.235, 0.15, 0.305, 1.25, true},
    {"metal1", 0.235, 0.525, 0.925, 0.66, true},
};

inline constexpr GroupSpec kNangateBUFX8Groups[] = {
    {BindingKind::kPinNet, "A", kNangateBUFX8PinA, std::size(kNangateBUFX8PinA)},
    {BindingKind::kPinNet, "Z", kNangateBUFX8PinZ, std::size(kNangateBUFX8PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateBUFX8Power, std::size(kNangateBUFX8Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateBUFX8Ground, std::size(kNangateBUFX8Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateBUFX8ObsGroup0, std::size(kNangateBUFX8ObsGroup0)},
};

inline constexpr RectSpec kNangateCLKBUFX1PinA[] = {
    {"metal1", 0.06, 0.525, 0.21, 0.7},
};

inline constexpr RectSpec kNangateCLKBUFX1PinZ[] = {
    {"metal1", 0.44, 0.15, 0.51, 1.24},
};

inline constexpr RectSpec kNangateCLKBUFX1Power[] = {
    {"metal1", 0.0, 1.315, 0.57, 1.485},
    {"metal1", 0.245, 0.965, 0.315, 1.485},
};

inline constexpr RectSpec kNangateCLKBUFX1Ground[] = {
    {"metal1", 0.0, -0.085, 0.57, 0.085},
    {"metal1", 0.245, -0.085, 0.315, 0.285},
};

inline constexpr RectSpec kNangateCLKBUFX1ObsGroup0[] = {
    {"metal1", 0.065, 0.83, 0.135, 1.24, true},
    {"metal1", 0.065, 0.83, 0.37, 0.9, true},
    {"metal1", 0.3, 0.35, 0.37, 0.9, true},
    {"metal1", 0.065, 0.35, 0.37, 0.42, true},
    {"metal1", 0.065, 0.15, 0.135, 0.42, true},
};

inline constexpr GroupSpec kNangateCLKBUFX1Groups[] = {
    {BindingKind::kPinNet, "A", kNangateCLKBUFX1PinA, std::size(kNangateCLKBUFX1PinA)},
    {BindingKind::kPinNet, "Z", kNangateCLKBUFX1PinZ, std::size(kNangateCLKBUFX1PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateCLKBUFX1Power, std::size(kNangateCLKBUFX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateCLKBUFX1Ground, std::size(kNangateCLKBUFX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateCLKBUFX1ObsGroup0, std::size(kNangateCLKBUFX1ObsGroup0)},
};

inline constexpr RectSpec kNangateCLKBUFX2PinA[] = {
    {"metal1", 0.06, 0.525, 0.19, 0.7},
};

inline constexpr RectSpec kNangateCLKBUFX2PinZ[] = {
    {"metal1", 0.425, 0.15, 0.51, 1.25},
};

inline constexpr RectSpec kNangateCLKBUFX2Power[] = {
    {"metal1", 0.0, 1.315, 0.76, 1.485},
    {"metal1", 0.605, 0.975, 0.675, 1.485},
    {"metal1", 0.225, 1.04, 0.295, 1.485},
};

inline constexpr RectSpec kNangateCLKBUFX2Ground[] = {
    {"metal1", 0.0, -0.085, 0.76, 0.085},
    {"metal1", 0.605, -0.085, 0.675, 0.285},
    {"metal1", 0.225, -0.085, 0.295, 0.285},
};

inline constexpr RectSpec kNangateCLKBUFX2ObsGroup0[] = {
    {"metal1", 0.045, 0.905, 0.115, 1.25, true},
    {"metal1", 0.045, 0.905, 0.36, 0.975, true},
    {"metal1", 0.29, 0.35, 0.36, 0.975, true},
    {"metal1", 0.045, 0.35, 0.36, 0.42, true},
    {"metal1", 0.045, 0.15, 0.115, 0.42, true},
};

inline constexpr GroupSpec kNangateCLKBUFX2Groups[] = {
    {BindingKind::kPinNet, "A", kNangateCLKBUFX2PinA, std::size(kNangateCLKBUFX2PinA)},
    {BindingKind::kPinNet, "Z", kNangateCLKBUFX2PinZ, std::size(kNangateCLKBUFX2PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateCLKBUFX2Power, std::size(kNangateCLKBUFX2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateCLKBUFX2Ground, std::size(kNangateCLKBUFX2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateCLKBUFX2ObsGroup0, std::size(kNangateCLKBUFX2ObsGroup0)},
};

inline constexpr RectSpec kNangateCLKBUFX3PinA[] = {
    {"metal1", 0.06, 0.525, 0.19, 0.7},
};

inline constexpr RectSpec kNangateCLKBUFX3PinZ[] = {
    {"metal1", 0.795, 0.18, 0.865, 1.175},
    {"metal1", 0.425, 0.42, 0.865, 0.56},
    {"metal1", 0.425, 0.18, 0.495, 1.175},
};

inline constexpr RectSpec kNangateCLKBUFX3Power[] = {
    {"metal1", 0.0, 1.315, 0.95, 1.485},
    {"metal1", 0.605, 0.9, 0.675, 1.485},
    {"metal1", 0.225, 0.9, 0.295, 1.485},
};

inline constexpr RectSpec kNangateCLKBUFX3Ground[] = {
    {"metal1", 0.0, -0.085, 0.95, 0.085},
    {"metal1", 0.605, -0.085, 0.675, 0.235},
    {"metal1", 0.225, -0.085, 0.295, 0.235},
};

inline constexpr RectSpec kNangateCLKBUFX3ObsGroup0[] = {
    {"metal1", 0.045, 0.765, 0.115, 1.175, true},
    {"metal1", 0.045, 0.765, 0.355, 0.835, true},
    {"metal1", 0.285, 0.38, 0.355, 0.835, true},
    {"metal1", 0.045, 0.38, 0.355, 0.45, true},
    {"metal1", 0.045, 0.18, 0.115, 0.45, true},
};

inline constexpr GroupSpec kNangateCLKBUFX3Groups[] = {
    {BindingKind::kPinNet, "A", kNangateCLKBUFX3PinA, std::size(kNangateCLKBUFX3PinA)},
    {BindingKind::kPinNet, "Z", kNangateCLKBUFX3PinZ, std::size(kNangateCLKBUFX3PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateCLKBUFX3Power, std::size(kNangateCLKBUFX3Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateCLKBUFX3Ground, std::size(kNangateCLKBUFX3Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateCLKBUFX3ObsGroup0, std::size(kNangateCLKBUFX3ObsGroup0)},
};

inline constexpr RectSpec kNangateCLKGATETSTX1PinCK[] = {
    {"metal1", 2.075, 0.7, 2.22, 0.84},
};

inline constexpr RectSpec kNangateCLKGATETSTX1PinE[] = {
    {"metal1", 0.25, 0.7, 0.38, 0.84},
};

inline constexpr RectSpec kNangateCLKGATETSTX1PinSE[] = {
    {"metal1", 0.06, 0.7, 0.185, 0.84},
};

inline constexpr RectSpec kNangateCLKGATETSTX1PinGCK[] = {
    {"metal1", 2.705, 0.35, 2.79, 1.235},
};

inline constexpr RectSpec kNangateCLKGATETSTX1Power[] = {
    {"metal1", 0.0, 1.315, 2.85, 1.485},
    {"metal1", 2.48, 1.045, 2.615, 1.485},
    {"metal1", 2.135, 0.94, 2.205, 1.485},
    {"metal1", 1.755, 0.94, 1.825, 1.485},
    {"metal1", 1.185, 1.01, 1.32, 1.485},
    {"metal1", 0.385, 1.04, 0.52, 1.485},
};

inline constexpr RectSpec kNangateCLKGATETSTX1Ground[] = {
    {"metal1", 0.0, -0.085, 2.85, 0.085},
    {"metal1", 2.485, -0.085, 2.62, 0.385},
    {"metal1", 1.75, -0.085, 1.82, 0.42},
    {"metal1", 1.185, -0.085, 1.32, 0.38},
    {"metal1", 0.385, -0.085, 0.52, 0.385},
    {"metal1", 0.04, -0.085, 0.11, 0.42},
};

inline constexpr RectSpec kNangateCLKGATETSTX1ObsGroup0[] = {
    {"metal1", 2.33, 0.525, 2.4, 1.005, true},
    {"metal1", 2.33, 0.525, 2.64, 0.66, true},
    {"metal1", 2.14, 0.525, 2.64, 0.595, true},
    {"metal1", 2.14, 0.285, 2.21, 0.595, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX1ObsGroup1[] = {
    {"metal1", 1.935, 0.15, 2.005, 1.21, true},
    {"metal1", 1.935, 0.15, 2.07, 0.22, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX1ObsGroup2[] = {
    {"metal1", 1.565, 0.93, 1.69, 1.205, true},
    {"metal1", 1.62, 0.585, 1.69, 1.205, true},
    {"metal1", 1.105, 0.585, 1.69, 0.655, true},
    {"metal1", 1.565, 0.285, 1.635, 0.655, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX1ObsGroup3[] = {
    {"metal1", 0.805, 0.285, 0.875, 1.095, true},
    {"metal1", 0.805, 0.735, 1.555, 0.805, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX1ObsGroup4[] = {
    {"metal1", 1.405, 0.875, 1.475, 1.235, true},
    {"metal1", 0.67, 1.16, 1.12, 1.23, true},
    {"metal1", 1.05, 0.875, 1.12, 1.23, true},
    {"metal1", 0.67, 0.15, 0.74, 1.23, true},
    {"metal1", 1.05, 0.875, 1.475, 0.945, true},
    {"metal1", 0.945, 0.445, 1.475, 0.515, true},
    {"metal1", 1.405, 0.285, 1.475, 0.515, true},
    {"metal1", 0.945, 0.15, 1.015, 0.515, true},
    {"metal1", 0.67, 0.15, 1.015, 0.22, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX1ObsGroup5[] = {
    {"metal1", 0.045, 0.905, 0.115, 1.235, true},
    {"metal1", 0.045, 0.905, 0.57, 0.975, true},
    {"metal1", 0.5, 0.45, 0.57, 0.975, true},
    {"metal1", 0.235, 0.45, 0.57, 0.52, true},
    {"metal1", 0.235, 0.285, 0.305, 0.52, true},
};

inline constexpr GroupSpec kNangateCLKGATETSTX1Groups[] = {
    {BindingKind::kPinNet, "CK", kNangateCLKGATETSTX1PinCK, std::size(kNangateCLKGATETSTX1PinCK)},
    {BindingKind::kPinNet, "E", kNangateCLKGATETSTX1PinE, std::size(kNangateCLKGATETSTX1PinE)},
    {BindingKind::kPinNet, "SE", kNangateCLKGATETSTX1PinSE, std::size(kNangateCLKGATETSTX1PinSE)},
    {BindingKind::kPinNet, "GCK", kNangateCLKGATETSTX1PinGCK, std::size(kNangateCLKGATETSTX1PinGCK)},
    {BindingKind::kSupplyNet, "POWER", kNangateCLKGATETSTX1Power, std::size(kNangateCLKGATETSTX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateCLKGATETSTX1Ground, std::size(kNangateCLKGATETSTX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateCLKGATETSTX1ObsGroup0, std::size(kNangateCLKGATETSTX1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateCLKGATETSTX1ObsGroup1, std::size(kNangateCLKGATETSTX1ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateCLKGATETSTX1ObsGroup2, std::size(kNangateCLKGATETSTX1ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateCLKGATETSTX1ObsGroup3, std::size(kNangateCLKGATETSTX1ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateCLKGATETSTX1ObsGroup4, std::size(kNangateCLKGATETSTX1ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateCLKGATETSTX1ObsGroup5, std::size(kNangateCLKGATETSTX1ObsGroup5)},
};

inline constexpr RectSpec kNangateCLKGATETSTX2PinCK[] = {
    {"metal1", 2.18, 0.85, 2.825, 0.92},
    {"metal1", 2.72, 0.525, 2.825, 0.92},
    {"metal1", 2.18, 0.525, 2.25, 0.92},
};

inline constexpr RectSpec kNangateCLKGATETSTX2PinE[] = {
    {"metal1", 0.25, 0.56, 0.375, 0.725},
};

inline constexpr RectSpec kNangateCLKGATETSTX2PinSE[] = {
    {"metal1", 0.44, 0.56, 0.545, 0.725},
};

inline constexpr RectSpec kNangateCLKGATETSTX2PinGCK[] = {
    {"metal1", 2.52, 0.15, 2.6, 0.785},
};

inline constexpr RectSpec kNangateCLKGATETSTX2Power[] = {
    {"metal1", 0.0, 1.315, 3.04, 1.485},
    {"metal1", 2.675, 1.24, 2.81, 1.485},
    {"metal1", 2.275, 1.24, 2.41, 1.485},
    {"metal1", 1.83, 1.24, 1.965, 1.485},
    {"metal1", 1.515, 0.91, 1.585, 1.485},
    {"metal1", 0.73, 1.115, 0.865, 1.485},
    {"metal1", 0.225, 0.94, 0.295, 1.485},
};

inline constexpr RectSpec kNangateCLKGATETSTX2Ground[] = {
    {"metal1", 0.0, -0.085, 3.04, 0.085},
    {"metal1", 2.7, -0.085, 2.77, 0.195},
    {"metal1", 2.325, -0.085, 2.395, 0.195},
    {"metal1", 1.765, -0.085, 1.9, 0.185},
    {"metal1", 1.45, -0.085, 1.52, 0.405},
    {"metal1", 0.605, -0.085, 0.675, 0.285},
    {"metal1", 0.225, -0.085, 0.295, 0.285},
};

inline constexpr RectSpec kNangateCLKGATETSTX2ObsGroup0[] = {
    {"metal1", 1.68, 1.08, 1.75, 1.245, true},
    {"metal1", 2.895, 0.15, 2.965, 1.24, true},
    {"metal1", 1.68, 1.08, 2.965, 1.15, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX2ObsGroup1[] = {
    {"metal1", 2.045, 0.39, 2.115, 0.925, true},
    {"metal1", 2.045, 0.39, 2.45, 0.46, true},
    {"metal1", 2.17, 0.325, 2.45, 0.46, true},
    {"metal1", 2.17, 0.15, 2.24, 0.46, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX2ObsGroup2[] = {
    {"metal1", 1.38, 0.76, 1.775, 0.83, true},
    {"metal1", 1.705, 0.28, 1.775, 0.83, true},
    {"metal1", 1.61, 0.28, 1.775, 0.35, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX2ObsGroup3[] = {
    {"metal1", 1.145, 0.285, 1.215, 1.03, true},
    {"metal1", 1.145, 0.525, 1.63, 0.66, true},
    {"metal1", 1.08, 0.285, 1.215, 0.42, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX2ObsGroup4[] = {
    {"metal1", 0.045, 0.15, 0.115, 1.125, true},
    {"metal1", 0.41, 0.95, 1.015, 1.02, true},
    {"metal1", 0.945, 0.15, 1.015, 1.02, true},
    {"metal1", 0.41, 0.805, 0.48, 1.02, true},
    {"metal1", 0.045, 0.805, 0.48, 0.875, true},
    {"metal1", 0.945, 0.61, 1.08, 0.745, true},
    {"metal1", 0.945, 0.15, 1.285, 0.22, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX2ObsGroup5[] = {
    {"metal1", 0.61, 0.41, 0.68, 0.885, true},
    {"metal1", 0.61, 0.41, 0.87, 0.545, true},
    {"metal1", 0.425, 0.41, 0.87, 0.48, true},
    {"metal1", 0.425, 0.15, 0.495, 0.48, true},
};

inline constexpr GroupSpec kNangateCLKGATETSTX2Groups[] = {
    {BindingKind::kPinNet, "CK", kNangateCLKGATETSTX2PinCK, std::size(kNangateCLKGATETSTX2PinCK)},
    {BindingKind::kPinNet, "E", kNangateCLKGATETSTX2PinE, std::size(kNangateCLKGATETSTX2PinE)},
    {BindingKind::kPinNet, "SE", kNangateCLKGATETSTX2PinSE, std::size(kNangateCLKGATETSTX2PinSE)},
    {BindingKind::kPinNet, "GCK", kNangateCLKGATETSTX2PinGCK, std::size(kNangateCLKGATETSTX2PinGCK)},
    {BindingKind::kSupplyNet, "POWER", kNangateCLKGATETSTX2Power, std::size(kNangateCLKGATETSTX2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateCLKGATETSTX2Ground, std::size(kNangateCLKGATETSTX2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateCLKGATETSTX2ObsGroup0, std::size(kNangateCLKGATETSTX2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateCLKGATETSTX2ObsGroup1, std::size(kNangateCLKGATETSTX2ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateCLKGATETSTX2ObsGroup2, std::size(kNangateCLKGATETSTX2ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateCLKGATETSTX2ObsGroup3, std::size(kNangateCLKGATETSTX2ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateCLKGATETSTX2ObsGroup4, std::size(kNangateCLKGATETSTX2ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateCLKGATETSTX2ObsGroup5, std::size(kNangateCLKGATETSTX2ObsGroup5)},
};

inline constexpr RectSpec kNangateCLKGATETSTX4PinCK[] = {
    {"metal1", 2.21, 0.77, 2.85, 0.85},
    {"metal1", 2.72, 0.525, 2.85, 0.85},
    {"metal1", 2.21, 0.525, 2.28, 0.85},
};

inline constexpr RectSpec kNangateCLKGATETSTX4PinE[] = {
    {"metal1", 0.25, 0.56, 0.38, 0.775},
};

inline constexpr RectSpec kNangateCLKGATETSTX4PinSE[] = {
    {"metal1", 0.06, 0.56, 0.185, 0.775},
};

inline constexpr RectSpec kNangateCLKGATETSTX4PinGCK[] = {
    {"metal1", 3.455, 0.18, 3.525, 0.925},
    {"metal1", 3.085, 0.42, 3.525, 0.56},
    {"metal1", 3.085, 0.18, 3.155, 0.925},
};

inline constexpr RectSpec kNangateCLKGATETSTX4Power[] = {
    {"metal1", 0.0, 1.315, 3.8, 1.485},
    {"metal1", 3.645, 0.975, 3.715, 1.485},
    {"metal1", 3.265, 0.975, 3.335, 1.485},
    {"metal1", 2.885, 1.2, 2.955, 1.485},
    {"metal1", 2.505, 1.2, 2.575, 1.485},
    {"metal1", 2.13, 1.205, 2.2, 1.485},
    {"metal1", 1.49, 1.165, 1.625, 1.485},
    {"metal1", 0.755, 1.13, 0.825, 1.485},
    {"metal1", 0.415, 0.975, 0.485, 1.485},
};

inline constexpr RectSpec kNangateCLKGATETSTX4Ground[] = {
    {"metal1", 0.0, -0.085, 3.8, 0.085},
    {"metal1", 3.645, -0.085, 3.715, 0.2},
    {"metal1", 3.265, -0.085, 3.335, 0.2},
    {"metal1", 2.885, -0.085, 2.955, 0.2},
    {"metal1", 2.125, -0.085, 2.195, 0.285},
    {"metal1", 1.53, -0.085, 1.6, 0.285},
    {"metal1", 0.755, -0.085, 0.825, 0.195},
    {"metal1", 0.415, -0.085, 0.485, 0.285},
    {"metal1", 0.04, -0.085, 0.11, 0.285},
};

inline constexpr RectSpec kNangateCLKGATETSTX4ObsGroup0[] = {
    {"metal1", 2.29, 0.93, 3.015, 1.0, true},
    {"metal1", 2.945, 0.35, 3.015, 1.0, true},
    {"metal1", 2.655, 0.35, 3.015, 0.42, true},
    {"metal1", 2.655, 0.185, 2.725, 0.42, true},
    {"metal1", 2.48, 0.185, 2.725, 0.255, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX4ObsGroup1[] = {
    {"metal1", 1.13, 1.03, 1.205, 1.25, true},
    {"metal1", 1.13, 1.03, 2.125, 1.1, true},
    {"metal1", 2.055, 0.39, 2.125, 1.1, true},
    {"metal1", 1.13, 0.525, 1.2, 1.25, true},
    {"metal1", 2.425, 0.39, 2.495, 0.66, true},
    {"metal1", 1.13, 0.525, 1.645, 0.66, true},
    {"metal1", 1.39, 0.185, 1.46, 0.66, true},
    {"metal1", 2.055, 0.39, 2.495, 0.46, true},
    {"metal1", 1.11, 0.185, 1.46, 0.255, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX4ObsGroup2[] = {
    {"metal1", 1.265, 0.865, 1.99, 0.935, true},
    {"metal1", 1.92, 0.15, 1.99, 0.935, true},
    {"metal1", 1.265, 0.795, 1.335, 0.935, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX4ObsGroup3[] = {
    {"metal1", 1.405, 0.725, 1.78, 0.795, true},
    {"metal1", 1.71, 0.15, 1.78, 0.795, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX4ObsGroup4[] = {
    {"metal1", 0.575, 0.975, 0.645, 1.25, true},
    {"metal1", 0.575, 0.975, 1.065, 1.045, true},
    {"metal1", 0.975, 0.39, 1.065, 1.045, true},
    {"metal1", 0.975, 0.39, 1.325, 0.46, true},
    {"metal1", 0.975, 0.26, 1.045, 1.045, true},
    {"metal1", 0.575, 0.26, 1.045, 0.33, true},
    {"metal1", 0.575, 0.15, 0.645, 0.33, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX4ObsGroup5[] = {
    {"metal1", 0.045, 0.84, 0.115, 1.25, true},
    {"metal1", 0.045, 0.84, 0.91, 0.91, true},
    {"metal1", 0.84, 0.415, 0.91, 0.91, true},
    {"metal1", 0.235, 0.415, 0.91, 0.485, true},
    {"metal1", 0.235, 0.15, 0.335, 0.485, true},
};

inline constexpr GroupSpec kNangateCLKGATETSTX4Groups[] = {
    {BindingKind::kPinNet, "CK", kNangateCLKGATETSTX4PinCK, std::size(kNangateCLKGATETSTX4PinCK)},
    {BindingKind::kPinNet, "E", kNangateCLKGATETSTX4PinE, std::size(kNangateCLKGATETSTX4PinE)},
    {BindingKind::kPinNet, "SE", kNangateCLKGATETSTX4PinSE, std::size(kNangateCLKGATETSTX4PinSE)},
    {BindingKind::kPinNet, "GCK", kNangateCLKGATETSTX4PinGCK, std::size(kNangateCLKGATETSTX4PinGCK)},
    {BindingKind::kSupplyNet, "POWER", kNangateCLKGATETSTX4Power, std::size(kNangateCLKGATETSTX4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateCLKGATETSTX4Ground, std::size(kNangateCLKGATETSTX4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateCLKGATETSTX4ObsGroup0, std::size(kNangateCLKGATETSTX4ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateCLKGATETSTX4ObsGroup1, std::size(kNangateCLKGATETSTX4ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateCLKGATETSTX4ObsGroup2, std::size(kNangateCLKGATETSTX4ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateCLKGATETSTX4ObsGroup3, std::size(kNangateCLKGATETSTX4ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateCLKGATETSTX4ObsGroup4, std::size(kNangateCLKGATETSTX4ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateCLKGATETSTX4ObsGroup5, std::size(kNangateCLKGATETSTX4ObsGroup5)},
};

inline constexpr RectSpec kNangateCLKGATETSTX8PinCK[] = {
    {"metal1", 2.385, 0.845, 3.925, 0.915},
    {"metal1", 3.855, 0.56, 3.925, 0.915},
    {"metal1", 3.765, 0.56, 3.925, 0.63},
    {"metal1", 3.1, 0.56, 3.17, 0.915},
    {"metal1", 3.035, 0.56, 3.17, 0.63},
    {"metal1", 2.385, 0.525, 2.455, 0.915},
};

inline constexpr RectSpec kNangateCLKGATETSTX8PinE[] = {
    {"metal1", 0.33, 0.7, 0.51, 0.84},
};

inline constexpr RectSpec kNangateCLKGATETSTX8PinSE[] = {
    {"metal1", 0.06, 0.7, 0.25, 0.84},
};

inline constexpr RectSpec kNangateCLKGATETSTX8PinGCK[] = {
    {"metal1", 5.205, 0.15, 5.275, 1.25},
    {"metal1", 4.12, 0.56, 5.275, 0.7},
    {"metal1", 4.825, 0.15, 4.895, 1.25},
    {"metal1", 4.445, 0.15, 4.515, 1.25},
    {"metal1", 4.075, 0.975, 4.19, 1.25},
    {"metal1", 4.12, 0.15, 4.19, 1.25},
    {"metal1", 4.075, 0.15, 4.19, 0.285},
};

inline constexpr RectSpec kNangateCLKGATETSTX8Power[] = {
    {"metal1", 0.0, 1.315, 5.51, 1.485},
    {"metal1", 5.395, 0.975, 5.465, 1.485},
    {"metal1", 5.015, 0.975, 5.085, 1.485},
    {"metal1", 4.635, 0.975, 4.705, 1.485},
    {"metal1", 4.26, 0.975, 4.33, 1.485},
    {"metal1", 3.845, 1.01, 3.98, 1.485},
    {"metal1", 3.465, 1.01, 3.6, 1.485},
    {"metal1", 3.085, 1.01, 3.22, 1.485},
    {"metal1", 2.705, 1.01, 2.84, 1.485},
    {"metal1", 2.365, 1.06, 2.435, 1.485},
    {"metal1", 1.915, 1.1, 2.05, 1.485},
    {"metal1", 1.535, 1.1, 1.67, 1.485},
    {"metal1", 0.75, 1.24, 0.885, 1.485},
    {"metal1", 0.41, 1.215, 0.545, 1.485},
};

inline constexpr RectSpec kNangateCLKGATETSTX8Ground[] = {
    {"metal1", 0.0, -0.085, 5.51, 0.085},
    {"metal1", 5.395, -0.085, 5.465, 0.285},
    {"metal1", 5.015, -0.085, 5.085, 0.285},
    {"metal1", 4.635, -0.085, 4.705, 0.285},
    {"metal1", 4.255, -0.085, 4.325, 0.285},
    {"metal1", 3.845, -0.085, 3.98, 0.25},
    {"metal1", 3.085, -0.085, 3.22, 0.16},
    {"metal1", 2.33, -0.085, 2.465, 0.16},
    {"metal1", 1.95, -0.085, 2.02, 0.425},
    {"metal1", 1.575, -0.085, 1.645, 0.265},
    {"metal1", 0.75, -0.085, 0.885, 0.175},
    {"metal1", 0.44, -0.085, 0.51, 0.285},
    {"metal1", 0.065, -0.085, 0.135, 0.285},
};

inline constexpr RectSpec kNangateCLKGATETSTX8ObsGroup0[] = {
    {"metal1", 3.235, 0.71, 3.79, 0.78, true},
    {"metal1", 2.52, 0.71, 3.03, 0.78, true},
    {"metal1", 3.235, 0.705, 3.7, 0.78, true},
    {"metal1", 3.63, 0.16, 3.7, 0.78, true},
    {"metal1", 2.9, 0.425, 2.97, 0.78, true},
    {"metal1", 3.235, 0.425, 3.305, 0.78, true},
    {"metal1", 2.71, 0.425, 3.305, 0.495, true},
    {"metal1", 3.63, 0.35, 4.055, 0.485, true},
    {"metal1", 3.47, 0.16, 3.7, 0.23, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX8ObsGroup1[] = {
    {"metal1", 1.16, 0.56, 1.23, 1.185, true},
    {"metal1", 1.16, 0.965, 2.305, 1.035, true},
    {"metal1", 2.235, 0.29, 2.305, 1.035, true},
    {"metal1", 2.575, 0.56, 2.735, 0.63, true},
    {"metal1", 1.16, 0.56, 1.75, 0.63, true},
    {"metal1", 3.37, 0.555, 3.52, 0.625, true},
    {"metal1", 2.575, 0.29, 2.645, 0.63, true},
    {"metal1", 1.435, 0.18, 1.505, 0.63, true},
    {"metal1", 3.37, 0.29, 3.44, 0.625, true},
    {"metal1", 2.235, 0.29, 3.44, 0.36, true},
    {"metal1", 1.155, 0.18, 1.505, 0.25, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX8ObsGroup2[] = {
    {"metal1", 1.315, 0.83, 2.17, 0.9, true},
    {"metal1", 2.1, 0.195, 2.17, 0.9, true},
    {"metal1", 1.315, 0.715, 1.385, 0.9, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX8ObsGroup3[] = {
    {"metal1", 1.45, 0.695, 1.885, 0.765, true},
    {"metal1", 1.815, 0.185, 1.885, 0.765, true},
    {"metal1", 1.73, 0.185, 1.885, 0.39, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX8ObsGroup4[] = {
    {"metal1", 0.565, 1.065, 1.085, 1.135, true},
    {"metal1", 1.015, 0.25, 1.085, 1.135, true},
    {"metal1", 1.015, 0.425, 1.37, 0.495, true},
    {"metal1", 0.6, 0.25, 1.085, 0.32, true},
    {"metal1", 0.6, 0.15, 0.67, 0.32, true},
};

inline constexpr RectSpec kNangateCLKGATETSTX8ObsGroup5[] = {
    {"metal1", 0.07, 0.905, 0.14, 1.25, true},
    {"metal1", 0.07, 0.905, 0.95, 0.975, true},
    {"metal1", 0.87, 0.42, 0.95, 0.975, true},
    {"metal1", 0.26, 0.42, 0.95, 0.49, true},
    {"metal1", 0.26, 0.15, 0.33, 0.49, true},
};

inline constexpr GroupSpec kNangateCLKGATETSTX8Groups[] = {
    {BindingKind::kPinNet, "CK", kNangateCLKGATETSTX8PinCK, std::size(kNangateCLKGATETSTX8PinCK)},
    {BindingKind::kPinNet, "E", kNangateCLKGATETSTX8PinE, std::size(kNangateCLKGATETSTX8PinE)},
    {BindingKind::kPinNet, "SE", kNangateCLKGATETSTX8PinSE, std::size(kNangateCLKGATETSTX8PinSE)},
    {BindingKind::kPinNet, "GCK", kNangateCLKGATETSTX8PinGCK, std::size(kNangateCLKGATETSTX8PinGCK)},
    {BindingKind::kSupplyNet, "POWER", kNangateCLKGATETSTX8Power, std::size(kNangateCLKGATETSTX8Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateCLKGATETSTX8Ground, std::size(kNangateCLKGATETSTX8Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateCLKGATETSTX8ObsGroup0, std::size(kNangateCLKGATETSTX8ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateCLKGATETSTX8ObsGroup1, std::size(kNangateCLKGATETSTX8ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateCLKGATETSTX8ObsGroup2, std::size(kNangateCLKGATETSTX8ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateCLKGATETSTX8ObsGroup3, std::size(kNangateCLKGATETSTX8ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateCLKGATETSTX8ObsGroup4, std::size(kNangateCLKGATETSTX8ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateCLKGATETSTX8ObsGroup5, std::size(kNangateCLKGATETSTX8ObsGroup5)},
};

inline constexpr RectSpec kNangateCLKGATEX1PinCK[] = {
    {"metal1", 1.54, 0.42, 1.895, 0.56},
};

inline constexpr RectSpec kNangateCLKGATEX1PinE[] = {
    {"metal1", 0.91, 0.525, 1.08, 0.7},
};

inline constexpr RectSpec kNangateCLKGATEX1PinGCK[] = {
    {"metal1", 2.31, 0.175, 2.41, 1.09},
};

inline constexpr RectSpec kNangateCLKGATEX1Power[] = {
    {"metal1", 0.0, 1.315, 2.47, 1.485},
    {"metal1", 2.03, 0.915, 2.1, 1.485},
    {"metal1", 1.585, 0.89, 1.655, 1.485},
    {"metal1", 0.955, 0.9, 1.09, 1.485},
    {"metal1", 0.225, 0.955, 0.295, 1.485},
};

inline constexpr RectSpec kNangateCLKGATEX1Ground[] = {
    {"metal1", 0.0, -0.085, 2.47, 0.085},
    {"metal1", 2.12, -0.085, 2.19, 0.225},
    {"metal1", 1.585, -0.085, 1.655, 0.195},
    {"metal1", 0.985, -0.085, 1.055, 0.32},
    {"metal1", 0.225, -0.085, 0.295, 0.32},
};

inline constexpr RectSpec kNangateCLKGATEX1ObsGroup0[] = {
    {"metal1", 1.785, 0.765, 1.855, 1.09, true},
    {"metal1", 1.785, 0.765, 2.245, 0.835, true},
    {"metal1", 2.175, 0.35, 2.245, 0.835, true},
    {"metal1", 1.97, 0.35, 2.245, 0.42, true},
    {"metal1", 1.97, 0.185, 2.04, 0.42, true},
};

inline constexpr RectSpec kNangateCLKGATEX1ObsGroup1[] = {
    {"metal1", 1.405, 0.195, 1.475, 1.09, true},
    {"metal1", 1.145, 0.525, 1.475, 0.66, true},
};

inline constexpr RectSpec kNangateCLKGATEX1ObsGroup2[] = {
    {"metal1", 1.175, 0.765, 1.245, 1.05, true},
    {"metal1", 0.695, 0.765, 1.245, 0.835, true},
    {"metal1", 0.695, 0.39, 0.765, 0.835, true},
    {"metal1", 0.695, 0.39, 1.245, 0.46, true},
    {"metal1", 1.175, 0.27, 1.245, 0.46, true},
};

inline constexpr RectSpec kNangateCLKGATEX1ObsGroup3[] = {
    {"metal1", 0.51, 0.98, 0.715, 1.05, true},
    {"metal1", 0.51, 0.22, 0.58, 1.05, true},
    {"metal1", 0.175, 0.59, 0.58, 0.725, true},
    {"metal1", 0.51, 0.22, 0.71, 0.29, true},
};

inline constexpr RectSpec kNangateCLKGATEX1ObsGroup4[] = {
    {"metal1", 0.04, 0.265, 0.11, 1.04, true},
    {"metal1", 0.04, 0.45, 0.44, 0.52, true},
};

inline constexpr GroupSpec kNangateCLKGATEX1Groups[] = {
    {BindingKind::kPinNet, "CK", kNangateCLKGATEX1PinCK, std::size(kNangateCLKGATEX1PinCK)},
    {BindingKind::kPinNet, "E", kNangateCLKGATEX1PinE, std::size(kNangateCLKGATEX1PinE)},
    {BindingKind::kPinNet, "GCK", kNangateCLKGATEX1PinGCK, std::size(kNangateCLKGATEX1PinGCK)},
    {BindingKind::kSupplyNet, "POWER", kNangateCLKGATEX1Power, std::size(kNangateCLKGATEX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateCLKGATEX1Ground, std::size(kNangateCLKGATEX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateCLKGATEX1ObsGroup0, std::size(kNangateCLKGATEX1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateCLKGATEX1ObsGroup1, std::size(kNangateCLKGATEX1ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateCLKGATEX1ObsGroup2, std::size(kNangateCLKGATEX1ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateCLKGATEX1ObsGroup3, std::size(kNangateCLKGATEX1ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateCLKGATEX1ObsGroup4, std::size(kNangateCLKGATEX1ObsGroup4)},
};

inline constexpr RectSpec kNangateCLKGATEX2PinCK[] = {
    {"metal1", 1.58, 0.42, 1.65, 0.66},
};

inline constexpr RectSpec kNangateCLKGATEX2PinE[] = {
    {"metal1", 0.34, 0.42, 0.51, 0.59},
};

inline constexpr RectSpec kNangateCLKGATEX2PinGCK[] = {
    {"metal1", 2.32, 0.185, 2.41, 1.215},
};

inline constexpr RectSpec kNangateCLKGATEX2Power[] = {
    {"metal1", 0.0, 1.315, 2.66, 1.485},
    {"metal1", 2.505, 0.94, 2.575, 1.485},
    {"metal1", 2.095, 0.94, 2.165, 1.485},
    {"metal1", 1.725, 0.89, 1.795, 1.485},
    {"metal1", 0.985, 0.98, 1.055, 1.485},
    {"metal1", 0.225, 0.94, 0.295, 1.485},
};

inline constexpr RectSpec kNangateCLKGATEX2Ground[] = {
    {"metal1", 0.0, -0.085, 2.66, 0.085},
    {"metal1", 2.505, -0.085, 2.575, 0.22},
    {"metal1", 2.095, -0.085, 2.165, 0.22},
    {"metal1", 1.565, -0.085, 1.635, 0.235},
    {"metal1", 0.955, -0.085, 1.09, 0.285},
    {"metal1", 0.225, -0.085, 0.295, 0.32},
};

inline constexpr RectSpec kNangateCLKGATEX2ObsGroup0[] = {
    {"metal1", 1.915, 0.805, 1.985, 1.215, true},
    {"metal1", 1.915, 0.805, 2.255, 0.875, true},
    {"metal1", 2.185, 0.39, 2.255, 0.875, true},
    {"metal1", 1.725, 0.39, 2.255, 0.46, true},
    {"metal1", 1.725, 0.185, 1.795, 0.46, true},
};

inline constexpr RectSpec kNangateCLKGATEX2ObsGroup1[] = {
    {"metal1", 1.12, 1.18, 1.64, 1.25, true},
    {"metal1", 1.57, 0.755, 1.64, 1.25, true},
    {"metal1", 0.36, 1.18, 0.92, 1.25, true},
    {"metal1", 0.85, 0.79, 0.92, 1.25, true},
    {"metal1", 1.12, 0.79, 1.19, 1.25, true},
    {"metal1", 0.36, 0.805, 0.43, 1.25, true},
    {"metal1", 0.04, 0.295, 0.11, 1.17, true},
    {"metal1", 0.04, 0.805, 0.43, 0.875, true},
    {"metal1", 0.85, 0.79, 1.19, 0.86, true},
    {"metal1", 1.57, 0.755, 1.785, 0.825, true},
    {"metal1", 1.715, 0.56, 1.785, 0.825, true},
    {"metal1", 1.715, 0.56, 2.095, 0.63, true},
};

inline constexpr RectSpec kNangateCLKGATEX2ObsGroup2[] = {
    {"metal1", 1.42, 0.49, 1.49, 0.975, true},
    {"metal1", 1.065, 0.49, 1.49, 0.56, true},
    {"metal1", 1.385, 0.185, 1.455, 0.56, true},
};

inline constexpr RectSpec kNangateCLKGATEX2ObsGroup3[] = {
    {"metal1", 1.255, 0.65, 1.325, 1.115, true},
    {"metal1", 0.74, 0.65, 1.325, 0.72, true},
    {"metal1", 0.74, 0.585, 0.99, 0.72, true},
    {"metal1", 0.92, 0.35, 0.99, 0.72, true},
    {"metal1", 0.92, 0.35, 1.28, 0.42, true},
};

inline constexpr RectSpec kNangateCLKGATEX2ObsGroup4[] = {
    {"metal1", 0.605, 0.2, 0.675, 1.115, true},
    {"metal1", 0.175, 0.655, 0.675, 0.725, true},
    {"metal1", 0.175, 0.525, 0.245, 0.725, true},
};

inline constexpr GroupSpec kNangateCLKGATEX2Groups[] = {
    {BindingKind::kPinNet, "CK", kNangateCLKGATEX2PinCK, std::size(kNangateCLKGATEX2PinCK)},
    {BindingKind::kPinNet, "E", kNangateCLKGATEX2PinE, std::size(kNangateCLKGATEX2PinE)},
    {BindingKind::kPinNet, "GCK", kNangateCLKGATEX2PinGCK, std::size(kNangateCLKGATEX2PinGCK)},
    {BindingKind::kSupplyNet, "POWER", kNangateCLKGATEX2Power, std::size(kNangateCLKGATEX2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateCLKGATEX2Ground, std::size(kNangateCLKGATEX2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateCLKGATEX2ObsGroup0, std::size(kNangateCLKGATEX2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateCLKGATEX2ObsGroup1, std::size(kNangateCLKGATEX2ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateCLKGATEX2ObsGroup2, std::size(kNangateCLKGATEX2ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateCLKGATEX2ObsGroup3, std::size(kNangateCLKGATEX2ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateCLKGATEX2ObsGroup4, std::size(kNangateCLKGATEX2ObsGroup4)},
};

inline constexpr RectSpec kNangateCLKGATEX4PinCK[] = {
    {"metal1", 1.895, 0.39, 1.965, 0.66},
    {"metal1", 1.535, 0.39, 1.965, 0.46},
    {"metal1", 1.535, 0.39, 1.65, 0.7},
};

inline constexpr RectSpec kNangateCLKGATEX4PinE[] = {
    {"metal1", 0.35, 0.42, 0.51, 0.63},
};

inline constexpr RectSpec kNangateCLKGATEX4PinGCK[] = {
    {"metal1", 2.925, 0.15, 2.995, 1.24},
    {"metal1", 2.555, 0.42, 2.995, 0.56},
    {"metal1", 2.555, 0.15, 2.625, 1.24},
};

inline constexpr RectSpec kNangateCLKGATEX4Power[] = {
    {"metal1", 0.0, 1.315, 3.23, 1.485},
    {"metal1", 3.115, 0.965, 3.185, 1.485},
    {"metal1", 2.735, 0.965, 2.805, 1.485},
    {"metal1", 2.355, 1.065, 2.425, 1.485},
    {"metal1", 1.975, 1.065, 2.045, 1.485},
    {"metal1", 1.57, 1.24, 1.705, 1.485},
    {"metal1", 0.995, 0.965, 1.065, 1.485},
    {"metal1", 0.235, 0.965, 0.305, 1.485},
};

inline constexpr RectSpec kNangateCLKGATEX4Ground[] = {
    {"metal1", 0.0, -0.085, 3.23, 0.085},
    {"metal1", 3.115, -0.085, 3.185, 0.215},
    {"metal1", 2.735, -0.085, 2.805, 0.215},
    {"metal1", 2.325, -0.085, 2.46, 0.185},
    {"metal1", 1.58, -0.085, 1.65, 0.285},
    {"metal1", 0.995, -0.085, 1.065, 0.32},
    {"metal1", 0.235, -0.085, 0.305, 0.32},
};

inline constexpr RectSpec kNangateCLKGATEX4ObsGroup0[] = {
    {"metal1", 2.165, 0.905, 2.235, 1.24, true},
    {"metal1", 1.79, 0.905, 1.86, 1.24, true},
    {"metal1", 1.79, 0.905, 2.49, 0.975, true},
    {"metal1", 2.42, 0.255, 2.49, 0.975, true},
    {"metal1", 1.95, 0.255, 2.49, 0.325, true},
};

inline constexpr RectSpec kNangateCLKGATEX4ObsGroup1[] = {
    {"metal1", 0.05, 0.15, 0.12, 1.24, true},
    {"metal1", 0.37, 1.165, 0.885, 1.235, true},
    {"metal1", 0.815, 0.83, 0.885, 1.235, true},
    {"metal1", 1.13, 1.105, 1.64, 1.175, true},
    {"metal1", 1.57, 0.765, 1.64, 1.175, true},
    {"metal1", 0.37, 0.83, 0.44, 1.235, true},
    {"metal1", 1.13, 0.83, 1.2, 1.175, true},
    {"metal1", 0.815, 0.83, 1.2, 0.9, true},
    {"metal1", 0.05, 0.83, 0.44, 0.9, true},
    {"metal1", 1.57, 0.765, 2.32, 0.835, true},
    {"metal1", 2.25, 0.525, 2.32, 0.835, true},
    {"metal1", 0.92, 0.56, 0.99, 0.9, true},
    {"metal1", 1.715, 0.525, 1.785, 0.835, true},
};

inline constexpr RectSpec kNangateCLKGATEX4ObsGroup2[] = {
    {"metal1", 1.4, 0.15, 1.47, 1.04, true},
    {"metal1", 1.19, 0.56, 1.47, 0.63, true},
};

inline constexpr RectSpec kNangateCLKGATEX4ObsGroup3[] = {
    {"metal1", 1.265, 0.695, 1.335, 0.87, true},
    {"metal1", 1.055, 0.695, 1.335, 0.765, true},
    {"metal1", 1.055, 0.39, 1.125, 0.765, true},
    {"metal1", 0.75, 0.39, 0.82, 0.66, true},
    {"metal1", 0.75, 0.39, 1.255, 0.46, true},
    {"metal1", 1.185, 0.3, 1.255, 0.46, true},
};

inline constexpr RectSpec kNangateCLKGATEX4ObsGroup4[] = {
    {"metal1", 0.615, 0.2, 0.685, 1.095, true},
    {"metal1", 0.185, 0.695, 0.685, 0.765, true},
    {"metal1", 0.185, 0.525, 0.255, 0.765, true},
};

inline constexpr GroupSpec kNangateCLKGATEX4Groups[] = {
    {BindingKind::kPinNet, "CK", kNangateCLKGATEX4PinCK, std::size(kNangateCLKGATEX4PinCK)},
    {BindingKind::kPinNet, "E", kNangateCLKGATEX4PinE, std::size(kNangateCLKGATEX4PinE)},
    {BindingKind::kPinNet, "GCK", kNangateCLKGATEX4PinGCK, std::size(kNangateCLKGATEX4PinGCK)},
    {BindingKind::kSupplyNet, "POWER", kNangateCLKGATEX4Power, std::size(kNangateCLKGATEX4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateCLKGATEX4Ground, std::size(kNangateCLKGATEX4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateCLKGATEX4ObsGroup0, std::size(kNangateCLKGATEX4ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateCLKGATEX4ObsGroup1, std::size(kNangateCLKGATEX4ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateCLKGATEX4ObsGroup2, std::size(kNangateCLKGATEX4ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateCLKGATEX4ObsGroup3, std::size(kNangateCLKGATEX4ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateCLKGATEX4ObsGroup4, std::size(kNangateCLKGATEX4ObsGroup4)},
};

inline constexpr RectSpec kNangateCLKGATEX8PinCK[] = {
    {"metal1", 1.625, 0.86, 2.935, 0.93},
    {"metal1", 2.865, 0.525, 2.935, 0.93},
    {"metal1", 2.13, 0.525, 2.22, 0.93},
};

inline constexpr RectSpec kNangateCLKGATEX8PinE[] = {
    {"metal1", 0.345, 0.56, 0.51, 0.7},
};

inline constexpr RectSpec kNangateCLKGATEX8PinGCK[] = {
    {"metal1", 4.615, 0.15, 4.685, 1.235},
    {"metal1", 3.485, 0.42, 4.685, 0.56},
    {"metal1", 4.235, 0.15, 4.305, 1.235},
    {"metal1", 3.855, 0.15, 3.925, 1.235},
    {"metal1", 3.485, 0.15, 3.555, 1.235},
};

inline constexpr RectSpec kNangateCLKGATEX8Power[] = {
    {"metal1", 0.0, 1.315, 4.94, 1.485},
    {"metal1", 4.805, 0.96, 4.875, 1.485},
    {"metal1", 4.425, 0.96, 4.495, 1.485},
    {"metal1", 4.045, 0.96, 4.115, 1.485},
    {"metal1", 3.665, 0.96, 3.735, 1.485},
    {"metal1", 3.275, 0.96, 3.345, 1.485},
    {"metal1", 2.88, 1.205, 2.95, 1.485},
    {"metal1", 2.5, 1.205, 2.57, 1.485},
    {"metal1", 2.12, 1.205, 2.19, 1.485},
    {"metal1", 1.725, 1.065, 1.795, 1.485},
    {"metal1", 1.355, 1.175, 1.49, 1.485},
    {"metal1", 1.005, 0.995, 1.075, 1.485},
    {"metal1", 0.23, 0.96, 0.3, 1.485},
};

inline constexpr RectSpec kNangateCLKGATEX8Ground[] = {
    {"metal1", 0.0, -0.085, 4.94, 0.085},
    {"metal1", 4.805, -0.085, 4.875, 0.285},
    {"metal1", 4.425, -0.085, 4.495, 0.285},
    {"metal1", 4.045, -0.085, 4.115, 0.285},
    {"metal1", 3.67, -0.085, 3.74, 0.285},
    {"metal1", 3.245, -0.085, 3.38, 0.16},
    {"metal1", 2.47, -0.085, 2.605, 0.16},
    {"metal1", 1.715, -0.085, 1.85, 0.16},
    {"metal1", 1.355, -0.085, 1.49, 0.16},
    {"metal1", 1.005, -0.085, 1.075, 0.285},
    {"metal1", 0.2, -0.085, 0.335, 0.25},
};

inline constexpr RectSpec kNangateCLKGATEX8ObsGroup0[] = {
    {"metal1", 3.07, 0.725, 3.14, 1.235, true},
    {"metal1", 2.66, 0.995, 2.795, 1.2, true},
    {"metal1", 2.28, 0.995, 2.415, 1.2, true},
    {"metal1", 1.905, 0.995, 2.04, 1.2, true},
    {"metal1", 1.905, 0.995, 3.14, 1.065, true},
    {"metal1", 3.005, 0.725, 3.42, 0.795, true},
    {"metal1", 3.35, 0.525, 3.42, 0.795, true},
    {"metal1", 2.31, 0.725, 2.74, 0.795, true},
    {"metal1", 2.67, 0.39, 2.74, 0.795, true},
    {"metal1", 3.005, 0.39, 3.075, 0.795, true},
    {"metal1", 2.31, 0.39, 2.38, 0.795, true},
    {"metal1", 2.67, 0.39, 3.075, 0.46, true},
    {"metal1", 2.095, 0.39, 2.38, 0.46, true},
};

inline constexpr RectSpec kNangateCLKGATEX8ObsGroup1[] = {
    {"metal1", 0.87, 0.725, 1.275, 0.795, true},
    {"metal1", 1.205, 0.15, 1.275, 0.795, true},
    {"metal1", 3.155, 0.255, 3.225, 0.66, true},
    {"metal1", 2.5, 0.255, 2.57, 0.66, true},
    {"metal1", 1.825, 0.255, 1.895, 0.66, true},
    {"metal1", 1.205, 0.255, 3.225, 0.325, true},
};

inline constexpr RectSpec kNangateCLKGATEX8ObsGroup2[] = {
    {"metal1", 0.44, 1.15, 0.94, 1.22, true},
    {"metal1", 0.87, 0.86, 0.94, 1.22, true},
    {"metal1", 0.44, 0.765, 0.51, 1.22, true},
    {"metal1", 1.49, 1.005, 1.645, 1.075, true},
    {"metal1", 1.49, 0.43, 1.56, 1.075, true},
    {"metal1", 0.87, 0.86, 1.56, 0.93, true},
    {"metal1", 0.18, 0.765, 0.51, 0.835, true},
    {"metal1", 0.18, 0.605, 0.25, 0.835, true},
    {"metal1", 1.49, 0.43, 1.645, 0.5, true},
};

inline constexpr RectSpec kNangateCLKGATEX8ObsGroup3[] = {
    {"metal1", 0.585, 1.01, 0.805, 1.08, true},
    {"metal1", 0.735, 0.525, 0.805, 1.08, true},
    {"metal1", 0.735, 0.525, 1.14, 0.66, true},
    {"metal1", 0.865, 0.18, 0.935, 0.66, true},
    {"metal1", 0.585, 0.18, 0.935, 0.25, true},
};

inline constexpr RectSpec kNangateCLKGATEX8ObsGroup4[] = {
    {"metal1", 0.045, 0.15, 0.115, 1.235, true},
    {"metal1", 0.575, 0.39, 0.645, 0.87, true},
    {"metal1", 0.045, 0.39, 0.8, 0.46, true},
};

inline constexpr GroupSpec kNangateCLKGATEX8Groups[] = {
    {BindingKind::kPinNet, "CK", kNangateCLKGATEX8PinCK, std::size(kNangateCLKGATEX8PinCK)},
    {BindingKind::kPinNet, "E", kNangateCLKGATEX8PinE, std::size(kNangateCLKGATEX8PinE)},
    {BindingKind::kPinNet, "GCK", kNangateCLKGATEX8PinGCK, std::size(kNangateCLKGATEX8PinGCK)},
    {BindingKind::kSupplyNet, "POWER", kNangateCLKGATEX8Power, std::size(kNangateCLKGATEX8Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateCLKGATEX8Ground, std::size(kNangateCLKGATEX8Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateCLKGATEX8ObsGroup0, std::size(kNangateCLKGATEX8ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateCLKGATEX8ObsGroup1, std::size(kNangateCLKGATEX8ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateCLKGATEX8ObsGroup2, std::size(kNangateCLKGATEX8ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateCLKGATEX8ObsGroup3, std::size(kNangateCLKGATEX8ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateCLKGATEX8ObsGroup4, std::size(kNangateCLKGATEX8ObsGroup4)},
};

inline constexpr RectSpec kNangateDFFRSX1PinD[] = {
    {"metal1", 4.12, 0.585, 4.31, 0.84},
};

inline constexpr RectSpec kNangateDFFRSX1PinRN[] = {
    {"metal1", 1.2, 0.7, 1.345, 0.84},
};

inline constexpr RectSpec kNangateDFFRSX1PinSN[] = {
    {"metal1", 0.8, 0.7, 0.89, 0.84},
};

inline constexpr RectSpec kNangateDFFRSX1PinCK[] = {
    {"metal1", 4.24, 0.28, 4.385, 0.495},
};

inline constexpr RectSpec kNangateDFFRSX1PinQ[] = {
    {"metal1", 0.44, 0.4, 0.51, 0.875},
};

inline constexpr RectSpec kNangateDFFRSX1PinQN[] = {
    {"metal1", 0.06, 0.185, 0.13, 1.075},
};

inline constexpr RectSpec kNangateDFFRSX1Power[] = {
    {"metal1", 0.0, 1.315, 4.56, 1.485},
    {"metal1", 4.255, 0.915, 4.325, 1.485},
    {"metal1", 3.325, 1.03, 3.46, 1.485},
    {"metal1", 2.795, 0.835, 2.93, 1.485},
    {"metal1", 2.415, 0.89, 2.55, 1.485},
    {"metal1", 1.655, 0.99, 1.79, 1.485},
    {"metal1", 1.345, 0.925, 1.415, 1.485},
    {"metal1", 0.965, 1.065, 1.035, 1.485},
    {"metal1", 0.56, 1.095, 0.695, 1.485},
    {"metal1", 0.215, 1.1, 0.35, 1.485},
};

inline constexpr RectSpec kNangateDFFRSX1Ground[] = {
    {"metal1", 0.0, -0.085, 4.56, 0.085},
    {"metal1", 4.225, -0.085, 4.36, 0.16},
    {"metal1", 3.135, -0.085, 3.27, 0.285},
    {"metal1", 2.415, -0.085, 2.55, 0.285},
    {"metal1", 1.47, -0.085, 1.605, 0.285},
    {"metal1", 0.935, -0.085, 1.07, 0.285},
    {"metal1", 0.215, -0.085, 0.35, 0.2},
};

inline constexpr RectSpec kNangateDFFRSX1ObsGroup0[] = {
    {"metal1", 3.68, 1.18, 4.055, 1.25, true},
    {"metal1", 3.985, 0.15, 4.055, 1.25, true},
    {"metal1", 1.955, 1.165, 2.275, 1.235, true},
    {"metal1", 2.205, 0.35, 2.275, 1.235, true},
    {"metal1", 3.68, 0.76, 3.75, 1.25, true},
    {"metal1", 3.02, 0.76, 3.09, 1.07, true},
    {"metal1", 3.02, 0.76, 3.75, 0.83, true},
    {"metal1", 3.62, 0.15, 3.69, 0.46, true},
    {"metal1", 2.98, 0.35, 3.69, 0.42, true},
    {"metal1", 2.205, 0.35, 2.76, 0.42, true},
    {"metal1", 2.69, 0.165, 2.76, 0.42, true},
    {"metal1", 2.98, 0.165, 3.05, 0.42, true},
    {"metal1", 2.69, 0.165, 3.05, 0.235, true},
    {"metal1", 3.62, 0.15, 4.055, 0.22, true},
};

inline constexpr RectSpec kNangateDFFRSX1ObsGroup1[] = {
    {"metal1", 3.85, 0.62, 3.92, 1.115, true},
    {"metal1", 2.5, 0.62, 3.92, 0.69, true},
    {"metal1", 3.76, 0.285, 3.83, 0.69, true},
};

inline constexpr RectSpec kNangateDFFRSX1ObsGroup2[] = {
    {"metal1", 3.545, 0.895, 3.615, 1.115, true},
    {"metal1", 3.175, 0.895, 3.245, 1.115, true},
    {"metal1", 3.175, 0.895, 3.615, 0.965, true},
};

inline constexpr RectSpec kNangateDFFRSX1ObsGroup3[] = {
    {"metal1", 2.635, 0.755, 2.705, 1.07, true},
    {"metal1", 2.345, 0.755, 2.705, 0.825, true},
    {"metal1", 2.345, 0.485, 2.415, 0.825, true},
    {"metal1", 2.345, 0.485, 3.545, 0.555, true},
    {"metal1", 2.825, 0.3, 2.895, 0.555, true},
};

inline constexpr RectSpec kNangateDFFRSX1ObsGroup4[] = {
    {"metal1", 2.065, 0.185, 2.135, 1.085, true},
    {"metal1", 1.09, 0.495, 2.135, 0.63, true},
};

inline constexpr RectSpec kNangateDFFRSX1ObsGroup5[] = {
    {"metal1", 1.875, 0.855, 1.945, 1.075, true},
    {"metal1", 1.505, 0.855, 1.575, 1.075, true},
    {"metal1", 1.505, 0.855, 1.945, 0.925, true},
};

inline constexpr RectSpec kNangateDFFRSX1ObsGroup6[] = {
    {"metal1", 0.955, 0.925, 1.26, 0.995, true},
    {"metal1", 0.955, 0.35, 1.025, 0.995, true},
    {"metal1", 0.595, 0.555, 1.025, 0.625, true},
    {"metal1", 0.95, 0.35, 1.025, 0.625, true},
    {"metal1", 0.95, 0.35, 1.9, 0.425, true},
};

inline constexpr RectSpec kNangateDFFRSX1ObsGroup7[] = {
    {"metal1", 0.2, 0.96, 0.88, 1.03, true},
    {"metal1", 0.2, 0.265, 0.27, 1.03, true},
    {"metal1", 0.2, 0.265, 0.695, 0.335, true},
};

inline constexpr RectSpec kNangateDFFRSX1ObsGroup8[] = {
    {"metal1", 4.45, 0.185, 4.52, 1.25, true},
};

inline constexpr GroupSpec kNangateDFFRSX1Groups[] = {
    {BindingKind::kPinNet, "D", kNangateDFFRSX1PinD, std::size(kNangateDFFRSX1PinD)},
    {BindingKind::kPinNet, "RN", kNangateDFFRSX1PinRN, std::size(kNangateDFFRSX1PinRN)},
    {BindingKind::kPinNet, "SN", kNangateDFFRSX1PinSN, std::size(kNangateDFFRSX1PinSN)},
    {BindingKind::kPinNet, "CK", kNangateDFFRSX1PinCK, std::size(kNangateDFFRSX1PinCK)},
    {BindingKind::kPinNet, "Q", kNangateDFFRSX1PinQ, std::size(kNangateDFFRSX1PinQ)},
    {BindingKind::kPinNet, "QN", kNangateDFFRSX1PinQN, std::size(kNangateDFFRSX1PinQN)},
    {BindingKind::kSupplyNet, "POWER", kNangateDFFRSX1Power, std::size(kNangateDFFRSX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateDFFRSX1Ground, std::size(kNangateDFFRSX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateDFFRSX1ObsGroup0, std::size(kNangateDFFRSX1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateDFFRSX1ObsGroup1, std::size(kNangateDFFRSX1ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateDFFRSX1ObsGroup2, std::size(kNangateDFFRSX1ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateDFFRSX1ObsGroup3, std::size(kNangateDFFRSX1ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateDFFRSX1ObsGroup4, std::size(kNangateDFFRSX1ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateDFFRSX1ObsGroup5, std::size(kNangateDFFRSX1ObsGroup5)},
    {BindingKind::kSyntheticNet, "OBS6", kNangateDFFRSX1ObsGroup6, std::size(kNangateDFFRSX1ObsGroup6)},
    {BindingKind::kSyntheticNet, "OBS7", kNangateDFFRSX1ObsGroup7, std::size(kNangateDFFRSX1ObsGroup7)},
    {BindingKind::kSyntheticNet, "OBS8", kNangateDFFRSX1ObsGroup8, std::size(kNangateDFFRSX1ObsGroup8)},
};

inline constexpr RectSpec kNangateDFFRSX2PinD[] = {
    {"metal1", 4.485, 0.28, 4.69, 0.46},
    {"metal1", 4.485, 0.28, 4.555, 0.575},
};

inline constexpr RectSpec kNangateDFFRSX2PinRN[] = {
    {"metal1", 1.39, 0.545, 1.46, 0.7},
};

inline constexpr RectSpec kNangateDFFRSX2PinSN[] = {
    {"metal1", 1.2, 0.545, 1.27, 0.7},
};

inline constexpr RectSpec kNangateDFFRSX2PinCK[] = {
    {"metal1", 4.62, 0.54, 4.72, 0.7},
};

inline constexpr RectSpec kNangateDFFRSX2PinQ[] = {
    {"metal1", 0.625, 0.4, 0.7, 0.965},
};

inline constexpr RectSpec kNangateDFFRSX2PinQN[] = {
    {"metal1", 0.24, 0.2, 0.32, 0.965},
};

inline constexpr RectSpec kNangateDFFRSX2Power[] = {
    {"metal1", 0.0, 1.315, 4.94, 1.485},
    {"metal1", 4.59, 0.765, 4.66, 1.485},
    {"metal1", 3.695, 1.03, 3.83, 1.485},
    {"metal1", 3.195, 0.765, 3.265, 1.485},
    {"metal1", 2.815, 0.955, 2.885, 1.485},
    {"metal1", 2.055, 0.955, 2.125, 1.485},
    {"metal1", 1.715, 0.895, 1.785, 1.485},
    {"metal1", 1.335, 1.08, 1.405, 1.485},
    {"metal1", 0.875, 1.205, 0.945, 1.485},
    {"metal1", 0.425, 1.205, 0.495, 1.485},
    {"metal1", 0.05, 0.925, 0.12, 1.485},
};

inline constexpr RectSpec kNangateDFFRSX2Ground[] = {
    {"metal1", 0.0, -0.085, 4.94, 0.085},
    {"metal1", 4.56, -0.085, 4.695, 0.215},
    {"metal1", 3.505, -0.085, 3.64, 0.285},
    {"metal1", 2.785, -0.085, 2.92, 0.285},
    {"metal1", 1.87, -0.085, 1.94, 0.32},
    {"metal1", 1.335, -0.085, 1.405, 0.32},
    {"metal1", 0.805, -0.085, 0.875, 0.2},
    {"metal1", 0.425, -0.085, 0.495, 0.2},
    {"metal1", 0.05, -0.085, 0.12, 0.415},
};

inline constexpr RectSpec kNangateDFFRSX2ObsGroup0[] = {
    {"metal1", 4.05, 1.18, 4.39, 1.25, true},
    {"metal1", 4.32, 0.15, 4.39, 1.25, true},
    {"metal1", 2.325, 1.14, 2.64, 1.21, true},
    {"metal1", 2.57, 0.35, 2.64, 1.21, true},
    {"metal1", 4.05, 0.76, 4.12, 1.25, true},
    {"metal1", 3.39, 0.76, 3.46, 1.04, true},
    {"metal1", 3.39, 0.76, 4.12, 0.83, true},
    {"metal1", 3.985, 0.15, 4.055, 0.46, true},
    {"metal1", 3.35, 0.35, 4.055, 0.42, true},
    {"metal1", 2.57, 0.35, 3.13, 0.42, true},
    {"metal1", 3.06, 0.185, 3.13, 0.42, true},
    {"metal1", 3.35, 0.185, 3.42, 0.42, true},
    {"metal1", 3.06, 0.185, 3.42, 0.255, true},
    {"metal1", 3.985, 0.15, 4.39, 0.22, true},
};

inline constexpr RectSpec kNangateDFFRSX2ObsGroup1[] = {
    {"metal1", 4.185, 0.62, 4.255, 1.115, true},
    {"metal1", 2.895, 0.62, 4.255, 0.69, true},
    {"metal1", 4.13, 0.285, 4.2, 0.69, true},
};

inline constexpr RectSpec kNangateDFFRSX2ObsGroup2[] = {
    {"metal1", 3.915, 0.895, 3.985, 1.115, true},
    {"metal1", 3.545, 0.895, 3.615, 1.115, true},
    {"metal1", 3.545, 0.895, 3.985, 0.965, true},
};

inline constexpr RectSpec kNangateDFFRSX2ObsGroup3[] = {
    {"metal1", 3.005, 0.755, 3.075, 1.04, true},
    {"metal1", 2.76, 0.755, 3.075, 0.825, true},
    {"metal1", 2.76, 0.485, 2.83, 0.825, true},
    {"metal1", 2.76, 0.485, 3.915, 0.555, true},
    {"metal1", 3.195, 0.32, 3.265, 0.555, true},
};

inline constexpr RectSpec kNangateDFFRSX2ObsGroup4[] = {
    {"metal1", 2.425, 0.2, 2.505, 1.075, true},
    {"metal1", 1.58, 0.58, 2.505, 0.65, true},
};

inline constexpr RectSpec kNangateDFFRSX2ObsGroup5[] = {
    {"metal1", 2.245, 0.82, 2.315, 1.075, true},
    {"metal1", 1.875, 0.82, 1.945, 1.075, true},
    {"metal1", 1.875, 0.82, 2.315, 0.89, true},
};

inline constexpr RectSpec kNangateDFFRSX2ObsGroup6[] = {
    {"metal1", 1.065, 0.845, 1.63, 0.915, true},
    {"metal1", 1.065, 0.41, 1.135, 0.915, true},
    {"metal1", 0.84, 0.525, 1.135, 0.66, true},
    {"metal1", 1.065, 0.41, 2.27, 0.48, true},
    {"metal1", 1.715, 0.205, 1.785, 0.48, true},
};

inline constexpr RectSpec kNangateDFFRSX2ObsGroup7[] = {
    {"metal1", 0.49, 1.035, 1.225, 1.105, true},
    {"metal1", 0.49, 0.265, 0.56, 1.105, true},
    {"metal1", 0.385, 0.525, 0.56, 0.66, true},
    {"metal1", 0.49, 0.265, 1.065, 0.335, true},
};

inline constexpr RectSpec kNangateDFFRSX2ObsGroup8[] = {
    {"metal1", 4.785, 0.25, 4.855, 1.24, true},
};

inline constexpr GroupSpec kNangateDFFRSX2Groups[] = {
    {BindingKind::kPinNet, "D", kNangateDFFRSX2PinD, std::size(kNangateDFFRSX2PinD)},
    {BindingKind::kPinNet, "RN", kNangateDFFRSX2PinRN, std::size(kNangateDFFRSX2PinRN)},
    {BindingKind::kPinNet, "SN", kNangateDFFRSX2PinSN, std::size(kNangateDFFRSX2PinSN)},
    {BindingKind::kPinNet, "CK", kNangateDFFRSX2PinCK, std::size(kNangateDFFRSX2PinCK)},
    {BindingKind::kPinNet, "Q", kNangateDFFRSX2PinQ, std::size(kNangateDFFRSX2PinQ)},
    {BindingKind::kPinNet, "QN", kNangateDFFRSX2PinQN, std::size(kNangateDFFRSX2PinQN)},
    {BindingKind::kSupplyNet, "POWER", kNangateDFFRSX2Power, std::size(kNangateDFFRSX2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateDFFRSX2Ground, std::size(kNangateDFFRSX2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateDFFRSX2ObsGroup0, std::size(kNangateDFFRSX2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateDFFRSX2ObsGroup1, std::size(kNangateDFFRSX2ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateDFFRSX2ObsGroup2, std::size(kNangateDFFRSX2ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateDFFRSX2ObsGroup3, std::size(kNangateDFFRSX2ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateDFFRSX2ObsGroup4, std::size(kNangateDFFRSX2ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateDFFRSX2ObsGroup5, std::size(kNangateDFFRSX2ObsGroup5)},
    {BindingKind::kSyntheticNet, "OBS6", kNangateDFFRSX2ObsGroup6, std::size(kNangateDFFRSX2ObsGroup6)},
    {BindingKind::kSyntheticNet, "OBS7", kNangateDFFRSX2ObsGroup7, std::size(kNangateDFFRSX2ObsGroup7)},
    {BindingKind::kSyntheticNet, "OBS8", kNangateDFFRSX2ObsGroup8, std::size(kNangateDFFRSX2ObsGroup8)},
};

inline constexpr RectSpec kNangateDFFRX1PinD[] = {
    {"metal1", 0.6, 0.56, 0.72, 0.745},
};

inline constexpr RectSpec kNangateDFFRX1PinRN[] = {
    {"metal1", 2.455, 0.64, 2.89, 0.71},
    {"metal1", 2.455, 0.56, 2.6, 0.71},
    {"metal1", 2.105, 1.18, 2.525, 1.25},
    {"metal1", 2.455, 0.56, 2.525, 1.25},
    {"metal1", 2.105, 0.93, 2.175, 1.25},
    {"metal1", 1.815, 0.93, 2.175, 1.0},
    {"metal1", 1.495, 1.165, 1.885, 1.235},
    {"metal1", 1.815, 0.93, 1.885, 1.235},
};

inline constexpr RectSpec kNangateDFFRX1PinCK[] = {
    {"metal1", 0.175, 0.42, 0.32, 0.56},
};

inline constexpr RectSpec kNangateDFFRX1PinQ[] = {
    {"metal1", 3.66, 0.185, 3.74, 1.25},
};

inline constexpr RectSpec kNangateDFFRX1PinQN[] = {
    {"metal1", 3.285, 0.4, 3.36, 1.25},
};

inline constexpr RectSpec kNangateDFFRX1Power[] = {
    {"metal1", 0.0, 1.315, 3.8, 1.485},
    {"metal1", 3.465, 0.975, 3.535, 1.485},
    {"metal1", 3.08, 1.065, 3.15, 1.485},
    {"metal1", 2.7, 0.98, 2.77, 1.485},
    {"metal1", 1.95, 1.065, 2.02, 1.485},
    {"metal1", 1.295, 1.03, 1.43, 1.485},
    {"metal1", 0.575, 1.015, 0.645, 1.485},
    {"metal1", 0.23, 1.065, 0.3, 1.485},
};

inline constexpr RectSpec kNangateDFFRX1Ground[] = {
    {"metal1", 0.0, -0.085, 3.8, 0.085},
    {"metal1", 3.465, -0.085, 3.535, 0.195},
    {"metal1", 2.7, -0.085, 2.77, 0.32},
    {"metal1", 1.895, -0.085, 2.03, 0.285},
    {"metal1", 1.515, -0.085, 1.585, 0.41},
    {"metal1", 0.575, -0.085, 0.645, 0.32},
    {"metal1", 0.23, -0.085, 0.3, 0.32},
};

inline constexpr RectSpec kNangateDFFRX1ObsGroup0[] = {
    {"metal1", 2.89, 0.81, 2.96, 1.25, true},
    {"metal1", 2.59, 0.81, 3.185, 0.88, true},
    {"metal1", 3.115, 0.265, 3.185, 0.88, true},
    {"metal1", 3.525, 0.265, 3.595, 0.66, true},
    {"metal1", 3.05, 0.265, 3.595, 0.335, true},
};

inline constexpr RectSpec kNangateDFFRX1ObsGroup1[] = {
    {"metal1", 2.32, 0.185, 2.39, 1.115, true},
    {"metal1", 2.98, 0.425, 3.05, 0.66, true},
    {"metal1", 2.32, 0.425, 3.05, 0.495, true},
};

inline constexpr RectSpec kNangateDFFRX1ObsGroup2[] = {
    {"metal1", 1.68, 0.76, 1.75, 0.96, true},
    {"metal1", 1.19, 0.76, 2.255, 0.83, true},
    {"metal1", 2.185, 0.35, 2.255, 0.83, true},
    {"metal1", 1.69, 0.35, 2.255, 0.42, true},
    {"metal1", 1.69, 0.185, 1.76, 0.42, true},
};

inline constexpr RectSpec kNangateDFFRX1ObsGroup3[] = {
    {"metal1", 0.42, 0.185, 0.49, 1.25, true},
    {"metal1", 0.82, 0.15, 0.89, 0.785, true},
    {"metal1", 1.985, 0.485, 2.12, 0.67, true},
    {"metal1", 1.09, 0.485, 2.12, 0.555, true},
    {"metal1", 0.42, 0.425, 0.89, 0.495, true},
    {"metal1", 1.09, 0.15, 1.16, 0.555, true},
    {"metal1", 0.82, 0.15, 1.16, 0.22, true},
};

inline constexpr RectSpec kNangateDFFRX1ObsGroup4[] = {
    {"metal1", 0.955, 0.29, 1.025, 1.125, true},
    {"metal1", 0.955, 0.625, 1.895, 0.695, true},
};

inline constexpr RectSpec kNangateDFFRX1ObsGroup5[] = {
    {"metal1", 1.135, 0.895, 1.205, 1.125, true},
    {"metal1", 1.495, 1.025, 1.63, 1.095, true},
    {"metal1", 1.495, 0.895, 1.565, 1.095, true},
    {"metal1", 1.135, 0.895, 1.565, 0.965, true},
};

inline constexpr RectSpec kNangateDFFRX1ObsGroup6[] = {
    {"metal1", 0.04, 0.185, 0.11, 1.25, true},
    {"metal1", 0.04, 0.7, 0.355, 0.835, true},
};

inline constexpr GroupSpec kNangateDFFRX1Groups[] = {
    {BindingKind::kPinNet, "D", kNangateDFFRX1PinD, std::size(kNangateDFFRX1PinD)},
    {BindingKind::kPinNet, "RN", kNangateDFFRX1PinRN, std::size(kNangateDFFRX1PinRN)},
    {BindingKind::kPinNet, "CK", kNangateDFFRX1PinCK, std::size(kNangateDFFRX1PinCK)},
    {BindingKind::kPinNet, "Q", kNangateDFFRX1PinQ, std::size(kNangateDFFRX1PinQ)},
    {BindingKind::kPinNet, "QN", kNangateDFFRX1PinQN, std::size(kNangateDFFRX1PinQN)},
    {BindingKind::kSupplyNet, "POWER", kNangateDFFRX1Power, std::size(kNangateDFFRX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateDFFRX1Ground, std::size(kNangateDFFRX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateDFFRX1ObsGroup0, std::size(kNangateDFFRX1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateDFFRX1ObsGroup1, std::size(kNangateDFFRX1ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateDFFRX1ObsGroup2, std::size(kNangateDFFRX1ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateDFFRX1ObsGroup3, std::size(kNangateDFFRX1ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateDFFRX1ObsGroup4, std::size(kNangateDFFRX1ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateDFFRX1ObsGroup5, std::size(kNangateDFFRX1ObsGroup5)},
    {BindingKind::kSyntheticNet, "OBS6", kNangateDFFRX1ObsGroup6, std::size(kNangateDFFRX1ObsGroup6)},
};

inline constexpr RectSpec kNangateDFFRX2PinD[] = {
    {"metal1", 0.63, 0.52, 0.74, 0.7},
};

inline constexpr RectSpec kNangateDFFRX2PinRN[] = {
    {"metal1", 2.52, 0.56, 2.905, 0.7},
    {"metal1", 2.17, 1.15, 2.59, 1.22},
    {"metal1", 2.52, 0.56, 2.59, 1.22},
    {"metal1", 2.17, 0.965, 2.24, 1.22},
    {"metal1", 1.835, 0.965, 2.24, 1.035},
    {"metal1", 1.515, 1.165, 1.905, 1.235},
    {"metal1", 1.835, 0.965, 1.905, 1.235},
};

inline constexpr RectSpec kNangateDFFRX2PinCK[] = {
    {"metal1", 0.195, 0.42, 0.32, 0.56},
};

inline constexpr RectSpec kNangateDFFRX2PinQ[] = {
    {"metal1", 3.86, 0.185, 3.935, 1.08},
};

inline constexpr RectSpec kNangateDFFRX2PinQN[] = {
    {"metal1", 3.41, 0.645, 3.55, 0.785},
    {"metal1", 3.48, 0.185, 3.55, 0.785},
};

inline constexpr RectSpec kNangateDFFRX2Power[] = {
    {"metal1", 0.0, 1.315, 4.18, 1.485},
    {"metal1", 4.05, 1.065, 4.12, 1.485},
    {"metal1", 3.67, 1.065, 3.74, 1.485},
    {"metal1", 3.19, 1.065, 3.26, 1.485},
    {"metal1", 2.725, 1.0, 2.86, 1.485},
    {"metal1", 1.97, 1.1, 2.105, 1.485},
    {"metal1", 1.315, 1.03, 1.45, 1.485},
    {"metal1", 0.59, 1.015, 0.66, 1.485},
    {"metal1", 0.245, 0.945, 0.315, 1.485},
};

inline constexpr RectSpec kNangateDFFRX2Ground[] = {
    {"metal1", 0.0, -0.085, 4.18, 0.085},
    {"metal1", 4.05, -0.085, 4.12, 0.335},
    {"metal1", 3.67, -0.085, 3.74, 0.335},
    {"metal1", 3.295, -0.085, 3.365, 0.195},
    {"metal1", 2.69, -0.085, 2.76, 0.32},
    {"metal1", 1.9, -0.085, 2.035, 0.285},
    {"metal1", 1.535, -0.085, 1.605, 0.41},
    {"metal1", 0.59, -0.085, 0.66, 0.32},
    {"metal1", 0.245, -0.085, 0.315, 0.32},
};

inline constexpr RectSpec kNangateDFFRX2ObsGroup0[] = {
    {"metal1", 2.97, 0.85, 3.04, 1.22, true},
    {"metal1", 2.655, 0.85, 3.79, 0.92, true},
    {"metal1", 3.72, 0.525, 3.79, 0.92, true},
    {"metal1", 3.07, 0.4, 3.14, 0.92, true},
    {"metal1", 2.655, 0.765, 2.725, 0.92, true},
};

inline constexpr RectSpec kNangateDFFRX2ObsGroup1[] = {
    {"metal1", 2.375, 0.215, 2.445, 1.085, true},
    {"metal1", 3.24, 0.265, 3.31, 0.66, true},
    {"metal1", 2.375, 0.385, 2.95, 0.455, true},
    {"metal1", 2.88, 0.265, 2.95, 0.455, true},
    {"metal1", 2.88, 0.265, 3.31, 0.335, true},
    {"metal1", 2.285, 0.215, 2.445, 0.285, true},
};

inline constexpr RectSpec kNangateDFFRX2ObsGroup2[] = {
    {"metal1", 1.7, 0.76, 1.77, 0.96, true},
    {"metal1", 1.7, 0.83, 2.26, 0.9, true},
    {"metal1", 2.19, 0.35, 2.26, 0.9, true},
    {"metal1", 1.235, 0.76, 1.77, 0.83, true},
    {"metal1", 1.75, 0.35, 2.26, 0.42, true},
    {"metal1", 1.75, 0.185, 1.82, 0.42, true},
};

inline constexpr RectSpec kNangateDFFRX2ObsGroup3[] = {
    {"metal1", 0.44, 0.185, 0.51, 0.98, true},
    {"metal1", 0.83, 0.15, 0.9, 0.82, true},
    {"metal1", 2.055, 0.485, 2.125, 0.705, true},
    {"metal1", 1.105, 0.485, 2.125, 0.555, true},
    {"metal1", 1.105, 0.15, 1.175, 0.555, true},
    {"metal1", 0.44, 0.385, 0.9, 0.455, true},
    {"metal1", 0.83, 0.15, 1.175, 0.22, true},
};

inline constexpr RectSpec kNangateDFFRX2ObsGroup4[] = {
    {"metal1", 0.97, 0.29, 1.04, 1.125, true},
    {"metal1", 1.85, 0.625, 1.925, 0.765, true},
    {"metal1", 0.97, 0.625, 1.925, 0.695, true},
};

inline constexpr RectSpec kNangateDFFRX2ObsGroup5[] = {
    {"metal1", 1.155, 0.895, 1.225, 1.125, true},
    {"metal1", 1.515, 1.025, 1.65, 1.095, true},
    {"metal1", 1.515, 0.895, 1.585, 1.095, true},
    {"metal1", 1.155, 0.895, 1.585, 0.965, true},
};

inline constexpr RectSpec kNangateDFFRX2ObsGroup6[] = {
    {"metal1", 0.06, 0.185, 0.13, 1.22, true},
    {"metal1", 0.06, 0.655, 0.375, 0.79, true},
};

inline constexpr GroupSpec kNangateDFFRX2Groups[] = {
    {BindingKind::kPinNet, "D", kNangateDFFRX2PinD, std::size(kNangateDFFRX2PinD)},
    {BindingKind::kPinNet, "RN", kNangateDFFRX2PinRN, std::size(kNangateDFFRX2PinRN)},
    {BindingKind::kPinNet, "CK", kNangateDFFRX2PinCK, std::size(kNangateDFFRX2PinCK)},
    {BindingKind::kPinNet, "Q", kNangateDFFRX2PinQ, std::size(kNangateDFFRX2PinQ)},
    {BindingKind::kPinNet, "QN", kNangateDFFRX2PinQN, std::size(kNangateDFFRX2PinQN)},
    {BindingKind::kSupplyNet, "POWER", kNangateDFFRX2Power, std::size(kNangateDFFRX2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateDFFRX2Ground, std::size(kNangateDFFRX2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateDFFRX2ObsGroup0, std::size(kNangateDFFRX2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateDFFRX2ObsGroup1, std::size(kNangateDFFRX2ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateDFFRX2ObsGroup2, std::size(kNangateDFFRX2ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateDFFRX2ObsGroup3, std::size(kNangateDFFRX2ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateDFFRX2ObsGroup4, std::size(kNangateDFFRX2ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateDFFRX2ObsGroup5, std::size(kNangateDFFRX2ObsGroup5)},
    {BindingKind::kSyntheticNet, "OBS6", kNangateDFFRX2ObsGroup6, std::size(kNangateDFFRX2ObsGroup6)},
};

inline constexpr RectSpec kNangateDFFSX1PinD[] = {
    {"metal1", 0.34, 0.56, 0.51, 0.7},
};

inline constexpr RectSpec kNangateDFFSX1PinSN[] = {
    {"metal1", 2.625, 0.7, 2.79, 0.84},
};

inline constexpr RectSpec kNangateDFFSX1PinCK[] = {
    {"metal1", 1.77, 0.59, 1.84, 0.84},
    {"metal1", 1.705, 0.59, 1.84, 0.725},
};

inline constexpr RectSpec kNangateDFFSX1PinQ[] = {
    {"metal1", 3.575, 0.56, 3.74, 0.7},
    {"metal1", 3.575, 0.185, 3.645, 1.16},
};

inline constexpr RectSpec kNangateDFFSX1PinQN[] = {
    {"metal1", 3.195, 0.56, 3.36, 0.7},
    {"metal1", 3.195, 0.185, 3.265, 0.925},
};

inline constexpr RectSpec kNangateDFFSX1Power[] = {
    {"metal1", 0.0, 1.315, 3.8, 1.485},
    {"metal1", 3.38, 1.205, 3.45, 1.485},
    {"metal1", 2.855, 1.005, 2.925, 1.485},
    {"metal1", 2.48, 1.065, 2.615, 1.485},
    {"metal1", 1.755, 0.905, 1.825, 1.485},
    {"metal1", 1.41, 0.885, 1.48, 1.485},
    {"metal1", 1.015, 0.94, 1.085, 1.485},
    {"metal1", 0.225, 0.9, 0.295, 1.485},
};

inline constexpr RectSpec kNangateDFFSX1Ground[] = {
    {"metal1", 0.0, -0.085, 3.8, 0.085},
    {"metal1", 3.385, -0.085, 3.455, 0.46},
    {"metal1", 2.67, -0.085, 2.805, 0.34},
    {"metal1", 1.75, -0.085, 1.82, 0.375},
    {"metal1", 1.04, -0.085, 1.11, 0.32},
    {"metal1", 0.225, -0.085, 0.295, 0.32},
};

inline constexpr RectSpec kNangateDFFSX1ObsGroup0[] = {
    {"metal1", 3.01, 0.995, 3.505, 1.065, true},
    {"metal1", 3.435, 0.525, 3.505, 1.065, true},
    {"metal1", 3.01, 0.42, 3.08, 1.065, true},
    {"metal1", 2.375, 0.42, 3.08, 0.49, true},
    {"metal1", 2.905, 0.185, 2.975, 0.49, true},
};

inline constexpr RectSpec kNangateDFFSX1ObsGroup1[] = {
    {"metal1", 2.105, 1.045, 2.24, 1.115, true},
    {"metal1", 2.17, 0.29, 2.24, 1.115, true},
    {"metal1", 2.17, 0.56, 2.925, 0.63, true},
    {"metal1", 2.105, 0.29, 2.24, 0.36, true},
};

inline constexpr RectSpec kNangateDFFSX1ObsGroup2[] = {
    {"metal1", 2.7, 0.93, 2.77, 1.15, true},
    {"metal1", 2.33, 0.93, 2.4, 1.15, true},
    {"metal1", 2.33, 0.93, 2.77, 1.0, true},
};

inline constexpr RectSpec kNangateDFFSX1ObsGroup3[] = {
    {"metal1", 1.57, 0.815, 1.67, 1.09, true},
    {"metal1", 0.635, 0.72, 0.73, 0.855, true},
    {"metal1", 1.57, 0.15, 1.64, 1.09, true},
    {"metal1", 1.97, 0.665, 2.095, 0.8, true},
    {"metal1", 0.635, 0.42, 0.705, 0.855, true},
    {"metal1", 0.175, 0.42, 0.245, 0.685, true},
    {"metal1", 1.97, 0.15, 2.04, 0.8, true},
    {"metal1", 1.57, 0.44, 2.04, 0.51, true},
    {"metal1", 0.175, 0.42, 0.705, 0.49, true},
    {"metal1", 0.905, 0.385, 1.35, 0.455, true},
    {"metal1", 1.28, 0.15, 1.35, 0.455, true},
    {"metal1", 0.445, 0.15, 0.515, 0.49, true},
    {"metal1", 0.905, 0.15, 0.975, 0.455, true},
    {"metal1", 1.97, 0.15, 2.32, 0.22, true},
    {"metal1", 1.28, 0.15, 1.64, 0.22, true},
    {"metal1", 0.445, 0.15, 0.975, 0.22, true},
};

inline constexpr RectSpec kNangateDFFSX1ObsGroup4[] = {
    {"metal1", 1.22, 0.75, 1.29, 1.09, true},
    {"metal1", 0.94, 0.75, 1.485, 0.82, true},
    {"metal1", 1.415, 0.285, 1.485, 0.82, true},
    {"metal1", 0.94, 0.685, 1.01, 0.82, true},
};

inline constexpr RectSpec kNangateDFFSX1ObsGroup5[] = {
    {"metal1", 0.59, 0.975, 0.865, 1.045, true},
    {"metal1", 0.795, 0.545, 0.865, 1.045, true},
    {"metal1", 1.28, 0.545, 1.35, 0.685, true},
    {"metal1", 0.77, 0.545, 1.35, 0.615, true},
    {"metal1", 0.77, 0.285, 0.84, 0.615, true},
    {"metal1", 0.59, 0.285, 0.84, 0.355, true},
};

inline constexpr RectSpec kNangateDFFSX1ObsGroup6[] = {
    {"metal1", 0.04, 0.185, 0.11, 1.16, true},
    {"metal1", 0.04, 0.765, 0.57, 0.835, true},
};

inline constexpr GroupSpec kNangateDFFSX1Groups[] = {
    {BindingKind::kPinNet, "D", kNangateDFFSX1PinD, std::size(kNangateDFFSX1PinD)},
    {BindingKind::kPinNet, "SN", kNangateDFFSX1PinSN, std::size(kNangateDFFSX1PinSN)},
    {BindingKind::kPinNet, "CK", kNangateDFFSX1PinCK, std::size(kNangateDFFSX1PinCK)},
    {BindingKind::kPinNet, "Q", kNangateDFFSX1PinQ, std::size(kNangateDFFSX1PinQ)},
    {BindingKind::kPinNet, "QN", kNangateDFFSX1PinQN, std::size(kNangateDFFSX1PinQN)},
    {BindingKind::kSupplyNet, "POWER", kNangateDFFSX1Power, std::size(kNangateDFFSX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateDFFSX1Ground, std::size(kNangateDFFSX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateDFFSX1ObsGroup0, std::size(kNangateDFFSX1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateDFFSX1ObsGroup1, std::size(kNangateDFFSX1ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateDFFSX1ObsGroup2, std::size(kNangateDFFSX1ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateDFFSX1ObsGroup3, std::size(kNangateDFFSX1ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateDFFSX1ObsGroup4, std::size(kNangateDFFSX1ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateDFFSX1ObsGroup5, std::size(kNangateDFFSX1ObsGroup5)},
    {BindingKind::kSyntheticNet, "OBS6", kNangateDFFSX1ObsGroup6, std::size(kNangateDFFSX1ObsGroup6)},
};

inline constexpr RectSpec kNangateDFFSX2PinD[] = {
    {"metal1", 0.35, 0.56, 0.51, 0.7},
};

inline constexpr RectSpec kNangateDFFSX2PinSN[] = {
    {"metal1", 2.675, 0.56, 2.79, 0.7},
};

inline constexpr RectSpec kNangateDFFSX2PinCK[] = {
    {"metal1", 1.75, 0.59, 1.84, 0.84},
};

inline constexpr RectSpec kNangateDFFSX2PinQ[] = {
    {"metal1", 3.1, 0.4, 3.17, 0.925},
};

inline constexpr RectSpec kNangateDFFSX2PinQN[] = {
    {"metal1", 3.48, 0.4, 3.55, 0.925},
};

inline constexpr RectSpec kNangateDFFSX2Power[] = {
    {"metal1", 0.0, 1.315, 3.99, 1.485},
    {"metal1", 3.66, 1.205, 3.73, 1.485},
    {"metal1", 3.285, 1.205, 3.355, 1.485},
    {"metal1", 2.91, 1.205, 2.98, 1.485},
    {"metal1", 2.53, 1.065, 2.665, 1.485},
    {"metal1", 1.805, 0.94, 1.875, 1.485},
    {"metal1", 1.46, 0.94, 1.53, 1.485},
    {"metal1", 1.08, 0.94, 1.15, 1.485},
    {"metal1", 0.235, 0.94, 0.305, 1.485},
};

inline constexpr RectSpec kNangateDFFSX2Ground[] = {
    {"metal1", 0.0, -0.085, 3.99, 0.085},
    {"metal1", 3.66, -0.085, 3.73, 0.195},
    {"metal1", 3.28, -0.085, 3.35, 0.195},
    {"metal1", 2.72, -0.085, 2.855, 0.34},
    {"metal1", 1.8, -0.085, 1.87, 0.32},
    {"metal1", 1.09, -0.085, 1.16, 0.37},
    {"metal1", 0.235, -0.085, 0.305, 0.32},
};

inline constexpr RectSpec kNangateDFFSX2ObsGroup0[] = {
    {"metal1", 3.85, 0.26, 3.92, 1.215, true},
    {"metal1", 2.92, 0.99, 3.92, 1.06, true},
    {"metal1", 3.235, 0.525, 3.305, 1.06, true},
    {"metal1", 2.92, 0.795, 2.99, 1.06, true},
    {"metal1", 2.45, 0.795, 2.99, 0.865, true},
};

inline constexpr RectSpec kNangateDFFSX2ObsGroup1[] = {
    {"metal1", 2.155, 1.045, 2.29, 1.115, true},
    {"metal1", 2.22, 0.29, 2.29, 1.115, true},
    {"metal1", 3.615, 0.265, 3.685, 0.66, true},
    {"metal1", 2.22, 0.405, 3.035, 0.475, true},
    {"metal1", 2.965, 0.265, 3.035, 0.475, true},
    {"metal1", 2.155, 0.29, 2.29, 0.36, true},
    {"metal1", 2.965, 0.265, 3.685, 0.335, true},
};

inline constexpr RectSpec kNangateDFFSX2ObsGroup2[] = {
    {"metal1", 2.75, 0.93, 2.82, 1.15, true},
    {"metal1", 2.38, 0.93, 2.45, 1.15, true},
    {"metal1", 2.38, 0.93, 2.82, 1.0, true},
};

inline constexpr RectSpec kNangateDFFSX2ObsGroup3[] = {
    {"metal1", 1.615, 0.94, 1.72, 1.075, true},
    {"metal1", 1.615, 0.15, 1.685, 1.075, true},
    {"metal1", 0.65, 0.735, 0.755, 0.87, true},
    {"metal1", 2.02, 0.665, 2.145, 0.8, true},
    {"metal1", 0.65, 0.425, 0.72, 0.87, true},
    {"metal1", 0.19, 0.425, 0.26, 0.695, true},
    {"metal1", 2.02, 0.15, 2.09, 0.8, true},
    {"metal1", 1.615, 0.455, 2.09, 0.525, true},
    {"metal1", 0.955, 0.435, 1.295, 0.505, true},
    {"metal1", 1.225, 0.15, 1.295, 0.505, true},
    {"metal1", 0.19, 0.425, 0.72, 0.495, true},
    {"metal1", 0.955, 0.15, 1.025, 0.505, true},
    {"metal1", 0.455, 0.15, 0.525, 0.495, true},
    {"metal1", 2.02, 0.15, 2.395, 0.22, true},
    {"metal1", 1.225, 0.15, 1.685, 0.22, true},
    {"metal1", 0.455, 0.15, 1.025, 0.22, true},
};

inline constexpr RectSpec kNangateDFFSX2ObsGroup4[] = {
    {"metal1", 0.965, 0.77, 1.535, 0.84, true},
    {"metal1", 1.465, 0.285, 1.535, 0.84, true},
};

inline constexpr RectSpec kNangateDFFSX2ObsGroup5[] = {
    {"metal1", 0.585, 0.975, 0.89, 1.045, true},
    {"metal1", 0.82, 0.285, 0.89, 1.045, true},
    {"metal1", 0.82, 0.57, 1.4, 0.705, true},
    {"metal1", 0.59, 0.285, 0.89, 0.355, true},
};

inline constexpr RectSpec kNangateDFFSX2ObsGroup6[] = {
    {"metal1", 0.05, 0.185, 0.12, 1.215, true},
    {"metal1", 0.05, 0.765, 0.585, 0.835, true},
};

inline constexpr GroupSpec kNangateDFFSX2Groups[] = {
    {BindingKind::kPinNet, "D", kNangateDFFSX2PinD, std::size(kNangateDFFSX2PinD)},
    {BindingKind::kPinNet, "SN", kNangateDFFSX2PinSN, std::size(kNangateDFFSX2PinSN)},
    {BindingKind::kPinNet, "CK", kNangateDFFSX2PinCK, std::size(kNangateDFFSX2PinCK)},
    {BindingKind::kPinNet, "Q", kNangateDFFSX2PinQ, std::size(kNangateDFFSX2PinQ)},
    {BindingKind::kPinNet, "QN", kNangateDFFSX2PinQN, std::size(kNangateDFFSX2PinQN)},
    {BindingKind::kSupplyNet, "POWER", kNangateDFFSX2Power, std::size(kNangateDFFSX2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateDFFSX2Ground, std::size(kNangateDFFSX2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateDFFSX2ObsGroup0, std::size(kNangateDFFSX2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateDFFSX2ObsGroup1, std::size(kNangateDFFSX2ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateDFFSX2ObsGroup2, std::size(kNangateDFFSX2ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateDFFSX2ObsGroup3, std::size(kNangateDFFSX2ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateDFFSX2ObsGroup4, std::size(kNangateDFFSX2ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateDFFSX2ObsGroup5, std::size(kNangateDFFSX2ObsGroup5)},
    {BindingKind::kSyntheticNet, "OBS6", kNangateDFFSX2ObsGroup6, std::size(kNangateDFFSX2ObsGroup6)},
};

inline constexpr RectSpec kNangateDFFX1PinD[] = {
    {"metal1", 0.81, 0.53, 0.97, 0.7},
};

inline constexpr RectSpec kNangateDFFX1PinCK[] = {
    {"metal1", 1.56, 0.53, 1.67, 0.7},
};

inline constexpr RectSpec kNangateDFFX1PinQ[] = {
    {"metal1", 3.1, 0.26, 3.17, 1.13},
};

inline constexpr RectSpec kNangateDFFX1PinQN[] = {
    {"metal1", 2.72, 0.26, 2.79, 0.785},
};

inline constexpr RectSpec kNangateDFFX1Power[] = {
    {"metal1", 0.0, 1.315, 3.23, 1.485},
    {"metal1", 2.905, 0.985, 2.975, 1.485},
    {"metal1", 2.345, 1.1, 2.48, 1.485},
    {"metal1", 1.61, 0.9, 1.68, 1.485},
    {"metal1", 1.005, 1.08, 1.075, 1.485},
    {"metal1", 0.24, 0.98, 0.31, 1.485},
};

inline constexpr RectSpec kNangateDFFX1Ground[] = {
    {"metal1", 0.0, -0.085, 3.23, 0.085},
    {"metal1", 2.905, -0.085, 2.975, 0.46},
    {"metal1", 2.345, -0.085, 2.48, 0.37},
    {"metal1", 1.61, -0.085, 1.68, 0.36},
    {"metal1", 0.975, -0.085, 1.11, 0.3},
    {"metal1", 0.24, -0.085, 0.31, 0.405},
};

inline constexpr RectSpec kNangateDFFX1ObsGroup0[] = {
    {"metal1", 2.57, 0.225, 2.64, 1.115, true},
    {"metal1", 2.57, 0.85, 3.035, 0.92, true},
    {"metal1", 2.965, 0.525, 3.035, 0.92, true},
    {"metal1", 2.265, 0.73, 2.64, 0.8, true},
};

inline constexpr RectSpec kNangateDFFX1ObsGroup1[] = {
    {"metal1", 2.0, 0.285, 2.07, 1.2, true},
    {"metal1", 2.0, 0.525, 2.505, 0.66, true},
};

inline constexpr RectSpec kNangateDFFX1ObsGroup2[] = {
    {"metal1", 1.14, 1.18, 1.495, 1.25, true},
    {"metal1", 1.425, 0.225, 1.495, 1.25, true},
    {"metal1", 0.485, 1.18, 0.94, 1.25, true},
    {"metal1", 0.87, 0.945, 0.94, 1.25, true},
    {"metal1", 1.14, 0.945, 1.21, 1.25, true},
    {"metal1", 0.87, 0.945, 1.21, 1.015, true},
    {"metal1", 1.425, 0.765, 1.925, 0.835, true},
    {"metal1", 1.855, 0.15, 1.925, 0.835, true},
    {"metal1", 1.855, 0.15, 2.205, 0.22, true},
};

inline constexpr RectSpec kNangateDFFX1ObsGroup3[] = {
    {"metal1", 1.275, 0.37, 1.345, 0.995, true},
    {"metal1", 0.38, 0.15, 0.45, 0.545, true},
    {"metal1", 0.785, 0.37, 1.345, 0.44, true},
    {"metal1", 1.2, 0.27, 1.27, 0.44, true},
    {"metal1", 0.785, 0.15, 0.855, 0.44, true},
    {"metal1", 0.38, 0.15, 0.855, 0.22, true},
};

inline constexpr RectSpec kNangateDFFX1ObsGroup4[] = {
    {"metal1", 0.635, 0.285, 0.705, 1.115, true},
    {"metal1", 0.635, 0.765, 1.19, 0.835, true},
    {"metal1", 1.12, 0.53, 1.19, 0.835, true},
};

inline constexpr RectSpec kNangateDFFX1ObsGroup5[] = {
    {"metal1", 0.06, 0.27, 0.13, 1.13, true},
    {"metal1", 0.06, 0.61, 0.57, 0.745, true},
};

inline constexpr GroupSpec kNangateDFFX1Groups[] = {
    {BindingKind::kPinNet, "D", kNangateDFFX1PinD, std::size(kNangateDFFX1PinD)},
    {BindingKind::kPinNet, "CK", kNangateDFFX1PinCK, std::size(kNangateDFFX1PinCK)},
    {BindingKind::kPinNet, "Q", kNangateDFFX1PinQ, std::size(kNangateDFFX1PinQ)},
    {BindingKind::kPinNet, "QN", kNangateDFFX1PinQN, std::size(kNangateDFFX1PinQN)},
    {BindingKind::kSupplyNet, "POWER", kNangateDFFX1Power, std::size(kNangateDFFX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateDFFX1Ground, std::size(kNangateDFFX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateDFFX1ObsGroup0, std::size(kNangateDFFX1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateDFFX1ObsGroup1, std::size(kNangateDFFX1ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateDFFX1ObsGroup2, std::size(kNangateDFFX1ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateDFFX1ObsGroup3, std::size(kNangateDFFX1ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateDFFX1ObsGroup4, std::size(kNangateDFFX1ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateDFFX1ObsGroup5, std::size(kNangateDFFX1ObsGroup5)},
};

inline constexpr RectSpec kNangateDFFX2PinD[] = {
    {"metal1", 0.94, 0.56, 1.08, 0.7},
};

inline constexpr RectSpec kNangateDFFX2PinCK[] = {
    {"metal1", 1.57, 0.56, 1.65, 0.7},
};

inline constexpr RectSpec kNangateDFFX2PinQ[] = {
    {"metal1", 3.29, 0.25, 3.36, 1.115},
};

inline constexpr RectSpec kNangateDFFX2PinQN[] = {
    {"metal1", 2.91, 0.25, 2.98, 0.925},
};

inline constexpr RectSpec kNangateDFFX2Power[] = {
    {"metal1", 0.0, 1.315, 3.61, 1.485},
    {"metal1", 3.485, 0.84, 3.555, 1.485},
    {"metal1", 3.105, 1.205, 3.175, 1.485},
    {"metal1", 2.73, 1.205, 2.8, 1.485},
    {"metal1", 2.35, 0.875, 2.485, 1.485},
    {"metal1", 1.62, 0.9, 1.69, 1.485},
    {"metal1", 1.015, 1.08, 1.085, 1.485},
    {"metal1", 0.255, 0.965, 0.325, 1.485},
};

inline constexpr RectSpec kNangateDFFX2Ground[] = {
    {"metal1", 0.0, -0.085, 3.61, 0.085},
    {"metal1", 3.485, -0.085, 3.555, 0.46},
    {"metal1", 3.105, -0.085, 3.175, 0.46},
    {"metal1", 2.73, -0.085, 2.8, 0.46},
    {"metal1", 2.35, -0.085, 2.485, 0.45},
    {"metal1", 1.62, -0.085, 1.69, 0.385},
    {"metal1", 0.985, -0.085, 1.12, 0.215},
    {"metal1", 0.255, -0.085, 0.325, 0.385},
};

inline constexpr RectSpec kNangateDFFX2ObsGroup0[] = {
    {"metal1", 2.575, 1.045, 3.215, 1.115, true},
    {"metal1", 3.145, 0.525, 3.215, 1.115, true},
    {"metal1", 2.575, 0.2, 2.645, 1.115, true},
    {"metal1", 2.245, 0.735, 2.645, 0.805, true},
};

inline constexpr RectSpec kNangateDFFX2ObsGroup1[] = {
    {"metal1", 2.01, 0.35, 2.08, 0.975, true},
    {"metal1", 2.01, 0.525, 2.51, 0.66, true},
};

inline constexpr RectSpec kNangateDFFX2ObsGroup2[] = {
    {"metal1", 1.15, 1.18, 1.505, 1.25, true},
    {"metal1", 1.435, 0.25, 1.505, 1.25, true},
    {"metal1", 0.5, 1.18, 0.935, 1.25, true},
    {"metal1", 0.865, 0.945, 0.935, 1.25, true},
    {"metal1", 1.15, 0.945, 1.22, 1.25, true},
    {"metal1", 0.865, 0.945, 1.22, 1.015, true},
    {"metal1", 1.435, 0.765, 1.945, 0.835, true},
    {"metal1", 1.875, 0.215, 1.945, 0.835, true},
    {"metal1", 1.875, 0.215, 2.215, 0.285, true},
};

inline constexpr RectSpec kNangateDFFX2ObsGroup3[] = {
    {"metal1", 1.285, 0.285, 1.355, 1.115, true},
    {"metal1", 0.39, 0.15, 0.46, 0.7, true},
    {"metal1", 0.825, 0.285, 1.355, 0.355, true},
    {"metal1", 0.825, 0.15, 0.895, 0.355, true},
    {"metal1", 0.39, 0.15, 0.895, 0.22, true},
};

inline constexpr RectSpec kNangateDFFX2ObsGroup4[] = {
    {"metal1", 0.61, 1.0, 0.76, 1.07, true},
    {"metal1", 0.69, 0.285, 0.76, 1.07, true},
    {"metal1", 0.69, 0.765, 1.215, 0.835, true},
    {"metal1", 1.145, 0.565, 1.215, 0.835, true},
    {"metal1", 0.61, 0.285, 0.76, 0.355, true},
};

inline constexpr RectSpec kNangateDFFX2ObsGroup5[] = {
    {"metal1", 0.075, 0.325, 0.145, 1.055, true},
    {"metal1", 0.075, 0.765, 0.625, 0.835, true},
    {"metal1", 0.555, 0.565, 0.625, 0.835, true},
};

inline constexpr GroupSpec kNangateDFFX2Groups[] = {
    {BindingKind::kPinNet, "D", kNangateDFFX2PinD, std::size(kNangateDFFX2PinD)},
    {BindingKind::kPinNet, "CK", kNangateDFFX2PinCK, std::size(kNangateDFFX2PinCK)},
    {BindingKind::kPinNet, "Q", kNangateDFFX2PinQ, std::size(kNangateDFFX2PinQ)},
    {BindingKind::kPinNet, "QN", kNangateDFFX2PinQN, std::size(kNangateDFFX2PinQN)},
    {BindingKind::kSupplyNet, "POWER", kNangateDFFX2Power, std::size(kNangateDFFX2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateDFFX2Ground, std::size(kNangateDFFX2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateDFFX2ObsGroup0, std::size(kNangateDFFX2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateDFFX2ObsGroup1, std::size(kNangateDFFX2ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateDFFX2ObsGroup2, std::size(kNangateDFFX2ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateDFFX2ObsGroup3, std::size(kNangateDFFX2ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateDFFX2ObsGroup4, std::size(kNangateDFFX2ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateDFFX2ObsGroup5, std::size(kNangateDFFX2ObsGroup5)},
};

inline constexpr RectSpec kNangateDLHX1PinD[] = {
    {"metal1", 0.95, 0.525, 1.08, 0.7},
};

inline constexpr RectSpec kNangateDLHX1PinG[] = {
    {"metal1", 0.2, 0.525, 0.32, 0.7},
};

inline constexpr RectSpec kNangateDLHX1PinQ[] = {
    {"metal1", 0.44, 0.185, 0.51, 0.785},
};

inline constexpr RectSpec kNangateDLHX1Power[] = {
    {"metal1", 0.0, 1.315, 1.9, 1.485},
    {"metal1", 1.595, 1.025, 1.665, 1.485},
    {"metal1", 0.845, 0.965, 0.915, 1.485},
    {"metal1", 0.25, 0.985, 0.32, 1.485},
};

inline constexpr RectSpec kNangateDLHX1Ground[] = {
    {"metal1", 0.0, -0.085, 1.9, 0.085},
    {"metal1", 1.595, -0.085, 1.665, 0.445},
    {"metal1", 0.805, -0.085, 0.94, 0.285},
    {"metal1", 0.25, -0.085, 0.32, 0.32},
};

inline constexpr RectSpec kNangateDLHX1ObsGroup0[] = {
    {"metal1", 1.79, 0.32, 1.86, 1.16, true},
    {"metal1", 1.485, 0.525, 1.86, 0.595, true},
};

inline constexpr RectSpec kNangateDLHX1ObsGroup1[] = {
    {"metal1", 1.19, 1.045, 1.415, 1.115, true},
    {"metal1", 1.345, 0.35, 1.415, 1.115, true},
    {"metal1", 1.345, 0.66, 1.725, 0.795, true},
    {"metal1", 0.785, 0.35, 0.855, 0.66, true},
    {"metal1", 0.785, 0.35, 1.415, 0.42, true},
};

inline constexpr RectSpec kNangateDLHX1ObsGroup2[] = {
    {"metal1", 1.025, 1.18, 1.43, 1.25, true},
    {"metal1", 1.025, 0.765, 1.095, 1.25, true},
    {"metal1", 0.65, 0.185, 0.72, 1.115, true},
    {"metal1", 0.65, 0.765, 1.215, 0.835, true},
    {"metal1", 1.145, 0.49, 1.215, 0.835, true},
    {"metal1", 1.145, 0.49, 1.28, 0.56, true},
};

inline constexpr RectSpec kNangateDLHX1ObsGroup3[] = {
    {"metal1", 0.505, 1.18, 0.78, 1.25, true},
    {"metal1", 0.065, 0.185, 0.135, 1.24, true},
    {"metal1", 0.505, 0.85, 0.575, 1.25, true},
    {"metal1", 0.065, 0.85, 0.575, 0.92, true},
};

inline constexpr GroupSpec kNangateDLHX1Groups[] = {
    {BindingKind::kPinNet, "D", kNangateDLHX1PinD, std::size(kNangateDLHX1PinD)},
    {BindingKind::kPinNet, "G", kNangateDLHX1PinG, std::size(kNangateDLHX1PinG)},
    {BindingKind::kPinNet, "Q", kNangateDLHX1PinQ, std::size(kNangateDLHX1PinQ)},
    {BindingKind::kSupplyNet, "POWER", kNangateDLHX1Power, std::size(kNangateDLHX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateDLHX1Ground, std::size(kNangateDLHX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateDLHX1ObsGroup0, std::size(kNangateDLHX1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateDLHX1ObsGroup1, std::size(kNangateDLHX1ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateDLHX1ObsGroup2, std::size(kNangateDLHX1ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateDLHX1ObsGroup3, std::size(kNangateDLHX1ObsGroup3)},
};

inline constexpr RectSpec kNangateDLHX2PinD[] = {
    {"metal1", 1.135, 0.525, 1.27, 0.7},
};

inline constexpr RectSpec kNangateDLHX2PinG[] = {
    {"metal1", 0.18, 0.525, 0.32, 0.7},
};

inline constexpr RectSpec kNangateDLHX2PinQ[] = {
    {"metal1", 0.44, 0.185, 0.51, 0.785},
};

inline constexpr RectSpec kNangateDLHX2Power[] = {
    {"metal1", 0.0, 1.315, 2.09, 1.485},
    {"metal1", 1.78, 1.08, 1.85, 1.485},
    {"metal1", 1.03, 1.04, 1.1, 1.485},
    {"metal1", 0.62, 1.0, 0.69, 1.485},
    {"metal1", 0.24, 1.055, 0.31, 1.485},
};

inline constexpr RectSpec kNangateDLHX2Ground[] = {
    {"metal1", 0.0, -0.085, 2.09, 0.085},
    {"metal1", 1.78, -0.085, 1.85, 0.32},
    {"metal1", 1.03, -0.085, 1.1, 0.32},
    {"metal1", 0.62, -0.085, 0.69, 0.255},
    {"metal1", 0.24, -0.085, 0.31, 0.255},
};

inline constexpr RectSpec kNangateDLHX2ObsGroup0[] = {
    {"metal1", 1.975, 0.185, 2.045, 1.215, true},
    {"metal1", 1.705, 0.495, 2.045, 0.63, true},
};

inline constexpr RectSpec kNangateDLHX2ObsGroup1[] = {
    {"metal1", 1.4, 0.78, 1.47, 1.2, true},
    {"metal1", 1.4, 0.78, 1.91, 0.875, true},
    {"metal1", 1.545, 0.74, 1.91, 0.875, true},
    {"metal1", 0.985, 0.78, 1.91, 0.85, true},
    {"metal1", 0.985, 0.525, 1.055, 0.85, true},
    {"metal1", 1.545, 0.185, 1.615, 0.875, true},
    {"metal1", 1.41, 0.185, 1.615, 0.32, true},
};

inline constexpr RectSpec kNangateDLHX2ObsGroup2[] = {
    {"metal1", 0.82, 0.975, 0.92, 1.25, true},
    {"metal1", 0.85, 0.175, 0.92, 1.25, true},
    {"metal1", 1.405, 0.39, 1.475, 0.67, true},
    {"metal1", 0.85, 0.39, 1.475, 0.46, true},
    {"metal1", 0.82, 0.175, 0.92, 0.31, true},
};

inline constexpr RectSpec kNangateDLHX2ObsGroup3[] = {
    {"metal1", 0.045, 0.185, 0.115, 1.24, true},
    {"metal1", 0.045, 0.85, 0.78, 0.92, true},
    {"metal1", 0.71, 0.375, 0.78, 0.92, true},
};

inline constexpr GroupSpec kNangateDLHX2Groups[] = {
    {BindingKind::kPinNet, "D", kNangateDLHX2PinD, std::size(kNangateDLHX2PinD)},
    {BindingKind::kPinNet, "G", kNangateDLHX2PinG, std::size(kNangateDLHX2PinG)},
    {BindingKind::kPinNet, "Q", kNangateDLHX2PinQ, std::size(kNangateDLHX2PinQ)},
    {BindingKind::kSupplyNet, "POWER", kNangateDLHX2Power, std::size(kNangateDLHX2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateDLHX2Ground, std::size(kNangateDLHX2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateDLHX2ObsGroup0, std::size(kNangateDLHX2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateDLHX2ObsGroup1, std::size(kNangateDLHX2ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateDLHX2ObsGroup2, std::size(kNangateDLHX2ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateDLHX2ObsGroup3, std::size(kNangateDLHX2ObsGroup3)},
};

inline constexpr RectSpec kNangateDLLX1PinD[] = {
    {"metal1", 0.25, 0.56, 0.43, 0.7},
};

inline constexpr RectSpec kNangateDLLX1PinGN[] = {
    {"metal1", 1.58, 0.525, 1.705, 0.7},
};

inline constexpr RectSpec kNangateDLLX1PinQ[] = {
    {"metal1", 1.39, 0.26, 1.46, 0.84},
};

inline constexpr RectSpec kNangateDLLX1Power[] = {
    {"metal1", 0.0, 1.315, 1.9, 1.485},
    {"metal1", 1.575, 1.04, 1.645, 1.485},
    {"metal1", 1.035, 0.95, 1.105, 1.485},
    {"metal1", 0.275, 0.915, 0.345, 1.485},
};

inline constexpr RectSpec kNangateDLLX1Ground[] = {
    {"metal1", 0.0, -0.085, 1.9, 0.085},
    {"metal1", 1.575, -0.085, 1.645, 0.235},
    {"metal1", 1.035, -0.085, 1.105, 0.42},
    {"metal1", 0.275, -0.085, 0.345, 0.415},
};

inline constexpr RectSpec kNangateDLLX1ObsGroup0[] = {
    {"metal1", 1.235, 1.18, 1.51, 1.25, true},
    {"metal1", 1.44, 0.905, 1.51, 1.25, true},
    {"metal1", 1.77, 0.195, 1.84, 1.24, true},
    {"metal1", 1.44, 0.905, 1.84, 0.975, true},
};

inline constexpr RectSpec kNangateDLLX1ObsGroup1[] = {
    {"metal1", 1.23, 0.285, 1.3, 1.085, true},
    {"metal1", 0.9, 0.775, 1.3, 0.845, true},
};

inline constexpr RectSpec kNangateDLLX1ObsGroup2[] = {
    {"metal1", 0.665, 0.285, 0.735, 1.085, true},
    {"metal1", 0.665, 0.525, 1.165, 0.66, true},
};

inline constexpr RectSpec kNangateDLLX1ObsGroup3[] = {
    {"metal1", 0.53, 0.15, 0.6, 1.25, true},
    {"metal1", 0.095, 0.28, 0.165, 1.085, true},
    {"metal1", 0.095, 0.78, 0.6, 0.85, true},
    {"metal1", 0.53, 0.15, 0.845, 0.22, true},
};

inline constexpr GroupSpec kNangateDLLX1Groups[] = {
    {BindingKind::kPinNet, "D", kNangateDLLX1PinD, std::size(kNangateDLLX1PinD)},
    {BindingKind::kPinNet, "GN", kNangateDLLX1PinGN, std::size(kNangateDLLX1PinGN)},
    {BindingKind::kPinNet, "Q", kNangateDLLX1PinQ, std::size(kNangateDLLX1PinQ)},
    {BindingKind::kSupplyNet, "POWER", kNangateDLLX1Power, std::size(kNangateDLLX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateDLLX1Ground, std::size(kNangateDLLX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateDLLX1ObsGroup0, std::size(kNangateDLLX1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateDLLX1ObsGroup1, std::size(kNangateDLLX1ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateDLLX1ObsGroup2, std::size(kNangateDLLX1ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateDLLX1ObsGroup3, std::size(kNangateDLLX1ObsGroup3)},
};

inline constexpr RectSpec kNangateDLLX2PinD[] = {
    {"metal1", 0.25, 0.51, 0.38, 0.7},
};

inline constexpr RectSpec kNangateDLLX2PinGN[] = {
    {"metal1", 1.77, 0.525, 1.89, 0.7},
};

inline constexpr RectSpec kNangateDLLX2PinQ[] = {
    {"metal1", 1.58, 0.26, 1.65, 1.005},
};

inline constexpr RectSpec kNangateDLLX2Power[] = {
    {"metal1", 0.0, 1.315, 2.09, 1.485},
    {"metal1", 1.76, 1.205, 1.83, 1.485},
    {"metal1", 1.385, 1.205, 1.455, 1.485},
    {"metal1", 0.985, 0.875, 1.055, 1.485},
    {"metal1", 0.225, 0.9, 0.295, 1.485},
};

inline constexpr RectSpec kNangateDLLX2Ground[] = {
    {"metal1", 0.0, -0.085, 2.09, 0.085},
    {"metal1", 1.76, -0.085, 1.83, 0.195},
    {"metal1", 1.385, -0.085, 1.455, 0.395},
    {"metal1", 0.985, -0.085, 1.055, 0.46},
    {"metal1", 0.225, -0.085, 0.295, 0.37},
};

inline constexpr RectSpec kNangateDLLX2ObsGroup0[] = {
    {"metal1", 1.185, 1.07, 1.32, 1.25, true},
    {"metal1", 1.955, 0.195, 2.025, 1.24, true},
    {"metal1", 1.185, 1.07, 2.025, 1.14, true},
};

inline constexpr RectSpec kNangateDLLX2ObsGroup1[] = {
    {"metal1", 1.19, 0.325, 1.26, 1.005, true},
    {"metal1", 0.85, 0.73, 1.26, 0.8, true},
};

inline constexpr RectSpec kNangateDLLX2ObsGroup2[] = {
    {"metal1", 0.615, 0.335, 0.685, 1.015, true},
    {"metal1", 0.615, 0.525, 1.125, 0.66, true},
};

inline constexpr RectSpec kNangateDLLX2ObsGroup3[] = {
    {"metal1", 0.045, 0.3, 0.115, 1.145, true},
    {"metal1", 0.045, 0.765, 0.55, 0.835, true},
    {"metal1", 0.48, 0.195, 0.55, 0.835, true},
    {"metal1", 0.48, 0.195, 0.82, 0.265, true},
};

inline constexpr GroupSpec kNangateDLLX2Groups[] = {
    {BindingKind::kPinNet, "D", kNangateDLLX2PinD, std::size(kNangateDLLX2PinD)},
    {BindingKind::kPinNet, "GN", kNangateDLLX2PinGN, std::size(kNangateDLLX2PinGN)},
    {BindingKind::kPinNet, "Q", kNangateDLLX2PinQ, std::size(kNangateDLLX2PinQ)},
    {BindingKind::kSupplyNet, "POWER", kNangateDLLX2Power, std::size(kNangateDLLX2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateDLLX2Ground, std::size(kNangateDLLX2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateDLLX2ObsGroup0, std::size(kNangateDLLX2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateDLLX2ObsGroup1, std::size(kNangateDLLX2ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateDLLX2ObsGroup2, std::size(kNangateDLLX2ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateDLLX2ObsGroup3, std::size(kNangateDLLX2ObsGroup3)},
};

inline constexpr RectSpec kNangateFAX1PinA[] = {
    {"metal1", 0.905, 0.825, 2.66, 0.895},
    {"metal1", 2.53, 0.7, 2.66, 0.895},
};

inline constexpr RectSpec kNangateFAX1PinB[] = {
    {"metal1", 2.34, 0.42, 2.47, 0.56},
    {"metal1", 1.41, 0.42, 2.47, 0.49},
};

inline constexpr RectSpec kNangateFAX1PinCI[] = {
    {"metal1", 0.63, 0.555, 2.275, 0.625},
    {"metal1", 0.63, 0.42, 0.7, 0.625},
};

inline constexpr RectSpec kNangateFAX1PinCO[] = {
    {"metal1", 0.06, 0.195, 0.135, 1.215},
};

inline constexpr RectSpec kNangateFAX1PinS[] = {
    {"metal1", 2.89, 0.195, 2.98, 1.215},
};

inline constexpr RectSpec kNangateFAX1Power[] = {
    {"metal1", 0.0, 1.315, 3.04, 1.485},
    {"metal1", 2.695, 1.205, 2.765, 1.485},
    {"metal1", 1.705, 1.095, 1.84, 1.485},
    {"metal1", 1.36, 0.965, 1.43, 1.485},
    {"metal1", 1.015, 1.095, 1.085, 1.485},
    {"metal1", 0.25, 0.94, 0.32, 1.485},
};

inline constexpr RectSpec kNangateFAX1Ground[] = {
    {"metal1", 0.0, -0.085, 3.04, 0.085},
    {"metal1", 2.665, -0.085, 2.8, 0.16},
    {"metal1", 1.705, -0.085, 1.84, 0.16},
    {"metal1", 1.36, -0.085, 1.43, 0.195},
    {"metal1", 1.025, -0.085, 1.095, 0.33},
    {"metal1", 0.25, -0.085, 0.32, 0.33},
};

inline constexpr RectSpec kNangateFAX1ObsGroup0[] = {
    {"metal1", 2.13, 0.96, 2.2, 1.24, true},
    {"metal1", 2.13, 0.96, 2.82, 1.03, true},
    {"metal1", 2.75, 0.225, 2.82, 1.03, true},
    {"metal1", 2.1, 0.225, 2.82, 0.295, true},
};

inline constexpr RectSpec kNangateFAX1ObsGroup1[] = {
    {"metal1", 0.63, 0.69, 0.7, 1.215, true},
    {"metal1", 0.495, 0.69, 2.115, 0.76, true},
    {"metal1", 0.495, 0.23, 0.565, 0.76, true},
    {"metal1", 0.205, 0.525, 0.565, 0.66, true},
    {"metal1", 0.495, 0.23, 0.735, 0.3, true},
};

inline constexpr RectSpec kNangateFAX1ObsGroup2[] = {
    {"metal1", 1.93, 0.96, 2.0, 1.24, true},
    {"metal1", 1.555, 0.96, 1.625, 1.24, true},
    {"metal1", 1.555, 0.96, 2.0, 1.03, true},
};

inline constexpr RectSpec kNangateFAX1ObsGroup3[] = {
    {"metal1", 0.835, 0.395, 1.275, 0.465, true},
    {"metal1", 1.205, 0.195, 1.275, 0.465, true},
    {"metal1", 0.835, 0.195, 0.905, 0.465, true},
};

inline constexpr RectSpec kNangateFAX1ObsGroup4[] = {
    {"metal1", 1.205, 0.96, 1.275, 1.235, true},
    {"metal1", 0.8, 0.96, 0.935, 1.215, true},
    {"metal1", 0.8, 0.96, 1.275, 1.03, true},
};

inline constexpr RectSpec kNangateFAX1ObsGroup5[] = {
    {"metal1", 1.52, 0.225, 2.03, 0.295, true},
};

inline constexpr GroupSpec kNangateFAX1Groups[] = {
    {BindingKind::kPinNet, "A", kNangateFAX1PinA, std::size(kNangateFAX1PinA)},
    {BindingKind::kPinNet, "B", kNangateFAX1PinB, std::size(kNangateFAX1PinB)},
    {BindingKind::kPinNet, "CI", kNangateFAX1PinCI, std::size(kNangateFAX1PinCI)},
    {BindingKind::kPinNet, "CO", kNangateFAX1PinCO, std::size(kNangateFAX1PinCO)},
    {BindingKind::kPinNet, "S", kNangateFAX1PinS, std::size(kNangateFAX1PinS)},
    {BindingKind::kSupplyNet, "POWER", kNangateFAX1Power, std::size(kNangateFAX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateFAX1Ground, std::size(kNangateFAX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateFAX1ObsGroup0, std::size(kNangateFAX1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateFAX1ObsGroup1, std::size(kNangateFAX1ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateFAX1ObsGroup2, std::size(kNangateFAX1ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateFAX1ObsGroup3, std::size(kNangateFAX1ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateFAX1ObsGroup4, std::size(kNangateFAX1ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateFAX1ObsGroup5, std::size(kNangateFAX1ObsGroup5)},
};

inline constexpr RectSpec kNangateTAPCELLX1Power[] = {
    {"metal1", 0.0, 1.315, 0.19, 1.485},
    {"metal1", 0.06, 0.975, 0.13, 1.315},
};

inline constexpr RectSpec kNangateTAPCELLX1Ground[] = {
    {"metal1", 0.0, -0.085, 0.19, 0.085},
    {"metal1", 0.06, 0.085, 0.13, 0.425},
};

inline constexpr GroupSpec kNangateTAPCELLX1Groups[] = {
    {BindingKind::kSupplyNet, "POWER", kNangateTAPCELLX1Power, std::size(kNangateTAPCELLX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateTAPCELLX1Ground, std::size(kNangateTAPCELLX1Ground)},
};

inline constexpr RectSpec kNangateFILLCELLX1Power[] = {
    {"metal1", 0.0, 1.315, 0.19, 1.485},
};

inline constexpr RectSpec kNangateFILLCELLX1Ground[] = {
    {"metal1", 0.0, -0.085, 0.19, 0.085},
};

inline constexpr GroupSpec kNangateFILLCELLX1Groups[] = {
    {BindingKind::kSupplyNet, "POWER", kNangateFILLCELLX1Power, std::size(kNangateFILLCELLX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateFILLCELLX1Ground, std::size(kNangateFILLCELLX1Ground)},
};

inline constexpr RectSpec kNangateFILLCELLX16Power[] = {
    {"metal1", 0.0, 1.315, 3.04, 1.485},
};

inline constexpr RectSpec kNangateFILLCELLX16Ground[] = {
    {"metal1", 0.0, -0.085, 3.04, 0.085},
};

inline constexpr GroupSpec kNangateFILLCELLX16Groups[] = {
    {BindingKind::kSupplyNet, "POWER", kNangateFILLCELLX16Power, std::size(kNangateFILLCELLX16Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateFILLCELLX16Ground, std::size(kNangateFILLCELLX16Ground)},
};

inline constexpr RectSpec kNangateFILLCELLX2Power[] = {
    {"metal1", 0.0, 1.315, 0.19, 1.485},
};

inline constexpr RectSpec kNangateFILLCELLX2Ground[] = {
    {"metal1", 0.0, -0.085, 0.19, 0.085},
};

inline constexpr GroupSpec kNangateFILLCELLX2Groups[] = {
    {BindingKind::kSupplyNet, "POWER", kNangateFILLCELLX2Power, std::size(kNangateFILLCELLX2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateFILLCELLX2Ground, std::size(kNangateFILLCELLX2Ground)},
};

inline constexpr RectSpec kNangateFILLCELLX32Power[] = {
    {"metal1", 0.0, 1.315, 6.08, 1.485},
};

inline constexpr RectSpec kNangateFILLCELLX32Ground[] = {
    {"metal1", 0.0, -0.085, 6.08, 0.085},
};

inline constexpr GroupSpec kNangateFILLCELLX32Groups[] = {
    {BindingKind::kSupplyNet, "POWER", kNangateFILLCELLX32Power, std::size(kNangateFILLCELLX32Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateFILLCELLX32Ground, std::size(kNangateFILLCELLX32Ground)},
};

inline constexpr RectSpec kNangateFILLCELLX4Power[] = {
    {"metal1", 0.0, 1.315, 0.76, 1.485},
};

inline constexpr RectSpec kNangateFILLCELLX4Ground[] = {
    {"metal1", 0.0, -0.085, 0.76, 0.085},
};

inline constexpr GroupSpec kNangateFILLCELLX4Groups[] = {
    {BindingKind::kSupplyNet, "POWER", kNangateFILLCELLX4Power, std::size(kNangateFILLCELLX4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateFILLCELLX4Ground, std::size(kNangateFILLCELLX4Ground)},
};

inline constexpr RectSpec kNangateFILLCELLX8Power[] = {
    {"metal1", 0.0, 1.315, 1.52, 1.485},
};

inline constexpr RectSpec kNangateFILLCELLX8Ground[] = {
    {"metal1", 0.0, -0.085, 1.52, 0.085},
};

inline constexpr GroupSpec kNangateFILLCELLX8Groups[] = {
    {BindingKind::kSupplyNet, "POWER", kNangateFILLCELLX8Power, std::size(kNangateFILLCELLX8Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateFILLCELLX8Ground, std::size(kNangateFILLCELLX8Ground)},
};

inline constexpr RectSpec kNangateHAX1PinA[] = {
    {"metal1", 1.01, 0.56, 1.08, 0.7},
    {"metal1", 0.67, 0.56, 1.08, 0.63},
    {"metal1", 0.355, 0.725, 0.74, 0.795},
    {"metal1", 0.67, 0.56, 0.74, 0.795},
    {"metal1", 0.355, 0.525, 0.425, 0.795},
};

inline constexpr RectSpec kNangateHAX1PinB[] = {
    {"metal1", 0.195, 0.86, 0.89, 0.93},
    {"metal1", 0.805, 0.7, 0.89, 0.93},
    {"metal1", 0.195, 0.525, 0.265, 0.93},
};

inline constexpr RectSpec kNangateHAX1PinCO[] = {
    {"metal1", 1.77, 0.15, 1.85, 1.25},
};

inline constexpr RectSpec kNangateHAX1PinS[] = {
    {"metal1", 0.06, 0.29, 0.525, 0.36},
    {"metal1", 0.455, 0.15, 0.525, 0.36},
    {"metal1", 0.06, 0.995, 0.37, 1.065},
    {"metal1", 0.06, 0.29, 0.13, 1.065},
};

inline constexpr RectSpec kNangateHAX1Power[] = {
    {"metal1", 0.0, 1.315, 1.9, 1.485},
    {"metal1", 1.59, 1.08, 1.66, 1.485},
    {"metal1", 1.22, 0.94, 1.29, 1.485},
    {"metal1", 0.645, 1.08, 0.715, 1.485},
};

inline constexpr RectSpec kNangateHAX1Ground[] = {
    {"metal1", 0.0, -0.085, 1.9, 0.085},
    {"metal1", 1.59, -0.085, 1.66, 0.285},
    {"metal1", 1.03, -0.085, 1.1, 0.285},
    {"metal1", 0.645, -0.085, 0.715, 0.285},
    {"metal1", 0.08, -0.085, 0.15, 0.225},
};

inline constexpr RectSpec kNangateHAX1ObsGroup0[] = {
    {"metal1", 1.4, 0.15, 1.47, 1.115, true},
    {"metal1", 1.4, 0.525, 1.705, 0.66, true},
    {"metal1", 1.22, 0.15, 1.47, 0.285, true},
};

inline constexpr RectSpec kNangateHAX1ObsGroup1[] = {
    {"metal1", 1.035, 0.765, 1.105, 1.115, true},
    {"metal1", 1.035, 0.765, 1.25, 0.835, true},
    {"metal1", 1.18, 0.425, 1.25, 0.835, true},
    {"metal1", 0.535, 0.425, 0.605, 0.66, true},
    {"metal1", 0.535, 0.425, 1.25, 0.495, true},
    {"metal1", 0.84, 0.15, 0.91, 0.495, true},
};

inline constexpr RectSpec kNangateHAX1ObsGroup2[] = {
    {"metal1", 0.05, 1.13, 0.56, 1.2, true},
};

inline constexpr GroupSpec kNangateHAX1Groups[] = {
    {BindingKind::kPinNet, "A", kNangateHAX1PinA, std::size(kNangateHAX1PinA)},
    {BindingKind::kPinNet, "B", kNangateHAX1PinB, std::size(kNangateHAX1PinB)},
    {BindingKind::kPinNet, "CO", kNangateHAX1PinCO, std::size(kNangateHAX1PinCO)},
    {BindingKind::kPinNet, "S", kNangateHAX1PinS, std::size(kNangateHAX1PinS)},
    {BindingKind::kSupplyNet, "POWER", kNangateHAX1Power, std::size(kNangateHAX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateHAX1Ground, std::size(kNangateHAX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateHAX1ObsGroup0, std::size(kNangateHAX1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateHAX1ObsGroup1, std::size(kNangateHAX1ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateHAX1ObsGroup2, std::size(kNangateHAX1ObsGroup2)},
};

inline constexpr RectSpec kNangateINVX1PinA[] = {
    {"metal1", 0.06, 0.525, 0.165, 0.7},
};

inline constexpr RectSpec kNangateINVX1PinZN[] = {
    {"metal1", 0.23, 0.15, 0.325, 1.25},
};

inline constexpr RectSpec kNangateINVX1Power[] = {
    {"metal1", 0.0, 1.315, 0.38, 1.485},
    {"metal1", 0.04, 0.975, 0.11, 1.485},
};

inline constexpr RectSpec kNangateINVX1Ground[] = {
    {"metal1", 0.0, -0.085, 0.38, 0.085},
    {"metal1", 0.04, -0.085, 0.11, 0.425},
};

inline constexpr GroupSpec kNangateINVX1Groups[] = {
    {BindingKind::kPinNet, "A", kNangateINVX1PinA, std::size(kNangateINVX1PinA)},
    {BindingKind::kPinNet, "ZN", kNangateINVX1PinZN, std::size(kNangateINVX1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateINVX1Power, std::size(kNangateINVX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateINVX1Ground, std::size(kNangateINVX1Ground)},
};

inline constexpr RectSpec kNangateINVX16PinA[] = {
    {"metal1", 0.095, 1.05, 3.095, 1.12},
    {"metal1", 3.025, 0.525, 3.095, 1.12},
    {"metal1", 2.0, 0.525, 2.07, 1.12},
    {"metal1", 1.2, 0.525, 1.27, 1.12},
    {"metal1", 0.095, 0.525, 0.165, 1.12},
};

inline constexpr RectSpec kNangateINVX16PinZN[] = {
    {"metal1", 2.885, 0.15, 2.955, 0.985},
    {"metal1", 0.235, 0.28, 2.955, 0.42},
    {"metal1", 2.505, 0.15, 2.575, 0.985},
    {"metal1", 2.135, 0.28, 2.205, 0.985},
    {"metal1", 2.125, 0.15, 2.195, 0.42},
    {"metal1", 1.745, 0.15, 1.815, 0.985},
    {"metal1", 1.365, 0.15, 1.435, 0.985},
    {"metal1", 0.985, 0.15, 1.055, 0.985},
    {"metal1", 0.605, 0.16, 0.675, 0.985},
    {"metal1", 0.235, 0.18, 0.305, 0.985},
};

inline constexpr RectSpec kNangateINVX16Power[] = {
    {"metal1", 0.0, 1.315, 3.23, 1.485},
    {"metal1", 3.075, 1.205, 3.145, 1.485},
    {"metal1", 2.695, 1.205, 2.765, 1.485},
    {"metal1", 2.315, 1.205, 2.385, 1.485},
    {"metal1", 1.935, 1.205, 2.005, 1.485},
    {"metal1", 1.555, 1.205, 1.625, 1.485},
    {"metal1", 1.175, 1.205, 1.245, 1.485},
    {"metal1", 0.795, 1.205, 0.865, 1.485},
    {"metal1", 0.415, 1.205, 0.485, 1.485},
    {"metal1", 0.04, 1.205, 0.11, 1.485},
};

inline constexpr RectSpec kNangateINVX16Ground[] = {
    {"metal1", 0.0, -0.085, 3.23, 0.085},
    {"metal1", 3.075, -0.085, 3.145, 0.365},
    {"metal1", 2.695, -0.085, 2.765, 0.21},
    {"metal1", 2.315, -0.085, 2.385, 0.21},
    {"metal1", 1.935, -0.085, 2.005, 0.21},
    {"metal1", 1.555, -0.085, 1.625, 0.21},
    {"metal1", 1.175, -0.085, 1.245, 0.21},
    {"metal1", 0.795, -0.085, 0.865, 0.21},
    {"metal1", 0.415, -0.085, 0.485, 0.21},
    {"metal1", 0.04, -0.085, 0.11, 0.365},
};

inline constexpr GroupSpec kNangateINVX16Groups[] = {
    {BindingKind::kPinNet, "A", kNangateINVX16PinA, std::size(kNangateINVX16PinA)},
    {BindingKind::kPinNet, "ZN", kNangateINVX16PinZN, std::size(kNangateINVX16PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateINVX16Power, std::size(kNangateINVX16Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateINVX16Ground, std::size(kNangateINVX16Ground)},
};

inline constexpr RectSpec kNangateINVX2PinA[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateINVX2PinZN[] = {
    {"metal1", 0.25, 0.15, 0.32, 1.25},
};

inline constexpr RectSpec kNangateINVX2Power[] = {
    {"metal1", 0.0, 1.315, 0.57, 1.485},
    {"metal1", 0.43, 0.975, 0.5, 1.485},
    {"metal1", 0.055, 0.975, 0.125, 1.485},
};

inline constexpr RectSpec kNangateINVX2Ground[] = {
    {"metal1", 0.0, -0.085, 0.57, 0.085},
    {"metal1", 0.43, -0.085, 0.5, 0.425},
    {"metal1", 0.055, -0.085, 0.125, 0.425},
};

inline constexpr GroupSpec kNangateINVX2Groups[] = {
    {BindingKind::kPinNet, "A", kNangateINVX2PinA, std::size(kNangateINVX2PinA)},
    {BindingKind::kPinNet, "ZN", kNangateINVX2PinZN, std::size(kNangateINVX2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateINVX2Power, std::size(kNangateINVX2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateINVX2Ground, std::size(kNangateINVX2Ground)},
};

inline constexpr RectSpec kNangateINVX32PinA[] = {
    {"metal1", 0.115, 0.93, 5.85, 1.0},
    {"metal1", 5.78, 0.525, 5.85, 1.0},
    {"metal1", 4.62, 0.525, 4.69, 1.0},
    {"metal1", 3.48, 0.525, 3.55, 1.0},
    {"metal1", 2.34, 0.525, 2.41, 1.0},
    {"metal1", 1.2, 0.525, 1.27, 1.0},
    {"metal1", 0.115, 0.525, 0.185, 1.0},
};

inline constexpr RectSpec kNangateINVX32PinZN[] = {
    {"metal1", 5.945, 0.16, 6.015, 1.005},
    {"metal1", 0.25, 0.28, 6.015, 0.42},
    {"metal1", 5.56, 0.16, 5.63, 0.865},
    {"metal1", 5.18, 0.16, 5.25, 0.865},
    {"metal1", 4.81, 0.28, 4.88, 0.865},
    {"metal1", 4.8, 0.16, 4.87, 0.42},
    {"metal1", 4.42, 0.16, 4.49, 0.865},
    {"metal1", 4.04, 0.16, 4.11, 0.865},
    {"metal1", 3.665, 0.16, 3.735, 0.865},
    {"metal1", 3.28, 0.16, 3.35, 0.865},
    {"metal1", 2.9, 0.16, 2.97, 0.865},
    {"metal1", 2.525, 0.16, 2.595, 0.865},
    {"metal1", 2.14, 0.16, 2.21, 0.865},
    {"metal1", 1.76, 0.16, 1.83, 0.865},
    {"metal1", 1.39, 0.16, 1.46, 0.865},
    {"metal1", 1.0, 0.16, 1.07, 0.865},
    {"metal1", 0.62, 0.16, 0.69, 0.865},
    {"metal1", 0.25, 0.16, 0.32, 0.865},
};

inline constexpr RectSpec kNangateINVX32Power[] = {
    {"metal1", 0.0, 1.315, 6.27, 1.485},
    {"metal1", 6.13, 1.065, 6.2, 1.485},
    {"metal1", 5.75, 1.065, 5.82, 1.485},
    {"metal1", 5.37, 1.065, 5.44, 1.485},
    {"metal1", 4.99, 1.065, 5.06, 1.485},
    {"metal1", 4.61, 1.065, 4.68, 1.485},
    {"metal1", 4.23, 1.065, 4.3, 1.485},
    {"metal1", 3.85, 1.065, 3.92, 1.485},
    {"metal1", 3.47, 1.065, 3.54, 1.485},
    {"metal1", 3.09, 1.065, 3.16, 1.485},
    {"metal1", 2.71, 1.065, 2.78, 1.485},
    {"metal1", 2.33, 1.065, 2.4, 1.485},
    {"metal1", 1.95, 1.065, 2.02, 1.485},
    {"metal1", 1.57, 1.065, 1.64, 1.485},
    {"metal1", 1.19, 1.065, 1.26, 1.485},
    {"metal1", 0.81, 1.065, 0.88, 1.485},
    {"metal1", 0.43, 1.065, 0.5, 1.485},
    {"metal1", 0.055, 1.065, 0.125, 1.485},
};

inline constexpr RectSpec kNangateINVX32Ground[] = {
    {"metal1", 0.0, -0.085, 6.27, 0.085},
    {"metal1", 6.13, -0.085, 6.2, 0.335},
    {"metal1", 5.75, -0.085, 5.82, 0.195},
    {"metal1", 5.37, -0.085, 5.44, 0.195},
    {"metal1", 4.99, -0.085, 5.06, 0.195},
    {"metal1", 4.61, -0.085, 4.68, 0.195},
    {"metal1", 4.23, -0.085, 4.3, 0.195},
    {"metal1", 3.85, -0.085, 3.92, 0.195},
    {"metal1", 3.47, -0.085, 3.54, 0.195},
    {"metal1", 3.09, -0.085, 3.16, 0.195},
    {"metal1", 2.71, -0.085, 2.78, 0.195},
    {"metal1", 2.33, -0.085, 2.4, 0.195},
    {"metal1", 1.95, -0.085, 2.02, 0.195},
    {"metal1", 1.57, -0.085, 1.64, 0.195},
    {"metal1", 1.19, -0.085, 1.26, 0.195},
    {"metal1", 0.81, -0.085, 0.88, 0.195},
    {"metal1", 0.43, -0.085, 0.5, 0.195},
    {"metal1", 0.055, -0.085, 0.125, 0.335},
};

inline constexpr GroupSpec kNangateINVX32Groups[] = {
    {BindingKind::kPinNet, "A", kNangateINVX32PinA, std::size(kNangateINVX32PinA)},
    {BindingKind::kPinNet, "ZN", kNangateINVX32PinZN, std::size(kNangateINVX32PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateINVX32Power, std::size(kNangateINVX32Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateINVX32Ground, std::size(kNangateINVX32Ground)},
};

inline constexpr RectSpec kNangateINVX4PinA[] = {
    {"metal1", 0.06, 0.525, 0.17, 0.7},
};

inline constexpr RectSpec kNangateINVX4PinZN[] = {
    {"metal1", 0.615, 0.15, 0.685, 1.04},
    {"metal1", 0.235, 0.56, 0.685, 0.7},
    {"metal1", 0.61, 0.15, 0.685, 0.7},
    {"metal1", 0.235, 0.15, 0.305, 1.04},
};

inline constexpr RectSpec kNangateINVX4Power[] = {
    {"metal1", 0.0, 1.315, 0.95, 1.485},
    {"metal1", 0.795, 0.98, 0.865, 1.485},
    {"metal1", 0.415, 0.98, 0.485, 1.485},
    {"metal1", 0.04, 0.98, 0.11, 1.485},
};

inline constexpr RectSpec kNangateINVX4Ground[] = {
    {"metal1", 0.0, -0.085, 0.95, 0.085},
    {"metal1", 0.795, -0.085, 0.865, 0.425},
    {"metal1", 0.415, -0.085, 0.485, 0.425},
    {"metal1", 0.04, -0.085, 0.11, 0.425},
};

inline constexpr GroupSpec kNangateINVX4Groups[] = {
    {BindingKind::kPinNet, "A", kNangateINVX4PinA, std::size(kNangateINVX4PinA)},
    {BindingKind::kPinNet, "ZN", kNangateINVX4PinZN, std::size(kNangateINVX4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateINVX4Power, std::size(kNangateINVX4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateINVX4Ground, std::size(kNangateINVX4Ground)},
};

inline constexpr RectSpec kNangateINVX8PinA[] = {
    {"metal1", 0.06, 0.525, 0.17, 0.7},
};

inline constexpr RectSpec kNangateINVX8PinZN[] = {
    {"metal1", 1.375, 0.15, 1.445, 1.04},
    {"metal1", 0.235, 0.56, 1.445, 0.7},
    {"metal1", 0.985, 0.15, 1.055, 1.04},
    {"metal1", 0.605, 0.15, 0.675, 1.04},
    {"metal1", 0.235, 0.15, 0.305, 1.04},
};

inline constexpr RectSpec kNangateINVX8Power[] = {
    {"metal1", 0.0, 1.315, 1.71, 1.485},
    {"metal1", 1.555, 0.97, 1.625, 1.485},
    {"metal1", 1.175, 0.97, 1.245, 1.485},
    {"metal1", 0.795, 0.97, 0.865, 1.485},
    {"metal1", 0.415, 0.97, 0.485, 1.485},
    {"metal1", 0.04, 0.97, 0.11, 1.485},
};

inline constexpr RectSpec kNangateINVX8Ground[] = {
    {"metal1", 0.0, -0.085, 1.71, 0.085},
    {"metal1", 1.555, -0.085, 1.625, 0.36},
    {"metal1", 1.175, -0.085, 1.245, 0.36},
    {"metal1", 0.795, -0.085, 0.865, 0.36},
    {"metal1", 0.415, -0.085, 0.485, 0.36},
    {"metal1", 0.04, -0.085, 0.11, 0.36},
};

inline constexpr GroupSpec kNangateINVX8Groups[] = {
    {BindingKind::kPinNet, "A", kNangateINVX8PinA, std::size(kNangateINVX8PinA)},
    {BindingKind::kPinNet, "ZN", kNangateINVX8PinZN, std::size(kNangateINVX8PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateINVX8Power, std::size(kNangateINVX8Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateINVX8Ground, std::size(kNangateINVX8Ground)},
};

inline constexpr RectSpec kNangateLOGIC0X1PinZ[] = {
    {"metal1", 0.06, 0.15, 0.13, 0.84},
};

inline constexpr RectSpec kNangateLOGIC0X1Power[] = {
    {"metal1", 0.0, 1.315, 0.38, 1.485},
    {"metal1", 0.245, 1.115, 0.315, 1.485},
};

inline constexpr RectSpec kNangateLOGIC0X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.38, 0.085},
    {"metal1", 0.24, -0.085, 0.31, 0.285},
};

inline constexpr RectSpec kNangateLOGIC0X1ObsGroup0[] = {
    {"metal1", 0.06, 0.975, 0.18, 1.25, true},
};

inline constexpr GroupSpec kNangateLOGIC0X1Groups[] = {
    {BindingKind::kPinNet, "Z", kNangateLOGIC0X1PinZ, std::size(kNangateLOGIC0X1PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateLOGIC0X1Power, std::size(kNangateLOGIC0X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateLOGIC0X1Ground, std::size(kNangateLOGIC0X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateLOGIC0X1ObsGroup0, std::size(kNangateLOGIC0X1ObsGroup0)},
};

inline constexpr RectSpec kNangateLOGIC1X1PinZ[] = {
    {"metal1", 0.06, 0.56, 0.13, 1.25},
};

inline constexpr RectSpec kNangateLOGIC1X1Power[] = {
    {"metal1", 0.0, 1.315, 0.38, 1.485},
    {"metal1", 0.24, 1.115, 0.31, 1.485},
};

inline constexpr RectSpec kNangateLOGIC1X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.38, 0.085},
    {"metal1", 0.245, -0.085, 0.315, 0.285},
};

inline constexpr RectSpec kNangateLOGIC1X1ObsGroup0[] = {
    {"metal1", 0.06, 0.15, 0.18, 0.425, true},
};

inline constexpr GroupSpec kNangateLOGIC1X1Groups[] = {
    {BindingKind::kPinNet, "Z", kNangateLOGIC1X1PinZ, std::size(kNangateLOGIC1X1PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateLOGIC1X1Power, std::size(kNangateLOGIC1X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateLOGIC1X1Ground, std::size(kNangateLOGIC1X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateLOGIC1X1ObsGroup0, std::size(kNangateLOGIC1X1ObsGroup0)},
};

inline constexpr RectSpec kNangateMUX2X1PinA[] = {
    {"metal1", 0.25, 0.525, 0.38, 0.7},
};

inline constexpr RectSpec kNangateMUX2X1PinB[] = {
    {"metal1", 0.82, 0.525, 0.95, 0.7},
};

inline constexpr RectSpec kNangateMUX2X1PinS[] = {
    {"metal1", 0.06, 0.765, 0.595, 0.835},
    {"metal1", 0.525, 0.535, 0.595, 0.835},
    {"metal1", 0.06, 0.525, 0.185, 0.835},
};

inline constexpr RectSpec kNangateMUX2X1PinZ[] = {
    {"metal1", 1.18, 0.19, 1.27, 1.23},
};

inline constexpr RectSpec kNangateMUX2X1Power[] = {
    {"metal1", 0.0, 1.315, 1.33, 1.485},
    {"metal1", 0.985, 0.975, 1.055, 1.485},
    {"metal1", 0.225, 1.035, 0.295, 1.485},
};

inline constexpr RectSpec kNangateMUX2X1Ground[] = {
    {"metal1", 0.0, -0.085, 1.33, 0.085},
    {"metal1", 0.985, -0.085, 1.055, 0.24},
    {"metal1", 0.225, -0.085, 0.295, 0.24},
};

inline constexpr RectSpec kNangateMUX2X1ObsGroup0[] = {
    {"metal1", 0.58, 1.07, 0.92, 1.14, true},
    {"metal1", 0.85, 0.84, 0.92, 1.14, true},
    {"metal1", 0.85, 0.84, 1.115, 0.91, true},
    {"metal1", 1.045, 0.39, 1.115, 0.91, true},
    {"metal1", 0.83, 0.39, 1.115, 0.46, true},
    {"metal1", 0.83, 0.22, 0.9, 0.46, true},
    {"metal1", 0.58, 0.22, 0.9, 0.29, true},
};

inline constexpr RectSpec kNangateMUX2X1ObsGroup1[] = {
    {"metal1", 0.045, 0.9, 0.115, 1.25, true},
    {"metal1", 0.045, 0.9, 0.755, 0.97, true},
    {"metal1", 0.685, 0.39, 0.755, 0.97, true},
    {"metal1", 0.045, 0.39, 0.755, 0.46, true},
    {"metal1", 0.045, 0.19, 0.115, 0.46, true},
};

inline constexpr GroupSpec kNangateMUX2X1Groups[] = {
    {BindingKind::kPinNet, "A", kNangateMUX2X1PinA, std::size(kNangateMUX2X1PinA)},
    {BindingKind::kPinNet, "B", kNangateMUX2X1PinB, std::size(kNangateMUX2X1PinB)},
    {BindingKind::kPinNet, "S", kNangateMUX2X1PinS, std::size(kNangateMUX2X1PinS)},
    {BindingKind::kPinNet, "Z", kNangateMUX2X1PinZ, std::size(kNangateMUX2X1PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateMUX2X1Power, std::size(kNangateMUX2X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateMUX2X1Ground, std::size(kNangateMUX2X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateMUX2X1ObsGroup0, std::size(kNangateMUX2X1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateMUX2X1ObsGroup1, std::size(kNangateMUX2X1ObsGroup1)},
};

inline constexpr RectSpec kNangateMUX2X2PinA[] = {
    {"metal1", 0.06, 0.525, 0.225, 0.7},
};

inline constexpr RectSpec kNangateMUX2X2PinB[] = {
    {"metal1", 0.575, 0.525, 0.7, 0.7},
};

inline constexpr RectSpec kNangateMUX2X2PinS[] = {
    {"metal1", 0.925, 0.85, 1.535, 0.92},
    {"metal1", 1.465, 0.525, 1.535, 0.92},
    {"metal1", 0.925, 0.525, 0.995, 0.92},
    {"metal1", 0.77, 0.525, 0.995, 0.7},
};

inline constexpr RectSpec kNangateMUX2X2PinZ[] = {
    {"metal1", 1.2, 0.15, 1.29, 0.785},
};

inline constexpr RectSpec kNangateMUX2X2Power[] = {
    {"metal1", 0.0, 1.315, 1.71, 1.485},
    {"metal1", 1.405, 1.205, 1.475, 1.485},
    {"metal1", 1.035, 1.205, 1.105, 1.485},
    {"metal1", 0.24, 1.24, 0.375, 1.485},
};

inline constexpr RectSpec kNangateMUX2X2Ground[] = {
    {"metal1", 0.0, -0.085, 1.71, 0.085},
    {"metal1", 1.405, -0.085, 1.475, 0.285},
    {"metal1", 1.03, -0.085, 1.1, 0.285},
    {"metal1", 0.46, -0.085, 0.53, 0.285},
};

inline constexpr RectSpec kNangateMUX2X2ObsGroup0[] = {
    {"metal1", 1.6, 0.15, 1.67, 1.25, true},
    {"metal1", 0.79, 0.985, 1.67, 1.055, true},
    {"metal1", 0.79, 0.765, 0.86, 1.055, true},
    {"metal1", 0.425, 0.765, 0.86, 0.835, true},
    {"metal1", 0.425, 0.525, 0.495, 0.835, true},
};

inline constexpr RectSpec kNangateMUX2X2ObsGroup1[] = {
    {"metal1", 0.655, 0.9, 0.725, 1.075, true},
    {"metal1", 0.29, 0.9, 0.725, 0.97, true},
    {"metal1", 0.29, 0.385, 0.36, 0.97, true},
    {"metal1", 1.065, 0.385, 1.135, 0.66, true},
    {"metal1", 0.09, 0.385, 1.135, 0.455, true},
    {"metal1", 0.845, 0.15, 0.915, 0.455, true},
    {"metal1", 0.09, 0.15, 0.16, 0.455, true},
};

inline constexpr RectSpec kNangateMUX2X2ObsGroup2[] = {
    {"metal1", 0.46, 1.175, 0.955, 1.245, true},
    {"metal1", 0.46, 1.065, 0.53, 1.245, true},
    {"metal1", 0.09, 1.065, 0.53, 1.135, true},
    {"metal1", 0.09, 0.86, 0.16, 1.135, true},
};

inline constexpr GroupSpec kNangateMUX2X2Groups[] = {
    {BindingKind::kPinNet, "A", kNangateMUX2X2PinA, std::size(kNangateMUX2X2PinA)},
    {BindingKind::kPinNet, "B", kNangateMUX2X2PinB, std::size(kNangateMUX2X2PinB)},
    {BindingKind::kPinNet, "S", kNangateMUX2X2PinS, std::size(kNangateMUX2X2PinS)},
    {BindingKind::kPinNet, "Z", kNangateMUX2X2PinZ, std::size(kNangateMUX2X2PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateMUX2X2Power, std::size(kNangateMUX2X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateMUX2X2Ground, std::size(kNangateMUX2X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateMUX2X2ObsGroup0, std::size(kNangateMUX2X2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateMUX2X2ObsGroup1, std::size(kNangateMUX2X2ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateMUX2X2ObsGroup2, std::size(kNangateMUX2X2ObsGroup2)},
};

inline constexpr RectSpec kNangateNAND2X1PinA1[] = {
    {"metal1", 0.385, 0.525, 0.51, 0.7},
};

inline constexpr RectSpec kNangateNAND2X1PinA2[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateNAND2X1PinZN[] = {
    {"metal1", 0.25, 0.355, 0.5, 0.425},
    {"metal1", 0.43, 0.15, 0.5, 0.425},
    {"metal1", 0.25, 0.355, 0.32, 1.25},
};

inline constexpr RectSpec kNangateNAND2X1Power[] = {
    {"metal1", 0.0, 1.315, 0.57, 1.485},
    {"metal1", 0.43, 0.975, 0.5, 1.485},
    {"metal1", 0.055, 0.975, 0.125, 1.485},
};

inline constexpr RectSpec kNangateNAND2X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.57, 0.085},
    {"metal1", 0.055, -0.085, 0.125, 0.425},
};

inline constexpr GroupSpec kNangateNAND2X1Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNAND2X1PinA1, std::size(kNangateNAND2X1PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNAND2X1PinA2, std::size(kNangateNAND2X1PinA2)},
    {BindingKind::kPinNet, "ZN", kNangateNAND2X1PinZN, std::size(kNangateNAND2X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNAND2X1Power, std::size(kNangateNAND2X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNAND2X1Ground, std::size(kNangateNAND2X1Ground)},
};

inline constexpr RectSpec kNangateNAND2X2PinA1[] = {
    {"metal1", 0.44, 0.525, 0.51, 0.7},
};

inline constexpr RectSpec kNangateNAND2X2PinA2[] = {
    {"metal1", 0.25, 0.77, 0.81, 0.84},
    {"metal1", 0.74, 0.525, 0.81, 0.84},
    {"metal1", 0.25, 0.525, 0.32, 0.84},
    {"metal1", 0.175, 0.525, 0.32, 0.66},
};

inline constexpr RectSpec kNangateNAND2X2PinZN[] = {
    {"metal1", 0.63, 0.905, 0.7, 1.25},
    {"metal1", 0.04, 0.905, 0.7, 0.975},
    {"metal1", 0.04, 0.39, 0.51, 0.46},
    {"metal1", 0.44, 0.15, 0.51, 0.46},
    {"metal1", 0.25, 0.905, 0.32, 1.25},
    {"metal1", 0.04, 0.39, 0.11, 0.975},
};

inline constexpr RectSpec kNangateNAND2X2Power[] = {
    {"metal1", 0.0, 1.315, 0.95, 1.485},
    {"metal1", 0.82, 1.04, 0.89, 1.485},
    {"metal1", 0.44, 1.04, 0.51, 1.485},
    {"metal1", 0.065, 1.04, 0.135, 1.485},
};

inline constexpr RectSpec kNangateNAND2X2Ground[] = {
    {"metal1", 0.0, -0.085, 0.95, 0.085},
    {"metal1", 0.82, -0.085, 0.89, 0.425},
    {"metal1", 0.065, -0.085, 0.135, 0.285},
};

inline constexpr GroupSpec kNangateNAND2X2Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNAND2X2PinA1, std::size(kNangateNAND2X2PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNAND2X2PinA2, std::size(kNangateNAND2X2PinA2)},
    {BindingKind::kPinNet, "ZN", kNangateNAND2X2PinZN, std::size(kNangateNAND2X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNAND2X2Power, std::size(kNangateNAND2X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNAND2X2Ground, std::size(kNangateNAND2X2Ground)},
};

inline constexpr RectSpec kNangateNAND2X4PinA1[] = {
    {"metal1", 1.01, 0.525, 1.14, 0.7},
};

inline constexpr RectSpec kNangateNAND2X4PinA2[] = {
    {"metal1", 0.38, 0.525, 0.51, 0.7},
};

inline constexpr RectSpec kNangateNAND2X4PinZN[] = {
    {"metal1", 1.405, 0.35, 1.475, 1.07},
    {"metal1", 0.275, 0.785, 1.475, 0.855},
    {"metal1", 1.39, 0.35, 1.475, 0.855},
    {"metal1", 1.0, 0.35, 1.475, 0.42},
    {"metal1", 1.025, 0.785, 1.095, 1.07},
    {"metal1", 0.645, 0.785, 0.715, 1.07},
    {"metal1", 0.275, 0.785, 0.345, 1.07},
};

inline constexpr RectSpec kNangateNAND2X4Power[] = {
    {"metal1", 0.0, 1.315, 1.71, 1.485},
    {"metal1", 1.595, 1.04, 1.665, 1.485},
    {"metal1", 1.215, 1.04, 1.285, 1.485},
    {"metal1", 0.835, 1.04, 0.905, 1.485},
    {"metal1", 0.455, 1.04, 0.525, 1.485},
    {"metal1", 0.08, 1.04, 0.15, 1.485},
};

inline constexpr RectSpec kNangateNAND2X4Ground[] = {
    {"metal1", 0.0, -0.085, 1.71, 0.085},
    {"metal1", 0.645, -0.085, 0.715, 0.285},
    {"metal1", 0.265, -0.085, 0.335, 0.285},
};

inline constexpr RectSpec kNangateNAND2X4ObsGroup0[] = {
    {"metal1", 1.595, 0.15, 1.665, 0.425, true},
    {"metal1", 0.085, 0.355, 0.905, 0.425, true},
    {"metal1", 0.835, 0.15, 0.905, 0.425, true},
    {"metal1", 0.455, 0.15, 0.525, 0.425, true},
    {"metal1", 0.085, 0.15, 0.155, 0.425, true},
    {"metal1", 0.835, 0.15, 1.665, 0.22, true},
};

inline constexpr GroupSpec kNangateNAND2X4Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNAND2X4PinA1, std::size(kNangateNAND2X4PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNAND2X4PinA2, std::size(kNangateNAND2X4PinA2)},
    {BindingKind::kPinNet, "ZN", kNangateNAND2X4PinZN, std::size(kNangateNAND2X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNAND2X4Power, std::size(kNangateNAND2X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNAND2X4Ground, std::size(kNangateNAND2X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateNAND2X4ObsGroup0, std::size(kNangateNAND2X4ObsGroup0)},
};

inline constexpr RectSpec kNangateNAND3X1PinA1[] = {
    {"metal1", 0.44, 0.525, 0.54, 0.7},
};

inline constexpr RectSpec kNangateNAND3X1PinA2[] = {
    {"metal1", 0.25, 0.525, 0.375, 0.7},
};

inline constexpr RectSpec kNangateNAND3X1PinA3[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateNAND3X1PinZN[] = {
    {"metal1", 0.605, 0.15, 0.675, 1.25},
    {"metal1", 0.235, 0.8, 0.675, 0.87},
    {"metal1", 0.235, 0.8, 0.32, 1.25},
};

inline constexpr RectSpec kNangateNAND3X1Power[] = {
    {"metal1", 0.0, 1.315, 0.76, 1.485},
    {"metal1", 0.415, 0.975, 0.485, 1.485},
    {"metal1", 0.04, 0.975, 0.11, 1.485},
};

inline constexpr RectSpec kNangateNAND3X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.76, 0.085},
    {"metal1", 0.04, -0.085, 0.11, 0.425},
};

inline constexpr GroupSpec kNangateNAND3X1Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNAND3X1PinA1, std::size(kNangateNAND3X1PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNAND3X1PinA2, std::size(kNangateNAND3X1PinA2)},
    {BindingKind::kPinNet, "A3", kNangateNAND3X1PinA3, std::size(kNangateNAND3X1PinA3)},
    {BindingKind::kPinNet, "ZN", kNangateNAND3X1PinZN, std::size(kNangateNAND3X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNAND3X1Power, std::size(kNangateNAND3X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNAND3X1Ground, std::size(kNangateNAND3X1Ground)},
};

inline constexpr RectSpec kNangateNAND3X2PinA1[] = {
    {"metal1", 0.595, 0.56, 0.73, 0.7},
};

inline constexpr RectSpec kNangateNAND3X2PinA2[] = {
    {"metal1", 0.95, 0.42, 1.08, 0.7},
    {"metal1", 0.38, 0.42, 1.08, 0.49},
    {"metal1", 0.38, 0.42, 0.45, 0.66},
};

inline constexpr RectSpec kNangateNAND3X2PinA3[] = {
    {"metal1", 0.195, 0.77, 1.215, 0.84},
    {"metal1", 1.145, 0.525, 1.215, 0.84},
    {"metal1", 0.195, 0.7, 0.32, 0.84},
    {"metal1", 0.195, 0.525, 0.265, 0.84},
};

inline constexpr RectSpec kNangateNAND3X2PinZN[] = {
    {"metal1", 1.025, 0.905, 1.095, 1.25},
    {"metal1", 0.06, 0.905, 1.095, 0.975},
    {"metal1", 0.06, 0.265, 0.75, 0.335},
    {"metal1", 0.645, 0.905, 0.715, 1.25},
    {"metal1", 0.265, 0.905, 0.335, 1.25},
    {"metal1", 0.06, 0.265, 0.13, 0.975},
};

inline constexpr RectSpec kNangateNAND3X2Power[] = {
    {"metal1", 0.0, 1.315, 1.33, 1.485},
    {"metal1", 1.215, 1.04, 1.285, 1.485},
    {"metal1", 0.835, 1.04, 0.905, 1.485},
    {"metal1", 0.455, 1.04, 0.525, 1.485},
    {"metal1", 0.08, 1.04, 0.15, 1.485},
};

inline constexpr RectSpec kNangateNAND3X2Ground[] = {
    {"metal1", 0.0, -0.085, 1.33, 0.085},
    {"metal1", 1.215, -0.085, 1.285, 0.335},
    {"metal1", 0.08, -0.085, 0.15, 0.195},
};

inline constexpr GroupSpec kNangateNAND3X2Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNAND3X2PinA1, std::size(kNangateNAND3X2PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNAND3X2PinA2, std::size(kNangateNAND3X2PinA2)},
    {BindingKind::kPinNet, "A3", kNangateNAND3X2PinA3, std::size(kNangateNAND3X2PinA3)},
    {BindingKind::kPinNet, "ZN", kNangateNAND3X2PinZN, std::size(kNangateNAND3X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNAND3X2Power, std::size(kNangateNAND3X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNAND3X2Ground, std::size(kNangateNAND3X2Ground)},
};

inline constexpr RectSpec kNangateNAND3X4PinA1[] = {
    {"metal1", 1.66, 0.555, 1.89, 0.625},
    {"metal1", 1.66, 0.29, 1.73, 0.625},
    {"metal1", 0.82, 0.29, 1.73, 0.36},
    {"metal1", 0.625, 0.555, 0.89, 0.625},
    {"metal1", 0.82, 0.29, 0.89, 0.625},
};

inline constexpr RectSpec kNangateNAND3X4PinA2[] = {
    {"metal1", 1.525, 0.69, 2.13, 0.76},
    {"metal1", 2.06, 0.525, 2.13, 0.76},
    {"metal1", 1.525, 0.425, 1.595, 0.76},
    {"metal1", 0.955, 0.425, 1.595, 0.495},
    {"metal1", 0.38, 0.69, 1.08, 0.76},
    {"metal1", 0.955, 0.425, 1.08, 0.76},
    {"metal1", 0.38, 0.525, 0.45, 0.76},
};

inline constexpr RectSpec kNangateNAND3X4PinA3[] = {
    {"metal1", 0.19, 0.825, 2.3, 0.895},
    {"metal1", 2.23, 0.525, 2.3, 0.895},
    {"metal1", 1.19, 0.56, 1.325, 0.895},
    {"metal1", 0.19, 0.525, 0.26, 0.895},
};

inline constexpr RectSpec kNangateNAND3X4PinZN[] = {
    {"metal1", 0.055, 0.98, 2.435, 1.05},
    {"metal1", 2.365, 0.355, 2.435, 1.05},
    {"metal1", 1.795, 0.355, 2.435, 0.425},
    {"metal1", 2.165, 0.98, 2.235, 1.22},
    {"metal1", 0.265, 0.98, 2.235, 1.12},
    {"metal1", 1.795, 0.15, 1.865, 0.425},
    {"metal1", 1.785, 0.98, 1.855, 1.22},
    {"metal1", 1.405, 0.98, 1.475, 1.22},
    {"metal1", 1.025, 0.98, 1.095, 1.22},
    {"metal1", 0.645, 0.98, 0.715, 1.22},
    {"metal1", 0.055, 0.355, 0.715, 0.425},
    {"metal1", 0.645, 0.15, 0.715, 0.425},
    {"metal1", 0.265, 0.98, 0.335, 1.22},
    {"metal1", 0.055, 0.355, 0.125, 1.05},
};

inline constexpr RectSpec kNangateNAND3X4Power[] = {
    {"metal1", 0.0, 1.315, 2.47, 1.485},
    {"metal1", 2.355, 1.17, 2.425, 1.485},
    {"metal1", 1.945, 1.205, 2.08, 1.485},
    {"metal1", 1.565, 1.205, 1.7, 1.485},
    {"metal1", 1.185, 1.205, 1.32, 1.485},
    {"metal1", 0.805, 1.195, 0.94, 1.485},
    {"metal1", 0.425, 1.195, 0.56, 1.485},
    {"metal1", 0.08, 1.16, 0.15, 1.485},
};

inline constexpr RectSpec kNangateNAND3X4Ground[] = {
    {"metal1", 0.0, -0.085, 2.47, 0.085},
    {"metal1", 2.355, -0.085, 2.425, 0.195},
    {"metal1", 1.215, -0.085, 1.285, 0.195},
    {"metal1", 0.08, -0.085, 0.15, 0.195},
};

inline constexpr GroupSpec kNangateNAND3X4Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNAND3X4PinA1, std::size(kNangateNAND3X4PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNAND3X4PinA2, std::size(kNangateNAND3X4PinA2)},
    {BindingKind::kPinNet, "A3", kNangateNAND3X4PinA3, std::size(kNangateNAND3X4PinA3)},
    {BindingKind::kPinNet, "ZN", kNangateNAND3X4PinZN, std::size(kNangateNAND3X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNAND3X4Power, std::size(kNangateNAND3X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNAND3X4Ground, std::size(kNangateNAND3X4Ground)},
};

inline constexpr RectSpec kNangateNAND4X1PinA1[] = {
    {"metal1", 0.765, 0.525, 0.89, 0.7},
};

inline constexpr RectSpec kNangateNAND4X1PinA2[] = {
    {"metal1", 0.44, 0.42, 0.555, 0.66},
};

inline constexpr RectSpec kNangateNAND4X1PinA3[] = {
    {"metal1", 0.25, 0.42, 0.375, 0.66},
};

inline constexpr RectSpec kNangateNAND4X1PinA4[] = {
    {"metal1", 0.06, 0.42, 0.185, 0.66},
};

inline constexpr RectSpec kNangateNAND4X1PinZN[] = {
    {"metal1", 0.63, 0.355, 0.865, 0.425},
    {"metal1", 0.795, 0.15, 0.865, 0.425},
    {"metal1", 0.615, 0.84, 0.7, 1.25},
    {"metal1", 0.63, 0.355, 0.7, 1.25},
    {"metal1", 0.235, 0.84, 0.7, 0.91},
    {"metal1", 0.235, 0.84, 0.305, 1.25},
};

inline constexpr RectSpec kNangateNAND4X1Power[] = {
    {"metal1", 0.0, 1.315, 0.95, 1.485},
    {"metal1", 0.795, 0.975, 0.865, 1.485},
    {"metal1", 0.415, 0.975, 0.485, 1.485},
    {"metal1", 0.04, 0.975, 0.11, 1.485},
};

inline constexpr RectSpec kNangateNAND4X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.95, 0.085},
    {"metal1", 0.04, -0.085, 0.11, 0.355},
};

inline constexpr GroupSpec kNangateNAND4X1Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNAND4X1PinA1, std::size(kNangateNAND4X1PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNAND4X1PinA2, std::size(kNangateNAND4X1PinA2)},
    {BindingKind::kPinNet, "A3", kNangateNAND4X1PinA3, std::size(kNangateNAND4X1PinA3)},
    {BindingKind::kPinNet, "A4", kNangateNAND4X1PinA4, std::size(kNangateNAND4X1PinA4)},
    {BindingKind::kPinNet, "ZN", kNangateNAND4X1PinZN, std::size(kNangateNAND4X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNAND4X1Power, std::size(kNangateNAND4X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNAND4X1Ground, std::size(kNangateNAND4X1Ground)},
};

inline constexpr RectSpec kNangateNAND4X2PinA1[] = {
    {"metal1", 0.81, 0.42, 0.945, 0.625},
};

inline constexpr RectSpec kNangateNAND4X2PinA2[] = {
    {"metal1", 1.145, 0.285, 1.27, 0.66},
    {"metal1", 0.575, 0.285, 1.27, 0.355},
    {"metal1", 0.575, 0.285, 0.645, 0.66},
};

inline constexpr RectSpec kNangateNAND4X2PinA3[] = {
    {"metal1", 0.39, 0.725, 1.405, 0.795},
    {"metal1", 1.335, 0.525, 1.405, 0.795},
    {"metal1", 0.39, 0.525, 0.51, 0.795},
};

inline constexpr RectSpec kNangateNAND4X2PinA4[] = {
    {"metal1", 0.195, 0.86, 1.59, 0.93},
    {"metal1", 1.52, 0.525, 1.59, 0.93},
    {"metal1", 0.195, 0.525, 0.32, 0.93},
};

inline constexpr RectSpec kNangateNAND4X2PinZN[] = {
    {"metal1", 1.375, 0.995, 1.51, 1.25},
    {"metal1", 0.06, 0.995, 1.51, 1.065},
    {"metal1", 0.995, 0.995, 1.13, 1.25},
    {"metal1", 0.285, 0.15, 0.94, 0.22},
    {"metal1", 0.615, 0.995, 0.75, 1.25},
    {"metal1", 0.235, 0.995, 0.37, 1.25},
    {"metal1", 0.06, 0.39, 0.355, 0.46},
    {"metal1", 0.285, 0.15, 0.355, 0.46},
    {"metal1", 0.06, 0.39, 0.13, 1.065},
};

inline constexpr RectSpec kNangateNAND4X2Power[] = {
    {"metal1", 0.0, 1.315, 1.71, 1.485},
    {"metal1", 1.595, 1.065, 1.665, 1.485},
    {"metal1", 1.215, 1.13, 1.285, 1.485},
    {"metal1", 0.835, 1.13, 0.905, 1.485},
    {"metal1", 0.455, 1.13, 0.525, 1.485},
    {"metal1", 0.08, 1.13, 0.15, 1.485},
};

inline constexpr RectSpec kNangateNAND4X2Ground[] = {
    {"metal1", 0.0, -0.085, 1.71, 0.085},
    {"metal1", 1.595, -0.085, 1.665, 0.39},
    {"metal1", 0.08, -0.085, 0.15, 0.25},
};

inline constexpr GroupSpec kNangateNAND4X2Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNAND4X2PinA1, std::size(kNangateNAND4X2PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNAND4X2PinA2, std::size(kNangateNAND4X2PinA2)},
    {BindingKind::kPinNet, "A3", kNangateNAND4X2PinA3, std::size(kNangateNAND4X2PinA3)},
    {BindingKind::kPinNet, "A4", kNangateNAND4X2PinA4, std::size(kNangateNAND4X2PinA4)},
    {BindingKind::kPinNet, "ZN", kNangateNAND4X2PinZN, std::size(kNangateNAND4X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNAND4X2Power, std::size(kNangateNAND4X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNAND4X2Ground, std::size(kNangateNAND4X2Ground)},
};

inline constexpr RectSpec kNangateNAND4X4PinA1[] = {
    {"metal1", 0.405, 0.525, 0.51, 0.7},
};

inline constexpr RectSpec kNangateNAND4X4PinA2[] = {
    {"metal1", 1.17, 0.525, 1.27, 0.7},
};

inline constexpr RectSpec kNangateNAND4X4PinA3[] = {
    {"metal1", 2.15, 0.525, 2.22, 0.7},
};

inline constexpr RectSpec kNangateNAND4X4PinA4[] = {
    {"metal1", 2.91, 0.525, 2.98, 0.7},
};

inline constexpr RectSpec kNangateNAND4X4PinZN[] = {
    {"metal1", 3.27, 0.84, 3.34, 1.155},
    {"metal1", 0.09, 0.84, 3.34, 0.98},
    {"metal1", 2.89, 0.84, 2.96, 1.155},
    {"metal1", 2.51, 0.84, 2.58, 1.155},
    {"metal1", 2.13, 0.84, 2.2, 1.155},
    {"metal1", 1.68, 0.84, 1.75, 1.155},
    {"metal1", 1.22, 0.84, 1.29, 1.155},
    {"metal1", 0.84, 0.84, 0.91, 1.155},
    {"metal1", 0.685, 0.285, 0.755, 0.98},
    {"metal1", 0.225, 0.285, 0.755, 0.355},
    {"metal1", 0.46, 0.84, 0.53, 1.155},
    {"metal1", 0.09, 0.84, 0.16, 1.155},
};

inline constexpr RectSpec kNangateNAND4X4Power[] = {
    {"metal1", 0.0, 1.315, 3.42, 1.485},
    {"metal1", 3.05, 1.095, 3.185, 1.485},
    {"metal1", 2.67, 1.095, 2.805, 1.485},
    {"metal1", 2.29, 1.095, 2.425, 1.485},
    {"metal1", 1.91, 1.095, 2.045, 1.485},
    {"metal1", 1.38, 1.095, 1.515, 1.485},
    {"metal1", 1.0, 1.095, 1.135, 1.485},
    {"metal1", 0.62, 1.095, 0.755, 1.485},
    {"metal1", 0.24, 1.095, 0.375, 1.485},
};

inline constexpr RectSpec kNangateNAND4X4Ground[] = {
    {"metal1", 0.0, -0.085, 3.42, 0.085},
    {"metal1", 3.05, -0.085, 3.185, 0.3},
    {"metal1", 2.67, -0.085, 2.805, 0.3},
};

inline constexpr RectSpec kNangateNAND4X4ObsGroup0[] = {
    {"metal1", 2.51, 0.39, 3.34, 0.46, true},
    {"metal1", 3.27, 0.185, 3.34, 0.46, true},
    {"metal1", 1.76, 0.15, 1.83, 0.46, true},
    {"metal1", 2.89, 0.185, 2.96, 0.46, true},
    {"metal1", 2.51, 0.15, 2.58, 0.46, true},
    {"metal1", 1.76, 0.15, 2.58, 0.22, true},
};

inline constexpr RectSpec kNangateNAND4X4ObsGroup1[] = {
    {"metal1", 1.38, 0.525, 2.045, 0.595, true},
    {"metal1", 1.91, 0.285, 2.045, 0.595, true},
    {"metal1", 1.38, 0.285, 1.515, 0.595, true},
    {"metal1", 1.91, 0.285, 2.425, 0.355, true},
    {"metal1", 1.005, 0.285, 1.515, 0.355, true},
};

inline constexpr RectSpec kNangateNAND4X4ObsGroup2[] = {
    {"metal1", 1.6, 0.15, 1.67, 0.46, true},
    {"metal1", 0.84, 0.15, 0.91, 0.46, true},
    {"metal1", 0.09, 0.15, 0.16, 0.46, true},
    {"metal1", 0.09, 0.15, 1.67, 0.22, true},
};

inline constexpr GroupSpec kNangateNAND4X4Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNAND4X4PinA1, std::size(kNangateNAND4X4PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNAND4X4PinA2, std::size(kNangateNAND4X4PinA2)},
    {BindingKind::kPinNet, "A3", kNangateNAND4X4PinA3, std::size(kNangateNAND4X4PinA3)},
    {BindingKind::kPinNet, "A4", kNangateNAND4X4PinA4, std::size(kNangateNAND4X4PinA4)},
    {BindingKind::kPinNet, "ZN", kNangateNAND4X4PinZN, std::size(kNangateNAND4X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNAND4X4Power, std::size(kNangateNAND4X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNAND4X4Ground, std::size(kNangateNAND4X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateNAND4X4ObsGroup0, std::size(kNangateNAND4X4ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateNAND4X4ObsGroup1, std::size(kNangateNAND4X4ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateNAND4X4ObsGroup2, std::size(kNangateNAND4X4ObsGroup2)},
};

inline constexpr RectSpec kNangateNOR2X1PinA1[] = {
    {"metal1", 0.385, 0.525, 0.51, 0.7},
};

inline constexpr RectSpec kNangateNOR2X1PinA2[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateNOR2X1PinZN[] = {
    {"metal1", 0.43, 0.975, 0.5, 1.25},
    {"metal1", 0.25, 0.975, 0.5, 1.045},
    {"metal1", 0.25, 0.15, 0.32, 1.045},
};

inline constexpr RectSpec kNangateNOR2X1Power[] = {
    {"metal1", 0.0, 1.315, 0.57, 1.485},
    {"metal1", 0.055, 0.975, 0.125, 1.485},
};

inline constexpr RectSpec kNangateNOR2X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.57, 0.085},
    {"metal1", 0.43, -0.085, 0.5, 0.425},
    {"metal1", 0.055, -0.085, 0.125, 0.425},
};

inline constexpr GroupSpec kNangateNOR2X1Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNOR2X1PinA1, std::size(kNangateNOR2X1PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNOR2X1PinA2, std::size(kNangateNOR2X1PinA2)},
    {BindingKind::kPinNet, "ZN", kNangateNOR2X1PinZN, std::size(kNangateNOR2X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNOR2X1Power, std::size(kNangateNOR2X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNOR2X1Ground, std::size(kNangateNOR2X1Ground)},
};

inline constexpr RectSpec kNangateNOR2X2PinA1[] = {
    {"metal1", 0.44, 0.42, 0.51, 0.66},
};

inline constexpr RectSpec kNangateNOR2X2PinA2[] = {
    {"metal1", 0.195, 0.725, 0.89, 0.795},
    {"metal1", 0.76, 0.525, 0.89, 0.795},
    {"metal1", 0.195, 0.525, 0.265, 0.795},
};

inline constexpr RectSpec kNangateNOR2X2PinZN[] = {
    {"metal1", 0.06, 0.26, 0.75, 0.33},
    {"metal1", 0.455, 0.91, 0.525, 1.25},
    {"metal1", 0.06, 0.91, 0.525, 0.98},
    {"metal1", 0.06, 0.26, 0.13, 0.98},
};

inline constexpr RectSpec kNangateNOR2X2Power[] = {
    {"metal1", 0.0, 1.315, 0.95, 1.485},
    {"metal1", 0.835, 1.045, 0.905, 1.485},
    {"metal1", 0.08, 1.045, 0.15, 1.485},
};

inline constexpr RectSpec kNangateNOR2X2Ground[] = {
    {"metal1", 0.0, -0.085, 0.95, 0.085},
    {"metal1", 0.835, -0.085, 0.905, 0.335},
    {"metal1", 0.455, -0.085, 0.525, 0.195},
    {"metal1", 0.08, -0.085, 0.15, 0.195},
};

inline constexpr GroupSpec kNangateNOR2X2Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNOR2X2PinA1, std::size(kNangateNOR2X2PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNOR2X2PinA2, std::size(kNangateNOR2X2PinA2)},
    {BindingKind::kPinNet, "ZN", kNangateNOR2X2PinZN, std::size(kNangateNOR2X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNOR2X2Power, std::size(kNangateNOR2X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNOR2X2Ground, std::size(kNangateNOR2X2Ground)},
};

inline constexpr RectSpec kNangateNOR2X4PinA1[] = {
    {"metal1", 1.09, 0.42, 1.16, 0.66},
    {"metal1", 0.59, 0.42, 1.16, 0.49},
    {"metal1", 0.59, 0.42, 0.7, 0.66},
};

inline constexpr RectSpec kNangateNOR2X4PinA2[] = {
    {"metal1", 0.215, 0.91, 1.535, 0.98},
    {"metal1", 1.465, 0.525, 1.535, 0.98},
    {"metal1", 0.805, 0.56, 0.94, 0.98},
    {"metal1", 0.215, 0.525, 0.285, 0.98},
};

inline constexpr RectSpec kNangateNOR2X4PinZN[] = {
    {"metal1", 0.24, 0.28, 1.51, 0.35},
    {"metal1", 1.225, 0.28, 1.295, 0.845},
    {"metal1", 0.44, 0.28, 0.525, 0.845},
};

inline constexpr RectSpec kNangateNOR2X4Power[] = {
    {"metal1", 0.0, 1.315, 1.71, 1.485},
    {"metal1", 1.6, 0.71, 1.67, 1.485},
    {"metal1", 0.835, 1.045, 0.905, 1.485},
    {"metal1", 0.08, 0.71, 0.15, 1.485},
};

inline constexpr RectSpec kNangateNOR2X4Ground[] = {
    {"metal1", 0.0, -0.085, 1.71, 0.085},
    {"metal1", 1.595, -0.085, 1.665, 0.39},
    {"metal1", 1.215, -0.085, 1.285, 0.195},
    {"metal1", 0.835, -0.085, 0.905, 0.195},
    {"metal1", 0.455, -0.085, 0.525, 0.195},
    {"metal1", 0.08, -0.085, 0.15, 0.39},
};

inline constexpr GroupSpec kNangateNOR2X4Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNOR2X4PinA1, std::size(kNangateNOR2X4PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNOR2X4PinA2, std::size(kNangateNOR2X4PinA2)},
    {BindingKind::kPinNet, "ZN", kNangateNOR2X4PinZN, std::size(kNangateNOR2X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNOR2X4Power, std::size(kNangateNOR2X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNOR2X4Ground, std::size(kNangateNOR2X4Ground)},
};

inline constexpr RectSpec kNangateNOR3X1PinA1[] = {
    {"metal1", 0.44, 0.525, 0.545, 0.7},
};

inline constexpr RectSpec kNangateNOR3X1PinA2[] = {
    {"metal1", 0.25, 0.525, 0.375, 0.7},
};

inline constexpr RectSpec kNangateNOR3X1PinA3[] = {
    {"metal1", 0.06, 0.525, 0.175, 0.7},
};

inline constexpr RectSpec kNangateNOR3X1PinZN[] = {
    {"metal1", 0.61, 0.15, 0.7, 1.0},
    {"metal1", 0.235, 0.355, 0.7, 0.425},
    {"metal1", 0.235, 0.15, 0.305, 0.425},
};

inline constexpr RectSpec kNangateNOR3X1Power[] = {
    {"metal1", 0.0, 1.315, 0.76, 1.485},
    {"metal1", 0.04, 0.975, 0.11, 1.485},
};

inline constexpr RectSpec kNangateNOR3X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.76, 0.085},
    {"metal1", 0.415, -0.085, 0.485, 0.22},
    {"metal1", 0.04, -0.085, 0.11, 0.425},
};

inline constexpr GroupSpec kNangateNOR3X1Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNOR3X1PinA1, std::size(kNangateNOR3X1PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNOR3X1PinA2, std::size(kNangateNOR3X1PinA2)},
    {BindingKind::kPinNet, "A3", kNangateNOR3X1PinA3, std::size(kNangateNOR3X1PinA3)},
    {BindingKind::kPinNet, "ZN", kNangateNOR3X1PinZN, std::size(kNangateNOR3X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNOR3X1Power, std::size(kNangateNOR3X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNOR3X1Ground, std::size(kNangateNOR3X1Ground)},
};

inline constexpr RectSpec kNangateNOR3X2PinA1[] = {
    {"metal1", 0.62, 0.56, 0.755, 0.7},
};

inline constexpr RectSpec kNangateNOR3X2PinA2[] = {
    {"metal1", 0.92, 0.425, 0.99, 0.66},
    {"metal1", 0.39, 0.425, 0.99, 0.495},
    {"metal1", 0.39, 0.425, 0.51, 0.7},
};

inline constexpr RectSpec kNangateNOR3X2PinA3[] = {
    {"metal1", 0.195, 0.77, 1.27, 0.84},
    {"metal1", 1.145, 0.525, 1.27, 0.84},
    {"metal1", 0.195, 0.525, 0.265, 0.84},
};

inline constexpr RectSpec kNangateNOR3X2PinZN[] = {
    {"metal1", 0.06, 0.285, 1.13, 0.355},
    {"metal1", 0.645, 0.905, 0.715, 1.18},
    {"metal1", 0.06, 0.905, 0.715, 0.975},
    {"metal1", 0.06, 0.285, 0.13, 0.975},
};

inline constexpr RectSpec kNangateNOR3X2Power[] = {
    {"metal1", 0.0, 1.315, 1.33, 1.485},
    {"metal1", 1.215, 1.065, 1.285, 1.485},
    {"metal1", 0.08, 1.065, 0.15, 1.485},
};

inline constexpr RectSpec kNangateNOR3X2Ground[] = {
    {"metal1", 0.0, -0.085, 1.33, 0.085},
    {"metal1", 1.215, -0.085, 1.285, 0.335},
    {"metal1", 0.835, -0.085, 0.905, 0.195},
    {"metal1", 0.455, -0.085, 0.525, 0.195},
    {"metal1", 0.08, -0.085, 0.15, 0.195},
};

inline constexpr GroupSpec kNangateNOR3X2Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNOR3X2PinA1, std::size(kNangateNOR3X2PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNOR3X2PinA2, std::size(kNangateNOR3X2PinA2)},
    {BindingKind::kPinNet, "A3", kNangateNOR3X2PinA3, std::size(kNangateNOR3X2PinA3)},
    {BindingKind::kPinNet, "ZN", kNangateNOR3X2PinZN, std::size(kNangateNOR3X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNOR3X2Power, std::size(kNangateNOR3X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNOR3X2Ground, std::size(kNangateNOR3X2Ground)},
};

inline constexpr RectSpec kNangateNOR3X4PinA1[] = {
    {"metal1", 0.425, 0.525, 0.51, 0.7},
};

inline constexpr RectSpec kNangateNOR3X4PinA2[] = {
    {"metal1", 1.185, 0.525, 1.27, 0.7},
};

inline constexpr RectSpec kNangateNOR3X4PinA3[] = {
    {"metal1", 2.13, 0.525, 2.23, 0.7},
};

inline constexpr RectSpec kNangateNOR3X4PinZN[] = {
    {"metal1", 0.235, 0.39, 2.38, 0.46},
    {"metal1", 2.31, 0.15, 2.38, 0.46},
    {"metal1", 1.93, 0.15, 2.0, 0.46},
    {"metal1", 1.365, 0.15, 1.435, 0.46},
    {"metal1", 0.985, 0.15, 1.055, 0.46},
    {"metal1", 0.605, 0.765, 0.675, 1.115},
    {"metal1", 0.605, 0.15, 0.675, 0.46},
    {"metal1", 0.235, 0.765, 0.675, 0.835},
    {"metal1", 0.235, 0.39, 0.32, 0.835},
    {"metal1", 0.235, 0.15, 0.305, 1.115},
};

inline constexpr RectSpec kNangateNOR3X4Power[] = {
    {"metal1", 0.0, 1.315, 2.66, 1.485},
    {"metal1", 2.5, 0.9, 2.57, 1.485},
    {"metal1", 2.09, 0.935, 2.225, 1.485},
    {"metal1", 1.745, 0.9, 1.815, 1.485},
};

inline constexpr RectSpec kNangateNOR3X4Ground[] = {
    {"metal1", 0.0, -0.085, 2.66, 0.085},
    {"metal1", 2.505, -0.085, 2.575, 0.425},
    {"metal1", 2.09, -0.085, 2.225, 0.325},
    {"metal1", 1.525, -0.085, 1.85, 0.325},
    {"metal1", 1.145, -0.085, 1.28, 0.325},
    {"metal1", 0.765, -0.085, 0.9, 0.325},
    {"metal1", 0.385, -0.085, 0.52, 0.325},
    {"metal1", 0.04, -0.085, 0.11, 0.425},
};

inline constexpr RectSpec kNangateNOR3X4ObsGroup0[] = {
    {"metal1", 2.31, 0.765, 2.38, 1.175, true},
    {"metal1", 1.93, 0.765, 2.0, 1.175, true},
    {"metal1", 1.365, 0.765, 1.435, 1.115, true},
    {"metal1", 0.995, 0.765, 1.065, 1.115, true},
    {"metal1", 0.995, 0.765, 2.38, 0.835, true},
};

inline constexpr RectSpec kNangateNOR3X4ObsGroup1[] = {
    {"metal1", 0.045, 1.18, 1.625, 1.25, true},
    {"metal1", 1.555, 0.9, 1.625, 1.25, true},
    {"metal1", 1.175, 0.9, 1.245, 1.25, true},
    {"metal1", 0.795, 0.9, 0.865, 1.25, true},
    {"metal1", 0.415, 0.9, 0.485, 1.25, true},
    {"metal1", 0.045, 0.9, 0.115, 1.25, true},
};

inline constexpr GroupSpec kNangateNOR3X4Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNOR3X4PinA1, std::size(kNangateNOR3X4PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNOR3X4PinA2, std::size(kNangateNOR3X4PinA2)},
    {BindingKind::kPinNet, "A3", kNangateNOR3X4PinA3, std::size(kNangateNOR3X4PinA3)},
    {BindingKind::kPinNet, "ZN", kNangateNOR3X4PinZN, std::size(kNangateNOR3X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNOR3X4Power, std::size(kNangateNOR3X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNOR3X4Ground, std::size(kNangateNOR3X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateNOR3X4ObsGroup0, std::size(kNangateNOR3X4ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateNOR3X4ObsGroup1, std::size(kNangateNOR3X4ObsGroup1)},
};

inline constexpr RectSpec kNangateNOR4X1PinA1[] = {
    {"metal1", 0.765, 0.525, 0.89, 0.7},
};

inline constexpr RectSpec kNangateNOR4X1PinA2[] = {
    {"metal1", 0.44, 0.525, 0.565, 0.7},
};

inline constexpr RectSpec kNangateNOR4X1PinA3[] = {
    {"metal1", 0.25, 0.525, 0.375, 0.7},
};

inline constexpr RectSpec kNangateNOR4X1PinA4[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateNOR4X1PinZN[] = {
    {"metal1", 0.795, 0.975, 0.865, 1.25},
    {"metal1", 0.63, 0.975, 0.865, 1.045},
    {"metal1", 0.63, 0.15, 0.7, 1.045},
    {"metal1", 0.235, 0.355, 0.7, 0.425},
    {"metal1", 0.61, 0.15, 0.7, 0.425},
    {"metal1", 0.235, 0.15, 0.305, 0.425},
};

inline constexpr RectSpec kNangateNOR4X1Power[] = {
    {"metal1", 0.0, 1.315, 0.95, 1.485},
    {"metal1", 0.04, 0.975, 0.11, 1.485},
};

inline constexpr RectSpec kNangateNOR4X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.95, 0.085},
    {"metal1", 0.795, -0.085, 0.865, 0.425},
    {"metal1", 0.415, -0.085, 0.485, 0.285},
    {"metal1", 0.04, -0.085, 0.11, 0.425},
};

inline constexpr GroupSpec kNangateNOR4X1Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNOR4X1PinA1, std::size(kNangateNOR4X1PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNOR4X1PinA2, std::size(kNangateNOR4X1PinA2)},
    {BindingKind::kPinNet, "A3", kNangateNOR4X1PinA3, std::size(kNangateNOR4X1PinA3)},
    {BindingKind::kPinNet, "A4", kNangateNOR4X1PinA4, std::size(kNangateNOR4X1PinA4)},
    {BindingKind::kPinNet, "ZN", kNangateNOR4X1PinZN, std::size(kNangateNOR4X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNOR4X1Power, std::size(kNangateNOR4X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNOR4X1Ground, std::size(kNangateNOR4X1Ground)},
};

inline constexpr RectSpec kNangateNOR4X2PinA1[] = {
    {"metal1", 0.81, 0.56, 0.945, 0.7},
};

inline constexpr RectSpec kNangateNOR4X2PinA2[] = {
    {"metal1", 1.11, 0.42, 1.18, 0.66},
    {"metal1", 0.57, 0.42, 1.18, 0.49},
    {"metal1", 0.57, 0.42, 0.7, 0.7},
};

inline constexpr RectSpec kNangateNOR4X2PinA3[] = {
    {"metal1", 0.38, 0.765, 1.46, 0.835},
    {"metal1", 1.33, 0.525, 1.46, 0.835},
    {"metal1", 0.38, 0.525, 0.45, 0.835},
};

inline constexpr RectSpec kNangateNOR4X2PinA4[] = {
    {"metal1", 0.2, 0.91, 1.65, 0.98},
    {"metal1", 1.525, 0.84, 1.65, 0.98},
    {"metal1", 1.525, 0.525, 1.595, 0.98},
    {"metal1", 0.2, 0.525, 0.27, 0.98},
};

inline constexpr RectSpec kNangateNOR4X2PinZN[] = {
    {"metal1", 1.405, 0.15, 1.475, 0.425},
    {"metal1", 0.055, 0.26, 1.475, 0.33},
    {"metal1", 0.055, 1.055, 0.94, 1.125},
    {"metal1", 0.055, 0.26, 0.13, 1.125},
};

inline constexpr RectSpec kNangateNOR4X2Power[] = {
    {"metal1", 0.0, 1.315, 1.71, 1.485},
    {"metal1", 1.595, 1.065, 1.665, 1.485},
    {"metal1", 0.08, 1.205, 0.15, 1.485},
};

inline constexpr RectSpec kNangateNOR4X2Ground[] = {
    {"metal1", 0.0, -0.085, 1.71, 0.085},
    {"metal1", 1.595, -0.085, 1.665, 0.335},
    {"metal1", 1.185, -0.085, 1.32, 0.16},
    {"metal1", 0.805, -0.085, 0.94, 0.16},
    {"metal1", 0.425, -0.085, 0.56, 0.16},
    {"metal1", 0.08, -0.085, 0.15, 0.195},
};

inline constexpr GroupSpec kNangateNOR4X2Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNOR4X2PinA1, std::size(kNangateNOR4X2PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNOR4X2PinA2, std::size(kNangateNOR4X2PinA2)},
    {BindingKind::kPinNet, "A3", kNangateNOR4X2PinA3, std::size(kNangateNOR4X2PinA3)},
    {BindingKind::kPinNet, "A4", kNangateNOR4X2PinA4, std::size(kNangateNOR4X2PinA4)},
    {BindingKind::kPinNet, "ZN", kNangateNOR4X2PinZN, std::size(kNangateNOR4X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNOR4X2Power, std::size(kNangateNOR4X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNOR4X2Ground, std::size(kNangateNOR4X2Ground)},
};

inline constexpr RectSpec kNangateNOR4X4PinA1[] = {
    {"metal1", 0.425, 0.525, 0.51, 0.7},
};

inline constexpr RectSpec kNangateNOR4X4PinA2[] = {
    {"metal1", 1.18, 0.525, 1.27, 0.7},
};

inline constexpr RectSpec kNangateNOR4X4PinA3[] = {
    {"metal1", 2.15, 0.525, 2.245, 0.7},
};

inline constexpr RectSpec kNangateNOR4X4PinA4[] = {
    {"metal1", 2.91, 0.525, 3.0, 0.7},
};

inline constexpr RectSpec kNangateNOR4X4PinZN[] = {
    {"metal1", 0.235, 0.39, 3.375, 0.46},
    {"metal1", 3.305, 0.15, 3.375, 0.46},
    {"metal1", 2.925, 0.15, 2.995, 0.46},
    {"metal1", 2.545, 0.15, 2.615, 0.46},
    {"metal1", 2.165, 0.15, 2.235, 0.46},
    {"metal1", 1.79, 0.15, 1.86, 0.46},
    {"metal1", 1.37, 0.15, 1.44, 0.46},
    {"metal1", 0.985, 0.15, 1.055, 0.46},
    {"metal1", 0.605, 0.765, 0.675, 1.115},
    {"metal1", 0.605, 0.15, 0.675, 0.46},
    {"metal1", 0.235, 0.765, 0.675, 0.835},
    {"metal1", 0.235, 0.39, 0.32, 0.835},
    {"metal1", 0.235, 0.15, 0.305, 1.115},
};

inline constexpr RectSpec kNangateNOR4X4Power[] = {
    {"metal1", 0.0, 1.315, 3.42, 1.485},
    {"metal1", 3.085, 0.935, 3.22, 1.485},
    {"metal1", 2.705, 0.935, 2.84, 1.485},
};

inline constexpr RectSpec kNangateNOR4X4Ground[] = {
    {"metal1", 0.0, -0.085, 3.42, 0.085},
    {"metal1", 3.085, -0.085, 3.22, 0.325},
    {"metal1", 2.705, -0.085, 2.84, 0.325},
    {"metal1", 2.325, -0.085, 2.46, 0.325},
    {"metal1", 1.945, -0.085, 2.08, 0.325},
    {"metal1", 1.525, -0.085, 1.66, 0.325},
    {"metal1", 1.145, -0.085, 1.28, 0.325},
    {"metal1", 0.765, -0.085, 0.9, 0.325},
    {"metal1", 0.385, -0.085, 0.52, 0.325},
    {"metal1", 0.04, -0.085, 0.11, 0.36},
};

inline constexpr RectSpec kNangateNOR4X4ObsGroup0[] = {
    {"metal1", 3.305, 0.765, 3.375, 1.175, true},
    {"metal1", 2.925, 0.765, 2.995, 1.175, true},
    {"metal1", 2.545, 0.765, 2.615, 1.175, true},
    {"metal1", 2.165, 0.765, 2.235, 1.115, true},
    {"metal1", 1.795, 0.765, 1.865, 1.115, true},
    {"metal1", 1.795, 0.765, 3.375, 0.835, true},
};

inline constexpr RectSpec kNangateNOR4X4ObsGroup1[] = {
    {"metal1", 0.995, 1.18, 2.425, 1.25, true},
    {"metal1", 2.355, 0.9, 2.425, 1.25, true},
    {"metal1", 1.975, 0.9, 2.045, 1.25, true},
    {"metal1", 1.365, 0.9, 1.435, 1.25, true},
    {"metal1", 0.995, 0.9, 1.065, 1.25, true},
};

inline constexpr RectSpec kNangateNOR4X4ObsGroup2[] = {
    {"metal1", 0.045, 1.18, 0.865, 1.25, true},
    {"metal1", 0.795, 0.765, 0.865, 1.25, true},
    {"metal1", 0.415, 0.9, 0.485, 1.25, true},
    {"metal1", 0.045, 0.9, 0.115, 1.25, true},
    {"metal1", 1.555, 0.765, 1.625, 1.115, true},
    {"metal1", 1.175, 0.765, 1.245, 1.115, true},
    {"metal1", 0.795, 0.765, 1.625, 0.835, true},
};

inline constexpr GroupSpec kNangateNOR4X4Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateNOR4X4PinA1, std::size(kNangateNOR4X4PinA1)},
    {BindingKind::kPinNet, "A2", kNangateNOR4X4PinA2, std::size(kNangateNOR4X4PinA2)},
    {BindingKind::kPinNet, "A3", kNangateNOR4X4PinA3, std::size(kNangateNOR4X4PinA3)},
    {BindingKind::kPinNet, "A4", kNangateNOR4X4PinA4, std::size(kNangateNOR4X4PinA4)},
    {BindingKind::kPinNet, "ZN", kNangateNOR4X4PinZN, std::size(kNangateNOR4X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateNOR4X4Power, std::size(kNangateNOR4X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateNOR4X4Ground, std::size(kNangateNOR4X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateNOR4X4ObsGroup0, std::size(kNangateNOR4X4ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateNOR4X4ObsGroup1, std::size(kNangateNOR4X4ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateNOR4X4ObsGroup2, std::size(kNangateNOR4X4ObsGroup2)},
};

inline constexpr RectSpec kNangateOAI211X1PinA[] = {
    {"metal1", 0.575, 0.525, 0.7, 0.7},
};

inline constexpr RectSpec kNangateOAI211X1PinB[] = {
    {"metal1", 0.79, 0.525, 0.89, 0.7},
};

inline constexpr RectSpec kNangateOAI211X1PinC1[] = {
    {"metal1", 0.4, 0.525, 0.51, 0.7},
};

inline constexpr RectSpec kNangateOAI211X1PinC2[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateOAI211X1PinZN[] = {
    {"metal1", 0.835, 0.78, 0.905, 1.055},
    {"metal1", 0.25, 0.78, 0.905, 0.85},
    {"metal1", 0.455, 0.78, 0.525, 1.055},
    {"metal1", 0.25, 0.78, 0.525, 0.855},
    {"metal1", 0.25, 0.285, 0.335, 0.855},
};

inline constexpr RectSpec kNangateOAI211X1Power[] = {
    {"metal1", 0.0, 1.315, 0.95, 1.485},
    {"metal1", 0.645, 1.04, 0.715, 1.485},
    {"metal1", 0.08, 1.04, 0.15, 1.485},
};

inline constexpr RectSpec kNangateOAI211X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.95, 0.085},
    {"metal1", 0.835, -0.085, 0.905, 0.46},
};

inline constexpr RectSpec kNangateOAI211X1ObsGroup0[] = {
    {"metal1", 0.455, 0.15, 0.525, 0.425, true},
    {"metal1", 0.085, 0.15, 0.155, 0.425, true},
    {"metal1", 0.085, 0.15, 0.525, 0.22, true},
};

inline constexpr GroupSpec kNangateOAI211X1Groups[] = {
    {BindingKind::kPinNet, "A", kNangateOAI211X1PinA, std::size(kNangateOAI211X1PinA)},
    {BindingKind::kPinNet, "B", kNangateOAI211X1PinB, std::size(kNangateOAI211X1PinB)},
    {BindingKind::kPinNet, "C1", kNangateOAI211X1PinC1, std::size(kNangateOAI211X1PinC1)},
    {BindingKind::kPinNet, "C2", kNangateOAI211X1PinC2, std::size(kNangateOAI211X1PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateOAI211X1PinZN, std::size(kNangateOAI211X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOAI211X1Power, std::size(kNangateOAI211X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOAI211X1Ground, std::size(kNangateOAI211X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOAI211X1ObsGroup0, std::size(kNangateOAI211X1ObsGroup0)},
};

inline constexpr RectSpec kNangateOAI211X2PinA[] = {
    {"metal1", 0.185, 0.765, 0.755, 0.835},
    {"metal1", 0.685, 0.525, 0.755, 0.835},
    {"metal1", 0.185, 0.525, 0.32, 0.835},
};

inline constexpr RectSpec kNangateOAI211X2PinB[] = {
    {"metal1", 0.44, 0.525, 0.53, 0.7},
};

inline constexpr RectSpec kNangateOAI211X2PinC1[] = {
    {"metal1", 1.19, 0.525, 1.29, 0.7},
};

inline constexpr RectSpec kNangateOAI211X2PinC2[] = {
    {"metal1", 0.96, 0.77, 1.65, 0.84},
    {"metal1", 1.525, 0.525, 1.65, 0.84},
    {"metal1", 0.96, 0.525, 1.03, 0.84},
};

inline constexpr RectSpec kNangateOAI211X2PinZN[] = {
    {"metal1", 0.82, 0.39, 1.51, 0.46},
    {"metal1", 1.215, 0.905, 1.285, 1.25},
    {"metal1", 0.27, 0.905, 1.285, 0.975},
    {"metal1", 0.82, 0.39, 0.89, 0.975},
    {"metal1", 0.645, 0.905, 0.715, 1.25},
    {"metal1", 0.27, 0.905, 0.34, 1.25},
};

inline constexpr RectSpec kNangateOAI211X2Power[] = {
    {"metal1", 0.0, 1.315, 1.71, 1.485},
    {"metal1", 1.595, 1.04, 1.665, 1.485},
    {"metal1", 0.835, 1.04, 0.905, 1.485},
    {"metal1", 0.455, 1.04, 0.525, 1.485},
    {"metal1", 0.08, 1.04, 0.15, 1.485},
};

inline constexpr RectSpec kNangateOAI211X2Ground[] = {
    {"metal1", 0.0, -0.085, 1.71, 0.085},
    {"metal1", 0.45, -0.085, 0.52, 0.32},
};

inline constexpr RectSpec kNangateOAI211X2ObsGroup0[] = {
    {"metal1", 1.595, 0.185, 1.665, 0.46, true},
    {"metal1", 0.08, 0.39, 0.66, 0.46, true},
    {"metal1", 0.59, 0.185, 0.66, 0.46, true},
    {"metal1", 0.08, 0.185, 0.15, 0.46, true},
    {"metal1", 0.59, 0.185, 1.665, 0.255, true},
};

inline constexpr GroupSpec kNangateOAI211X2Groups[] = {
    {BindingKind::kPinNet, "A", kNangateOAI211X2PinA, std::size(kNangateOAI211X2PinA)},
    {BindingKind::kPinNet, "B", kNangateOAI211X2PinB, std::size(kNangateOAI211X2PinB)},
    {BindingKind::kPinNet, "C1", kNangateOAI211X2PinC1, std::size(kNangateOAI211X2PinC1)},
    {BindingKind::kPinNet, "C2", kNangateOAI211X2PinC2, std::size(kNangateOAI211X2PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateOAI211X2PinZN, std::size(kNangateOAI211X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOAI211X2Power, std::size(kNangateOAI211X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOAI211X2Ground, std::size(kNangateOAI211X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOAI211X2ObsGroup0, std::size(kNangateOAI211X2ObsGroup0)},
};

inline constexpr RectSpec kNangateOAI211X4PinA[] = {
    {"metal1", 1.39, 0.39, 1.52, 0.66},
    {"metal1", 0.125, 0.39, 1.52, 0.46},
    {"metal1", 0.805, 0.39, 0.875, 0.66},
    {"metal1", 0.125, 0.39, 0.195, 0.66},
};

inline constexpr RectSpec kNangateOAI211X4PinB[] = {
    {"metal1", 0.42, 0.77, 1.245, 0.84},
    {"metal1", 1.175, 0.525, 1.245, 0.84},
    {"metal1", 0.42, 0.525, 0.51, 0.84},
};

inline constexpr RectSpec kNangateOAI211X4PinC1[] = {
    {"metal1", 1.91, 0.77, 2.8, 0.84},
    {"metal1", 2.665, 0.56, 2.8, 0.84},
    {"metal1", 1.91, 0.56, 2.045, 0.84},
};

inline constexpr RectSpec kNangateOAI211X4PinC2[] = {
    {"metal1", 2.965, 0.425, 3.035, 0.66},
    {"metal1", 1.67, 0.425, 3.035, 0.495},
    {"metal1", 2.31, 0.425, 2.41, 0.7},
    {"metal1", 1.67, 0.425, 1.74, 0.66},
};

inline constexpr RectSpec kNangateOAI211X4PinZN[] = {
    {"metal1", 0.235, 0.905, 3.17, 0.975},
    {"metal1", 3.1, 0.29, 3.17, 0.975},
    {"metal1", 1.72, 0.29, 3.17, 0.36},
    {"metal1", 2.695, 0.905, 2.765, 1.25},
    {"metal1", 1.935, 0.905, 2.005, 1.25},
    {"metal1", 1.365, 0.905, 1.435, 1.25},
    {"metal1", 0.985, 0.905, 1.055, 1.25},
    {"metal1", 0.605, 0.905, 0.675, 1.25},
    {"metal1", 0.235, 0.905, 0.305, 1.25},
};

inline constexpr RectSpec kNangateOAI211X4Power[] = {
    {"metal1", 0.0, 1.315, 3.23, 1.485},
    {"metal1", 3.075, 1.04, 3.145, 1.485},
    {"metal1", 2.315, 1.04, 2.385, 1.485},
    {"metal1", 1.555, 1.04, 1.625, 1.485},
    {"metal1", 1.175, 1.04, 1.245, 1.485},
    {"metal1", 0.795, 1.04, 0.865, 1.485},
    {"metal1", 0.415, 1.04, 0.485, 1.485},
    {"metal1", 0.04, 1.04, 0.11, 1.485},
};

inline constexpr RectSpec kNangateOAI211X4Ground[] = {
    {"metal1", 0.0, -0.085, 3.23, 0.085},
    {"metal1", 1.145, -0.085, 1.28, 0.16},
    {"metal1", 0.385, -0.085, 0.52, 0.16},
};

inline constexpr RectSpec kNangateOAI211X4ObsGroup0[] = {
    {"metal1", 0.045, 0.225, 1.625, 0.295, true},
    {"metal1", 1.555, 0.15, 1.625, 0.295, true},
    {"metal1", 0.045, 0.15, 0.115, 0.295, true},
    {"metal1", 1.555, 0.15, 3.18, 0.22, true},
};

inline constexpr GroupSpec kNangateOAI211X4Groups[] = {
    {BindingKind::kPinNet, "A", kNangateOAI211X4PinA, std::size(kNangateOAI211X4PinA)},
    {BindingKind::kPinNet, "B", kNangateOAI211X4PinB, std::size(kNangateOAI211X4PinB)},
    {BindingKind::kPinNet, "C1", kNangateOAI211X4PinC1, std::size(kNangateOAI211X4PinC1)},
    {BindingKind::kPinNet, "C2", kNangateOAI211X4PinC2, std::size(kNangateOAI211X4PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateOAI211X4PinZN, std::size(kNangateOAI211X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOAI211X4Power, std::size(kNangateOAI211X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOAI211X4Ground, std::size(kNangateOAI211X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOAI211X4ObsGroup0, std::size(kNangateOAI211X4ObsGroup0)},
};

inline constexpr RectSpec kNangateOAI21X1PinA[] = {
    {"metal1", 0.575, 0.525, 0.7, 0.7},
};

inline constexpr RectSpec kNangateOAI21X1PinB1[] = {
    {"metal1", 0.385, 0.525, 0.51, 0.7},
};

inline constexpr RectSpec kNangateOAI21X1PinB2[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateOAI21X1PinZN[] = {
    {"metal1", 0.44, 0.765, 0.51, 1.25},
    {"metal1", 0.25, 0.765, 0.51, 0.835},
    {"metal1", 0.25, 0.285, 0.32, 0.835},
};

inline constexpr RectSpec kNangateOAI21X1Power[] = {
    {"metal1", 0.0, 1.315, 0.76, 1.485},
    {"metal1", 0.63, 0.975, 0.7, 1.485},
    {"metal1", 0.065, 0.975, 0.135, 1.485},
};

inline constexpr RectSpec kNangateOAI21X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.76, 0.085},
    {"metal1", 0.63, -0.085, 0.7, 0.46},
};

inline constexpr RectSpec kNangateOAI21X1ObsGroup0[] = {
    {"metal1", 0.44, 0.15, 0.51, 0.425, true},
    {"metal1", 0.07, 0.15, 0.14, 0.425, true},
    {"metal1", 0.07, 0.15, 0.51, 0.22, true},
};

inline constexpr GroupSpec kNangateOAI21X1Groups[] = {
    {BindingKind::kPinNet, "A", kNangateOAI21X1PinA, std::size(kNangateOAI21X1PinA)},
    {BindingKind::kPinNet, "B1", kNangateOAI21X1PinB1, std::size(kNangateOAI21X1PinB1)},
    {BindingKind::kPinNet, "B2", kNangateOAI21X1PinB2, std::size(kNangateOAI21X1PinB2)},
    {BindingKind::kPinNet, "ZN", kNangateOAI21X1PinZN, std::size(kNangateOAI21X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOAI21X1Power, std::size(kNangateOAI21X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOAI21X1Ground, std::size(kNangateOAI21X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOAI21X1ObsGroup0, std::size(kNangateOAI21X1ObsGroup0)},
};

inline constexpr RectSpec kNangateOAI21X2PinA[] = {
    {"metal1", 0.06, 0.525, 0.19, 0.7},
};

inline constexpr RectSpec kNangateOAI21X2PinB1[] = {
    {"metal1", 0.805, 0.525, 0.89, 0.7},
};

inline constexpr RectSpec kNangateOAI21X2PinB2[] = {
    {"metal1", 0.44, 0.77, 1.135, 0.84},
    {"metal1", 1.065, 0.525, 1.135, 0.84},
    {"metal1", 0.44, 0.525, 0.57, 0.84},
};

inline constexpr RectSpec kNangateOAI21X2PinZN[] = {
    {"metal1", 0.235, 0.905, 1.27, 0.975},
    {"metal1", 1.2, 0.355, 1.27, 0.975},
    {"metal1", 0.58, 0.355, 1.27, 0.425},
    {"metal1", 0.795, 0.905, 0.865, 1.25},
    {"metal1", 0.235, 0.905, 0.305, 1.25},
};

inline constexpr RectSpec kNangateOAI21X2Power[] = {
    {"metal1", 0.0, 1.315, 1.33, 1.485},
    {"metal1", 1.175, 1.04, 1.245, 1.485},
    {"metal1", 0.415, 1.04, 0.485, 1.485},
    {"metal1", 0.04, 1.04, 0.11, 1.485},
};

inline constexpr RectSpec kNangateOAI21X2Ground[] = {
    {"metal1", 0.0, -0.085, 1.33, 0.085},
    {"metal1", 0.225, -0.085, 0.295, 0.285},
};

inline constexpr RectSpec kNangateOAI21X2ObsGroup0[] = {
    {"metal1", 0.045, 0.355, 0.485, 0.425, true},
    {"metal1", 0.415, 0.15, 0.485, 0.425, true},
    {"metal1", 0.045, 0.15, 0.115, 0.425, true},
    {"metal1", 0.415, 0.15, 1.28, 0.22, true},
};

inline constexpr GroupSpec kNangateOAI21X2Groups[] = {
    {BindingKind::kPinNet, "A", kNangateOAI21X2PinA, std::size(kNangateOAI21X2PinA)},
    {BindingKind::kPinNet, "B1", kNangateOAI21X2PinB1, std::size(kNangateOAI21X2PinB1)},
    {BindingKind::kPinNet, "B2", kNangateOAI21X2PinB2, std::size(kNangateOAI21X2PinB2)},
    {BindingKind::kPinNet, "ZN", kNangateOAI21X2PinZN, std::size(kNangateOAI21X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOAI21X2Power, std::size(kNangateOAI21X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOAI21X2Ground, std::size(kNangateOAI21X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOAI21X2ObsGroup0, std::size(kNangateOAI21X2ObsGroup0)},
};

inline constexpr RectSpec kNangateOAI21X4PinA[] = {
    {"metal1", 0.43, 0.525, 0.515, 0.7},
};

inline constexpr RectSpec kNangateOAI21X4PinB1[] = {
    {"metal1", 1.15, 0.69, 2.04, 0.76},
    {"metal1", 1.905, 0.56, 2.04, 0.76},
    {"metal1", 1.15, 0.56, 1.285, 0.76},
};

inline constexpr RectSpec kNangateOAI21X4PinB2[] = {
    {"metal1", 2.15, 0.42, 2.275, 0.66},
    {"metal1", 0.91, 0.42, 2.275, 0.49},
    {"metal1", 1.525, 0.42, 1.66, 0.625},
    {"metal1", 0.91, 0.42, 0.98, 0.66},
};

inline constexpr RectSpec kNangateOAI21X4PinZN[] = {
    {"metal1", 0.235, 0.845, 2.41, 0.915},
    {"metal1", 2.34, 0.285, 2.41, 0.915},
    {"metal1", 0.96, 0.285, 2.41, 0.355},
    {"metal1", 1.935, 0.845, 2.005, 1.19},
    {"metal1", 1.175, 0.845, 1.245, 1.19},
    {"metal1", 0.605, 0.845, 0.675, 1.19},
    {"metal1", 0.235, 0.845, 0.305, 1.19},
};

inline constexpr RectSpec kNangateOAI21X4Power[] = {
    {"metal1", 0.0, 1.315, 2.47, 1.485},
    {"metal1", 2.315, 1.04, 2.385, 1.485},
    {"metal1", 1.555, 1.04, 1.625, 1.485},
    {"metal1", 0.795, 1.04, 0.865, 1.485},
    {"metal1", 0.415, 1.04, 0.485, 1.485},
    {"metal1", 0.04, 1.04, 0.11, 1.485},
};

inline constexpr RectSpec kNangateOAI21X4Ground[] = {
    {"metal1", 0.0, -0.085, 2.47, 0.085},
    {"metal1", 0.605, -0.085, 0.675, 0.285},
    {"metal1", 0.225, -0.085, 0.295, 0.285},
};

inline constexpr RectSpec kNangateOAI21X4ObsGroup0[] = {
    {"metal1", 0.045, 0.355, 0.83, 0.425, true},
    {"metal1", 0.76, 0.15, 0.83, 0.425, true},
    {"metal1", 0.42, 0.15, 0.49, 0.425, true},
    {"metal1", 0.045, 0.15, 0.115, 0.425, true},
    {"metal1", 0.76, 0.15, 2.42, 0.22, true},
};

inline constexpr GroupSpec kNangateOAI21X4Groups[] = {
    {BindingKind::kPinNet, "A", kNangateOAI21X4PinA, std::size(kNangateOAI21X4PinA)},
    {BindingKind::kPinNet, "B1", kNangateOAI21X4PinB1, std::size(kNangateOAI21X4PinB1)},
    {BindingKind::kPinNet, "B2", kNangateOAI21X4PinB2, std::size(kNangateOAI21X4PinB2)},
    {BindingKind::kPinNet, "ZN", kNangateOAI21X4PinZN, std::size(kNangateOAI21X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOAI21X4Power, std::size(kNangateOAI21X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOAI21X4Ground, std::size(kNangateOAI21X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOAI21X4ObsGroup0, std::size(kNangateOAI21X4ObsGroup0)},
};

inline constexpr RectSpec kNangateOAI221X1PinA[] = {
    {"metal1", 0.44, 0.525, 0.565, 0.7},
};

inline constexpr RectSpec kNangateOAI221X1PinB1[] = {
    {"metal1", 0.25, 0.525, 0.375, 0.7},
};

inline constexpr RectSpec kNangateOAI221X1PinB2[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateOAI221X1PinC1[] = {
    {"metal1", 0.955, 0.525, 1.08, 0.7},
};

inline constexpr RectSpec kNangateOAI221X1PinC2[] = {
    {"metal1", 0.63, 0.525, 0.74, 0.7},
};

inline constexpr RectSpec kNangateOAI221X1PinZN[] = {
    {"metal1", 0.985, 0.85, 1.055, 1.25},
    {"metal1", 0.425, 0.85, 1.055, 0.92},
    {"metal1", 0.805, 0.4, 0.89, 0.92},
    {"metal1", 0.425, 0.85, 0.495, 1.25},
};

inline constexpr RectSpec kNangateOAI221X1Power[] = {
    {"metal1", 0.0, 1.315, 1.14, 1.485},
    {"metal1", 0.605, 1.04, 0.675, 1.485},
    {"metal1", 0.04, 1.04, 0.11, 1.485},
};

inline constexpr RectSpec kNangateOAI221X1Ground[] = {
    {"metal1", 0.0, -0.085, 1.14, 0.085},
    {"metal1", 0.225, -0.085, 0.295, 0.285},
};

inline constexpr RectSpec kNangateOAI221X1ObsGroup0[] = {
    {"metal1", 0.985, 0.15, 1.055, 0.425, true},
    {"metal1", 0.615, 0.15, 0.685, 0.425, true},
    {"metal1", 0.615, 0.15, 1.055, 0.22, true},
};

inline constexpr RectSpec kNangateOAI221X1ObsGroup1[] = {
    {"metal1", 0.045, 0.355, 0.485, 0.425, true},
    {"metal1", 0.415, 0.15, 0.485, 0.425, true},
    {"metal1", 0.045, 0.15, 0.115, 0.425, true},
};

inline constexpr GroupSpec kNangateOAI221X1Groups[] = {
    {BindingKind::kPinNet, "A", kNangateOAI221X1PinA, std::size(kNangateOAI221X1PinA)},
    {BindingKind::kPinNet, "B1", kNangateOAI221X1PinB1, std::size(kNangateOAI221X1PinB1)},
    {BindingKind::kPinNet, "B2", kNangateOAI221X1PinB2, std::size(kNangateOAI221X1PinB2)},
    {BindingKind::kPinNet, "C1", kNangateOAI221X1PinC1, std::size(kNangateOAI221X1PinC1)},
    {BindingKind::kPinNet, "C2", kNangateOAI221X1PinC2, std::size(kNangateOAI221X1PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateOAI221X1PinZN, std::size(kNangateOAI221X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOAI221X1Power, std::size(kNangateOAI221X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOAI221X1Ground, std::size(kNangateOAI221X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOAI221X1ObsGroup0, std::size(kNangateOAI221X1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateOAI221X1ObsGroup1, std::size(kNangateOAI221X1ObsGroup1)},
};

inline constexpr RectSpec kNangateOAI221X2PinA[] = {
    {"metal1", 0.955, 0.9, 2.03, 0.97},
    {"metal1", 1.93, 0.525, 2.03, 0.97},
    {"metal1", 0.955, 0.525, 1.025, 0.97},
};

inline constexpr RectSpec kNangateOAI221X2PinB1[] = {
    {"metal1", 1.155, 0.765, 1.84, 0.835},
    {"metal1", 1.715, 0.525, 1.84, 0.835},
    {"metal1", 1.155, 0.525, 1.225, 0.835},
};

inline constexpr RectSpec kNangateOAI221X2PinB2[] = {
    {"metal1", 1.38, 0.525, 1.48, 0.7},
};

inline constexpr RectSpec kNangateOAI221X2PinC1[] = {
    {"metal1", 0.44, 0.525, 0.525, 0.7},
};

inline constexpr RectSpec kNangateOAI221X2PinC2[] = {
    {"metal1", 0.195, 0.77, 0.89, 0.84},
    {"metal1", 0.76, 0.525, 0.89, 0.84},
    {"metal1", 0.195, 0.525, 0.265, 0.84},
};

inline constexpr RectSpec kNangateOAI221X2PinZN[] = {
    {"metal1", 1.755, 1.035, 1.89, 1.245},
    {"metal1", 0.06, 1.035, 1.89, 1.105},
    {"metal1", 0.995, 1.035, 1.13, 1.245},
    {"metal1", 0.06, 0.39, 0.75, 0.46},
    {"metal1", 0.425, 1.035, 0.56, 1.245},
    {"metal1", 0.06, 0.39, 0.13, 1.105},
};

inline constexpr RectSpec kNangateOAI221X2Power[] = {
    {"metal1", 0.0, 1.315, 2.09, 1.485},
    {"metal1", 1.975, 1.065, 2.045, 1.485},
    {"metal1", 1.405, 1.17, 1.475, 1.485},
    {"metal1", 0.835, 1.17, 0.905, 1.485},
    {"metal1", 0.085, 1.17, 0.155, 1.485},
};

inline constexpr RectSpec kNangateOAI221X2Ground[] = {
    {"metal1", 0.0, -0.085, 2.09, 0.085},
    {"metal1", 1.565, -0.085, 1.7, 0.19},
    {"metal1", 1.185, -0.085, 1.32, 0.19},
};

inline constexpr RectSpec kNangateOAI221X2ObsGroup0[] = {
    {"metal1", 1.975, 0.15, 2.045, 0.425, true},
    {"metal1", 0.05, 0.255, 2.045, 0.325, true},
};

inline constexpr RectSpec kNangateOAI221X2ObsGroup1[] = {
    {"metal1", 1.0, 0.39, 1.89, 0.46, true},
};

inline constexpr GroupSpec kNangateOAI221X2Groups[] = {
    {BindingKind::kPinNet, "A", kNangateOAI221X2PinA, std::size(kNangateOAI221X2PinA)},
    {BindingKind::kPinNet, "B1", kNangateOAI221X2PinB1, std::size(kNangateOAI221X2PinB1)},
    {BindingKind::kPinNet, "B2", kNangateOAI221X2PinB2, std::size(kNangateOAI221X2PinB2)},
    {BindingKind::kPinNet, "C1", kNangateOAI221X2PinC1, std::size(kNangateOAI221X2PinC1)},
    {BindingKind::kPinNet, "C2", kNangateOAI221X2PinC2, std::size(kNangateOAI221X2PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateOAI221X2PinZN, std::size(kNangateOAI221X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOAI221X2Power, std::size(kNangateOAI221X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOAI221X2Ground, std::size(kNangateOAI221X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOAI221X2ObsGroup0, std::size(kNangateOAI221X2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateOAI221X2ObsGroup1, std::size(kNangateOAI221X2ObsGroup1)},
};

inline constexpr RectSpec kNangateOAI221X4PinA[] = {
    {"metal1", 0.585, 0.525, 0.7, 0.7},
};

inline constexpr RectSpec kNangateOAI221X4PinB1[] = {
    {"metal1", 0.775, 0.525, 0.9, 0.7},
};

inline constexpr RectSpec kNangateOAI221X4PinB2[] = {
    {"metal1", 1.01, 0.525, 1.155, 0.7},
};

inline constexpr RectSpec kNangateOAI221X4PinC1[] = {
    {"metal1", 0.06, 0.525, 0.245, 0.7},
};

inline constexpr RectSpec kNangateOAI221X4PinC2[] = {
    {"metal1", 0.395, 0.525, 0.51, 0.7},
};

inline constexpr RectSpec kNangateOAI221X4PinZN[] = {
    {"metal1", 2.165, 0.185, 2.235, 1.25},
    {"metal1", 1.795, 0.7, 2.235, 0.84},
    {"metal1", 1.795, 0.185, 1.865, 1.25},
};

inline constexpr RectSpec kNangateOAI221X4Power[] = {
    {"metal1", 0.0, 1.315, 2.47, 1.485},
    {"metal1", 2.355, 0.975, 2.425, 1.485},
    {"metal1", 1.975, 0.975, 2.045, 1.485},
    {"metal1", 1.595, 0.975, 1.665, 1.485},
    {"metal1", 1.19, 1.04, 1.26, 1.485},
    {"metal1", 0.47, 1.04, 0.54, 1.485},
};

inline constexpr RectSpec kNangateOAI221X4Ground[] = {
    {"metal1", 0.0, -0.085, 2.47, 0.085},
    {"metal1", 2.355, -0.085, 2.425, 0.46},
    {"metal1", 1.975, -0.085, 2.045, 0.46},
    {"metal1", 1.595, -0.085, 1.665, 0.335},
    {"metal1", 1.19, -0.085, 1.26, 0.2},
    {"metal1", 0.82, -0.085, 0.955, 0.16},
};

inline constexpr RectSpec kNangateOAI221X4ObsGroup0[] = {
    {"metal1", 1.415, 0.185, 1.485, 1.25, true},
    {"metal1", 1.415, 0.525, 1.73, 0.66, true},
};

inline constexpr RectSpec kNangateOAI221X4ObsGroup1[] = {
    {"metal1", 0.66, 0.775, 0.73, 1.12, true},
    {"metal1", 0.1, 0.775, 0.17, 1.12, true},
    {"metal1", 0.1, 0.775, 1.35, 0.845, true},
    {"metal1", 1.28, 0.39, 1.35, 0.845, true},
    {"metal1", 0.29, 0.39, 1.35, 0.46, true},
    {"metal1", 0.29, 0.285, 0.36, 0.46, true},
};

inline constexpr RectSpec kNangateOAI221X4ObsGroup2[] = {
    {"metal1", 0.67, 0.255, 1.11, 0.325, true},
    {"metal1", 0.67, 0.15, 0.74, 0.325, true},
};

inline constexpr RectSpec kNangateOAI221X4ObsGroup3[] = {
    {"metal1", 0.47, 0.15, 0.54, 0.285, true},
    {"metal1", 0.1, 0.15, 0.17, 0.285, true},
    {"metal1", 0.1, 0.15, 0.54, 0.22, true},
};

inline constexpr GroupSpec kNangateOAI221X4Groups[] = {
    {BindingKind::kPinNet, "A", kNangateOAI221X4PinA, std::size(kNangateOAI221X4PinA)},
    {BindingKind::kPinNet, "B1", kNangateOAI221X4PinB1, std::size(kNangateOAI221X4PinB1)},
    {BindingKind::kPinNet, "B2", kNangateOAI221X4PinB2, std::size(kNangateOAI221X4PinB2)},
    {BindingKind::kPinNet, "C1", kNangateOAI221X4PinC1, std::size(kNangateOAI221X4PinC1)},
    {BindingKind::kPinNet, "C2", kNangateOAI221X4PinC2, std::size(kNangateOAI221X4PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateOAI221X4PinZN, std::size(kNangateOAI221X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOAI221X4Power, std::size(kNangateOAI221X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOAI221X4Ground, std::size(kNangateOAI221X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOAI221X4ObsGroup0, std::size(kNangateOAI221X4ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateOAI221X4ObsGroup1, std::size(kNangateOAI221X4ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateOAI221X4ObsGroup2, std::size(kNangateOAI221X4ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateOAI221X4ObsGroup3, std::size(kNangateOAI221X4ObsGroup3)},
};

inline constexpr RectSpec kNangateOAI222X1PinA1[] = {
    {"metal1", 1.34, 0.525, 1.46, 0.7},
};

inline constexpr RectSpec kNangateOAI222X1PinA2[] = {
    {"metal1", 1.01, 0.525, 1.115, 0.7},
};

inline constexpr RectSpec kNangateOAI222X1PinB1[] = {
    {"metal1", 0.63, 0.525, 0.755, 0.7},
};

inline constexpr RectSpec kNangateOAI222X1PinB2[] = {
    {"metal1", 0.82, 0.525, 0.945, 0.7},
};

inline constexpr RectSpec kNangateOAI222X1PinC1[] = {
    {"metal1", 0.35, 0.525, 0.51, 0.7},
};

inline constexpr RectSpec kNangateOAI222X1PinC2[] = {
    {"metal1", 0.06, 0.525, 0.2, 0.7},
};

inline constexpr RectSpec kNangateOAI222X1PinZN[] = {
    {"metal1", 1.36, 0.795, 1.43, 1.14},
    {"metal1", 0.52, 0.795, 1.43, 0.865},
    {"metal1", 1.18, 0.4, 1.27, 0.865},
    {"metal1", 0.52, 0.795, 0.59, 1.14},
};

inline constexpr RectSpec kNangateOAI222X1Power[] = {
    {"metal1", 0.0, 1.315, 1.52, 1.485},
    {"metal1", 0.98, 1.04, 1.05, 1.485},
    {"metal1", 0.05, 1.04, 0.12, 1.485},
};

inline constexpr RectSpec kNangateOAI222X1Ground[] = {
    {"metal1", 0.0, -0.085, 1.52, 0.085},
    {"metal1", 0.395, -0.085, 0.53, 0.19},
    {"metal1", 0.05, -0.085, 0.12, 0.425},
};

inline constexpr RectSpec kNangateOAI222X1ObsGroup0[] = {
    {"metal1", 0.575, 0.39, 1.05, 0.46, true},
    {"metal1", 0.98, 0.15, 1.05, 0.46, true},
    {"metal1", 1.36, 0.15, 1.43, 0.425, true},
    {"metal1", 0.98, 0.265, 1.43, 0.335, true},
};

inline constexpr RectSpec kNangateOAI222X1ObsGroup1[] = {
    {"metal1", 0.245, 0.15, 0.315, 0.425, true},
    {"metal1", 0.245, 0.255, 0.86, 0.325, true},
    {"metal1", 0.79, 0.15, 0.86, 0.325, true},
};

inline constexpr GroupSpec kNangateOAI222X1Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateOAI222X1PinA1, std::size(kNangateOAI222X1PinA1)},
    {BindingKind::kPinNet, "A2", kNangateOAI222X1PinA2, std::size(kNangateOAI222X1PinA2)},
    {BindingKind::kPinNet, "B1", kNangateOAI222X1PinB1, std::size(kNangateOAI222X1PinB1)},
    {BindingKind::kPinNet, "B2", kNangateOAI222X1PinB2, std::size(kNangateOAI222X1PinB2)},
    {BindingKind::kPinNet, "C1", kNangateOAI222X1PinC1, std::size(kNangateOAI222X1PinC1)},
    {BindingKind::kPinNet, "C2", kNangateOAI222X1PinC2, std::size(kNangateOAI222X1PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateOAI222X1PinZN, std::size(kNangateOAI222X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOAI222X1Power, std::size(kNangateOAI222X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOAI222X1Ground, std::size(kNangateOAI222X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOAI222X1ObsGroup0, std::size(kNangateOAI222X1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateOAI222X1ObsGroup1, std::size(kNangateOAI222X1ObsGroup1)},
};

inline constexpr RectSpec kNangateOAI222X2PinA1[] = {
    {"metal1", 1.85, 0.725, 2.465, 0.795},
    {"metal1", 2.34, 0.525, 2.465, 0.795},
    {"metal1", 1.85, 0.525, 1.92, 0.795},
};

inline constexpr RectSpec kNangateOAI222X2PinA2[] = {
    {"metal1", 2.15, 0.42, 2.22, 0.66},
};

inline constexpr RectSpec kNangateOAI222X2PinB1[] = {
    {"metal1", 0.955, 0.77, 1.65, 0.84},
    {"metal1", 1.525, 0.525, 1.65, 0.84},
    {"metal1", 0.955, 0.525, 1.025, 0.84},
};

inline constexpr RectSpec kNangateOAI222X2PinB2[] = {
    {"metal1", 1.2, 0.525, 1.29, 0.7},
};

inline constexpr RectSpec kNangateOAI222X2PinC1[] = {
    {"metal1", 0.195, 0.77, 0.83, 0.84},
    {"metal1", 0.76, 0.525, 0.83, 0.84},
    {"metal1", 0.195, 0.525, 0.32, 0.84},
};

inline constexpr RectSpec kNangateOAI222X2PinC2[] = {
    {"metal1", 0.44, 0.525, 0.53, 0.7},
};

inline constexpr RectSpec kNangateOAI222X2PinZN[] = {
    {"metal1", 2.53, 0.285, 2.6, 1.25},
    {"metal1", 0.09, 0.905, 2.6, 0.975},
    {"metal1", 1.925, 0.285, 2.6, 0.355},
    {"metal1", 1.605, 0.905, 1.675, 1.25},
    {"metal1", 0.84, 0.905, 0.91, 1.25},
    {"metal1", 0.09, 0.905, 0.16, 1.25},
};

inline constexpr RectSpec kNangateOAI222X2Power[] = {
    {"metal1", 0.0, 1.315, 2.66, 1.485},
    {"metal1", 2.14, 1.04, 2.21, 1.485},
    {"metal1", 1.22, 1.04, 1.29, 1.485},
    {"metal1", 0.46, 1.04, 0.53, 1.485},
};

inline constexpr RectSpec kNangateOAI222X2Ground[] = {
    {"metal1", 0.0, -0.085, 2.66, 0.085},
    {"metal1", 0.65, -0.085, 0.72, 0.285},
    {"metal1", 0.27, -0.085, 0.34, 0.285},
};

inline constexpr RectSpec kNangateOAI222X2ObsGroup0[] = {
    {"metal1", 1.005, 0.355, 1.84, 0.425, true},
    {"metal1", 1.77, 0.15, 1.84, 0.425, true},
    {"metal1", 1.77, 0.15, 2.625, 0.22, true},
};

inline constexpr RectSpec kNangateOAI222X2ObsGroup1[] = {
    {"metal1", 0.09, 0.355, 0.91, 0.425, true},
    {"metal1", 0.84, 0.15, 0.91, 0.425, true},
    {"metal1", 0.465, 0.15, 0.535, 0.425, true},
    {"metal1", 0.09, 0.15, 0.16, 0.425, true},
    {"metal1", 0.84, 0.15, 1.705, 0.22, true},
};

inline constexpr GroupSpec kNangateOAI222X2Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateOAI222X2PinA1, std::size(kNangateOAI222X2PinA1)},
    {BindingKind::kPinNet, "A2", kNangateOAI222X2PinA2, std::size(kNangateOAI222X2PinA2)},
    {BindingKind::kPinNet, "B1", kNangateOAI222X2PinB1, std::size(kNangateOAI222X2PinB1)},
    {BindingKind::kPinNet, "B2", kNangateOAI222X2PinB2, std::size(kNangateOAI222X2PinB2)},
    {BindingKind::kPinNet, "C1", kNangateOAI222X2PinC1, std::size(kNangateOAI222X2PinC1)},
    {BindingKind::kPinNet, "C2", kNangateOAI222X2PinC2, std::size(kNangateOAI222X2PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateOAI222X2PinZN, std::size(kNangateOAI222X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOAI222X2Power, std::size(kNangateOAI222X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOAI222X2Ground, std::size(kNangateOAI222X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOAI222X2ObsGroup0, std::size(kNangateOAI222X2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateOAI222X2ObsGroup1, std::size(kNangateOAI222X2ObsGroup1)},
};

inline constexpr RectSpec kNangateOAI222X4PinA1[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateOAI222X4PinA2[] = {
    {"metal1", 0.25, 0.525, 0.38, 0.7},
};

inline constexpr RectSpec kNangateOAI222X4PinB1[] = {
    {"metal1", 0.765, 0.56, 0.9, 0.7},
};

inline constexpr RectSpec kNangateOAI222X4PinB2[] = {
    {"metal1", 0.495, 0.56, 0.7, 0.7},
};

inline constexpr RectSpec kNangateOAI222X4PinC1[] = {
    {"metal1", 0.995, 0.56, 1.13, 0.7},
};

inline constexpr RectSpec kNangateOAI222X4PinC2[] = {
    {"metal1", 1.195, 0.56, 1.33, 0.7},
};

inline constexpr RectSpec kNangateOAI222X4PinZN[] = {
    {"metal1", 2.29, 0.15, 2.36, 1.25},
    {"metal1", 1.915, 0.56, 2.36, 0.7},
    {"metal1", 1.915, 0.15, 1.985, 1.25},
};

inline constexpr RectSpec kNangateOAI222X4Power[] = {
    {"metal1", 0.0, 1.315, 2.66, 1.485},
    {"metal1", 2.475, 0.975, 2.545, 1.485},
    {"metal1", 2.095, 0.975, 2.165, 1.485},
    {"metal1", 1.715, 0.975, 1.785, 1.485},
    {"metal1", 1.335, 1.04, 1.405, 1.485},
    {"metal1", 0.415, 1.03, 0.485, 1.485},
};

inline constexpr RectSpec kNangateOAI222X4Ground[] = {
    {"metal1", 0.0, -0.085, 2.66, 0.085},
    {"metal1", 2.475, -0.085, 2.545, 0.425},
    {"metal1", 2.095, -0.085, 2.165, 0.425},
    {"metal1", 1.715, -0.085, 1.785, 0.335},
    {"metal1", 1.335, -0.085, 1.405, 0.22},
    {"metal1", 0.965, -0.085, 1.035, 0.22},
};

inline constexpr RectSpec kNangateOAI222X4ObsGroup0[] = {
    {"metal1", 1.535, 0.15, 1.605, 1.16, true},
    {"metal1", 1.535, 0.525, 1.85, 0.66, true},
};

inline constexpr RectSpec kNangateOAI222X4ObsGroup1[] = {
    {"metal1", 0.88, 0.785, 0.95, 1.075, true},
    {"metal1", 0.045, 0.785, 0.115, 1.075, true},
    {"metal1", 0.045, 0.785, 1.465, 0.855, true},
    {"metal1", 1.395, 0.285, 1.465, 0.855, true},
    {"metal1", 0.2, 0.285, 1.465, 0.355, true},
};

inline constexpr RectSpec kNangateOAI222X4ObsGroup2[] = {
    {"metal1", 0.045, 0.15, 0.115, 0.425, true},
    {"metal1", 0.045, 0.15, 0.9, 0.22, true},
};

inline constexpr RectSpec kNangateOAI222X4ObsGroup3[] = {
    {"metal1", 0.58, 0.42, 1.25, 0.49, true},
};

inline constexpr GroupSpec kNangateOAI222X4Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateOAI222X4PinA1, std::size(kNangateOAI222X4PinA1)},
    {BindingKind::kPinNet, "A2", kNangateOAI222X4PinA2, std::size(kNangateOAI222X4PinA2)},
    {BindingKind::kPinNet, "B1", kNangateOAI222X4PinB1, std::size(kNangateOAI222X4PinB1)},
    {BindingKind::kPinNet, "B2", kNangateOAI222X4PinB2, std::size(kNangateOAI222X4PinB2)},
    {BindingKind::kPinNet, "C1", kNangateOAI222X4PinC1, std::size(kNangateOAI222X4PinC1)},
    {BindingKind::kPinNet, "C2", kNangateOAI222X4PinC2, std::size(kNangateOAI222X4PinC2)},
    {BindingKind::kPinNet, "ZN", kNangateOAI222X4PinZN, std::size(kNangateOAI222X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOAI222X4Power, std::size(kNangateOAI222X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOAI222X4Ground, std::size(kNangateOAI222X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOAI222X4ObsGroup0, std::size(kNangateOAI222X4ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateOAI222X4ObsGroup1, std::size(kNangateOAI222X4ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateOAI222X4ObsGroup2, std::size(kNangateOAI222X4ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateOAI222X4ObsGroup3, std::size(kNangateOAI222X4ObsGroup3)},
};

inline constexpr RectSpec kNangateOAI22X1PinA1[] = {
    {"metal1", 0.575, 0.525, 0.7, 0.7},
};

inline constexpr RectSpec kNangateOAI22X1PinA2[] = {
    {"metal1", 0.765, 0.525, 0.89, 0.7},
};

inline constexpr RectSpec kNangateOAI22X1PinB1[] = {
    {"metal1", 0.25, 0.525, 0.375, 0.7},
};

inline constexpr RectSpec kNangateOAI22X1PinB2[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateOAI22X1PinZN[] = {
    {"metal1", 0.44, 0.39, 0.725, 0.46},
    {"metal1", 0.44, 0.39, 0.51, 1.05},
};

inline constexpr RectSpec kNangateOAI22X1Power[] = {
    {"metal1", 0.0, 1.315, 0.95, 1.485},
    {"metal1", 0.81, 0.975, 0.88, 1.485},
    {"metal1", 0.055, 0.975, 0.125, 1.485},
};

inline constexpr RectSpec kNangateOAI22X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.95, 0.085},
    {"metal1", 0.21, -0.085, 0.345, 0.16},
};

inline constexpr RectSpec kNangateOAI22X1ObsGroup0[] = {
    {"metal1", 0.81, 0.185, 0.88, 0.46, true},
    {"metal1", 0.06, 0.185, 0.13, 0.46, true},
    {"metal1", 0.06, 0.245, 0.88, 0.315, true},
};

inline constexpr GroupSpec kNangateOAI22X1Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateOAI22X1PinA1, std::size(kNangateOAI22X1PinA1)},
    {BindingKind::kPinNet, "A2", kNangateOAI22X1PinA2, std::size(kNangateOAI22X1PinA2)},
    {BindingKind::kPinNet, "B1", kNangateOAI22X1PinB1, std::size(kNangateOAI22X1PinB1)},
    {BindingKind::kPinNet, "B2", kNangateOAI22X1PinB2, std::size(kNangateOAI22X1PinB2)},
    {BindingKind::kPinNet, "ZN", kNangateOAI22X1PinZN, std::size(kNangateOAI22X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOAI22X1Power, std::size(kNangateOAI22X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOAI22X1Ground, std::size(kNangateOAI22X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOAI22X1ObsGroup0, std::size(kNangateOAI22X1ObsGroup0)},
};

inline constexpr RectSpec kNangateOAI22X2PinA1[] = {
    {"metal1", 1.185, 0.525, 1.27, 0.7},
};

inline constexpr RectSpec kNangateOAI22X2PinA2[] = {
    {"metal1", 0.82, 0.765, 1.515, 0.835},
    {"metal1", 1.445, 0.525, 1.515, 0.835},
    {"metal1", 0.82, 0.525, 0.95, 0.835},
};

inline constexpr RectSpec kNangateOAI22X2PinB1[] = {
    {"metal1", 0.425, 0.525, 0.525, 0.7},
};

inline constexpr RectSpec kNangateOAI22X2PinB2[] = {
    {"metal1", 0.06, 0.765, 0.75, 0.835},
    {"metal1", 0.68, 0.525, 0.75, 0.835},
    {"metal1", 0.06, 0.525, 0.185, 0.835},
};

inline constexpr RectSpec kNangateOAI22X2PinZN[] = {
    {"metal1", 0.425, 0.9, 1.65, 0.97},
    {"metal1", 1.58, 0.39, 1.65, 0.97},
    {"metal1", 0.96, 0.39, 1.65, 0.46},
    {"metal1", 1.185, 0.9, 1.255, 1.25},
    {"metal1", 0.425, 0.9, 0.495, 1.25},
};

inline constexpr RectSpec kNangateOAI22X2Power[] = {
    {"metal1", 0.0, 1.315, 1.71, 1.485},
    {"metal1", 1.555, 1.035, 1.625, 1.485},
    {"metal1", 0.795, 1.035, 0.865, 1.485},
    {"metal1", 0.04, 1.035, 0.11, 1.485},
};

inline constexpr RectSpec kNangateOAI22X2Ground[] = {
    {"metal1", 0.0, -0.085, 1.71, 0.085},
    {"metal1", 0.605, -0.085, 0.675, 0.285},
    {"metal1", 0.225, -0.085, 0.295, 0.285},
};

inline constexpr RectSpec kNangateOAI22X2ObsGroup0[] = {
    {"metal1", 0.045, 0.355, 0.865, 0.425, true},
    {"metal1", 0.795, 0.15, 0.865, 0.425, true},
    {"metal1", 0.415, 0.15, 0.485, 0.425, true},
    {"metal1", 0.045, 0.15, 0.115, 0.425, true},
    {"metal1", 0.795, 0.15, 1.66, 0.22, true},
};

inline constexpr GroupSpec kNangateOAI22X2Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateOAI22X2PinA1, std::size(kNangateOAI22X2PinA1)},
    {BindingKind::kPinNet, "A2", kNangateOAI22X2PinA2, std::size(kNangateOAI22X2PinA2)},
    {BindingKind::kPinNet, "B1", kNangateOAI22X2PinB1, std::size(kNangateOAI22X2PinB1)},
    {BindingKind::kPinNet, "B2", kNangateOAI22X2PinB2, std::size(kNangateOAI22X2PinB2)},
    {BindingKind::kPinNet, "ZN", kNangateOAI22X2PinZN, std::size(kNangateOAI22X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOAI22X2Power, std::size(kNangateOAI22X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOAI22X2Ground, std::size(kNangateOAI22X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOAI22X2ObsGroup0, std::size(kNangateOAI22X2ObsGroup0)},
};

inline constexpr RectSpec kNangateOAI22X4PinA1[] = {
    {"metal1", 1.91, 0.725, 2.805, 0.795},
    {"metal1", 2.67, 0.56, 2.805, 0.795},
    {"metal1", 1.91, 0.56, 2.045, 0.795},
};

inline constexpr RectSpec kNangateOAI22X4PinA2[] = {
    {"metal1", 2.91, 0.425, 3.035, 0.7},
    {"metal1", 1.645, 0.425, 3.035, 0.495},
    {"metal1", 2.32, 0.425, 2.39, 0.66},
    {"metal1", 1.645, 0.425, 1.715, 0.66},
};

inline constexpr RectSpec kNangateOAI22X4PinB1[] = {
    {"metal1", 0.385, 0.725, 1.28, 0.795},
    {"metal1", 1.145, 0.56, 1.28, 0.795},
    {"metal1", 0.385, 0.56, 0.52, 0.795},
};

inline constexpr RectSpec kNangateOAI22X4PinB2[] = {
    {"metal1", 1.39, 0.425, 1.52, 0.7},
    {"metal1", 0.15, 0.425, 1.52, 0.495},
    {"metal1", 0.795, 0.425, 0.865, 0.66},
    {"metal1", 0.15, 0.425, 0.22, 0.66},
};

inline constexpr RectSpec kNangateOAI22X4PinZN[] = {
    {"metal1", 0.425, 0.865, 3.17, 0.935},
    {"metal1", 3.1, 0.29, 3.17, 0.935},
    {"metal1", 1.72, 0.29, 3.17, 0.36},
    {"metal1", 2.695, 0.865, 2.765, 1.21},
    {"metal1", 1.935, 0.865, 2.005, 1.21},
    {"metal1", 1.175, 0.865, 1.245, 1.21},
    {"metal1", 0.425, 0.865, 0.495, 1.21},
};

inline constexpr RectSpec kNangateOAI22X4Power[] = {
    {"metal1", 0.0, 1.315, 3.23, 1.485},
    {"metal1", 3.075, 1.04, 3.145, 1.485},
    {"metal1", 2.315, 1.04, 2.385, 1.485},
    {"metal1", 1.555, 1.04, 1.625, 1.485},
    {"metal1", 0.795, 1.04, 0.865, 1.485},
    {"metal1", 0.04, 1.04, 0.11, 1.485},
};

inline constexpr RectSpec kNangateOAI22X4Ground[] = {
    {"metal1", 0.0, -0.085, 3.23, 0.085},
    {"metal1", 1.365, -0.085, 1.435, 0.195},
    {"metal1", 0.985, -0.085, 1.055, 0.195},
    {"metal1", 0.605, -0.085, 0.675, 0.195},
    {"metal1", 0.225, -0.085, 0.295, 0.195},
};

inline constexpr RectSpec kNangateOAI22X4ObsGroup0[] = {
    {"metal1", 0.045, 0.26, 1.595, 0.33, true},
    {"metal1", 1.525, 0.15, 1.595, 0.33, true},
    {"metal1", 0.045, 0.185, 0.115, 0.33, true},
    {"metal1", 1.525, 0.15, 3.18, 0.22, true},
};

inline constexpr GroupSpec kNangateOAI22X4Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateOAI22X4PinA1, std::size(kNangateOAI22X4PinA1)},
    {BindingKind::kPinNet, "A2", kNangateOAI22X4PinA2, std::size(kNangateOAI22X4PinA2)},
    {BindingKind::kPinNet, "B1", kNangateOAI22X4PinB1, std::size(kNangateOAI22X4PinB1)},
    {BindingKind::kPinNet, "B2", kNangateOAI22X4PinB2, std::size(kNangateOAI22X4PinB2)},
    {BindingKind::kPinNet, "ZN", kNangateOAI22X4PinZN, std::size(kNangateOAI22X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOAI22X4Power, std::size(kNangateOAI22X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOAI22X4Ground, std::size(kNangateOAI22X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOAI22X4ObsGroup0, std::size(kNangateOAI22X4ObsGroup0)},
};

inline constexpr RectSpec kNangateOAI33X1PinA1[] = {
    {"metal1", 0.765, 0.525, 0.89, 0.7},
};

inline constexpr RectSpec kNangateOAI33X1PinA2[] = {
    {"metal1", 0.955, 0.525, 1.08, 0.7},
};

inline constexpr RectSpec kNangateOAI33X1PinA3[] = {
    {"metal1", 1.145, 0.525, 1.27, 0.7},
};

inline constexpr RectSpec kNangateOAI33X1PinB1[] = {
    {"metal1", 0.44, 0.525, 0.565, 0.7},
};

inline constexpr RectSpec kNangateOAI33X1PinB2[] = {
    {"metal1", 0.25, 0.525, 0.375, 0.7},
};

inline constexpr RectSpec kNangateOAI33X1PinB3[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateOAI33X1PinZN[] = {
    {"metal1", 0.63, 0.365, 1.26, 0.435},
    {"metal1", 1.19, 0.15, 1.26, 0.435},
    {"metal1", 0.63, 0.365, 0.7, 1.0},
};

inline constexpr RectSpec kNangateOAI33X1Power[] = {
    {"metal1", 0.0, 1.315, 1.33, 1.485},
    {"metal1", 1.19, 0.975, 1.26, 1.485},
    {"metal1", 0.055, 0.975, 0.125, 1.485},
};

inline constexpr RectSpec kNangateOAI33X1Ground[] = {
    {"metal1", 0.0, -0.085, 1.33, 0.085},
    {"metal1", 0.4, -0.085, 0.535, 0.16},
    {"metal1", 0.055, -0.085, 0.125, 0.335},
};

inline constexpr RectSpec kNangateOAI33X1ObsGroup0[] = {
    {"metal1", 0.215, 0.225, 1.105, 0.295, true},
};

inline constexpr GroupSpec kNangateOAI33X1Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateOAI33X1PinA1, std::size(kNangateOAI33X1PinA1)},
    {BindingKind::kPinNet, "A2", kNangateOAI33X1PinA2, std::size(kNangateOAI33X1PinA2)},
    {BindingKind::kPinNet, "A3", kNangateOAI33X1PinA3, std::size(kNangateOAI33X1PinA3)},
    {BindingKind::kPinNet, "B1", kNangateOAI33X1PinB1, std::size(kNangateOAI33X1PinB1)},
    {BindingKind::kPinNet, "B2", kNangateOAI33X1PinB2, std::size(kNangateOAI33X1PinB2)},
    {BindingKind::kPinNet, "B3", kNangateOAI33X1PinB3, std::size(kNangateOAI33X1PinB3)},
    {BindingKind::kPinNet, "ZN", kNangateOAI33X1PinZN, std::size(kNangateOAI33X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOAI33X1Power, std::size(kNangateOAI33X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOAI33X1Ground, std::size(kNangateOAI33X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOAI33X1ObsGroup0, std::size(kNangateOAI33X1ObsGroup0)},
};

inline constexpr RectSpec kNangateOR2X1PinA1[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateOR2X1PinA2[] = {
    {"metal1", 0.25, 0.525, 0.38, 0.7},
};

inline constexpr RectSpec kNangateOR2X1PinZN[] = {
    {"metal1", 0.61, 0.15, 0.7, 1.24},
};

inline constexpr RectSpec kNangateOR2X1Power[] = {
    {"metal1", 0.0, 1.315, 0.76, 1.485},
    {"metal1", 0.415, 0.965, 0.485, 1.485},
};

inline constexpr RectSpec kNangateOR2X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.76, 0.085},
    {"metal1", 0.415, -0.085, 0.485, 0.285},
    {"metal1", 0.04, -0.085, 0.11, 0.285},
};

inline constexpr RectSpec kNangateOR2X1ObsGroup0[] = {
    {"metal1", 0.045, 0.83, 0.115, 1.24, true},
    {"metal1", 0.045, 0.83, 0.54, 0.9, true},
    {"metal1", 0.47, 0.35, 0.54, 0.9, true},
    {"metal1", 0.235, 0.35, 0.54, 0.42, true},
    {"metal1", 0.235, 0.15, 0.305, 0.42, true},
};

inline constexpr GroupSpec kNangateOR2X1Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateOR2X1PinA1, std::size(kNangateOR2X1PinA1)},
    {BindingKind::kPinNet, "A2", kNangateOR2X1PinA2, std::size(kNangateOR2X1PinA2)},
    {BindingKind::kPinNet, "ZN", kNangateOR2X1PinZN, std::size(kNangateOR2X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOR2X1Power, std::size(kNangateOR2X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOR2X1Ground, std::size(kNangateOR2X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOR2X1ObsGroup0, std::size(kNangateOR2X1ObsGroup0)},
};

inline constexpr RectSpec kNangateOR2X2PinA1[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateOR2X2PinA2[] = {
    {"metal1", 0.25, 0.525, 0.38, 0.7},
};

inline constexpr RectSpec kNangateOR2X2PinZN[] = {
    {"metal1", 0.615, 0.15, 0.7, 1.25},
};

inline constexpr RectSpec kNangateOR2X2Power[] = {
    {"metal1", 0.0, 1.315, 0.95, 1.485},
    {"metal1", 0.795, 0.975, 0.865, 1.485},
    {"metal1", 0.415, 1.04, 0.485, 1.485},
};

inline constexpr RectSpec kNangateOR2X2Ground[] = {
    {"metal1", 0.0, -0.085, 0.95, 0.085},
    {"metal1", 0.795, -0.085, 0.865, 0.425},
    {"metal1", 0.415, -0.085, 0.485, 0.285},
    {"metal1", 0.04, -0.085, 0.11, 0.425},
};

inline constexpr RectSpec kNangateOR2X2ObsGroup0[] = {
    {"metal1", 0.045, 0.905, 0.115, 1.25, true},
    {"metal1", 0.045, 0.905, 0.545, 0.975, true},
    {"metal1", 0.475, 0.355, 0.545, 0.975, true},
    {"metal1", 0.235, 0.355, 0.545, 0.425, true},
    {"metal1", 0.235, 0.15, 0.305, 0.425, true},
};

inline constexpr GroupSpec kNangateOR2X2Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateOR2X2PinA1, std::size(kNangateOR2X2PinA1)},
    {BindingKind::kPinNet, "A2", kNangateOR2X2PinA2, std::size(kNangateOR2X2PinA2)},
    {BindingKind::kPinNet, "ZN", kNangateOR2X2PinZN, std::size(kNangateOR2X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOR2X2Power, std::size(kNangateOR2X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOR2X2Ground, std::size(kNangateOR2X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOR2X2ObsGroup0, std::size(kNangateOR2X2ObsGroup0)},
};

inline constexpr RectSpec kNangateOR2X4PinA1[] = {
    {"metal1", 0.25, 0.525, 0.38, 0.7},
};

inline constexpr RectSpec kNangateOR2X4PinA2[] = {
    {"metal1", 0.06, 0.765, 0.76, 0.835},
    {"metal1", 0.69, 0.525, 0.76, 0.835},
    {"metal1", 0.06, 0.525, 0.15, 0.835},
};

inline constexpr RectSpec kNangateOR2X4PinZN[] = {
    {"metal1", 1.365, 0.15, 1.435, 1.095},
    {"metal1", 0.995, 0.56, 1.435, 0.7},
    {"metal1", 0.995, 0.15, 1.075, 0.7},
    {"metal1", 0.995, 0.15, 1.065, 1.095},
};

inline constexpr RectSpec kNangateOR2X4Power[] = {
    {"metal1", 0.0, 1.315, 1.71, 1.485},
    {"metal1", 1.555, 1.035, 1.625, 1.485},
    {"metal1", 1.175, 1.035, 1.245, 1.485},
    {"metal1", 0.795, 1.035, 0.865, 1.485},
    {"metal1", 0.04, 1.035, 0.11, 1.485},
};

inline constexpr RectSpec kNangateOR2X4Ground[] = {
    {"metal1", 0.0, -0.085, 1.71, 0.085},
    {"metal1", 1.555, -0.085, 1.625, 0.425},
    {"metal1", 1.175, -0.085, 1.245, 0.425},
    {"metal1", 0.795, -0.085, 0.865, 0.285},
    {"metal1", 0.415, -0.085, 0.485, 0.285},
    {"metal1", 0.04, -0.085, 0.11, 0.425},
};

inline constexpr RectSpec kNangateOR2X4ObsGroup0[] = {
    {"metal1", 0.425, 0.9, 0.495, 1.25, true},
    {"metal1", 0.425, 0.9, 0.925, 0.97, true},
    {"metal1", 0.855, 0.355, 0.925, 0.97, true},
    {"metal1", 0.235, 0.355, 0.925, 0.425, true},
    {"metal1", 0.605, 0.15, 0.675, 0.425, true},
    {"metal1", 0.235, 0.15, 0.305, 0.425, true},
};

inline constexpr GroupSpec kNangateOR2X4Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateOR2X4PinA1, std::size(kNangateOR2X4PinA1)},
    {BindingKind::kPinNet, "A2", kNangateOR2X4PinA2, std::size(kNangateOR2X4PinA2)},
    {BindingKind::kPinNet, "ZN", kNangateOR2X4PinZN, std::size(kNangateOR2X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOR2X4Power, std::size(kNangateOR2X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOR2X4Ground, std::size(kNangateOR2X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOR2X4ObsGroup0, std::size(kNangateOR2X4ObsGroup0)},
};

inline constexpr RectSpec kNangateOR3X1PinA1[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateOR3X1PinA2[] = {
    {"metal1", 0.25, 0.525, 0.375, 0.7},
};

inline constexpr RectSpec kNangateOR3X1PinA3[] = {
    {"metal1", 0.44, 0.525, 0.57, 0.7},
};

inline constexpr RectSpec kNangateOR3X1PinZN[] = {
    {"metal1", 0.8, 0.15, 0.89, 1.24},
};

inline constexpr RectSpec kNangateOR3X1Power[] = {
    {"metal1", 0.0, 1.315, 0.95, 1.485},
    {"metal1", 0.605, 0.965, 0.675, 1.485},
};

inline constexpr RectSpec kNangateOR3X1Ground[] = {
    {"metal1", 0.0, -0.085, 0.95, 0.085},
    {"metal1", 0.605, -0.085, 0.675, 0.285},
    {"metal1", 0.225, -0.085, 0.295, 0.285},
};

inline constexpr RectSpec kNangateOR3X1ObsGroup0[] = {
    {"metal1", 0.045, 0.83, 0.115, 1.24, true},
    {"metal1", 0.045, 0.83, 0.73, 0.9, true},
    {"metal1", 0.66, 0.35, 0.73, 0.9, true},
    {"metal1", 0.045, 0.35, 0.73, 0.42, true},
    {"metal1", 0.415, 0.15, 0.485, 0.42, true},
    {"metal1", 0.045, 0.15, 0.115, 0.42, true},
};

inline constexpr GroupSpec kNangateOR3X1Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateOR3X1PinA1, std::size(kNangateOR3X1PinA1)},
    {BindingKind::kPinNet, "A2", kNangateOR3X1PinA2, std::size(kNangateOR3X1PinA2)},
    {BindingKind::kPinNet, "A3", kNangateOR3X1PinA3, std::size(kNangateOR3X1PinA3)},
    {BindingKind::kPinNet, "ZN", kNangateOR3X1PinZN, std::size(kNangateOR3X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOR3X1Power, std::size(kNangateOR3X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOR3X1Ground, std::size(kNangateOR3X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOR3X1ObsGroup0, std::size(kNangateOR3X1ObsGroup0)},
};

inline constexpr RectSpec kNangateOR3X2PinA1[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateOR3X2PinA2[] = {
    {"metal1", 0.25, 0.525, 0.375, 0.7},
};

inline constexpr RectSpec kNangateOR3X2PinA3[] = {
    {"metal1", 0.44, 0.525, 0.57, 0.7},
};

inline constexpr RectSpec kNangateOR3X2PinZN[] = {
    {"metal1", 0.805, 0.15, 0.89, 1.25},
};

inline constexpr RectSpec kNangateOR3X2Power[] = {
    {"metal1", 0.0, 1.315, 1.14, 1.485},
    {"metal1", 0.985, 0.975, 1.055, 1.485},
    {"metal1", 0.605, 0.975, 0.675, 1.485},
};

inline constexpr RectSpec kNangateOR3X2Ground[] = {
    {"metal1", 0.0, -0.085, 1.14, 0.085},
    {"metal1", 0.985, -0.085, 1.055, 0.425},
    {"metal1", 0.605, -0.085, 0.675, 0.285},
    {"metal1", 0.225, -0.085, 0.295, 0.285},
};

inline constexpr RectSpec kNangateOR3X2ObsGroup0[] = {
    {"metal1", 0.045, 0.84, 0.115, 1.25, true},
    {"metal1", 0.045, 0.84, 0.73, 0.91, true},
    {"metal1", 0.66, 0.39, 0.73, 0.91, true},
    {"metal1", 0.045, 0.39, 0.73, 0.46, true},
    {"metal1", 0.415, 0.15, 0.485, 0.46, true},
    {"metal1", 0.045, 0.15, 0.115, 0.46, true},
};

inline constexpr GroupSpec kNangateOR3X2Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateOR3X2PinA1, std::size(kNangateOR3X2PinA1)},
    {BindingKind::kPinNet, "A2", kNangateOR3X2PinA2, std::size(kNangateOR3X2PinA2)},
    {BindingKind::kPinNet, "A3", kNangateOR3X2PinA3, std::size(kNangateOR3X2PinA3)},
    {BindingKind::kPinNet, "ZN", kNangateOR3X2PinZN, std::size(kNangateOR3X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOR3X2Power, std::size(kNangateOR3X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOR3X2Ground, std::size(kNangateOR3X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOR3X2ObsGroup0, std::size(kNangateOR3X2ObsGroup0)},
};

inline constexpr RectSpec kNangateOR3X4PinA1[] = {
    {"metal1", 0.61, 0.56, 0.745, 0.7},
};

inline constexpr RectSpec kNangateOR3X4PinA2[] = {
    {"metal1", 0.915, 0.42, 0.985, 0.66},
    {"metal1", 0.375, 0.42, 0.985, 0.49},
    {"metal1", 0.375, 0.42, 0.51, 0.66},
};

inline constexpr RectSpec kNangateOR3X4PinA3[] = {
    {"metal1", 0.185, 0.77, 1.2, 0.84},
    {"metal1", 1.13, 0.525, 1.2, 0.84},
    {"metal1", 0.185, 0.7, 0.32, 0.84},
    {"metal1", 0.185, 0.525, 0.255, 0.84},
};

inline constexpr RectSpec kNangateOR3X4PinZN[] = {
    {"metal1", 1.79, 0.26, 1.86, 1.25},
    {"metal1", 1.415, 0.56, 1.86, 0.7},
    {"metal1", 1.415, 0.26, 1.485, 1.25},
};

inline constexpr RectSpec kNangateOR3X4Power[] = {
    {"metal1", 0.0, 1.315, 2.09, 1.485},
    {"metal1", 1.975, 1.035, 2.045, 1.485},
    {"metal1", 1.595, 1.035, 1.665, 1.485},
    {"metal1", 1.21, 1.045, 1.28, 1.485},
    {"metal1", 0.075, 1.035, 0.145, 1.485},
};

inline constexpr RectSpec kNangateOR3X4Ground[] = {
    {"metal1", 0.0, -0.085, 2.09, 0.085},
    {"metal1", 1.975, -0.085, 2.045, 0.335},
    {"metal1", 1.595, -0.085, 1.665, 0.335},
    {"metal1", 1.21, -0.085, 1.28, 0.195},
    {"metal1", 0.83, -0.085, 0.9, 0.195},
    {"metal1", 0.45, -0.085, 0.52, 0.195},
    {"metal1", 0.075, -0.085, 0.145, 0.335},
};

inline constexpr RectSpec kNangateOR3X4ObsGroup0[] = {
    {"metal1", 0.65, 0.91, 0.72, 1.25, true},
    {"metal1", 0.65, 0.91, 1.35, 0.98, true},
    {"metal1", 1.28, 0.26, 1.35, 0.98, true},
    {"metal1", 0.235, 0.26, 1.35, 0.33, true},
};

inline constexpr GroupSpec kNangateOR3X4Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateOR3X4PinA1, std::size(kNangateOR3X4PinA1)},
    {BindingKind::kPinNet, "A2", kNangateOR3X4PinA2, std::size(kNangateOR3X4PinA2)},
    {BindingKind::kPinNet, "A3", kNangateOR3X4PinA3, std::size(kNangateOR3X4PinA3)},
    {BindingKind::kPinNet, "ZN", kNangateOR3X4PinZN, std::size(kNangateOR3X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOR3X4Power, std::size(kNangateOR3X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOR3X4Ground, std::size(kNangateOR3X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOR3X4ObsGroup0, std::size(kNangateOR3X4ObsGroup0)},
};

inline constexpr RectSpec kNangateOR4X1PinA1[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateOR4X1PinA2[] = {
    {"metal1", 0.25, 0.525, 0.375, 0.7},
};

inline constexpr RectSpec kNangateOR4X1PinA3[] = {
    {"metal1", 0.44, 0.525, 0.565, 0.7},
};

inline constexpr RectSpec kNangateOR4X1PinA4[] = {
    {"metal1", 0.63, 0.525, 0.76, 0.7},
};

inline constexpr RectSpec kNangateOR4X1PinZN[] = {
    {"metal1", 0.99, 0.15, 1.08, 1.24},
};

inline constexpr RectSpec kNangateOR4X1Power[] = {
    {"metal1", 0.0, 1.315, 1.14, 1.485},
    {"metal1", 0.795, 0.965, 0.865, 1.485},
};

inline constexpr RectSpec kNangateOR4X1Ground[] = {
    {"metal1", 0.0, -0.085, 1.14, 0.085},
    {"metal1", 0.795, -0.085, 0.865, 0.285},
    {"metal1", 0.415, -0.085, 0.485, 0.285},
    {"metal1", 0.04, -0.085, 0.11, 0.285},
};

inline constexpr RectSpec kNangateOR4X1ObsGroup0[] = {
    {"metal1", 0.045, 0.83, 0.115, 1.24, true},
    {"metal1", 0.045, 0.83, 0.92, 0.9, true},
    {"metal1", 0.85, 0.35, 0.92, 0.9, true},
    {"metal1", 0.235, 0.35, 0.92, 0.42, true},
    {"metal1", 0.605, 0.15, 0.675, 0.42, true},
    {"metal1", 0.235, 0.15, 0.305, 0.42, true},
};

inline constexpr GroupSpec kNangateOR4X1Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateOR4X1PinA1, std::size(kNangateOR4X1PinA1)},
    {BindingKind::kPinNet, "A2", kNangateOR4X1PinA2, std::size(kNangateOR4X1PinA2)},
    {BindingKind::kPinNet, "A3", kNangateOR4X1PinA3, std::size(kNangateOR4X1PinA3)},
    {BindingKind::kPinNet, "A4", kNangateOR4X1PinA4, std::size(kNangateOR4X1PinA4)},
    {BindingKind::kPinNet, "ZN", kNangateOR4X1PinZN, std::size(kNangateOR4X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOR4X1Power, std::size(kNangateOR4X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOR4X1Ground, std::size(kNangateOR4X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOR4X1ObsGroup0, std::size(kNangateOR4X1ObsGroup0)},
};

inline constexpr RectSpec kNangateOR4X2PinA1[] = {
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateOR4X2PinA2[] = {
    {"metal1", 0.25, 0.525, 0.375, 0.7},
};

inline constexpr RectSpec kNangateOR4X2PinA3[] = {
    {"metal1", 0.44, 0.525, 0.565, 0.7},
};

inline constexpr RectSpec kNangateOR4X2PinA4[] = {
    {"metal1", 0.63, 0.525, 0.76, 0.7},
};

inline constexpr RectSpec kNangateOR4X2PinZN[] = {
    {"metal1", 0.995, 0.15, 1.08, 1.25},
};

inline constexpr RectSpec kNangateOR4X2Power[] = {
    {"metal1", 0.0, 1.315, 1.33, 1.485},
    {"metal1", 1.175, 0.975, 1.245, 1.485},
    {"metal1", 0.795, 0.975, 0.865, 1.485},
};

inline constexpr RectSpec kNangateOR4X2Ground[] = {
    {"metal1", 0.0, -0.085, 1.33, 0.085},
    {"metal1", 1.175, -0.085, 1.245, 0.425},
    {"metal1", 0.795, -0.085, 0.865, 0.285},
    {"metal1", 0.415, -0.085, 0.485, 0.285},
    {"metal1", 0.04, -0.085, 0.11, 0.425},
};

inline constexpr RectSpec kNangateOR4X2ObsGroup0[] = {
    {"metal1", 0.045, 0.84, 0.115, 1.25, true},
    {"metal1", 0.045, 0.84, 0.925, 0.91, true},
    {"metal1", 0.855, 0.355, 0.925, 0.91, true},
    {"metal1", 0.235, 0.355, 0.925, 0.425, true},
    {"metal1", 0.605, 0.15, 0.675, 0.425, true},
    {"metal1", 0.235, 0.15, 0.305, 0.425, true},
};

inline constexpr GroupSpec kNangateOR4X2Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateOR4X2PinA1, std::size(kNangateOR4X2PinA1)},
    {BindingKind::kPinNet, "A2", kNangateOR4X2PinA2, std::size(kNangateOR4X2PinA2)},
    {BindingKind::kPinNet, "A3", kNangateOR4X2PinA3, std::size(kNangateOR4X2PinA3)},
    {BindingKind::kPinNet, "A4", kNangateOR4X2PinA4, std::size(kNangateOR4X2PinA4)},
    {BindingKind::kPinNet, "ZN", kNangateOR4X2PinZN, std::size(kNangateOR4X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOR4X2Power, std::size(kNangateOR4X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOR4X2Ground, std::size(kNangateOR4X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOR4X2ObsGroup0, std::size(kNangateOR4X2ObsGroup0)},
};

inline constexpr RectSpec kNangateOR4X4PinA1[] = {
    {"metal1", 0.805, 0.525, 0.89, 0.7},
};

inline constexpr RectSpec kNangateOR4X4PinA2[] = {
    {"metal1", 1.01, 0.39, 1.14, 0.66},
    {"metal1", 0.505, 0.39, 1.14, 0.46},
    {"metal1", 0.505, 0.39, 0.575, 0.66},
};

inline constexpr RectSpec kNangateOR4X4PinA3[] = {
    {"metal1", 0.31, 0.77, 1.33, 0.84},
    {"metal1", 1.26, 0.525, 1.33, 0.84},
    {"metal1", 0.31, 0.525, 0.38, 0.84},
    {"metal1", 0.25, 0.525, 0.38, 0.7},
};

inline constexpr RectSpec kNangateOR4X4PinA4[] = {
    {"metal1", 0.115, 0.905, 1.52, 0.975},
    {"metal1", 1.45, 0.525, 1.52, 0.975},
    {"metal1", 0.115, 0.525, 0.185, 0.975},
    {"metal1", 0.06, 0.525, 0.185, 0.7},
};

inline constexpr RectSpec kNangateOR4X4PinZN[] = {
    {"metal1", 2.13, 0.15, 2.2, 1.25},
    {"metal1", 1.755, 0.56, 2.2, 0.7},
    {"metal1", 1.755, 0.15, 1.825, 1.25},
};

inline constexpr RectSpec kNangateOR4X4Power[] = {
    {"metal1", 0.0, 1.315, 2.47, 1.485},
    {"metal1", 2.315, 1.045, 2.385, 1.485},
    {"metal1", 1.935, 1.045, 2.005, 1.485},
    {"metal1", 1.555, 1.205, 1.625, 1.485},
    {"metal1", 0.04, 1.045, 0.11, 1.485},
};

inline constexpr RectSpec kNangateOR4X4Ground[] = {
    {"metal1", 0.0, -0.085, 2.47, 0.085},
    {"metal1", 2.315, -0.085, 2.385, 0.4},
    {"metal1", 1.905, -0.085, 2.04, 0.365},
    {"metal1", 1.525, -0.085, 1.66, 0.325},
    {"metal1", 1.145, -0.085, 1.28, 0.16},
    {"metal1", 0.765, -0.085, 0.9, 0.16},
    {"metal1", 0.385, -0.085, 0.52, 0.16},
    {"metal1", 0.04, -0.085, 0.11, 0.4},
};

inline constexpr RectSpec kNangateOR4X4ObsGroup0[] = {
    {"metal1", 0.77, 1.04, 1.685, 1.11, true},
    {"metal1", 1.615, 0.39, 1.685, 1.11, true},
    {"metal1", 1.37, 0.39, 1.685, 0.46, true},
    {"metal1", 0.235, 0.15, 0.305, 0.425, true},
    {"metal1", 1.37, 0.15, 1.44, 0.46, true},
    {"metal1", 0.235, 0.225, 1.44, 0.295, true},
};

inline constexpr GroupSpec kNangateOR4X4Groups[] = {
    {BindingKind::kPinNet, "A1", kNangateOR4X4PinA1, std::size(kNangateOR4X4PinA1)},
    {BindingKind::kPinNet, "A2", kNangateOR4X4PinA2, std::size(kNangateOR4X4PinA2)},
    {BindingKind::kPinNet, "A3", kNangateOR4X4PinA3, std::size(kNangateOR4X4PinA3)},
    {BindingKind::kPinNet, "A4", kNangateOR4X4PinA4, std::size(kNangateOR4X4PinA4)},
    {BindingKind::kPinNet, "ZN", kNangateOR4X4PinZN, std::size(kNangateOR4X4PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateOR4X4Power, std::size(kNangateOR4X4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateOR4X4Ground, std::size(kNangateOR4X4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateOR4X4ObsGroup0, std::size(kNangateOR4X4ObsGroup0)},
};

inline constexpr RectSpec kNangateSDFFRSX1PinD[] = {
    {"metal1", 5.07, 0.765, 5.26, 0.98},
};

inline constexpr RectSpec kNangateSDFFRSX1PinRN[] = {
    {"metal1", 0.82, 0.525, 0.92, 0.7},
};

inline constexpr RectSpec kNangateSDFFRSX1PinSE[] = {
    {"metal1", 5.19, 0.39, 5.335, 0.56},
    {"metal1", 4.76, 0.39, 5.335, 0.46},
    {"metal1", 4.76, 0.765, 5.005, 0.835},
    {"metal1", 4.76, 0.39, 4.83, 0.835},
};

inline constexpr RectSpec kNangateSDFFRSX1PinSI[] = {
    {"metal1", 4.56, 0.695, 4.69, 0.84},
};

inline constexpr RectSpec kNangateSDFFRSX1PinSN[] = {
    {"metal1", 1.01, 0.525, 1.11, 0.7},
};

inline constexpr RectSpec kNangateSDFFRSX1PinCK[] = {
    {"metal1", 1.575, 0.7, 1.67, 0.84},
};

inline constexpr RectSpec kNangateSDFFRSX1PinQ[] = {
    {"metal1", 0.045, 0.26, 0.13, 1.105},
};

inline constexpr RectSpec kNangateSDFFRSX1PinQN[] = {
    {"metal1", 0.425, 0.36, 0.51, 0.8},
};

inline constexpr RectSpec kNangateSDFFRSX1Power[] = {
    {"metal1", 0.0, 1.315, 5.51, 1.485},
    {"metal1", 5.175, 1.095, 5.31, 1.485},
    {"metal1", 4.415, 1.13, 4.55, 1.485},
    {"metal1", 3.585, 1.03, 3.72, 1.485},
    {"metal1", 3.045, 0.865, 3.18, 1.485},
    {"metal1", 2.665, 0.99, 2.8, 1.485},
    {"metal1", 1.945, 0.83, 2.015, 1.485},
    {"metal1", 1.305, 1.105, 1.44, 1.485},
    {"metal1", 0.925, 1.105, 1.06, 1.485},
    {"metal1", 0.545, 1.035, 0.68, 1.485},
    {"metal1", 0.195, 1.18, 0.33, 1.485},
};

inline constexpr RectSpec kNangateSDFFRSX1Ground[] = {
    {"metal1", 0.0, -0.085, 5.51, 0.085},
    {"metal1", 5.175, -0.085, 5.31, 0.225},
    {"metal1", 4.415, -0.085, 4.55, 0.225},
    {"metal1", 3.4, -0.085, 3.535, 0.285},
    {"metal1", 2.665, -0.085, 2.8, 0.285},
    {"metal1", 1.755, -0.085, 1.825, 0.32},
    {"metal1", 0.92, -0.085, 1.055, 0.285},
    {"metal1", 0.195, -0.085, 0.33, 0.16},
};

inline constexpr RectSpec kNangateSDFFRSX1ObsGroup0[] = {
    {"metal1", 5.4, 0.215, 5.47, 1.235, true},
    {"metal1", 4.9, 0.625, 5.47, 0.695, true},
    {"metal1", 4.9, 0.56, 4.975, 0.695, true},
};

inline constexpr RectSpec kNangateSDFFRSX1ObsGroup1[] = {
    {"metal1", 4.37, 0.945, 4.93, 1.015, true},
    {"metal1", 4.37, 0.41, 4.44, 1.015, true},
    {"metal1", 4.37, 0.41, 4.685, 0.48, true},
    {"metal1", 4.615, 0.22, 4.685, 0.48, true},
    {"metal1", 4.615, 0.22, 4.93, 0.29, true},
};

inline constexpr RectSpec kNangateSDFFRSX1ObsGroup2[] = {
    {"metal1", 3.94, 1.18, 4.28, 1.25, true},
    {"metal1", 4.21, 0.16, 4.28, 1.25, true},
    {"metal1", 3.94, 0.76, 4.01, 1.25, true},
    {"metal1", 2.18, 1.035, 2.525, 1.105, true},
    {"metal1", 2.455, 0.35, 2.525, 1.105, true},
    {"metal1", 3.27, 0.76, 3.34, 1.09, true},
    {"metal1", 3.27, 0.76, 4.01, 0.83, true},
    {"metal1", 3.865, 0.16, 3.935, 0.51, true},
    {"metal1", 3.265, 0.35, 3.935, 0.42, true},
    {"metal1", 2.455, 0.35, 2.98, 0.42, true},
    {"metal1", 2.91, 0.16, 2.98, 0.42, true},
    {"metal1", 3.265, 0.16, 3.335, 0.42, true},
    {"metal1", 3.865, 0.16, 4.28, 0.23, true},
    {"metal1", 2.91, 0.16, 3.335, 0.23, true},
};

inline constexpr RectSpec kNangateSDFFRSX1ObsGroup3[] = {
    {"metal1", 4.075, 0.295, 4.145, 1.115, true},
    {"metal1", 2.75, 0.62, 4.145, 0.69, true},
    {"metal1", 4.0, 0.295, 4.145, 0.69, true},
};

inline constexpr RectSpec kNangateSDFFRSX1ObsGroup4[] = {
    {"metal1", 3.805, 0.895, 3.875, 1.115, true},
    {"metal1", 3.435, 0.895, 3.505, 1.115, true},
    {"metal1", 3.435, 0.895, 3.875, 0.965, true},
};

inline constexpr RectSpec kNangateSDFFRSX1ObsGroup5[] = {
    {"metal1", 2.615, 0.755, 2.99, 0.825, true},
    {"metal1", 2.615, 0.485, 2.685, 0.825, true},
    {"metal1", 2.615, 0.485, 3.8, 0.555, true},
    {"metal1", 3.045, 0.295, 3.18, 0.555, true},
};

inline constexpr RectSpec kNangateSDFFRSX1ObsGroup6[] = {
    {"metal1", 2.315, 0.2, 2.385, 0.965, true},
    {"metal1", 1.415, 0.555, 2.385, 0.625, true},
};

inline constexpr RectSpec kNangateSDFFRSX1ObsGroup7[] = {
    {"metal1", 2.125, 0.695, 2.195, 0.965, true},
    {"metal1", 1.755, 0.695, 1.825, 0.965, true},
    {"metal1", 1.755, 0.695, 2.195, 0.765, true},
};

inline constexpr RectSpec kNangateSDFFRSX1ObsGroup8[] = {
    {"metal1", 1.145, 0.765, 1.215, 1.105, true},
    {"metal1", 0.61, 0.765, 1.215, 0.835, true},
    {"metal1", 0.61, 0.39, 0.68, 0.835, true},
    {"metal1", 0.61, 0.39, 1.19, 0.46, true},
    {"metal1", 1.12, 0.25, 1.19, 0.46, true},
    {"metal1", 1.62, 0.385, 2.15, 0.455, true},
    {"metal1", 1.62, 0.15, 1.69, 0.455, true},
    {"metal1", 1.12, 0.25, 1.4, 0.32, true},
    {"metal1", 1.33, 0.15, 1.4, 0.32, true},
    {"metal1", 1.33, 0.15, 1.69, 0.22, true},
};

inline constexpr RectSpec kNangateSDFFRSX1ObsGroup9[] = {
    {"metal1", 1.585, 1.165, 1.815, 1.235, true},
    {"metal1", 1.585, 0.905, 1.655, 1.235, true},
    {"metal1", 1.28, 0.905, 1.655, 0.975, true},
    {"metal1", 1.28, 0.41, 1.35, 0.975, true},
    {"metal1", 1.28, 0.41, 1.555, 0.48, true},
    {"metal1", 1.485, 0.285, 1.555, 0.48, true},
};

inline constexpr RectSpec kNangateSDFFRSX1ObsGroup10[] = {
    {"metal1", 0.195, 0.9, 0.865, 0.97, true},
    {"metal1", 0.195, 0.225, 0.265, 0.97, true},
    {"metal1", 0.195, 0.225, 0.68, 0.295, true},
};

inline constexpr GroupSpec kNangateSDFFRSX1Groups[] = {
    {BindingKind::kPinNet, "D", kNangateSDFFRSX1PinD, std::size(kNangateSDFFRSX1PinD)},
    {BindingKind::kPinNet, "RN", kNangateSDFFRSX1PinRN, std::size(kNangateSDFFRSX1PinRN)},
    {BindingKind::kPinNet, "SE", kNangateSDFFRSX1PinSE, std::size(kNangateSDFFRSX1PinSE)},
    {BindingKind::kPinNet, "SI", kNangateSDFFRSX1PinSI, std::size(kNangateSDFFRSX1PinSI)},
    {BindingKind::kPinNet, "SN", kNangateSDFFRSX1PinSN, std::size(kNangateSDFFRSX1PinSN)},
    {BindingKind::kPinNet, "CK", kNangateSDFFRSX1PinCK, std::size(kNangateSDFFRSX1PinCK)},
    {BindingKind::kPinNet, "Q", kNangateSDFFRSX1PinQ, std::size(kNangateSDFFRSX1PinQ)},
    {BindingKind::kPinNet, "QN", kNangateSDFFRSX1PinQN, std::size(kNangateSDFFRSX1PinQN)},
    {BindingKind::kSupplyNet, "POWER", kNangateSDFFRSX1Power, std::size(kNangateSDFFRSX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateSDFFRSX1Ground, std::size(kNangateSDFFRSX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateSDFFRSX1ObsGroup0, std::size(kNangateSDFFRSX1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateSDFFRSX1ObsGroup1, std::size(kNangateSDFFRSX1ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateSDFFRSX1ObsGroup2, std::size(kNangateSDFFRSX1ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateSDFFRSX1ObsGroup3, std::size(kNangateSDFFRSX1ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateSDFFRSX1ObsGroup4, std::size(kNangateSDFFRSX1ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateSDFFRSX1ObsGroup5, std::size(kNangateSDFFRSX1ObsGroup5)},
    {BindingKind::kSyntheticNet, "OBS6", kNangateSDFFRSX1ObsGroup6, std::size(kNangateSDFFRSX1ObsGroup6)},
    {BindingKind::kSyntheticNet, "OBS7", kNangateSDFFRSX1ObsGroup7, std::size(kNangateSDFFRSX1ObsGroup7)},
    {BindingKind::kSyntheticNet, "OBS8", kNangateSDFFRSX1ObsGroup8, std::size(kNangateSDFFRSX1ObsGroup8)},
    {BindingKind::kSyntheticNet, "OBS9", kNangateSDFFRSX1ObsGroup9, std::size(kNangateSDFFRSX1ObsGroup9)},
    {BindingKind::kSyntheticNet, "OBS10", kNangateSDFFRSX1ObsGroup10, std::size(kNangateSDFFRSX1ObsGroup10)},
};

inline constexpr RectSpec kNangateSDFFRSX2PinD[] = {
    {"metal1", 5.495, 0.42, 5.64, 0.56},
};

inline constexpr RectSpec kNangateSDFFRSX2PinRN[] = {
    {"metal1", 1.01, 0.545, 1.165, 0.7},
};

inline constexpr RectSpec kNangateSDFFRSX2PinSE[] = {
    {"metal1", 5.57, 0.675, 5.7, 0.84},
    {"metal1", 5.135, 0.72, 5.7, 0.79},
    {"metal1", 5.135, 0.385, 5.205, 0.79},
};

inline constexpr RectSpec kNangateSDFFRSX2PinSI[] = {
    {"metal1", 4.925, 0.56, 5.07, 0.7},
};

inline constexpr RectSpec kNangateSDFFRSX2PinSN[] = {
    {"metal1", 1.365, 0.545, 1.46, 0.7},
};

inline constexpr RectSpec kNangateSDFFRSX2PinCK[] = {
    {"metal1", 1.9, 0.175, 2.065, 0.245},
};

inline constexpr RectSpec kNangateSDFFRSX2PinQ[] = {
    {"metal1", 0.24, 0.15, 0.32, 1.125},
};

inline constexpr RectSpec kNangateSDFFRSX2PinQN[] = {
    {"metal1", 0.6, 0.435, 0.735, 0.9},
};

inline constexpr RectSpec kNangateSDFFRSX2Power[] = {
    {"metal1", 0.0, 1.315, 5.89, 1.485},
    {"metal1", 5.54, 1.195, 5.675, 1.485},
    {"metal1", 4.78, 1.09, 4.915, 1.485},
    {"metal1", 3.95, 1.09, 4.085, 1.485},
    {"metal1", 3.42, 0.985, 3.555, 1.485},
    {"metal1", 3.04, 0.985, 3.175, 1.485},
    {"metal1", 2.285, 0.965, 2.42, 1.485},
    {"metal1", 1.64, 1.115, 1.775, 1.485},
    {"metal1", 1.18, 1.12, 1.315, 1.485},
    {"metal1", 0.79, 1.1, 0.925, 1.485},
    {"metal1", 0.41, 1.1, 0.545, 1.485},
    {"metal1", 0.065, 0.85, 0.135, 1.485},
};

inline constexpr RectSpec kNangateSDFFRSX2Ground[] = {
    {"metal1", 0.0, -0.085, 5.89, 0.085},
    {"metal1", 5.54, -0.085, 5.675, 0.18},
    {"metal1", 4.81, -0.085, 4.88, 0.27},
    {"metal1", 3.76, -0.085, 3.895, 0.285},
    {"metal1", 3.04, -0.085, 3.175, 0.285},
    {"metal1", 2.13, -0.085, 2.2, 0.32},
    {"metal1", 1.7, -0.085, 1.835, 0.285},
    {"metal1", 0.79, -0.085, 0.925, 0.16},
    {"metal1", 0.41, -0.085, 0.545, 0.16},
    {"metal1", 0.065, -0.085, 0.135, 0.41},
};

inline constexpr RectSpec kNangateSDFFRSX2ObsGroup0[] = {
    {"metal1", 5.765, 0.15, 5.835, 1.09, true},
    {"metal1", 5.27, 0.565, 5.41, 0.635, true},
    {"metal1", 5.34, 0.285, 5.41, 0.635, true},
    {"metal1", 5.34, 0.285, 5.835, 0.355, true},
};

inline constexpr RectSpec kNangateSDFFRSX2ObsGroup1[] = {
    {"metal1", 4.74, 0.95, 5.295, 1.02, true},
    {"metal1", 4.74, 0.375, 4.81, 1.02, true},
    {"metal1", 4.74, 0.375, 5.045, 0.445, true},
    {"metal1", 4.975, 0.165, 5.045, 0.445, true},
    {"metal1", 4.975, 0.165, 5.295, 0.235, true},
};

inline constexpr RectSpec kNangateSDFFRSX2ObsGroup2[] = {
    {"metal1", 4.305, 1.155, 4.675, 1.225, true},
    {"metal1", 4.605, 0.15, 4.675, 1.225, true},
    {"metal1", 2.555, 1.115, 2.915, 1.185, true},
    {"metal1", 2.845, 0.35, 2.915, 1.185, true},
    {"metal1", 4.305, 0.765, 4.375, 1.225, true},
    {"metal1", 3.615, 0.765, 4.375, 0.835, true},
    {"metal1", 4.575, 0.69, 4.675, 0.825, true},
    {"metal1", 3.61, 0.355, 4.34, 0.425, true},
    {"metal1", 4.27, 0.15, 4.34, 0.425, true},
    {"metal1", 2.845, 0.35, 3.39, 0.42, true},
    {"metal1", 3.32, 0.15, 3.39, 0.42, true},
    {"metal1", 3.61, 0.15, 3.68, 0.425, true},
    {"metal1", 4.27, 0.15, 4.675, 0.22, true},
    {"metal1", 3.32, 0.15, 3.68, 0.22, true},
};

inline constexpr RectSpec kNangateSDFFRSX2ObsGroup3[] = {
    {"metal1", 4.44, 0.625, 4.51, 1.09, true},
    {"metal1", 3.125, 0.625, 4.51, 0.695, true},
    {"metal1", 4.405, 0.285, 4.475, 0.695, true},
    {"metal1", 4.405, 0.285, 4.54, 0.355, true},
};

inline constexpr RectSpec kNangateSDFFRSX2ObsGroup4[] = {
    {"metal1", 4.17, 0.955, 4.24, 1.175, true},
    {"metal1", 3.8, 0.955, 3.87, 1.175, true},
    {"metal1", 3.8, 0.955, 4.24, 1.025, true},
};

inline constexpr RectSpec kNangateSDFFRSX2ObsGroup5[] = {
    {"metal1", 2.99, 0.765, 3.37, 0.835, true},
    {"metal1", 2.99, 0.485, 3.06, 0.835, true},
    {"metal1", 2.99, 0.49, 4.17, 0.56, true},
    {"metal1", 2.99, 0.485, 3.525, 0.56, true},
    {"metal1", 3.455, 0.32, 3.525, 0.56, true},
};

inline constexpr RectSpec kNangateSDFFRSX2ObsGroup6[] = {
    {"metal1", 2.7, 0.2, 2.77, 1.05, true},
    {"metal1", 1.665, 0.485, 1.735, 0.68, true},
    {"metal1", 1.665, 0.485, 2.77, 0.555, true},
};

inline constexpr RectSpec kNangateSDFFRSX2ObsGroup7[] = {
    {"metal1", 1.53, 0.84, 2.04, 0.91, true},
    {"metal1", 1.97, 0.685, 2.04, 0.91, true},
    {"metal1", 1.53, 0.35, 1.6, 0.91, true},
    {"metal1", 1.97, 0.685, 2.635, 0.755, true},
    {"metal1", 2.565, 0.62, 2.635, 0.755, true},
    {"metal1", 1.53, 0.35, 2.04, 0.42, true},
};

inline constexpr RectSpec kNangateSDFFRSX2ObsGroup8[] = {
    {"metal1", 2.5, 0.83, 2.57, 1.05, true},
    {"metal1", 2.13, 0.83, 2.2, 1.05, true},
    {"metal1", 2.13, 0.83, 2.57, 0.9, true},
};

inline constexpr RectSpec kNangateSDFFRSX2ObsGroup9[] = {
    {"metal1", 1.84, 1.16, 2.22, 1.23, true},
    {"metal1", 1.84, 0.975, 1.91, 1.23, true},
    {"metal1", 1.395, 0.975, 1.91, 1.045, true},
    {"metal1", 1.395, 0.765, 1.465, 1.045, true},
    {"metal1", 0.87, 0.765, 1.465, 0.835, true},
    {"metal1", 0.87, 0.41, 0.94, 0.835, true},
    {"metal1", 0.87, 0.41, 1.46, 0.48, true},
};

inline constexpr RectSpec kNangateSDFFRSX2ObsGroup10[] = {
    {"metal1", 0.39, 0.965, 1.12, 1.035, true},
    {"metal1", 0.39, 0.23, 0.46, 1.035, true},
    {"metal1", 0.39, 0.23, 1.305, 0.3, true},
};

inline constexpr GroupSpec kNangateSDFFRSX2Groups[] = {
    {BindingKind::kPinNet, "D", kNangateSDFFRSX2PinD, std::size(kNangateSDFFRSX2PinD)},
    {BindingKind::kPinNet, "RN", kNangateSDFFRSX2PinRN, std::size(kNangateSDFFRSX2PinRN)},
    {BindingKind::kPinNet, "SE", kNangateSDFFRSX2PinSE, std::size(kNangateSDFFRSX2PinSE)},
    {BindingKind::kPinNet, "SI", kNangateSDFFRSX2PinSI, std::size(kNangateSDFFRSX2PinSI)},
    {BindingKind::kPinNet, "SN", kNangateSDFFRSX2PinSN, std::size(kNangateSDFFRSX2PinSN)},
    {BindingKind::kPinNet, "CK", kNangateSDFFRSX2PinCK, std::size(kNangateSDFFRSX2PinCK)},
    {BindingKind::kPinNet, "Q", kNangateSDFFRSX2PinQ, std::size(kNangateSDFFRSX2PinQ)},
    {BindingKind::kPinNet, "QN", kNangateSDFFRSX2PinQN, std::size(kNangateSDFFRSX2PinQN)},
    {BindingKind::kSupplyNet, "POWER", kNangateSDFFRSX2Power, std::size(kNangateSDFFRSX2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateSDFFRSX2Ground, std::size(kNangateSDFFRSX2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateSDFFRSX2ObsGroup0, std::size(kNangateSDFFRSX2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateSDFFRSX2ObsGroup1, std::size(kNangateSDFFRSX2ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateSDFFRSX2ObsGroup2, std::size(kNangateSDFFRSX2ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateSDFFRSX2ObsGroup3, std::size(kNangateSDFFRSX2ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateSDFFRSX2ObsGroup4, std::size(kNangateSDFFRSX2ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateSDFFRSX2ObsGroup5, std::size(kNangateSDFFRSX2ObsGroup5)},
    {BindingKind::kSyntheticNet, "OBS6", kNangateSDFFRSX2ObsGroup6, std::size(kNangateSDFFRSX2ObsGroup6)},
    {BindingKind::kSyntheticNet, "OBS7", kNangateSDFFRSX2ObsGroup7, std::size(kNangateSDFFRSX2ObsGroup7)},
    {BindingKind::kSyntheticNet, "OBS8", kNangateSDFFRSX2ObsGroup8, std::size(kNangateSDFFRSX2ObsGroup8)},
    {BindingKind::kSyntheticNet, "OBS9", kNangateSDFFRSX2ObsGroup9, std::size(kNangateSDFFRSX2ObsGroup9)},
    {BindingKind::kSyntheticNet, "OBS10", kNangateSDFFRSX2ObsGroup10, std::size(kNangateSDFFRSX2ObsGroup10)},
};

inline constexpr RectSpec kNangateSDFFRX1PinD[] = {
    {"metal1", 4.24, 0.56, 4.365, 0.7},
};

inline constexpr RectSpec kNangateSDFFRX1PinRN[] = {
    {"metal1", 0.82, 0.84, 0.925, 0.98},
};

inline constexpr RectSpec kNangateSDFFRX1PinSE[] = {
    {"metal1", 4.105, 0.77, 4.53, 0.84},
    {"metal1", 4.43, 0.56, 4.53, 0.84},
    {"metal1", 4.105, 0.565, 4.175, 0.84},
};

inline constexpr RectSpec kNangateSDFFRX1PinSI[] = {
    {"metal1", 3.67, 0.655, 3.765, 0.84},
};

inline constexpr RectSpec kNangateSDFFRX1PinCK[] = {
    {"metal1", 1.77, 0.66, 1.995, 0.84},
};

inline constexpr RectSpec kNangateSDFFRX1PinQ[] = {
    {"metal1", 0.435, 0.185, 0.51, 1.015},
};

inline constexpr RectSpec kNangateSDFFRX1PinQN[] = {
    {"metal1", 0.06, 0.185, 0.13, 1.065},
};

inline constexpr RectSpec kNangateSDFFRX1Power[] = {
    {"metal1", 0.0, 1.315, 4.75, 1.485},
    {"metal1", 4.4, 1.045, 4.47, 1.485},
    {"metal1", 3.64, 1.08, 3.71, 1.485},
    {"metal1", 3.27, 1.08, 3.34, 1.485},
    {"metal1", 2.4, 0.995, 2.47, 1.485},
    {"metal1", 1.84, 1.06, 1.975, 1.485},
    {"metal1", 1.15, 1.205, 1.22, 1.485},
    {"metal1", 0.74, 1.24, 0.875, 1.485},
    {"metal1", 0.21, 1.24, 0.345, 1.485},
};

inline constexpr RectSpec kNangateSDFFRX1Ground[] = {
    {"metal1", 0.0, -0.085, 4.75, 0.085},
    {"metal1", 4.4, -0.085, 4.47, 0.32},
    {"metal1", 3.64, -0.085, 3.71, 0.32},
    {"metal1", 3.11, -0.085, 3.18, 0.32},
    {"metal1", 2.27, -0.085, 2.34, 0.425},
    {"metal1", 1.71, -0.085, 1.845, 0.285},
    {"metal1", 0.77, -0.085, 0.84, 0.32},
    {"metal1", 0.24, -0.085, 0.31, 0.46},
};

inline constexpr RectSpec kNangateSDFFRX1ObsGroup0[] = {
    {"metal1", 4.595, 0.185, 4.665, 1.22, true},
    {"metal1", 3.965, 0.905, 4.665, 0.975, true},
    {"metal1", 3.965, 0.715, 4.035, 0.975, true},
    {"metal1", 4.1, 0.415, 4.665, 0.485, true},
};

inline constexpr RectSpec kNangateSDFFRX1ObsGroup1[] = {
    {"metal1", 3.83, 1.04, 4.125, 1.11, true},
    {"metal1", 3.83, 0.22, 3.9, 1.11, true},
    {"metal1", 3.12, 0.52, 3.9, 0.59, true},
    {"metal1", 3.83, 0.22, 4.125, 0.29, true},
};

inline constexpr RectSpec kNangateSDFFRX1ObsGroup2[] = {
    {"metal1", 2.54, 1.18, 3.205, 1.25, true},
    {"metal1", 3.135, 0.945, 3.205, 1.25, true},
    {"metal1", 3.45, 0.945, 3.52, 1.2, true},
    {"metal1", 2.54, 0.505, 2.61, 1.25, true},
    {"metal1", 3.135, 0.945, 3.585, 1.015, true},
    {"metal1", 3.515, 0.655, 3.585, 1.015, true},
    {"metal1", 2.985, 0.655, 3.585, 0.725, true},
    {"metal1", 2.985, 0.385, 3.055, 0.725, true},
    {"metal1", 2.985, 0.385, 3.335, 0.455, true},
    {"metal1", 3.265, 0.185, 3.335, 0.455, true},
};

inline constexpr RectSpec kNangateSDFFRX1ObsGroup3[] = {
    {"metal1", 2.69, 1.015, 3.065, 1.085, true},
    {"metal1", 2.995, 0.81, 3.065, 1.085, true},
    {"metal1", 2.69, 0.305, 2.76, 1.085, true},
    {"metal1", 2.995, 0.81, 3.45, 0.88, true},
};

inline constexpr RectSpec kNangateSDFFRX1ObsGroup4[] = {
    {"metal1", 2.22, 0.855, 2.29, 1.13, true},
    {"metal1", 2.22, 0.855, 2.405, 0.925, true},
    {"metal1", 2.335, 0.49, 2.405, 0.925, true},
    {"metal1", 2.85, 0.17, 2.92, 0.835, true},
    {"metal1", 1.43, 0.49, 1.5, 0.7, true},
    {"metal1", 1.43, 0.49, 2.475, 0.56, true},
    {"metal1", 2.405, 0.17, 2.475, 0.56, true},
    {"metal1", 2.09, 0.185, 2.16, 0.56, true},
    {"metal1", 2.405, 0.17, 2.92, 0.24, true},
};

inline constexpr RectSpec kNangateSDFFRX1ObsGroup5[] = {
    {"metal1", 1.545, 1.18, 1.695, 1.25, true},
    {"metal1", 1.625, 0.765, 1.695, 1.25, true},
    {"metal1", 2.065, 0.655, 2.135, 1.065, true},
    {"metal1", 1.625, 0.905, 2.135, 0.975, true},
    {"metal1", 1.28, 0.765, 1.695, 0.835, true},
    {"metal1", 2.065, 0.655, 2.26, 0.79, true},
    {"metal1", 1.28, 0.35, 1.35, 0.835, true},
    {"metal1", 1.28, 0.35, 2.0, 0.42, true},
    {"metal1", 1.93, 0.185, 2.0, 0.42, true},
};

inline constexpr RectSpec kNangateSDFFRX1ObsGroup6[] = {
    {"metal1", 1.49, 0.905, 1.56, 1.04, true},
    {"metal1", 1.14, 0.905, 1.56, 0.975, true},
    {"metal1", 1.14, 0.215, 1.21, 0.975, true},
    {"metal1", 0.72, 0.705, 1.21, 0.775, true},
    {"metal1", 0.72, 0.525, 0.79, 0.775, true},
    {"metal1", 1.14, 0.215, 1.46, 0.285, true},
};

inline constexpr RectSpec kNangateSDFFRX1ObsGroup7[] = {
    {"metal1", 0.585, 0.185, 0.655, 1.24, true},
    {"metal1", 0.195, 1.08, 0.655, 1.15, true},
    {"metal1", 0.195, 0.525, 0.265, 1.15, true},
    {"metal1", 1.005, 0.39, 1.075, 0.635, true},
    {"metal1", 0.585, 0.39, 1.075, 0.46, true},
};

inline constexpr RectSpec kNangateSDFFRX1ObsGroup8[] = {
    {"metal1", 0.935, 1.045, 1.41, 1.115, true},
};

inline constexpr GroupSpec kNangateSDFFRX1Groups[] = {
    {BindingKind::kPinNet, "D", kNangateSDFFRX1PinD, std::size(kNangateSDFFRX1PinD)},
    {BindingKind::kPinNet, "RN", kNangateSDFFRX1PinRN, std::size(kNangateSDFFRX1PinRN)},
    {BindingKind::kPinNet, "SE", kNangateSDFFRX1PinSE, std::size(kNangateSDFFRX1PinSE)},
    {BindingKind::kPinNet, "SI", kNangateSDFFRX1PinSI, std::size(kNangateSDFFRX1PinSI)},
    {BindingKind::kPinNet, "CK", kNangateSDFFRX1PinCK, std::size(kNangateSDFFRX1PinCK)},
    {BindingKind::kPinNet, "Q", kNangateSDFFRX1PinQ, std::size(kNangateSDFFRX1PinQ)},
    {BindingKind::kPinNet, "QN", kNangateSDFFRX1PinQN, std::size(kNangateSDFFRX1PinQN)},
    {BindingKind::kSupplyNet, "POWER", kNangateSDFFRX1Power, std::size(kNangateSDFFRX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateSDFFRX1Ground, std::size(kNangateSDFFRX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateSDFFRX1ObsGroup0, std::size(kNangateSDFFRX1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateSDFFRX1ObsGroup1, std::size(kNangateSDFFRX1ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateSDFFRX1ObsGroup2, std::size(kNangateSDFFRX1ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateSDFFRX1ObsGroup3, std::size(kNangateSDFFRX1ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateSDFFRX1ObsGroup4, std::size(kNangateSDFFRX1ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateSDFFRX1ObsGroup5, std::size(kNangateSDFFRX1ObsGroup5)},
    {BindingKind::kSyntheticNet, "OBS6", kNangateSDFFRX1ObsGroup6, std::size(kNangateSDFFRX1ObsGroup6)},
    {BindingKind::kSyntheticNet, "OBS7", kNangateSDFFRX1ObsGroup7, std::size(kNangateSDFFRX1ObsGroup7)},
    {BindingKind::kSyntheticNet, "OBS8", kNangateSDFFRX1ObsGroup8, std::size(kNangateSDFFRX1ObsGroup8)},
};

inline constexpr RectSpec kNangateSDFFRX2PinD[] = {
    {"metal1", 4.565, 0.42, 4.69, 0.625},
};

inline constexpr RectSpec kNangateSDFFRX2PinRN[] = {
    {"metal1", 1.145, 0.84, 1.27, 0.98},
};

inline constexpr RectSpec kNangateSDFFRX2PinSE[] = {
    {"metal1", 4.345, 0.7, 4.765, 0.845},
    {"metal1", 4.345, 0.565, 4.415, 0.845},
};

inline constexpr RectSpec kNangateSDFFRX2PinSI[] = {
    {"metal1", 3.86, 0.67, 4.005, 0.84},
};

inline constexpr RectSpec kNangateSDFFRX2PinCK[] = {
    {"metal1", 2.145, 0.695, 2.28, 0.84},
};

inline constexpr RectSpec kNangateSDFFRX2PinQ[] = {
    {"metal1", 0.425, 0.395, 0.51, 1.005},
};

inline constexpr RectSpec kNangateSDFFRX2PinQN[] = {
    {"metal1", 0.795, 0.56, 0.89, 1.005},
    {"metal1", 0.795, 0.395, 0.865, 1.005},
};

inline constexpr RectSpec kNangateSDFFRX2Power[] = {
    {"metal1", 0.0, 1.315, 4.94, 1.485},
    {"metal1", 4.635, 1.045, 4.705, 1.485},
    {"metal1", 3.875, 1.08, 3.945, 1.485},
    {"metal1", 3.46, 1.115, 3.595, 1.485},
    {"metal1", 2.66, 0.995, 2.73, 1.485},
    {"metal1", 2.06, 1.06, 2.195, 1.485},
    {"metal1", 1.37, 1.205, 1.44, 1.485},
    {"metal1", 0.985, 1.205, 1.055, 1.485},
    {"metal1", 0.575, 1.24, 0.71, 1.485},
    {"metal1", 0.225, 1.205, 0.295, 1.485},
};

inline constexpr RectSpec kNangateSDFFRX2Ground[] = {
    {"metal1", 0.0, -0.085, 4.94, 0.085},
    {"metal1", 4.635, -0.085, 4.705, 0.195},
    {"metal1", 3.875, -0.085, 3.945, 0.32},
    {"metal1", 3.295, -0.085, 3.365, 0.32},
    {"metal1", 2.535, -0.085, 2.605, 0.42},
    {"metal1", 2.005, -0.085, 2.075, 0.32},
    {"metal1", 1.065, -0.085, 1.135, 0.32},
    {"metal1", 0.575, -0.085, 0.71, 0.16},
    {"metal1", 0.195, -0.085, 0.33, 0.16},
};

inline constexpr RectSpec kNangateSDFFRX2ObsGroup0[] = {
    {"metal1", 4.83, 0.195, 4.9, 1.22, true},
    {"metal1", 4.205, 0.91, 4.9, 0.98, true},
    {"metal1", 4.205, 0.715, 4.275, 0.98, true},
    {"metal1", 4.36, 0.415, 4.495, 0.485, true},
    {"metal1", 4.425, 0.285, 4.495, 0.485, true},
    {"metal1", 4.425, 0.285, 4.9, 0.355, true},
};

inline constexpr RectSpec kNangateSDFFRX2ObsGroup1[] = {
    {"metal1", 4.07, 1.045, 4.36, 1.115, true},
    {"metal1", 4.07, 0.23, 4.14, 1.115, true},
    {"metal1", 3.42, 0.52, 4.14, 0.59, true},
    {"metal1", 4.07, 0.23, 4.36, 0.3, true},
};

inline constexpr RectSpec kNangateSDFFRX2ObsGroup2[] = {
    {"metal1", 2.805, 1.18, 3.255, 1.25, true},
    {"metal1", 3.185, 0.975, 3.255, 1.25, true},
    {"metal1", 3.69, 0.655, 3.76, 1.2, true},
    {"metal1", 2.805, 0.5, 2.875, 1.25, true},
    {"metal1", 3.185, 0.975, 3.76, 1.045, true},
    {"metal1", 3.285, 0.655, 3.76, 0.725, true},
    {"metal1", 3.285, 0.385, 3.355, 0.725, true},
    {"metal1", 3.285, 0.385, 3.57, 0.455, true},
    {"metal1", 3.5, 0.2, 3.57, 0.455, true},
};

inline constexpr RectSpec kNangateSDFFRX2ObsGroup3[] = {
    {"metal1", 3.04, 0.84, 3.11, 1.115, true},
    {"metal1", 2.955, 0.84, 3.11, 0.915, true},
    {"metal1", 2.955, 0.84, 3.625, 0.91, true},
    {"metal1", 2.955, 0.33, 3.025, 0.915, true},
    {"metal1", 2.89, 0.33, 3.025, 0.4, true},
};

inline constexpr RectSpec kNangateSDFFRX2ObsGroup4[] = {
    {"metal1", 2.48, 0.815, 2.55, 1.09, true},
    {"metal1", 2.48, 0.815, 2.74, 0.885, true},
    {"metal1", 2.67, 0.165, 2.74, 0.885, true},
    {"metal1", 3.15, 0.165, 3.22, 0.775, true},
    {"metal1", 1.715, 0.545, 1.785, 0.685, true},
    {"metal1", 1.715, 0.545, 2.74, 0.615, true},
    {"metal1", 2.35, 0.285, 2.42, 0.615, true},
    {"metal1", 2.67, 0.165, 3.22, 0.235, true},
};

inline constexpr RectSpec kNangateSDFFRX2ObsGroup5[] = {
    {"metal1", 1.79, 1.18, 1.95, 1.25, true},
    {"metal1", 1.88, 0.75, 1.95, 1.25, true},
    {"metal1", 1.88, 0.915, 2.415, 0.985, true},
    {"metal1", 2.345, 0.68, 2.415, 0.985, true},
    {"metal1", 1.56, 0.75, 1.95, 0.82, true},
    {"metal1", 2.345, 0.68, 2.56, 0.75, true},
    {"metal1", 1.56, 0.41, 1.63, 0.82, true},
    {"metal1", 1.56, 0.41, 2.265, 0.48, true},
    {"metal1", 2.195, 0.26, 2.265, 0.48, true},
};

inline constexpr RectSpec kNangateSDFFRX2ObsGroup6[] = {
    {"metal1", 1.425, 0.885, 1.815, 0.955, true},
    {"metal1", 1.425, 0.265, 1.495, 0.955, true},
    {"metal1", 0.29, 0.26, 0.36, 0.66, true},
    {"metal1", 0.93, 0.385, 1.495, 0.455, true},
    {"metal1", 0.93, 0.26, 1.0, 0.455, true},
    {"metal1", 1.425, 0.265, 1.73, 0.335, true},
    {"metal1", 0.29, 0.26, 1.0, 0.33, true},
};

inline constexpr RectSpec kNangateSDFFRX2ObsGroup7[] = {
    {"metal1", 1.155, 1.045, 1.29, 1.25, true},
    {"metal1", 1.155, 1.045, 1.63, 1.115, true},
};

inline constexpr RectSpec kNangateSDFFRX2ObsGroup8[] = {
    {"metal1", 0.045, 1.07, 1.08, 1.14, true},
    {"metal1", 1.01, 0.64, 1.08, 1.14, true},
    {"metal1", 0.66, 0.525, 0.73, 1.14, true},
    {"metal1", 0.045, 0.26, 0.115, 1.14, true},
    {"metal1", 1.01, 0.64, 1.36, 0.775, true},
};

inline constexpr GroupSpec kNangateSDFFRX2Groups[] = {
    {BindingKind::kPinNet, "D", kNangateSDFFRX2PinD, std::size(kNangateSDFFRX2PinD)},
    {BindingKind::kPinNet, "RN", kNangateSDFFRX2PinRN, std::size(kNangateSDFFRX2PinRN)},
    {BindingKind::kPinNet, "SE", kNangateSDFFRX2PinSE, std::size(kNangateSDFFRX2PinSE)},
    {BindingKind::kPinNet, "SI", kNangateSDFFRX2PinSI, std::size(kNangateSDFFRX2PinSI)},
    {BindingKind::kPinNet, "CK", kNangateSDFFRX2PinCK, std::size(kNangateSDFFRX2PinCK)},
    {BindingKind::kPinNet, "Q", kNangateSDFFRX2PinQ, std::size(kNangateSDFFRX2PinQ)},
    {BindingKind::kPinNet, "QN", kNangateSDFFRX2PinQN, std::size(kNangateSDFFRX2PinQN)},
    {BindingKind::kSupplyNet, "POWER", kNangateSDFFRX2Power, std::size(kNangateSDFFRX2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateSDFFRX2Ground, std::size(kNangateSDFFRX2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateSDFFRX2ObsGroup0, std::size(kNangateSDFFRX2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateSDFFRX2ObsGroup1, std::size(kNangateSDFFRX2ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateSDFFRX2ObsGroup2, std::size(kNangateSDFFRX2ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateSDFFRX2ObsGroup3, std::size(kNangateSDFFRX2ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateSDFFRX2ObsGroup4, std::size(kNangateSDFFRX2ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateSDFFRX2ObsGroup5, std::size(kNangateSDFFRX2ObsGroup5)},
    {BindingKind::kSyntheticNet, "OBS6", kNangateSDFFRX2ObsGroup6, std::size(kNangateSDFFRX2ObsGroup6)},
    {BindingKind::kSyntheticNet, "OBS7", kNangateSDFFRX2ObsGroup7, std::size(kNangateSDFFRX2ObsGroup7)},
    {BindingKind::kSyntheticNet, "OBS8", kNangateSDFFRX2ObsGroup8, std::size(kNangateSDFFRX2ObsGroup8)},
};

inline constexpr RectSpec kNangateSDFFSX1PinD[] = {
    {"metal1", 0.25, 0.55, 0.38, 0.7},
};

inline constexpr RectSpec kNangateSDFFSX1PinSE[] = {
    {"metal1", 0.06, 0.765, 0.57, 0.835},
    {"metal1", 0.5, 0.55, 0.57, 0.835},
    {"metal1", 0.06, 0.55, 0.185, 0.835},
};

inline constexpr RectSpec kNangateSDFFSX1PinSI[] = {
    {"metal1", 0.91, 0.42, 1.08, 0.56},
};

inline constexpr RectSpec kNangateSDFFSX1PinSN[] = {
    {"metal1", 3.84, 0.42, 3.93, 0.575},
};

inline constexpr RectSpec kNangateSDFFSX1PinCK[] = {
    {"metal1", 1.01, 0.785, 1.115, 0.98},
};

inline constexpr RectSpec kNangateSDFFSX1PinQ[] = {
    {"metal1", 4.24, 0.98, 4.335, 1.25},
    {"metal1", 4.265, 0.4, 4.335, 1.25},
};

inline constexpr RectSpec kNangateSDFFSX1PinQN[] = {
    {"metal1", 4.62, 0.98, 4.705, 1.25},
    {"metal1", 4.635, 0.15, 4.705, 1.25},
};

inline constexpr RectSpec kNangateSDFFSX1Power[] = {
    {"metal1", 0.0, 1.315, 4.75, 1.485},
    {"metal1", 4.445, 0.975, 4.515, 1.485},
    {"metal1", 4.105, 0.975, 4.175, 1.485},
    {"metal1", 3.735, 1.07, 3.805, 1.485},
    {"metal1", 2.83, 1.07, 2.9, 1.485},
    {"metal1", 2.3, 1.155, 2.37, 1.485},
    {"metal1", 1.52, 1.04, 1.59, 1.485},
    {"metal1", 0.985, 1.045, 1.055, 1.485},
    {"metal1", 0.225, 1.035, 0.295, 1.485},
};

inline constexpr RectSpec kNangateSDFFSX1Ground[] = {
    {"metal1", 0.0, -0.085, 4.75, 0.085},
    {"metal1", 4.445, -0.085, 4.515, 0.195},
    {"metal1", 3.735, -0.085, 3.805, 0.32},
    {"metal1", 2.805, -0.085, 2.94, 0.285},
    {"metal1", 2.485, -0.085, 2.555, 0.37},
    {"metal1", 1.49, -0.085, 1.625, 0.215},
    {"metal1", 0.985, -0.085, 1.055, 0.285},
    {"metal1", 0.225, -0.085, 0.295, 0.285},
};

inline constexpr RectSpec kNangateSDFFSX1ObsGroup0[] = {
    {"metal1", 3.915, 0.775, 3.985, 1.25, true},
    {"metal1", 3.69, 0.775, 3.985, 0.915, true},
    {"metal1", 3.69, 0.775, 4.2, 0.845, true},
    {"metal1", 4.13, 0.265, 4.2, 0.845, true},
    {"metal1", 4.495, 0.265, 4.565, 0.66, true},
    {"metal1", 4.075, 0.265, 4.565, 0.335, true},
};

inline constexpr RectSpec kNangateSDFFSX1ObsGroup1[] = {
    {"metal1", 3.255, 1.1, 3.625, 1.17, true},
    {"metal1", 3.555, 0.215, 3.625, 1.17, true},
    {"metal1", 3.555, 0.64, 4.065, 0.71, true},
    {"metal1", 3.995, 0.525, 4.065, 0.71, true},
    {"metal1", 3.25, 0.215, 3.625, 0.285, true},
};

inline constexpr RectSpec kNangateSDFFSX1ObsGroup2[] = {
    {"metal1", 2.615, 0.93, 3.49, 1.0, true},
    {"metal1", 3.42, 0.35, 3.49, 1.0, true},
    {"metal1", 2.615, 0.805, 2.685, 1.0, true},
    {"metal1", 2.225, 0.805, 2.685, 0.875, true},
    {"metal1", 2.65, 0.35, 3.49, 0.42, true},
    {"metal1", 2.65, 0.2, 2.72, 0.42, true},
};

inline constexpr RectSpec kNangateSDFFSX1ObsGroup3[] = {
    {"metal1", 1.34, 0.905, 1.41, 1.25, true},
    {"metal1", 1.34, 0.905, 1.865, 0.975, true},
    {"metal1", 1.795, 0.74, 1.865, 0.975, true},
    {"metal1", 3.285, 0.485, 3.355, 0.86, true},
    {"metal1", 1.795, 0.74, 2.025, 0.81, true},
    {"metal1", 1.955, 0.42, 2.025, 0.81, true},
    {"metal1", 2.225, 0.485, 3.355, 0.555, true},
    {"metal1", 1.74, 0.42, 2.025, 0.49, true},
    {"metal1", 2.225, 0.15, 2.295, 0.555, true},
    {"metal1", 1.74, 0.15, 1.81, 0.49, true},
    {"metal1", 1.34, 0.28, 1.81, 0.35, true},
    {"metal1", 1.34, 0.15, 1.41, 0.35, true},
    {"metal1", 1.74, 0.15, 2.295, 0.22, true},
};

inline constexpr RectSpec kNangateSDFFSX1ObsGroup4[] = {
    {"metal1", 1.87, 1.17, 2.005, 1.24, true},
    {"metal1", 1.935, 0.88, 2.005, 1.24, true},
    {"metal1", 1.935, 0.88, 2.16, 0.95, true},
    {"metal1", 2.09, 0.285, 2.16, 0.95, true},
    {"metal1", 2.09, 0.665, 2.945, 0.735, true},
    {"metal1", 1.875, 0.285, 2.16, 0.355, true},
};

inline constexpr RectSpec kNangateSDFFSX1ObsGroup5[] = {
    {"metal1", 2.455, 1.17, 2.59, 1.24, true},
    {"metal1", 2.07, 1.17, 2.205, 1.24, true},
    {"metal1", 2.135, 1.02, 2.205, 1.24, true},
    {"metal1", 2.455, 1.02, 2.525, 1.24, true},
    {"metal1", 2.135, 1.02, 2.525, 1.09, true},
};

inline constexpr RectSpec kNangateSDFFSX1ObsGroup6[] = {
    {"metal1", 1.18, 0.77, 1.25, 1.25, true},
    {"metal1", 1.18, 0.77, 1.675, 0.84, true},
    {"metal1", 1.605, 0.415, 1.675, 0.84, true},
    {"metal1", 1.605, 0.6, 1.89, 0.67, true},
    {"metal1", 1.18, 0.415, 1.675, 0.485, true},
    {"metal1", 1.18, 0.15, 1.25, 0.485, true},
};

inline constexpr RectSpec kNangateSDFFSX1ObsGroup7[] = {
    {"metal1", 0.58, 1.035, 0.715, 1.24, true},
    {"metal1", 0.58, 1.035, 0.9, 1.105, true},
    {"metal1", 0.83, 0.625, 0.9, 1.105, true},
    {"metal1", 0.775, 0.625, 1.54, 0.695, true},
    {"metal1", 0.775, 0.15, 0.845, 0.695, true},
    {"metal1", 0.615, 0.15, 0.845, 0.285, true},
};

inline constexpr RectSpec kNangateSDFFSX1ObsGroup8[] = {
    {"metal1", 0.045, 0.9, 0.115, 1.25, true},
    {"metal1", 0.045, 0.9, 0.765, 0.97, true},
    {"metal1", 0.635, 0.835, 0.765, 0.97, true},
    {"metal1", 0.635, 0.415, 0.705, 0.97, true},
    {"metal1", 0.045, 0.415, 0.705, 0.485, true},
    {"metal1", 0.045, 0.15, 0.115, 0.485, true},
};

inline constexpr GroupSpec kNangateSDFFSX1Groups[] = {
    {BindingKind::kPinNet, "D", kNangateSDFFSX1PinD, std::size(kNangateSDFFSX1PinD)},
    {BindingKind::kPinNet, "SE", kNangateSDFFSX1PinSE, std::size(kNangateSDFFSX1PinSE)},
    {BindingKind::kPinNet, "SI", kNangateSDFFSX1PinSI, std::size(kNangateSDFFSX1PinSI)},
    {BindingKind::kPinNet, "SN", kNangateSDFFSX1PinSN, std::size(kNangateSDFFSX1PinSN)},
    {BindingKind::kPinNet, "CK", kNangateSDFFSX1PinCK, std::size(kNangateSDFFSX1PinCK)},
    {BindingKind::kPinNet, "Q", kNangateSDFFSX1PinQ, std::size(kNangateSDFFSX1PinQ)},
    {BindingKind::kPinNet, "QN", kNangateSDFFSX1PinQN, std::size(kNangateSDFFSX1PinQN)},
    {BindingKind::kSupplyNet, "POWER", kNangateSDFFSX1Power, std::size(kNangateSDFFSX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateSDFFSX1Ground, std::size(kNangateSDFFSX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateSDFFSX1ObsGroup0, std::size(kNangateSDFFSX1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateSDFFSX1ObsGroup1, std::size(kNangateSDFFSX1ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateSDFFSX1ObsGroup2, std::size(kNangateSDFFSX1ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateSDFFSX1ObsGroup3, std::size(kNangateSDFFSX1ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateSDFFSX1ObsGroup4, std::size(kNangateSDFFSX1ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateSDFFSX1ObsGroup5, std::size(kNangateSDFFSX1ObsGroup5)},
    {BindingKind::kSyntheticNet, "OBS6", kNangateSDFFSX1ObsGroup6, std::size(kNangateSDFFSX1ObsGroup6)},
    {BindingKind::kSyntheticNet, "OBS7", kNangateSDFFSX1ObsGroup7, std::size(kNangateSDFFSX1ObsGroup7)},
    {BindingKind::kSyntheticNet, "OBS8", kNangateSDFFSX1ObsGroup8, std::size(kNangateSDFFSX1ObsGroup8)},
};

inline constexpr RectSpec kNangateSDFFSX2PinD[] = {
    {"metal1", 0.25, 0.67, 0.375, 0.84},
};

inline constexpr RectSpec kNangateSDFFSX2PinSE[] = {
    {"metal1", 0.06, 0.91, 0.595, 0.98},
    {"metal1", 0.525, 0.67, 0.595, 0.98},
    {"metal1", 0.06, 0.795, 0.185, 0.98},
};

inline constexpr RectSpec kNangateSDFFSX2PinSI[] = {
    {"metal1", 0.965, 0.42, 1.08, 0.64},
};

inline constexpr RectSpec kNangateSDFFSX2PinSN[] = {
    {"metal1", 3.34, 0.56, 4.03, 0.63},
    {"metal1", 3.34, 0.28, 3.41, 0.63},
    {"metal1", 2.91, 0.28, 3.41, 0.35},
    {"metal1", 2.42, 0.425, 2.98, 0.495},
    {"metal1", 2.91, 0.28, 2.98, 0.495},
};

inline constexpr RectSpec kNangateSDFFSX2PinCK[] = {
    {"metal1", 1.01, 0.84, 1.13, 0.98},
};

inline constexpr RectSpec kNangateSDFFSX2PinQ[] = {
    {"metal1", 4.43, 0.395, 4.5, 0.785},
};

inline constexpr RectSpec kNangateSDFFSX2PinQN[] = {
    {"metal1", 4.81, 0.395, 4.88, 0.785},
};

inline constexpr RectSpec kNangateSDFFSX2Power[] = {
    {"metal1", 0.0, 1.315, 5.13, 1.485},
    {"metal1", 4.99, 1.125, 5.06, 1.485},
    {"metal1", 4.58, 1.15, 4.715, 1.485},
    {"metal1", 4.2, 1.15, 4.335, 1.485},
    {"metal1", 3.825, 1.15, 3.96, 1.485},
    {"metal1", 3.51, 1.12, 3.58, 1.485},
    {"metal1", 2.64, 1.03, 2.71, 1.485},
    {"metal1", 2.265, 1.165, 2.4, 1.485},
    {"metal1", 1.505, 1.24, 1.64, 1.485},
    {"metal1", 0.99, 1.115, 1.06, 1.485},
    {"metal1", 0.195, 1.24, 0.33, 1.485},
};

inline constexpr RectSpec kNangateSDFFSX2Ground[] = {
    {"metal1", 0.0, -0.085, 5.13, 0.085},
    {"metal1", 4.99, -0.085, 5.06, 0.195},
    {"metal1", 4.58, -0.085, 4.715, 0.18},
    {"metal1", 4.2, -0.085, 4.335, 0.18},
    {"metal1", 3.475, -0.085, 3.61, 0.48},
    {"metal1", 2.475, -0.085, 2.61, 0.345},
    {"metal1", 1.51, -0.085, 1.645, 0.345},
    {"metal1", 0.96, -0.085, 1.095, 0.28},
    {"metal1", 0.2, -0.085, 0.335, 0.465},
};

inline constexpr RectSpec kNangateSDFFSX2ObsGroup0[] = {
    {"metal1", 2.91, 1.18, 3.445, 1.25, true},
    {"metal1", 3.375, 0.985, 3.445, 1.25, true},
    {"metal1", 2.91, 0.83, 2.98, 1.25, true},
    {"metal1", 3.375, 0.985, 5.015, 1.055, true},
    {"metal1", 4.945, 0.26, 5.015, 1.055, true},
    {"metal1", 2.26, 0.83, 2.98, 0.965, true},
    {"metal1", 3.69, 0.26, 3.76, 0.495, true},
    {"metal1", 3.69, 0.26, 5.015, 0.33, true},
};

inline constexpr RectSpec kNangateSDFFSX2ObsGroup1[] = {
    {"metal1", 3.375, 0.85, 4.745, 0.92, true},
    {"metal1", 4.675, 0.525, 4.745, 0.92, true},
    {"metal1", 4.295, 0.415, 4.365, 0.92, true},
    {"metal1", 3.825, 0.415, 4.365, 0.485, true},
};

inline constexpr RectSpec kNangateSDFFSX2ObsGroup2[] = {
    {"metal1", 3.045, 1.045, 3.31, 1.115, true},
    {"metal1", 3.24, 0.695, 3.31, 1.115, true},
    {"metal1", 3.24, 0.695, 4.23, 0.765, true},
    {"metal1", 4.095, 0.56, 4.23, 0.765, true},
    {"metal1", 3.205, 0.415, 3.275, 0.76, true},
    {"metal1", 3.045, 0.415, 3.275, 0.485, true},
};

inline constexpr RectSpec kNangateSDFFSX2ObsGroup3[] = {
    {"metal1", 1.355, 1.105, 1.425, 1.25, true},
    {"metal1", 1.355, 1.105, 1.855, 1.175, true},
    {"metal1", 1.785, 0.76, 1.855, 1.175, true},
    {"metal1", 3.07, 0.845, 3.175, 0.98, true},
    {"metal1", 3.07, 0.56, 3.14, 0.98, true},
    {"metal1", 1.785, 0.76, 2.05, 0.83, true},
    {"metal1", 1.98, 0.425, 2.05, 0.83, true},
    {"metal1", 2.285, 0.56, 3.14, 0.63, true},
    {"metal1", 1.98, 0.425, 2.075, 0.575, true},
    {"metal1", 2.285, 0.155, 2.355, 0.63, true},
    {"metal1", 1.355, 0.425, 2.075, 0.495, true},
    {"metal1", 1.75, 0.155, 1.82, 0.495, true},
    {"metal1", 1.355, 0.36, 1.425, 0.495, true},
    {"metal1", 1.75, 0.155, 2.355, 0.225, true},
};

inline constexpr RectSpec kNangateSDFFSX2ObsGroup4[] = {
    {"metal1", 1.925, 0.895, 1.995, 1.25, true},
    {"metal1", 1.925, 0.895, 2.195, 0.965, true},
    {"metal1", 2.125, 0.695, 2.195, 0.965, true},
    {"metal1", 2.125, 0.695, 2.825, 0.765, true},
    {"metal1", 2.15, 0.29, 2.22, 0.765, true},
    {"metal1", 1.895, 0.29, 2.22, 0.36, true},
};

inline constexpr RectSpec kNangateSDFFSX2ObsGroup5[] = {
    {"metal1", 2.485, 1.03, 2.555, 1.25, true},
    {"metal1", 2.115, 1.03, 2.185, 1.25, true},
    {"metal1", 2.115, 1.03, 2.555, 1.1, true},
};

inline constexpr RectSpec kNangateSDFFSX2ObsGroup6[] = {
    {"metal1", 1.195, 0.87, 1.265, 1.25, true},
    {"metal1", 1.195, 0.87, 1.705, 0.94, true},
    {"metal1", 1.635, 0.56, 1.705, 0.94, true},
    {"metal1", 1.635, 0.625, 1.915, 0.695, true},
    {"metal1", 1.195, 0.56, 1.705, 0.63, true},
    {"metal1", 1.195, 0.315, 1.265, 0.63, true},
};

inline constexpr RectSpec kNangateSDFFSX2ObsGroup7[] = {
    {"metal1", 0.585, 1.18, 0.9, 1.25, true},
    {"metal1", 0.83, 0.35, 0.9, 1.25, true},
    {"metal1", 0.83, 0.705, 1.57, 0.775, true},
    {"metal1", 0.585, 0.35, 0.9, 0.42, true},
};

inline constexpr RectSpec kNangateSDFFSX2ObsGroup8[] = {
    {"metal1", 0.045, 1.045, 0.115, 1.25, true},
    {"metal1", 0.045, 1.045, 0.765, 1.115, true},
    {"metal1", 0.695, 0.535, 0.765, 1.115, true},
    {"metal1", 0.045, 0.535, 0.765, 0.605, true},
    {"metal1", 0.045, 0.38, 0.115, 0.605, true},
};

inline constexpr GroupSpec kNangateSDFFSX2Groups[] = {
    {BindingKind::kPinNet, "D", kNangateSDFFSX2PinD, std::size(kNangateSDFFSX2PinD)},
    {BindingKind::kPinNet, "SE", kNangateSDFFSX2PinSE, std::size(kNangateSDFFSX2PinSE)},
    {BindingKind::kPinNet, "SI", kNangateSDFFSX2PinSI, std::size(kNangateSDFFSX2PinSI)},
    {BindingKind::kPinNet, "SN", kNangateSDFFSX2PinSN, std::size(kNangateSDFFSX2PinSN)},
    {BindingKind::kPinNet, "CK", kNangateSDFFSX2PinCK, std::size(kNangateSDFFSX2PinCK)},
    {BindingKind::kPinNet, "Q", kNangateSDFFSX2PinQ, std::size(kNangateSDFFSX2PinQ)},
    {BindingKind::kPinNet, "QN", kNangateSDFFSX2PinQN, std::size(kNangateSDFFSX2PinQN)},
    {BindingKind::kSupplyNet, "POWER", kNangateSDFFSX2Power, std::size(kNangateSDFFSX2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateSDFFSX2Ground, std::size(kNangateSDFFSX2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateSDFFSX2ObsGroup0, std::size(kNangateSDFFSX2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateSDFFSX2ObsGroup1, std::size(kNangateSDFFSX2ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateSDFFSX2ObsGroup2, std::size(kNangateSDFFSX2ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateSDFFSX2ObsGroup3, std::size(kNangateSDFFSX2ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateSDFFSX2ObsGroup4, std::size(kNangateSDFFSX2ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateSDFFSX2ObsGroup5, std::size(kNangateSDFFSX2ObsGroup5)},
    {BindingKind::kSyntheticNet, "OBS6", kNangateSDFFSX2ObsGroup6, std::size(kNangateSDFFSX2ObsGroup6)},
    {BindingKind::kSyntheticNet, "OBS7", kNangateSDFFSX2ObsGroup7, std::size(kNangateSDFFSX2ObsGroup7)},
    {BindingKind::kSyntheticNet, "OBS8", kNangateSDFFSX2ObsGroup8, std::size(kNangateSDFFSX2ObsGroup8)},
};

inline constexpr RectSpec kNangateSDFFX1PinD[] = {
    {"metal1", 3.975, 0.42, 4.125, 0.565},
};

inline constexpr RectSpec kNangateSDFFX1PinSE[] = {
    {"metal1", 4.05, 0.7, 4.18, 0.84},
    {"metal1", 3.75, 0.7, 4.18, 0.77},
    {"metal1", 3.75, 0.59, 3.885, 0.77},
};

inline constexpr RectSpec kNangateSDFFX1PinSI[] = {
    {"metal1", 3.415, 0.525, 3.55, 0.7},
};

inline constexpr RectSpec kNangateSDFFX1PinCK[] = {
    {"metal1", 2.02, 0.42, 2.225, 0.58},
};

inline constexpr RectSpec kNangateSDFFX1PinQ[] = {
    {"metal1", 0.44, 0.15, 0.51, 0.785},
};

inline constexpr RectSpec kNangateSDFFX1PinQN[] = {
    {"metal1", 0.06, 0.15, 0.135, 1.215},
};

inline constexpr RectSpec kNangateSDFFX1Power[] = {
    {"metal1", 0.0, 1.315, 4.37, 1.485},
    {"metal1", 4.02, 0.975, 4.155, 1.485},
    {"metal1", 3.295, 1.04, 3.365, 1.485},
    {"metal1", 2.935, 1.08, 3.005, 1.485},
    {"metal1", 2.07, 0.94, 2.14, 1.485},
    {"metal1", 1.51, 0.975, 1.645, 1.485},
    {"metal1", 0.75, 1.165, 0.885, 1.485},
    {"metal1", 0.25, 1.04, 0.32, 1.485},
};

inline constexpr RectSpec kNangateSDFFX1Ground[] = {
    {"metal1", 0.0, -0.085, 4.37, 0.085},
    {"metal1", 4.02, -0.085, 4.155, 0.16},
    {"metal1", 3.295, -0.085, 3.365, 0.195},
    {"metal1", 2.905, -0.085, 3.04, 0.19},
    {"metal1", 2.04, -0.085, 2.175, 0.285},
    {"metal1", 1.51, -0.085, 1.645, 0.285},
    {"metal1", 0.75, -0.085, 0.885, 0.285},
    {"metal1", 0.25, -0.085, 0.32, 0.425},
};

inline constexpr RectSpec kNangateSDFFX1ObsGroup0[] = {
    {"metal1", 4.245, 0.15, 4.315, 1.215, true},
    {"metal1", 3.615, 0.45, 3.685, 0.84, true},
    {"metal1", 3.615, 0.45, 3.88, 0.52, true},
    {"metal1", 3.81, 0.28, 3.88, 0.52, true},
    {"metal1", 3.81, 0.28, 4.315, 0.35, true},
};

inline constexpr RectSpec kNangateSDFFX1ObsGroup1[] = {
    {"metal1", 3.67, 0.905, 3.74, 1.215, true},
    {"metal1", 3.28, 0.905, 3.74, 0.975, true},
    {"metal1", 3.28, 0.285, 3.35, 0.975, true},
    {"metal1", 2.9, 0.695, 3.35, 0.83, true},
    {"metal1", 3.28, 0.285, 3.74, 0.355, true},
    {"metal1", 3.67, 0.15, 3.74, 0.355, true},
};

inline constexpr RectSpec kNangateSDFFX1ObsGroup2[] = {
    {"metal1", 3.125, 0.92, 3.195, 1.215, true},
    {"metal1", 2.205, 1.14, 2.835, 1.21, true},
    {"metal1", 2.765, 0.545, 2.835, 1.21, true},
    {"metal1", 2.205, 0.815, 2.275, 1.21, true},
    {"metal1", 2.765, 0.92, 3.195, 0.99, true},
    {"metal1", 2.765, 0.545, 3.215, 0.615, true},
    {"metal1", 3.145, 0.15, 3.215, 0.615, true},
};

inline constexpr RectSpec kNangateSDFFX1ObsGroup3[] = {
    {"metal1", 2.53, 0.975, 2.7, 1.045, true},
    {"metal1", 2.63, 0.215, 2.7, 1.045, true},
    {"metal1", 2.63, 0.325, 3.08, 0.46, true},
    {"metal1", 2.53, 0.215, 2.7, 0.285, true},
};

inline constexpr RectSpec kNangateSDFFX1ObsGroup4[] = {
    {"metal1", 1.885, 0.2, 1.955, 1.09, true},
    {"metal1", 2.37, 0.68, 2.44, 0.95, true},
    {"metal1", 1.885, 0.68, 2.565, 0.75, true},
    {"metal1", 2.495, 0.35, 2.565, 0.75, true},
    {"metal1", 1.26, 0.65, 1.955, 0.72, true},
};

inline constexpr RectSpec kNangateSDFFX1ObsGroup5[] = {
    {"metal1", 1.73, 0.84, 1.8, 1.215, true},
    {"metal1", 1.125, 0.84, 1.8, 0.91, true},
    {"metal1", 1.125, 0.475, 1.195, 0.91, true},
    {"metal1", 1.125, 0.475, 1.8, 0.545, true},
    {"metal1", 1.73, 0.32, 1.8, 0.545, true},
};

inline constexpr RectSpec kNangateSDFFX1ObsGroup6[] = {
    {"metal1", 0.99, 1.15, 1.265, 1.22, true},
    {"metal1", 0.99, 0.23, 1.06, 1.22, true},
    {"metal1", 0.73, 0.525, 1.06, 0.66, true},
    {"metal1", 0.99, 0.23, 1.265, 0.3, true},
};

inline constexpr RectSpec kNangateSDFFX1ObsGroup7[] = {
    {"metal1", 0.595, 0.15, 0.665, 1.215, true},
    {"metal1", 0.2, 0.885, 0.665, 0.955, true},
    {"metal1", 0.2, 0.51, 0.27, 0.955, true},
    {"metal1", 0.595, 0.73, 0.925, 0.865, true},
};

inline constexpr GroupSpec kNangateSDFFX1Groups[] = {
    {BindingKind::kPinNet, "D", kNangateSDFFX1PinD, std::size(kNangateSDFFX1PinD)},
    {BindingKind::kPinNet, "SE", kNangateSDFFX1PinSE, std::size(kNangateSDFFX1PinSE)},
    {BindingKind::kPinNet, "SI", kNangateSDFFX1PinSI, std::size(kNangateSDFFX1PinSI)},
    {BindingKind::kPinNet, "CK", kNangateSDFFX1PinCK, std::size(kNangateSDFFX1PinCK)},
    {BindingKind::kPinNet, "Q", kNangateSDFFX1PinQ, std::size(kNangateSDFFX1PinQ)},
    {BindingKind::kPinNet, "QN", kNangateSDFFX1PinQN, std::size(kNangateSDFFX1PinQN)},
    {BindingKind::kSupplyNet, "POWER", kNangateSDFFX1Power, std::size(kNangateSDFFX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateSDFFX1Ground, std::size(kNangateSDFFX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateSDFFX1ObsGroup0, std::size(kNangateSDFFX1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateSDFFX1ObsGroup1, std::size(kNangateSDFFX1ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateSDFFX1ObsGroup2, std::size(kNangateSDFFX1ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateSDFFX1ObsGroup3, std::size(kNangateSDFFX1ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateSDFFX1ObsGroup4, std::size(kNangateSDFFX1ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateSDFFX1ObsGroup5, std::size(kNangateSDFFX1ObsGroup5)},
    {BindingKind::kSyntheticNet, "OBS6", kNangateSDFFX1ObsGroup6, std::size(kNangateSDFFX1ObsGroup6)},
    {BindingKind::kSyntheticNet, "OBS7", kNangateSDFFX1ObsGroup7, std::size(kNangateSDFFX1ObsGroup7)},
};

inline constexpr RectSpec kNangateSDFFX2PinD[] = {
    {"metal1", 4.165, 0.42, 4.33, 0.56},
};

inline constexpr RectSpec kNangateSDFFX2PinSE[] = {
    {"metal1", 3.95, 0.7, 4.355, 0.84},
    {"metal1", 3.95, 0.595, 4.02, 0.84},
};

inline constexpr RectSpec kNangateSDFFX2PinSI[] = {
    {"metal1", 3.48, 0.42, 3.58, 0.56},
};

inline constexpr RectSpec kNangateSDFFX2PinCK[] = {
    {"metal1", 2.225, 0.42, 2.41, 0.58},
};

inline constexpr RectSpec kNangateSDFFX2PinQ[] = {
    {"metal1", 0.425, 0.4, 0.51, 0.785},
};

inline constexpr RectSpec kNangateSDFFX2PinQN[] = {
    {"metal1", 0.805, 0.185, 0.89, 0.84},
};

inline constexpr RectSpec kNangateSDFFX2Power[] = {
    {"metal1", 0.0, 1.315, 4.56, 1.485},
    {"metal1", 4.24, 0.965, 4.31, 1.485},
    {"metal1", 3.455, 1.24, 3.59, 1.485},
    {"metal1", 3.135, 1.08, 3.205, 1.485},
    {"metal1", 2.275, 0.91, 2.345, 1.485},
    {"metal1", 1.745, 0.94, 1.815, 1.485},
    {"metal1", 0.985, 1.04, 1.055, 1.485},
    {"metal1", 0.605, 1.04, 0.675, 1.485},
    {"metal1", 0.225, 1.04, 0.295, 1.485},
};

inline constexpr RectSpec kNangateSDFFX2Ground[] = {
    {"metal1", 0.0, -0.085, 4.56, 0.085},
    {"metal1", 4.21, -0.085, 4.345, 0.16},
    {"metal1", 3.485, -0.085, 3.555, 0.255},
    {"metal1", 3.065, -0.085, 3.2, 0.165},
    {"metal1", 2.275, -0.085, 2.345, 0.32},
    {"metal1", 1.745, -0.085, 1.815, 0.32},
    {"metal1", 0.985, -0.085, 1.055, 0.32},
    {"metal1", 0.605, -0.085, 0.675, 0.195},
    {"metal1", 0.225, -0.085, 0.295, 0.195},
};

inline constexpr RectSpec kNangateSDFFX2ObsGroup0[] = {
    {"metal1", 4.43, 0.195, 4.5, 1.24, true},
    {"metal1", 3.78, 0.42, 3.85, 0.895, true},
    {"metal1", 3.78, 0.42, 4.05, 0.49, true},
    {"metal1", 3.98, 0.285, 4.05, 0.49, true},
    {"metal1", 3.98, 0.285, 4.5, 0.355, true},
};

inline constexpr RectSpec kNangateSDFFX2ObsGroup1[] = {
    {"metal1", 3.86, 0.96, 3.93, 1.24, true},
    {"metal1", 3.645, 0.96, 3.93, 1.03, true},
    {"metal1", 3.645, 0.15, 3.715, 1.03, true},
    {"metal1", 3.105, 0.64, 3.715, 0.775, true},
    {"metal1", 3.645, 0.15, 3.965, 0.22, true},
};

inline constexpr RectSpec kNangateSDFFX2ObsGroup2[] = {
    {"metal1", 3.33, 0.89, 3.4, 1.185, true},
    {"metal1", 2.41, 1.11, 3.04, 1.18, true},
    {"metal1", 2.97, 0.505, 3.04, 1.18, true},
    {"metal1", 2.41, 0.785, 2.48, 1.18, true},
    {"metal1", 2.97, 0.89, 3.4, 0.96, true},
    {"metal1", 2.97, 0.505, 3.405, 0.575, true},
    {"metal1", 3.335, 0.185, 3.405, 0.575, true},
};

inline constexpr RectSpec kNangateSDFFX2ObsGroup3[] = {
    {"metal1", 2.63, 0.945, 2.905, 1.015, true},
    {"metal1", 2.835, 0.215, 2.905, 1.015, true},
    {"metal1", 2.835, 0.37, 3.27, 0.44, true},
    {"metal1", 2.635, 0.215, 2.905, 0.285, true},
};

inline constexpr RectSpec kNangateSDFFX2ObsGroup4[] = {
    {"metal1", 2.09, 0.185, 2.16, 1.185, true},
    {"metal1", 2.575, 0.65, 2.645, 0.88, true},
    {"metal1", 2.09, 0.65, 2.77, 0.72, true},
    {"metal1", 2.7, 0.35, 2.77, 0.72, true},
    {"metal1", 1.42, 0.63, 2.16, 0.7, true},
};

inline constexpr RectSpec kNangateSDFFX2ObsGroup5[] = {
    {"metal1", 1.935, 0.79, 2.005, 1.185, true},
    {"metal1", 1.265, 0.475, 1.335, 0.985, true},
    {"metal1", 1.265, 0.79, 2.005, 0.86, true},
    {"metal1", 1.265, 0.475, 2.005, 0.545, true},
    {"metal1", 1.935, 0.185, 2.005, 0.545, true},
};

inline constexpr RectSpec kNangateSDFFX2ObsGroup6[] = {
    {"metal1", 1.13, 1.055, 1.47, 1.125, true},
    {"metal1", 1.13, 0.22, 1.2, 1.125, true},
    {"metal1", 0.29, 0.905, 1.2, 0.975, true},
    {"metal1", 0.29, 0.525, 0.36, 0.975, true},
    {"metal1", 1.13, 0.22, 1.47, 0.29, true},
};

inline constexpr RectSpec kNangateSDFFX2ObsGroup7[] = {
    {"metal1", 0.045, 0.185, 0.115, 1.185, true},
    {"metal1", 0.67, 0.265, 0.74, 0.66, true},
    {"metal1", 0.045, 0.265, 0.74, 0.335, true},
};

inline constexpr GroupSpec kNangateSDFFX2Groups[] = {
    {BindingKind::kPinNet, "D", kNangateSDFFX2PinD, std::size(kNangateSDFFX2PinD)},
    {BindingKind::kPinNet, "SE", kNangateSDFFX2PinSE, std::size(kNangateSDFFX2PinSE)},
    {BindingKind::kPinNet, "SI", kNangateSDFFX2PinSI, std::size(kNangateSDFFX2PinSI)},
    {BindingKind::kPinNet, "CK", kNangateSDFFX2PinCK, std::size(kNangateSDFFX2PinCK)},
    {BindingKind::kPinNet, "Q", kNangateSDFFX2PinQ, std::size(kNangateSDFFX2PinQ)},
    {BindingKind::kPinNet, "QN", kNangateSDFFX2PinQN, std::size(kNangateSDFFX2PinQN)},
    {BindingKind::kSupplyNet, "POWER", kNangateSDFFX2Power, std::size(kNangateSDFFX2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateSDFFX2Ground, std::size(kNangateSDFFX2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateSDFFX2ObsGroup0, std::size(kNangateSDFFX2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateSDFFX2ObsGroup1, std::size(kNangateSDFFX2ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateSDFFX2ObsGroup2, std::size(kNangateSDFFX2ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateSDFFX2ObsGroup3, std::size(kNangateSDFFX2ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateSDFFX2ObsGroup4, std::size(kNangateSDFFX2ObsGroup4)},
    {BindingKind::kSyntheticNet, "OBS5", kNangateSDFFX2ObsGroup5, std::size(kNangateSDFFX2ObsGroup5)},
    {BindingKind::kSyntheticNet, "OBS6", kNangateSDFFX2ObsGroup6, std::size(kNangateSDFFX2ObsGroup6)},
    {BindingKind::kSyntheticNet, "OBS7", kNangateSDFFX2ObsGroup7, std::size(kNangateSDFFX2ObsGroup7)},
};

inline constexpr RectSpec kNangateTBUFX1PinA[] = {
    {"metal1", 0.82, 0.495, 0.89, 0.73},
    {"metal1", 0.51, 0.495, 0.89, 0.565},
    {"metal1", 0.51, 0.495, 0.58, 0.63},
};

inline constexpr RectSpec kNangateTBUFX1PinEN[] = {
    {"metal1", 1.2, 0.695, 1.33, 0.92},
};

inline constexpr RectSpec kNangateTBUFX1PinZ[] = {
    {"metal1", 0.035, 0.97, 0.14, 1.245},
    {"metal1", 0.035, 0.15, 0.14, 0.425},
    {"metal1", 0.035, 0.15, 0.105, 1.245},
};

inline constexpr RectSpec kNangateTBUFX1Power[] = {
    {"metal1", 0.0, 1.315, 1.52, 1.485},
    {"metal1", 1.19, 1.24, 1.325, 1.485},
    {"metal1", 0.69, 1.145, 0.76, 1.485},
    {"metal1", 0.225, 1.145, 0.36, 1.485},
};

inline constexpr RectSpec kNangateTBUFX1Ground[] = {
    {"metal1", 0.0, -0.085, 1.52, 0.085},
    {"metal1", 1.15, -0.085, 1.285, 0.295},
    {"metal1", 0.77, -0.085, 0.905, 0.295},
    {"metal1", 0.225, -0.085, 0.36, 0.16},
};

inline constexpr RectSpec kNangateTBUFX1ObsGroup0[] = {
    {"metal1", 1.41, 0.365, 1.48, 1.245, true},
    {"metal1", 0.875, 1.105, 1.48, 1.175, true},
    {"metal1", 0.875, 0.94, 0.945, 1.175, true},
    {"metal1", 0.65, 0.94, 0.945, 1.01, true},
    {"metal1", 0.65, 0.645, 0.72, 1.01, true},
    {"metal1", 1.345, 0.365, 1.48, 0.435, true},
};

inline constexpr RectSpec kNangateTBUFX1ObsGroup1[] = {
    {"metal1", 1.065, 0.36, 1.135, 1.04, true},
    {"metal1", 0.17, 0.495, 0.305, 0.565, true},
    {"metal1", 0.235, 0.225, 0.305, 0.565, true},
    {"metal1", 0.615, 0.36, 1.135, 0.43, true},
    {"metal1", 0.615, 0.225, 0.685, 0.43, true},
    {"metal1", 0.235, 0.225, 0.685, 0.295, true},
};

inline constexpr RectSpec kNangateTBUFX1ObsGroup2[] = {
    {"metal1", 0.495, 0.835, 0.565, 1.115, true},
    {"metal1", 0.37, 0.835, 0.565, 0.905, true},
    {"metal1", 0.37, 0.36, 0.44, 0.905, true},
    {"metal1", 0.17, 0.645, 0.44, 0.715, true},
    {"metal1", 0.37, 0.36, 0.53, 0.43, true},
};

inline constexpr GroupSpec kNangateTBUFX1Groups[] = {
    {BindingKind::kPinNet, "A", kNangateTBUFX1PinA, std::size(kNangateTBUFX1PinA)},
    {BindingKind::kPinNet, "EN", kNangateTBUFX1PinEN, std::size(kNangateTBUFX1PinEN)},
    {BindingKind::kPinNet, "Z", kNangateTBUFX1PinZ, std::size(kNangateTBUFX1PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateTBUFX1Power, std::size(kNangateTBUFX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateTBUFX1Ground, std::size(kNangateTBUFX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateTBUFX1ObsGroup0, std::size(kNangateTBUFX1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateTBUFX1ObsGroup1, std::size(kNangateTBUFX1ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateTBUFX1ObsGroup2, std::size(kNangateTBUFX1ObsGroup2)},
};

inline constexpr RectSpec kNangateTBUFX16PinA[] = {
    {"metal1", 4.265, 0.39, 4.335, 0.66},
    {"metal1", 3.67, 0.39, 4.335, 0.46},
    {"metal1", 3.475, 0.555, 3.74, 0.625},
    {"metal1", 3.67, 0.39, 3.74, 0.625},
};

inline constexpr RectSpec kNangateTBUFX16PinEN[] = {
    {"metal1", 4.05, 0.725, 4.6, 0.795},
    {"metal1", 4.53, 0.525, 4.6, 0.795},
    {"metal1", 4.05, 0.56, 4.12, 0.795},
    {"metal1", 3.955, 0.56, 4.12, 0.63},
};

inline constexpr RectSpec kNangateTBUFX16PinZ[] = {
    {"metal1", 2.895, 0.36, 3.03, 1.005},
    {"metal1", 0.36, 0.56, 3.03, 0.7},
    {"metal1", 2.515, 0.36, 2.65, 1.005},
    {"metal1", 2.14, 0.56, 2.275, 1.005},
    {"metal1", 2.135, 0.36, 2.27, 0.7},
    {"metal1", 1.76, 0.36, 1.895, 0.7},
    {"metal1", 1.755, 0.56, 1.89, 1.005},
    {"metal1", 1.38, 0.56, 1.515, 1.005},
    {"metal1", 1.375, 0.36, 1.51, 0.7},
    {"metal1", 1.0, 0.36, 1.135, 0.7},
    {"metal1", 0.995, 0.56, 1.13, 1.005},
    {"metal1", 0.62, 0.36, 0.755, 1.005},
    {"metal1", 0.24, 0.86, 0.43, 0.93},
    {"metal1", 0.36, 0.36, 0.43, 0.93},
    {"metal1", 0.24, 0.36, 0.43, 0.43},
};

inline constexpr RectSpec kNangateTBUFX16Power[] = {
    {"metal1", 0.0, 1.315, 4.94, 1.485},
    {"metal1", 4.605, 1.24, 4.74, 1.485},
    {"metal1", 3.845, 1.24, 3.98, 1.485},
    {"metal1", 3.465, 1.24, 3.6, 1.485},
    {"metal1", 3.085, 1.24, 3.22, 1.485},
    {"metal1", 2.705, 1.24, 2.84, 1.485},
    {"metal1", 2.325, 1.24, 2.46, 1.485},
    {"metal1", 1.945, 1.24, 2.08, 1.485},
    {"metal1", 1.565, 1.24, 1.7, 1.485},
    {"metal1", 1.185, 1.24, 1.32, 1.485},
    {"metal1", 0.805, 1.24, 0.94, 1.485},
    {"metal1", 0.425, 1.24, 0.56, 1.485},
    {"metal1", 0.05, 1.24, 0.185, 1.485},
};

inline constexpr RectSpec kNangateTBUFX16Ground[] = {
    {"metal1", 0.0, -0.085, 4.94, 0.085},
    {"metal1", 4.605, -0.085, 4.74, 0.16},
    {"metal1", 4.225, -0.085, 4.36, 0.16},
    {"metal1", 3.845, -0.085, 3.98, 0.16},
    {"metal1", 3.085, -0.085, 3.22, 0.16},
    {"metal1", 2.705, -0.085, 2.84, 0.16},
    {"metal1", 2.325, -0.085, 2.46, 0.16},
    {"metal1", 1.945, -0.085, 2.08, 0.16},
    {"metal1", 1.565, -0.085, 1.7, 0.16},
    {"metal1", 1.185, -0.085, 1.32, 0.16},
    {"metal1", 0.805, -0.085, 0.94, 0.16},
    {"metal1", 0.425, -0.085, 0.56, 0.16},
    {"metal1", 0.05, -0.085, 0.185, 0.16},
};

inline constexpr RectSpec kNangateTBUFX16ObsGroup0[] = {
    {"metal1", 4.825, 0.26, 4.895, 1.25, true},
    {"metal1", 3.86, 0.995, 4.895, 1.065, true},
    {"metal1", 3.86, 0.83, 3.93, 1.065, true},
    {"metal1", 3.23, 0.83, 3.93, 0.9, true},
    {"metal1", 3.805, 0.525, 3.875, 0.9, true},
    {"metal1", 3.23, 0.525, 3.3, 0.9, true},
};

inline constexpr RectSpec kNangateTBUFX16ObsGroup1[] = {
    {"metal1", 4.23, 0.86, 4.735, 0.93, true},
    {"metal1", 4.665, 0.225, 4.735, 0.93, true},
    {"metal1", 0.105, 0.495, 0.29, 0.565, true},
    {"metal1", 0.105, 0.225, 0.175, 0.565, true},
    {"metal1", 0.105, 0.225, 4.735, 0.295, true},
};

inline constexpr RectSpec kNangateTBUFX16ObsGroup2[] = {
    {"metal1", 0.105, 1.085, 3.79, 1.155, true},
    {"metal1", 3.095, 0.36, 3.165, 1.155, true},
    {"metal1", 0.105, 0.65, 0.175, 1.155, true},
    {"metal1", 0.105, 0.65, 0.295, 0.72, true},
    {"metal1", 3.095, 0.36, 3.6, 0.43, true},
};

inline constexpr GroupSpec kNangateTBUFX16Groups[] = {
    {BindingKind::kPinNet, "A", kNangateTBUFX16PinA, std::size(kNangateTBUFX16PinA)},
    {BindingKind::kPinNet, "EN", kNangateTBUFX16PinEN, std::size(kNangateTBUFX16PinEN)},
    {BindingKind::kPinNet, "Z", kNangateTBUFX16PinZ, std::size(kNangateTBUFX16PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateTBUFX16Power, std::size(kNangateTBUFX16Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateTBUFX16Ground, std::size(kNangateTBUFX16Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateTBUFX16ObsGroup0, std::size(kNangateTBUFX16ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateTBUFX16ObsGroup1, std::size(kNangateTBUFX16ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateTBUFX16ObsGroup2, std::size(kNangateTBUFX16ObsGroup2)},
};

inline constexpr RectSpec kNangateTBUFX2PinA[] = {
    {"metal1", 0.82, 0.56, 0.965, 0.7},
};

inline constexpr RectSpec kNangateTBUFX2PinEN[] = {
    {"metal1", 1.2, 0.7, 1.535, 0.84},
    {"metal1", 1.2, 0.285, 1.27, 0.84},
    {"metal1", 0.685, 0.285, 1.27, 0.355},
    {"metal1", 0.685, 0.285, 0.755, 0.66},
};

inline constexpr RectSpec kNangateTBUFX2PinZ[] = {
    {"metal1", 0.06, 0.8, 0.335, 0.87},
    {"metal1", 0.06, 0.35, 0.33, 0.42},
    {"metal1", 0.06, 0.35, 0.13, 0.87},
};

inline constexpr RectSpec kNangateTBUFX2Power[] = {
    {"metal1", 0.0, 1.315, 1.71, 1.485},
    {"metal1", 1.39, 1.065, 1.46, 1.485},
    {"metal1", 0.975, 1.065, 1.045, 1.485},
    {"metal1", 0.415, 1.135, 0.485, 1.485},
    {"metal1", 0.04, 0.995, 0.11, 1.485},
};

inline constexpr RectSpec kNangateTBUFX2Ground[] = {
    {"metal1", 0.0, -0.085, 1.71, 0.085},
    {"metal1", 1.405, -0.085, 1.475, 0.25},
    {"metal1", 0.91, -0.085, 0.98, 0.2},
    {"metal1", 0.415, -0.085, 0.485, 0.39},
    {"metal1", 0.04, -0.085, 0.11, 0.25},
};

inline constexpr RectSpec kNangateTBUFX2ObsGroup0[] = {
    {"metal1", 1.6, 0.15, 1.67, 1.25, true},
    {"metal1", 1.335, 0.56, 1.67, 0.63, true},
};

inline constexpr RectSpec kNangateTBUFX2ObsGroup1[] = {
    {"metal1", 0.4, 0.925, 1.27, 0.995, true},
    {"metal1", 1.065, 0.43, 1.135, 0.995, true},
    {"metal1", 0.4, 0.65, 0.47, 0.995, true},
    {"metal1", 0.235, 0.65, 0.47, 0.72, true},
    {"metal1", 1.0, 0.43, 1.135, 0.5, true},
};

inline constexpr RectSpec kNangateTBUFX2ObsGroup2[] = {
    {"metal1", 0.55, 0.725, 0.705, 0.795, true},
    {"metal1", 0.55, 0.15, 0.62, 0.795, true},
    {"metal1", 0.235, 0.495, 0.62, 0.565, true},
    {"metal1", 0.55, 0.15, 0.825, 0.22, true},
};

inline constexpr GroupSpec kNangateTBUFX2Groups[] = {
    {BindingKind::kPinNet, "A", kNangateTBUFX2PinA, std::size(kNangateTBUFX2PinA)},
    {BindingKind::kPinNet, "EN", kNangateTBUFX2PinEN, std::size(kNangateTBUFX2PinEN)},
    {BindingKind::kPinNet, "Z", kNangateTBUFX2PinZ, std::size(kNangateTBUFX2PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateTBUFX2Power, std::size(kNangateTBUFX2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateTBUFX2Ground, std::size(kNangateTBUFX2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateTBUFX2ObsGroup0, std::size(kNangateTBUFX2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateTBUFX2ObsGroup1, std::size(kNangateTBUFX2ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateTBUFX2ObsGroup2, std::size(kNangateTBUFX2ObsGroup2)},
};

inline constexpr RectSpec kNangateTBUFX4PinA[] = {
    {"metal1", 1.35, 0.525, 1.46, 0.7},
};

inline constexpr RectSpec kNangateTBUFX4PinEN[] = {
    {"metal1", 1.75, 0.525, 1.84, 0.7},
};

inline constexpr RectSpec kNangateTBUFX4PinZ[] = {
    {"metal1", 0.235, 1.065, 0.745, 1.135},
    {"metal1", 0.235, 0.33, 0.745, 0.4},
    {"metal1", 0.235, 0.33, 0.32, 1.135},
};

inline constexpr RectSpec kNangateTBUFX4Power[] = {
    {"metal1", 0.0, 1.315, 2.09, 1.485},
    {"metal1", 1.745, 0.86, 1.815, 1.485},
    {"metal1", 1.21, 1.205, 1.28, 1.485},
    {"metal1", 0.83, 1.205, 0.9, 1.485},
    {"metal1", 0.45, 1.205, 0.52, 1.485},
    {"metal1", 0.075, 1.205, 0.145, 1.485},
};

inline constexpr RectSpec kNangateTBUFX4Ground[] = {
    {"metal1", 0.0, -0.085, 2.09, 0.085},
    {"metal1", 1.74, -0.085, 1.81, 0.195},
    {"metal1", 1.365, -0.085, 1.435, 0.195},
    {"metal1", 0.83, -0.085, 0.9, 0.195},
    {"metal1", 0.45, -0.085, 0.52, 0.195},
    {"metal1", 0.075, -0.085, 0.145, 0.335},
};

inline constexpr RectSpec kNangateTBUFX4ObsGroup0[] = {
    {"metal1", 1.935, 0.15, 2.005, 0.995, true},
    {"metal1", 0.945, 0.265, 1.015, 0.66, true},
    {"metal1", 0.945, 0.265, 2.005, 0.335, true},
};

inline constexpr RectSpec kNangateTBUFX4ObsGroup1[] = {
    {"metal1", 1.365, 0.895, 1.435, 1.14, true},
    {"metal1", 0.59, 0.895, 1.63, 0.965, true},
    {"metal1", 1.56, 0.4, 1.63, 0.965, true},
    {"metal1", 0.59, 0.465, 0.66, 0.965, true},
};

inline constexpr RectSpec kNangateTBUFX4ObsGroup2[] = {
    {"metal1", 0.73, 0.725, 1.28, 0.795, true},
    {"metal1", 1.21, 0.4, 1.28, 0.795, true},
    {"metal1", 0.73, 0.615, 0.8, 0.795, true},
};

inline constexpr GroupSpec kNangateTBUFX4Groups[] = {
    {BindingKind::kPinNet, "A", kNangateTBUFX4PinA, std::size(kNangateTBUFX4PinA)},
    {BindingKind::kPinNet, "EN", kNangateTBUFX4PinEN, std::size(kNangateTBUFX4PinEN)},
    {BindingKind::kPinNet, "Z", kNangateTBUFX4PinZ, std::size(kNangateTBUFX4PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateTBUFX4Power, std::size(kNangateTBUFX4Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateTBUFX4Ground, std::size(kNangateTBUFX4Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateTBUFX4ObsGroup0, std::size(kNangateTBUFX4ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateTBUFX4ObsGroup1, std::size(kNangateTBUFX4ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateTBUFX4ObsGroup2, std::size(kNangateTBUFX4ObsGroup2)},
};

inline constexpr RectSpec kNangateTBUFX8PinA[] = {
    {"metal1", 2.72, 0.39, 2.79, 0.66},
    {"metal1", 2.14, 0.39, 2.79, 0.46},
    {"metal1", 1.95, 0.56, 2.21, 0.63},
    {"metal1", 2.14, 0.39, 2.21, 0.63},
};

inline constexpr RectSpec kNangateTBUFX8PinEN[] = {
    {"metal1", 2.465, 0.725, 3.08, 0.795},
    {"metal1", 3.01, 0.525, 3.08, 0.795},
    {"metal1", 2.465, 0.525, 2.6, 0.795},
};

inline constexpr RectSpec kNangateTBUFX8PinZ[] = {
    {"metal1", 1.36, 1.01, 1.505, 1.08},
    {"metal1", 1.355, 0.375, 1.505, 0.445},
    {"metal1", 1.36, 0.775, 1.43, 1.08},
    {"metal1", 0.265, 0.7, 1.425, 0.84},
    {"metal1", 1.355, 0.375, 1.425, 0.84},
    {"metal1", 1.02, 0.2, 1.095, 0.84},
    {"metal1", 1.02, 0.2, 1.09, 1.25},
    {"metal1", 0.645, 0.2, 0.715, 1.25},
    {"metal1", 0.265, 0.2, 0.335, 1.25},
};

inline constexpr RectSpec kNangateTBUFX8Power[] = {
    {"metal1", 0.0, 1.315, 3.42, 1.485},
    {"metal1", 3.085, 1.13, 3.22, 1.485},
    {"metal1", 2.32, 1.15, 2.455, 1.485},
    {"metal1", 1.97, 0.995, 2.04, 1.485},
    {"metal1", 1.59, 0.995, 1.66, 1.485},
    {"metal1", 1.21, 0.975, 1.28, 1.485},
    {"metal1", 0.83, 0.975, 0.9, 1.485},
    {"metal1", 0.415, 1.01, 0.55, 1.485},
    {"metal1", 0.07, 0.975, 0.14, 1.485},
};

inline constexpr RectSpec kNangateTBUFX8Ground[] = {
    {"metal1", 0.0, -0.085, 3.42, 0.085},
    {"metal1", 3.09, -0.085, 3.225, 0.16},
    {"metal1", 2.7, -0.085, 2.835, 0.16},
    {"metal1", 2.32, -0.085, 2.455, 0.16},
    {"metal1", 1.56, -0.085, 1.695, 0.16},
    {"metal1", 1.18, -0.085, 1.315, 0.16},
    {"metal1", 0.8, -0.085, 0.935, 0.16},
    {"metal1", 0.415, -0.085, 0.55, 0.375},
    {"metal1", 0.07, -0.085, 0.14, 0.41},
};

inline constexpr RectSpec kNangateTBUFX8ObsGroup0[] = {
    {"metal1", 3.305, 0.2, 3.375, 1.25, true},
    {"metal1", 2.295, 0.995, 3.375, 1.065, true},
    {"metal1", 2.295, 0.525, 2.365, 1.065, true},
    {"metal1", 1.705, 0.725, 2.365, 0.795, true},
    {"metal1", 2.275, 0.525, 2.365, 0.795, true},
    {"metal1", 1.705, 0.525, 1.775, 0.795, true},
};

inline constexpr RectSpec kNangateTBUFX8ObsGroup1[] = {
    {"metal1", 2.705, 0.86, 3.215, 0.93, true},
    {"metal1", 3.145, 0.225, 3.215, 0.93, true},
    {"metal1", 1.205, 0.225, 1.275, 0.6, true},
    {"metal1", 1.205, 0.225, 3.215, 0.295, true},
};

inline constexpr RectSpec kNangateTBUFX8ObsGroup2[] = {
    {"metal1", 2.16, 0.86, 2.23, 1.25, true},
    {"metal1", 1.78, 0.86, 1.85, 1.25, true},
    {"metal1", 1.57, 0.86, 2.23, 0.93, true},
    {"metal1", 1.57, 0.39, 1.64, 0.93, true},
    {"metal1", 1.49, 0.615, 1.64, 0.75, true},
    {"metal1", 1.57, 0.39, 2.075, 0.46, true},
};

inline constexpr GroupSpec kNangateTBUFX8Groups[] = {
    {BindingKind::kPinNet, "A", kNangateTBUFX8PinA, std::size(kNangateTBUFX8PinA)},
    {BindingKind::kPinNet, "EN", kNangateTBUFX8PinEN, std::size(kNangateTBUFX8PinEN)},
    {BindingKind::kPinNet, "Z", kNangateTBUFX8PinZ, std::size(kNangateTBUFX8PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateTBUFX8Power, std::size(kNangateTBUFX8Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateTBUFX8Ground, std::size(kNangateTBUFX8Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateTBUFX8ObsGroup0, std::size(kNangateTBUFX8ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateTBUFX8ObsGroup1, std::size(kNangateTBUFX8ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateTBUFX8ObsGroup2, std::size(kNangateTBUFX8ObsGroup2)},
};

inline constexpr RectSpec kNangateTINVX1PinEN[] = {
    {"metal1", 0.45, 0.65, 0.585, 0.72},
    {"metal1", 0.175, 0.84, 0.52, 0.98},
    {"metal1", 0.45, 0.65, 0.52, 0.98},
    {"metal1", 0.175, 0.625, 0.245, 0.98},
};

inline constexpr RectSpec kNangateTINVX1PinI[] = {
    {"metal1", 0.31, 0.42, 0.38, 0.6},
    {"metal1", 0.25, 0.42, 0.38, 0.56},
};

inline constexpr RectSpec kNangateTINVX1PinZN[] = {
    {"metal1", 0.63, 0.84, 0.72, 1.24},
    {"metal1", 0.65, 0.155, 0.72, 1.24},
};

inline constexpr RectSpec kNangateTINVX1Power[] = {
    {"metal1", 0.0, 1.315, 0.76, 1.485},
    {"metal1", 0.225, 1.065, 0.295, 1.485},
};

inline constexpr RectSpec kNangateTINVX1Ground[] = {
    {"metal1", 0.0, -0.085, 0.76, 0.085},
    {"metal1", 0.225, -0.085, 0.295, 0.195},
};

inline constexpr RectSpec kNangateTINVX1ObsGroup0[] = {
    {"metal1", 0.04, 0.195, 0.11, 1.24, true},
    {"metal1", 0.45, 0.495, 0.585, 0.565, true},
    {"metal1", 0.45, 0.275, 0.52, 0.565, true},
    {"metal1", 0.04, 0.275, 0.52, 0.345, true},
};

inline constexpr GroupSpec kNangateTINVX1Groups[] = {
    {BindingKind::kPinNet, "EN", kNangateTINVX1PinEN, std::size(kNangateTINVX1PinEN)},
    {BindingKind::kPinNet, "I", kNangateTINVX1PinI, std::size(kNangateTINVX1PinI)},
    {BindingKind::kPinNet, "ZN", kNangateTINVX1PinZN, std::size(kNangateTINVX1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateTINVX1Power, std::size(kNangateTINVX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateTINVX1Ground, std::size(kNangateTINVX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateTINVX1ObsGroup0, std::size(kNangateTINVX1ObsGroup0)},
};

inline constexpr RectSpec kNangateTLATX1PinD[] = {
    {"metal1", 0.63, 0.585, 0.73, 0.84},
};

inline constexpr RectSpec kNangateTLATX1PinG[] = {
    {"metal1", 0.185, 0.745, 0.32, 0.98},
};

inline constexpr RectSpec kNangateTLATX1PinOE[] = {
    {"metal1", 1.815, 0.5, 2.275, 0.57},
    {"metal1", 1.815, 0.5, 2.03, 0.7},
};

inline constexpr RectSpec kNangateTLATX1PinQ[] = {
    {"metal1", 2.265, 1.01, 2.41, 1.215},
    {"metal1", 2.34, 0.22, 2.41, 1.215},
    {"metal1", 2.265, 0.22, 2.41, 0.425},
};

inline constexpr RectSpec kNangateTLATX1Power[] = {
    {"metal1", 0.0, 1.315, 2.47, 1.485},
    {"metal1", 1.87, 0.975, 1.94, 1.485},
    {"metal1", 1.305, 1.08, 1.44, 1.485},
    {"metal1", 0.585, 1.04, 0.655, 1.485},
    {"metal1", 0.235, 1.045, 0.305, 1.485},
};

inline constexpr RectSpec kNangateTLATX1Ground[] = {
    {"metal1", 0.0, -0.085, 2.47, 0.085},
    {"metal1", 1.87, -0.085, 1.94, 0.32},
    {"metal1", 1.335, -0.085, 1.405, 0.32},
    {"metal1", 0.585, -0.085, 0.655, 0.46},
    {"metal1", 0.235, -0.085, 0.305, 0.32},
};

inline constexpr RectSpec kNangateTLATX1ObsGroup0[] = {
    {"metal1", 1.68, 0.185, 1.75, 1.245, true},
    {"metal1", 1.68, 0.775, 2.275, 0.855, true},
    {"metal1", 2.14, 0.65, 2.275, 0.855, true},
};

inline constexpr RectSpec kNangateTLATX1ObsGroup1[] = {
    {"metal1", 1.53, 0.185, 1.6, 1.185, true},
    {"metal1", 1.26, 0.515, 1.6, 0.65, true},
};

inline constexpr RectSpec kNangateTLATX1ObsGroup2[] = {
    {"metal1", 0.93, 1.07, 1.09, 1.14, true},
    {"metal1", 1.02, 0.22, 1.09, 1.14, true},
    {"metal1", 1.02, 0.745, 1.465, 0.88, true},
    {"metal1", 0.93, 0.22, 1.09, 0.29, true},
};

inline constexpr RectSpec kNangateTLATX1ObsGroup3[] = {
    {"metal1", 0.43, 0.185, 0.5, 1.25, true},
    {"metal1", 0.43, 0.905, 0.945, 0.975, true},
    {"metal1", 0.875, 0.51, 0.945, 0.975, true},
};

inline constexpr RectSpec kNangateTLATX1ObsGroup4[] = {
    {"metal1", 0.05, 0.185, 0.12, 1.25, true},
    {"metal1", 0.05, 0.46, 0.365, 0.595, true},
};

inline constexpr GroupSpec kNangateTLATX1Groups[] = {
    {BindingKind::kPinNet, "D", kNangateTLATX1PinD, std::size(kNangateTLATX1PinD)},
    {BindingKind::kPinNet, "G", kNangateTLATX1PinG, std::size(kNangateTLATX1PinG)},
    {BindingKind::kPinNet, "OE", kNangateTLATX1PinOE, std::size(kNangateTLATX1PinOE)},
    {BindingKind::kPinNet, "Q", kNangateTLATX1PinQ, std::size(kNangateTLATX1PinQ)},
    {BindingKind::kSupplyNet, "POWER", kNangateTLATX1Power, std::size(kNangateTLATX1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateTLATX1Ground, std::size(kNangateTLATX1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateTLATX1ObsGroup0, std::size(kNangateTLATX1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateTLATX1ObsGroup1, std::size(kNangateTLATX1ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateTLATX1ObsGroup2, std::size(kNangateTLATX1ObsGroup2)},
    {BindingKind::kSyntheticNet, "OBS3", kNangateTLATX1ObsGroup3, std::size(kNangateTLATX1ObsGroup3)},
    {BindingKind::kSyntheticNet, "OBS4", kNangateTLATX1ObsGroup4, std::size(kNangateTLATX1ObsGroup4)},
};

inline constexpr RectSpec kNangateXNOR2X1PinA[] = {
    {"metal1", 0.65, 0.555, 0.81, 0.625},
    {"metal1", 0.65, 0.39, 0.72, 0.625},
    {"metal1", 0.185, 0.39, 0.72, 0.46},
    {"metal1", 0.185, 0.39, 0.32, 0.56},
};

inline constexpr RectSpec kNangateXNOR2X1PinB[] = {
    {"metal1", 0.35, 0.84, 0.965, 0.91},
    {"metal1", 0.895, 0.525, 0.965, 0.91},
    {"metal1", 0.35, 0.84, 0.51, 0.98},
};

inline constexpr RectSpec kNangateXNOR2X1PinZN[] = {
    {"metal1", 0.63, 0.98, 1.1, 1.05},
    {"metal1", 1.03, 0.295, 1.1, 1.05},
    {"metal1", 0.785, 0.295, 1.1, 0.365},
    {"metal1", 0.63, 0.98, 0.7, 1.25},
};

inline constexpr RectSpec kNangateXNOR2X1Power[] = {
    {"metal1", 0.0, 1.315, 1.14, 1.485},
    {"metal1", 1.0, 1.115, 1.07, 1.485},
    {"metal1", 0.43, 1.115, 0.5, 1.485},
    {"metal1", 0.05, 1.115, 0.12, 1.485},
};

inline constexpr RectSpec kNangateXNOR2X1Ground[] = {
    {"metal1", 0.0, -0.085, 1.14, 0.085},
    {"metal1", 0.395, -0.085, 0.53, 0.25},
};

inline constexpr RectSpec kNangateXNOR2X1ObsGroup0[] = {
    {"metal1", 0.21, 1.145, 0.345, 1.215, true},
    {"metal1", 0.21, 0.67, 0.28, 1.215, true},
    {"metal1", 0.05, 0.67, 0.585, 0.74, true},
    {"metal1", 0.515, 0.525, 0.585, 0.74, true},
    {"metal1", 0.05, 0.15, 0.12, 0.74, true},
};

inline constexpr RectSpec kNangateXNOR2X1ObsGroup1[] = {
    {"metal1", 0.595, 0.16, 1.105, 0.23, true},
};

inline constexpr GroupSpec kNangateXNOR2X1Groups[] = {
    {BindingKind::kPinNet, "A", kNangateXNOR2X1PinA, std::size(kNangateXNOR2X1PinA)},
    {BindingKind::kPinNet, "B", kNangateXNOR2X1PinB, std::size(kNangateXNOR2X1PinB)},
    {BindingKind::kPinNet, "ZN", kNangateXNOR2X1PinZN, std::size(kNangateXNOR2X1PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateXNOR2X1Power, std::size(kNangateXNOR2X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateXNOR2X1Ground, std::size(kNangateXNOR2X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateXNOR2X1ObsGroup0, std::size(kNangateXNOR2X1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateXNOR2X1ObsGroup1, std::size(kNangateXNOR2X1ObsGroup1)},
};

inline constexpr RectSpec kNangateXNOR2X2PinA[] = {
    {"metal1", 1.01, 0.525, 1.08, 0.7},
};

inline constexpr RectSpec kNangateXNOR2X2PinB[] = {
    {"metal1", 0.82, 0.77, 1.65, 0.84},
    {"metal1", 1.58, 0.525, 1.65, 0.84},
    {"metal1", 0.82, 0.56, 0.89, 0.84},
    {"metal1", 0.505, 0.56, 0.89, 0.63},
};

inline constexpr RectSpec kNangateXNOR2X2PinZN[] = {
    {"metal1", 0.21, 0.905, 1.84, 0.975},
    {"metal1", 1.77, 0.19, 1.84, 0.975},
    {"metal1", 0.975, 0.36, 1.84, 0.43},
    {"metal1", 1.765, 0.19, 1.84, 0.43},
};

inline constexpr RectSpec kNangateXNOR2X2Power[] = {
    {"metal1", 0.0, 1.315, 1.9, 1.485},
    {"metal1", 1.54, 1.24, 1.675, 1.485},
    {"metal1", 0.805, 1.065, 0.875, 1.485},
    {"metal1", 0.425, 1.065, 0.495, 1.485},
    {"metal1", 0.05, 1.065, 0.12, 1.485},
};

inline constexpr RectSpec kNangateXNOR2X2Ground[] = {
    {"metal1", 0.0, -0.085, 1.9, 0.085},
    {"metal1", 0.395, -0.085, 0.53, 0.16},
    {"metal1", 0.05, -0.085, 0.12, 0.325},
};

inline constexpr RectSpec kNangateXNOR2X2ObsGroup0[] = {
    {"metal1", 0.245, 0.725, 0.72, 0.795, true},
    {"metal1", 0.245, 0.39, 0.315, 0.795, true},
    {"metal1", 0.245, 0.39, 0.91, 0.46, true},
};

inline constexpr RectSpec kNangateXNOR2X2ObsGroup1[] = {
    {"metal1", 0.975, 1.095, 1.865, 1.165, true},
};

inline constexpr RectSpec kNangateXNOR2X2ObsGroup2[] = {
    {"metal1", 0.21, 0.225, 1.675, 0.295, true},
};

inline constexpr GroupSpec kNangateXNOR2X2Groups[] = {
    {BindingKind::kPinNet, "A", kNangateXNOR2X2PinA, std::size(kNangateXNOR2X2PinA)},
    {BindingKind::kPinNet, "B", kNangateXNOR2X2PinB, std::size(kNangateXNOR2X2PinB)},
    {BindingKind::kPinNet, "ZN", kNangateXNOR2X2PinZN, std::size(kNangateXNOR2X2PinZN)},
    {BindingKind::kSupplyNet, "POWER", kNangateXNOR2X2Power, std::size(kNangateXNOR2X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateXNOR2X2Ground, std::size(kNangateXNOR2X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateXNOR2X2ObsGroup0, std::size(kNangateXNOR2X2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateXNOR2X2ObsGroup1, std::size(kNangateXNOR2X2ObsGroup1)},
    {BindingKind::kSyntheticNet, "OBS2", kNangateXNOR2X2ObsGroup2, std::size(kNangateXNOR2X2ObsGroup2)},
};

inline constexpr RectSpec kNangateXOR2X1PinA[] = {
    {"metal1", 0.63, 0.525, 0.755, 0.66},
    {"metal1", 0.175, 0.73, 0.7, 0.8},
    {"metal1", 0.63, 0.525, 0.7, 0.8},
    {"metal1", 0.175, 0.665, 0.245, 0.8},
};

inline constexpr RectSpec kNangateXOR2X1PinB[] = {
    {"metal1", 0.82, 0.525, 0.945, 0.66},
    {"metal1", 0.305, 0.875, 0.89, 0.945},
    {"metal1", 0.82, 0.525, 0.89, 0.945},
};

inline constexpr RectSpec kNangateXOR2X1PinZ[] = {
    {"metal1", 0.775, 1.04, 1.08, 1.11},
    {"metal1", 1.01, 0.35, 1.08, 1.11},
    {"metal1", 0.62, 0.35, 1.08, 0.42},
    {"metal1", 0.62, 0.15, 0.69, 0.42},
};

inline constexpr RectSpec kNangateXOR2X1Power[] = {
    {"metal1", 0.0, 1.315, 1.14, 1.485},
    {"metal1", 0.42, 1.15, 0.49, 1.485},
};

inline constexpr RectSpec kNangateXOR2X1Ground[] = {
    {"metal1", 0.0, -0.085, 1.14, 0.085},
    {"metal1", 0.99, -0.085, 1.06, 0.285},
    {"metal1", 0.42, -0.085, 0.49, 0.285},
    {"metal1", 0.04, -0.085, 0.11, 0.285},
};

inline constexpr RectSpec kNangateXOR2X1ObsGroup0[] = {
    {"metal1", 0.04, 0.525, 0.11, 1.25, true},
    {"metal1", 0.495, 0.525, 0.565, 0.66, true},
    {"metal1", 0.04, 0.525, 0.565, 0.595, true},
    {"metal1", 0.225, 0.15, 0.295, 0.595, true},
};

inline constexpr RectSpec kNangateXOR2X1ObsGroup1[] = {
    {"metal1", 0.585, 1.175, 1.095, 1.245, true},
};

inline constexpr GroupSpec kNangateXOR2X1Groups[] = {
    {BindingKind::kPinNet, "A", kNangateXOR2X1PinA, std::size(kNangateXOR2X1PinA)},
    {BindingKind::kPinNet, "B", kNangateXOR2X1PinB, std::size(kNangateXOR2X1PinB)},
    {BindingKind::kPinNet, "Z", kNangateXOR2X1PinZ, std::size(kNangateXOR2X1PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateXOR2X1Power, std::size(kNangateXOR2X1Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateXOR2X1Ground, std::size(kNangateXOR2X1Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateXOR2X1ObsGroup0, std::size(kNangateXOR2X1ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateXOR2X1ObsGroup1, std::size(kNangateXOR2X1ObsGroup1)},
};

inline constexpr RectSpec kNangateXOR2X2PinA[] = {
    {"metal1", 1.255, 0.395, 1.325, 0.66},
    {"metal1", 0.745, 0.395, 1.325, 0.465},
    {"metal1", 0.745, 0.285, 0.82, 0.66},
    {"metal1", 0.06, 0.285, 0.82, 0.355},
    {"metal1", 0.06, 0.285, 0.165, 0.7},
};

inline constexpr RectSpec kNangateXOR2X2PinB[] = {
    {"metal1", 0.365, 0.77, 1.125, 0.84},
    {"metal1", 0.99, 0.56, 1.125, 0.84},
    {"metal1", 0.365, 0.56, 0.5, 0.84},
};

inline constexpr RectSpec kNangateXOR2X2PinZ[] = {
    {"metal1", 0.8, 0.905, 1.465, 0.975},
    {"metal1", 1.39, 0.26, 1.465, 0.975},
    {"metal1", 0.885, 0.26, 1.465, 0.33},
    {"metal1", 0.885, 0.15, 0.955, 0.33},
    {"metal1", 0.61, 0.15, 0.955, 0.22},
};

inline constexpr RectSpec kNangateXOR2X2Power[] = {
    {"metal1", 0.0, 1.315, 1.71, 1.485},
    {"metal1", 1.585, 1.205, 1.655, 1.485},
    {"metal1", 0.445, 1.205, 0.515, 1.485},
};

inline constexpr RectSpec kNangateXOR2X2Ground[] = {
    {"metal1", 0.0, -0.085, 1.71, 0.085},
    {"metal1", 1.585, -0.085, 1.655, 0.335},
    {"metal1", 1.025, -0.085, 1.095, 0.195},
    {"metal1", 0.445, -0.085, 0.515, 0.195},
    {"metal1", 0.07, -0.085, 0.14, 0.21},
};

inline constexpr RectSpec kNangateXOR2X2ObsGroup0[] = {
    {"metal1", 0.04, 1.04, 1.6, 1.11, true},
    {"metal1", 1.53, 0.525, 1.6, 1.11, true},
    {"metal1", 0.23, 0.425, 0.3, 1.11, true},
    {"metal1", 0.575, 0.425, 0.645, 0.66, true},
    {"metal1", 0.23, 0.425, 0.645, 0.495, true},
};

inline constexpr RectSpec kNangateXOR2X2ObsGroup1[] = {
    {"metal1", 0.61, 1.175, 1.5, 1.245, true},
};

inline constexpr GroupSpec kNangateXOR2X2Groups[] = {
    {BindingKind::kPinNet, "A", kNangateXOR2X2PinA, std::size(kNangateXOR2X2PinA)},
    {BindingKind::kPinNet, "B", kNangateXOR2X2PinB, std::size(kNangateXOR2X2PinB)},
    {BindingKind::kPinNet, "Z", kNangateXOR2X2PinZ, std::size(kNangateXOR2X2PinZ)},
    {BindingKind::kSupplyNet, "POWER", kNangateXOR2X2Power, std::size(kNangateXOR2X2Power)},
    {BindingKind::kSupplyNet, "GROUND", kNangateXOR2X2Ground, std::size(kNangateXOR2X2Ground)},
    {BindingKind::kSyntheticNet, "OBS0", kNangateXOR2X2ObsGroup0, std::size(kNangateXOR2X2ObsGroup0)},
    {BindingKind::kSyntheticNet, "OBS1", kNangateXOR2X2ObsGroup1, std::size(kNangateXOR2X2ObsGroup1)},
};

inline constexpr MacroSpec kSupportedMacros[] = {
    {"AND2_X1", 0.76, 1.4, kNangateAND2X1Groups, std::size(kNangateAND2X1Groups)},
    {"AND2_X2", 0.95, 1.4, kNangateAND2X2Groups, std::size(kNangateAND2X2Groups)},
    {"AND2_X4", 1.71, 1.4, kNangateAND2X4Groups, std::size(kNangateAND2X4Groups)},
    {"AND3_X1", 0.95, 1.4, kNangateAND3X1Groups, std::size(kNangateAND3X1Groups)},
    {"AND3_X2", 1.14, 1.4, kNangateAND3X2Groups, std::size(kNangateAND3X2Groups)},
    {"AND3_X4", 2.09, 1.4, kNangateAND3X4Groups, std::size(kNangateAND3X4Groups)},
    {"AND4_X1", 1.14, 1.4, kNangateAND4X1Groups, std::size(kNangateAND4X1Groups)},
    {"AND4_X2", 1.33, 1.4, kNangateAND4X2Groups, std::size(kNangateAND4X2Groups)},
    {"AND4_X4", 2.47, 1.4, kNangateAND4X4Groups, std::size(kNangateAND4X4Groups)},
    {"ANTENNA_X1", 0.19, 1.4, kNangateANTENNAX1Groups, std::size(kNangateANTENNAX1Groups)},
    {"AOI211_X1", 0.95, 1.4, kNangateAOI211X1Groups, std::size(kNangateAOI211X1Groups)},
    {"AOI211_X2", 1.71, 1.4, kNangateAOI211X2Groups, std::size(kNangateAOI211X2Groups)},
    {"AOI211_X4", 2.09, 1.4, kNangateAOI211X4Groups, std::size(kNangateAOI211X4Groups)},
    {"AOI21_X1", 0.76, 1.4, kNangateAOI21X1Groups, std::size(kNangateAOI21X1Groups)},
    {"AOI21_X2", 1.33, 1.4, kNangateAOI21X2Groups, std::size(kNangateAOI21X2Groups)},
    {"AOI21_X4", 2.47, 1.4, kNangateAOI21X4Groups, std::size(kNangateAOI21X4Groups)},
    {"AOI221_X1", 1.14, 1.4, kNangateAOI221X1Groups, std::size(kNangateAOI221X1Groups)},
    {"AOI221_X2", 2.09, 1.4, kNangateAOI221X2Groups, std::size(kNangateAOI221X2Groups)},
    {"AOI221_X4", 2.47, 1.4, kNangateAOI221X4Groups, std::size(kNangateAOI221X4Groups)},
    {"AOI222_X1", 1.52, 1.4, kNangateAOI222X1Groups, std::size(kNangateAOI222X1Groups)},
    {"AOI222_X2", 2.66, 1.4, kNangateAOI222X2Groups, std::size(kNangateAOI222X2Groups)},
    {"AOI222_X4", 2.66, 1.4, kNangateAOI222X4Groups, std::size(kNangateAOI222X4Groups)},
    {"AOI22_X1", 0.95, 1.4, kNangateAOI22X1Groups, std::size(kNangateAOI22X1Groups)},
    {"AOI22_X2", 1.71, 1.4, kNangateAOI22X2Groups, std::size(kNangateAOI22X2Groups)},
    {"AOI22_X4", 3.23, 1.4, kNangateAOI22X4Groups, std::size(kNangateAOI22X4Groups)},
    {"BUF_X1", 0.57, 1.4, kNangateBUFX1Groups, std::size(kNangateBUFX1Groups)},
    {"BUF_X16", 4.75, 1.4, kNangateBUFX16Groups, std::size(kNangateBUFX16Groups)},
    {"BUF_X2", 0.76, 1.4, kNangateBUFX2Groups, std::size(kNangateBUFX2Groups)},
    {"BUF_X32", 9.31, 1.4, kNangateBUFX32Groups, std::size(kNangateBUFX32Groups)},
    {"BUF_X4", 1.33, 1.4, kNangateBUFX4Groups, std::size(kNangateBUFX4Groups)},
    {"BUF_X8", 2.47, 1.4, kNangateBUFX8Groups, std::size(kNangateBUFX8Groups)},
    {"CLKBUF_X1", 0.57, 1.4, kNangateCLKBUFX1Groups, std::size(kNangateCLKBUFX1Groups)},
    {"CLKBUF_X2", 0.76, 1.4, kNangateCLKBUFX2Groups, std::size(kNangateCLKBUFX2Groups)},
    {"CLKBUF_X3", 0.95, 1.4, kNangateCLKBUFX3Groups, std::size(kNangateCLKBUFX3Groups)},
    {"CLKGATETST_X1", 2.85, 1.4, kNangateCLKGATETSTX1Groups, std::size(kNangateCLKGATETSTX1Groups)},
    {"CLKGATETST_X2", 3.04, 1.4, kNangateCLKGATETSTX2Groups, std::size(kNangateCLKGATETSTX2Groups)},
    {"CLKGATETST_X4", 3.8, 1.4, kNangateCLKGATETSTX4Groups, std::size(kNangateCLKGATETSTX4Groups)},
    {"CLKGATETST_X8", 5.51, 1.4, kNangateCLKGATETSTX8Groups, std::size(kNangateCLKGATETSTX8Groups)},
    {"CLKGATE_X1", 2.47, 1.4, kNangateCLKGATEX1Groups, std::size(kNangateCLKGATEX1Groups)},
    {"CLKGATE_X2", 2.66, 1.4, kNangateCLKGATEX2Groups, std::size(kNangateCLKGATEX2Groups)},
    {"CLKGATE_X4", 3.23, 1.4, kNangateCLKGATEX4Groups, std::size(kNangateCLKGATEX4Groups)},
    {"CLKGATE_X8", 4.94, 1.4, kNangateCLKGATEX8Groups, std::size(kNangateCLKGATEX8Groups)},
    {"DFFRS_X1", 4.56, 1.4, kNangateDFFRSX1Groups, std::size(kNangateDFFRSX1Groups)},
    {"DFFRS_X2", 4.94, 1.4, kNangateDFFRSX2Groups, std::size(kNangateDFFRSX2Groups)},
    {"DFFR_X1", 3.8, 1.4, kNangateDFFRX1Groups, std::size(kNangateDFFRX1Groups)},
    {"DFFR_X2", 4.18, 1.4, kNangateDFFRX2Groups, std::size(kNangateDFFRX2Groups)},
    {"DFFS_X1", 3.8, 1.4, kNangateDFFSX1Groups, std::size(kNangateDFFSX1Groups)},
    {"DFFS_X2", 3.99, 1.4, kNangateDFFSX2Groups, std::size(kNangateDFFSX2Groups)},
    {"DFF_X1", 3.23, 1.4, kNangateDFFX1Groups, std::size(kNangateDFFX1Groups)},
    {"DFF_X2", 3.61, 1.4, kNangateDFFX2Groups, std::size(kNangateDFFX2Groups)},
    {"DLH_X1", 1.9, 1.4, kNangateDLHX1Groups, std::size(kNangateDLHX1Groups)},
    {"DLH_X2", 2.09, 1.4, kNangateDLHX2Groups, std::size(kNangateDLHX2Groups)},
    {"DLL_X1", 1.9, 1.4, kNangateDLLX1Groups, std::size(kNangateDLLX1Groups)},
    {"DLL_X2", 2.09, 1.4, kNangateDLLX2Groups, std::size(kNangateDLLX2Groups)},
    {"FA_X1", 3.04, 1.4, kNangateFAX1Groups, std::size(kNangateFAX1Groups)},
    {"TAPCELL_X1", 0.19, 1.4, kNangateTAPCELLX1Groups, std::size(kNangateTAPCELLX1Groups)},
    {"FILLCELL_X1", 0.19, 1.4, kNangateFILLCELLX1Groups, std::size(kNangateFILLCELLX1Groups)},
    {"FILLCELL_X16", 3.04, 1.4, kNangateFILLCELLX16Groups, std::size(kNangateFILLCELLX16Groups)},
    {"FILLCELL_X2", 0.38, 1.4, kNangateFILLCELLX2Groups, std::size(kNangateFILLCELLX2Groups)},
    {"FILLCELL_X32", 6.08, 1.4, kNangateFILLCELLX32Groups, std::size(kNangateFILLCELLX32Groups)},
    {"FILLCELL_X4", 0.76, 1.4, kNangateFILLCELLX4Groups, std::size(kNangateFILLCELLX4Groups)},
    {"FILLCELL_X8", 1.52, 1.4, kNangateFILLCELLX8Groups, std::size(kNangateFILLCELLX8Groups)},
    {"HA_X1", 1.9, 1.4, kNangateHAX1Groups, std::size(kNangateHAX1Groups)},
    {"INV_X1", 0.38, 1.4, kNangateINVX1Groups, std::size(kNangateINVX1Groups)},
    {"INV_X16", 3.23, 1.4, kNangateINVX16Groups, std::size(kNangateINVX16Groups)},
    {"INV_X2", 0.57, 1.4, kNangateINVX2Groups, std::size(kNangateINVX2Groups)},
    {"INV_X32", 6.27, 1.4, kNangateINVX32Groups, std::size(kNangateINVX32Groups)},
    {"INV_X4", 0.95, 1.4, kNangateINVX4Groups, std::size(kNangateINVX4Groups)},
    {"INV_X8", 1.71, 1.4, kNangateINVX8Groups, std::size(kNangateINVX8Groups)},
    {"LOGIC0_X1", 0.38, 1.4, kNangateLOGIC0X1Groups, std::size(kNangateLOGIC0X1Groups)},
    {"LOGIC1_X1", 0.38, 1.4, kNangateLOGIC1X1Groups, std::size(kNangateLOGIC1X1Groups)},
    {"MUX2_X1", 1.33, 1.4, kNangateMUX2X1Groups, std::size(kNangateMUX2X1Groups)},
    {"MUX2_X2", 1.71, 1.4, kNangateMUX2X2Groups, std::size(kNangateMUX2X2Groups)},
    {"NAND2_X1", 0.57, 1.4, kNangateNAND2X1Groups, std::size(kNangateNAND2X1Groups)},
    {"NAND2_X2", 0.95, 1.4, kNangateNAND2X2Groups, std::size(kNangateNAND2X2Groups)},
    {"NAND2_X4", 1.71, 1.4, kNangateNAND2X4Groups, std::size(kNangateNAND2X4Groups)},
    {"NAND3_X1", 0.76, 1.4, kNangateNAND3X1Groups, std::size(kNangateNAND3X1Groups)},
    {"NAND3_X2", 1.33, 1.4, kNangateNAND3X2Groups, std::size(kNangateNAND3X2Groups)},
    {"NAND3_X4", 2.47, 1.4, kNangateNAND3X4Groups, std::size(kNangateNAND3X4Groups)},
    {"NAND4_X1", 0.95, 1.4, kNangateNAND4X1Groups, std::size(kNangateNAND4X1Groups)},
    {"NAND4_X2", 1.71, 1.4, kNangateNAND4X2Groups, std::size(kNangateNAND4X2Groups)},
    {"NAND4_X4", 3.42, 1.4, kNangateNAND4X4Groups, std::size(kNangateNAND4X4Groups)},
    {"NOR2_X1", 0.57, 1.4, kNangateNOR2X1Groups, std::size(kNangateNOR2X1Groups)},
    {"NOR2_X2", 0.95, 1.4, kNangateNOR2X2Groups, std::size(kNangateNOR2X2Groups)},
    {"NOR2_X4", 1.71, 1.4, kNangateNOR2X4Groups, std::size(kNangateNOR2X4Groups)},
    {"NOR3_X1", 0.76, 1.4, kNangateNOR3X1Groups, std::size(kNangateNOR3X1Groups)},
    {"NOR3_X2", 1.33, 1.4, kNangateNOR3X2Groups, std::size(kNangateNOR3X2Groups)},
    {"NOR3_X4", 2.66, 1.4, kNangateNOR3X4Groups, std::size(kNangateNOR3X4Groups)},
    {"NOR4_X1", 0.95, 1.4, kNangateNOR4X1Groups, std::size(kNangateNOR4X1Groups)},
    {"NOR4_X2", 1.71, 1.4, kNangateNOR4X2Groups, std::size(kNangateNOR4X2Groups)},
    {"NOR4_X4", 3.42, 1.4, kNangateNOR4X4Groups, std::size(kNangateNOR4X4Groups)},
    {"OAI211_X1", 0.95, 1.4, kNangateOAI211X1Groups, std::size(kNangateOAI211X1Groups)},
    {"OAI211_X2", 1.71, 1.4, kNangateOAI211X2Groups, std::size(kNangateOAI211X2Groups)},
    {"OAI211_X4", 3.23, 1.4, kNangateOAI211X4Groups, std::size(kNangateOAI211X4Groups)},
    {"OAI21_X1", 0.76, 1.4, kNangateOAI21X1Groups, std::size(kNangateOAI21X1Groups)},
    {"OAI21_X2", 1.33, 1.4, kNangateOAI21X2Groups, std::size(kNangateOAI21X2Groups)},
    {"OAI21_X4", 2.47, 1.4, kNangateOAI21X4Groups, std::size(kNangateOAI21X4Groups)},
    {"OAI221_X1", 1.14, 1.4, kNangateOAI221X1Groups, std::size(kNangateOAI221X1Groups)},
    {"OAI221_X2", 2.09, 1.4, kNangateOAI221X2Groups, std::size(kNangateOAI221X2Groups)},
    {"OAI221_X4", 2.47, 1.4, kNangateOAI221X4Groups, std::size(kNangateOAI221X4Groups)},
    {"OAI222_X1", 1.52, 1.4, kNangateOAI222X1Groups, std::size(kNangateOAI222X1Groups)},
    {"OAI222_X2", 2.66, 1.4, kNangateOAI222X2Groups, std::size(kNangateOAI222X2Groups)},
    {"OAI222_X4", 2.66, 1.4, kNangateOAI222X4Groups, std::size(kNangateOAI222X4Groups)},
    {"OAI22_X1", 0.95, 1.4, kNangateOAI22X1Groups, std::size(kNangateOAI22X1Groups)},
    {"OAI22_X2", 1.71, 1.4, kNangateOAI22X2Groups, std::size(kNangateOAI22X2Groups)},
    {"OAI22_X4", 3.23, 1.4, kNangateOAI22X4Groups, std::size(kNangateOAI22X4Groups)},
    {"OAI33_X1", 1.33, 1.4, kNangateOAI33X1Groups, std::size(kNangateOAI33X1Groups)},
    {"OR2_X1", 0.76, 1.4, kNangateOR2X1Groups, std::size(kNangateOR2X1Groups)},
    {"OR2_X2", 0.95, 1.4, kNangateOR2X2Groups, std::size(kNangateOR2X2Groups)},
    {"OR2_X4", 1.71, 1.4, kNangateOR2X4Groups, std::size(kNangateOR2X4Groups)},
    {"OR3_X1", 0.95, 1.4, kNangateOR3X1Groups, std::size(kNangateOR3X1Groups)},
    {"OR3_X2", 1.14, 1.4, kNangateOR3X2Groups, std::size(kNangateOR3X2Groups)},
    {"OR3_X4", 2.09, 1.4, kNangateOR3X4Groups, std::size(kNangateOR3X4Groups)},
    {"OR4_X1", 1.14, 1.4, kNangateOR4X1Groups, std::size(kNangateOR4X1Groups)},
    {"OR4_X2", 1.33, 1.4, kNangateOR4X2Groups, std::size(kNangateOR4X2Groups)},
    {"OR4_X4", 2.47, 1.4, kNangateOR4X4Groups, std::size(kNangateOR4X4Groups)},
    {"SDFFRS_X1", 5.51, 1.4, kNangateSDFFRSX1Groups, std::size(kNangateSDFFRSX1Groups)},
    {"SDFFRS_X2", 5.89, 1.4, kNangateSDFFRSX2Groups, std::size(kNangateSDFFRSX2Groups)},
    {"SDFFR_X1", 4.75, 1.4, kNangateSDFFRX1Groups, std::size(kNangateSDFFRX1Groups)},
    {"SDFFR_X2", 4.94, 1.4, kNangateSDFFRX2Groups, std::size(kNangateSDFFRX2Groups)},
    {"SDFFS_X1", 4.75, 1.4, kNangateSDFFSX1Groups, std::size(kNangateSDFFSX1Groups)},
    {"SDFFS_X2", 5.13, 1.4, kNangateSDFFSX2Groups, std::size(kNangateSDFFSX2Groups)},
    {"SDFF_X1", 4.37, 1.4, kNangateSDFFX1Groups, std::size(kNangateSDFFX1Groups)},
    {"SDFF_X2", 4.56, 1.4, kNangateSDFFX2Groups, std::size(kNangateSDFFX2Groups)},
    {"TBUF_X1", 1.52, 1.4, kNangateTBUFX1Groups, std::size(kNangateTBUFX1Groups)},
    {"TBUF_X16", 4.94, 1.4, kNangateTBUFX16Groups, std::size(kNangateTBUFX16Groups)},
    {"TBUF_X2", 1.71, 1.4, kNangateTBUFX2Groups, std::size(kNangateTBUFX2Groups)},
    {"TBUF_X4", 2.09, 1.4, kNangateTBUFX4Groups, std::size(kNangateTBUFX4Groups)},
    {"TBUF_X8", 3.42, 1.4, kNangateTBUFX8Groups, std::size(kNangateTBUFX8Groups)},
    {"TINV_X1", 0.76, 1.4, kNangateTINVX1Groups, std::size(kNangateTINVX1Groups)},
    {"TLAT_X1", 2.47, 1.4, kNangateTLATX1Groups, std::size(kNangateTLATX1Groups)},
    {"XNOR2_X1", 1.14, 1.4, kNangateXNOR2X1Groups, std::size(kNangateXNOR2X1Groups)},
    {"XNOR2_X2", 1.9, 1.4, kNangateXNOR2X2Groups, std::size(kNangateXNOR2X2Groups)},
    {"XOR2_X1", 1.14, 1.4, kNangateXOR2X1Groups, std::size(kNangateXOR2X1Groups)},
    {"XOR2_X2", 1.71, 1.4, kNangateXOR2X2Groups, std::size(kNangateXOR2X2Groups)},
};

}  // namespace capbench_compiled_recipes
