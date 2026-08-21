# Ferro Weave — firmware top-level CMakeLists
#
# Two build targets:
#   1. STM32G474  — built with arm-none-eabi-gcc + STM32CubeG4 HAL
#                   (see stm32/CMakeLists.txt, not generated here)
#   2. ESP32-C3   — built with ESP-IDF (see esp32/CMakeLists.txt)
#
# The host simulation build lives in sim/CMakeLists.txt and is invoked
# directly:  cmake -B build-sim -S sim && cmake --build build-sim
cmake_minimum_required(VERSION 3.16)
project(ferro_weave C)

message(STATUS "Ferro Weave firmware")
message(STATUS "  STM32 build:  cmake -B build-stm32 -S stm32 -DCMAKE_TOOLCHAIN_FILE=stm32/arm-gcc.cmake")
message(STATUS "  ESP32  build: cd esp32 && idf.py build")
message(STATUS "  Simulation:   cmake -B build-sim -S sim && cmake --build build-sim")