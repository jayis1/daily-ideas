#!/bin/bash
# Sonar Cast — flash the STM32G474 firmware via OpenOCD + ST-Link
# Requires: openocd, arm-none-eabi-gcc toolchain
set -e
cd "$(dirname "$0")/../firmware"
mkdir -p build && cd build
cmake -DCMAKE_TOOLCHAIN_FILE=../gcc-arm-none-eabi.cmake .. 2>/dev/null || true
make -j$(nproc)
openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
    -c "program sonar-cast.bin 0x08000000 verify reset exit"
echo "Sonar Cast STM32 firmware flashed."