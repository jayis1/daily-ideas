# CMakeLists.txt — Fluor Cast firmware build
# STM32G474RET6 with STM32CubeMX / ARM GCC
cmake_minimum_required(VERSION 3.22)

project(fluor_cast C)

# ── Toolchain ───────────────────────────────────────────
set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)
set(CMAKE_OBJCOPY arm-none-eabi-objcopy)
set(CMAKE_SIZE arm-none-eabi-size)

set(MCU_ARCH cortex-m4)
set(MCU_FPU fpv4-sp-d16)
set(MCU_FPU_ABI hard)

set(MCU_FLAGS
    -mcpu=${MCU_ARCH}
    -mthumb
    -mfpu=${MCU_FPU}
    -mfloat-abi=${MCU_FPU_ABI}
)

set(CMAKE_C_FLAGS "${MCU_FLAGS} -std=c11 -Os -Wall -Wextra -ffunction-sections -fdata-sections -g3")
set(CMAKE_EXE_LINKER_FLAGS "${MCU_FLAGS} -T${CMAKE_SOURCE_DIR}/linker_script.ld -Wl,--gc-sections -Wl,-Map=fluor_cast.map")

# ── Include paths ───────────────────────────────────────
include_directories(
    Core/Inc
    Drivers/STM32G4xx_HAL_Driver/Inc
    Drivers/STM32G4xx_HAL_Driver/Inc/Legacy
    Drivers/CMSIS/Device/ST/STM32G4xx/Include
    Drivers/CMSIS/Include
)

# ── Source files ────────────────────────────────────────
set(SOURCES
    Core/Src/main.c
    Core/Src/ccd_driver.c
    Core/Src/led_wheel.c
    Core/Src/fluorometer.c
    Core/Src/eem.c
    Core/Src/library.c
    Core/Src/display.c
    Core/Src/storage.c
    Core/Src/ble_bridge.c
    Core/Src/onewire.c
    Core/Src/power.c
    # STM32 HAL sources (add as needed)
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_adc.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_i2c.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_spi.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_tim.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_uart.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_gpio.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_rcc.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_pwr.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_flash.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_dma.c
    Drivers/CMSIS/Device/ST/STM32G4xx/Source/Templates/system_stm32g4xx.c
    Drivers/CMSIS/Device/ST/STM32G4xx/Source/Templates/gcc/startup_stm32g474xx.s
)

# ── Defines ─────────────────────────────────────────────
add_definitions(
    -DSTM32G474xx
    -DUSE_HAL_DRIVER
    -DDEBUG
)

# ── Target ──────────────────────────────────────────────
add_executable(fluor_cast.elf ${SOURCES})

# ── Post-build: generate .hex and .bin ──────────────────
add_custom_command(TARGET fluor_cast.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:fluor_cast.elf> fluor_cast.hex
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:fluor_cast.elf> fluor_cast.bin
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:fluor_cast.elf>
    COMMENT "Generating HEX and BIN files"
)