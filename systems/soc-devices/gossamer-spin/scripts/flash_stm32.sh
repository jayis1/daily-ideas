#!/bin/bash
# Gossamer Spin — Flash STM32G474 firmware via ST-Link + OpenOCD
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FW_DIR="${SCRIPT_DIR}/../firmware"
BUILD_DIR="${FW_DIR}/build"

echo "=== Gossamer Spin — STM32 firmware flash ==="

# Build if not already built
if [ ! -f "${BUILD_DIR}/gossamer-spin.bin" ]; then
    echo "Building firmware..."
    mkdir -p "${BUILD_DIR}"
    cd "${BUILD_DIR}"
    cmake -DCMAKE_TOOLCHAIN_FILE=../gcc-arm-none-eabi.cmake ..
    make -j$(nproc)
fi

echo "Flashing via ST-Link..."
openocd -f interface/stlink.cfg -f target/stm32g4x.cfg \
    -c "program ${BUILD_DIR}/gossamer-spin.bin 0x08000000 verify reset exit"

echo "Done. STM32 firmware flashed."