# CMakeLists.txt — Bone Echo firmware
# Target: STM32G474RET6 (ARM Cortex-M4F, 170 MHz, 512 KB flash, 128 KB SRAM)
# Toolchain: arm-none-eabi-gcc + STM32Cube HAL + CMSIS-DSP
cmake_minimum_required(VERSION 3.22)

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR cortex-m4)
set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)
set(CMAKE_OBJCOPY arm-none-eabi-objcopy)

project(bone_echo C ASM)

# ARM math + DSP
set(MCPU "-mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard -mthumb")
add_compile_options(${MCPU} -Os -g3 -ffunction-sections -fdata-sections -Wall -Wextra -std=c11)
add_link_options(${MCPU} -T${CMAKE_CURRENT_SOURCE_DIR}/stm32g474_ret6.ld -Wl,--gc-sections -nostartfiles)

# CMSIS-DSP prebuilt lib (link against libarm_cortexM4lf_math.a)
link_directories(/usr/lib/arm-none-eabi/newlib/thumb/v7e-m+fp/hard)

add_executable(bone_echo.elf
    startup_stm32g474xx.s
    main.c
    tx_pulser.c
    rx_chain.c
    adc.c
    sos.c
    bua.c
    stiffness.c
    normative.c
    phantom.c
    heel_caliper.c
    display.c
    sd_log.c
    ble_bridge.c
    aux_adc.c
    battery.c
    patient.c
    ui.c
)

target_include_directories(bone_echo.elf PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    /usr/include/cmsis
    /usr/include/stm32cubehal
)

target_link_libraries(bone_echo.elf
    arm_cortexM4lf_math
    c
    nosys
)