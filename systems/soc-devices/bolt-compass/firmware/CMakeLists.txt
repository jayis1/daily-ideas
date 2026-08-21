# Bolt Compass — firmware top-level CMakeLists
#
# ESP32-S3 build via ESP-IDF v5.2:
#   idf.py set-target esp32s3 && idf.py build
#
# Host simulation build (exercises detect/classify/bearing/range math):
#   cmake -B build-sim -S sim && cmake --build build-sim
cmake_minimum_required(VERSION 3.16)
project(bolt_compass C)

message(STATUS "Bolt Compass firmware")
message(STATUS "  ESP32-S3 build: idf.py set-target esp32s3 && idf.py build")
message(STATUS "  Simulation:     cmake -B build-sim -S sim && cmake --build build-sim")