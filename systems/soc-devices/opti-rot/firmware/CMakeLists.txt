# cmake minimum version
cmake_minimum_required(VERSION 3.16)

# Project
project(opti_rot C)

# Toolchain
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# ARM toolchain (arm-none-eabi-gcc)
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR cortex-m4)
set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)
set(CMAKE_OBJCOPY arm-none-eabi-objcopy)

# STM32G491 flags
set(MCU_FLAGS "-mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard")
set(CMAKE_C_FLAGS "${MCU_FLAGS} -O2 -ffunction-sections -fdata-sections -Wall -Wextra -g")
set(CMAKE_EXE_LINKER_FLAGS "${MCU_FLAGS} -T${CMAKE_SOURCE_DIR}/STM32G491RETX_FLASH.ld -Wl,--gc-sections -Wl,-Map=opti_rot.map")

# HAL include paths (STM32CubeMX generated)
include_directories(
    Inc
    Drivers/STM32G4xx_HAL_Driver/Inc
    Drivers/CMSIS/Device/ST/STM32G4xx/Include
    Drivers/CMSIS/Include
)

# Sources
set(SOURCES
    Src/main.c
    Src/stm32g4xx_it.c
    Src/stepper.c
    Src/photodiode.c
    Src/polarimeter.c
    Src/drude.c
    Src/temperature.c
    Src/library.c
    Src/display.c
    Src/sd_log.c
    Src/ble_bridge.c
    Src/ui.c
    Src/led.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_rcc.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_gpio.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_i2c.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_spi.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_uart.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_adc.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_dac.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_tim.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_cordic.c
)

add_executable(opti_rot.elf ${SOURCES})
target_link_libraries(opti_rot.elf c)

# Generate .bin and .hex
add_custom_command(TARGET opti_rot.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:opti_rot.elf> opti_rot.bin
    COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:opti_rot.elf> opti_rot.hex
    COMMENT "Generating opti_rot.bin and opti_rot.hex"
)