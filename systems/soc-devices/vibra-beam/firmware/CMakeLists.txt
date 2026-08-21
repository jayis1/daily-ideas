# CMakeLists.txt — Vibra Beam firmware build
# STM32G474RET6 with ARM GCC
cmake_minimum_required(VERSION 3.22)

project(vibra_beam C)

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
set(CMAKE_EXE_LINKER_FLAGS "${MCU_FLAGS} -T${CMAKE_SOURCE_DIR}/linker_script.ld -Wl,--gc-sections -Wl,-Map=vibra_beam.map")

# ── Include paths ───────────────────────────────────────
include_directories(
    Core/Inc
    Drivers/STM32G4xx_HAL_Driver/Inc
    Drivers/STM32G4xx_HAL_Driver/Inc/Legacy
    Drivers/CMSIS/Device/ST/STM32G4xx/Include
    Drivers/CMSIS/Include
    Drivers/CMSIS/DSP/Include
)

# ── Source files ────────────────────────────────────────
set(SOURCES
    Core/Src/main.c
    Core/Src/interferometer.c
    Core/Src/dsp.c
    Core/Src/imu.c
    Core/Src/laser.c
    Core/Src/display.c
    Core/Src/storage.c
    Core/Src/ble_bridge.c
    Core/Src/audio.c
    Core/Src/power.c
    Core/Src/onewire.c
    Core/Src/i2c_util.c
)

# ── HAL / CMSIS (placeholder paths — vendor drops here) ──
set(HAL_SOURCES
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_adc.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_i2c.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_spi.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_tim.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_uart.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_i2s.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_cordic.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_iwdg.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_gpio.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_dma.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_rcc.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_pwr.c
    Drivers/STM32G4xx_HAL_Driver/Src/stm32g4xx_hal_flash.c
    Drivers/STM32G4xx_HAL_Driver/Src/system_stm32g4xx.c
    Drivers/CMSIS/DSP/Source/TransformFunctions/arm_rfft_fast_f32.c
    Drivers/CMSIS/DSP/Source/TransformFunctions/arm_rfft_fast_init_f32.c
    Drivers/CMSIS/DSP/Source/TransformFunctions/arm_cfft_f32.c
    Drivers/CMSIS/DSP/Source/TransformFunctions/arm_cfft_radix4_f32.c
    Drivers/CMSIS/DSP/Source/CommonTables/arm_const_structs.c
)

# ── FatFs (for SD logging) ──
set(FATFS_SOURCES
    Middlewares/Third_Party/FatFs/source/ff.c
    Middlewares/Third_Party/FatFs/source/diskio.c
    Middlewares/Third_Party/FatFs/source/sd_diskio.c
)

add_executable(vibra_beam.elf ${SOURCES} ${HAL_SOURCES} ${FATFS_SOURCES})

target_link_libraries(vibra_beam.elf m)

add_custom_command(TARGET vibra_beam.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:vibra_beam.elf> vibra_beam.bin
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:vibra_beam.elf>
    COMMENT "Generating vibra_beam.bin"
)