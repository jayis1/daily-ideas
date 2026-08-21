# Ferro Weave — ESP32-C3 main component CMakeLists
idf_component_register(
    SRCS
        "main.c"
        "proto.c"
        "ble.c"
        "wifi.c"
    INCLUDE_DIRS
        "."
    REQUIRES
        driver
        nvs_flash
        esp_timer
        bt
        esp_wifi
)