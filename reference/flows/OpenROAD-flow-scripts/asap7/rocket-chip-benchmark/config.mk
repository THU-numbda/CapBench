#############################################
# rocket-chip-benchmark flow configuration - 7nm (ASAP7) #
#############################################

# ===============================
# Platform & design identity
# ===============================
export PLATFORM                 = asap7
export DESIGN_NAME              = ExampleRocketSystem
export DESIGN_NICKNAME          = rocket-chip-benchmark-7nm

# ===============================
# Paths (this file's dir, and RTL root)
export DESIGN_CFG_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
export DESIGN_SRC_DIR := $(abspath $(DESIGN_CFG_DIR)/../../src/rocket-chip-benchmark)

# ===============================

# HDL front-end
# ===============================
export SYNTH_HDL = verilog
export SYNTH_MEMORY_MAX_BITS    = 100000

# ===============================
# Final file lists
# ===============================
export VERILOG_FILES := \
  $(DESIGN_SRC_DIR)/merged_top.v \
  $(DESIGN_SRC_DIR)/sram_stubs.v \
  $(DESIGN_SRC_DIR)/shims.v \
  $(wildcard $(DESIGN_CFG_DIR)/fakeram_7/*/*.bb.v)
export VERILOG_INCLUDE_DIRS    =

# ===============================
# FakeRAM2.0 7nm blackboxes
# ===============================
export ADDITIONAL_LEFS := $(wildcard $(DESIGN_CFG_DIR)/fakeram_7/*/*.lef)
export ADDITIONAL_LIBS := $(wildcard $(DESIGN_CFG_DIR)/fakeram_7/*/*.lib)
# Strip sim helpers / random inits for synth
export VERILOG_DEFINES += \
  -D SYNTHESIS \
  -D RANDOMIZE_GARBAGE_ASSIGN=0 \
  -D RANDOMIZE_DELAY=0 \
  -D RANDOMIZE_REG_INIT=0 \
  -D RANDOMIZE_MEM_INIT=0 \
  -D INIT_RANDOM=0 \
  -D PRINTF_COND=0 \
  -D STOP_COND=0 \
  -D ASSERT_VERBOSE_COND=0

# ===============================
# Constraints & flow knobs
# ===============================
export SDC_FILE = $(DESIGN_CFG_DIR)/constraints.sdc

# ===============================
# Universal "Synthesis-First" Configuration
# Very relaxed settings for easiest synthesis
# ===============================

# Floorplan - Very low utilization for easy placement
export CORE_UTILIZATION = 0.45  # Very relaxed, lots of whitespace
export ASPECT_RATIO = 1.0

# Keep the original macro placement parameters
export MACRO_PLACE_HALO         = 10 10
export MACRO_PLACE_CHANNEL      = 10 10
export CELL_PAD_IN_SITES        = 2

# RTLMP - More relaxed parameters
export RTLMP_MAX_NUM_LEVEL      ?= 1
export RTLMP_MIN_AR             ?= 0.5
export RTLMP_TARGET_DEAD_SPACE  ?= 0.40  # Increased from default
export RTLMP_SIG_NET_THRESHOLD  ?= 30
export RTLMP_TIMING_DRIVEN      ?= 0     # Disabled for easier synthesis

# Flow speedups
export SKIP_LAST_GASP          ?= 1
export SYNTH_MINIMUM_KEEP_SIZE ?= 40000

# ===============================
# Placement - Very relaxed density for easy synthesis
# ===============================
# Timing-driven placement disabled for easier synthesis
export GPL_TIMING_DRIVEN        ?= 0
export DPL_TIMING_DRIVEN        ?= 0
export GPL_MAX_ITERATIONS       ?= 500   # Reduced from default (faster)

# Very density target for easy placement
export GPL_TARGET_DENSITY       = 0.55 


# ===============================
# Timing Repair - Minimal to avoid buffer explosion
# ===============================
export SKIP_CTS_REPAIR_TIMING   = 1
export TNS_END_PERCENT          = 100
export HOLD_SLACK_MARGIN        = -2.0

export DETAILED_ROUTE_ARGS = \
  -droute_end_iter 8 -verbose 1 -drc_report_iter_step 5
