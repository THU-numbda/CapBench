#############################################
# rocket-chip flow configuration #
#############################################

# ===============================
# Platform & design identity
# ===============================
export PLATFORM                 = nangate45
export DESIGN_NAME              = ExampleRocketSystem
export DESIGN_NICKNAME          = rocket-chip-benchmark-45nm

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
  $(wildcard $(DESIGN_CFG_DIR)/fakeram_45/*/*.bb.v)
export VERILOG_INCLUDE_DIRS    =

# ===============================
# FakeRAM2.0 7nm blackboxes
# ===============================
export ADDITIONAL_LEFS := $(wildcard $(DESIGN_CFG_DIR)/fakeram_45/*/*.lef)
export ADDITIONAL_LIBS := $(wildcard $(DESIGN_CFG_DIR)/fakeram_45/*/*.lib)
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

# Route-friendly defaults (Nangate45)
export CORE_UTILIZATION         = 55
export CORE_MARGIN              = 4
export PLACE_DENSITY            = 0.58

# Keepouts for future macros (SRAMs, etc.)
# Reduced from 30μm to 10μm for consistent optimization
export MACRO_PLACE_HALO         = 10 10
export MACRO_PLACE_CHANNEL      = 10 10

# Gentle cell padding
export CELL_PAD_IN_SITES        = 2

# Flow speedups
export SKIP_LAST_GASP          ?= 1
export SYNTH_MINIMUM_KEEP_SIZE ?= 40000
