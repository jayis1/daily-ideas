# pyro-balance / esp32-c3 CMakeLists.txt
# ESP-IDF v5.x build
idf_component_register(SRCS "main/main.c"
                       INCLUDE_DIRS "."
                       REQUIRES driver nvs_flash bt esp_wifi esp_http_server)