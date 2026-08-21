# CMakeLists.txt — Taste Bead firmware
# ESP32-S3-based pocket electronic tongue (EIS liquid fingerprinter)
# Built with ESP-IDF v5.1+

cmake_minimum_required(VERSION 3.16)

# This project is intended to be built with ESP-IDF
# Include this in an ESP-IDF project directory structure:
#   taste-bead/firmware/
#   ├── CMakeLists.txt       (this file)
#   ├── sdkconfig.h
#   ├── main.c
#   ├── ad5941.c / .h
#   ├── ...
#   └── components/           (optional: vendor libraries)
#
# Build: idf.py build && idf.py flash

# When using ESP-IDF, the top-level CMakeLists.txt just calls idf.cmake
# The following is a standalone CMakeLists for reference

include($ENV{IDF_PATH}/tools/cmake/project.cmake OPTIONAL)

project(taste_bead C)

# If using ESP-IDF build system, sources are automatically picked up
# For standalone builds, list all sources:

set(TASTE_BEAD_SOURCES
    main.c
    ad5941.c
    mux.c
    eis.c
    features.c
    classifier.c
    library.c
    display.c
    sd_log.c
    ble.c
    bme280.c
    ui.c
    calibrate.c
)

if(COMMAND target_sources)
    target_sources(${CMAKE_PROJECT_NAME} PRIVATE ${TASTE_BEAD_SOURCES})
endif()

# Component requirements (ESP-IDF)
if(COMMAND target_link_libraries)
    target_link_libraries(${CMAKE_PROJECT_NAME}
        PRIVATE
        esp_timer
        esp_wifi
        esp_bt
        nvs_flash
        driver_gpio
        driver_spi
        driver_i2c
        driver_adc
        esp_partition
    )
endif()