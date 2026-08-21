# visco-shear / firmware / CMakeLists.txt
# CMake build for Visco Shear firmware (RP2040 + Pico SDK)
#
# Build:
#   mkdir build && cd build
#   cmake ..
#   make -j4

cmake_minimum_required(VERSION 3.13)

# Pull in Pico SDK (must have PICO_SDK_PATH set)
include(${PICO_SDK_PATH}/pico_sdk_init.cmake)

project(visco_shear C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

# Initialise the Pico SDK
pico_sdk_init()

# Executable
add_executable(visco_shear
    main.c
    stepper.c
    torque.c
    rheology.c
    temperature.c
    spindle.c
    oled_display.c
    sd_logger.c
    ble_uart.c
    database.c
    buttons.c
)

# Include paths
target_include_directories(visco_shear PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

# Link Pico SDK libraries
target_link_libraries(visco_shear
    pico_stdlib
    hardware_gpio
    hardware_adc
    hardware_i2c
    hardware_spi
    hardware_uart
    hardware_pwm
    hardware_dma
    hardware_pio
    pico_multicore
    pico_bootsel_via_double_reset
)

# Enable USB output, release build
pico_enable_stdio_usb(visco_shear 1)
pico_enable_stdio_uart(visco_shear 0)
pico_add_extra_outputs(visco_shear)

# Link map
target_link_options(visco_shear PRIVATE -Wl,-Map=visco_shear.map)