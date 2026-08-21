cmake_minimum_required(VERSION 3.16)

# Iono Pin — STM32G474RET6 firmware (CMake entry point)
# This top-level CMakeLists bootstraps the STM32 arm-none-eabi build.
# The ESP32-C3 bridge lives in ../bridge/ and is built with ESP-IDF.

project(iono_pin_stm32 C ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

set(MCPU "-mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb")

set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${MCPU} -Os -g3 -ffunction-sections -fdata-sections -Wall -Wextra")
set(CMAKE_EXE_LINKER_FLAGS "${MCPU} -T ${CMAKE_CURRENT_SOURCE_DIR}/main/stm32g474_ret6.ld -Wl,--gc-sections -nostartfiles")

add_executable(iono_pin.elf
    main/startup_stm32g474xx.s
    main/main.c
    main/hv_supply.c
    main/shutter.c
    main/ionizer.c
    main/electrometer.c
    main/ims.c
    main/library.c
    main/pump.c
    main/bme280.c
    main/ds18b20.c
    main/display.c
    main/sd_log.c
    main/ble_bridge.c
    main/safety.c
    main/buttons.c
)

target_include_directories(iono_pin.elf PRIVATE main)
target_link_libraries(iono_pin.elf PRIVATE arm_cortexM4lf_math)

add_custom_command(TARGET iono_pin.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:iono_pin.elf> iono_pin.hex
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:iono_pin.elf> iono_pin.bin
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:iono_pin.elf>
)