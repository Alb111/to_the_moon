module boot_fsm (
    input logic clk,
    input logic reset_n,

    output logic spi_start_o,
    output logic [7:0] spi_tx_i,
    input logic [7:0] spi_rx_i,
    input logic spi_done_i,

    output logic cores_run_o
);

    typedef enum logic [3:0] {
        RESET,
        CMD,
        ADDR0,
        ADDR1,
        ADDR2,
        READ0,
        READ1,
        READ2,
        READ3,
        DONE
    } boot_states;

    boot_state curr_state, next_state;
    logic [31:0] word_buf;

    //state register
    always_ff @(posedge clk) begin
        if (!reset_n) begin
            curr_state <= RESET;
        end else begin
            curr_state <= next_state;
        end
    end

    //fsm
    always_comb begin
        next_state = curr_state;
        spi_start_o = 1'b0;
        cores_run_o = 1'b0;

        case(curr_state)
            RESET: next_state = CMD;

            CMD: begin
                spi_tx_i = 8'h03;
                spi_start_o = 1'b1;
                next_state = ADDR0;
            end

            ADDR0: if(spi_done_i) begin
                spi_tx_i = 8'h00; 
                spi_start_o = 1'b1;
                next_state = ADDR1;
            end

            ADDR1: if(spi_done_i) begin
                spi_tx_i = 8'h00; 
                spi_start_o = 1'b1;
                next_state = ADDR2;
            end

            ADDR2: if(spi_done_i) begin
                spi_tx_i = 8'h00; 
                spi_start_o = 1'b1;
                next_state = READ0;
            end

            READ0: if(spi_done_i) begin
                next_state = READ1;
            end

            READ1: if(spi_done_i) begin
                next_state = READ2;
            end

            READ2: if(spi_done_i) begin
                next_state = READ3;
            end

            READ3: if(spi_done_i) begin
                next_state = DONE;
            end

            DONE: begin
                cores_run_o = 1'b1;
            end
        endcase
    end

    // capture data
    always_ff @(posedge clk) begin
        if (curr_state == READ0 && spi_done_i) word_buf[7:0] <= spi_rx_i;
        if (curr_state == READ1 && spi_done_i) word_buf[15:8] <= spi_rx_i;
        if (curr_state == READ2 && spi_done_i) word_buf[23:16] <= spi_rx_i;
        if (curr_state == READ3 && spi_done_i) word_buf[31:24] <= spi_rx_i;
    end
endmodule


