# SPDX-License-Identifier: MIT
# Levia Forge — CMake build for RP2040 firmware
cmake_minimum_required(VERSION 3.13)

# Pull in Pico SDK (must be on CMAKE_MODULE_PATH or set PICO_SDK_PATH)
include(pico_sdk_import.cmake)

project(levia_forge C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(levia_forge
    main.c
    phase_engine.c
    phase_compute.c
    transducer_layout.c
    display.c
    tof.c
    sd_log.c
    ble_bridge.c
    safety.c
    input.c
)

# PIO assembly
pico_generate_pio_header(levia_forge
    ${CMAKE_CURRENT_LIST_DIR}/pio_phase.pio
)

target_include_directories(levia_forge PRIVATE ${CMAKE_CURRENT_LIST_DIR})

target_link_libraries(levia_forge
    pico_stdlib
    pico_multicore
    pico_dma
    pico_pio
    hardware_adc
    hardware_i2c
    hardware_spi
    hardware_pwm
    hardware_watchdog
    hardware_flash
    hardware_sync
    hardware_clocks
)

# Enable USB output for debug
pico_enable_stdio_usb(levia_forge 0)
pico_enable_stdio_uart(levia_forge 1)

# Create UF2 + ELF + BIN + MAP
pico_add_extra_outputs(levia_forge)