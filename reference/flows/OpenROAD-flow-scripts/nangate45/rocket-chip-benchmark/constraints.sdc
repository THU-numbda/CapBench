# RocketChip merged top-level constraints

# Primary clock on top-level port 'clock'
create_clock -name core_clk -period 10.000 [get_ports clock]

# Basic clock uncertainty
set_clock_uncertainty 0.20 [get_clocks core_clk]

# Treat reset as asynchronous (no timing to sequential)
set_false_path -from [get_ports reset] -to [all_registers]

# 0 ns IO delays relative to the core clock (adjust if needed)
set_input_delay 0 -clock core_clk [get_ports -filter "direction==in && name!=clock && name!=reset"]
set_output_delay 0 -clock core_clk [all_outputs]

