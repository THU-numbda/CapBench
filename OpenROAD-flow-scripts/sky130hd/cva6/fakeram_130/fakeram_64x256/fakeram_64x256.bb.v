module fakeram_64x256
(
   rd_out,
   addr_in,
   we_in,
   wd_in,
   clk,
   ce_in
);
   parameter BITS = 64;
   parameter WORD_DEPTH = 256;
   parameter ADDR_WIDTH = 8;
   parameter corrupt_mem_on_X_p = 1;

   output reg [BITS-1:0]    rd_out;
   input  [ADDR_WIDTH-1:0]  addr_in;
   input                    we_in;
   input  [BITS-1:0]        wd_in;
   input                    clk;
   input                    ce_in;

endmodule
