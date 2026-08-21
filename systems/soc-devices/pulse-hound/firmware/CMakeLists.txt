# Pulse Hound — ESP32-S3 Firmware
# CMakeLists.txt — ESP-IDF build
#
# Copyright (c) 2026 SoC Device Inventions. MIT License.
#
# Build with ESP-IDF:
#   idf.py set-target esp32s3
#   idf.py build
#   idf.py flash monitor

cmake_minimum_required(VERSION 3.16)

# Include ESP-IDF build system
# (This file assumes the project is opened inside an ESP-IDF project structure)
# In a real setup, the top-level CMakeLists.txt would contain:
#   idf_build_set_property(COMPONENTS "driver;esp_timer;esp_wifi;bt;fatfs;sdmmc")
#   file(GLOB SRCS "*.c")
#   idf_component_register(SRCS ${SRCS} INCLUDE_DIRS ".")

# ---- Standalone portable build (for syntax checking / simulation) ----
# This CMakeLists allows building the firmware source as a host-side
# simulation stub (no real hardware — for testing the algorithms).

project(pulse_hound_sim C)

set(SRC_FILES
    main.c
    rf_detector.c
    spectrum.c
    direction.c
    classifier.c
    audio.c
    display.c
    ble_stream.c
    sd_logger.c
    power.c
)

# Simulation build: compile all sources with a HAL stub
# The platform HAL stubs are provided by a separate port_sim.c file
# (not included in the repo — created for testing only)
if(DEFINED ENV{PULSE_HOUND_SIM})
    add_executable(pulse_hound_sim ${SRC_FILES} port_sim.c)
    target_include_directories(pulse_hound_sim PRIVATE .)
    target_link_libraries(pulse_hound_sim m)
endif()

# ---- ESP-IDF build (production) ----
# When included as a component in an ESP-IDF project:
if(DEFINED ENV{IDF_PATH})
    # This file becomes a component CMakeLists.txt
    # idf_component_register(
    #     SRCS ${SRC_FILES}
    #     INCLUDE_DIRS "."
    #     REQUIRES driver esp_timer nvs_flash bt fatfs sdmmc
    # )
endif()

# ---- Build targets ----
# Production: use ESP-IDF
#   idf.py set-target esp32s3
#   idf.py build
#
# Simulation (for algorithm testing without hardware):
#   PULSE_HOUND_SIM=1 cmake -B build && cmake --build build