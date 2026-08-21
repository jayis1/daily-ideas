# Spectra Charm — ESP32-C3 Firmware Build
idf_component_register(SRCS
    "main/main.c"
    "main/ble_spectrum.c"
    "main/wifi_api.c"
    "main/oled_ui.c"
    "main/uart_comm.c"
    "main/button.c"
    "main/led_indicator.c"
    INCLUDE_DIRS
    "main"
)