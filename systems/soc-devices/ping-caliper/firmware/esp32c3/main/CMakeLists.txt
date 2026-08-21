/*
 * Ping Caliper — ESP32-C3 Communications Module
 * main/CMakeLists.txt
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

idf_component_register(
    SRCS
        "main.c"
        "uart_comm.c"
        "ble_ndt.c"
        "wifi_api.c"
        "button.c"
        "led_indicator.c"
    INCLUDE_DIRS
        "."
)