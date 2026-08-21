# Native simulation of the Sky Lens physics + math path.
# Compiles on a host (gcc/clang), links port_sim.c (stubbed HALs),
# and runs a synthetic 24-hour muon run to verify the coincidence,
# zenith-fit, skymap, pressure-correction, and lifetime-fit code.
cmake_minimum_required(VERSION 3.16)
project(sky_lens_sim C)

set(SRC
    ${CMAKE_CURRENT_SOURCE_DIR}/../port_sim.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../esp32/main/coincidence.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../esp32/main/adc.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../esp32/main/sipm_bias.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../esp32/main/imu.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../esp32/main/pressure.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../esp32/main/skymap.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../esp32/main/zenith.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../esp32/main/lifetime.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../esp32/main/sdlog.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../esp32/main/display.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../esp32/main/ble.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../esp32/main/wifi.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../esp32/main/proto.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../esp32/main/power.c
    ${CMAKE_CURRENT_SOURCE_DIR}/../esp32/main/main.c
)

add_executable(sky_lens_sim ${SRC})
target_include_directories(sky_lens_sim PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../esp32/main
    ${CMAKE_CURRENT_SOURCE_DIR}/..)
target_compile_definitions(sky_lens_sim PRIVATE SKY_LENS_SIM=1)
target_link_libraries(sky_lens_sim PRIVATE m)