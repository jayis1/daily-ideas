# Echo Trap — ESP32-S3 Acoustic Insect Trap Firmware
# CMakeLists.txt — top-level ESP-IDF project
#
# Build:
#   idf.py set-target esp32s3
#   idf.py build
#   idf.py -p /dev/ttyUSB0 flash monitor
#
# Copyright (c) 2026 SoC Device Inventions. MIT License.

cmake_minimum_required(VERSION 3.20)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)

project(echo-trap C)