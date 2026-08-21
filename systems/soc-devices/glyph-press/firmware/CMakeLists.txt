# glyph_press/firmware/CMakeLists.txt
# CMake build for Glyph Press firmware (RP2040 + Pico SDK)
#
# Build:
#   mkdir build && cd build
#   cmake ..
#   make -j4

cmake_minimum_required(VERSION 3.13)

# Pull in Pico SDK (must have PICO_SDK_PATH set)
include(${PICO_SDK_PATH}/pico_sdk_init.cmake)

project(glyph_press C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

# Initialise the Pico SDK
pico_sdk_init()

# Executable
add_executable(glyph_press
    main.c
    braille.c
    emboss.c
    feed.c
    sh1106.c
    ble_uart.c
    sd_card.c
    flash_table.c
    buttons.c
    encoder.c
    ws2812.c
    battery.c
    paper_sensor.c
)

# Include paths
target_include_directories(glyph_press PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

# Link Pico SDK libraries
target_link_libraries(glyph_press
    pico_stdlib
    hardware_gpio
    hardware_adc
    hardware_i2c
    hardware_spi
    hardware_uart
    hardware_pwm
    pico_multicore
    pico_bootsel_via_double_reset
)

# Optional: link FatFs for SD card support
# (uncomment to enable full FAT32 file reading)
# add_subdirectory(fatfs)
# target_link_libraries(glyph_press fatfs)

# Enable USB output, release build
pico_enable_stdio_usb(glyph_press 1)
pico_enable_stdio_uart(glyph_press 0)
pico_add_extra_outputs(glyph_press)

# Link map
target_link_options(glyph_press PRIVATE -Wl,-Map=glyph_press.map)