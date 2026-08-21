# Tremor Tile — CMakeLists.txt
# Pico SDK build configuration for RP2040

cmake_minimum_required(VERSION 3.13)

# Pull in Pico SDK
include(pico_sdk_import.cmake)

project(tremor_tile C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

# Initialize the Pico SDK
pico_sdk_init()

# Main executable
add_executable(tremor_tile
    main/app_main.c
    main/sensor_acq.c
    main/fft_engine.c
    main/anomaly_detect.c
    main/lora_radio.c
    main/remaining_modules.c
)

# Include paths
target_include_directories(tremor_tile PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/main
    ${CMAKE_CURRENT_SOURCE_DIR}/lib
)

# Link Pico SDK libraries
target_link_libraries(tremor_tile
    pico_stdlib
    pico_multicore
    pico_spi
    pico_i2c
    pico_adc
    pico_pwm
    pico_sleep
    hardware_gpio
    hardware_adc
    hardware_flash
    hardware_sync
    hardware_spi
    hardware_i2c
    hardware_pwm
    hardware_sleep
)

# CMSIS-DSP for FFT
# (In production, this would be linked from the CMSIS-DSP library)
# target_link_libraries(tremor_tile cmsis_dsp)

# Generate UF2, HEX, MAP, and disassembly outputs
pico_add_extra_outputs(tremor_tile)

# Enable USB output (for field service)
pico_enable_stdio_usb(tremor_tile 1)
pico_enable_stdio_uart(tremor_tile 0)

# Optimize for size
target_compile_options(tremor_tile PRIVATE -Os -DNDEBUG)

# Debug options (uncomment for development)
# target_compile_options(tremor_tile PRIVATE -O0 -g3 -DDEBUG)
# target_compile_definitions(tremor_tile PRIVATE DEBUG=1)