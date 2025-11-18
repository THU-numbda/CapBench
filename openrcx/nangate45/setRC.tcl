# Liberty units are fF,kOhm
set_layer_rc -layer metal1 -resistance 5.4286e-03 -capacitance 7.41819E-02
set_layer_rc -layer metal2 -resistance 3.5714e-03 -capacitance 6.74606E-02
set_layer_rc -layer metal3 -resistance 3.5714e-03 -capacitance 8.88758E-02
set_layer_rc -layer metal4 -resistance 1.5000e-03 -capacitance 1.07121E-01
set_layer_rc -layer metal5 -resistance 1.5000e-03 -capacitance 1.08964E-01
set_layer_rc -layer metal6 -resistance 1.5000e-03 -capacitance 1.02044E-01
set_layer_rc -layer metal7 -resistance 1.8750e-04 -capacitance 1.10436E-01
set_layer_rc -layer metal8 -resistance 1.8750e-04 -capacitance 9.69714E-02
# No calibration data available for metal9 and metal10
#set_layer_rc -layer metal9 -resistance 3.7500e-05 -capacitance 3.6864e-02
#set_layer_rc -layer metal10 -resistance 3.7500e-05 -capacitance 2.8042e-02

if {[info exists ::env(OPENRCX_OUT_SPEF)]} {
  set spef_path $::env(OPENRCX_OUT_SPEF)
} else {
  puts "ERROR: OPENRCX_OUT_SPEF environment variable not set"
  exit 1
}

define_process_corner -ext_model_index 0 X
set rcx_rules [file join [file dirname [info script]] rcx_patterns.rules]
if {![file exists $rcx_rules]} {
  puts "ERROR: RCX rules file not found at $rcx_rules"
  exit 1
}
extract_parasitics -ext_model_file $rcx_rules
write_spef $spef_path
