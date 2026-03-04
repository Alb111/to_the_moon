module housekeeping_top #(
   parameter BOOT_SIZE = 32,
   parameter SRAM_BASE_ADDR = 32'h0000_0000
)(
   input logic clk_i,
   input logic reset_i,

   //external pins (where the computer plugs in)
   input logic ext_sck_i,
   input logic ext_mosi_i,
   input logic ext_csb_i,
   output logic ext_miso_o,
   input logic pass_thru_en_i   // switch: 0 = boot, 1 = pass thru
    
   // spi Flash pins
   output logic spi_sck_o,
   output logic spi_mosi_o,
   input logic spi_miso_i,
   output logic flash_csb_o,
    
   // output writing
   output logic sram_wr_en_o,
   output logic [31:0] sram_addr_o,
   output logic [31:0] sram_data_o,
    
   // Core control
   output logic cores_en_o,
   output logic boot_done_o
);
   // wires between spi and fsm
   logic fsm_sck, fsm_mosi, fsm_csb;
   logic spi_start;
   logic spi_done;
   logic spi_busy;
   logic [7:0] spi_data_out;
   logic [7:0] spi_data_in;
   logic raw_boot_done, raw_cores_en;

   //pass thru mux logic
   // if pass_thru_en_i high -> external pins drive flash
   // else our internal FSM/SPI engine drives flash
   assign spi_sck_o = (pass_thru_en_i) ? ext_sck_i : fsm_sck;
   assign spi_mosi_o = (pass_thru_en_i) ? ext_mosi_i : fsm_mosi;
   assign flash_csb_o = (pass_thru_en_i) ? ext_csb_i  : fsm_csb;
   assign ext_miso_o = spi_miso_i; // pass falsh data back to computer
      
   // spi Engine
   spi_engine spi_master (
      .clk_i(clk_i),
      .reset_i(reset_i || pass_thru_en_i),   //keep spi idle during pass thur
      .start_i(spi_start),
      .data_in_i(spi_data_out),
      .data_out_o(spi_data_in),
      .done_o(spi_done),
      .busy_o(spi_busy),
      .spi_sck_o(fsm_sck), //connected to mux
      .spi_mosi_o(fsm_mosi),  //connected to mux
      .spi_miso_i(spi_miso_i)
   );
   
   // boot fsm
   boot_fsm #(
      .BOOT_SIZE      (BOOT_SIZE),
      .SRAM_BASE_ADDR (SRAM_BASE_ADDR)
   ) boot_controller (
      .clk_i(clk_i),
      .reset_i(reset_i || pass_thru_en_i),   //fsm idel during pass thru
      .spi_start_o(spi_start),
      .spi_out_o(spi_data_out),
      .spi_in_i(spi_data_in),
      .spi_done_i(spi_done),
      .spi_busy_i(spi_busy),
      .flash_csb_o(fsm_csb),     //connect to mux
      .sram_wr_en_o(sram_wr_en_o),
      .sram_addr_o(sram_addr_o),
      .sram_data_o(sram_data_o),
      .cores_en_o(cores_en_o),
      .boot_done_o(boot_done_o)
   );

endmodule
