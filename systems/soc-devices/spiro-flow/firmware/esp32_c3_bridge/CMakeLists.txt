# spiro_flow/firmware/esp32_c3_bridge/CMakeLists.txt
# ESP32-C3 BLE/WiFi bridge firmware
# ESP-IDF v5.2

idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "."
    REQUIRES
        driver
        nvs_flash
        esp_bt
        esp_gap_ble
        esp_gatts
        esp_wifi
        esp_event
        esp_netif
)