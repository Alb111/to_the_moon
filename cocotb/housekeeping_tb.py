import os
import sys
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles, ReadOnly
import random


current_dir = Path(__file__).resolve().parent
emulation_path = current_dir.parent / "emulation" / "arbitration_cachecoh"
sys.path.append(str(emulation_path))

try:
    from weighted_round_robin import WeightedRoundRobinArbiter
except ImportError:
    print(f"Error: Could not find weighted_round_robin.py in {emulation_path}")
    sys.exit(1)

async def flash_model(dut, data):
    """Simulates a Flash chip bit-stream"""
    # Wait for the Address Phase (32 bits) to finish
    for _ in range(32):
        await RisingEdge(dut.spi_sck_o)
    
    for byte in data:
        for i in range(8):
            await FallingEdge(dut.spi_sck_o)
            dut.spi_miso_i.value = (byte >> (7-i)) & 1

@cocotb.test()
async def test_boot_with_arbiter_contention(dut):
    """Full Boot Test: 2 words with random Arbiter delays"""
    
    cocotb.start_soon(Clock(dut.clk_i, 20, "ns").start())
    
    # initialize arbiter (Housekeeping is index 0)
    weights = [1, 5] 
    arbiter = WeightedRoundRobinArbiter(num_requesters=2, weights=weights)
    
    # reset
    dut.reset_i.value = 1
    dut.arb_gnt_i.value = 0
    dut.spi_miso_i.value = 0
    await ClockCycles(dut.clk_i, 10)
    dut.reset_i.value = 0
    
    boot_data = [
        0x11, 0x22, 0x33, 0x44, # Word 0
        0x55, 0x66, 0x77, 0x88, # Word 1
        0x99, 0xAA, 0xBB, 0xCC, # Word 2
        0xDD, 0xEE, 0xFF, 0x00, # Word 3
        0x12, 0x34, 0x56, 0x78, # Word 4
        0x9A, 0xBC, 0xDE, 0xF0, # Word 5
        0x11, 0x22, 0x33, 0x44, # Word 6
        0x55, 0x66, 0x77, 0x88  # Word 7 (Total 32 bytes)
    ]
    expected_words = [
        0x44332211, 0x88776655, 0xCCBBAA99, 0x00FFEEDD,
        0x78563412, 0xF0DEBC9A, 0x44332211, 0x88776655
    ]
    
    cocotb.start_soon(flash_model(dut, boot_data))

    words_captured = 0
    while words_captured < len(expected_words):
        # 1. wait for request
        await RisingEdge(dut.arb_req_o)
        
        # 2. simulate other things happening on the bus (Wait 1-10 cycles)
        delay = random.randint(1, 10)
        await ClockCycles(dut.clk_i, delay)
        
        # 3. call python arbiter (pretending core 1 isn't requesting)
        # requests = [housekeeping, core1]
        grant_result = arbiter.arbitrate([1, 0]) 
        
        if grant_result[0] == 1:
            dut.arb_gnt_i.value = 1
            # wait for fsm to see grant and pulse write
            await RisingEdge(dut.clk_i) 
            
            if dut.sram_wr_en_o.value == 1:
                actual = int(dut.sram_data_o.value)
                assert actual == expected_words[words_captured]
                dut._log.info(f"✓ Word {words_captured} written: {hex(actual)}")
                words_captured += 1
            
            await FallingEdge(dut.clk_i)
            dut.arb_gnt_i.value = 0

    await RisingEdge(dut.boot_done_o)
    assert dut.cores_en_o.value == 1
    dut._log.info("✓ SUCCESS: Boot Sequence Complete!")

@cocotb.test()
async def test_boot_comprehensive(dut):
    """Comprehensive Test with strict 32-bit formatting and explicit checks"""
    cocotb.start_soon(Clock(dut.clk_i, 20, "ns").start())
    
    # 1. Reset
    dut.reset_i.value = 1
    await ClockCycles(dut.clk_i, 5)
    dut.reset_i.value = 0
    
    # 2. Setup Data: [0, 1, 2, 3...]
    boot_data = [i for i in range(32)]
    expected_words = []
    for i in range(0, 32, 4):
        word = (boot_data[i+3] << 24) | (boot_data[i+2] << 16) | (boot_data[i+1] << 8) | boot_data[i]
        expected_words.append(word)

    cocotb.start_soon(flash_model(dut, boot_data))

    # moniter
    for i in range(len(expected_words)):
        if dut.arb_req_o.value == 1:
            await FallingEdge(dut.arb_req_o)
        await RisingEdge(dut.arb_req_o)
        
        await ReadOnly() # lock sim for reading
        
        actual_data = int(dut.sram_data_o.value)
        actual_addr = int(dut.sram_addr_o.value)
        
        # check against python calculated word
        assert actual_data == expected_words[i], f"DATA BUG! Word {i}: Expected 0x{expected_words[i]:08x}, Got 0x{actual_data:08x}"
        assert actual_addr == (i * 4), f"ADDR BUG! Word {i}: Expected 0x{(i*4):08x}, Got 0x{actual_addr:08x}"

        # exit read only phase before driving signals
        await FallingEdge(dut.clk_i) 
        
        # 4. grant accesss
        dut.arb_gnt_i.value = 1
        await RisingEdge(dut.sram_wr_en_o)
        await FallingEdge(dut.clk_i)
        dut.arb_gnt_i.value = 0
        
        dut._log.info(f"✓ Word {i} Verified: Addr=0x{actual_addr:08x}, Data=0x{actual_data:08x}")




@cocotb.test()
async def test_reset_during_boot(dut):
    """Verify that a reset during boot clears all internal states"""
    clock = Clock(dut.clk_i, 20, "ns")
    cocotb.start_soon(clock.start())
    
    dut.reset_i.value = 1
    await ClockCycles(dut.clk_i, 5)
    dut.reset_i.value = 0
    
    flash_task = cocotb.start_soon(flash_model(dut, [0xAA]*32))
    
    # wait for 1st activity
    await RisingEdge(dut.arb_req_o)
    dut._log.info("Boot started, hitting Reset...")
    
    dut.reset_i.value = 1
    await ClockCycles(dut.clk_i, 10)
    
    # assertion check if hardware actually responded to reset
    assert dut.arb_req_o.value == 0, "Error: Request stayed high during reset!"
    assert dut.sram_addr_o.value == 0, "Error: Address didn't clear!"
    assert dut.boot_done_o.value == 0, "Error: boot_done high during reset!"
    
    flash_task.cancel() 
    dut._log.info("✓ Reset recovery verified.")

@cocotb.test()
async def test_short_boot_failure(dut):
    """Verify cores remain disabled if SPI stream ends prematurely"""
    cocotb.start_soon(Clock(dut.clk_i, 20, "ns").start())
    dut.reset_i.value = 1
    await ClockCycles(dut.clk_i, 5)
    dut.reset_i.value = 0

    # send only 1 word
    short_data = [0xAA, 0xBB, 0xCC, 0xDD]
    flash_task = cocotb.start_soon(flash_model(dut, short_data))
    
    dut._log.info("Sent partial data, waiting to see if system incorrectly activates...")
    await ClockCycles(dut.clk_i, 1000) 
    
    # signal check
    # check that fsm is stuck and wait for more data state and hasnt triggered the final signals

    done_val = dut.boot_done_o.value
    en_val = dut.cores_en_o.value
    
    dut._log.info(f"Signal Check: boot_done={done_val}, cores_en={en_val}")
    
    assert done_val == 0, "FAIL: System reported DONE on partial data!"
    assert en_val == 0, "FAIL: Cores enabled on partial data!"
    
    flash_task.cancel()
    dut._log.info("✓ Short boot failure (Security Check) passed.")

@cocotb.test()
async def test_infinite_arbiter_wait(dut):
    """Verify FSM holds data stable during long arbiter delays"""
    clock = Clock(dut.clk_i, 20, "ns")
    cocotb.start_soon(clock.start())
    dut.reset_i.value = 1
    await ClockCycles(dut.clk_i, 5)
    dut.reset_i.value = 0
    
    # random word
    test_word = random.randint(0, 0xFFFFFFFF)
    test_bytes = [
        test_word & 0xFF,
        (test_word >> 8) & 0xFF,
        (test_word >> 16) & 0xFF,
        (test_word >> 24) & 0xFF
    ]
    
    cocotb.start_soon(flash_model(dut, test_bytes * 8))
    
    await RisingEdge(dut.arb_req_o)
    
    # simulate arbiter being stuck/busy w/ core 1
    dut.arb_gnt_i.value = 0
    dut._log.info("Arbiter busy... holding gnt low for 200 cycles")
    
    for _ in range(200):
        await RisingEdge(dut.clk_i)
        # check fsm is not changing address or data while waiting
        assert dut.sram_data_o.value == test_word, "Data corrupted while waiting for Grant!"
        assert dut.sram_wr_en_o.value == 0, "Write enable pulsed without Grant!"
    
    # give grant
    dut.arb_gnt_i.value = 1
    await RisingEdge(dut.sram_wr_en_o)
    await FallingEdge(dut.clk_i)
    dut.arb_gnt_i.value = 0
    dut._log.info("✓ Long arbiter wait (stability) verified.")

if __name__ == "__main__":
    from cocotb_tools.runner import get_runner
    proj_path = Path(__file__).resolve().parent
    sim = os.getenv("SIM", "icarus")

    sources = [
        proj_path / "../src/housekeeping/spi_engine.sv",
        proj_path / "../src/housekeeping/boot_fsm.sv",
        proj_path / "../src/housekeeping/housekeeping_top.sv"
    ]
    
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="housekeeping_top",
        always=True,
        waves=True
    )
    runner.test(
        hdl_toplevel="housekeeping_top",
        test_module="housekeeping_tb",
        waves=True
    )