# CMakeLists.txt — Plume Sniffer firmware
# ESP32-C3-based pocket gas chromatograph (MEMS TCD)
# Built with ESP-IDF v5.1+
#
# Build:  idf.py set-target esp32c3 && idf.py build && idf.py flash -p /dev/ttyUSB0

cmake_minimum_required(VERSION 3.16)

include($ENV{IDF_PATH}/tools/cmake/project.cmake OPTIONAL)

project(plume_sniffer C)

set(PLUME_SOURCES
    main.c
    tcd.c
    column.c
    preconc.c
    pump.c
    peak.c
    identify.c
    library.c
    display.c
    sd_log.c
    ble.c
    bme280.c
    battery.c
    ui.c
)

if(COMMAND target_sources)
    target_sources(${CMAKE_PROJECT_NAME} PRIVATE ${PLUME_SOURCES})
endif()

if(COMMAND target_link_libraries)
    target_link_libraries(${CMAKE_PROJECT_NAME}
        PRIVATE
        esp_timer
        esp_bt
        esp_wifi
        nvs_flash
        driver_gpio
        driver_spi
        driver_i2c
        driver_adc
        driver_ledc
        driver_rmt
    )
endif()