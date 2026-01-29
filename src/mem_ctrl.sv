// uses axi slave interface
// input and outputs was based of the defenition provided in the following:
// https://www.realdigital.org/doc/a9fee931f7a172423e1ba73f66ca4081
// https://github.com/arhamhashmi01/Axi4-lite/blob/main/Axi4-lite-verilator/axi4_lite_slave.sv

`default_nettype none

module mem_ctrl #(
  parameter int WIDTH_P = 32,
  parameter int ADDR_WIDTH = 9
)(

  `ifdef USE_POWER_PINS
    inout  wire VDD,
    inout  wire VSS,
  `endif

  input wire                 ACLK,
  input wire                 ARESETN,

  ////Read Address Channel wire
  input wire [WIDTH_P-1:0]   S_ARADDR,
  input wire                 S_ARVALID,

  //Read Data Channel wire
  input wire                 S_RREADY,

  //Write Address Channel wire
  input wire [WIDTH_P-1:0]   S_AWADDR,
  input wire                 S_AWVALID,

  //Write Data  Channel wire
  input wire [WIDTH_P-1:0]   S_WDATA,
  input wire [3:0]           S_WSTRB,
  input wire                 S_WVALID,

  //Write Response Channel  wireS
  input wire                 S_BREADY,

  //Read Address Channel OUTPUTS
  output                     S_ARREADY,

  //Read Data Channel OUTPUTS
  output     [WIDTH_P-1:0]   S_RDATA,
  output     [1:0]           S_RRESP,
  output                     S_RVALID,

  //Write Address Channel OUTPUTS
  output                     S_AWREADY,
  output                     S_WREADY,

  //Write Response Channel OUTPUTS
  output          [1:0]      S_BRESP,
  output                     S_BVALID

);

  localparam int ExtraBits = ADDR_WIDTH - 9;
  localparam int SramCount = 1 << ExtraBits;


  logic [7:0] sram_data_in;
  logic [7:0] sram_data_out;
  logic [ExtraBits + 8:0] sram_addr;
  logic write_en;

  generate
    for (i = 0; i < SramCount; i = i + 1) begin: gen_srams
      gf180mcu_fd_ip_sram__sram512x8m8wm1 sram_0 (

          `ifdef USE_POWER_PINS
            .VDD  (VDD),
            .VSS  (VSS),
          `endif

          .CLK  (ACLK), // clock
          .CEN  (sram_addr[9 + ExtraBits:9] != i[9 + ExtraBits:9]), // mem enable (active low)
          .GWEN (write_en), // write enable: 0 == write, 1 == read (active low)
          .WEN  (8'b0), // write bitbask (active low)
          .A    (sram_addr[8:0]),   // address
          .D    (sram_data_in),   // data input bus
          .Q    (sram_data_out) // data output bus
      );
    end
  endgenerate


  always_comb begin
    if (ARVALID && RREADY) begin
    end   

  end


endmodule

