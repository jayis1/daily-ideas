# hall-puck / esp32-c3 / main / CMakeLists.txt
idf_component_register(SRCS "main.c"
                       INCLUDE_DIRS "."
                       REQUIRES driver nvs_flash bt esp_wifi esp_http_server)