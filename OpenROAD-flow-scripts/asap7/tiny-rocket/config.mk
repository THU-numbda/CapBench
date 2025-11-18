#############################################
# tiny-rocket — 7nm (ASAP7)
#############################################

export PLATFORM                 = asap7
export DESIGN_NAME              = RocketTile
export DESIGN_NICKNAME         ?= tiny-rocket-7nm

export DESIGN_CFG_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
export DESIGN_SRC_DIR := $(abspath $(DESIGN_CFG_DIR)/../../src/tiny-rocket)

export SYNTH_HDL = verilog
export SYNTH_HIERARCHICAL = 1

export VERILOG_FILES := \
  $(DESIGN_SRC_DIR)/freechips.rocketchip.system.TinyConfig.v \
  $(DESIGN_SRC_DIR)/rtl/local.freechips.rocketchip.system.TinyConfig.v \
  $(DESIGN_SRC_DIR)/rtl/AsyncResetReg.v \
  $(DESIGN_SRC_DIR)/rtl/ClockDivider2.v \
  $(DESIGN_SRC_DIR)/rtl/ClockDivider3.v \
  $(DESIGN_SRC_DIR)/rtl/plusarg_reader.v \
  $(wildcard $(DESIGN_CFG_DIR)/fakeram_7/*/*.bb.v)
export SDC_FILE = $(DESIGN_CFG_DIR)/constraints.sdc

export ADDITIONAL_LEFS := $(wildcard $(DESIGN_CFG_DIR)/fakeram_7/*/*.lef)
export ADDITIONAL_LIBS := $(wildcard $(DESIGN_CFG_DIR)/fakeram_7/*/*.lib)

# ===============================
# Universal "Synthesis-First" Configuration
# Very relaxed settings for easiest synthesis
# ===============================

# Floorplan - Very low utilization for easy placement
export CORE_UTILIZATION = 0.45  # Very relaxed, lots of whitespace
export ASPECT_RATIO = 1.0

# The following will be calculated based on utilization and aspect ratio
# export DIE_AREA    = 0 0 1274.76 1498.2
# export CORE_AREA   = 10.07 9.8 1244.55 1468.8

# Macro Placement - Generous spacing
export MACRO_PLACE_HALO         = 10 10
export MACRO_PLACE_CHANNEL      = 10 10
export CELL_PAD_IN_SITES        = 4

# RTLMP - More relaxed parameters
export RTLMP_MAX_NUM_LEVEL      ?= 1
export RTLMP_MIN_AR             ?= 0.2
export RTLMP_TARGET_DEAD_SPACE  ?= 0.40  # Increased from 0.30
export RTLMP_TIMING_DRIVEN      ?= 0

# ===============================
# Placement - Very relaxed density for easy synthesis
# ===============================
export GPL_TIMING_DRIVEN        ?= 0
export DPL_TIMING_DRIVEN        ?= 0
export GPL_MAX_ITERATIONS       ?= 500   # Reduced from 1000 (faster)

# Very low density target for easy placement
export GPL_TARGET_DENSITY       = 0.55   # Much lower than standard 0.75
# The overflow parameter will be calculated based on the density target
# export GPL_TARGET_OVERFLOW      ?= 0.20

# ===============================
# Timing Repair - Minimal to avoid buffer explosion
# ===============================
export SKIP_CTS_REPAIR_TIMING   = 1
export TNS_END_PERCENT = 100
export HOLD_SLACK_MARGIN        = -2.0