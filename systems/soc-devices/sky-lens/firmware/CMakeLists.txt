# Top-level CMake for Sky Lens firmware.
# Builds the ESP32-S3 target (via ESP-IDF) and a native simulation
# target (no ESP-IDF required) that exercises the physics + math path.
cmake_minimum_required(VERSION 3.16)

# The ESP-IDF build is invoked from firmware/esp32 with idf.py.
# This file is consumed only by the native simulation target.
if(NOT ESP_PLATFORM)
    add_subdirectory(sim)
endif()