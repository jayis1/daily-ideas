# terra_pin/firmware/CMakeLists.txt
# ESP32-S3 firmware build using ESP-IDF v5.2
#
# Build with:
#   idf.py set-target esp32s3
#   idf.py build
#   idf.py -p /dev/ttyUSB0 flash monitor

# ESP-IDF CMake integration expects this file to be the main component
# CMakeLists.txt inside a component or project directory.

set(SRCS
    main.c
    scd41.c
    ezo_orp.c
    ezo_ec.c
    ds18b20.c
    moisture.c
    shi.c
    sh1106.c
    sdlog.c
    ble.c
)

idf_component_register(
    SRCS ${SRCS}
    INCLUDE_DIRS "."
    REQUIRES
        driver
        nvs_flash
        esp_timer
        esp_bt
        esp_gap_ble
        esp_gatts
        fatfs
        sdmmc
        led_strip
)

# Extra component config for the LED strip RMT driver
idf_build_set_property(COMPILE_DEFINITIONS
    "CONFIG_BT_NIMBLE_ENABLED=0"
    "CONFIG_BT_BLUEDROID_ENABLED=1"
    APPEND)