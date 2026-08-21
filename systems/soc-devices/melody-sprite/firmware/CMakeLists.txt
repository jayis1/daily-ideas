# Melody Sprite — CMakeLists.txt
# RP2040 CMake build configuration using Pico SDK

cmake_minimum_required(VERSION 3.13)

# Pull in Pico SDK
include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)

project(melody_sprite C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

# Initialize Pico SDK
pico_sdk_init()

# Source files
set(SOURCES
    main.c
    synth_engine.c
    sequencer.c
    i2s_audio.c
    touch.c
    display.c
)

# Header files
set(HEADERS
    synth_engine.h
    sequencer.h
    i2s_audio.h
    touch.h
    display.h
)

# Executable
add_executable(melody_sprite ${SOURCES})

target_include_directories(melody_sprite PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

# Link Pico SDK libraries
target_link_libraries(melody_sprite
    pico_stdlib
    pico_multicore
    pico_runtime
    hardware_adc
    hardware_i2c
    hardware_spi
    hardware_dma
    hardware_pio
    hardware_gpio
    hardware_timer
    hardware_flash
    hardware_clocks
    hardware_watchdog
)

# Generate UF2 output (drag-and-drop USB flash)
pico_add_extra_outputs(melody_sprite)

# Enable USB output (for debug UART over USB)
pico_enable_stdio_usb(melody_sprite 1)
pico_enable_stdio_uart(melody_sprite 0)

# Compile definitions
target_compile_definitions(melody_sprite PRIVATE
    PICO_DEFAULT_UART_BAUD_RATE=115200
)

# Optimization flags
target_compile_options(melody_sprite PRIVATE
    -O2
    -ffast-math
    -fsingle-precision-constant
)