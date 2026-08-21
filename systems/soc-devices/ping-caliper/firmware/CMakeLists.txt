cmake_minimum_required(VERSION 3.20)

# Ping Caliper — STM32G474RET6 Ultrasonic NDT Gauge Firmware
project(ping-caliper C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Toolchain setup — expects arm-none-eabi-gcc on PATH
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR ARM)

set(TOOLCHAIN_PREFIX arm-none-eabi-)
set(CMAKE_C_COMPILER ${TOOLCHAIN_PREFIX}gcc)
set(CMAKE_CXX_COMPILER ${TOOLCHAIN_PREFIX}g++)
set(CMAKE_ASM_COMPILER ${TOOLCHAIN_PREFIX}gcc)
set(CMAKE_AR ${TOOLCHAIN_PREFIX}ar)
set(CMAKE_OBJCOPY ${TOOLCHAIN_PREFIX}objcopy)
set(CMAKE_OBJDUMP ${TOOLCHAIN_PREFIX}objdump)
set(CMAKE_SIZE ${TOOLCHAIN_PREFIX}size)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)

# CPU flags for Cortex-M4F (STM32G474)
set(CPU_FLAGS "-mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard")

# Compiler flags
set(CMAKE_C_FLAGS "${CPU_FLAGS} -Wall -Wextra -Werror -Wno-unused-parameter")
set(CMAKE_C_FLAGS_DEBUG "-O0 -g3")
set(CMAKE_C_FLAGS_RELEASE "-O2 -flto")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -ffunction-sections -fdata-sections -fno-common")

# Linker flags
set(CMAKE_EXE_LINKER_FLAGS "${CPU_FLAGS} -T${CMAKE_SOURCE_DIR}/stm32g474ret6.ld")
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -Wl,--gc-sections -Wl,--print-memory-usage")
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -specs=nano.specs -specs=nosys.specs")

# Source files
set(SOURCES
    main.c
    pulser.c
    tgc.c
    receiver.c
    thickness.c
    flaw.c
    materials.c
    calibration.c
    display.c
    sd_log.c
    uart_proto.c
    power.c
    startup.c
    system_stm32g474.c
)

# Include dirs
include_directories(${CMAKE_SOURCE_DIR})

# Executable
add_executable(ping-caliper.elf ${SOURCES})

# Generate hex and bin
add_custom_command(TARGET ping-caliper.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:ping-caliper.elf> ping-caliper.hex
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:ping-caliper.elf> ping-caliper.bin
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:ping-caliper.elf>
    COMMENT "Generating hex and binary"
)