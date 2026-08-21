# visco-shear / firmware / esp32c3 / CMakeLists.txt
# ESP-IDF v5.2+ project for Visco Shear ESP32-C3 companion
# Target: ESP32-C3-WROOM-02
#
# Build:
#   idf.py set-target esp32c3
#   idf.py build
#   idf.py -p /dev/ttyUSB1 flash

cmake_minimum_required(VERSION 3.16)

set(EXTRA_COMPONENT_DIRS "")

include($ENV{IDF_PATH}/tools/cmake/project.cmake)

project(visco-shear-c3)