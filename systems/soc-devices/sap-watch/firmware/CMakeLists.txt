# Sap Watch — Tree Sap-Flow Monitor
# STM32WL55JC Firmware — CMake build
#
# Requires STM32CubeWL HAL + LoRaWAN stack components.
# Build with a arm-none-eabi-gcc toolchain.
#
# Copyright (c) 2026 SoC Device Inventions. MIT License.

cmake_minimum_required(VERSION 3.22)

project(sap_watch C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# ---- Toolchain (set via -DCMAKE_TOOLCHAIN_FILE=... or environment) ----
# Default to arm-none-eabi-gcc if not cross-compiling already
if(NOT CMAKE_C_COMPILER MATCHES "arm-none-eabi")
    set(CMAKE_C_COMPILER arm-none-eabi-gcc)
    set(CMAKE_CXX_COMPILER arm-none-eabi-g++)
    set(CMAKE_OBJCOPY arm-none-eabi-objcopy CACHE STRING "")
    set(CMAKE_OBJDUMP arm-none-eabi-objdump CACHE STRING "")
    set(CMAKE_SIZE arm-none-eabi-size CACHE STRING "")
endif()

# ---- MCU flags (Cortex-M4 + M0+ dual core; firmware runs on M4) ----
set(MCU_FLAGS "-mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard")
set(MCU_FLAGS "${MCU_FLAGS} -DSTM32WL55xx -DUSE_HAL_DRIVER")

set(CMAKE_C_FLAGS_INIT "${MCU_FLAGS} -Wall -Wextra -Wno-unused-parameter -Os -ffunction-sections -fdata-sections -g3")
set(CMAKE_EXE_LINKER_FLAGS_INIT "${MCU_FLAGS} -T${CMAKE_SOURCE_DIR}/STM32WL55JC_FLASH.ld -Wl,--gc-sections -Wl,-Map=${CMAKE_BINARY_DIR}/sap_watch.map -Wl,--print-memory-usage")

# ---- Include paths ----
# (STM32Cube HAL paths set via STM32CUBE_WL_PATH env var)
if(DEFINED ENV{STM32CUBE_WL_PATH})
    set(HAL_INC
        $ENV{STM32CUBE_WL_PATH}/Drivers/STM32WLxx_HAL_Driver/Inc
        $ENV{STM32CUBE_WL_PATH}/Drivers/CMSIS/Device/ST/STM32WLxx/Include
        $ENV{STM32CUBE_WL_PATH}/Drivers/CMSIS/Include
        $ENV{STM32CUBE_WL_PATH}/Middlewares/Third_Party/LoRaWAN/Endpoint
        $ENV{STM32CUBE_WL_PATH}/Middlewares/Third_Party/SubGHz_Phy
    )
endif()

include_directories(
    ${CMAKE_SOURCE_DIR}
    ${HAL_INC}
)

# ---- Source files ----
set(SAP_WATCH_SOURCES
    main.c
    config.h
    probe.c
    probe.h
    heat_ratio.c
    heat_ratio.h
    sensors.c
    sensors.h
    lorawan.c
    lorawan.h
    power.c
    power.h
    storage.c
    storage.h
    heater_safety.c
    heater_safety.h
    stm32wl55_startup.s
    system_stm32wl55.c
)

# STM32Cube HAL sources (if available)
if(DEFINED ENV{STM32CUBE_WL_PATH})
    file(GLOB HAL_SOURCES
        $ENV{STM32CUBE_WL_PATH}/Drivers/STM32WLxx_HAL_Driver/Src/*.c
    )
    list(APPEND SAP_WATCH_SOURCES ${HAL_SOURCES})
endif()

# ---- Executable ----
add_executable(sap_watch.elf ${SAP_WATCH_SOURCES})

# ---- Post-build: generate .bin and .hex ----
add_custom_command(TARGET sap_watch.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:sap_watch.elf> sap_watch.bin
    COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:sap_watch.elf> sap_watch.hex
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:sap_watch.elf>
    COMMENT "Generating sap_watch.bin and sap_watch.hex"
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
)