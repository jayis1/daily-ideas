# Cor Sono — firmware/main component CMakeLists
# ESP-IDF v5.2+

idf_component_register(
    SRCS
        "main.c"
        "audio.c"
        "anc.c"
        "pcg.c"
        "classifier.c"
        "oled_display.c"
        "sd_logger.c"
        "ble_stream.c"
        "wifi_web.c"
        "buttons.c"
    INCLUDE_DIRS
        "."
    REQUIRES
        driver
        esp_timer
        nvs_flash
        esp_wifi
        esp_bt
)