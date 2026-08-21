# Quartz Tuner — firmware top-level CMakeLists
#
# STM32G491RET6 build via arm-none-eabi-gcc + CMake:
#   cmake -B build -DCMAKE_TOOLCHAIN_FILE=toolchain-arm.cmake
#   cmake --build build
#
# Host simulation build:
#   cmake -B build-sim -S sim && cmake --build build-sim
cmake_minimum_required(VERSION 3.16)

project(quartz_tuner C)

message(STATUS "Quartz Tuner firmware")
message(STATUS "  STM32G491RET6 build: cmake -B build -DCMAKE_TOOLCHAIN_FILE=toolchain-arm.cmake && cmake --build build")
message(STATUS "  Simulation:         cmake -B build-sim -S sim && cmake --build build-sim")