# Phase Scope — CMakeLists.txt
# STM32G491RET6 firmware build
cmake_minimum_required(VERSION 3.20)

project(phase-scope C ASM)

# Toolchain
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR ARM)

set(TRIPLE arm-none-eabi)
set(CMAKE_C_COMPILER ${TRIPLE}-gcc)
set(CMAKE_ASM_COMPILER ${TRIPLE}-gcc)
set(CMAKE_OBJCOPY ${TRIPLE}-objcopy)
set(CMAKE_SIZE ${TRIPLE}-size)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)

# CPU flags
set(CPU_FLAGS "-mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16")
set(CMAKE_C_FLAGS "${CPU_FLAGS} -Wall -Wextra -Wno-unused-parameter -O2 -g3 -ffunction-sections -fdata-sections -fno-common -fno-builtin-printf")
set(CMAKE_ASM_FLAGS "${CPU_FLAGS} -g3")
set(CMAKE_EXE_LINKER_FLAGS "${CPU_FLAGS} -Wl,--gc-sections -Wl,--print-memory-usage -T${CMAKE_SOURCE_DIR}/stm32g491ret6.ld -specs=nano.specs -specs=nosys.specs")

# CMSIS headers (download separately)
include_directories(${CMAKE_SOURCE_DIR}/../CMSIS/Include)

# Source files
set(SOURCES
    main.c
    adc.c
    power_quality.c
    fft.c
    display.c
    ble_uart.c
    sd_log.c
    calibration.c
)

add_executable(${PROJECT_NAME}.elf ${SOURCES})

# Generate binary and hex
add_custom_command(TARGET ${PROJECT_NAME}.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O binary ${PROJECT_NAME}.elf ${PROJECT_NAME}.bin
    COMMAND ${CMAKE_OBJCOPY} -O ihex ${PROJECT_NAME}.elf ${PROJECT_NAME}.hex
    COMMAND ${CMAKE_SIZE} ${PROJECT_NAME}.elf
)