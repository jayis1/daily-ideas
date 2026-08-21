cmake_minimum_required(VERSION 3.16)

# Iono Pin — ESP32-C3-MINI-1 BLE/Wi-Fi bridge firmware (ESP-IDF)
# Built with `idf.py build flash monitor` from this directory.

idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "."
    REQUIRES driver nvs_flash bt esp_wifi
)