cmake_minimum_required(VERSION 3.20)

# Spectra Charm — STM32G491RET6 Spectrometer Firmware
project(spectra-charm C)

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

# CPU flags for Cortex-M4F
set(CPU_FLAGS "-mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard")

# Compiler flags
set(CMAKE_C_FLAGS "${CPU_FLAGS} -Wall -Wextra -Werror -Wno-unused-parameter")
set(CMAKE_C_FLAGS_DEBUG "-O0 -g3")
set(CMAKE_C_FLAGS_RELEASE "-O2 -flto")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -ffunction-sections -fdata-sections -fno-common")

# Linker flags
set(CMAKE_EXE_LINKER_FLAGS "${CPU_FLAGS} -T${CMAKE_SOURCE_DIR}/stm32g491ret6.ld")
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -Wl,--gc-sections -Wl,--print-memory-usage")
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -specs=nano.specs -specs=nosys.specs")

# Source files
set(SOURCES
    main.c
    spectrometer.c
    deconv.c
    matching.c
    baseline.c
    beerlambert.c
    led_driver.c
    flash_store.c
    uart_proto.c
    eeprom.c
    fuel_gauge.c
    power.c
)

# Include paths
include_directories(
    ${CMAKE_SOURCE_DIR}
    ${CMAKE_SOURCE_DIR}/Drivers/STM32G4_HAL_Driver/Inc
    ${CMAKE_SOURCE_DIR}/Drivers/CMSIS/Device/ST/STM32G4xx/Include
    ${CMAKE_SOURCE_DIR}/Drivers/CMSIS/Core/Include
    ${CMAKE_SOURCE_DIR}/Middlewares/FreeRTOS/Source/include
    ${CMAKE_SOURCE_DIR}/Middlewares/FreeRTOS/Source/portable/GCC/ARM_CM4F
)

# Define linker output
add_executable(${PROJECT_NAME}.elf ${SOURCES})
target_compile_definitions(${PROJECT_NAME}.elf PRIVATE
    STM32G491xx
    USE_HAL_DRIVER
    ARM_MATH_CM4
    __FPU_PRESENT=1
)

# Generate hex and bin
add_custom_command(TARGET ${PROJECT_NAME}.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -Oihex $<TARGET_FILE:${PROJECT_NAME}.elf> ${PROJECT_NAME}.hex
    COMMAND ${CMAKE_OBJCOPY} -Obinary $<TARGET_FILE:${PROJECT_NAME}.elf> ${PROJECT_NAME}.bin
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:${PROJECT_NAME}.elf>
)