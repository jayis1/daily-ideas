# Flux Ring — CMakeLists.txt
# nRF52840 firmware build using Zephyr / nRF Connect SDK

cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{Zephyr_DIR})

project(flux-ring VERSION 1.0.0 LANGUAGES C)

# Source files
target_sources(app PRIVATE
    main/app_main.c
    main/mag_sensor.c
    main/accel_sensor.c
    main/baro_sensor.c
    main/field_engine.c
    main/compass.c
    main/haptic_feedback.c
    main/led_feedback.c
    main/oled_display.c
    main/ble_service.c
    main/data_logger.c
    main/power_manager.c
    main/touch_input.c
)

# Include paths
target_include_directories(app PRIVATE
    main
)

# Compiler options
target_compile_options(app PRIVATE
    -Wall
    -Wextra
    -Wno-unused-parameter
    -O2
)

# Link against math library (for atan2f, sqrtf, etc.)
# Zephyr provides these via newlib or minimal libc
# If using nRF Connect SDK with ARM clang, add:
# target_link_libraries(app PRIVATE m)