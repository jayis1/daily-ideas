# CMakeLists.txt — QCM Halo firmware build
# STM32G474RET6 with ARM GCC
cmake_minimum_required(VERSION 3.22)

project(qcm_halo C)

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
set(CMAKE_EXE_LINKER_FLAGS "${MCU_FLAGS} -T${CMAKE_SOURCE_DIR}/linker_script.ld -Wl,--gc-sections -Wl,-Map=qcm_halo.map")

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
    Core/Src/qcm_driver.c
    Core/Src/dissipation.c
    Core/Src/sauerbrey.c
    Core/Src/voigt.c
    Core/Src/overtone.c
    Core/Src/temperature.c
    Core/Src/liquid.c
    Core/Src/display.c
    Core/Src/storage.c
    Core/Src/ble_bridge.c
    Core/Src/onewire.c
    Core/Src/power.c
    Core/Src/i2c_util.c
    # STM32 HAL sources
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
add_executable(qcm_halo.elf ${SOURCES})

# ── Post-build ──────────────────────────────────────────
add_custom_command(TARGET qcm_halo.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:qcm_halo.elf> qcm_halo.hex
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:qcm_halo.elf> qcm_halo.bin
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:qcm_halo.elf>
    COMMENT "Generating HEX and BIN files"
)