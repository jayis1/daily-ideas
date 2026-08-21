# gravi-dot/firmware/CMakeLists.txt
# STM32G474RET6 firmware build (arm-none-eabi-gcc + STM32Cube HAL + FreeRTOS)

cmake_minimum_required(VERSION 3.13)
project(gravi_dot C)

# Toolchain file: cmake/gcc-arm-none-eabi.cmake
# Sets CMAKE_C_COMPILER, CMAKE_OBJCOPY, etc.

set(MCU   stm32g474ret6)
set(MCU_FLAGS
    -mcpu=cortex-m4
    -mfpu=fpv4-sp-d16
    -mfloat-abi=hard
    -mthumb
)

set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${MCU_FLAGS} -Os -Wall -Wextra -ffunction-sections -fdata-sections -g3")
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} ${MCU_FLAGS} -T${CMAKE_SOURCE_DIR}/linker/STM32G474RETX_FLASH.ld -Wl,--gc-sections")

# HAL / FreeRTOS sources (expected in Drivers/ and Middlewares/ from CubeMX)
file(GLOB HAL_SRC     Drivers/STM32G4xx_HAL_Driver/Src/*.c)
file(GLOB FREERTOS_SRC Middlewares/Third_Party/FreeRTOS/Source/*.c
                      Middlewares/Third_Party/FreeRTOS/Source/CMSIS_RTOS/*.c
                      Middlewares/Third_Party/FreeRTOS/Source/portable/GCC/ARM_CM4F/*.c)

add_executable(gravi_dot.elf
    main.c
    adxl355.c
    scl3300.c
    ms5837.c
    ds18b20.c
    sh1106.c
    neom9n.c
    cordic_math.c
    gravity_corrections.c
    system_stm32g4xx.c
    startup_stm32g474xx.s
    ${HAL_SRC}
    ${FREERTOS_SRC}
)

target_include_directories(gravi_dot.elf PRIVATE
    .
    Inc
    Drivers/STM32G4xx_HAL_Driver/Inc
    Drivers/STM32G4xx_HAL_Driver/Inc/Legacy
    Drivers/CMSIS/Device/ST/STM32G4xx/Include
    Drivers/CMSIS/Include
    Middlewares/Third_Party/FreeRTOS/Source/include
    Middlewares/Third_Party/FreeRTOS/Source/CMSIS_RTOS
    Middlewares/Third_Party/FreeRTOS/Source/portable/GCC/ARM_CM4F
)

target_compile_definitions(gravi_dot.elf PRIVATE
    STM32G474xx
    USE_HAL_DRIVER
    HAL_CORDIC_MODULE_ENABLED
)

# Generate .hex and .bin
add_custom_command(TARGET gravi_dot.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex   $<TARGET_FILE:gravi_dot.elf> gravi_dot.hex
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:gravi_dot.elf> gravi_dot.bin
    COMMENT "Generating gravi_dot.hex and gravi_dot.bin"
)