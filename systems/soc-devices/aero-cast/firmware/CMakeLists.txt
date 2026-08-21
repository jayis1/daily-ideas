# CMakeLists.txt — Aero Cast firmware
# RP2040-based pocket 3-axis ultrasonic anemometer

cmake_minimum_required(VERSION 3.13)

include(pico_sdk_import.cmake)

project(aero_cast C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(aero_cast
    main.c
    sonic.c
    wind.c
    bme280.c
    display.c
    sd_log.c
    ble_bridge.c
    ui.c
    calibration.c
)

target_sources(aero_cast PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}/pio_sonic.pio
)

target_include_directories(aero_cast PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}
    ${PICO_SDK_PATH}/src/common/pico_stdlib/include
)

target_link_libraries(aero_cast PRIVATE
    pico_stdlib
    pico_bootrom
    hardware_pio
    hardware_i2c
    hardware_spi
    hardware_adc
    hardware_dma
    hardware_flash
    hardware_gpio
    pico_multicore
    pico_time
    pico_cyw43_arch   # optional, if using Pico W
    hardware_watchdog
    hardware_sync
)

pico_enable_stdio_usb(aero_cast 1)
pico_enable_stdio_uart(aero_cast 0)
pico_add_extra_outputs(aero_cast)