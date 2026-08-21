# Refracto Bead ESP32-C3 main component CMakeLists.txt

idf_component_register(
    SRCS
        "main.c"
        "ble_service.c"
        "wifi_server.c"
        "uart_protocol.c"
    INCLUDE_DIRS
        "."
)