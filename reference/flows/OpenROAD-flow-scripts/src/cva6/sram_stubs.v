// Generated shim to bridge CVA6's asap7-style macro names (fakeram7_*)
// to the FakeRAM outputs used in Sky130/Nangate flows (fakeram_*).

module fakeram7_64x256 (
  output [63:0] rd_out,
  input  [7:0]  addr_in,
  input         we_in,
  input  [63:0] wd_in,
  input         clk,
  input         ce_in
);
  fakeram_64x256 u_mem (
    .rd_out (rd_out),
    .addr_in(addr_in),
    .we_in  (we_in),
    .wd_in  (wd_in),
    .clk    (clk),
    .ce_in  (ce_in)
  );
endmodule

module fakeram7_128x64 (
  output [127:0] rd_out,
  input  [5:0]   addr_in,
  input          we_in,
  input  [127:0] wd_in,
  input          clk,
  input          ce_in
);
  fakeram_128x64 u_mem (
    .rd_out (rd_out),
    .addr_in(addr_in),
    .we_in  (we_in),
    .wd_in  (wd_in),
    .clk    (clk),
    .ce_in  (ce_in)
  );
endmodule

module fakeram7_64x28 (
  output [63:0] rd_out,
  input  [4:0]  addr_in,
  input         we_in,
  input  [63:0] wd_in,
  input         clk,
  input         ce_in
);
  fakeram_64x28 u_mem (
    .rd_out (rd_out),
    .addr_in(addr_in),
    .we_in  (we_in),
    .wd_in  (wd_in),
    .clk    (clk),
    .ce_in  (ce_in)
  );
endmodule

module fakeram7_64x25 (
  output [63:0] rd_out,
  input  [4:0]  addr_in,
  input         we_in,
  input  [63:0] wd_in,
  input         clk,
  input         ce_in
);
  fakeram_64x25 u_mem (
    .rd_out (rd_out),
    .addr_in(addr_in),
    .we_in  (we_in),
    .wd_in  (wd_in),
    .clk    (clk),
    .ce_in  (ce_in)
  );
endmodule
