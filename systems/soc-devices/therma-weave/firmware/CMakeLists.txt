# Therma Weave — ESP32-C3 Firmware Build Configuration
# CMakeLists.txt

cmake_minimum_required(VERSION 3.16)

# Project definition
project(therma-weave)

# ESP-IDF component registration
idf_component_register(
    SRCS
        "main/app_main.c"
        "main/zone_controller.c"
        "main/temp_sensor.c"
        "main/current_monitor.c"
        "main/ble_service.c"
        "main/oled_display.c"
        "main/activity_detect.c"
        "main/ambient_sensor.c"
        "main/power_manager.c"
        "main/safety_watchdog.c"
        "main/nvs_storage.c"
    INCLUDE_DIRS
        "main"
    REQUIRES
        bt
        nvs_flash
        driver
        esp_timer
)

# Set target
set(IDF_TARGET esp32c3)

# Optimizations for size
target_compile_options(${COMPONENT_LIB} PRIVATE
    -Os
    -ffunction-sections
    -fdata-sections
)

target_link_options(${COMPONENT_LIB} PRIVATE
    -Wl,--gc-sections
    -Wl,--cref
)