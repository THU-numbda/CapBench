#############################################
# tiny-rocket — 130nm (Sky130HD)
#############################################

export PLATFORM                 = sky130hd
export DESIGN_NAME              = RocketTile
export DESIGN_NICKNAME         ?= tiny-rocket-130nm

export DESIGN_CFG_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
export DESIGN_SRC_DIR := $(abspath $(DESIGN_CFG_DIR)/../../src/tiny-rocket)

export SYNTH_HDL = verilog
export SYNTH_HIERARCHICAL = 1
export SYNTH_MEMORY_MAX_BITS   = 100000
export SYNTH_MINIMUM_KEEP_SIZE ?= 40000

export VERILOG_FILES := \
  $(DESIGN_SRC_DIR)/freechips.rocketchip.system.TinyConfig.v \
  $(DESIGN_SRC_DIR)/rtl/local.freechips.rocketchip.system.TinyConfig.v \
  $(DESIGN_SRC_DIR)/rtl/AsyncResetReg.v \
  $(DESIGN_SRC_DIR)/rtl/ClockDivider2.v \
  $(DESIGN_SRC_DIR)/rtl/ClockDivider3.v \
  $(DESIGN_SRC_DIR)/rtl/plusarg_reader.v \
  $(wildcard $(DESIGN_CFG_DIR)/fakeram_130/*/*.bb.v)
export SDC_FILE = $(DESIGN_CFG_DIR)/constraints.sdc

export ADDITIONAL_LEFS := $(wildcard $(DESIGN_CFG_DIR)/fakeram_130/*/*.lef)
export ADDITIONAL_LIBS := $(wildcard $(DESIGN_CFG_DIR)/fakeram_130/*/*.lib)

# ===============================
# Universal "Synthesis-First" Configuration + Floorplan overrides
# ===============================

# Floorplan - Manual die/core sizing to accommodate macro halos
export PLACE_DENSITY    = 0.3
export CORE_UTILIZATION = 30
export FP_PDN_VERTICAL_HALO   = 10
export FP_PDN_HORIZONTAL_HALO = 10
export CORE_MARGIN = 10

# Macro Placement - Generous spacing
export MACRO_PLACE_HALO         = 10 10
export MACRO_PLACE_CHANNEL      = 20 20
export CELL_PAD_IN_SITES        = 4

# RTLMP - Relaxed parameters (match asap7 tuning)
export RTLMP_MAX_NUM_LEVEL      ?= 1
export RTLMP_MIN_AR             ?= 0.2
export RTLMP_TARGET_DEAD_SPACE  ?= 0.40
export RTLMP_TIMING_DRIVEN      ?= 0

# ===============================
# Placement - Very relaxed density for easy synthesis
# ===============================
export GPL_TIMING_DRIVEN        ?= 0
export DPL_TIMING_DRIVEN        ?= 0
export GPL_MAX_ITERATIONS       ?= 500
export GPL_TARGET_DENSITY       = 0.55

# ===============================
# Timing Repair - Minimal to avoid buffer explosion
# ===============================
export SKIP_CTS_REPAIR_TIMING   = 1
export TNS_END_PERCENT          = 100
export HOLD_SLACK_MARGIN        = -2.0

# ===============================
# Routing - rely on platform defaults (met1-met5)
# ===============================
