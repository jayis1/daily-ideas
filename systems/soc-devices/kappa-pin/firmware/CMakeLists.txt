# kappa-pin / firmware / CMakeLists.txt
# ESP-IDF v5.2+ project for Kappa Pin — Pocket Thermal Conductivity Meter
# Target: ESP32-S3-WROOM-1
#
# Build:
#   idf.py set-target esp32s3
#   idf.py build
#   idf.py -p /dev/ttyUSB0 flash monitor

cmake_minimum_required(VERSION 3.16)

set(EXTRA_COMPONENT_DIRS "")

include($ENV{IDF_PATH}/tools/cmake/project.cmake)

project(kappa-pin)