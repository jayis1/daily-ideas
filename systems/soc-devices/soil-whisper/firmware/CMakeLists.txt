cmake_minimum_required(VERSION 3.22)

# Soil Whisper — STM32WL55JC Firmware
project(soil-whisper C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# STM32WL55JC — Cortex-M4 + Sub-GHz radio
set(MCU_FAMILY STM32WLxx)
set(MCU_MODEL STM32WL55xx)
set(CPU_TYPE cortex-m4)
set(FPU_TYPE fpv4-sp-d16)

# Toolchain
set(CROSS_COMPILE arm-none-eabi-)

set(CMAKE_C_COMPILER ${CROSS_COMPILE}gcc)
set(CMAKE_CXX_COMPILER ${CROSS_COMPILE}g++)
set(CMAKE_ASM_COMPILER ${CROSS_COMPILE}gcc)
set(CMAKE_AR ${CROSS_COMPILE}ar)
set(CMAKE_OBJCOPY ${CROSS_COMPILE}objcopy)
set(CMAKE_SIZE ${CROSS_COMPILE}size)

set(MCU_FLAGS
    -mcpu=${CPU_TYPE}
    -mthumb
    -mfpu=${FPU_TYPE}
    -mfloat-abi=hard
)

set(CMAKE_C_FLAGS "${MCU_FLAGS} -Wall -Wextra -Wno-unused-parameter -O2 -ffunction-sections -fdata-sections -fno-common -fmessage-length=0")
set(CMAKE_ASM_FLAGS "${MCU_FLAGS} -x assembler-with-cpp")
set(CMAKE_EXE_LINKER_FLAGS "${MCU_FLAGS} -Wl,--gc-sections -Wl,--no-warn-rwx-segments -T ${CMAKE_SOURCE_DIR}/STM32WL55JCIX_FLASH.ld -specs=nano.specs -specs=nosys.specs")

# HAL / CMSIS sources (simplified — production uses full CubeMX generated project)
set(HAL_SOURCES
    ${CMAKE_SOURCE_DIR}/system_stm32wlxx.c
)

# Application sources
set(APP_SOURCES
    ${CMAKE_SOURCE_DIR}/main.c
    ${CMAKE_SOURCE_DIR}/startup_stm32wl55xx.c
)

add_executable(${PROJECT_NAME}.elf ${APP_SOURCES} ${HAL_SOURCES})

target_include_directories(${PROJECT_NAME}.elf PRIVATE
    ${CMAKE_SOURCE_DIR}
    ${CMAKE_SOURCE_DIR}/Drivers/CMSIS/Device/ST/STM32WLxx/Include
    ${CMAKE_SOURCE_DIR}/Drivers/CMSIS/Include
    ${CMAKE_SOURCE_DIR}/Drivers/STM32WLxx_HAL_Driver/Inc
)

# Generate .hex and .bin from .elf
add_custom_command(TARGET ${PROJECT_NAME}.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -Oihex $<TARGET_FILE:${PROJECT_NAME}.elf> ${PROJECT_NAME}.hex
    COMMAND ${CMAKE_OBJCOPY} -Obinary $<TARGET_FILE:${PROJECT_NAME}.elf> ${PROJECT_NAME}.bin
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:${PROJECT_NAME}.elf>
)