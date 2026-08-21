# Mussel Watch — nRF52840 Firmware
# CMakeLists.txt — nRF Connect SDK / Zephyr build
#
# Copyright (c) 2026 SoC Device Inventions. MIT License.
#
# Production build (nRF Connect SDK / Zephyr):
#   west build -b nrf52840dk_nrf52840 firmware
#   west flash
#
# Simulation build (algorithm test on host, no hardware):
#   MUSSEL_WATCH_SIM=1 cmake -B build && cmake --build build
#   ./build/mussel_watch_sim

cmake_minimum_required(VERSION 3.16)

# ---- Standalone portable build (for syntax checking / simulation) ----
# This CMakeLists allows building the firmware source as a host-side
# simulation stub (no real hardware — for testing the algorithms).

project(mussel_watch_sim C)

set(SRC_FILES
    main.c
    gape_sensor.c
    water_quality.c
    anomaly.c
    lora_uplink.c
    ble_config.c
    logger.c
    power.c
)

# Simulation build: compile all sources with a HAL stub
# The platform HAL stubs are provided by a separate port_sim.c file
# (not included in the repo — created for testing only)
if(DEFINED ENV{MUSSEL_WATCH_SIM})
    add_executable(mussel_watch_sim ${SRC_FILES} port_sim.c)
    target_include_directories(mussel_watch_sim PRIVATE .)
    target_link_libraries(mussel_watch_sim m)
endif()

# ---- nRF Connect SDK / Zephyr build (production) ----
# When building within the nRF Connect SDK tree, the top-level CMakeLists
# or west.yml targets this directory as a Zephyr app. The Zephyr build
# system automatically picks up all .c files in the directory.
#
# Zephyr CMakeLists.txt equivalent:
# target_sources(app PRIVATE
#     main.c
#     gape_sensor.c
#     water_quality.c
#     anomaly.c
#     lora_uplink.c
#     ble_config.c
#     logger.c
#     power.c
# )
# target_include_directories(app PRIVATE .)
#
# Required Kconfig options (prj.conf):
#   CONFIG_BT=y
#   CONFIG_BT_PERIPHERAL=y
#   CONFIG_BT_GATT_DYNAMIC_DB=y
#   CONFIG_SPI=y
#   CONFIG_I2C=y
#   CONFIG_ADC=y
#   CONFIG_SDHC=y
#   CONFIG_FATFS=y
#   CONFIG_FLASH=y
#   CONFIG_FLASH_PAGE_LAYOUT=y
#
# Required device tree overlays:
#   &i2c0 { sda-pin = <3>; scl-pin = <4>; frequency = <100000>; };
#   &spi0 { mosi-pin = <29>; miso-pin = <28>; sck-pin = <30>; };
#   &adc { channel@0 { ... }; channel@1 { ... }; };

# ---- Build targets ----
# Production: use nRF Connect SDK
#   west build -b nrf52840dk_nrf52840 firmware
#   west flash
#
# Simulation (for algorithm testing without hardware):
#   MUSSEL_WATCH_SIM=1 cmake -B build && cmake --build build