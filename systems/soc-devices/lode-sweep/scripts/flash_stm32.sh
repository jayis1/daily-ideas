#!/bin/bash
# Lode Sweep — flash STM32 via OpenOCD + ST-Link
# Usage: ./flash_stm32.sh [path/to/firmware.bin]

set -e

FW="${1:-../firmware/build/lode-sweep.bin}"

if [ ! -f "$FW" ]; then
    echo "Error: firmware binary not found at $FW"
    echo "Build it first: cd firmware && mkdir build && cd build && cmake .. && make -j"
    exit 1
fi

echo "Flashing $FW to STM32G474 via ST-Link..."
openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
    -c "program $FW 0x08000000 verify reset exit"

echo "Done. STM32 firmware flashed successfully."