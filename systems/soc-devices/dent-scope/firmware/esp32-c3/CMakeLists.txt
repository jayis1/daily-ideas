# dent-scope / firmware/esp32-c3/CMakeLists.txt
# ESP-IDF CMake for ESP32-C3-MINI-1 BLE/Wi-Fi uplink module
# MIT License
cmake_minimum_required(VERSION 3.16)

set(EXTRA_COMPONENT_DIRS "")
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(dent-scope-esp32)