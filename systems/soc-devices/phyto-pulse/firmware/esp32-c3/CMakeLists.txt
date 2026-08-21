# CMakeLists.txt — ESP32-C3 firmware for Phyto Pulse
# ESP-IDF project

cmake_minimum_required(VERSION 3.16)

set(COMPONENTS esp_timer nvs_flash esp_wifi esp_bt bt nimble driver)

idf_component_register(
    SRCS
        "main/main.c"
        "main/ble_service.c"
        "main/wifi_server.c"
        "main/uart_protocol.c"
    INCLUDE_DIRS
        "main"
)

# Project name
set(PROJECT_NAME "phyto-pulse-esp32c3")
set(EXTRA_COMPONENT_DIRS "")