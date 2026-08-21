/*
 * Ping Caliper — ESP32-C3 Communications Module
 *
 * CMakeLists.txt — top-level build for the ESP32-C3 comms MCU
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

# ESP32-C3 build (ESP-IDF)
# This CMakeLists is used with idf.py build from this directory.
#
# Build:
#   idf.py set-target esp32c3
#   idf.py build
#   idf.py -p /dev/ttyUSB0 flash monitor

cmake_minimum_required(VERSION 3.20)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)

project(ping-caliper-esp32c3 C)