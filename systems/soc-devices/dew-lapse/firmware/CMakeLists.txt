# frost-point firmware
#
# Top-level CMake build for STM32L476RG.
cmake_minimum_required(VERSION 3.13)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Toolchain is provided by arm-none-eabi-gcc; use the standard STM32Cube
# toolchain file shipped with STM32CubeIDE or define your own.
project(frost_point C)

# --- HAL / CMSIS sources (from STM32Cube_FW_L4_V1.18.0) -----------------
set(HAL_DIR ${CMAKE_SOURCE_DIR}/Drivers)
file(GLOB HAL_CORE  ${HAL_DIR}/STM32L4xx_HAL_Driver/Src/*.c)
file(GLOB HAL_PORT  ${HAL_DIR}/STM32L4xx_HAL_Driver/Src/stm32l4xx_hal_*.c)
set(HAL_SRCS ${HAL_CORE} ${HAL_PORT}
    ${HAL_DIR}/CMSIS/Device/ST/STM32L4xx/Source/Templates/system_stm32l4xx.c)

# --- Application sources -------------------------------------------------
set(APP_SRCS
    src/main.c
    src/system_stm32l4xx.c
    src/startup_stm32l4xx.s
    src/adc_ads122.c
    src/tec.c
    src/pid.c
    src/mirror.c
    src/dewpoint.c
    src/optics.c
    src/sensors.c
    src/flash_log.c
    src/ble.c
    src/oled.c
    src/state_machine.c
)

add_executable(frost_point.elf
    ${APP_SRCS}
    ${HAL_SRCS}
)

target_include_directories(frost_point.elf PRIVATE
    inc
    ${HAL_DIR}/STM32L4xx_HAL_Driver/Inc
    ${HAL_DIR}/CMSIS/Device/ST/STM32L4xx/Include
    ${HAL_DIR}/CMSIS/Include
)

target_compile_definitions(frost_point.elf PRIVATE
    STM32L476xx
    USE_HAL_DRIVER
)

target_compile_options(frost_point.elf PRIVATE
    -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard
    -Os -g3 -ffunction-sections -fdata-sections -Wall -Wextra
)

target_link_options(frost_point.elf PRIVATE
    -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard
    -T${CMAKE_SOURCE_DIR}/linker/STM32L476RG_FLASH.ld
    -Wl,--gc-sections -Wl,-Map=frost_point.map
)

add_custom_command(TARGET frost_point.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:frost_point.elf> frost_point.hex
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:frost_point.elf> frost_point.bin
)