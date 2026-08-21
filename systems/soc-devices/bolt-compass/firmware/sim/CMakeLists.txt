# Bolt Compass — host simulation CMakeLists
# Exercises the detect → classify → bearing → range math path with
# synthetic sferics, no ESP-IDF required.
cmake_minimum_required(VERSION 3.16)
project(bolt_compass_sim C)

add_executable(bolt_compass_sim
    main_sim.c
    ../port_sim.c
    ../main/detect.c
    ../main/classify_data.c
    ../main/bearing.c
    ../main/range.c
    ../main/fft.c
)

target_include_directories(bolt_compass_sim PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../main
    ${CMAKE_CURRENT_SOURCE_DIR}/stubs
)

# detect.c calls esp_log — provide stubs in port_sim.c / stubs
target_compile_definitions(bolt_compass_sim PRIVATE
    BOLT_COMPASS_SIM=1
)

target_link_libraries(bolt_compass_sim PRIVATE m)