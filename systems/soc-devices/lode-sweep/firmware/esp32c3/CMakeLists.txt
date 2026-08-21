# Lode Sweep — ESP32-C3 radio/GPS firmware (ESP-IDF v5.2+)
idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "."
    REQUIRES
        driver
        nvs_flash
        esp_wifi
        esp_bt
        esp_log
)