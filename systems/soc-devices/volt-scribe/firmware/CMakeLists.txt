# volt-scribe CMakeLists.txt
# Build for STM32G491RET6 using STM32CubeMX / arm-none-eabi-gcc

cmake_minimum_required(VERSION 3.20)

project(volt-scribe C ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Toolchain
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR ARM)

set(TOOLCHAIN_PREFIX arm-none-eabi-)
set(CMAKE_C_COMPILER ${TOOLCHAIN_PREFIX}gcc)
set(CMAKE_ASM_COMPILER ${TOOLCHAIN_PREFIX}gcc)
set(CMAKE_CXX_COMPILER ${TOOLCHAIN_PREFIX}g++)
set(CMAKE_OBJCOPY ${TOOLCHAIN_PREFIX}objcopy)
set(CMAKE_SIZE ${TOOLCHAIN_PREFIX}size)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)

# CPU flags
set(CPU_FLAGS
    -mcpu=cortex-m4
    -mthumb
    -mfloat-abi=hard
    -mfpu=fpv4-sp-d16
)

set(COMMON_FLAGS
    ${CPU_FLAGS}
    -Wall
    -Wextra
    -Wno-unused-parameter
    -O2
    -ffunction-sections
    -fdata-sections
    -fno-common
    -fno-builtin
    -ffreestanding
)

set(CMAKE_C_FLAGS "${COMMON_FLAGS}" CACHE STRING "C flags")
set(CMAKE_ASM_FLAGS "${COMMON_FLAGS} -x assembler-with-cpp" CACHE STRING "ASM flags")

set(LINKER_SCRIPT ${CMAKE_SOURCE_DIR}/STM32G491RETx_FLASH.ld)
set(CMAKE_EXE_LINKER_FLAGS
    "${CPU_FLAGS} -T${LINKER_SCRIPT} -Wl,--gc-sections -Wl,--print-memory-usage"
    CACHE STRING "Linker flags")

# STM32 HAL sources (from CubeMX generated project)
set(HAL_DIR ${CMAKE_SOURCE_DIR}/Drivers/STM32G4xx_HAL_Driver/Src)
set(HAL_SOURCES
    ${HAL_DIR}/stm32g4xx_hal.c
    ${HAL_DIR}/stm32g4xx_hal_cordic.c
    ${HAL_DIR}/stm32g4xx_hal_dac.c
    ${HAL_DIR}/stm32g4xx_hal_dac_ex.c
    ${HAL_DIR}/stm32g4xx_hal_adc.c
    ${HAL_DIR}/stm32g4xx_hal_adc_ex.c
    ${HAL_DIR}/stm32g4xx_hal_i2c.c
    ${HAL_DIR}/stm32g4xx_hal_i2c_ex.c
    ${HAL_DIR}/stm32g4xx_hal_spi.c
    ${HAL_DIR}/stm32g4xx_hal_spi_ex.c
    ${HAL_DIR}/stm32g4xx_hal_uart.c
    ${HAL_DIR}/stm32g4xx_hal_uart_ex.c
    ${HAL_DIR}/stm32g4xx_hal_gpio.c
    ${HAL_DIR}/stm32g4xx_hal_rcc.c
    ${HAL_DIR}/stm32g4xx_hal_rcc_ex.c
    ${HAL_DIR}/stm32g4xx_hal_cortex.c
    ${HAL_DIR}/stm32g4xx_hal_flash.c
    ${HAL_DIR}/stm32g4xx_hal_flash_ex.c
    ${HAL_DIR}/stm32g4xx_hal_pwr.c
    ${HAL_DIR}/stm32g4xx_hal_pwr_ex.c
    ${HAL_DIR}/stm32g4xx_hal_tim.c
    ${HAL_DIR}/stm32g4xx_hal_tim_ex.c
    ${HAL_DIR}/stm32g4xx_hal_dma.c
    ${HAL_DIR}/stm32g4xx_hal_dma_ex.c
)

# Application sources
set(APP_SOURCES
    main.c
    potentiostat.c
    cv_engine.c
    dpv_engine.c
    swv_engine.c
    eis_engine.c
    amperometric.c
    dsp.c
    display.c
    sd_log.c
    ble_relay.c
    stm32g4xx_it.c
    system_stm32g4xx.c
    startup_stm32g491xx.s
)

add_executable(volt-scribe.elf
    ${APP_SOURCES}
    ${HAL_SOURCES}
)

target_include_directories(volt-scribe.elf PRIVATE
    ${CMAKE_SOURCE_DIR}
    ${CMAKE_SOURCE_DIR}/Drivers/CMSIS/Device/ST/STM32G4xx/Include
    ${CMAKE_SOURCE_DIR}/Drivers/CMSIS/Include
    ${CMAKE_SOURCE_DIR}/Drivers/STM32G4xx_HAL_Driver/Inc
    ${CMAKE_SOURCE_DIR}/Core/Inc
)

target_compile_definitions(volt-scribe.elf PRIVATE
    STM32G491xx
    USE_HAL_DRIVER
    HSE_VALUE=8000000
)

# Generate .bin and .hex
add_custom_command(TARGET volt-scribe.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:volt-scribe.elf> volt-scribe.bin
    COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:volt-scribe.elf> volt-scribe.hex
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:volt-scribe.elf>
)