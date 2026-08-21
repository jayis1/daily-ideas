# Ferro Weave — simulation build (host, no STM32 HAL / no ESP-IDF)
# Links the portable math path (bh.c, sweep.c) + sim stubs (port_sim.c)
# against the host libc so the B-H computation can be verified without
# hardware. Excludes main.c (which provides the firmware main()).
cmake_minimum_required(VERSION 3.16)
project(ferro_weave_sim C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()
add_compile_options(-Wall -Wextra -O2 -Wno-unused-parameter)

add_executable(ferro_weave_sim
    ${CMAKE_CURRENT_SOURCE_DIR}/../port_sim.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../main/bh.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../main/sweep.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../main/adc.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../main/integrator.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../main/power.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../main/display.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../main/sdlog.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../main/esp_link.c
)

target_include_directories(ferro_weave_sim PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../main)
target_link_libraries(ferro_weave_sim PRIVATE m)