# Mycelium Node - Mushroom Fruiting Chamber Controller
# ESP32-C6-MINI-1 ESP-IDF CMake configuration

cmake_minimum_required(VERSION 3.20)

# ESP-IDF component registration
include($ENV{IDF_PATH}/tools/cmake/project.cmake)

project(mycelium-node)

# Component source files
idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "."
)

# Custom compile options for size optimization
target_compile_options(${COMPONENT_LIB} PRIVATE
    -Os
    -Wall
    -Wextra
    -Wno-unused-parameter
)

# ESP-IDF component dependencies (auto-resolved)
# - driver (I2C, UART, LEDC, GPIO, ADC)
# - esp_wifi
# - mqtt
# - nvs_flash
# - esp_timer
# - freertos