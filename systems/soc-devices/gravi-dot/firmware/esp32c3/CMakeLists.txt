# esp32c3/CMakeLists.txt — ESP-IDF component build
# Build: idf.py set-target esp32c3 && idf.py build flash monitor

idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "."
    REQUIRES driver nvs_flash esp_bt esp_wifi esp_http_client
)