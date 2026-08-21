# Gossamer Spin — STM32G474 firmware build
# Requires arm-none-eabi-gcc 10.3+ and STM32G4 CMSIS/HAL
cmake_minimum_required(VERSION 3.16)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Toolchain (point to your arm-none-eabi-gcc)
set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)
set(CMAKE_OBJCOPY arm-none-eabi-objcopy)
set(CMAKE_SIZE arm-none-eabi-size)

project(gossamer_spin C)

# Build flags: -O2 for control loops, -mfpu=fpv4-sp-d16 for M4F, -DSTM32G474xx
set(MCU_FLAGS
    -mcpu=cortex-m4
    -mthumb
    -mfpu=fpv4-sp-d16
    -mfloat-abi=hard
)
set(COMMON_FLAGS
    ${MCU_FLAGS}
    -DSTM32G474xx
    -DUSE_HAL_DRIVER
    -O2
    -ffunction-sections
    -fdata-sections
    -Wall -Wextra
    -Wno-unused-parameter
)
set(CMAKE_C_FLAGS "${COMMON_FLAGS}")
set(CMAKE_EXE_LINKER_FLAGS
    "${MCU_FLAGS} -T${CMAKE_SOURCE_DIR}/linker.ld -Wl,--gc-sections -Wl,-Map=gossamer-spin.map --specs=nano.specs -lc -lm"
)

add_executable(gossamer-spin.elf
    main.c
    hv_supply.c
    syringe_pump.c
    collector.c
    jet_current.c
    safety.c
    env_monitor.c
    oled.c
    sd_log.c
    uart_link.c
    recipe.c
    startup_stm32g474xx.s
)

target_include_directories(gossamer-spin.elf PRIVATE
    .
    ../CMSIS/Core/Include
    ../STM32G4xx_HAL_Driver/Inc
    ../STM32G4xx_HAL_Driver/Inc/Legacy
)