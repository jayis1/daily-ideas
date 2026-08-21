# Ferro Weave — ESP32-C3 co-processor firmware (ESP-IDF v5.2)
#
# Owns BLE + Wi-Fi. Receives sweep frames from the STM32 over UART,
# repackages them as a BLE GATT characteristic and/or an HTTP/TCP
# endpoint for the companion PC app.
cmake_minimum_required(VERSION 3.16)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(ferro_weave_esp32)