// BSG Memory stubs for rocket-chip-benchmark
module rockettile_dcache_data_arrays_0_512x256 (
	RW0_addr,
	RW0_en,
	RW0_clk,
	RW0_wmode,
	RW0_wdata,
	RW0_rdata,
	RW0_wmask
);
	input [8:0] RW0_addr;
	input RW0_en;
	input RW0_clk;
	input RW0_wmode;
	input [255:0] RW0_wdata;
	output wire [255:0] RW0_rdata;
	input [7:0] RW0_wmask;
	
	// BSG fakeram instance
	fakeram_256x512 bsg_mem (
		.rd_out(RW0_rdata),
		.addr_in(RW0_addr),
		.we_in(RW0_en & RW0_wmode),
		.wd_in(RW0_wdata),
		.clk(RW0_clk),
		.ce_in(RW0_en)
	);
endmodule


// ICache data arrays: 512x128 -> fakeram_128x512_1rw
module rockettile_icache_data_arrays_512x128 (
	RW0_addr,
	RW0_en,
	RW0_clk,
	RW0_wmode,
	RW0_wdata,
	RW0_rdata,
	RW0_wmask
);
	input [8:0] RW0_addr;
	input RW0_en;
	input RW0_clk;
	input RW0_wmode;
	input [127:0] RW0_wdata;
	output wire [127:0] RW0_rdata;
	input [3:0] RW0_wmask;
	
	// BSG fakeram instance
	fakeram_128x512 bsg_mem (
		.rd_out(RW0_rdata),
		.addr_in(RW0_addr),
		.we_in(RW0_en & RW0_wmode),
		.wd_in(RW0_wdata),
		.clk(RW0_clk),
		.ce_in(RW0_en)
	);
endmodule