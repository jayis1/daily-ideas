# Cor Sono — ESP-IDF firmware build
# ESP32-S3-WROOM-1, ESP-IDF v5.2+

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
        "main"
    REQUIRES
        driver
        esp_timer
        nvs_flash
        esp_wifi
        esp_bt
        esp_codec_dev
)

# Use ESP-IDF native WiFi + BLE
# Requires the esp-tflite-micro component for on-device CNN inference
# (see sdkconfig.defaults for memory configuration)