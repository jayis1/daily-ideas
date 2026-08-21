# Sonar Cast — STM32G474 firmware build
# Requires arm-none-eabi-gcc 10.3+ and STM32G4 CMSIS/HAL
cmake_minimum_required(VERSION 3.16)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Toolchain (point to your arm-none-eabi-gcc)
set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)
set(CMAKE_OBJCOPY arm-none-eabi-objcopy)
set(CMAKE_SIZE arm-none-eabi-size)

project(sonar_cast C)

# Build flags: -O2 for DSP, -mfpu=fpv4-sp-d16 for M4F, -DSTM32G474xx
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
    "${MCU_FLAGS} -T${CMAKE_SOURCE_DIR}/linker.ld -Wl,--gc-sections -Wl,-Map=sonar-cast.map --specs=nano.specs -lc -lm"
)

add_executable(sonar-cast.elf
    main.c
    chirp.c
    hrtim_drv.c
    adc_dsp.c
    detector.c
    bottom_class.c
    imuw.c
    depth.c
    sd_log.c
    oled.c
    uart_link.c
    model.c
    startup_stm32g474xx.s
)

target_include_directories(sonar-cast.elf PRIVATE
    .
    ../CMSIS/Core/Include
    ../STM32G4xx_HAL_Driver/Inc
    ../STM32G4xx_HAL_Driver/Inc/Legacy
)

target_link_libraries(sonar-cast.elf PRIVATE m)

add_custom_command(TARGET sonar-cast.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:sonar-cast.elf> sonar-cast.bin
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:sonar-cast.elf>
    COMMENT "Generating sonar-cast.bin and printing size"
)